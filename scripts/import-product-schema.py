#!/usr/bin/env python3
"""Import the sheet's Product JSON-LD into custom.product_schema.

The theme has been building Product structured data from live product data.
That was the right call while the store was on USD and the stored copy
hardcoded AED — but the live store runs in AED, so that objection goes away on
launch, and the stored schema is the one the SEO work was written against.

Three repairs are applied on the way in, because the stored copy cannot be
emitted verbatim without producing invalid rich results:

  1. offers.price is null or absent on 1,015 of the 1,308 rows. 996 are filled
     from the sheet's own price column. The remaining 19 have no price
     anywhere, so their offers block is dropped entirely — Google rejects an
     Offer without a price, and no offer is better than a broken one.

  2. sku and gtin are added where the sheet has them (66 and 3 rows). The
     stored schema omits both; the theme's live builder emitted them, so
     without this the switch would lose data.

  3. @id is added, derived from the offers URL, so the Product node can be
     referenced and does not collide with other nodes on the page.

Known loss, accepted deliberately: aggregateRating. The theme's live builder
emits it from Judge.me review data when a product has reviews; a static schema
cannot. Re-add it once reviews exist on the live store — it needs merging live
data into the stored JSON, which is a render-time job, not an import one.

Everything else in the stored schema is passed through untouched, including
the thefragrancesecrets.com URLs and image CDN paths, which are correct for
the live store this is destined for.

    python3 scripts/import-product-schema.py            # dry run
    python3 scripts/import-product-schema.py --limit 5  # dry run, first 5
    python3 scripts/import-product-schema.py --apply    # write
"""

import argparse
import json
import os
import re
import ssl
import sys
import time
import urllib.error
import urllib.request
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
XLSX = REPO / "TFS Final Catalog Sheet - 1_308 ProductsSEO_AEO_GEO Optimized.xlsx"

try:
    import certifi
    SSL_CTX = ssl.create_default_context(cafile=certifi.where())
except ImportError:
    SSL_CTX = ssl.create_default_context()


def load_env():
    env = {}
    p = REPO / ".env"
    for line in (p.read_text(encoding="utf-8").splitlines() if p.exists() else []):
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip()
    dom = (env.get("SHOPIFY_STORE_DOMAIN") or os.environ.get("SHOPIFY_STORE_DOMAIN", ""))
    tok = (env.get("SHOPIFY_ADMIN_ACCESS_TOKEN") or os.environ.get("SHOPIFY_ADMIN_ACCESS_TOKEN", ""))
    ver = (env.get("SHOPIFY_API_VERSION") or os.environ.get("SHOPIFY_API_VERSION", "2024-10"))
    dom = dom.replace("https://", "").replace("http://", "").strip("/")
    if not dom or not tok:
        sys.exit("Missing SHOPIFY_STORE_DOMAIN / SHOPIFY_ADMIN_ACCESS_TOKEN")
    return dom, tok, ver


def http(method, url, token, payload=None):
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(url, data=data, method=method, headers={
        "X-Shopify-Access-Token": token, "Accept": "application/json",
        "Content-Type": "application/json"})
    for attempt in range(8):
        try:
            r = urllib.request.urlopen(req, timeout=120, context=SSL_CTX)
            b = r.read()
            return json.loads(b) if b.strip() else {}
        except urllib.error.HTTPError as e:
            if e.code == 429:
                time.sleep(float(e.headers.get("Retry-After", 2)))
                continue
            if 500 <= e.code < 600:
                time.sleep(2 ** attempt)
                continue
            raise
        except (urllib.error.URLError, TimeoutError, ConnectionError, ssl.SSLError):
            if attempt == 7:
                raise
            time.sleep(2 ** attempt)
    raise RuntimeError(f"retries exhausted: {url}")


def gql(dom, tok, ver, query, variables=None):
    d = http("POST", f"https://{dom}/admin/api/{ver}/graphql.json", tok,
             {"query": query, "variables": variables or {}})
    if d.get("errors"):
        raise SystemExit(json.dumps(d["errors"])[:500])
    return d["data"]


def norm(s):
    s = re.sub(r"[–—]", "-", str(s or "").lower())
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


def money(v):
    try:
        f = float(str(v).replace(",", ""))
        return f"{f:.2f}" if f > 0 else None
    except (TypeError, ValueError):
        return None


def build(row):
    """The stored schema, repaired. Returns (json_text, list_of_repairs)."""
    schema = json.loads(row["schema"])
    fixes = []

    offers = schema.get("offers")
    if isinstance(offers, dict):
        price = offers.get("price")
        if price in (None, "", 0, "0"):
            sheet_price = money(row["price"])
            if sheet_price:
                offers["price"] = sheet_price
                fixes.append("price filled")
            else:
                schema.pop("offers")        # no price anywhere -> no offer
                fixes.append("offers dropped (unpriced)")
        if "offers" in schema:
            url = offers.get("url")
            if url and "@id" not in schema:
                schema["@id"] = url + "#product"
                fixes.append("@id added")

    if row["sku"] and "sku" not in schema:
        schema["sku"] = row["sku"]
        fixes.append("sku added")
    if row["barcode"] and "gtin" not in schema:
        schema["gtin"] = row["barcode"]
        fixes.append("gtin added")

    return json.dumps(schema, ensure_ascii=False, separators=(",", ":")), fixes


