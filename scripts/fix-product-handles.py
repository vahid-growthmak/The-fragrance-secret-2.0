#!/usr/bin/env python3
"""Rename product handles to the Canonical URL the catalogue sheet specifies.

Every product on this store got its handle from Shopify slugifying the title
at creation time. That was wrong: the sheet carries a Canonical URL column,
and the same URL is repeated inside each row's Product Schema `offers.url`, so
the intended handle was supplied all along and simply never read.

333 of 1,308 handles disagree with it. The differences are substantive, not
cosmetic — the sheet's title and canonical disagree on size for some rows
(75ml in the title, 100ml in the URL), the canonical carries keyword tails the
title does not ("...-for-men-fruity-woody-amber"), and title slugification
mangles accents that the canonical spells out ("Boisée" -> bois-e vs boisee).

Handles are the public URL. Changing one breaks every existing link to it, so
each rename is paired with a 301 from the old path to the new one, created in
the same step. Shopify does that automatically when you edit a handle in the
admin UI; it does not when you do it over the API.

Safety, in the order the checks run:

  1. Every product must match a sheet row by normalised title. A product the
     sheet does not describe is left completely alone.
  2. A target handle held by a *different* product aborts the whole run rather
     than renaming into a collision. Shopify would silently append "-1" and
     hand back a handle nobody asked for.
  3. The handle Shopify returns is compared against the one requested. A
     mismatch is recorded as a failure, not counted as a success.
  4. Redirects are created only after the rename succeeds, so a failed rename
     never leaves a 301 pointing at a URL that does not exist.

    python3 scripts/fix-product-handles.py            # dry run
    python3 scripts/fix-product-handles.py --limit 5  # dry run, first 5
    python3 scripts/fix-product-handles.py --apply    # rename + redirect
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
            body = r.read()
            return (json.loads(body) if body.strip() else {}), r.headers
        except urllib.error.HTTPError as e:
            if e.code == 429:
                time.sleep(float(e.headers.get("Retry-After", 2)))
                continue
            if 500 <= e.code < 600 and attempt < 7:
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
    """Title -> comparison key. Matches the other import scripts exactly."""
    s = re.sub(r"[–—]", "-", str(s or "").lower())
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


def handle_of(url):
    """Last path segment of a canonical URL, minus query and fragment."""
    u = str(url or "").strip().split("?")[0].split("#")[0].rstrip("/")
    return u.split("/")[-1] if u else ""


def read_sheet():
    try:
        import openpyxl
    except ImportError:
        sys.exit("pip install openpyxl")
    wb = openpyxl.load_workbook(XLSX, read_only=True, data_only=True)
    rows = list(wb[wb.sheetnames[0]].iter_rows(values_only=True))
    hdr = [str(h).strip() if h else "" for h in rows[0]]
    idx = {h: i for i, h in enumerate(hdr)}
    for c in ("title", "Canonical URL"):
        if c not in idx:
            sys.exit(f"sheet is missing the {c!r} column")
    out, seen = {}, Counter()
    for r in rows[1:]:
        if not r or not r[0] or not str(r[0]).strip():
            continue
        def g(c):
            i = idx[c]
            return "" if i >= len(r) or r[i] is None else str(r[i]).strip()
        h = handle_of(g("Canonical URL"))
        if not h:
            continue
        if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", h):
            sys.exit(f"canonical handle is not a legal Shopify handle: {h!r}")
        seen[h] += 1
        out[norm(g("title"))] = h
    dupes = [h for h, n in seen.items() if n > 1]
    if dupes:
        sys.exit(f"{len(dupes)} canonical handles are claimed by more than one row: {dupes[:5]}")
    return out


PRODUCTS_Q = """query($c:String){ products(first:250, after:$c){
  pageInfo{hasNextPage endCursor} nodes{ id handle title status } } }"""

RENAME = """mutation($id:ID!,$h:String!){ productUpdate(input:{id:$id, handle:$h}){
  product{ id handle } userErrors{ field message } } }"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--no-redirects", action="store_true",
                    help="rename only; do not create the 301s (not recommended)")
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
    print(f"sheet : {XLSX.name}  ({len(sheet)} rows with a canonical URL)\n")

    by_handle = {p["handle"]: p for p in products}
    plan, correct, unmatched = [], 0, []
    for p in products:
        want = sheet.get(norm(p["title"]))
        if not want:
            unmatched.append(p["title"])
            continue
        if want == p["handle"]:
            correct += 1
        else:
            plan.append({"id": p["id"], "title": p["title"],
                         "old": p["handle"], "new": want})

    # A target already held by a product that is NOT itself moving away would
    # make Shopify invent "handle-1". Refuse the run rather than half-apply it.
    moving_away = {j["old"] for j in plan}
    collisions = []
    for j in plan:
        occ = by_handle.get(j["new"])
        if occ and occ["id"] != j["id"] and occ["handle"] not in moving_away:
            collisions.append((j["old"], j["new"], occ["title"]))

    print(f"handles already canonical : {correct}")
    print(f"handles to rename         : {len(plan)}")
    print(f"products not in the sheet : {len(unmatched)}")
    for t in unmatched[:5]:
        print(f"    (left alone) {t[:70]}")
    if collisions:
        print(f"\nCOLLISIONS — target handle held by a product that is not moving: {len(collisions)}")
        for old, new, who in collisions[:10]:
            print(f"    {old[:46]:<48} -> {new[:46]}   held by {who[:40]}")
        sys.exit("\nrefusing to run: resolve the collisions above first")

    if args.limit:
        plan = plan[: args.limit]
    if plan:
        print("\nfirst 8 renames:")
        for j in plan[:8]:
            print(f"    {j['old'][:60]}\n      -> {j['new'][:60]}")

    preview = REPO / "scripts" / "handle-rename-plan.json"
    preview.write_text(json.dumps(plan, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"\nfull plan written to {preview.relative_to(REPO)}")

    if not args.apply:
        print("\n[dry run — nothing renamed. Re-run with --apply.]")
        return
    if not plan:
        print("\nnothing to do")
        return

    print(f"\nAbout to rename {len(plan)} product handles on {dom}"
          f"{'' if args.no_redirects else ', each with a 301 from the old URL'}.")
    print("This changes public product URLs.")
    if input("Type the store domain to confirm: ").strip() != dom:
        sys.exit("confirmation did not match — nothing renamed")

    renamed = redirected = failed = 0
    errors, done = [], []
    log = REPO / "scripts" / "handle-rename-run.json"

    def flush():
        log.write_text(json.dumps({"renamed": renamed, "redirected": redirected,
                                   "failed": failed, "errors": errors[:60],
                                   "done": done}, indent=1, ensure_ascii=False),
                       encoding="utf-8")

    for n, j in enumerate(plan, 1):
        try:
            res = gql(dom, tok, ver, RENAME, {"id": j["id"], "h": j["new"]})["productUpdate"]
            errs = res.get("userErrors") or []
            if errs:
                raise RuntimeError(errs[:2])
            got = res["product"]["handle"]
            if got != j["new"]:
                # Shopify silently uniquified it. Say so instead of banking it.
                raise RuntimeError(f"asked for {j['new']!r}, Shopify assigned {got!r}")
            renamed += 1
            done.append({"title": j["title"][:70], "old": j["old"], "new": got})

            if not args.no_redirects:
                try:
                    http("POST", f"https://{dom}/admin/api/{ver}/redirects.json", tok,
                         {"redirect": {"path": f"/products/{j['old']}",
                                       "target": f"/products/{j['new']}"}})
                    redirected += 1
                except urllib.error.HTTPError as e:
                    # 422 is "path already has a redirect" — the old URL is
                    # already covered, which is the outcome we wanted anyway.
                    if e.code == 422:
                        redirected += 1
                    else:
                        errors.append({"title": j["title"][:70],
                                       "stage": "redirect",
                                       "error": f"{e.code} {e.read().decode()[:150]}"})
        except Exception as e:
            failed += 1
            errors.append({"title": j["title"][:70], "stage": "rename",
                           "old": j["old"], "new": j["new"], "error": str(e)[:200]})
        if n % 25 == 0 or n == len(plan):
            print(f"  [{n}/{len(plan)}] {renamed} renamed, {redirected} redirects, {failed} failed",
                  flush=True)
            flush()
        time.sleep(0.4)

    flush()
    print(f"\n{renamed} handles renamed, {redirected} 301s in place, {failed} failed -> {log.relative_to(REPO)}")


if __name__ == "__main__":
    main()
