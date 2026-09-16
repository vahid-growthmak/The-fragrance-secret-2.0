#!/usr/bin/env python3
"""Move the nav collections onto the slugs in Fragrance_Secrets_URL_Slugs.xlsx.

The sheet is the agreed URL scheme: collections/mens-perfumes rather than
collections/mens, and so on for every entry in the Shop menu. The store was
built on the shorter handles, so 33 collections need renaming — and a renamed
collection is a changed URL, which means a 301 from the old one or the indexed
page is simply gone.

Each pair is worked out by matching the sheet's page name against the label on
the theme's own mega-menu link, not by comparing handle text. "Formal Event
Perfumes" lives at collections/wedding-formal and "Party Wear Perfumes" at
collections/party-clubbing; no string similarity would pair those correctly,
and pairing them wrongly points a category at someone else's products.

Three things happen per rename, and the third is the one that is easy to miss:

  1. the collection takes the new handle
  2. a 301 sends the old URL to the new one
  3. redirects that already pointed at the old handle are re-pointed at the
     new one, so an old brand URL does not hop twice to arrive

    python3 scripts/apply-url-slugs.py              # dry run
    python3 scripts/apply-url-slugs.py --apply

Nothing is written without --apply. Theme files are not touched here — run
scripts/update-collection-links.py after this, or the menu will point at
handles that now only exist as redirects.
"""

import argparse
import importlib.util
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
spec = importlib.util.spec_from_file_location(
    "sct", os.path.join(HERE, "set-collection-templates.py"))
sct = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sct)

GREEN, YELLOW, RED, DIM, RESET = sct.GREEN, sct.YELLOW, sct.RED, sct.DIM, sct.RESET

SHEET = os.path.join(REPO, "Fragrance_Secrets_URL_Slugs.xlsx")
HEADER = os.path.join(REPO, "sections", "header.liquid")
PLAN_OUT = os.path.join(HERE, "url-slug-plan.json")

COLLECTIONS = """
query($cursor: String) {
  collections(first: 250, after: $cursor) {
    pageInfo { hasNextPage endCursor }
    nodes { id handle title productsCount { count } }
  }
}
"""

REDIRECTS = """
query($cursor: String) {
  urlRedirects(first: 250, after: $cursor) {
    pageInfo { hasNextPage endCursor }
    nodes { id path target }
  }
}
"""

RENAME = """
mutation($input: CollectionInput!) {
  collectionUpdate(input: $input) {
    collection { id handle }
    userErrors { field message }
  }
}
"""

CREATE_REDIRECT = """
mutation($redirect: UrlRedirectInput!) {
  urlRedirectCreate(urlRedirect: $redirect) {
    urlRedirect { id path target }
    userErrors { field message }
  }
}
"""

UPDATE_REDIRECT = """
mutation($id: ID!, $redirect: UrlRedirectInput!) {
  urlRedirectUpdate(id: $id, urlRedirect: $redirect) {
    urlRedirect { id path target }
    userErrors { field message }
  }
}
"""


def label_key(text):
    """Menu labels and sheet names differ in punctuation and entities only."""
    text = re.sub(r"&amp;", "&", text or "")
    return re.sub(r"[^a-z0-9&]+", " ", text.lower()).strip()


def build_plan(collections):
    try:
        import openpyxl
    except ImportError:
        sys.exit("%sopenpyxl is needed to read the sheet: pip install openpyxl%s" % (RED, RESET))

    nav = re.findall(r'<a href="/collections/([a-z0-9-]+)">([^<]+)</a>',
                     open(HEADER, encoding="utf-8").read())
    by_label = {}
    for handle, label in nav:
        by_label.setdefault(label_key(label), handle)

    book = openpyxl.load_workbook(SHEET, read_only=True, data_only=True)
    rows = list(book["URL Slugs"].iter_rows(values_only=True))[1:]

    plan, skipped = [], []
    for row in rows:
        group, name, slug = [(c or "").strip() if isinstance(c, str) else c for c in row[:3]]
        if not slug:
            continue
        want = slug.split("/")[-1]
        current = by_label.get(label_key(name))

        if want in collections:
            continue                       # already on the agreed slug
        if not current:
            skipped.append((name, want, "not linked from the theme menu"))
            continue
        if current == "all":
            # /collections/all is Shopify's built-in listing, not a collection
            # that can be renamed. Giving "All Products" its own slug means
            # creating a new collection, which is a decision, not a rename.
            skipped.append((name, want, "/collections/all is built in, cannot be renamed"))
            continue
        if current not in collections:
            skipped.append((name, want, "no collection with handle %s" % current))
            continue
        if want in collections:
            skipped.append((name, want, "%s is already taken" % want))
            continue
        plan.append({"label": name, "group": group, "old": current, "new": want,
                     "id": collections[current]["id"],
                     "title": collections[current]["title"],
                     "products": collections[current]["productsCount"]["count"]})
    return plan, skipped


