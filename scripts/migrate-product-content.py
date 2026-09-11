#!/usr/bin/env python3
"""Phase 4 — copy custom.* metafield VALUES from the dev store to the live store.

Scope is deliberately narrower than the migration document allows. The
document permits updating descriptionHtml as well; measured across all 1,308
matched products the dev copy is 54% shorter than live's (median 963 -> 470
chars, 708,513 characters removed, 95% of products shorter). Live's copy
carries the store's organic rankings and feeds Google Merchant Center on a
store with active ad spend, so descriptions are left alone. This script has
no code path that writes descriptionHtml.

What it writes: product metafields in the `custom` namespace only, via
metafieldsSet. That mutation cannot reach price, SKU, handle, images or
variants — the protection is structural, not a promise. Live currently holds
no custom.* values at all, so every write is additive and overwrites nothing.

Matching is on handle only, never title or ID. A dev product with no live
handle match is reported and skipped; nothing is ever created or deleted.

    python3 scripts/migrate-product-content.py                    # dry run
    python3 scripts/migrate-product-content.py --apply --limit 25 # first batch
    python3 scripts/migrate-product-content.py --apply --start 25 # resume
"""

import argparse
import csv
import json
import ssl
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
NAMESPACE = "custom"

try:
    import certifi
    SSL_CTX = ssl.create_default_context(cafile=certifi.where())
except ImportError:
    SSL_CTX = ssl.create_default_context()


def load_env():
    env = {}
    for line in (REPO / ".env").read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if s and not s.startswith("#") and "=" in s:
            k, v = s.split("=", 1)
            env[k.strip()] = v.strip()
    return env


ENV = load_env()
VER = ENV.get("SHOPIFY_API_VERSION", "2024-10")
LIVE = (ENV["SHOPIFY_STORE_DOMAIN"].replace("https://", "").strip("/"), ENV["SHOPIFY_ADMIN_ACCESS_TOKEN"])
DEV = (ENV["DEV_SHOPIFY_STORE_DOMAIN"], ENV["DEV_SHOPIFY_ADMIN_ACCESS_TOKEN"])


def gql(store, query, variables=None):
    dom, tok = store
    body = json.dumps({"query": query, "variables": variables or {}}).encode()
    req = urllib.request.Request(f"https://{dom}/admin/api/{VER}/graphql.json", data=body,
                                 method="POST", headers={"X-Shopify-Access-Token": tok,
                                                         "Content-Type": "application/json"})
    for attempt in range(7):
        try:
            d = json.loads(urllib.request.urlopen(req, timeout=120, context=SSL_CTX).read())
            if d.get("errors"):
                raise RuntimeError(json.dumps(d["errors"])[:300])
            return d["data"]
        except urllib.error.HTTPError as e:
            if e.code == 429 or (500 <= e.code < 600 and attempt < 6):
                time.sleep(2 ** attempt)
                continue
            raise
        except (urllib.error.URLError, TimeoutError, ConnectionError, ssl.SSLError):
            if attempt == 6:
                raise
            time.sleep(2 ** attempt)
    raise RuntimeError("retries exhausted")


PAGE_Q = """query($c:String){ products(first:100, after:$c){
  pageInfo{hasNextPage endCursor}
  nodes{ id handle title
    metafields(first:60, namespace:"%s"){ nodes{ key type value } } } } }""" % NAMESPACE

SET_MF = """mutation($m:[MetafieldsSetInput!]!){ metafieldsSet(metafields:$m){
  userErrors{ field message } } }"""

VERIFY_Q = """query($h:String!){ productByHandle(handle:$h){ handle
  variants(first:30){ nodes{ sku price compareAtPrice } }
  media(first:40){ nodes{ id } }
  metafields(first:60, namespace:"%s"){ nodes{ key } } } }""" % NAMESPACE


def fetch(store):
    out, cur = {}, None
    while True:
        d = gql(store, PAGE_Q, {"c": cur})["products"]
        for n in d["nodes"]:
            out[n["handle"]] = n
        if not d["pageInfo"]["hasNextPage"]:
            break
        cur = d["pageInfo"]["endCursor"]
    return out


