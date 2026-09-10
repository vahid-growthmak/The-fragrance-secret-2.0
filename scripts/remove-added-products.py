#!/usr/bin/env python3
"""Delete the products created by add-missing-products.py.

The set is taken from products-added-to-dev-store.csv, which is the list that
was computed *before* creation and so is authoritative — scripts/created-
products.json holds only 187 of the 189, having been overwritten by the main
run after the two-product smoke test.

Deletion in Shopify is permanent, so this refuses to touch anything it cannot
positively identify as one of ours:

  - the handle must appear in the CSV;
  - the product must still carry the exact handle recorded there;
  - created_at must fall inside --max-age-days (default 3), which is what
    separates a product this tool made from a pre-existing one that happens
    to share a handle.

Anything failing a check is reported and skipped, never deleted.

    python3 scripts/remove-added-products.py            # dry run
    python3 scripts/remove-added-products.py --apply    # delete (confirms first)
    python3 scripts/remove-added-products.py --archive  # set status=archived instead
"""

import argparse
import csv
import json
import os
import re
import ssl
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
CSV_PATH = REPO / "products-added-to-dev-store.csv"

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
    for _ in range(6):
        try:
            r = urllib.request.urlopen(req, timeout=60, context=SSL_CTX)
            body = r.read()
            return (json.loads(body) if body.strip() else {}), r.headers
        except urllib.error.HTTPError as e:
            if e.code == 429:
                time.sleep(float(e.headers.get("Retry-After", 2)))
                continue
            raise
    raise RuntimeError(f"retries exhausted: {url}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--archive", action="store_true",
                    help="archive instead of deleting (reversible)")
    ap.add_argument("--max-age-days", type=float, default=3.0)
    args = ap.parse_args()

    dom, tok, ver = load_env()
    wanted = {r["handle"].strip() for r in csv.DictReader(CSV_PATH.open(encoding="utf-8"))
              if r.get("handle", "").strip()}
    print(f"store  : {dom}")
    print(f"list   : {CSV_PATH.name}  ({len(wanted)} handles)")
    print(f"action : {'ARCHIVE' if args.archive else 'DELETE'}\n")

    # index the store once
    live, url = {}, (f"https://{dom}/admin/api/{ver}/products.json"
                     f"?limit=250&fields=id,handle,title,created_at,status")
    while url:
        body, headers = request("GET", url, tok)
        for p in body["products"]:
            live[p["handle"]] = p
        m = re.search(r'<([^>]+)>;\s*rel="next"', headers.get("Link", ""))
        url = m.group(1) if m else None
    print(f"store holds {len(live)} products")

    cutoff = datetime.now(timezone.utc) - timedelta(days=args.max_age_days)
    todo, gone, refused = [], [], []
    for h in sorted(wanted):
        p = live.get(h)
        if not p:
            gone.append(h)
            continue
        created = datetime.fromisoformat(p["created_at"].replace("Z", "+00:00"))
        if created < cutoff:
            refused.append((h, f"created {created:%Y-%m-%d %H:%M} — older than {args.max_age_days}d"))
            continue
        todo.append(p)

    print(f"  to {'archive' if args.archive else 'delete'} : {len(todo)}")
    print(f"  already absent    : {len(gone)}")
    print(f"  REFUSED (too old) : {len(refused)}")
    for h, why in refused:
        print(f"      {h[:60]}  {why}")
    if todo:
        print("\n  first 5:")
        for p in todo[:5]:
            print(f"      {p['id']}  {p['created_at'][:19]}  {p['title'][:56]}")

    if not args.apply:
        print("\n[dry run — nothing removed. Re-run with --apply.]")
        return
    if not todo:
        print("\nnothing to do")
        return

    verb = "ARCHIVE" if args.archive else "PERMANENTLY DELETE"
    print(f"\nAbout to {verb} {len(todo)} products on {dom}.")
    if not args.archive:
        print("Deletion cannot be undone.")
    if input("Type the store domain to confirm: ").strip() != dom:
        sys.exit("confirmation did not match — nothing removed")

    ok = fail = 0
    log = []
    for n, p in enumerate(todo, 1):
        try:
            if args.archive:
                request("PUT", f"https://{dom}/admin/api/{ver}/products/{p['id']}.json", tok,
                        {"product": {"id": p["id"], "status": "archived"}})
            else:
                request("DELETE", f"https://{dom}/admin/api/{ver}/products/{p['id']}.json", tok)
            ok += 1
            log.append({"id": p["id"], "handle": p["handle"], "title": p["title"]})
            print(f"  [{n}/{len(todo)}] {'archived' if args.archive else 'deleted'} {p['handle'][:58]}")
        except urllib.error.HTTPError as e:
            fail += 1
            print(f"  [{n}/{len(todo)}] FAILED {p['handle'][:50]}: {e.code} {e.read().decode()[:120]}")
        time.sleep(0.55)

    out = REPO / "scripts" / "removed-products.json"
    out.write_text(json.dumps({"action": "archive" if args.archive else "delete",
                               "removed": log}, indent=1), encoding="utf-8")
    print(f"\n{'archived' if args.archive else 'deleted'} {ok}, failed {fail} -> {out}")


if __name__ == "__main__":
    main()
