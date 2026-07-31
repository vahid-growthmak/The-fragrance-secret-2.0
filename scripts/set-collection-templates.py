#!/usr/bin/env python3
"""Assign the Shop by Category / Shop by Lifestyle theme templates to their collections.

A Shopify collection renders templates/collection.json until its template suffix
is set, which is why those pages still show the default layout even though the
templates are in the theme. This sets the suffix for every collection below in
one run.

Usage
-----
    python3 scripts/set-collection-templates.py            # dry run, changes nothing
    python3 scripts/set-collection-templates.py --apply    # write the changes
    python3 scripts/set-collection-templates.py --handles   # list every handle in the store

Credentials are read from .env in the repo root (gitignored), falling back to
the environment:

    SHOPIFY_STORE_DOMAIN / SHOPIFY_STORE               your-store.myshopify.com
    SHOPIFY_ADMIN_ACCESS_TOKEN / SHOPIFY_ADMIN_TOKEN   shpat_xxxxxxxxxxxxxxxx
    SHOPIFY_API_VERSION                                optional, defaults below

The token needs the write_products scope (Settings -> Apps and sales channels ->
Develop apps -> Configure Admin API scopes). Nothing is written without --apply.

Requires no third-party packages.
"""

import argparse
import json
import os
import ssl
import sys
import time
import urllib.error
import urllib.request

# collection handle -> templates/collection.<suffix>.json
TEMPLATES = {
    # Shop by Category
    "mens": "mens",
    "womens": "womens",
    "unisex": "unisex",
    "kids": "kids",
    "luxury": "luxury",
    "arabic": "arabic",
    "attar": "attar",
    "perfume-oil": "perfume-oil",
    "inspired": "inspired",
    "miracle-plant": "miracle-plant",
    # Shop by Lifestyle
    "everyday-signature": "everyday-signature",
    "office-wear": "office-wear",
    "date-night": "date-night",
    "party-clubbing": "party-clubbing",
    "wedding": "wedding",
    "wedding-formal": "wedding-formal",
    "dinner-evening": "dinner-evening",
    "gym": "gym",
    "travel-friendly": "travel-friendly",
    "beach-vacation": "beach-vacation",
    "vacation-beach": "vacation-beach",
    # Shop by Climate
    "summer-wear": "summer-wear",
    "winter-holiday": "winter-holiday",
    "spring-bloom": "spring-bloom",
    "rainy-day": "rainy-day",
    "humid-weather": "humid-weather",
    "tropical-climate": "tropical-climate",
    "desert-climate": "desert-climate",
    "hot-weather": "hot-weather",
    "cold-weather": "cold-weather",
    "dry-weather": "dry-weather",
}

LOOKUP_QUERY = """
query CollectionsByHandle($q: String!) {
  collections(first: 250, query: $q) {
    nodes { id handle title templateSuffix }
  }
}
"""

ALL_HANDLES_QUERY = """
query AllCollections($after: String) {
  collections(first: 250, after: $after) {
    nodes { handle title templateSuffix }
    pageInfo { hasNextPage endCursor }
  }
}
"""

UPDATE_MUTATION = """
mutation SetTemplate($input: CollectionInput!) {
  collectionUpdate(input: $input) {
    collection { handle templateSuffix }
    userErrors { field message }
  }
}
"""

GREEN, YELLOW, RED, DIM, RESET = "\033[32m", "\033[33m", "\033[31m", "\033[2m", "\033[0m"

DEFAULT_API_VERSION = "2025-01"


def load_dotenv():
    """Read .env from the repo root without clobbering real environment vars."""
    path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
    values = {}
    if not os.path.exists(path):
        return values
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            values[key.strip()] = value.strip().strip("'\"")
    return values


def credential(dotenv, *names):
    for name in names:
        value = os.environ.get(name) or dotenv.get(name)
        if value:
            return value
    return None


def ssl_context():
    """Some macOS Pythons ship without a usable CA bundle; find one rather than
    disabling verification."""
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        pass
    if not ssl.create_default_context().cert_store_stats()["x509_ca"]:
        for candidate in ("/etc/ssl/cert.pem", "/usr/local/etc/openssl@3/cert.pem",
                          "/opt/homebrew/etc/openssl@3/cert.pem", "/etc/pki/tls/certs/ca-bundle.crt"):
            if os.path.exists(candidate):
                return ssl.create_default_context(cafile=candidate)
    return ssl.create_default_context()


def pin_host(hostname, address):
    """Work around a local resolver that NXDOMAINs a host public DNS resolves
    fine. TLS still verifies the certificate against the hostname."""
    import socket
    original = socket.getaddrinfo

    def patched(host, port, *args, **kwargs):
        if host == hostname:
            host = address
        return original(host, port, *args, **kwargs)

    socket.getaddrinfo = patched


