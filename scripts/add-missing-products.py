#!/usr/bin/env python3
"""Create the products the listings spreadsheet names but the store does not have.

The spreadsheet is an export of a catalogue with 1,111 unique handles; this
store holds 957. This creates the shortfall so the collection tags applied by
sync-collection-tags.py actually land on something.

What it writes, and nothing else:

    title, handle, vendor, status, tags
    one variant: price, compare_at_price, inventory_policy, inventory_management

Deliberately not written:
    SKU        — no row in the sheet carries one
    inventory  — every existing product in this store is untracked
                 (inventory_management null, policy continue), so quantities
                 would be meaningless here; the sheet's qty column is reported
                 in the dry run but not pushed
    images     — the sheet has no image column, so these arrive imageless and
                 will show the theme placeholder until art is attached
    body_html  — the sheet has no description column

Tags come from whichever collection sheets list the handle, so a product is
created already in its collections; sync-collection-tags.py is then a no-op
for it.

Usage
-----
    python3 scripts/add-missing-products.py                # dry run (default)
    python3 scripts/add-missing-products.py --limit 5      # dry run, first 5
    python3 scripts/add-missing-products.py --report r.md  # save the dry run
    python3 scripts/add-missing-products.py --apply        # create (confirms first)

Nothing is written without --apply.
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
from collections import Counter, defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
XLSX = REPO / "Fragrance_Secrets_Product Listings.xlsx"

SHEET_TAGS = {
    "Oud Woody": "family-oud-woody", "Fresh Citrus": "family-fresh-citrus",
    "Floral Rose": "family-floral-rose", "Sweet Gourmand": "family-sweet-gourmand",
    "Spicy Oriental": "family-spicy-oriental", "Everyday": "everyday-signature",
    "Office Wear": "office-wear", "Date Night": "date-night",
    "Party Wear": "party-clubbing", "Wedding": "wedding",
    "Formal Event": "wedding-formal", "Gym": "gym", "Travel": "travel-friendly",
    "Beach": "beach-vacation", "Vacation": "vacation-beach",
    "Evening Wear": "dinner-evening", "Climate-Summer": "summer-wear",
    "Climate-Winter": "winter-holiday", "Climate-Spring": "spring-bloom",
    "Climate-Rainy": "rainy-day", "Climate-Humid": "humid-weather",
    "Climate-Tropical": "tropical-climate", "Climate-Desert": "desert-climate",
    "Climate-Hot": "hot-weather", "Climate-Cold": "cold-weather",
    "Climate-Dry": "dry-weather", "Arabic Perfumes": "arabic",
    "Luxury Perfumes": "luxury", "Crazy Deals": "sale",
}
HEADER_ROWS, HANDLE_COL = 4, 7

try:
    import certifi
    SSL_CTX = ssl.create_default_context(cafile=certifi.where())
except ImportError:
    SSL_CTX = ssl.create_default_context()


def load_env():
    env = {}
    p = REPO / ".env"
    if p.exists():
        for line in p.read_text(encoding="utf-8").splitlines():
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


def request(method, url, token, payload=None):
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(url, data=data, method=method, headers={
        "X-Shopify-Access-Token": token, "Accept": "application/json",
        "Content-Type": "application/json"})
    for _ in range(6):
        try:
            r = urllib.request.urlopen(req, timeout=60, context=SSL_CTX)
            return json.load(r), r.headers
        except urllib.error.HTTPError as e:
            if e.code == 429:
                time.sleep(float(e.headers.get("Retry-After", 2)))
                continue
            raise
    raise RuntimeError(f"retries exhausted: {url}")


def existing_handles(dom, tok, ver):
    out, url = set(), f"https://{dom}/admin/api/{ver}/products.json?limit=250&fields=id,handle"
    while url:
        body, headers = request("GET", url, tok)
        out |= {p["handle"] for p in body["products"]}
        m = re.search(r'<([^>]+)>;\s*rel="next"', headers.get("Link", ""))
        url = m.group(1) if m else None
    return out


def read_sheet_rows():
    try:
        import openpyxl
    except ImportError:
        sys.exit("pip install openpyxl")
    wb = openpyxl.load_workbook(XLSX, read_only=True, data_only=True)
    info, tags = {}, defaultdict(set)
    for sheet, tag in SHEET_TAGS.items():
        for i, r in enumerate(wb[sheet].iter_rows(values_only=True)):
            if i < HEADER_ROWS or not r or not r[0]:
                continue
            if len(r) <= HANDLE_COL or not r[HANDLE_COL]:
                continue
            h = str(r[HANDLE_COL]).strip()
            tags[h].add(tag)              # a set, so the sheet's repeated rows collapse
            info.setdefault(h, {
                "title": str(r[0]).strip(), "vendor": str(r[1] or "").strip(),
                "price": r[3], "compare": r[4], "qty": r[5],
                "family": str(r[6] or "").strip()})
    return info, tags


def money(v):
    try:
        return f"{float(v):.2f}"
    except (TypeError, ValueError):
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--report")
    args = ap.parse_args()

    dom, tok, ver = load_env()
    info, tags = read_sheet_rows()
    have = existing_handles(dom, tok, ver)
    missing = sorted(set(info) - have)
    if args.limit:
        missing = missing[: args.limit]

    L = []
    def say(s=""):
        print(s); L.append(s)

    say(f"store            : {dom}")
    say(f"sheet handles    : {len(info)}")
    say(f"already in store : {len(set(info) & have)}")
    say(f"to create        : {len(missing)}")
    say()
    say("by vendor:")
    for v, c in Counter(info[h]["vendor"] for h in missing).most_common():
        say(f"  {c:4d}  {v}")
    say()
    no_price = [h for h in missing if money(info[h]["price"]) is None]
    say(f"rows with no usable price : {len(no_price)}")
    say(f"sheet qty column          : not written (store keeps inventory untracked)")
    say(f"images                    : none available in the sheet")
    say()
    say("first 10 payloads:")
    for h in missing[:10]:
        d = info[h]
        say(f"  {d['title'][:56]:56s} AED {money(d['price'])!s:>8s}  [{', '.join(sorted(tags[h]))[:52]}]")
    say()

    if args.report:
        Path(args.report).write_text("\n".join(L) + "\n", encoding="utf-8")
        print(f"[report -> {args.report}]")
    if not args.apply:
        print("[dry run — nothing created. Re-run with --apply.]")
        return

    print(f"\nAbout to CREATE {len(missing)} products on {dom}.")
    if input("Type the store domain to confirm: ").strip() != dom:
        sys.exit("confirmation did not match — nothing created")

    created, failed = [], []
    for n, h in enumerate(missing, 1):
        d = info[h]
        variant = {"price": money(d["price"]) or "0.00",
                   "inventory_management": None, "inventory_policy": "continue"}
        cmp_at = money(d["compare"])
        if cmp_at and float(cmp_at) > float(variant["price"]):
            variant["compare_at_price"] = cmp_at
        payload = {"product": {
            "title": d["title"], "handle": h, "vendor": d["vendor"],
            "status": "active", "tags": ", ".join(sorted(tags[h])),
            "variants": [variant]}}
        try:
            body, _ = request("POST", f"https://{dom}/admin/api/{ver}/products.json", tok, payload)
            pid = body["product"]["id"]
            created.append({"id": pid, "handle": h, "title": d["title"]})
            print(f"  [{n}/{len(missing)}] created {pid}  {h[:60]}")
        except urllib.error.HTTPError as e:
            msg = e.read().decode()[:160]
            failed.append({"handle": h, "error": f"{e.code} {msg}"})
            print(f"  [{n}/{len(missing)}] FAILED  {h[:50]}  {e.code} {msg}")
        time.sleep(0.55)

    out = REPO / "scripts" / "created-products.json"
    out.write_text(json.dumps({"created": created, "failed": failed}, indent=1), encoding="utf-8")
    print(f"\ncreated {len(created)}, failed {len(failed)} -> {out}")


if __name__ == "__main__":
    main()
