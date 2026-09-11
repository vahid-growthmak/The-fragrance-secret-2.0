#!/usr/bin/env python3
"""Phase 0 — complete read-only backup of the live store.

Writes a timestamped directory under live-backups/. Read-only: this script
issues no mutation and no POST other than GraphQL queries.

Covers the Phase 0 checklist: theme code, products with metafields,
metafield definitions, policies, navigation menus, redirects, collections
with their rules, orders, customers, and installed apps.

    python3 scripts/backup-live-store.py
"""

import json
import os
import re
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
    dom = env["SHOPIFY_STORE_DOMAIN"].replace("https://", "").replace("http://", "").strip("/")
    return dom, env["SHOPIFY_ADMIN_ACCESS_TOKEN"], env.get("SHOPIFY_API_VERSION", "2024-10")


DOM, TOK, VER = load_env()


def rest(path):
    url = path if path.startswith("http") else f"https://{DOM}/admin/api/{VER}/{path}"
    req = urllib.request.Request(url, headers={"X-Shopify-Access-Token": TOK,
                                               "Accept": "application/json"})
    for attempt in range(6):
        try:
            r = urllib.request.urlopen(req, timeout=90, context=SSL_CTX)
            return json.loads(r.read()), r.headers
        except urllib.error.HTTPError as e:
            if e.code == 429:
                time.sleep(float(e.headers.get("Retry-After", 2)))
                continue
            if 500 <= e.code < 600 and attempt < 5:
                time.sleep(2 ** attempt)
                continue
            raise
        except (urllib.error.URLError, TimeoutError, ConnectionError, ssl.SSLError):
            if attempt == 5:
                raise
            time.sleep(2 ** attempt)
    raise RuntimeError(path)


def rest_all(path, key):
    """Follow Link-header pagination."""
    out, url = [], f"https://{DOM}/admin/api/{VER}/{path}"
    while url:
        body, headers = rest(url)
        out += body.get(key, [])
        m = re.search(r'<([^>]+)>;\s*rel="next"', headers.get("Link", ""))
        url = m.group(1) if m else None
    return out


def gql(query, variables=None):
    body = json.dumps({"query": query, "variables": variables or {}}).encode()
    req = urllib.request.Request(f"https://{DOM}/admin/api/{VER}/graphql.json", data=body,
                                 method="POST", headers={"X-Shopify-Access-Token": TOK,
                                                         "Content-Type": "application/json"})
    for attempt in range(6):
        try:
            d = json.loads(urllib.request.urlopen(req, timeout=120, context=SSL_CTX).read())
            if d.get("errors"):
                raise RuntimeError(json.dumps(d["errors"])[:300])
            return d["data"]
        except urllib.error.HTTPError as e:
            if e.code == 429 or (500 <= e.code < 600 and attempt < 5):
                time.sleep(2 ** attempt)
                continue
            raise
        except (urllib.error.URLError, TimeoutError, ConnectionError, ssl.SSLError):
            if attempt == 5:
                raise
            time.sleep(2 ** attempt)
    raise RuntimeError("gql retries exhausted")


