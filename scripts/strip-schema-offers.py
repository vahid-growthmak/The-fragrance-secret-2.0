#!/usr/bin/env python3
"""Remove the frozen offers block from custom.product_schema.

The stored Product node came from the catalogue sheet, so its price and
availability are a snapshot taken at export time. Measured against live data
that snapshot had drifted badly: 249 products declared InStock while actually
sold out (some with negative inventory) and 3 carried a stale price. Google
cross-checks structured data against the landing page, so that is a Merchant
Center disapproval risk on a store running ads — and re-importing only resets
the clock, because the next sale or restock reintroduces it.

So offers is removed from the stored copy entirely and product-schema.liquid
appends one built from live product data on every render. The sheet keeps
what it is good at — curated description, brand, category, audience, images —
and the volatile fields come from the store, which is always right.

aggregateRating is stripped for the same reason: it depends on live review
counts, which a snapshot cannot track.

    python3 scripts/strip-schema-offers.py            # dry run
    python3 scripts/strip-schema-offers.py --apply    # write
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
DROP = ("offers", "aggregateRating")

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
DOM = ENV["SHOPIFY_STORE_DOMAIN"].replace("https://", "").strip("/")
TOK = ENV["SHOPIFY_ADMIN_ACCESS_TOKEN"]


def gql(query, variables=None):
    body = json.dumps({"query": query, "variables": variables or {}}).encode()
    req = urllib.request.Request(f"https://{DOM}/admin/api/{VER}/graphql.json", data=body,
                                 method="POST", headers={"X-Shopify-Access-Token": TOK,
                                                         "Content-Type": "application/json"})
    for attempt in range(7):
        try:
            d = json.loads(urllib.request.urlopen(req, timeout=45, context=SSL_CTX).read())
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


PAGE_Q = """query($c:String){ products(first:100, after:$c){
  pageInfo{hasNextPage endCursor}
  nodes{ id handle metafields(first:60, namespace:"custom"){ nodes{ key value } } } } }"""

SET_MF = """mutation($m:[MetafieldsSetInput!]!){ metafieldsSet(metafields:$m){
  userErrors{ field message } } }"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    prods, cur = [], None
    while True:
        d = gql(PAGE_Q, {"c": cur})["products"]
        prods += d["nodes"]
        if not d["pageInfo"]["hasNextPage"]:
            break
        cur = d["pageInfo"]["endCursor"]

    plan, bad, already = [], [], 0
    for p in prods:
        mf = {m["key"]: m["value"] for m in p["metafields"]["nodes"]}
        raw = (mf.get("product_schema") or "").strip()
        if not raw:
            continue
        try:
            obj = json.loads(raw)
        except Exception as e:
            bad.append((p["handle"], str(e)[:70])); continue
        if not any(k in obj for k in DROP):
            already += 1; continue
        dropped = [k for k in DROP if k in obj]
        for k in DROP:
            obj.pop(k, None)
        new = json.dumps(obj, ensure_ascii=False, separators=(",", ":"))
        if not new.endswith("}"):
            bad.append((p["handle"], "does not end with }")); continue
        plan.append({"id": p["id"], "handle": p["handle"], "new": new, "dropped": dropped})

    print(f"store   : {DOM}")
    print(f"products with a stored schema : {sum(1 for p in prods if (dict((m['key'],m['value']) for m in p['metafields']['nodes']).get('product_schema') or '').strip())}")
    print(f"  to rewrite (offers stripped): {len(plan)}")
    print(f"  already stripped            : {already}")
    print(f"  unparseable / unsafe        : {len(bad)}")
    for h, e in bad[:8]:
        print(f"     {h[:52]}: {e}")
    if plan:
        s = plan[0]
        print(f"\nexample — {s['handle']}  (dropped {s['dropped']})")
        print(f"   now ends: …{s['new'][-120:]}")

    if not args.apply:
        print("\n[dry run — nothing written. Re-run with --apply.]")
        return
    if not plan:
        print("nothing to do"); return

    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    bk = REPO / "live-backups" / f"product-schema-before-strip-{stamp}.json"
    orig = {}
    for p in prods:
        mf = {m["key"]: m["value"] for m in p["metafields"]["nodes"]}
        if (mf.get("product_schema") or "").strip():
            orig[p["handle"]] = mf["product_schema"]
    bk.write_text(json.dumps({"store": DOM, "taken_at_utc": stamp, "schemas": orig},
                             indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"\nbackup of the original schemas: {bk.relative_to(REPO)} ({bk.stat().st_size/1024/1024:.1f} MB)")

    print(f"\nAbout to rewrite custom.product_schema on {len(plan)} LIVE products.")
    if input("Type the store domain to confirm: ").strip() != DOM:
        sys.exit("confirmation did not match — nothing written")

    ok = fail = 0
    for n, j in enumerate(plan, 1):
        try:
            res = gql(SET_MF, {"m": [{"ownerId": j["id"], "namespace": "custom",
                                      "key": "product_schema",
                                      "type": "multi_line_text_field",
                                      "value": j["new"]}]})["metafieldsSet"]
            if res.get("userErrors"):
                raise RuntimeError(res["userErrors"][:2])
            ok += 1
        except Exception as e:
            fail += 1
            print(f"   FAIL {j['handle'][:50]}: {str(e)[:110]}")
        if n % 100 == 0:
            print(f"   [{n}/{len(plan)}] {ok} rewritten", flush=True)
        time.sleep(0.2)
    print(f"\nrewritten {ok}, failed {fail}")
    print(f"rollback: the original schemas are in {bk.relative_to(REPO)}")


if __name__ == "__main__":
    main()
