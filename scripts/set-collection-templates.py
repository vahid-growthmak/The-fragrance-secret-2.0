#!/usr/bin/env python3
"""Assign the Shop by Category / Shop by Lifestyle theme templates to their collections.

A Shopify collection renders templates/collection.json until its template suffix
is set, which is why those pages still show the default layout even though the
templates are in the theme. This sets the suffix for every collection below in
one run.

Usage
-----
    export SHOPIFY_STORE=your-store.myshopify.com
    export SHOPIFY_ADMIN_TOKEN=shpat_xxxxxxxxxxxxxxxx

    python3 scripts/set-collection-templates.py            # dry run, changes nothing
    python3 scripts/set-collection-templates.py --apply    # write the changes
    python3 scripts/set-collection-templates.py --handles   # list every handle in the store

The token needs the write_products scope (Settings -> Apps and sales channels ->
Develop apps -> Configure Admin API scopes). Nothing is written without --apply.

Requires no third-party packages.
"""

import argparse
import json
import os
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


class Shopify:
    def __init__(self, store, token, api_version):
        self.url = "https://%s/admin/api/%s/graphql.json" % (store, api_version)
        self.token = token

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
            with urllib.request.urlopen(request, timeout=30) as response:
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
    parser.add_argument("--store", default=os.environ.get("SHOPIFY_STORE"),
                        help="myshopify domain, or set SHOPIFY_STORE")
    parser.add_argument("--token", default=os.environ.get("SHOPIFY_ADMIN_TOKEN"),
                        help="Admin API access token, or set SHOPIFY_ADMIN_TOKEN")
    parser.add_argument("--api-version", default="2025-01")
    args = parser.parse_args()

    if not args.store or not args.token:
        sys.exit("Set SHOPIFY_STORE and SHOPIFY_ADMIN_TOKEN (or pass --store / --token). "
                 "See --help.")

    client = Shopify(args.store.replace("https://", "").strip("/"), args.token, args.api_version)
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
