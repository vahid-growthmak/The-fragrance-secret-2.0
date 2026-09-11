#!/usr/bin/env python3
"""Retire the old live-store collections that the new catalogue does not use.

"Old" means present on the live store but absent from the dev store, which is
the new theme's collection set. There were 122; `afnan` is excluded because it
was created during the migration and the new theme links to it.

They are the previous store's indexed category pages, and 110 existing
redirects point at them, so they are not simply deleted. In order:

  1. BACKUP   every collection's settings, rules and product membership. The
              Phase 0 export held settings only, and 75 of these are manual,
              so their curation existed nowhere else.
  2. REDIRECT a 301 from each old URL to its new equivalent, or to
              /collections/all where there is none. Created before the delete
              so there is no window in which the URL 404s.
  3. REPOINT  the redirects that already target an old collection, straight
              to the new target, so no request goes through two hops.
  4. DELETE   the collections. Products are never touched.

The storefront menu is unaffected: the new theme builds its own header and
footer and does not render the Shopify main-menu that links to these.

    python3 scripts/retire-live-collections.py            # dry run
    python3 scripts/retire-live-collections.py --apply    # all four phases
"""

import argparse
import json
import re
import ssl
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
KEEP = {"afnan", "bath-body-works"}

# Replacement homes created in phase 0 if absent. Bath & Body Works has 87
# live products and its only collection is one of the old ones being retired,
# so without this the brand would be left with no collection page at all.
CREATE_FIRST = {
    "bath-body-works": {"title": "Bath & Body Works",
                        "rules": [{"column": "VENDOR", "relation": "EQUALS",
                                   "condition": "Bath & Body Works"}]},
}

# Where a straight rename rule cannot find the new collection.
MANUAL_MAP = {
    "mens-collection": "mens", "perfume-for-womens-collection": "womens",
    "unisex-collection": "unisex", "kids-perfume": "kids",
    "perfume-oil-collection": "perfume-oil", "inspired-perfumes": "inspired",
    "premium-attar-perfume-collection-fragrance-perfume-perfume-and-attar": "attar",
    "paris-collections": "paris-collection", "best-selling": "best-sellers",
    "fragrance-secrets-perfumes": "fragrance-secrets", "best-rasasi-perfumes": "rasasi",
    "fragrance-in-sabrina-carpenters-sweet-tooth-range": "sabrina-carpenter",
    "best-perfumes-under-100-aed": "crazy-deals", "best-perfumes-under-50-aed": "crazy-deals",
    "perfumes-below-30": "crazy-deals",
    "channel": "chanel", "super-sale": "crazy-deals", "gift-hampers": "gift-sets",
    "afnan-perfumes": "afnan", "farzanas-collection-perfumes": "farzanas-collection",
    "raees-roll-on": "attar", "attar-roll-on-set": "attar",
}

# Old handles are long SEO slugs, so these match on their opening words.
PREFIX_MAP = [
    ("bath-body-works-collection", "bath-body-works"),
    ("elevate-your-scent-game-with-afnan", "afnan"),
    ("men-s-perfumes-collection", "mens"),
    ("women-s-perfumes-collection", "womens"),
    ("oud-perfumes-collection", "oud-woody"),
    ("amber-perfumes-collection", "amber-woody"),
    ("eid-sale-perfumes", "crazy-deals"),
    ("fragrance-secrets-single-note-perfume-oils", "perfume-oil"),
    ("shazine-attar-roll-on-collection", "attar"),
    ("valentine-s-day-exclusive-perfume-bundles", "gift-sets"),
]

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


def call(store, method, path, payload=None, gql=False):
    dom, tok = store
    url = path if path.startswith("http") else f"https://{dom}/admin/api/{VER}/{path}"
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(url, data=data, method=method, headers={
        "X-Shopify-Access-Token": tok, "Content-Type": "application/json",
        "Accept": "application/json"})
    for attempt in range(7):
        try:
            r = urllib.request.urlopen(req, timeout=45, context=SSL_CTX)
            body = r.read()
            out = json.loads(body) if body.strip() else {}
            if gql and out.get("errors"):
                raise RuntimeError(json.dumps(out["errors"])[:300])
            return out, r.headers
        except urllib.error.HTTPError as e:
            if e.code == 429 or (500 <= e.code < 600 and attempt < 6):
                time.sleep(min(2 ** attempt, 15)); continue
            raise
        except (urllib.error.URLError, TimeoutError, ConnectionError, ssl.SSLError):
            if attempt == 6:
                raise
            time.sleep(min(2 ** attempt, 15))
    raise RuntimeError("retries exhausted")


