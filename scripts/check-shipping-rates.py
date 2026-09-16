#!/usr/bin/env python3
"""Report the store's delivery rates, and what they actually charge.

The storefront's free-delivery promise is theme copy; what a customer pays is
a rate in Settings › Shipping and delivery. The two have no connection at all,
so the only way to know they agree is to read them. This reads the rates.

Read-only. It writes nothing, and it is meant to be run after the theme's
Delivery setting changes, to confirm the store charges what the site promises.

    python3 scripts/check-shipping-rates.py
"""

import importlib.util
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
        locationGroupZones(first: 20) {
          nodes {
            zone { name countries { code { countryCode } name } }
            methodDefinitions(first: 20) {
              nodes {
                name active
                rateProvider {
                  __typename
                  ... on DeliveryRateDefinition { price { amount currencyCode } }
                }
                methodConditions {
                  field operator
                  conditionCriteria {
                    __typename
                    ... on MoneyV2 { amount currencyCode }
                    ... on Weight { value unit }
                  }
                }
              }
            }
          }
        }
      }
    }
  }
}
"""


def main():
    dotenv = sct.load_dotenv()
    store = sct.credential(dotenv, "SHOPIFY_STORE_DOMAIN")
    token = sct.credential(dotenv, "SHOPIFY_ADMIN_ACCESS_TOKEN")
    version = sct.credential(dotenv, "SHOPIFY_API_VERSION") or sct.DEFAULT_API_VERSION
    if not store or not token:
        sys.exit("%sMissing credentials in .env%s" % (RED, RESET))

    client = sct.Shopify(store, token, version)
    shop = client.call("{ shop { name myshopifyDomain } }")["shop"]
    print("%sStore%s %s (%s)\n" % (DIM, RESET, shop["name"], shop["myshopifyDomain"]))

    body = client.call_raw(PROFILES)
    if body.get("errors"):
        # Quote Shopify rather than assuming which scope is missing: an app can
        # be re-released with a hundred new scopes and still not the one this
        # query needs, and "needs read_shipping" from memory would be a guess.
        for error in body["errors"]:
            required = (error.get("extensions") or {}).get("requiredAccess")
            print("  %s%s%s" % (YELLOW, error.get("message", error), RESET))
            if required:
                print("  %srequired access: %s%s" % (DIM, required, RESET))
        print("\n%sCheck Settings › Shipping and delivery by hand until that scope is granted.%s"
              % (DIM, RESET))
        return
    profiles = body["data"]["deliveryProfiles"]["nodes"]

    for profile in profiles:
        print("%s%s%s%s" % (GREEN, profile["name"], " (default)" if profile["default"] else "", RESET))
        for group in profile["profileLocationGroups"]:
            for zone_node in group["locationGroupZones"]["nodes"]:
                zone = zone_node["zone"]
                print("  %szone%s %s" % (DIM, RESET, zone["name"]))
                for method in zone_node["methodDefinitions"]["nodes"]:
                    provider = method.get("rateProvider") or {}
                    price = provider.get("price")
                    cost = ("%s %s" % (price["amount"], price["currencyCode"])) if price \
                        else provider.get("__typename", "carrier-calculated")
                    state = "" if method["active"] else " %s(inactive)%s" % (YELLOW, RESET)
                    print("    %-34s %s%s" % (method["name"], cost, state))
                    for condition in method.get("methodConditions") or []:
                        criteria = condition.get("conditionCriteria") or {}
                        if "amount" in criteria:
                            value = "%s %s" % (criteria["amount"], criteria["currencyCode"])
                        elif "value" in criteria:
                            value = "%s %s" % (criteria["value"], criteria.get("unit", ""))
                        else:
                            value = "?"
                        print("      %swhen %s %s %s%s"
                              % (DIM, condition["field"], condition["operator"], value, RESET))
        print("")


if __name__ == "__main__":
    main()
