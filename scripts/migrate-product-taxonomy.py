#!/usr/bin/env python3
"""Copy product tags and vendor from the dev store to the live store.

Prerequisite for the collection migration. The dev store's collections are
almost all smart collections keyed on TAG or VENDOR; live products carry
neither dev's tags nor, in 201 cases, the same vendor string. Recreating the
collections without this first produces 65 empty collection pages that the
new theme's navigation links straight into.

Tags are added, never removed. Live has its own taxonomy (2,478 tags, 6,323
assignments) that its existing 131 collections depend on, so the two sets are
merged rather than replaced.

Vendor is a single value and cannot be merged. Changing it was chosen
deliberately after the consequence was measured: exactly one existing live
collection shrinks, secret-scents-perfumes, from 37 products to about 5, as
32 products move from "Secret Scents" to "The Fragrance Secrets". Most of the
other changes are casing repairs ("channel" -> "Chanel"). About ten are
cross-brand reassignments and are listed separately in the dry run because
they are only correct if the catalogue sheet is authoritative.

Every before/after is recorded so both can be reversed.

    python3 scripts/migrate-product-taxonomy.py                  # dry run
    python3 scripts/migrate-product-taxonomy.py --apply          # tags + vendor
    python3 scripts/migrate-product-taxonomy.py --apply --tags-only
    python3 scripts/migrate-product-taxonomy.py --rollback FILE
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
            d = json.loads(urllib.request.urlopen(req, timeout=30, context=SSL_CTX).read())
            if d.get("errors"):
                raise RuntimeError(json.dumps(d["errors"])[:300])
            return d["data"]
        except urllib.error.HTTPError as e:
            if e.code == 429 or (500 <= e.code < 600 and attempt < 6):
                time.sleep(min(2 ** attempt, 15)); continue
            raise
        except (urllib.error.URLError, TimeoutError, ConnectionError, ssl.SSLError):
            if attempt == 6:
                raise
            time.sleep(min(2 ** attempt, 15))
    raise RuntimeError("retries exhausted")


PAGE_Q = """query($c:String){ products(first:250, after:$c){
  pageInfo{hasNextPage endCursor} nodes{ id handle vendor tags } } }"""

UPDATE = """mutation($id:ID!,$tags:[String!],$vendor:String){
  productUpdate(input:{id:$id, tags:$tags, vendor:$vendor}){
    product{ id handle vendor tags } userErrors{ field message } } }"""

# tagsAdd is far cheaper than productUpdate and is additive by definition, so
# the full merged array never has to be sent. productUpdate with a 30-element
# tag array was costing enough to stall the run.
UPDATE_TAGS = """mutation($id:ID!,$tags:[String!]!){
  tagsAdd(id:$id, tags:$tags){ node{ id } userErrors{ field message } } }"""


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
    rows = json.loads(Path(path).read_text(encoding="utf-8"))["products"]
    print(f"rollback : {path}\nstore    : {LIVE[0]}\nproducts : {len(rows)}")
    if input("Type the store domain to confirm: ").strip() != LIVE[0]:
        sys.exit("confirmation did not match")
    ok = fail = 0
    for n, r in enumerate(rows, 1):
        try:
            gql(LIVE, UPDATE, {"id": r["live_id"], "tags": r["tags_before"],
                               "vendor": r["vendor_before"]})
            ok += 1
        except Exception as e:
            fail += 1; print(f"  FAIL {r['handle'][:50]}: {str(e)[:100]}")
        if n % 100 == 0: print(f"  [{n}/{len(rows)}] {ok} ok", flush=True)
        time.sleep(0.25)
    print(f"\nrestored {ok}, failed {fail}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--tags-only", action="store_true")
    ap.add_argument("--batch", type=int, default=50)
    ap.add_argument("--limit", type=int)
    ap.add_argument("--rollback", metavar="FILE")
    args = ap.parse_args()
    if args.rollback:
        return do_rollback(args.rollback)

    live, dev = fetch(LIVE), fetch(DEV)
    matched = sorted(set(live) & set(dev))
    plan = []
    for h in matched:
        lt, dt = set(live[h]["tags"]), set(dev[h]["tags"])
        merged = sorted(lt | dt)
        add = sorted(dt - lt)
        lv, dv = (live[h]["vendor"] or "").strip(), (dev[h]["vendor"] or "").strip()
        vchange = (not args.tags_only) and dv and dv != lv
        if not add and not vchange:
            continue
        plan.append({"handle": h, "live_id": live[h]["id"],
                     "tags_before": sorted(lt), "tags_after": merged, "tags_added": add,
                     "vendor_before": lv, "vendor_after": dv if vchange else lv,
                     "vendor_change": bool(vchange)})

    tag_adds = sum(len(p["tags_added"]) for p in plan)
    vch = [p for p in plan if p["vendor_change"]]
    print(f"live {len(live)}   dev {len(dev)}   matched {len(matched)}")
    print(f"products to update : {len(plan)}")
    print(f"tag assignments to ADD (none removed): {tag_adds:,}")
    print(f"vendor changes     : {len(vch)}")
    cross = [p for p in vch
             if p["vendor_before"].lower().replace("'", "").replace("-", " ").replace(" ", "")
             != p["vendor_after"].lower().replace("'", "").replace("-", " ").replace(" ", "")]
    print(f"   of which casing/spacing repairs : {len(vch)-len(cross)}")
    print(f"   of which CROSS-BRAND moves      : {len(cross)}  <- only correct if the sheet is authoritative")
    for p in cross[:14]:
        print(f"      {p['handle'][:44]:<46} {p['vendor_before']!r} -> {p['vendor_after']!r}")

    window = plan[:args.limit] if args.limit else plan
    print(f"\nthis run: {len(window)} products")
    print("NEVER WRITTEN: handle, price, sku, images, variants, title, description, metafields")
    if not args.apply:
        print("\n[dry run — nothing written. Re-run with --apply.]")
        return
    if not window:
        print("nothing to do"); return

    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    backup = REPO / "live-backups" / f"taxonomy-before-{stamp}.json"
    backup.write_text(json.dumps({"store": LIVE[0], "taken_at_utc": stamp, "products": window},
                                 indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"\nbefore/after record: {backup.relative_to(REPO)}")
    print(f"restore: python3 scripts/migrate-product-taxonomy.py --rollback {backup.relative_to(REPO)}")
    print(f"\nAbout to update tags{'' if args.tags_only else ' and vendor'} on {len(window)} LIVE products.")
    if input("Type the store domain to confirm: ").strip() != LIVE[0]:
        sys.exit("confirmation did not match — nothing written")

    logf = REPO / "scripts" / "taxonomy-run-log.jsonl"
    ok = fail = 0
    for i in range(0, len(window), args.batch):
        chunk = window[i:i + args.batch]
        for p in chunk:
            e = {"ts": datetime.now(timezone.utc).isoformat(), "handle": p["handle"],
                 "tags_added": len(p["tags_added"]), "vendor_change": p["vendor_change"]}
            try:
                if p["vendor_change"]:
                    res = gql(LIVE, UPDATE, {"id": p["live_id"], "tags": p["tags_after"],
                                             "vendor": p["vendor_after"]})["productUpdate"]
                else:
                    res = gql(LIVE, UPDATE_TAGS, {"id": p["live_id"],
                                                  "tags": p["tags_added"]})["tagsAdd"]
                if res.get("userErrors"):
                    raise RuntimeError(res["userErrors"][:2])
                if "product" in res and res["product"]["handle"] != p["handle"]:
                    raise RuntimeError("handle moved")
                ok += 1; e["status"] = "ok"
            except Exception as ex:
                fail += 1; e["status"] = "FAILED"; e["error"] = str(ex)[:200]
                print(f"    FAIL {p['handle'][:50]}: {str(ex)[:100]}")
            with logf.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(e, ensure_ascii=False) + "\n")
            time.sleep(0.25)
        print(f"  [{min(i+args.batch,len(window))}/{len(window)}] {ok} ok, {fail} failed", flush=True)
    print(f"\ndone: {ok} updated, {fail} failed -> {logf.relative_to(REPO)}")
    print(f"rollback: {backup.relative_to(REPO)}")


if __name__ == "__main__":
    main()