def gql(store, query, variables=None):
    return call(store, "POST", "graphql.json", {"query": query, "variables": variables or {}}, gql=True)[0]["data"]


def all_collections(store):
    out, cur = {}, None
    while True:
        d = gql(store, """query($c:String){ collections(first:250, after:$c){
          pageInfo{hasNextPage endCursor}
          nodes{ id handle title descriptionHtml sortOrder templateSuffix updatedAt
            productsCount{count} seo{title description} image{url altText}
            ruleSet{appliedDisjunctively rules{column relation condition}} } } }""", {"c": cur})["collections"]
        for n in d["nodes"]:
            out[n["handle"]] = n
        if not d["pageInfo"]["hasNextPage"]:
            break
        cur = d["pageInfo"]["endCursor"]
    return out


def members(cid):
    out, cur = [], None
    while True:
        d = gql(LIVE, """query($id:ID!,$c:String){ collection(id:$id){
          products(first:250, after:$c){ pageInfo{hasNextPage endCursor}
            nodes{ id handle } } } }""", {"id": cid, "c": cur})["collection"]["products"]
        out += d["nodes"]
        if not d["pageInfo"]["hasNextPage"]:
            break
        cur = d["pageInfo"]["endCursor"]
    return out


def target_for(handle, new_set):
    if handle in MANUAL_MAP and MANUAL_MAP[handle] in new_set:
        return MANUAL_MAP[handle], "mapped"
    for prefix, tgt in PREFIX_MAP:
        if handle.startswith(prefix) and tgt in new_set:
            return tgt, "mapped"
    base = re.sub(r"-(perfumes?|collection|fragrances?).*$", "", handle)
    base = re.sub(r"^best-", "", base)
    for c in (base, base + "-perfumes", base.replace("-and-", "-")):
        if c in new_set:
            return c, "renamed"
    return None, "none"


