#!/usr/bin/env python3
"""Mirror the live site's product images onto products on this store.

Written for the Paris Collection, which is the default source, but --handles
points it at any product.

This store was built from the catalogue sheet, which carries one image per
product. thefragrancesecrets.com carries the full shoot — 3 to 7 images each,
in a deliberate order with the hero shot first. This copies that set over.

Products default to the paris-collection collection rather than a hardcoded
list, so the set follows the collection if it changes; --handles overrides
that with an explicit comma-separated list. Each is looked up on the live site
by its own handle, which works because the handle rename pass aligned every
product with the sheet's canonical (live) URL.

Images are ingested straight from the live CDN. cdn.shopify.com is public, so
Shopify pulls the file itself; nothing is downloaded and re-uploaded here.

Alt text is deliberately NOT copied wholesale. The SEO import wrote reviewed
alt text from the sheet onto each product's first image, and live's own alt is
worse — three of the four hero images have alt=None, and the rest carry a
trailing "  \n\n". So: the sheet's alt stays on the hero image, and the
remaining images take live's alt with whitespace collapsed, falling back to
the sheet's text when live has none.

Videos are skipped. Two products carry one on live, but a Shopify-hosted video
cannot be copied by URL the way an image can — it needs the source file and a
staged upload. Those are listed at the end rather than silently dropped.

Order of operations matters and is chosen so the product is never left without
images: add the new ones, wait for them to finish processing, then remove the
ones live does not have, then reorder, then set alt text. A failure at any
step leaves a product with more images than it needs, never fewer.

    python3 scripts/sync-paris-images.py                # dry run
    python3 scripts/sync-paris-images.py --apply        # write
    python3 scripts/sync-paris-images.py --apply --keep-extras   # never delete
    python3 scripts/sync-paris-images.py --handles some-product-handle
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
XLSX = REPO / "TFS Final Catalog Sheet - 1_308 ProductsSEO_AEO_GEO Optimized.xlsx"
COLLECTION = "paris-collection"
LIVE = "https://thefragrancesecrets.com"

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


def http(method, url, token=None, payload=None, timeout=90):
    data = json.dumps(payload).encode() if payload is not None else None
    headers = {"Accept": "application/json", "Content-Type": "application/json",
               "User-Agent": "Mozilla/5.0"}
    if token:
        headers["X-Shopify-Access-Token"] = token
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    for attempt in range(6):
        try:
            r = urllib.request.urlopen(req, timeout=timeout, context=SSL_CTX)
            body = r.read()
            return json.loads(body) if body.strip() else {}
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
    d = http("POST", f"https://{dom}/admin/api/{ver}/graphql.json", tok,
             {"query": query, "variables": variables or {}})
    if d.get("errors"):
        raise SystemExit(json.dumps(d["errors"])[:600])
    return d["data"]


def basename(url):
    """CDN filename, without the ?v= cache key."""
    return url.split("?")[0].split("/")[-1]


def ident(url, w, h):
    """Identity that survives Shopify renaming a file on ingest.

    Ingesting an image whose filename already exists in the store's file
    library does not overwrite it — Shopify stores it under a new name and
    appends a uuid, so SAFFEIRE.jpg arrives as
    SAFFEIRE_9ac611a2-de60-4c4f-a76b-2ee5147bf942.jpg. Matching on the raw
    basename then fails, which on the first run made the delete step remove
    images the add step had just created. Strip one trailing uuid or numeric
    suffix and pair the stem with the pixel dimensions instead.
    """
    name = basename(url)
    stem, _, ext = name.rpartition(".")
    stem = (stem or name).lower()
    stem = re.sub(r"_[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", "", stem)
    stem = re.sub(r"_\d+$", "", stem)
    return (stem, ext.lower(), w, h)


def clean_alt(s):
    return re.sub(r"\s+", " ", str(s or "")).strip()


def sheet_alt():
    try:
        import openpyxl
    except ImportError:
        sys.exit("pip install openpyxl")
    wb = openpyxl.load_workbook(XLSX, read_only=True, data_only=True)
    rows = list(wb[wb.sheetnames[0]].iter_rows(values_only=True))
    hdr = [str(h).strip() if h else "" for h in rows[0]]
    idx = {h: i for i, h in enumerate(hdr)}
    out = {}
    for r in rows[1:]:
        if not r or not r[0]:
            continue
        def g(c):
            i = idx.get(c)
            return "" if i is None or i >= len(r) or r[i] is None else str(r[i]).strip()
        h = g("Canonical URL").rstrip("/").split("/")[-1]
        if h:
            out[h] = g("Image Alt Text (SEO)")
    return out


COLL_Q = """query($h:String!){ collectionByHandle(handle:$h){ title
  products(first:100){ nodes{ id handle title
    media(first:50){ nodes{ id mediaContentType
      ... on MediaImage{ alt image{ url width height } } } } } } } }"""

PRODUCT_Q = """query($h:String!){ productByHandle(handle:$h){ id handle title
  media(first:50){ nodes{ id mediaContentType
    ... on MediaImage{ alt image{ url width height } } } } } }"""

CREATE = """mutation($pid:ID!,$m:[CreateMediaInput!]!){
  productCreateMedia(productId:$pid, media:$m){
    media{ ... on MediaImage{ id status } } mediaUserErrors{ field message } } }"""

STATUS_Q = """query($id:ID!){ product(id:$id){ media(first:50){ nodes{
  id status mediaContentType ... on MediaImage{ alt image{ url width height } } } } } }"""

DELETE = """mutation($pid:ID!,$ids:[ID!]!){
  productDeleteMedia(productId:$pid, mediaIds:$ids){ mediaUserErrors{ field message } } }"""

REORDER = """mutation($id:ID!,$moves:[MoveInput!]!){
  productReorderMedia(id:$id, moves:$moves){ mediaUserErrors{ field message } } }"""

SET_ALT = """mutation($pid:ID!,$m:[UpdateMediaInput!]!){
  productUpdateMedia(productId:$pid, media:$m){ mediaUserErrors{ field message } } }"""


def live_images(handle):
    """(images, had_video). Returns None if the product is not on the live site."""
    try:
        d = http("GET", f"{LIVE}/products/{handle}.js", timeout=45)
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None, False
        raise
    imgs, video = [], False
    for m in d.get("media", []):
        if m.get("media_type") != "image":
            video = True
            continue
        imgs.append({"url": m["src"], "alt": clean_alt(m.get("alt")),
                     "name": basename(m["src"]),
                     "ident": ident(m["src"], m.get("width"), m.get("height")),
                     "size": f"{m.get('width')}x{m.get('height')}"})
    return imgs, video


def wait_ready(dom, tok, ver, pid, want, tries=40):
    """Poll until every newly added image leaves PROCESSING."""
    for _ in range(tries):
        nodes = gql(dom, tok, ver, STATUS_Q, {"id": pid})["product"]["media"]["nodes"]
        pending = [n for n in nodes if n.get("status") in ("UPLOADED", "PROCESSING")]
        failed = [n for n in nodes if n.get("status") == "FAILED"]
        if failed:
            return nodes, failed
        if not pending:
            return nodes, []
        time.sleep(3)
    return gql(dom, tok, ver, STATUS_Q, {"id": pid})["product"]["media"]["nodes"], []


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--keep-extras", action="store_true",
                    help="do not delete images the live site does not have")
    ap.add_argument("--handles", help="comma-separated product handles to sync "
                                      "instead of a collection's contents")
    ap.add_argument("--collection", default=COLLECTION,
                    help=f"collection handle to sync (default {COLLECTION})")
    args = ap.parse_args()
    dom, tok, ver = load_env()
    alts = sheet_alt()

    print(f"store      : {dom}")
    if args.handles:
        targets = []
        for h in [x.strip() for x in args.handles.split(",") if x.strip()]:
            d = gql(dom, tok, ver, PRODUCT_Q, {"h": h})["productByHandle"]
            if not d:
                sys.exit(f"no product on this store with handle {h!r}")
            targets.append(d)
        print(f"products   : {len(targets)} named on the command line")
    else:
        coll = gql(dom, tok, ver, COLL_Q, {"h": args.collection})["collectionByHandle"]
        if not coll:
            sys.exit(f"no collection with handle {args.collection!r}")
        targets = coll["products"]["nodes"]
        print(f"collection : {coll['title']}  ({len(targets)} products)")
    print(f"source     : {LIVE}\n")

    jobs, no_live, videos = [], [], []
    for p in targets:
        imgs, had_video = live_images(p["handle"])
        if imgs is None:
            no_live.append(p)
            continue
        if had_video:
            videos.append(p["handle"])
        have = [m for m in p["media"]["nodes"] if m["mediaContentType"] == "IMAGE"]
        have_id = {}
        for m in have:
            im = m.get("image") or {}
            have_id[ident(im.get("url", ""), im.get("width"), im.get("height"))] = m
        want_id = {i["ident"] for i in imgs}
        add = [i for i in imgs if i["ident"] not in have_id]
        drop = [m for k, m in have_id.items() if k not in want_id]
        print(f"{p['title'][:64]}")
        print(f"   dev has {len(have)}   live has {len(imgs)}"
              f"   -> add {len(add)}, remove {0 if args.keep_extras else len(drop)}")
        for i in add:
            print(f"      + {i['size']:>10}  {i['name'][:62]}")
        for m in drop:
            mark = "keep" if args.keep_extras else "-   "
            print(f"      {mark} {basename((m.get('image') or {}).get('url',''))[:62]}")
        # Queued even when add and drop are both empty: order and alt text
        # still get reconciled against live.
        jobs.append({"p": p, "imgs": imgs, "add": add,
                     "drop": [] if args.keep_extras else drop})
        print()

    for p in no_live:
        print(f"SKIP  {p['title'][:60]}\n      /products/{p['handle']} is 404 on the live site")
    if videos:
        print(f"\nNOTE  these carry a video on live that is not copied (needs a file "
              f"upload, not a URL): {', '.join(videos)}")

    total_add = sum(len(j["add"]) for j in jobs)
    total_drop = sum(len(j["drop"]) for j in jobs)
    print(f"\nimages to add: {total_add}   images to remove: {total_drop}")

    if not args.apply:
        print("\n[dry run — nothing changed. Re-run with --apply.]")
        return
    if not total_add and not total_drop:
        print("nothing to do")
        return

    print(f"\nAbout to change product images on {dom}.")
    if input("Type the store domain to confirm: ").strip() != dom:
        sys.exit("confirmation did not match — nothing changed")

    for j in jobs:
        p, imgs = j["p"], j["imgs"]
        pid, handle = p["id"], p["handle"]
        print(f"\n{p['title'][:64]}")

        created = {}
        if j["add"]:
            res = gql(dom, tok, ver, CREATE, {"pid": pid, "m": [
                {"originalSource": i["url"], "mediaContentType": "IMAGE",
                 "alt": i["alt"][:512]} for i in j["add"]]})["productCreateMedia"]
            errs = res.get("mediaUserErrors") or []
            if errs:
                print(f"   ADD FAILED: {errs[:2]}")
                continue
            # The response comes back in the order requested, so this pins each
            # live image to the media it produced. Never re-derive it from the
            # filename: Shopify may have renamed the file on ingest.
            for i, m in zip(j["add"], res.get("media") or []):
                created[i["ident"]] = m["id"]
            print(f"   added {len(j['add'])}, waiting for processing…")
            nodes, failed = wait_ready(dom, tok, ver, pid, len(j["add"]))
            if failed:
                print(f"   {len(failed)} image(s) FAILED to process — leaving this product alone")
                continue
        else:
            nodes = gql(dom, tok, ver, STATUS_Q, {"id": pid})["product"]["media"]["nodes"]

        def index(nodes):
            out = {}
            for n in nodes:
                if n["mediaContentType"] != "IMAGE":
                    continue
                im = n.get("image") or {}
                out.setdefault(ident(im.get("url", ""), im.get("width"), im.get("height")), n)
            return out
        by_id = index(nodes)

        # Delete exactly what the plan identified, by id. Recomputing the set
        # here is what deleted freshly added images on the first run.
        ids = [m["id"] for m in j["drop"]]
        if ids:
            res = gql(dom, tok, ver, DELETE, {"pid": pid, "ids": ids})["productDeleteMedia"]
            errs = res.get("mediaUserErrors") or []
            print(f"   removed {len(ids)}" + (f"  errors {errs[:2]}" if errs else ""))
            nodes = gql(dom, tok, ver, STATUS_Q, {"id": pid})["product"]["media"]["nodes"]
            by_id = index(nodes)

        node_by_gid = {n["id"]: n for n in nodes}
        def resolve(i):
            n = by_id.get(i["ident"])
            return n or node_by_gid.get(created.get(i["ident"]))

        moves = []
        for pos, i in enumerate(imgs):
            n = resolve(i)
            if n:
                moves.append({"id": n["id"], "newPosition": str(pos)})
        if moves:
            res = gql(dom, tok, ver, REORDER, {"id": pid, "moves": moves})["productReorderMedia"]
            errs = res.get("mediaUserErrors") or []
            print(f"   reordered {len(moves)}" + (f"  errors {errs[:2]}" if errs else ""))

        hero = alts.get(handle, "")
        updates = []
        for pos, i in enumerate(imgs):
            n = resolve(i)
            if not n:
                continue
            want = (hero if pos == 0 and hero else (i["alt"] or hero))
            if want and clean_alt(n.get("alt")) != want:
                updates.append({"id": n["id"], "alt": want[:512]})
        if updates:
            res = gql(dom, tok, ver, SET_ALT, {"pid": pid, "m": updates})["productUpdateMedia"]
            errs = res.get("mediaUserErrors") or []
            print(f"   alt text set on {len(updates)}" + (f"  errors {errs[:2]}" if errs else ""))
        time.sleep(0.4)

    print("\ndone")


if __name__ == "__main__":
    main()