def read_sheet():
    try:
        import openpyxl
    except ImportError:
        sys.exit("pip install openpyxl")
    wb = openpyxl.load_workbook(XLSX, read_only=True, data_only=True)
    rows = list(wb[wb.sheetnames[0]].iter_rows(values_only=True))
    hdr = [str(h).strip() if h else "" for h in rows[0]]
    idx = {h: i for i, h in enumerate(hdr)}
    need = ["title", "Product Schema (JSON-LD)", "price", "sku", "barcode"]
    missing = [c for c in need if c not in idx]
    if missing:
        sys.exit(f"sheet is missing expected columns: {missing}")
    out = {}
    for r in rows[1:]:
        if not r or not r[0] or not str(r[0]).strip():
            continue
        def g(c):
            i = idx[c]
            return "" if i >= len(r) or r[i] is None else str(r[i]).strip()
        if not g("Product Schema (JSON-LD)"):
            continue
        out[norm(g("title"))] = {"schema": g("Product Schema (JSON-LD)"),
                                 "price": g("price"), "sku": g("sku"),
                                 "barcode": g("barcode")}
    return out


PRODUCTS_Q = """query($c:String){ products(first:200, after:$c){
  pageInfo{hasNextPage endCursor}
  nodes{ id title metafields(first:45, namespace:"custom"){ nodes{ key value } } } } }"""

SET_MF = """mutation($m:[MetafieldsSetInput!]!){
  metafieldsSet(metafields:$m){ userErrors{ field message } } }"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--limit", type=int)
    args = ap.parse_args()
    dom, tok, ver = load_env()

    sheet = read_sheet()
    products, cur = [], None
    while True:
        page = gql(dom, tok, ver, PRODUCTS_Q, {"c": cur})["products"]
        products += page["nodes"]
        if not page["pageInfo"]["hasNextPage"]:
            break
        cur = page["pageInfo"]["endCursor"]
    print(f"store : {dom}  ({len(products)} products)")
    print(f"sheet : {len(sheet)} rows carry a Product schema\n")

    plan, unmatched, repairs = [], 0, Counter()
    for p in products:
        row = sheet.get(norm(p["title"]))
        if not row:
            unmatched += 1
            continue
        try:
            text, fixes = build(row)
        except json.JSONDecodeError as e:
            repairs["INVALID JSON in sheet - skipped"] += 1
            continue
        json.loads(text)                      # never write anything unparseable
        for f in fixes:
            repairs[f] += 1
        have = {m["key"]: (m["value"] or "") for m in p["metafields"]["nodes"]}
        if have.get("product_schema", "") != text:
            plan.append((p, text))
    if args.limit:
        plan = plan[: args.limit]

    print(f"products to write : {len(plan)}")
    print(f"already correct   : {len(products) - unmatched - len(plan)}")
    print(f"not in the sheet  : {unmatched}\n")
    print("repairs applied on the way in:")
    for k, c in repairs.most_common():
        print(f"  {k:<32}{c:>6}")

    if not args.apply:
        print("\n[dry run — nothing written. Re-run with --apply.]")
        return

    print(f"\nAbout to write custom.product_schema on {len(plan)} products.")
    if input("Type the store domain to confirm: ").strip() != dom:
        sys.exit("confirmation did not match — nothing written")

    ok = failed = 0
    errors = []
    log = REPO / "scripts" / "product-schema-run.json"
    for n, (p, text) in enumerate(plan, 1):
        try:
            res = gql(dom, tok, ver, SET_MF, {"m": [{
                "ownerId": p["id"], "namespace": "custom", "key": "product_schema",
                "type": "multi_line_text_field", "value": text[:65000]}]})
            errs = res["metafieldsSet"]["userErrors"]
            if errs:
                raise RuntimeError(errs[:2])
            ok += 1
        except Exception as e:
            failed += 1
            errors.append({"title": p["title"][:70], "error": str(e)[:200]})
        if n % 50 == 0 or n == len(plan):
            print(f"  [{n}/{len(plan)}] {ok} ok, {failed} failed", flush=True)
            log.write_text(json.dumps({"ok": ok, "failed": failed, "errors": errors[:40]},
                                      indent=1), encoding="utf-8")
    log.write_text(json.dumps({"ok": ok, "failed": failed, "errors": errors[:40]},
                              indent=1), encoding="utf-8")
    print(f"\n{ok} written, {failed} failed -> {log}")


if __name__ == "__main__":
    main()
