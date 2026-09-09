#!/usr/bin/env python3
"""Attach a logo image to brand collections.

brand-chip.liquid renders a logo whenever the collection has an Image set, so
this is the only step needed to make a chip show its mark — no theme change.

    python3 scripts/set-brand-logos.py --dir <folder>            # dry run
    python3 scripts/set-brand-logos.py --dir <folder> --apply    # write

The folder holds one image per collection handle: `chanel.png` sets the logo on
the collection whose handle is `chanel`. PNG, JPG, GIF and WEBP are accepted;
transparent PNG suits the chip, which sits on white.

Writes the `image` field of the named collections and nothing else. Existing
logos are skipped unless --overwrite is passed, so a run cannot silently
replace art a merchant uploaded by hand.
"""

import argparse
import base64
import json
import mimetypes
import os
import ssl
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
OK_EXT = {".png", ".jpg", ".jpeg", ".gif", ".webp"}

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
            r = urllib.request.urlopen(req, timeout=90, context=SSL_CTX)
            return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code == 429:
                time.sleep(float(e.headers.get("Retry-After", 2)))
                continue
            raise
    raise RuntimeError(f"retries exhausted: {url}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True, help="folder of <handle>.<ext> logo files")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--overwrite", action="store_true",
                    help="replace a logo the collection already has")
    args = ap.parse_args()

    dom, tok, ver = load_env()
    files = {p.stem: p for p in sorted(Path(args.dir).iterdir())
             if p.suffix.lower() in OK_EXT}
    if not files:
        sys.exit(f"no usable images in {args.dir}")

    smart = request("GET", f"https://{dom}/admin/api/{ver}/smart_collections.json"
                           f"?limit=250&fields=id,handle,title,image", tok)["smart_collections"]
    custom = request("GET", f"https://{dom}/admin/api/{ver}/custom_collections.json"
                            f"?limit=250&fields=id,handle,title,image", tok)["custom_collections"]
    kind = {c["handle"]: ("smart_collections", c) for c in smart}
    kind.update({c["handle"]: ("custom_collections", c) for c in custom})

    print(f"store : {dom}")
    print(f"source: {args.dir}  ({len(files)} images)\n")

    todo, skip = [], []
    for handle, path in files.items():
        if handle not in kind:
            skip.append((handle, "no such collection")); continue
        endpoint, coll = kind[handle]
        if coll.get("image") and not args.overwrite:
            skip.append((handle, "already has a logo (use --overwrite)")); continue
        todo.append((handle, path, endpoint, coll))

    for handle, path, _, coll in todo:
        print(f"  SET   {handle:<24}{coll['title'][:34]:<36}{path.name}  {path.stat().st_size//1024}KB")
    for handle, why in skip:
        print(f"  skip  {handle:<24}{why}")
    print(f"\n{len(todo)} to set, {len(skip)} skipped")

    if not args.apply:
        print("[dry run — nothing written. Re-run with --apply.]")
        return
    if not todo:
        return

    print(f"\nAbout to write the `image` field on {len(todo)} collections on {dom}.")
    if input("Type the store domain to confirm: ").strip() != dom:
        sys.exit("confirmation did not match — nothing written")

    ok = fail = 0
    for handle, path, endpoint, coll in todo:
        singular = endpoint[:-1]                      # smart_collections -> smart_collection
        payload = {singular: {"id": coll["id"], "image": {
            "attachment": base64.b64encode(path.read_bytes()).decode(),
            "filename": path.name,
            "alt": coll["title"]}}}
        try:
            request("PUT", f"https://{dom}/admin/api/{ver}/{endpoint}/{coll['id']}.json", tok, payload)
            ok += 1
            print(f"  [{ok+fail}/{len(todo)}] set {handle}")
        except urllib.error.HTTPError as e:
            fail += 1
            print(f"  [{ok+fail}/{len(todo)}] FAILED {handle}: {e.code} {e.read().decode()[:120]}")
        time.sleep(0.55)
    print(f"\nset {ok}, failed {fail}")


if __name__ == "__main__":
    main()