def all_redirects():
    out, url = [], f"https://{LIVE[0]}/admin/api/{VER}/redirects.json?limit=250"
    while url:
        body, headers = call(LIVE, "GET", url)
        out += body.get("redirects", [])
        m = re.search(r'<([^>]+)>;\s*rel="next"', headers.get("Link", ""))
        url = m.group(1) if m else None
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    live, dev = all_collections(LIVE), all_collections(DEV)
    old = sorted((set(live) - set(dev)) - KEEP)
    # a redirect may point at anything that survives: the dev set, the kept
    # ones, and the replacement homes created in phase 0
    new_set = (set(live) | set(CREATE_FIRST)) - set(old)
    plan = {}
    for h in old:
        t, how = target_for(h, new_set)
        plan[h] = {"target": f"/collections/{t}" if t else "/collections/all", "how": how}

    reds = all_redirects()
    by_path = {r["path"]: r for r in reds}
    repoint = []
    for r in reds:
        m = re.match(r"^/collections/([a-z0-9-]+)/?$", r["target"])
        if m and m.group(1) in plan:
            repoint.append((r, plan[m.group(1)]["target"]))

    print(f"store: {LIVE[0]}")
    for h in CREATE_FIRST:
        print(f"phase 0 will {'create' if h not in live else 'reuse existing'} /collections/{h}")
    print(f"live {len(live)}   dev {len(dev)}   old to retire {len(old)}   kept: {sorted(KEEP)}")
    print(f"  with a new equivalent : {sum(1 for p in plan.values() if p['how']!='none')}")
    print(f"  -> /collections/all   : {sum(1 for p in plan.values() if p['how']=='none')}")
    print(f"  existing redirects to repoint: {len(repoint)}")
    print(f"  product memberships affected : {sum(live[h]['productsCount']['count'] for h in old)}  (products are NOT deleted)\n")
    print("  every mapping that is not a straight rename, for review:")
    for h in old:
        if plan[h]["how"] == "mapped":
            print(f"     {h[:52]:<54} -> {plan[h]['target']}")

    if not args.apply:
        out = REPO / "scripts" / "retire-collections-plan.json"
        out.write_text(json.dumps(plan, indent=1), encoding="utf-8")
        print(f"\nfull plan -> {out.relative_to(REPO)}")
        print("[dry run — nothing changed. Re-run with --apply.]")
        return

    print(f"\nAbout to retire {len(old)} collections on {LIVE[0]} (backup, redirect, repoint, delete).")
    if input("Type the store domain to confirm: ").strip() != LIVE[0]:
        sys.exit("confirmation did not match — nothing changed")

    # 0 REPLACEMENT HOMES
    for h, spec in CREATE_FIRST.items():
        if h in live:
            print(f"0 HOME     /collections/{h} already exists")
            continue
        res = gql(LIVE, """mutation($i:CollectionInput!){ collectionCreate(input:$i){
          collection{ id handle } userErrors{field message} } }""",
          {"i": {"handle": h, "title": spec["title"],
                 "ruleSet": {"appliedDisjunctively": False, "rules": spec["rules"]}}})["collectionCreate"]
        if res.get("userErrors"):
            sys.exit(f"could not create {h}: {res['userErrors']} — stopping before anything is deleted")
        cid = res["collection"]["id"].split("/")[-1]
        # collectionCreate does not publish to the Online Store; without this it 404s
        call(LIVE, "PUT", f"smart_collections/{cid}.json",
             {"smart_collection": {"id": int(cid), "published": True}})
        print(f"0 HOME     created and published /collections/{h}")

    # 1 BACKUP
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    bk = []
    for n, h in enumerate(old, 1):
        c = dict(live[h])
        c["members"] = members(c["id"])
        bk.append(c)
        if n % 20 == 0:
            print(f"  backup {n}/{len(old)}", flush=True)
    bfile = REPO / "live-backups" / f"retired-collections-{stamp}.json"
    bfile.write_text(json.dumps({"store": LIVE[0], "taken_at_utc": stamp, "collections": bk},
                                indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"1 BACKUP   {len(bk)} collections, {sum(len(c['members']) for c in bk)} memberships -> {bfile.relative_to(REPO)}")

    log = []
    # 2 REDIRECT
    made = upd = fail = 0
    for h in old:
        path, tgt = f"/collections/{h}", plan[h]["target"]
        try:
            if path in by_path:
                rid = by_path[path]["id"]
                call(LIVE, "PUT", f"redirects/{rid}.json", {"redirect": {"id": rid, "target": tgt}})
                upd += 1
            else:
                call(LIVE, "POST", "redirects.json", {"redirect": {"path": path, "target": tgt}})
                made += 1
            log.append({"step": "redirect", "path": path, "target": tgt, "ok": True})
        except urllib.error.HTTPError as e:
            fail += 1
            log.append({"step": "redirect", "path": path, "target": tgt, "ok": False,
                        "error": f"{e.code} {e.read().decode()[:160]}"})
        time.sleep(0.25)
    print(f"2 REDIRECT created {made}, updated {upd}, failed {fail}")

    # 3 REPOINT
    rp = rfail = 0
    for r, tgt in repoint:
        try:
            call(LIVE, "PUT", f"redirects/{r['id']}.json", {"redirect": {"id": r["id"], "target": tgt}})
            rp += 1
            log.append({"step": "repoint", "path": r["path"], "from": r["target"], "to": tgt, "ok": True})
        except urllib.error.HTTPError as e:
            rfail += 1
            log.append({"step": "repoint", "path": r["path"], "ok": False, "error": f"{e.code}"})
        time.sleep(0.25)
    print(f"3 REPOINT  {rp} redirects repointed, {rfail} failed")

    # 4 DELETE
    dl = dfail = 0
    for h in old:
        try:
            res = gql(LIVE, """mutation($id:ID!){ collectionDelete(input:{id:$id}){
              deletedCollectionId userErrors{field message} } }""", {"id": live[h]["id"]})["collectionDelete"]
            if res.get("userErrors"):
                raise RuntimeError(res["userErrors"][:2])
            dl += 1
            log.append({"step": "delete", "handle": h, "ok": True})
        except Exception as e:
            dfail += 1
            log.append({"step": "delete", "handle": h, "ok": False, "error": str(e)[:160]})
        time.sleep(0.25)
    print(f"4 DELETE   {dl} deleted, {dfail} failed")

    lf = REPO / "scripts" / "retire-collections-run-log.json"
    lf.write_text(json.dumps(log, indent=1), encoding="utf-8")
    print(f"\nlog -> {lf.relative_to(REPO)}")
    print(f"rollback data -> {bfile.relative_to(REPO)}")


if __name__ == "__main__":
    main()
