#!/usr/bin/env python3
"""Create the 301s for products whose handles were renamed.

scripts/handle-rename-run.json recorded renaming 333 products and creating 333
redirects. The redirects are not on this store — that run was against the dev
store, and only the products came across. So 333 URLs that were indexed under
the old handles now return 404 on the live domain.

Every redirect is checked from both ends before it is written, because a bad
redirect is worse than a 404:

  * no product may still hold the old handle. If one does, the old URL is a
    live page and a redirect would shadow it — a page lost, not saved.
  * a product must hold the new handle. A 301 into a 404 turns one dead URL
    into two and tells search engines the dead end is canonical.
  * the store must not already redirect that path, whatever the target.

Both checks read the store's own handles rather than fetching the storefront.
An earlier version asked the live site and was rate-limited into answering 429
for almost everything, which is indistinguishable from "a page is there" unless
you are careful — and being wrong in that direction silently shadows live pages.
One paginated query settles it for every product at once.

    python3 scripts/create-rename-redirects.py                 # dry run
    python3 scripts/create-rename-redirects.py --apply
    python3 scripts/create-rename-redirects.py --limit 20 --apply

Nothing is written without --apply.
"""

import argparse
import importlib.util
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location(
    "sct", os.path.join(HERE, "set-collection-templates.py"))
sct = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sct)

GREEN, YELLOW, RED, DIM, RESET = sct.GREEN, sct.YELLOW, sct.RED, sct.DIM, sct.RESET

HANDLES = """
query($cursor: String) {
  products(first: 250, after: $cursor) {
    pageInfo { hasNextPage endCursor }
    nodes { handle status }
  }
}
"""

REDIRECTS = """
query($cursor: String) {
  urlRedirects(first: 250, after: $cursor) {
    pageInfo { hasNextPage endCursor }
    nodes { path target }
  }
}
"""

CREATE = """
mutation($redirect: UrlRedirectInput!) {
  urlRedirectCreate(urlRedirect: $redirect) {
    urlRedirect { id path target }
    userErrors { field message }
  }
}
"""


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--limit", type=int, help="only handle the first N (for a cautious first run)")
    parser.add_argument("--apply", action="store_true", help="actually create them")
    args = parser.parse_args()

    dotenv = sct.load_dotenv()
    store = sct.credential(dotenv, "SHOPIFY_STORE_DOMAIN")
    token = sct.credential(dotenv, "SHOPIFY_ADMIN_ACCESS_TOKEN")
    version = sct.credential(dotenv, "SHOPIFY_API_VERSION") or sct.DEFAULT_API_VERSION
    if not store or not token:
        sys.exit("%sMissing credentials in .env%s" % (RED, RESET))

    client = sct.Shopify(store, token, version)
    shop = client.call("{ shop { name primaryDomain { url } } }")["shop"]
    domain = shop["primaryDomain"]["url"].rstrip("/")
    print("%sStore%s %s (%s)" % (DIM, RESET, shop["name"], domain))
    print("%sMode %s %s\n" % (DIM, RESET,
                              (GREEN + "APPLY" + RESET) if args.apply else (YELLOW + "dry run" + RESET)))

    with open(os.path.join(HERE, "handle-rename-run.json"), encoding="utf-8") as handle:
        renames = [r for r in json.load(handle).get("done", [])
                   if r.get("old") and r.get("new") and r["old"] != r["new"]]

    cursor, existing = None, set()
    while True:
        page = client.call(REDIRECTS, {"cursor": cursor})["urlRedirects"]
        existing.update(node["path"] for node in page["nodes"])
        if not page["pageInfo"]["hasNextPage"]:
            break
        cursor = page["pageInfo"]["endCursor"]

    pending = [r for r in renames if "/products/%s" % r["old"] not in existing]
    if args.limit:
        pending = pending[:args.limit]
    print("%s%d renames, %d already redirected, %d to check%s\n"
          % (DIM, len(renames), len(renames) - len([r for r in renames
                                                    if "/products/%s" % r["old"] not in existing]),
             len(pending), RESET))

    cursor, handles = None, {}
    while True:
        page = client.call(HANDLES, {"cursor": cursor})["products"]
        for node in page["nodes"]:
            handles[node["handle"]] = node["status"]
        if not page["pageInfo"]["hasNextPage"]:
            break
        cursor = page["pageInfo"]["endCursor"]
    print("%s%d product handles on the store%s\n" % (DIM, len(handles), RESET))

    create, skip = [], []
    for row in pending:
        old_path = "/products/%s" % row["old"]
        new_path = "/products/%s" % row["new"]
        if row["old"] in handles:
            skip.append((old_path, "a product still holds this handle — redirect would shadow it"))
        elif row["new"] not in handles:
            skip.append((old_path, "no product holds %s — would redirect into a dead end" % row["new"]))
        elif handles[row["new"]] != "ACTIVE":
            skip.append((old_path, "target product is %s, not ACTIVE" % handles[row["new"]].lower()))
        else:
            create.append((old_path, new_path, row.get("title", "")))

    print("\n  %s%d to create%s   %s%d skipped%s" % (GREEN, len(create), RESET, YELLOW, len(skip), RESET))
    for old_path, new_path, title in create[:8]:
        print("    %s\n      -> %s" % (old_path, new_path))
    if len(create) > 8:
        print("    %s… and %d more%s" % (DIM, len(create) - 8, RESET))
    if skip:
        print("\n  %sskipped%s" % (YELLOW, RESET))
        for old_path, why in skip[:10]:
            print("    %-70s %s" % (old_path[:70], why))
        if len(skip) > 10:
            print("    %s… and %d more%s" % (DIM, len(skip) - 10, RESET))

    if not args.apply:
        print("\n%sDry run — nothing was written. Re-run with --apply.%s" % (YELLOW, RESET))
        return

    done, failed = 0, []
    for old_path, new_path, title in create:
        result = client.call(CREATE, {"redirect": {"path": old_path, "target": new_path}})
        errors = result["urlRedirectCreate"]["userErrors"]
        if errors:
            failed.append((old_path, errors))
            continue
        done += 1
        if done % 50 == 0:
            print("  %s%d/%d…%s" % (DIM, done, len(create), RESET))

    print("\n%sCreated%s %d redirects" % (GREEN, RESET, done))
    if failed:
        print("%s%d failed%s" % (RED, len(failed), RESET))
        for old_path, errors in failed[:10]:
            print("  %s  %s" % (old_path, json.dumps(errors)))


if __name__ == "__main__":
    main()
