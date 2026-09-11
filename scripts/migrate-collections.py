#!/usr/bin/env python3
"""Create the dev store's collections on the live store.

The new theme's navigation and templates reference 94 collection handles; 85
of them did not exist on live, so those pages would have 404'd on publish.

Only collections missing from live are created — existing live collections are
never modified or deleted. Smart collections are recreated from their rules,
which is why the tag and vendor migration had to run first: without it 65 of
these would have been created empty.

frontpage and hydrogen are skipped. They are Shopify defaults, empty on dev,
and frontpage already exists on most stores.

    python3 scripts/migrate-collections.py            # dry run
    python3 scripts/migrate-collections.py --apply    # create
    python3 scripts/migrate-collections.py --verify   # report membership
"""

import argparse
import json
import ssl
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SKIP = {"frontpage", "hydrogen"}

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
    for attempt in range(6):
        try:
            d = json.loads(urllib.request.urlopen(req, timeout=45, context=SSL_CTX).read())
            if d.get("errors"):
                raise RuntimeError(json.dumps(d["errors"])[:300])
            return d["data"]
        except urllib.error.HTTPError as e:
            if e.code == 429 or (500 <= e.code < 600 and attempt < 5):
                time.sleep(min(2 ** attempt, 15)); continue
            raise
        except (urllib.error.URLError, TimeoutError, ConnectionError, ssl.SSLError):
            if attempt == 5:
                raise
            time.sleep(min(2 ** attempt, 15))
    raise RuntimeError("retries exhausted")


LIST_Q = """query($c:String){ collections(first:250, after:$c){
  pageInfo{hasNextPage endCursor}
  nodes{ id handle title descriptionHtml sortOrder templateSuffix
    productsCount{ count }
    seo{ title description }
    ruleSet{ appliedDisjunctively rules{ column relation condition } } } } }"""

CREATE = """mutation($input:CollectionInput!){ collectionCreate(input:$input){
  collection{ id handle title productsCount{count} } userErrors{ field message } } }"""


def fetch(store):
    out, cur = {}, None
    while True:
        d = gql(store, LIST_Q, {"c": cur})["collections"]
        for n in d["nodes"]:
            out[n["handle"]] = n
        if not d["pageInfo"]["hasNextPage"]:
            break
        cur = d["pageInfo"]["endCursor"]
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--verify", action="store_true")
    args = ap.parse_args()

    live, dev = fetch(LIVE), fetch(DEV)
    print(f"live collections {len(live)}   dev collections {len(dev)}")

    if args.verify:
        created = [h for h in dev if h in live]
        thin = [(h, live[h]["productsCount"]["count"]) for h in sorted(created)
                if live[h]["productsCount"]["count"] < 3]
        print(f"\ncollections present on live that dev also has: {len(created)}")
        print(f"  with fewer than 3 products: {len(thin)}")
        for h, c in thin:
            print(f"     {h:<44} {c:>4}  (dev has {dev[h]['productsCount']['count']})")
        return

    todo = [h for h in sorted(set(dev) - set(live)) if h not in SKIP]
    skipped = [h for h in sorted(set(dev) - set(live)) if h in SKIP]
    print(f"\nto create : {len(todo)}")
    print(f"skipped   : {skipped}")
    smart = [h for h in todo if dev[h]["ruleSet"]]
    print(f"  smart (rule-based) : {len(smart)}")
    print(f"  manual             : {len(todo)-len(smart)}")
    for h in todo[:6]:
        d = dev[h]
        rs = d["ruleSet"]
        r = " OR ".join(f"{x['column']}={x['condition']}" for x in rs["rules"]) if rs else "manual"
        print(f"     {h:<40} {r[:48]:<50} suffix={d['templateSuffix']}")
    if len(todo) > 6:
        print(f"     … and {len(todo)-6} more")

    if not args.apply:
        print("\n[dry run — nothing created. Re-run with --apply.]")
        return
    if not todo:
        print("nothing to do"); return

    print(f"\nAbout to CREATE {len(todo)} collections on {LIVE[0]}. Existing collections are untouched.")
    if input("Type the store domain to confirm: ").strip() != LIVE[0]:
        sys.exit("confirmation did not match — nothing created")

    log = REPO / "scripts" / "collections-run-log.jsonl"
    ok = fail = 0
    empties = []
    for n, h in enumerate(todo, 1):
        d = dev[h]
        inp = {"handle": h, "title": d["title"]}
        if d.get("descriptionHtml"):
            inp["descriptionHtml"] = d["descriptionHtml"]
        if d.get("templateSuffix"):
            inp["templateSuffix"] = d["templateSuffix"]
        if d.get("sortOrder"):
            inp["sortOrder"] = d["sortOrder"]
        seo = d.get("seo") or {}
        if seo.get("title") or seo.get("description"):
            inp["seo"] = {"title": seo.get("title") or "", "description": seo.get("description") or ""}
        if d["ruleSet"]:
            inp["ruleSet"] = {"appliedDisjunctively": d["ruleSet"]["appliedDisjunctively"],
                              "rules": [{"column": r["column"], "relation": r["relation"],
                                         "condition": r["condition"]} for r in d["ruleSet"]["rules"]]}
        try:
            res = gql(LIVE, CREATE, {"input": inp})["collectionCreate"]
            if res.get("userErrors"):
                raise RuntimeError(res["userErrors"][:2])
            c = res["collection"]
            cnt = c["productsCount"]["count"]
            ok += 1
            if cnt == 0:
                empties.append(h)
            entry = {"handle": h, "id": c["id"], "products": cnt, "status": "ok"}
        except Exception as e:
            fail += 1
            entry = {"handle": h, "status": "FAILED", "error": str(e)[:220]}
            print(f"  FAIL {h[:50]}: {str(e)[:120]}")
        with log.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
        if n % 20 == 0:
            print(f"  [{n}/{len(todo)}] created {ok}, failed {fail}", flush=True)
        time.sleep(0.3)
    print(f"\ncreated {ok}, failed {fail}")
    print(f"created but EMPTY (0 products): {len(empties)}")
    for h in empties[:20]:
        print(f"   {h}")
    print(f"\nlog -> {log.relative_to(REPO)}")
    print("note: smart-collection membership can take a minute to populate; re-run --verify")


if __name__ == "__main__":
    main()
