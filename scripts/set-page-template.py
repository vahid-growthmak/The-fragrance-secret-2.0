#!/usr/bin/env python3
"""Point an admin page at the theme template that was built for it.

A page renders through templates/page.<suffix>.json, and the suffix lives on
the page in admin, not in the theme. When the two disagree the theme's work is
simply never used: the payment policy page shipped with suffix "page", so it
rendered through the generic template while sections/page-payment-policy.liquid
sat unused.

Before writing, this checks that the *published* theme actually contains the
template being asked for. That is the whole risk of this change — a suffix
naming a template the live theme does not have is a page that stops rendering
the way anyone expects — and it is not a risk worth taking on trust, because
the theme in this repo is not necessarily the theme the store is serving.

Usage
-----
    python3 scripts/set-page-template.py payment-policy payment-policy
    python3 scripts/set-page-template.py payment-policy payment-policy --apply
    python3 scripts/set-page-template.py payment-policy "" --apply   # default

Credentials come from .env as everywhere else here; run refresh-token.py if
this returns 401. Nothing is written without --apply.
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

FIND_PAGE = """
query($cursor: String) {
  pages(first: 100, after: $cursor) {
    pageInfo { hasNextPage endCursor }
    nodes { id handle title templateSuffix }
  }
}
"""

THEMES = """
{ themes(first: 50) { nodes { id name role } } }
"""

THEME_FILES = """
query($id: ID!, $names: [String!]) {
  theme(id: $id) {
    name
    files(filenames: $names, first: 10) { nodes { filename } }
  }
}
"""

UPDATE_PAGE = """
mutation($id: ID!, $page: PageUpdateInput!) {
  pageUpdate(id: $id, page: $page) {
    page { id handle templateSuffix }
    userErrors { field code message }
  }
}
"""


def find_page(client, handle):
    cursor = None
    while True:
        data = client.call(FIND_PAGE, {"cursor": cursor})["pages"]
        for node in data["nodes"]:
            if node["handle"] == handle:
                return node
        if not data["pageInfo"]["hasNextPage"]:
            return None
        cursor = data["pageInfo"]["endCursor"]


def published_theme_has(client, suffix):
    """(theme name, has template, checked) for the live theme.

    Returns checked=False when the app cannot read themes, so the caller can
    say "unverified" rather than pretend either answer.
    """
    wanted = ["templates/page.%s.json" % suffix, "templates/page.%s.liquid" % suffix]
    body = client.call_raw(THEMES)
    if body.get("errors"):
        return None, None, False

    live = next((t for t in body["data"]["themes"]["nodes"] if t["role"] == "MAIN"), None)
    if not live:
        return None, None, False

    body = client.call_raw(THEME_FILES, {"id": live["id"], "names": wanted})
    if body.get("errors"):
        return live["name"], None, False

    found = [f["filename"] for f in body["data"]["theme"]["files"]["nodes"]]
    return live["name"], bool(found), True


def audit(client):
    """Every page template in the repo, against the pages that should use it.

    A template renders nothing unless a page in admin names it, and nothing
    anywhere reports that mismatch — the page just quietly falls back to the
    generic one, which is how sections/page-faqs.liquid came to be maintained
    for a page that never rendered it.
    """
    repo = os.path.dirname(HERE)
    suffixes = sorted(
        name[len("page."):-len(".json")]
        for name in os.listdir(os.path.join(repo, "templates"))
        if name.startswith("page.") and name.endswith(".json") and name != "page.json")

    cursor, pages = None, []
    while True:
        data = client.call(FIND_PAGE, {"cursor": cursor})["pages"]
        pages.extend(data["nodes"])
        if not data["pageInfo"]["hasNextPage"]:
            break
        cursor = data["pageInfo"]["endCursor"]
    by_handle = {p["handle"]: p for p in pages}

    print("%s%-26s %-26s %s%s" % (DIM, "theme template", "admin page", "suffix in admin", RESET))
    wrong = []
    for suffix in suffixes:
        page = by_handle.get(suffix)
        if not page:
            print("  %-24s %s%-26s%s —" % ("page." + suffix, YELLOW, "no page with that handle", RESET))
            continue
        current = page.get("templateSuffix") or ""
        ok = current == suffix
        print("  %-24s %-26s %s%s%s"
              % ("page." + suffix, page["title"][:26],
                 GREEN if ok else RED, current or "(default)", RESET))
        if not ok:
            wrong.append((suffix, page, current))

    if wrong:
        print("\n%s%d page(s) are not using the template built for them:%s" % (RED, len(wrong), RESET))
        for suffix, page, current in wrong:
            print("  python3 scripts/set-page-template.py %s %s --apply" % (page["handle"], suffix))
    else:
        print("\n%sEvery page template is in use.%s" % (GREEN, RESET))


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("handle", nargs="?", help="page handle, e.g. payment-policy")
    parser.add_argument("suffix", nargs="?", help='template suffix, or "" for the default page template')
    parser.add_argument("--audit", action="store_true",
                        help="report every page template in the repo and whether a page uses it")
    parser.add_argument("--apply", action="store_true", help="actually write it")
    parser.add_argument("--force", action="store_true",
                        help="write even if the published theme has no such template")
    args = parser.parse_args()

    if not args.audit and (args.handle is None or args.suffix is None):
        parser.error("give a handle and a suffix, or use --audit")
    suffix = (args.suffix or "").strip()

    dotenv = sct.load_dotenv()
    store = sct.credential(dotenv, "SHOPIFY_STORE_DOMAIN")
    token = sct.credential(dotenv, "SHOPIFY_ADMIN_ACCESS_TOKEN")
    version = sct.credential(dotenv, "SHOPIFY_API_VERSION") or sct.DEFAULT_API_VERSION
    if not store or not token:
        sys.exit("%sMissing credentials in .env%s" % (RED, RESET))

    client = sct.Shopify(store, token, version)
    shop = client.call("{ shop { name myshopifyDomain } }")["shop"]
    print("%sStore%s %s (%s)" % (DIM, RESET, shop["name"], shop["myshopifyDomain"]))
    print("%sMode %s %s\n" % (DIM, RESET,
                              (GREEN + "APPLY" + RESET) if args.apply else (YELLOW + "dry run" + RESET)))

    if args.audit:
        audit(client)
        return

    page = find_page(client, args.handle)
    if not page:
        sys.exit("%sNo page with handle %s%s" % (RED, args.handle, RESET))

    current = page.get("templateSuffix") or "(default)"
    print("  page           %s — %s" % (page["handle"], page["title"]))
    print("  suffix now     %s" % current)
    print("  suffix wanted  %s" % (suffix or "(default)"))

    if (page.get("templateSuffix") or "") == suffix:
        print("\n%sAlready set. Nothing to do.%s" % (GREEN, RESET))
        return

    if suffix:
        theme_name, has_template, checked = published_theme_has(client, suffix)
        if not checked:
            print("\n  %spublished theme%s could not be read (needs read_themes) — "
                  "template presence unverified" % (YELLOW, RESET))
            if not args.force:
                sys.exit("%sRefusing to guess. Confirm the live theme has "
                         "templates/page.%s.json, then re-run with --force.%s"
                         % (RED, suffix, RESET))
        elif has_template:
            print("  live theme     %s%s has templates/page.%s.json%s"
                  % (GREEN, theme_name, suffix, RESET))
        else:
            print("  live theme     %s%s has no page.%s template%s"
                  % (RED, theme_name, suffix, RESET))
            if not args.force:
                sys.exit("%sRefusing: this would point the page at a template the "
                         "live storefront does not have.%s" % (RED, RESET))

    if not args.apply:
        print("\n%sDry run — nothing was written. Re-run with --apply.%s" % (YELLOW, RESET))
        return

    result = client.call(UPDATE_PAGE, {"id": page["id"], "page": {"templateSuffix": suffix}})
    errors = result["pageUpdate"]["userErrors"]
    if errors:
        sys.exit("%sShopify rejected it: %s%s" % (RED, json.dumps(errors, indent=2), RESET))

    updated = result["pageUpdate"]["page"]
    print("\n%sUpdated%s %s — suffix is now %s"
          % (GREEN, RESET, updated["handle"], updated.get("templateSuffix") or "(default)"))


if __name__ == "__main__":
    main()
