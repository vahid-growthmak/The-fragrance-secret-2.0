#!/usr/bin/env python3
"""Set a collection's image from a local file.

collection.image is what snippets/collection-card.liquid renders for the tiles
on the brands page and the sibling rows on collection pages. It is not the
collection page's own hero — that comes from the hero_bg_image setting in the
collection's JSON template, which deliberately wins over collection.image.

Local files cannot be handed to collectionUpdate directly; it takes a URL, and
a COLLECTION_IMAGE staged-upload target is rejected as an image.src ("Error
updating collection with this image"). The REST endpoint accepts the bytes
inline as a base64 attachment instead, so that is what this uses — picking
smart_collections or custom_collections based on whether the collection has a
rule set.

    python3 scripts/set-collection-image.py --set handle=path/to.png
    python3 scripts/set-collection-image.py --set handle=path/to.png --apply
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
import uuid
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

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


def gql(dom, tok, ver, query, variables=None):
    body = json.dumps({"query": query, "variables": variables or {}}).encode()
    req = urllib.request.Request(f"https://{dom}/admin/api/{ver}/graphql.json", data=body,
                                 method="POST", headers={
                                     "X-Shopify-Access-Token": tok,
                                     "Content-Type": "application/json"})
    for attempt in range(6):
        try:
            d = json.loads(urllib.request.urlopen(req, timeout=120, context=SSL_CTX).read())
            break
        except urllib.error.HTTPError as e:
            if e.code == 429 or (500 <= e.code < 600 and attempt < 5):
                time.sleep(2 ** attempt)
                continue
            raise
        except (urllib.error.URLError, TimeoutError, ConnectionError, ssl.SSLError):
            if attempt == 5:
                raise
            time.sleep(2 ** attempt)
    else:
        raise RuntimeError("retries exhausted")
    if d.get("errors"):
        raise SystemExit(json.dumps(d["errors"])[:600])
    return d["data"]


def post_multipart(url, fields, filename, blob, content_type):
    boundary = f"----tfs{uuid.uuid4().hex}"
    parts = []
    for k, v in fields:
        parts.append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"{k}\"\r\n\r\n{v}\r\n"
                     .encode())
    parts.append(
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; "
        f"filename=\"{filename}\"\r\nContent-Type: {content_type}\r\n\r\n".encode())
    parts.append(blob)
    parts.append(f"\r\n--{boundary}--\r\n".encode())
    body = b"".join(parts)
    req = urllib.request.Request(url, data=body, method="POST", headers={
        "Content-Type": f"multipart/form-data; boundary={boundary}",
        "Content-Length": str(len(body))})
    with urllib.request.urlopen(req, timeout=300, context=SSL_CTX) as r:
        return r.status, r.read()[:300]


COLL_Q = """query($h:String!){ collectionByHandle(handle:$h){
  id title ruleSet{ rules{ column } } image{ url width height altText } } }"""

STAGE = """mutation($input:[StagedUploadInput!]!){ stagedUploadsCreate(input:$input){
  stagedTargets{ url resourceUrl parameters{ name value } } userErrors{ field message } } }"""

UPDATE = """mutation($input:CollectionInput!){ collectionUpdate(input:$input){
  collection{ id image{ url width height altText } } userErrors{ field message } } }"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--set", action="append", required=True, metavar="HANDLE=FILE")
    ap.add_argument("--alt", help="alt text for the image")
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()
    dom, tok, ver = load_env()

    jobs = []
    for spec in args.set:
        if "=" not in spec:
            sys.exit(f"--set needs HANDLE=FILE, got {spec!r}")
        handle, path = spec.split("=", 1)
        f = Path(path)
        if not f.exists():
            sys.exit(f"no such file: {f}")
        c = gql(dom, tok, ver, COLL_Q, {"h": handle})["collectionByHandle"]
        if not c:
            sys.exit(f"no collection with handle {handle!r}")
        cur = c["image"]
        jobs.append({"handle": handle, "file": f, "coll": c})
        print(f"{c['title']}")
        print(f"   current : {cur['width']}x{cur['height']}  "
              f"{cur['url'].split('?')[0].split('/')[-1]}" if cur else "   current : (none)")
        print(f"   new     : {f.name}  ({f.stat().st_size/1024:.0f} KB)")
        print(f"   alt     : {args.alt or '(unchanged)'}\n")

    if not args.apply:
        print("[dry run — nothing uploaded. Re-run with --apply.]")
        return

    print(f"About to set {len(jobs)} collection image(s) on {dom}.")
    if input("Type the store domain to confirm: ").strip() != dom:
        sys.exit("confirmation did not match — nothing changed")

    for j in jobs:
        f, c = j["file"], j["coll"]
        blob = f.read_bytes()
        cid = c["id"].split("/")[-1]
        # A rule set means it is a smart collection; the two REST resources are
        # separate and each rejects the other's id.
        kind = "smart_collections" if c.get("ruleSet") else "custom_collections"
        key = kind[:-1]
        payload = {key: {"id": int(cid),
                         "image": {"attachment": base64.b64encode(blob).decode(),
                                   "filename": f.name}}}
        if args.alt:
            payload[key]["image"]["alt"] = args.alt
        url = f"https://{dom}/admin/api/{ver}/{kind}/{cid}.json"
        req = urllib.request.Request(url, data=json.dumps(payload).encode(), method="PUT",
                                     headers={"X-Shopify-Access-Token": tok,
                                              "Content-Type": "application/json"})
        try:
            body = json.loads(urllib.request.urlopen(req, timeout=300, context=SSL_CTX).read())
        except urllib.error.HTTPError as e:
            print(f"   FAILED {c['title']}: {e.code} {e.read().decode()[:200]}")
            continue
        img = (body.get(key) or {}).get("image") or {}
        print(f"   OK {c['title']} -> {img.get('width')}x{img.get('height')}  "
              f"{str(img.get('src','')).split('?')[0].split('/')[-1]}")
        time.sleep(0.4)

    print("\ndone")


if __name__ == "__main__":
    main()
