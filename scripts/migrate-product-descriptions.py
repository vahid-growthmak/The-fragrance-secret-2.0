#!/usr/bin/env python3
"""Phase 4b — replace live product titles and descriptions with the dev store's.

Separated from the metafield migration on purpose. Metafields are additive:
live held no custom.* values, so nothing was overwritten. Descriptions are
not. Measured across all 1,308 matched products the dev copy is 54% shorter
than live's (median 963 -> 470 characters, 708,513 removed, 95% of products
shorter), and live's copy is what currently carries organic rankings and
feeds Google Merchant Center on a store with active ad spend.

That was flagged and the replacement was chosen deliberately, so this script
exists — but it writes a full before/after record first and can restore it,
because "reversible" has to mean a command, not a promise.

Titles (--titles) are a separate judgement and a clearer win: 156 live titles
carry "Inspired by <brand>", which is the trademark exposure that gets
Merchant Center accounts suspended, and none of the dev titles do. Dev titles
are also longer (median 69 vs 59) because they append the scent family.

Changing a title does NOT change the handle — Shopify only derives a handle at
creation — so product URLs are unaffected. The script asserts this after
every batch rather than assuming it.

    python3 scripts/migrate-product-descriptions.py                 # dry run
    python3 scripts/migrate-product-descriptions.py --apply         # write
    python3 scripts/migrate-product-descriptions.py --rollback FILE # restore

Matching is on handle only. Nothing is created or deleted. The mutation sends
id and descriptionHtml and nothing else — no seo, variants, images or handle,
so those cannot be collaterally rewritten the way an SEOInput would.
"""