def main():
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    out = REPO / "live-backups" / f"{DOM.split('.')[0]}-{stamp}"
    out.mkdir(parents=True, exist_ok=True)
    manifest = {"store": DOM, "taken_at_utc": stamp, "api_version": VER, "items": {}}

    def save(name, obj, note=""):
        p = out / name
        p.write_text(json.dumps(obj, indent=1, ensure_ascii=False), encoding="utf-8")
        n = len(obj) if isinstance(obj, list) else 1
        manifest["items"][name] = {"records": n, "bytes": p.stat().st_size, "note": note}
        print(f"  saved {name:<34} {n:>6} records  {p.stat().st_size/1024:>8.0f} KB {note}")

    print(f"Phase 0 backup of {DOM}\n  -> {out.relative_to(REPO)}\n")

    shop, _ = rest("shop.json")
    save("shop.json", shop["shop"])

    themes, _ = rest("themes.json")
    save("themes.json", themes["themes"])
    pub = [t for t in themes["themes"] if t["role"] == "main"][0]
    print(f"  published theme: {pub['name']!r} (id {pub['id']}) — pulling code…")
    assets, _ = rest(f"themes/{pub['id']}/assets.json")
    code_dir = out / "theme-published"
    got = fail = 0
    index = []
    for a in assets["assets"]:
        key = a["key"]
        try:
            body, _ = rest(f"themes/{pub['id']}/assets.json?asset[key]={urllib.parse.quote(key)}")
            asset = body["asset"]
            dest = code_dir / key
            dest.parent.mkdir(parents=True, exist_ok=True)
            if asset.get("value") is not None:
                dest.write_text(asset["value"], encoding="utf-8")
            elif asset.get("public_url"):
                index.append({"key": key, "public_url": asset["public_url"], "size": a.get("size")})
                dest.with_suffix(dest.suffix + ".url").write_text(asset["public_url"], encoding="utf-8")
            got += 1
        except Exception as e:
            fail += 1
            index.append({"key": key, "error": str(e)[:120]})
        time.sleep(0.12)
    save("theme-asset-index.json", index, f"(binary assets referenced by URL)")
    print(f"  theme code: {got} assets written, {fail} failed -> theme-published/")
    manifest["items"]["theme-published/"] = {"records": got, "failed": fail,
                                             "theme_id": pub["id"], "theme_name": pub["name"]}

    print("  pulling products with metafields (this is the slow part)…")
    Q = """query($c:String){ products(first:50, after:$c){
      pageInfo{hasNextPage endCursor}
      nodes{ id handle title status vendor productType tags templateSuffix
        descriptionHtml createdAt updatedAt publishedAt
        seo{ title description }
        featuredMedia{ ... on MediaImage{ id image{ url } } }
        media(first:30){ nodes{ ... on MediaImage{ id alt image{ url width height } } } }
        metafields(first:60){ nodes{ namespace key type value } }
        variants(first:50){ nodes{ id sku title price compareAtPrice barcode
          inventoryQuantity position selectedOptions{ name value } } } } } }"""
    prods, cur = [], None
    while True:
        page = gql(Q, {"c": cur})["products"]
        prods += page["nodes"]
        if len(prods) % 250 < 50:
            print(f"     {len(prods)}…", flush=True)
        if not page["pageInfo"]["hasNextPage"]:
            break
        cur = page["pageInfo"]["endCursor"]
    save("products.json", prods)

    # flat CSV of the fields this migration must never touch, for fast diffing
    import csv
    csv_path = out / "products-immutable-fields.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["handle", "product_id", "title", "status", "variant_id", "sku",
                    "price", "compare_at_price", "barcode", "image_count", "featured_image"])
        for p in prods:
            imgs = p["media"]["nodes"]
            fi = ((p.get("featuredMedia") or {}).get("image") or {}).get("url", "")
            for v in p["variants"]["nodes"]:
                w.writerow([p["handle"], p["id"], p["title"], p["status"], v["id"], v["sku"],
                            v["price"], v["compareAtPrice"], v["barcode"], len(imgs), fi])
    manifest["items"]["products-immutable-fields.csv"] = {
        "bytes": csv_path.stat().st_size, "note": "handle/sku/price/image baseline for verification"}
    print(f"  saved products-immutable-fields.csv  {csv_path.stat().st_size/1024:.0f} KB")

    defs, cur = [], None
    for owner in ["PRODUCT", "PRODUCTVARIANT", "COLLECTION", "SHOP", "PAGE", "CUSTOMER", "ORDER"]:
        cur = None
        while True:
            d = gql("""query($o:MetafieldOwnerType!,$c:String){
              metafieldDefinitions(first:100, ownerType:$o, after:$c){
                pageInfo{hasNextPage endCursor}
                nodes{ id name namespace key type{ name } description ownerType
                  validations{ name value } } } }""", {"o": owner, "c": cur})["metafieldDefinitions"]
            for n in d["nodes"]:
                n["ownerType"] = owner
            defs += d["nodes"]
            if not d["pageInfo"]["hasNextPage"]:
                break
            cur = d["pageInfo"]["endCursor"]
    save("metafield-definitions.json", defs)

    pol, _ = rest("policies.json")
    save("policies.json", pol["policies"])

    menus, cur = [], None
    while True:
        d = gql("""query($c:String){ menus(first:50, after:$c){
          pageInfo{hasNextPage endCursor}
          nodes{ id handle title
            items{ id title type url tags resourceId
              items{ id title type url resourceId
                items{ id title type url resourceId } } } } } }""", {"c": cur})["menus"]
        menus += d["nodes"]
        if not d["pageInfo"]["hasNextPage"]:
            break
        cur = d["pageInfo"]["endCursor"]
    save("navigation-menus.json", menus)

    save("redirects.json", rest_all("redirects.json?limit=250", "redirects"))
    save("smart-collections.json", rest_all("smart_collections.json?limit=250", "smart_collections"))
    save("custom-collections.json", rest_all("custom_collections.json?limit=250", "custom_collections"))
    save("pages.json", rest_all("pages.json?limit=250", "pages"))

    for label, path, key in [("orders", "orders.json?limit=250&status=any", "orders"),
                             ("customers", "customers.json?limit=250", "customers")]:
        try:
            save(f"{label}.json", rest_all(path, key))
        except urllib.error.HTTPError as e:
            manifest["items"][f"{label}.json"] = {"error": f"HTTP {e.code}"}
            print(f"  SKIPPED {label}: HTTP {e.code}")

    apps = gql("""{ appInstallations(first:100){ nodes{
      app{ title } accessScopes{ handle } launchUrl } } }""")["appInstallations"]["nodes"]
    save("installed-apps.json", apps)
    try:
        save("script-tags.json", rest_all("script_tags.json?limit=250", "script_tags"))
    except urllib.error.HTTPError as e:
        manifest["items"]["script-tags.json"] = {"error": f"HTTP {e.code} — read_script_tags not granted"}
        print(f"  SKIPPED script tags: HTTP {e.code} (scope not granted)")

    (out / "MANIFEST.json").write_text(json.dumps(manifest, indent=1), encoding="utf-8")
    total = sum(f.stat().st_size for f in out.rglob("*") if f.is_file())
    print(f"\nbackup complete: {out.relative_to(REPO)}  ({total/1024/1024:.1f} MB)")


if __name__ == "__main__":
    import urllib.parse
    main()
