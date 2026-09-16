#!/usr/bin/env python3
"""Make "free delivery above X" true at checkout, not just on the storefront.

The theme has promised free UAE delivery above a threshold for as long as it
has existed. The store never had a rate to match: the default profile charges
one flat AED 8 on every UAE order, with no conditions on it at all. This adds
the free rate and bounds the paid one so the two do not overlap.

What it does, in the named profile's UAE zone:

    Free delivery   0        when order subtotal >= threshold
    <paid rate>     as-is    when order subtotal <= threshold - 0.01

The 0.01 matters: Shopify's price conditions are inclusive at both ends, so a
paid rate capped at exactly the threshold would appear alongside the free one
at that price. Currency has two decimals, so there is no gap between them.

    python3 scripts/set-free-shipping-threshold.py 250
    python3 scripts/set-free-shipping-threshold.py 250 --apply

Nothing is written without --apply. Profiles other than the default are left
alone — "Free shipping for Oil" already ships those products free, and a
threshold on them would take a benefit away rather than add one.
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

PROFILES = """
{
  deliveryProfiles(first: 10) {
    nodes {
      id name default
      profileLocationGroups {
        locationGroup { id }
        locationGroupZones(first: 20) {
          nodes {
            zone { id name countries { code { countryCode } } }
            methodDefinitions(first: 20) {
              nodes {
                id name active
                rateProvider {
                  __typename
                  ... on DeliveryRateDefinition { id price { amount currencyCode } }
                }
                methodConditions { id field operator
                  conditionCriteria { ... on MoneyV2 { amount currencyCode } } }
              }
            }
          }
        }
      }
    }
  }
}
"""

UPDATE = """
mutation($id: ID!, $profile: DeliveryProfileInput!) {
  deliveryProfileUpdate(id: $id, profile: $profile) {
    profile { id name }
    userErrors { field message }
  }
}
"""

FREE_NAME = "Free delivery"


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("threshold", type=float, help="order subtotal at which delivery becomes free")
    parser.add_argument("--country", default="AE", help="country code of the zone to change (default AE)")
    parser.add_argument("--apply", action="store_true", help="actually write it")
    args = parser.parse_args()

    dotenv = sct.load_dotenv()
    store = sct.credential(dotenv, "SHOPIFY_STORE_DOMAIN")
    token = sct.credential(dotenv, "SHOPIFY_ADMIN_ACCESS_TOKEN")
    version = sct.credential(dotenv, "SHOPIFY_API_VERSION") or sct.DEFAULT_API_VERSION
    if not store or not token:
        sys.exit("%sMissing credentials in .env%s" % (RED, RESET))

    client = sct.Shopify(store, token, version)
    shop = client.call("{ shop { name myshopifyDomain currencyCode } }")["shop"]
    currency = shop["currencyCode"]
    print("%sStore%s %s (%s)" % (DIM, RESET, shop["name"], shop["myshopifyDomain"]))
    print("%sMode %s %s\n" % (DIM, RESET,
                              (GREEN + "APPLY" + RESET) if args.apply else (YELLOW + "dry run" + RESET)))

    profiles = client.call(PROFILES)["deliveryProfiles"]["nodes"]
    profile = next((p for p in profiles if p["default"]), None)
    if not profile:
        sys.exit("%sNo default delivery profile%s" % (RED, RESET))

    # Find the zone covering the country, inside the default profile.
    target = None
    for group in profile["profileLocationGroups"]:
        for zone_node in group["locationGroupZones"]["nodes"]:
            codes = [(c.get("code") or {}).get("countryCode") for c in zone_node["zone"]["countries"]]
            if args.country in codes:
                target = (group, zone_node)
                break
        if target:
            break
    if not target:
        sys.exit("%sNo zone in '%s' covers %s%s" % (RED, profile["name"], args.country, RESET))

    group, zone_node = target
    zone = zone_node["zone"]
    methods = zone_node["methodDefinitions"]["nodes"]
    print("%sprofile%s %s   %szone%s %s" % (DIM, RESET, profile["name"], DIM, RESET, zone["name"]))
    for method in methods:
        price = (method.get("rateProvider") or {}).get("price")
        print("  %-28s %s" % (method["name"],
                              ("%s %s" % (price["amount"], price["currencyCode"])) if price else "—"))
        for condition in method.get("methodConditions") or []:
            criteria = condition.get("conditionCriteria") or {}
            print("    %swhen %s %s %s%s" % (DIM, condition["field"], condition["operator"],
                                             criteria.get("amount", "?"), RESET))

    existing_free = next((m for m in methods if m["name"].strip().lower() == FREE_NAME.lower()), None)
    if existing_free:
        print("\n%s'%s' already exists in this zone — edit it in admin rather than "
              "adding a second one.%s" % (YELLOW, FREE_NAME, RESET))
        return

    # Anything that costs money and has no upper bound would keep showing
    # alongside the free rate. Bound each one, rather than only the first.
    paid = [m for m in methods
            if float(((m.get("rateProvider") or {}).get("price") or {}).get("amount", 0)) > 0]

    cap = "%.2f" % (args.threshold - 0.01)
    floor = "%.2f" % args.threshold

    create = [{
        "name": FREE_NAME,
        "description": "Free delivery on orders of %s %s or more" % (floor, currency),
        "active": True,
        "rateDefinition": {"price": {"amount": "0.00", "currencyCode": currency}},
        "priceConditionsToCreate": [
            {"criteria": {"amount": floor, "currencyCode": currency},
             "operator": "GREATER_THAN_OR_EQUAL_TO"},
        ],
    }]

    update = []
    for method in paid:
        update.append({
            "id": method["id"],
            "priceConditionsToCreate": [
                {"criteria": {"amount": cap, "currencyCode": currency},
                 "operator": "LESS_THAN_OR_EQUAL_TO"},
            ],
        })

    print("\n%s%s%s" % (DIM, "Would change" if not args.apply else "Changing", RESET))
    print("  create  %-22s 0.00 %s  when subtotal >= %s" % (FREE_NAME, currency, floor))
    for method in paid:
        price = (method.get("rateProvider") or {}).get("price") or {}
        print("  bound   %-22s %s %s  when subtotal <= %s"
              % (method["name"], price.get("amount"), currency, cap))

    if not args.apply:
        print("\n%sDry run — nothing was written. Re-run with --apply.%s" % (YELLOW, RESET))
        return

    variables = {
        "id": profile["id"],
        "profile": {
            "locationGroupsToUpdate": [{
                "id": group["locationGroup"]["id"],
                "zonesToUpdate": [{
                    "id": zone["id"],
                    "methodDefinitionsToCreate": create,
                    "methodDefinitionsToUpdate": update,
                }],
            }],
        },
    }
    result = client.call(UPDATE, variables)
    errors = result["deliveryProfileUpdate"]["userErrors"]
    if errors:
        sys.exit("%sShopify rejected it: %s%s" % (RED, json.dumps(errors, indent=2), RESET))

    print("\n%sUpdated%s %s" % (GREEN, RESET, result["deliveryProfileUpdate"]["profile"]["name"]))
    print("%sRun check-shipping-rates.py to see it as the store now holds it.%s" % (DIM, RESET))


if __name__ == "__main__":
    main()
