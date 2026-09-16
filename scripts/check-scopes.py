#!/usr/bin/env python3
"""Report the access scopes the current token actually has.

Scripts here fail with "Access denied … required access: read_x", and the
reason is never visible from this side: an app can be released with new scopes
while the store still holds the old grant, and the token keeps working for
everything else. This asks Shopify what this token is allowed to do, so the
answer is a list rather than a guess.

    python3 scripts/check-scopes.py
    python3 scripts/check-scopes.py --need read_shipping,write_shipping

Read-only.
"""

import argparse
import importlib.util
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location(
    "sct", os.path.join(HERE, "set-collection-templates.py"))
sct = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sct)

GREEN, YELLOW, RED, DIM, RESET = sct.GREEN, sct.YELLOW, sct.RED, sct.DIM, sct.RESET

SCOPES = """
{
  currentAppInstallation {
    id
    accessScopes { handle }
    app { id title handle developerName installation { id } }
  }
}
"""

# What the scripts in this folder need, and which of them needs it.
WANTED = {
    "read_products": "product and collection scripts",
    "write_products": "product and collection scripts",
    "read_content": "page templates (set-page-template.py)",
    "write_content": "page templates (set-page-template.py)",
    "read_themes": "published-theme check before repointing a page",
    "read_discounts": "create-welcome-discount.py",
    "write_discounts": "create-welcome-discount.py",
    "read_shipping": "check-shipping-rates.py",
    "write_shipping": "changing the free-delivery rate",
    "read_legal_policies": "dump-policies.py",
    "write_legal_policies": "editing policy text from here",
}


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--need", help="comma-separated scopes to check for; exits 1 if any is missing")
    parser.add_argument("--expect", metavar="LIST|@FILE",
                        help="the app's configured scope list, to diff against what the "
                             "install actually granted — a release changes the config, "
                             "the merchant's Update button changes the grant")
    args = parser.parse_args()

    dotenv = sct.load_dotenv()
    store = sct.credential(dotenv, "SHOPIFY_STORE_DOMAIN")
    token = sct.credential(dotenv, "SHOPIFY_ADMIN_ACCESS_TOKEN")
    version = sct.credential(dotenv, "SHOPIFY_API_VERSION") or sct.DEFAULT_API_VERSION
    if not store or not token:
        sys.exit("%sMissing credentials in .env%s" % (RED, RESET))

    client = sct.Shopify(store, token, version)
    data = client.call(SCOPES)["currentAppInstallation"]
    granted = sorted(s["handle"] for s in data["accessScopes"])
    app = data.get("app") or {}

    # Identity, not just a name: a scope release only reaches this token if it
    # was made on *this* app. Editing a different app in the same admin is the
    # failure that looks exactly like a release that did not work.
    print("%sStore%s %s" % (DIM, RESET, store))
    print("%sApp  %s %s (handle %s, by %s)"
          % (DIM, RESET, app.get("title") or "?", app.get("handle") or "?",
             app.get("developerName") or "?"))
    print("%s     %s%s" % (DIM, app.get("id") or "?", RESET))
    print("%sScopes%s %d granted\n" % (DIM, RESET, len(granted)))

    for scope in granted:
        print("  %s%s%s" % (GREEN, scope, RESET))

    missing = [s for s in WANTED if s not in granted]
    if missing:
        print("\n%sNot granted%s" % (DIM, RESET))
        for scope in sorted(missing):
            print("  %s%-22s%s %s" % (YELLOW, scope, RESET, WANTED[scope]))

    if args.expect:
        raw = args.expect
        if raw.startswith("@"):
            with open(raw[1:], encoding="utf-8") as handle:
                raw = handle.read()
        expected = sorted({s.strip() for s in raw.replace("\n", ",").split(",") if s.strip()})
        not_granted = [s for s in expected if s not in granted]
        not_configured = [s for s in granted if s not in expected]

        print("\n%sConfigured but not granted%s  (%d of %d)"
              % (DIM, RESET, len(not_granted), len(expected)))
        for scope in not_granted:
            print("  %s%s%s" % (RED, scope, RESET))
        if not not_granted:
            print("  %s— none: the install is up to date with the config%s" % (DIM, RESET))

        if not_configured:
            print("\n%sGranted but not in that list%s" % (DIM, RESET))
            for scope in not_configured:
                print("  %s%s%s" % (YELLOW, scope, RESET))

    if args.need:
        need = [s.strip() for s in args.need.split(",") if s.strip()]
        absent = [s for s in need if s not in granted]
        if absent:
            print("\n%sMissing: %s%s" % (RED, ", ".join(absent), RESET))
            sys.exit(1)
        print("\n%sAll requested scopes are granted.%s" % (GREEN, RESET))


if __name__ == "__main__":
    main()
