#!/usr/bin/env python3
"""Populate the product metafields the PDP reads, from the final catalogue sheet.

This is what makes the Description / Best For / Specifications tabs correct.
Without it the Best For tab does not render at all on products with no
best_for_details, the Specifications table shows only Brand, and the key-info
strip falls back to the same hardcoded "8-12 hours / Strong / Evening / Party
/ UAE" on every product.

The key list is explicit and closed. Every key below is one the theme actually
reads (verified against sections/ and snippets/) AND one the sheet supplies —
nothing is written speculatively, and no other namespace is touched.

    theme key            sheet column         feeds
    best_for_details     best_for_details     the Best For tab
    fragrance_family     fragrance_family     Specifications, notes block
    concentration        concentration        Specifications
    size                 size                 Specifications, card spec line
    product_form         product_form         Specifications
    dispenser            dispenser            Specifications
    gender               gender               Specifications, card spec line
    occasion             occasion             Specifications
    bottle_colour        bottle_colour        Specifications
    longevity            longevity            Specifications, key-info strip
    ships_to             ships_to             Specifications
    barcode              barcode              Specifications
    sillage              projection           key-info strip
    origin               made_in              key-info strip
    best_for             best_for             key-info strip
    notes_top/heart/base notes_*              the scent pyramid
    faq                  faq                  the PDP FAQ block
    why_youll_love       why_youll_love       the Description tab, after the copy
    inspired_by          inspired_by          the Inspired By tile

Three of those are renames, which is the whole reason this cannot be a blind
column-to-key copy: the theme reads `sillage` where the sheet says projection,
and `origin` where it says made_in.

Deliberately excluded:
    badge — the sheet marks 1,155 of 1,308 rows "New". A badge on 88% of the
        catalogue says nothing, and product-card.liquid already carries a
        hide_new flag to work around exactly that. Left to merchandising.
    Meta Title / Meta Description / the JSON-LD columns — these are SEO
        fields, ~150 of them name the inspired-by brand, and they belong to
        their own reviewed pass rather than riding along with this one.

Types match what the store already uses: multi_line_text_field for
best_for_details and faq, single_line_text_field for everything else. A
mismatched type is rejected by Shopify, so these are not guesses — they were
read off the existing products first.

Only values that actually differ are written, so a second run is a no-op.

    python3 scripts/import-product-metafields.py              # dry run
    python3 scripts/import-product-metafields.py --limit 5    # dry run, 5
    python3 scripts/import-product-metafields.py --apply      # write
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

MULTILINE = {"best_for_details", "faq", "why_youll_love"}
# theme metafield key -> sheet column
KEYS = {
    "best_for_details": "best_for_details",
    "fragrance_family": "fragrance_family",
    "concentration":    "concentration",
    "size":             "size",
    "product_form":     "product_form",
    "dispenser":        "dispenser",
    "gender":           "gender",
    "occasion":         "occasion",
    "bottle_colour":    "bottle_colour",
    "longevity":        "longevity",
    "ships_to":         "ships_to",
    "barcode":          "barcode",
    "sillage":          "projection",     # rename
    "origin":           "made_in",        # rename
    "best_for":         "best_for",
    "notes_top":        "notes_top",
    "notes_heart":      "notes_heart",
    "notes_base":       "notes_base",
    "faq":              "faq",
    "inspired_by":      "inspired_by",
    "why_youll_love":   "why_youll_love",
}

try:
    import certifi
    SSL_CTX = ssl.create_default_context(cafile=certifi.where())
except ImportError:
    SSL_CTX = ssl.create_default_context()


def load_env():
    env = {}
    p = REPO / ".env"
    for line in p.read_text(encoding="utf-8").splitlines() if p.exists() else []:
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
            body = r.read()
            return (json.loads(body) if body.strip() else {}), r.headers
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
    body, _ = http("POST", f"https://{dom}/admin/api/{ver}/graphql.json", tok,
                   {"query": query, "variables": variables or {}})
    if body.get("errors"):
        raise SystemExit(json.dumps(body["errors"])[:500])
    return body["data"]


def norm(s):
    s = re.sub(r"[–—]", "-", str(s or "").lower())
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


def read_sheet():
    try:
        import openpyxl
    except ImportError:
        sys.exit("pip install openpyxl")
    wb = openpyxl.load_workbook(XLSX, read_only=True, data_only=True)
    rows = list(wb[wb.sheetnames[0]].iter_rows(values_only=True))
    hdr = [str(h).strip() if h else "" for h in rows[0]]
    idx = {h: i for i, h in enumerate(hdr)}
    missing = [c for c in KEYS.values() if c not in idx]
    if missing:
        sys.exit(f"sheet is missing expected columns: {missing}")
    out = {}
    for r in rows[1:]:
        if not r or not r[0] or not str(r[0]).strip():
            continue
        def g(c):
            i = idx[c]
            return "" if i >= len(r) or r[i] is None else str(r[i]).strip()
        out[norm(g("title"))] = {k: g(col) for k, col in KEYS.items()}
    return out


PRODUCTS_Q = """query($c:String){ products(first:100, after:$c){
  pageInfo{hasNextPage endCursor}
  nodes{ id title metafields(first:40, namespace:"custom"){ nodes{ key value } } } } }"""

SET_M = """mutation($m:[MetafieldsSetInput!]!){ metafieldsSet(metafields:$m){
  userErrors{ field message } } }"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--limit", type=int)
    args = ap.parse_args()
    dom, tok, ver = load_env()

    sheet = read_sheet()
    print(f"store : {dom}")
    print(f"sheet : {XLSX.name}  ({len(sheet)} rows)")

    products, cur = [], None
    while True:
        page = gql(dom, tok, ver, PRODUCTS_Q, {"c": cur})["products"]
        products += page["nodes"]
        if not page["pageInfo"]["hasNextPage"]:
            break
        cur = page["pageInfo"]["endCursor"]
    print(f"store : {len(products)} products\n")

    plan, unmatched = [], 0
    per_key = Counter()
    for p in products:
        row = sheet.get(norm(p["title"]))
        if not row:
            unmatched += 1
            continue
        have = {m["key"]: (m["value"] or "") for m in p["metafields"]["nodes"]}
        writes = []
        for key, val in row.items():
            if not val:
                continue                       # never blank out an existing value
            if have.get(key, "") == val:
                continue                       # already correct
            writes.append({
                "ownerId": p["id"], "namespace": "custom", "key": key,
                "type": "multi_line_text_field" if key in MULTILINE else "single_line_text_field",
                "value": val[:65000],
            })
            per_key[key] += 1
        if writes:
            plan.append((p, writes))
    if args.limit:
        plan = plan[: args.limit]

    print(f"products needing metafields : {len(plan)}")
    print(f"products already correct    : {len(products) - unmatched - len(plan)}")
    print(f"products not in the sheet   : {unmatched}")
    print(f"metafields to write         : {sum(len(w) for _, w in plan)}\n")
    print(f"{'key':<20}{'writes':>8}")
    for k, c in per_key.most_common():
        print(f"  {k:<18}{c:>8}")

    if not args.apply:
        print("\n[dry run — nothing written. Re-run with --apply.]")
        return

    print(f"\nAbout to write metafields on {len(plan)} products on {dom}.")
    if input("Type the store domain to confirm: ").strip() != dom:
        sys.exit("confirmation did not match — nothing written")

    ok = failed = 0
    errors = []
    log = REPO / "scripts" / "metafield-import-run.json"
    for n, (p, writes) in enumerate(plan, 1):
        # metafieldsSet takes up to 25 per call; 20 keys fits in one.
        for chunk in [writes[i:i + 25] for i in range(0, len(writes), 25)]:
            try:
                res = gql(dom, tok, ver, SET_M, {"m": chunk})["metafieldsSet"]
                errs = res.get("userErrors") or []
                if errs:
                    failed += 1
                    errors.append({"title": p["title"], "errors": errs[:3]})
                else:
                    ok += len(chunk)
            except Exception as e:
                failed += 1
                errors.append({"title": p["title"], "errors": str(e)[:200]})
        if n % 50 == 0 or n == len(plan):
            print(f"  [{n}/{len(plan)}] {ok} metafields written", flush=True)
            log.write_text(json.dumps({"written": ok, "failed": failed,
                                       "errors": errors[:50]}, indent=1), encoding="utf-8")
        time.sleep(0.35)
    log.write_text(json.dumps({"written": ok, "failed": failed,
                               "errors": errors[:50]}, indent=1), encoding="utf-8")
    print(f"\nwrote {ok} metafields, {failed} failures -> {log}")


if __name__ == "__main__":
    main()
