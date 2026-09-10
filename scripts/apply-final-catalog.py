#!/usr/bin/env python3
"""Bring the store in line with the final catalogue sheet.

Source: "TFS Final Catalog Sheet - 1_308 ProductsSEO_AEO_GEO Optimized.xlsx".
The sheet has no handle column and only a handful of store products carry a
SKU, so rows are matched to products on a normalised title.

Three phases, additive work first and the destructive step last so a failure
part-way through never loses data that has not already been written:

  1. CREATE  rows in the sheet with no product in the store
  2. UPDATE  products that match a row, on the fields listed below
  3. DELETE  products with no row in the sheet

Fields written on an UPDATE, and nothing else:

    price, compare_at_price      from the sheet
    body_html                    from `description`, brand-cleaned (below)
    status, vendor, product_type
    sku                          only when the store variant has none
    image                        only when the product has none
    metafield custom.inspired_by the single named key, nothing else

Deliberately not touched on an update:
    title / handle  — they are the match key, and rewriting a handle breaks
                      every existing link to the product
    tags            — these carry the smart-collection membership set by
                      sync-collection-tags.py; changing them here would move
                      products between collections as a side effect
    every other metafield — docs/GO-LIVE.md forbids bulk metafield writes
                      without an explicit allow-list. That allow-list is
                      exactly one key: custom.inspired_by. The sheet's other
                      ~20 metafield columns deserve their own reviewed pass.

CREATE writes the same fields plus tags, taken from the row's own attributes
(family_collection, badge, collections_extra, gender). The script asserts none
of those collide with the 29 tags the smart collections key on, so creating a
product can never quietly change collection membership.

inspired_by never becomes a tag and never reaches body_html. Tags and
descriptions are public and can be pulled into the Google feed, so the brand
a fragrance is inspired by lives only in the custom.inspired_by metafield,
rendered in the PDP's "Inspired by" box. clean_description() strips it out of
the 153 descriptions that name it.

    python3 scripts/apply-final-catalog.py                  # dry run, all phases
    python3 scripts/apply-final-catalog.py --phase create   # dry run, one phase
    python3 scripts/apply-final-catalog.py --apply          # run (confirms first)
    python3 scripts/apply-final-catalog.py --apply --phase update
"""

import argparse
import html as _html
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

MANAGED_TAGS = {
    "family-oud-woody", "family-fresh-citrus", "family-floral-rose",
    "family-sweet-gourmand", "family-spicy-oriental", "everyday-signature",
    "office-wear", "date-night", "party-clubbing", "wedding", "wedding-formal",
    "gym", "travel-friendly", "beach-vacation", "vacation-beach",
    "dinner-evening", "summer-wear", "winter-holiday", "spring-bloom",
    "rainy-day", "humid-weather", "tropical-climate", "desert-climate",
    "hot-weather", "cold-weather", "dry-weather", "arabic", "luxury", "sale",
}

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
    dom = env.get("SHOPIFY_STORE_DOMAIN") or os.environ.get("SHOPIFY_STORE_DOMAIN", "")
    tok = env.get("SHOPIFY_ADMIN_ACCESS_TOKEN") or os.environ.get("SHOPIFY_ADMIN_ACCESS_TOKEN", "")
    ver = env.get("SHOPIFY_API_VERSION") or os.environ.get("SHOPIFY_API_VERSION", "2024-10")
    dom = dom.replace("https://", "").replace("http://", "").strip("/")
    if not dom or not tok:
        sys.exit("Missing SHOPIFY_STORE_DOMAIN / SHOPIFY_ADMIN_ACCESS_TOKEN")
    return dom, tok, ver


def request(method, url, token, payload=None):
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
            if e.code == 429:                       # leaky bucket full
                time.sleep(float(e.headers.get("Retry-After", 2)))
                continue
            if 500 <= e.code < 600:                 # Shopify hiccup
                time.sleep(2 ** attempt)
                continue
            raise
        except (urllib.error.URLError, TimeoutError, ConnectionError, ssl.SSLError) as e:
            # A read timeout part-way through a 1,300-product run should cost a
            # retry, not the whole run. Backs off 1,2,4,8... seconds.
            if attempt == 7:
                raise
            time.sleep(2 ** attempt)
            continue
    raise RuntimeError(f"retries exhausted: {url}")


def norm(s):
    s = re.sub(r"[–—]", "-", str(s or "").lower())
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


def handleize(s):
    s = re.sub(r"[–—]", "-", str(s or "").lower())
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")[:255]