class Shopify:
    def __init__(self, store, token, api_version):
        self.url = "https://%s/admin/api/%s/graphql.json" % (store, api_version)
        self.token = token
        self.ssl = ssl_context()

    def call(self, query, variables=None):
        payload = json.dumps({"query": query, "variables": variables or {}}).encode()
        request = urllib.request.Request(
            self.url,
            data=payload,
            headers={
                "Content-Type": "application/json",
                "X-Shopify-Access-Token": self.token,
                "Accept": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=30, context=self.ssl) as response:
                body = json.loads(response.read().decode())
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode(errors="replace")[:400]
            sys.exit("%sHTTP %s from Shopify: %s%s" % (RED, exc.code, detail, RESET))
        except urllib.error.URLError as exc:
            sys.exit("%sCould not reach %s: %s%s" % (RED, self.url, exc.reason, RESET))

        if body.get("errors"):
            sys.exit("%sGraphQL error: %s%s" % (RED, json.dumps(body["errors"], indent=2), RESET))
        return body["data"]


def list_all_handles(client):
    cursor, rows = None, []
    while True:
        data = client.call(ALL_HANDLES_QUERY, {"after": cursor})["collections"]
        rows.extend(data["nodes"])
        if not data["pageInfo"]["hasNextPage"]:
            break
        cursor = data["pageInfo"]["endCursor"]

    print("%d collections in the store:\n" % len(rows))
    for row in sorted(rows, key=lambda r: r["handle"]):
        suffix = row["templateSuffix"] or "-"
        print("  %-34s %-40s template: %s" % (row["handle"], row["title"][:40], suffix))
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--apply", action="store_true",
                        help="write the changes (default is a dry run)")
    parser.add_argument("--handles", action="store_true",
                        help="just list every collection handle in the store and exit")
    parser.add_argument("--store", help="myshopify domain (defaults to .env SHOPIFY_STORE_DOMAIN)")
    parser.add_argument("--token", help="Admin API token (defaults to .env SHOPIFY_ADMIN_ACCESS_TOKEN)")
    parser.add_argument("--api-version", help="defaults to .env SHOPIFY_API_VERSION or %s" % DEFAULT_API_VERSION)
    parser.add_argument("--resolve-ip", help="connect to this IP for the store host, for when the "
                                             "local resolver fails on a name public DNS resolves")
    args = parser.parse_args()

    dotenv = load_dotenv()
    store = args.store or credential(dotenv, "SHOPIFY_STORE_DOMAIN", "SHOPIFY_STORE")
    token = args.token or credential(dotenv, "SHOPIFY_ADMIN_ACCESS_TOKEN", "SHOPIFY_ADMIN_TOKEN")
    api_version = args.api_version or credential(dotenv, "SHOPIFY_API_VERSION") or DEFAULT_API_VERSION

    if not store or not token:
        sys.exit("No credentials found. Add SHOPIFY_STORE_DOMAIN and SHOPIFY_ADMIN_ACCESS_TOKEN to "
                 ".env, or pass --store / --token. See --help.")

    args.api_version = api_version
    host = store.replace("https://", "").replace("http://", "").strip("/")
    if args.resolve_ip:
        pin_host(host, args.resolve_ip)
    client = Shopify(host, token, api_version)
    args.store = host
    print("%sStore:%s %s   %sAPI:%s %s\n" % (DIM, RESET, args.store, DIM, RESET, args.api_version))

    if args.handles:
        list_all_handles(client)
        return

    query = " OR ".join("handle:%s" % handle for handle in TEMPLATES)
    found = {node["handle"]: node for node in client.call(LOOKUP_QUERY, {"q": query})["collections"]["nodes"]}

    planned, already, missing = [], [], []
    for handle, suffix in TEMPLATES.items():
        node = found.get(handle)
        if node is None:
            missing.append(handle)
        elif node["templateSuffix"] == suffix:
            already.append(handle)
        else:
            planned.append((node, suffix))

    for node, suffix in planned:
        current = node["templateSuffix"] or "collection (default)"
        print("  %s->%s %-24s %s  ->  %s" % (YELLOW, RESET, node["handle"], current, suffix))
    for handle in already:
        print("  %s ok %s %-24s already on %s" % (GREEN, RESET, handle, TEMPLATES[handle]))
    for handle in missing:
        print("  %s !! %s %-24s no collection with this handle" % (RED, RESET, handle))

    print("\n%d to change, %d already correct, %d handles not found"
          % (len(planned), len(already), len(missing)))

    if missing:
        print("\n%sRun with --handles to see the store's real handles, then update TEMPLATES\n"
              "at the top of this script (and rename the matching templates/collection.*.json\n"
              "so the names still line up).%s" % (DIM, RESET))

    if not planned:
        return

    if not args.apply:
        print("\n%sDry run — nothing written. Re-run with --apply to make these changes.%s"
              % (DIM, RESET))
        return

    print("\nApplying...")
    failures = 0
    for node, suffix in planned:
        result = client.call(UPDATE_MUTATION,
                             {"input": {"id": node["id"], "templateSuffix": suffix}})["collectionUpdate"]
        errors = result["userErrors"]
        if errors:
            failures += 1
            print("  %s !! %s %-24s %s" % (RED, RESET, node["handle"],
                                           "; ".join(e["message"] for e in errors)))
        else:
            print("  %s ok %s %-24s -> %s" % (GREEN, RESET, node["handle"],
                                              result["collection"]["templateSuffix"]))
        time.sleep(0.2)  # stay well inside the GraphQL cost bucket

    print("\n%d updated, %d failed" % (len(planned) - failures, failures))
    if failures:
        sys.exit(1)


if __name__ == "__main__":
    main()