import argparse
import json
import ssl
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

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
  nodes{ id handle title descriptionHtml } } }"""

UPDATE = """mutation($id:ID!,$html:String!){
  productUpdate(input:{id:$id, descriptionHtml:$html}){
    product{ id handle } userErrors{ field message } } }"""

UPDATE_BOTH = """mutation($id:ID!,$html:String!,$title:String!){
  productUpdate(input:{id:$id, descriptionHtml:$html, title:$title}){
    product{ id handle title } userErrors{ field message } } }"""

UPDATE_TITLE = """mutation($id:ID!,$title:String!){
  productUpdate(input:{id:$id, title:$title}){
    product{ id handle title } userErrors{ field message } } }"""

CHECK_Q = """query($h:String!){ productByHandle(handle:$h){ handle title descriptionHtml
  seo{ title description }
  variants(first:30){ nodes{ sku price } } media(first:40){ nodes{ id } } } }"""


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


def do_rollback(path):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    rows = data["products"]
    print(f"rollback source : {path}")
    print(f"store           : {LIVE[0]}")
    print(f"products to restore: {len(rows)}")
    print(f"\nAbout to RESTORE {len(rows)} descriptions to their pre-migration text.")
    if input("Type the store domain to confirm: ").strip() != LIVE[0]:
        sys.exit("confirmation did not match — nothing restored")
    ok = fail = 0
    for n, r in enumerate(rows, 1):
        try:
            if r.get("title_change"):
                res = gql(LIVE, UPDATE_BOTH, {"id": r["live_id"], "html": r["before"],
                                              "title": r["title_before"]})["productUpdate"]
            else:
                res = gql(LIVE, UPDATE, {"id": r["live_id"], "html": r["before"]})["productUpdate"]
            if res.get("userErrors"):
                raise RuntimeError(res["userErrors"][:2])
            ok += 1
        except Exception as e:
            fail += 1
            print(f"  FAIL {r['handle'][:56]}: {str(e)[:120]}")
        if n % 50 == 0:
            print(f"  [{n}/{len(rows)}] restored {ok}, failed {fail}", flush=True)
        time.sleep(0.25)
    print(f"\nrestored {ok}, failed {fail}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--batch", type=int, default=25)
    ap.add_argument("--start", type=int, default=0)
    ap.add_argument("--limit", type=int)
    ap.add_argument("--rollback", metavar="FILE")
    ap.add_argument("--titles", action="store_true",
                    help="also replace product titles with the dev store's")
    ap.add_argument("--titles-only", action="store_true",
                    help="replace titles and leave descriptions untouched")
    args = ap.parse_args()

    if args.rollback:
        return do_rollback(args.rollback)

    dev, live = fetch(DEV), fetch(LIVE)
    matched = sorted(set(dev) & set(live))
    do_desc = not args.titles_only
    do_title = args.titles or args.titles_only
    plan = []
    for h in matched:
        d_html, l_html = dev[h]["descriptionHtml"] or "", live[h]["descriptionHtml"] or ""
        d_title, l_title = (dev[h]["title"] or "").strip(), (live[h]["title"] or "").strip()
        desc_change = do_desc and d_html.strip() and d_html != l_html
        title_change = do_title and d_title and d_title != l_title
        if not desc_change and not title_change:
            continue
        plan.append({"handle": h, "live_id": live[h]["id"],
                     "before": l_html, "after": d_html if desc_change else l_html,
                     "title_before": l_title, "title_after": d_title if title_change else l_title,
                     "desc_change": bool(desc_change), "title_change": bool(title_change)})

    strip = lambda s: len(s)
    before_chars = sum(strip(p["before"]) for p in plan)
    after_chars = sum(strip(p["after"]) for p in plan)
    print(f"live {len(live)}   dev {len(dev)}   matched {len(matched)}")
    print(f"descriptions to replace : {len(plan)}")
    print(f"characters before       : {before_chars:,}")
    print(f"characters after        : {after_chars:,}   ({after_chars-before_chars:+,})")
    empty = [p for p in plan if not p["after"].strip()]
    print(f"dev descriptions empty  : {len(empty)}  (skipped — never blank a live description)")
    print(f"descriptions changing   : {sum(1 for p in plan if p['desc_change'])}")
    print(f"titles changing         : {sum(1 for p in plan if p['title_change'])}")

    window = plan[args.start: args.start + args.limit] if args.limit else plan[args.start:]
    print(f"this run                : {len(window)}\n")
    if window:
        p = window[0]
        print(f"example — {p['handle']}")
        if p["title_change"]:
            print(f"   title before: {p['title_before'][:96]!r}")
            print(f"   title after : {p['title_after'][:96]!r}")
        if p["desc_change"]:
            print(f"   desc before ({len(p['before'])} chars): {p['before'][:100]!r}")
            print(f"   desc after  ({len(p['after'])} chars): {p['after'][:100]!r}")
    print("\nNEVER WRITTEN: handle, price, sku, images, variants, seo title/description, metafields")

    if not args.apply:
        print("\n[dry run — nothing written. Re-run with --apply.]")
        return
    if not window:
        print("nothing to do")
        return

    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    backup = REPO / "live-backups" / f"descriptions-before-{stamp}.json"
    backup.parent.mkdir(parents=True, exist_ok=True)
    backup.write_text(json.dumps({"store": LIVE[0], "taken_at_utc": stamp,
                                  "products": window}, indent=1, ensure_ascii=False),
                      encoding="utf-8")
    print(f"\nbefore/after record written: {backup.relative_to(REPO)}  ({backup.stat().st_size/1024:.0f} KB)")
    print(f"restore with: python3 scripts/migrate-product-descriptions.py --rollback {backup.relative_to(REPO)}")

    print(f"\nAbout to REPLACE descriptions on {len(window)} LIVE products.")
    if input("Type the store domain to confirm: ").strip() != LIVE[0]:
        sys.exit("confirmation did not match — nothing written")

    logf = REPO / "scripts" / "phase4b-descriptions-log.jsonl"
    ok = fail = 0
    done = []
    for i in range(0, len(window), args.batch):
        chunk = window[i:i + args.batch]
        print(f"\n--- batch {i//args.batch + 1}: {args.start+i}..{args.start+i+len(chunk)-1}")
        for p in chunk:
            entry = {"ts": datetime.now(timezone.utc).isoformat(), "handle": p["handle"],
                     "live_id": p["live_id"], "before_len": len(p["before"]),
                     "after_len": len(p["after"])}
            entry["desc_change"] = p["desc_change"]; entry["title_change"] = p["title_change"]
            try:
                if p["desc_change"] and p["title_change"]:
                    q, v = UPDATE_BOTH, {"id": p["live_id"], "html": p["after"], "title": p["title_after"]}
                elif p["title_change"]:
                    q, v = UPDATE_TITLE, {"id": p["live_id"], "title": p["title_after"]}
                else:
                    q, v = UPDATE, {"id": p["live_id"], "html": p["after"]}
                res = gql(LIVE, q, v)["productUpdate"]
                if res.get("userErrors"):
                    raise RuntimeError(res["userErrors"][:2])
                if res["product"]["handle"] != p["handle"]:
                    raise RuntimeError(f"HANDLE MOVED {p['handle']} -> {res['product']['handle']}")
                ok += 1; entry["status"] = "ok"; done.append(p)
            except Exception as e:
                fail += 1; entry["status"] = "FAILED"; entry["error"] = str(e)[:250]
                print(f"    FAIL {p['handle'][:56]}: {str(e)[:110]}")
            with logf.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
            time.sleep(0.25)
        bad = []
        for p in done[-min(6, len(done)):]:
            c = gql(LIVE, CHECK_Q, {"h": p["handle"]})["productByHandle"]
            if c is None:
                bad.append((p["handle"], "HANDLE NO LONGER RESOLVES")); continue
            if p["desc_change"] and (c["descriptionHtml"] or "") != p["after"]:
                bad.append((p["handle"], "description did not take"))
            if p["title_change"] and (c["title"] or "").strip() != p["title_after"]:
                bad.append((p["handle"], "title did not take"))
        print(f"    written {ok}, failed {fail}")
        print(f"    spot-check: {'descriptions applied correctly' if not bad else bad}")
        if bad:
            sys.exit("STOPPING — verification failed")
    print(f"\ndone: {ok} replaced, {fail} failed -> {logf.relative_to(REPO)}")
    print(f"rollback available: {backup.relative_to(REPO)}")


if __name__ == "__main__":
    main()