def money(v):
    try:
        f = float(str(v).replace(",", ""))
        return f"{f:.2f}" if f > 0 else None
    except (TypeError, ValueError):
        return None


def clean_description(desc, brand):
    """Drop the inspired-by brand from feed-facing copy.

    body_html is what Shopify hands the Google feed, and 153 of the sheet's
    descriptions open by naming the fragrance they are inspired by. The brand
    belongs in the custom.inspired_by metafield and the PDP box only, so the
    reference is removed here while the sentence, and the rest of the copy,
    survives intact:

        "Amethyst inspired perfume is a fruity extrait de parfum for men and
         women from The Fragrance Secrets."
     -> "This is a fruity extrait de parfum for men and women from The
         Fragrance Secrets."
    """
    if not desc or not brand:
        return desc
    b = re.escape(brand)
    for pattern, repl in (
        (rf"^\s*{b}\s+inspired\s+(perfume|perfume oil|fragrance)\s+is\b", "This is"),
        (rf"(^|(?<=[.!?]\s)){b}\s+inspired\b", "This inspired"),
    ):
        new = re.sub(pattern, repl, desc, count=1, flags=re.I)
        if new != desc:
            return new.strip()
    return re.sub(rf"\b{b}\b\s*", "", desc, flags=re.I).strip()


def as_text(html):
    """Plain text of a description, for comparison only.

    Shopify wraps a plain-text body_html in <p>...</p> on save, so comparing
    the stored value against the sheet's raw text always differs. Strip tags
    and collapse whitespace on both sides before deciding anything changed —
    otherwise every run rewrites every description and never converges.
    """
    plain = re.sub(r"<[^>]+>", " ", html or "")
    # Shopify escapes & as &amp; on save; unescape before comparing or every
    # description containing an ampersand differs forever.
    return re.sub(r"\s+", " ", _html.unescape(plain)).strip()


def inspired_metafield(row):
    """The one metafield this script writes, named explicitly per GO-LIVE."""
    if not row.get("inspired_by"):
        return None
    return {"namespace": "custom", "key": "inspired_by",
            "type": "single_line_text_field", "value": row["inspired_by"][:255]}


def read_sheet():
    try:
        import openpyxl
    except ImportError:
        sys.exit("pip install openpyxl")
    wb = openpyxl.load_workbook(XLSX, read_only=True, data_only=True)
    rows = list(wb[wb.sheetnames[0]].iter_rows(values_only=True))
    hdr = [str(h).strip() if h else "" for h in rows[0]]
    idx = {h: i for i, h in enumerate(hdr)}
    keep = ("title", "vendor", "product_type", "status", "price", "compare_at_price",
            "sku", "gender", "family_collection", "collections_extra", "badge",
            "inspired_by", "image_url", "description")
    out = []
    for r in rows[1:]:
        if not r or not r[0] or not str(r[0]).strip():
            continue
        def g(k):
            i = idx.get(k)
            if i is None or i >= len(r) or r[i] is None:
                return ""
            return str(r[i]).strip()
        out.append({k: g(k) for k in keep})
    return out


def tags_for(row):
    tags, seen = [], set()
    # inspired_by is deliberately absent: it goes to a metafield, never a tag,
    # because tags are public and can be pulled into the Google feed.
    for part in (row["family_collection"], row["badge"], row["collections_extra"],
                 row["gender"]):
        for t in str(part).split(","):
            t = t.strip()
            if t and t.lower() not in seen:
                seen.add(t.lower())
                tags.append(t)
    return tags


def fetch_store(dom, tok, ver):
    out, url = [], (f"https://{dom}/admin/api/{ver}/products.json?limit=250"
                    f"&fields=id,handle,title,vendor,status,product_type,variants,images,body_html")
    while url:
        body, headers = request("GET", url, tok)
        out.extend(body["products"])
        m = re.search(r'<([^>]+)>;\s*rel="next"', headers.get("Link", ""))
        url = m.group(1) if m else None
    return out


