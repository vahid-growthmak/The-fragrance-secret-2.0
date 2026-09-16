#!/usr/bin/env python3
"""Replace an exact passage inside one of the store's legal policies.

These documents are the merchant's, not the theme's, and they are legal text:
the safe way to change one is to swap a passage that is quoted exactly and
leave every other byte alone. So this takes the old markup and the new markup
as files, refuses unless the old appears exactly once, and prints a diff of
what it would do before it does anything.

    python3 scripts/edit-policy.py SHIPPING_POLICY --find-file a.html --replace-file b.html
    python3 scripts/edit-policy.py SHIPPING_POLICY --find-file a.html --replace-file b.html --apply
    python3 scripts/edit-policy.py SHIPPING_POLICY --show > current.html

Nothing is written without --apply. Needs read_legal_policies and, to write,
write_legal_policies.
"""

import argparse
import difflib
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

POLICIES = """
{ shop { shopPolicies { id type title body } } }
"""

UPDATE = """
mutation($policy: ShopPolicyInput!) {
  shopPolicyUpdate(shopPolicy: $policy) {
    shopPolicy { id type title }
    userErrors { field message }
  }
}
"""


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("policy", help="policy type, e.g. SHIPPING_POLICY, REFUND_POLICY")
    parser.add_argument("--find-file", help="file holding the exact markup to replace")
    parser.add_argument("--replace-file", help="file holding the markup to put in its place")
    parser.add_argument("--show", action="store_true", help="print the policy body and exit")
    parser.add_argument("--apply", action="store_true", help="actually write it")
    args = parser.parse_args()

    dotenv = sct.load_dotenv()
    store = sct.credential(dotenv, "SHOPIFY_STORE_DOMAIN")
    token = sct.credential(dotenv, "SHOPIFY_ADMIN_ACCESS_TOKEN")
    version = sct.credential(dotenv, "SHOPIFY_API_VERSION") or sct.DEFAULT_API_VERSION
    if not store or not token:
        sys.exit("%sMissing credentials in .env%s" % (RED, RESET))

    client = sct.Shopify(store, token, version)
    body = client.call_raw(POLICIES)
    if body.get("errors"):
        for error in body["errors"]:
            print("%s%s%s" % (RED, error.get("message", error), RESET))
        sys.exit(1)

    policies = body["data"]["shop"]["shopPolicies"] or []
    policy = next((p for p in policies if p["type"].upper() == args.policy.upper()), None)
    if not policy:
        sys.exit("%sNo %s on this store. Found: %s%s"
                 % (RED, args.policy, ", ".join(p["type"] for p in policies), RESET))

    current = policy["body"] or ""
    if args.show:
        sys.stdout.write(current)
        return

    if not args.find_file or not args.replace_file:
        sys.exit("%sGive --find-file and --replace-file, or --show.%s" % (RED, RESET))

    with open(args.find_file, encoding="utf-8") as handle:
        old = handle.read().strip("\n")
    with open(args.replace_file, encoding="utf-8") as handle:
        new = handle.read().strip("\n")

    occurrences = current.count(old)
    print("%sStore%s %s" % (DIM, RESET, store))
    print("%sPolicy%s %s (%s) — %d chars\n" % (DIM, RESET, policy["title"], policy["type"], len(current)))

    if occurrences == 0:
        sys.exit("%sThe passage to replace is not in this policy — it may have been "
                 "edited in admin since the file was written.%s" % (RED, RESET))
    if occurrences > 1:
        sys.exit("%sThe passage appears %d times; it has to be unique to be replaced "
                 "safely. Quote more of the surrounding markup.%s" % (RED, occurrences, RESET))

    updated = current.replace(old, new)
    diff = difflib.unified_diff(old.splitlines(), new.splitlines(),
                                fromfile="current", tofile="proposed", lineterm="")
    print("%s%s%s" % (DIM, "Would change" if not args.apply else "Changing", RESET))
    for line in diff:
        colour = GREEN if line.startswith("+") else RED if line.startswith("-") else DIM
        print("  %s%s%s" % (colour, line, RESET))
    print("\n  %s%d chars → %d%s" % (DIM, len(current), len(updated), RESET))

    if not args.apply:
        print("\n%sDry run — nothing was written. Re-run with --apply.%s" % (YELLOW, RESET))
        return

    result = client.call(UPDATE, {"policy": {"id": policy["id"], "body": updated}})
    errors = result["shopPolicyUpdate"]["userErrors"]
    if errors:
        sys.exit("%sShopify rejected it: %s%s" % (RED, json.dumps(errors, indent=2), RESET))

    print("\n%sUpdated%s %s" % (GREEN, RESET, result["shopPolicyUpdate"]["shopPolicy"]["title"]))


if __name__ == "__main__":
    main()