def page_all(client, query, key):
    cursor, rows = None, []
    while True:
        page = client.call(query, {"cursor": cursor})[key]
        rows.extend(page["nodes"])
        if not page["pageInfo"]["hasNextPage"]:
            return rows
        cursor = page["pageInfo"]["endCursor"]


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--apply", action="store_true", help="actually rename and redirect")
    args = parser.parse_args()

    dotenv = sct.load_dotenv()
    store = sct.credential(dotenv, "SHOPIFY_STORE_DOMAIN")
    token = sct.credential(dotenv, "SHOPIFY_ADMIN_ACCESS_TOKEN")
    version = sct.credential(dotenv, "SHOPIFY_API_VERSION") or sct.DEFAULT_API_VERSION
    if not store or not token:
        sys.exit("%sMissing credentials in .env%s" % (RED, RESET))

    client = sct.Shopify(store, token, version)
    shop = client.call("{ shop { name } }")["shop"]
    print("%sStore%s %s" % (DIM, RESET, shop["name"]))
    print("%sMode %s %s\n" % (DIM, RESET,
                              (GREEN + "APPLY" + RESET) if args.apply else (YELLOW + "dry run" + RESET)))

    collections = {c["handle"]: c for c in page_all(client, COLLECTIONS, "collections")}
    plan, skipped = build_plan(collections)

    redirects = page_all(client, REDIRECTS, "urlRedirects")
    renaming = {p["old"]: p["new"] for p in plan}
    # A redirect already aimed at an old handle would hop twice once that
    # handle moves. Two hops still resolve, but they leak authority and some
    # crawlers stop following.
    chained = [r for r in redirects
               if r["target"].startswith("/collections/")
               and r["target"].rstrip("/").split("/")[-1] in renaming]

    print("%-26s %-22s    %-26s %s" % ("MENU LABEL", "CURRENT", "NEW SLUG", "PRODUCTS"))
    for row in plan:
        print("%-26s %-22s -> %-26s %s" % (row["label"][:26], row["old"], row["new"], row["products"]))
    print("\n  %d renames, %d redirects to create, %d existing redirects to re-point"
          % (len(plan), len(plan), len(chained)))
    if skipped:
        print("\n  %sleft alone%s" % (YELLOW, RESET))
        for name, want, why in skipped:
            print("    %-26s wants %-22s %s" % (name[:26], want, why))

    with open(PLAN_OUT, "w", encoding="utf-8") as handle:
        json.dump({"plan": plan, "skipped": skipped,
                   "rechained": [{"id": r["id"], "path": r["path"], "was": r["target"],
                                  "now": "/collections/%s"
                                         % renaming[r["target"].rstrip("/").split("/")[-1]]}
                                 for r in chained]}, handle, indent=1)
    print("\n%splan written to %s%s" % (DIM, os.path.relpath(PLAN_OUT, REPO), RESET))

    if not args.apply:
        print("\n%sDry run — nothing was written. Re-run with --apply.%s" % (YELLOW, RESET))
        return

    renamed, failed = 0, []
    for row in plan:
        result = client.call(RENAME, {"input": {"id": row["id"], "handle": row["new"]}})
        errors = result["collectionUpdate"]["userErrors"]
        if errors:
            failed.append((row["old"], errors))
            continue
        got = result["collectionUpdate"]["collection"]["handle"]
        if got != row["new"]:
            failed.append((row["old"], "Shopify gave handle %s" % got))
            continue
        renamed += 1

        created = client.call(CREATE_REDIRECT, {"redirect": {
            "path": "/collections/%s" % row["old"], "target": "/collections/%s" % row["new"]}})
        errors = created["urlRedirectCreate"]["userErrors"]
        if errors:
            failed.append(("redirect %s" % row["old"], errors))
    print("\n%srenamed%s %d of %d" % (GREEN, RESET, renamed, len(plan)))

    repointed = 0
    for row in chained:
        old_handle = row["target"].rstrip("/").split("/")[-1]
        result = client.call(UPDATE_REDIRECT, {
            "id": row["id"],
            "redirect": {"path": row["path"],
                         "target": "/collections/%s" % renaming[old_handle]}})
        errors = result["urlRedirectUpdate"]["userErrors"]
        if errors:
            failed.append(("rechain %s" % row["path"], errors))
        else:
            repointed += 1
    print("%sre-pointed%s %d of %d existing redirects" % (GREEN, RESET, repointed, len(chained)))

    if failed:
        print("\n%s%d problems%s" % (RED, len(failed), RESET))
        for what, why in failed[:12]:
            print("  %-40s %s" % (what, json.dumps(why) if not isinstance(why, str) else why))


if __name__ == "__main__":
    main()
