#!/usr/bin/env python3
"""Mint a fresh Admin API token from the custom app's client credentials.

The live store's app issues tokens through the client_credentials grant, and
those expire after 24 hours. Every other script here reads a static
SHOPIFY_ADMIN_ACCESS_TOKEN from .env, so rather than teaching each of them to
refresh, this mints a token and rewrites that one line in place.

Run it whenever a script starts returning 401.

    python3 scripts/refresh-token.py            # refresh for SHOPIFY_STORE_DOMAIN
    python3 scripts/refresh-token.py --check    # report status, write nothing
"""

import argparse
import json
import re
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
ENV = REPO / ".env"

try:
    import certifi
    SSL_CTX = ssl.create_default_context(cafile=certifi.where())
except ImportError:
    SSL_CTX = ssl.create_default_context()


def read_env():
    env = {}
    for line in ENV.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if s and not s.startswith("#") and "=" in s:
            k, v = s.split("=", 1)
            env[k.strip()] = v.strip()
    return env


def mint(shop, cid, secret):
    body = urllib.parse.urlencode({"client_id": cid, "client_secret": secret,
                                   "grant_type": "client_credentials"}).encode()
    req = urllib.request.Request(f"https://{shop}/admin/oauth/access_token", data=body,
                                 method="POST", headers={
                                     "Content-Type": "application/x-www-form-urlencoded",
                                     "Accept": "application/json"})
    return json.loads(urllib.request.urlopen(req, timeout=45, context=SSL_CTX).read())


def token_alive(shop, token, ver):
    req = urllib.request.Request(f"https://{shop}/admin/api/{ver}/shop.json",
                                 headers={"X-Shopify-Access-Token": token,
                                          "Accept": "application/json"})
    try:
        d = json.loads(urllib.request.urlopen(req, timeout=30, context=SSL_CTX).read())
        return True, d["shop"]["name"]
    except urllib.error.HTTPError as e:
        return False, f"HTTP {e.code}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="report only, do not write")
    args = ap.parse_args()

    env = read_env()
    shop = env.get("SHOPIFY_STORE_DOMAIN", "").replace("https://", "").replace("http://", "").strip("/")
    ver = env.get("SHOPIFY_API_VERSION", "2024-10")
    cid, secret = env.get("SHOPIFY_CLIENT_ID", ""), env.get("SHOPIFY_CLIENT_SECRET", "")
    cur = env.get("SHOPIFY_ADMIN_ACCESS_TOKEN", "")
    if not shop:
        sys.exit("SHOPIFY_STORE_DOMAIN is not set")

    print(f"store : {shop}")
    if cur:
        ok, who = token_alive(shop, cur, ver)
        print(f"token : {'valid — ' + who if ok else 'REJECTED (' + who + ')'}")
        if ok and args.check:
            return
    else:
        print("token : none set")

    if not cid or not secret:
        sys.exit("SHOPIFY_CLIENT_ID / SHOPIFY_CLIENT_SECRET are needed to mint a token")
    if args.check:
        print("[--check: not minting]")
        return

    try:
        d = mint(shop, cid, secret)
    except urllib.error.HTTPError as e:
        sys.exit(f"grant failed: HTTP {e.code} {e.read().decode()[:200]}")
    tok, exp = d["access_token"], d.get("expires_in")
    ok, who = token_alive(shop, tok, ver)
    if not ok:
        sys.exit(f"minted a token but it does not work: {who}")

    text = ENV.read_text(encoding="utf-8")
    if re.search(r"^SHOPIFY_ADMIN_ACCESS_TOKEN=.*$", text, flags=re.M):
        text = re.sub(r"^SHOPIFY_ADMIN_ACCESS_TOKEN=.*$",
                      f"SHOPIFY_ADMIN_ACCESS_TOKEN={tok}", text, flags=re.M)
    else:
        text += f"\nSHOPIFY_ADMIN_ACCESS_TOKEN={tok}\n"
    ENV.write_text(text, encoding="utf-8")
    when = time.strftime("%H:%M on %d %b", time.localtime(time.time() + (exp or 0)))
    print(f"minted: {tok[:10]}…  valid for {exp}s (until about {when})")
    print(f"written to .env — verified against {who}")


if __name__ == "__main__":
    main()
