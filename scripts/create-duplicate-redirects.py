#!/usr/bin/env python3
"""Create the three 301s for the duplicate Bath & Body Works body creams.

Three products were listed as duplicated, each with a URL to keep and a URL to
retire:

    Touch of Gold           .../touch-of-gold-body-cream-226g-for-women-fruity-floral-tonka-body-cream
                         -> .../touch-of-gold-body-cream-fruity-floral-tonka
    Vanilla Romance         .../vanilla-romance-body-cream-226g-for-women-vanilla-woody-body-cream
                         -> .../vanilla-romance-body-cream-vanilla-cardamom-woods
    Japanese Cherry Blossom .../japanese-cherry-blossom-body-cream-226g-for-women-floral-fruity-musk
                         -> .../japanese-cherry-blossom-body-cream-226g-for-women-floral-fruity-body-cream

The duplicates themselves do not exist on this store. It was built from the
1,308-row catalogue sheet, which carries one row per product, so there is
nothing here to delete — the duplication is on the live site. The redirects
are still worth creating now: those old URLs are indexed against the live
domain, and when this store takes that domain over they need somewhere to
land. Creating them here means they are already in place on the changeover
rather than being remembered afterwards.

Two checks before each write, because a bad redirect is worse than none:

  1. The KEEP handle must resolve to a real product. A 301 into a 404 turns a
     recoverable dead link into a redirect chain that ends nowhere.
  2. The DELETE handle must NOT be a real product. Shopify URL redirects take
     precedence over the resource at that path, so a redirect installed over a
     live product would silently hide it.

Anything failing either check is reported and skipped, never written.

    python3 scripts/create-duplicate-redirects.py          # dry run
    python3 scripts/create-duplicate-redirects.py --apply  # write
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
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

# (label, keep handle, handle to retire)
PAIRS = [
    ("Touch of Gold Body Cream",
     "bath-body-works-touch-of-gold-body-cream-fruity-floral-tonka",
     "bath-body-works-touch-of-gold-body-cream-226g-for-women-fruity-floral-tonka-body-cream"),
    ("Vanilla Romance Body Cream",
     "bath-body-works-vanilla-romance-body-cream-vanilla-cardamom-woods",
     "bath-body-works-vanilla-romance-body-cream-226g-for-women-vanilla-woody-body-cream"),
    ("Japanese Cherry Blossom Body Cream",
     "bath-body-works-japanese-cherry-blossom-body-cream-226g-for-women-floral-fruity-body-cream",
     "bath-body-works-japanese-cherry-blossom-body-cream-226g-for-women-floral-fruity-musk"),
]

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
    for attempt in range(6):
        try:
            r = urllib.request.urlopen(req, timeout=90, context=SSL_CTX)
            body = r.read()
            return (json.loads(body) if body.strip() else {}), r.headers
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
    raise RuntimeError(f"retries exhausted: {url}")


def gql(dom, tok, ver, query, variables=None):
    body, _ = http("POST", f"https://{dom}/admin/api/{ver}/graphql.json", tok,
                   {"query": query, "variables": variables or {}})
    if body.get("errors"):
        raise SystemExit(json.dumps(body["errors"])[:500])
    return body["data"]


BY_HANDLE = "query($h:String!){ productByHandle(handle:$h){ id title status } }"


def all_redirects(dom, tok, ver):
    out, url = [], f"https://{dom}/admin/api/{ver}/redirects.json?limit=250"
    while url:
        body, headers = http("GET", url, tok)
        out += body.get("redirects", [])
        m = re.search(r'<([^>]+)>;\s*rel="next"', headers.get("Link", ""))
        url = m.group(1) if m else None
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()
    dom, tok, ver = load_env()

    existing = {r["path"]: r for r in all_redirects(dom, tok, ver)}
    print(f"store : {dom}")
    print(f"redirects already present : {len(existing)}\n")

    todo, skip = [], []
    for label, keep, retire in PAIRS:
        path, target = f"/products/{retire}", f"/products/{keep}"
        kp = gql(dom, tok, ver, BY_HANDLE, {"h": keep})["productByHandle"]
        rp = gql(dom, tok, ver, BY_HANDLE, {"h": retire})["productByHandle"]

        print(f"{label}")
        print(f"  keep    {keep[:76]}")
        print(f"          {'OK — ' + kp['title'][:56] if kp else 'MISSING on this store'}")
        print(f"  retire  {retire[:76]}")
        print(f"          {'still a live product' if rp else 'not on this store (nothing to delete)'}")

        if not kp:
            skip.append((label, "the KEEP handle does not resolve — refusing a 301 into a 404"))
        elif rp:
            skip.append((label, "the RETIRE handle is a live product — a redirect would hide it"))
        elif path in existing:
            cur = existing[path]["target"]
            if cur == target:
                print("  -> 301 already in place")
            else:
                todo.append((label, path, target, existing[path]["id"], cur))
                print(f"  -> 301 exists but points at {cur[:50]} — will repoint")
        else:
            todo.append((label, path, target, None, None))
            print("  -> 301 to create")
        print()

    for label, why in skip:
        print(f"SKIP  {label}: {why}")
    print(f"\nredirects to write : {len(todo)}")

    if not args.apply:
        print("\n[dry run — nothing written. Re-run with --apply.]")
        return
    if not todo:
        print("nothing to do")
        return

    print(f"\nAbout to write {len(todo)} redirects on {dom}.")
    if input("Type the store domain to confirm: ").strip() != dom:
        sys.exit("confirmation did not match — nothing written")

    ok = fail = 0
    for label, path, target, rid, _old in todo:
        try:
            if rid:
                http("PUT", f"https://{dom}/admin/api/{ver}/redirects/{rid}.json", tok,
                     {"redirect": {"id": rid, "path": path, "target": target}})
            else:
                http("POST", f"https://{dom}/admin/api/{ver}/redirects.json", tok,
                     {"redirect": {"path": path, "target": target}})
            ok += 1
            print(f"  OK   {label}")
        except urllib.error.HTTPError as e:
            fail += 1
            print(f"  FAIL {label}: {e.code} {e.read().decode()[:160]}")
        time.sleep(0.4)
    print(f"\n{ok} written, {fail} failed")


if __name__ == "__main__":
    main()