def plan_update(p, r, existing_inspired=None):
    """Return the fields that actually differ, or None if the product is current."""
    v = p["variants"][0]
    prod, var = {}, {}
    sp = money(r["price"])
    if sp and v["price"] != sp:
        var["price"] = sp
    cmp_at = money(r["compare_at_price"])
    effective = float(sp or v["price"])
    if cmp_at and float(cmp_at) > effective and (v.get("compare_at_price") or "") != cmp_at:
        var["compare_at_price"] = cmp_at
    else:
        # Raising the price can strand an existing compare-at below it, which
        # renders as a struck-through "was" price cheaper than the real one.
        # Clear it rather than leave a sale that reads as an error.
        existing = money(v.get("compare_at_price"))
        if existing and float(existing) <= effective:
            var["compare_at_price"] = None
    if r["sku"] and not (v.get("sku") or "").strip():
        var["sku"] = r["sku"]
    desc = clean_description(r["description"], r["inspired_by"])
    if desc and len(desc) > 20 and as_text(p.get("body_html")) != as_text(desc):
        prod["body_html"] = desc
    if r["status"] in ("active", "draft") and p["status"] != r["status"]:
        prod["status"] = r["status"]
    if r["vendor"] and p["vendor"] != r["vendor"]:
        prod["vendor"] = r["vendor"]
    if r["product_type"] and (p.get("product_type") or "") != r["product_type"]:
        prod["product_type"] = r["product_type"]
    add_image = bool(r["image_url"]) and not p["images"]
    mf = inspired_metafield(r)
    if mf and existing_inspired is not None and existing_inspired == mf["value"]:
        mf = None                      # already set to this value
    if not prod and not var and not add_image and not mf:
        return None
    return {"product": prod, "variant": var, "add_image": add_image, "metafield": mf}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--phase", choices=["create", "update", "delete"], action="append")
    ap.add_argument("--limit", type=int)
    args = ap.parse_args()
    phases = args.phase or ["create", "update", "delete"]

    dom, tok, ver = load_env()
    rows = read_sheet()
    store = fetch_store(dom, tok, ver)
    by_title = {norm(p["title"]): p for p in store}
    have_handle = {p["handle"] for p in store}
    sheet_titles = {norm(r["title"]) for r in rows}

    creates, updates, deletes, unchanged = [], [], [], 0
    seen = set()
    for r in rows:
        k = norm(r["title"])
        if k in seen:
            continue
        seen.add(k)
        p = by_title.get(k)
        if p is None:
            h = handleize(r["title"])
            if h in have_handle:
                continue
            r["handle"] = h
            creates.append(r)
        else:
            cur = None
            if r.get("inspired_by"):
                try:
                    body, _ = request("GET",
                        f"https://{dom}/admin/api/{ver}/products/{p['id']}/metafields.json"
                        "?namespace=custom&key=inspired_by", tok)
                    ms = body.get("metafields") or []
                    cur = ms[0]["value"] if ms else ""
                    time.sleep(0.3)     # pace the lookups; a throttled GET
                                        # would otherwise flag a correct row
                except Exception:
                    cur = None          # unknown -> write it, upsert is safe
            d = plan_update(p, r, cur)
            if d:
                updates.append((p, r, d))
            else:
                unchanged += 1
    for p in store:
        if norm(p["title"]) not in sheet_titles:
            deletes.append(p)

    collide = {t for r in creates for t in tags_for(r) if t.lower() in MANAGED_TAGS}
    print(f"store  : {dom}  ({len(store)} products)")
    print(f"sheet  : {XLSX.name}  ({len(rows)} rows)")
    print(f"phases : {', '.join(phases)}\n")
    print(f"  CREATE   {len(creates):>5}   in the sheet, absent from the store")
    print(f"  UPDATE   {len(updates):>5}   matched and differing  ({unchanged} already current)")
    print(f"  DELETE   {len(deletes):>5}   in the store, absent from the sheet")
    print(f"\ntag collisions with the 29 managed tags: {len(collide)} {sorted(collide) if collide else '(none)'}")
    if collide:
        sys.exit("refusing to run: a tag would change smart-collection membership")

    fields = Counter()
    for _, _, d in updates:
        for k in d["product"]:
            fields[k] += 1
        for k in d["variant"]:
            fields[k] += 1
        if d["add_image"]:
            fields["image"] += 1
    if updates:
        print("\nupdate touches:")
        for k, c in fields.most_common():
            print(f"   {k:<20}{c:>5}")
    if creates:
        print("\ncreate, top vendors:")
        for v, c in Counter(r["vendor"] for r in creates).most_common(6):
            print(f"   {c:>4}  {v}")
    if deletes:
        print(f"\ndelete, first 3 of {len(deletes)}:")
        for p in deletes[:3]:
            print(f"   {p['id']}  {p['title'][:64]}")

    if args.limit:
        creates, updates, deletes = creates[:args.limit], updates[:args.limit], deletes[:args.limit]

    if not args.apply:
        print("\n[dry run — nothing written. Re-run with --apply.]")
        return

    print(f"\nAbout to run {', '.join(phases)} on {dom}.")
    if "delete" in phases and deletes:
        print(f"{len(deletes)} products will be PERMANENTLY DELETED. This cannot be undone.")
    if input("Type the store domain to confirm: ").strip() != dom:
        sys.exit("confirmation did not match — nothing written")

    log = {"created": [], "updated": [], "deleted": [], "failed": []}
    log_path = REPO / "scripts" / "final-catalog-run.json"

    def flush():
        log_path.write_text(json.dumps(log, indent=1), encoding="utf-8")

    flush()

    if "create" in phases:
        print(f"\n── CREATE ({len(creates)}) ──")
        for n, r in enumerate(creates, 1):
            price = money(r["price"]) or "0.00"
            variant = {"price": price, "inventory_management": None,
                       "inventory_policy": "continue"}
            cmp_at = money(r["compare_at_price"])
            if cmp_at and float(cmp_at) > float(price):
                variant["compare_at_price"] = cmp_at
            if r["sku"]:
                variant["sku"] = r["sku"]
            prod = {"title": r["title"], "handle": r["handle"], "vendor": r["vendor"],
                    "product_type": r["product_type"],
                    "status": "active" if r["status"] == "active" else "draft",
                    "body_html": clean_description(r["description"], r["inspired_by"]),
                    "tags": ", ".join(tags_for(r)),
                    "variants": [variant]}
            if r["image_url"]:
                prod["images"] = [{"src": r["image_url"], "alt": r["title"][:512]}]
            mf = inspired_metafield(r)
            if mf:
                prod["metafields"] = [mf]
            try:
                body, _ = request("POST", f"https://{dom}/admin/api/{ver}/products.json",
                                  tok, {"product": prod})
                log["created"].append({"id": body["product"]["id"], "handle": body["product"]["handle"]})
                flush()
                if n % 25 == 0 or n == len(creates):
                    print(f"  [{n}/{len(creates)}] created", flush=True)
            except urllib.error.HTTPError as e:
                log["failed"].append({"phase": "create", "title": r["title"],
                                      "error": f"{e.code} {e.read().decode()[:120]}"})
                print(f"  [{n}] CREATE FAILED {r['title'][:44]}", flush=True)
            time.sleep(0.55)

    if "update" in phases:
        print(f"\n── UPDATE ({len(updates)}) ──")
        for n, (p, r, d) in enumerate(updates, 1):
            payload = {"product": {"id": p["id"], **d["product"]}}
            if d["variant"]:
                payload["product"]["variants"] = [{"id": p["variants"][0]["id"], **d["variant"]}]
            if d["add_image"]:
                payload["product"]["images"] = [{"src": r["image_url"], "alt": r["title"][:512]}]
            if d.get("metafield"):
                payload["product"]["metafields"] = [d["metafield"]]
            try:
                request("PUT", f"https://{dom}/admin/api/{ver}/products/{p['id']}.json", tok, payload)
                log["updated"].append({"id": p["id"], "handle": p["handle"],
                                       "fields": sorted({**d["product"], **d["variant"]})})
                flush()
                if n % 50 == 0 or n == len(updates):
                    print(f"  [{n}/{len(updates)}] updated", flush=True)
            except urllib.error.HTTPError as e:
                log["failed"].append({"phase": "update", "handle": p["handle"],
                                      "error": f"{e.code} {e.read().decode()[:120]}"})
                print(f"  [{n}] UPDATE FAILED {p['handle'][:44]}", flush=True)
            time.sleep(0.55)

    if "delete" in phases:
        print(f"\n── DELETE ({len(deletes)}) ──")
        for n, p in enumerate(deletes, 1):
            # last guard: never delete something the sheet actually names
            if norm(p["title"]) in sheet_titles:
                log["failed"].append({"phase": "delete", "handle": p["handle"],
                                      "error": "title is in the sheet — refused"})
                continue
            try:
                request("DELETE", f"https://{dom}/admin/api/{ver}/products/{p['id']}.json", tok)
                log["deleted"].append({"id": p["id"], "handle": p["handle"], "title": p["title"]})
                flush()
                if n % 20 == 0 or n == len(deletes):
                    print(f"  [{n}/{len(deletes)}] deleted", flush=True)
            except urllib.error.HTTPError as e:
                log["failed"].append({"phase": "delete", "handle": p["handle"],
                                      "error": f"{e.code} {e.read().decode()[:120]}"})
            time.sleep(0.55)

    flush()
    out = log_path
    print(f"\ncreated {len(log['created'])}, updated {len(log['updated'])}, "
          f"deleted {len(log['deleted'])}, failed {len(log['failed'])}  -> {out}")


if __name__ == "__main__":
    main()