def baseline():
    bk = sorted((REPO / "live-backups").glob("nnxpvg-yx-*"))[-1]
    base = {}
    with (bk / "products-immutable-fields.csv").open(encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            base.setdefault(r["handle"], {"variants": [], "image_count": int(r["image_count"])})
            base[r["handle"]]["variants"].append(
                (r["sku"], r["price"], "" if r["compare_at_price"] in ("", "None") else r["compare_at_price"]))
    return bk, base


def spot_check(handles, base):
    """Confirm the fields Phase 4 must never touch are unchanged."""
    bad = []
    for h in handles:
        p = gql(LIVE, VERIFY_Q, {"h": h})["productByHandle"]
        if not p:
            bad.append((h, "product not found")); continue
        now = [(v["sku"] or "", v["price"], v["compareAtPrice"] or "") for v in p["variants"]["nodes"]]
        was = base.get(h, {}).get("variants", [])
        if now != was:
            bad.append((h, f"variant data changed: {was} -> {now}"))
        if len(p["media"]["nodes"]) != base.get(h, {}).get("image_count"):
            bad.append((h, f"image count changed: {base.get(h,{}).get('image_count')} -> {len(p['media']['nodes'])}"))
    return bad


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--batch", type=int, default=25)
    ap.add_argument("--start", type=int, default=0)
    ap.add_argument("--limit", type=int, help="how many products to process this run")
    args = ap.parse_args()

    bk, base = baseline()
    print(f"live     : {LIVE[0]}")
    print(f"dev      : {DEV[0]}")
    print(f"baseline : {bk.name}\n")

    dev, live = fetch(DEV), fetch(LIVE)
    matched = sorted(set(dev) & set(live))
    dev_only = sorted(set(dev) - set(live))
    print(f"dev {len(dev)}   live {len(live)}   matched {len(matched)}   dev-only {len(dev_only)} (skipped, never created)")

    plan = []
    for h in matched:
        want = {m["key"]: m for m in dev[h]["metafields"]["nodes"] if (m["value"] or "").strip()}
        have = {m["key"]: (m["value"] or "") for m in live[h]["metafields"]["nodes"]}
        writes = [{"ownerId": live[h]["id"], "namespace": NAMESPACE, "key": k,
                   "type": m["type"], "value": m["value"]}
                  for k, m in want.items() if have.get(k, "") != m["value"]]
        if writes:
            plan.append({"handle": h, "live_id": live[h]["id"], "writes": writes})

    window = plan[args.start: args.start + args.limit] if args.limit else plan[args.start:]
    print(f"products needing writes : {len(plan)}")
    print(f"this run                : {len(window)}  (start {args.start}, batch size {args.batch})")
    print(f"metafield values        : {sum(len(j['writes']) for j in window):,}\n")
    if window:
        j = window[0]
        print(f"example — {j['handle']}")
        for w in j["writes"][:4]:
            print(f"   {w['key']:<20} {w['type']:<24} {str(w['value'])[:52]!r}")
        print(f"   … {len(j['writes'])} keys total")
    print("\nNEVER WRITTEN: descriptionHtml, handle, price, sku, images, variants")

    if not args.apply:
        print("\n[dry run — nothing written. Re-run with --apply.]")
        return
    if not window:
        print("nothing to do")
        return

    print(f"\nAbout to write custom.* metafields on {len(window)} LIVE products.")
    if input("Type the store domain to confirm: ").strip() != LIVE[0]:
        sys.exit("confirmation did not match — nothing written")

    logf = REPO / "scripts" / "phase4-run-log.jsonl"
    ok = failed = 0
    done_handles = []
    for i in range(0, len(window), args.batch):
        chunk = window[i:i + args.batch]
        print(f"\n--- batch {i//args.batch + 1}: products {args.start+i}..{args.start+i+len(chunk)-1}")
        for j in chunk:
            entry = {"ts": datetime.now(timezone.utc).isoformat(), "handle": j["handle"],
                     "live_id": j["live_id"], "keys": [w["key"] for w in j["writes"]]}
            try:
                for c in [j["writes"][x:x+25] for x in range(0, len(j["writes"]), 25)]:
                    res = gql(LIVE, SET_MF, {"m": c})["metafieldsSet"]
                    if res.get("userErrors"):
                        raise RuntimeError(res["userErrors"][:2])
                ok += 1; entry["status"] = "ok"
                done_handles.append(j["handle"])
            except Exception as e:
                failed += 1; entry["status"] = "FAILED"; entry["error"] = str(e)[:250]
                print(f"    FAIL {j['handle'][:56]}: {str(e)[:120]}")
            with logf.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
            time.sleep(0.25)
        sample = done_handles[-min(8, len(done_handles)):]
        bad = spot_check(sample, base)
        print(f"    written {ok}, failed {failed}")
        print(f"    spot-check {len(sample)} products against the Phase 0 baseline: "
              f"{'ALL CLEAN — price/SKU/images unchanged' if not bad else 'PROBLEM'}")
        for h, why in bad:
            print(f"       {h}: {why}")
        if bad:
            sys.exit("STOPPING — unexpected field change detected")
    print(f"\ndone: {ok} products written, {failed} failed -> {logf.relative_to(REPO)}")


if __name__ == "__main__":
    main()
