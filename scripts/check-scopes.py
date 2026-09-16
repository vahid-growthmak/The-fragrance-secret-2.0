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
{ currentAppInstallation { accessScopes { handle } app { title } } }
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
    app = (data.get("app") or {}).get("title") or "this app"

    print("%sStore%s %s" % (DIM, RESET, store))
    print("%sApp  %s %s — %d scopes\n" % (DIM, RESET, app, len(granted)))

    for scope in granted:
        print("  %s%s%s" % (GREEN, scope, RESET))

    missing = [s for s in WANTED if s not in granted]
    if missing:
        print("\n%sNot granted%s" % (DIM, RESET))
        for scope in sorted(missing):
            print("  %s%-22s%s %s" % (YELLOW, scope, RESET, WANTED[scope]))

    if args.need:
        need = [s.strip() for s in args.need.split(",") if s.strip()]
        absent = [s for s in need if s not in granted]
        if absent:
            print("\n%sMissing: %s%s" % (RED, ", ".join(absent), RESET))
            sys.exit(1)
        print("\n%sAll requested scopes are granted.%s" % (GREEN, RESET))


if __name__ == "__main__":
    main()
