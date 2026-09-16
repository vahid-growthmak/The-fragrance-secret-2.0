#!/usr/bin/env python3
"""Create the welcome discount the storefront's 10% band promises.

The theme can put a code on a bag but it cannot invent one — a discount is a
Shopify object, so the code named in Theme settings › Welcome offer has to
exist in admin › Discounts or the band's button applies nothing. This creates
it to match: a percentage off the whole order, one use per customer, limited
to customers who have not ordered yet.

"Not ordered yet" is a customer segment (number_of_orders = 0), which also
does the work of requiring an account: segments only ever contain customer
records, so a guest checkout cannot qualify. The segment is created if the
store does not already have an equivalent one.

Usage
-----
    python3 scripts/create-welcome-discount.py             # dry run
    python3 scripts/create-welcome-discount.py --apply     # create it
    python3 scripts/create-welcome-discount.py --code SPRING10 --percent 15

Credentials come from .env exactly as the other scripts here read them; run
scripts/refresh-token.py first if this returns 401. Nothing is written without
--apply, and a code that already exists is reported and left alone rather than
duplicated — two live discounts sharing a code is not a state worth risking.
"""

import argparse
import datetime
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

FIRST_ORDER_QUERY = "number_of_orders = 0"
SEGMENT_NAME = "First-time buyers (no orders yet)"

LIST_CODES = """
query($cursor: String) {
  codeDiscountNodes(first: 100, after: $cursor) {
    pageInfo { hasNextPage endCursor }
    nodes {
      id
      codeDiscount {
        __typename
        ... on DiscountCodeBasic {
          title status startsAt endsAt appliesOncePerCustomer usageLimit
          codes(first: 10) { nodes { code } }
          customerGets { value { ... on DiscountPercentage { percentage } } }
          minimumRequirement {
            __typename
            ... on DiscountMinimumSubtotal {
              greaterThanOrEqualToSubtotal { amount currencyCode }
            }
            ... on DiscountMinimumQuantity { greaterThanOrEqualToQuantity }
          }
          customerSelection {
            __typename
            ... on DiscountCustomerSegments { segments { id name query } }
          }
          combinesWith { orderDiscounts productDiscounts shippingDiscounts }
        }
      }
    }
  }
}
"""

LIST_SEGMENTS = """
{ segments(first: 100) { nodes { id name query } } }
"""

CREATE_SEGMENT = """
mutation($name: String!, $query: String!) {
  segmentCreate(name: $name, query: $query) {
    segment { id name query }
    userErrors { field message }
  }
}
"""

UPDATE_DISCOUNT = """
mutation($id: ID!, $d: DiscountCodeBasicInput!) {
  discountCodeBasicUpdate(id: $id, basicCodeDiscount: $d) {
    codeDiscountNode {
      id
      codeDiscount { ... on DiscountCodeBasic { title status
        codes(first: 5) { nodes { code } }
        minimumRequirement { ... on DiscountMinimumSubtotal {
          greaterThanOrEqualToSubtotal { amount currencyCode } } } } }
    }
    userErrors { field code message }
  }
}
"""

CREATE_DISCOUNT = """
mutation($d: DiscountCodeBasicInput!) {
  discountCodeBasicCreate(basicCodeDiscount: $d) {
    codeDiscountNode {
      id
      codeDiscount { ... on DiscountCodeBasic { title status startsAt
        codes(first: 5) { nodes { code } } } }
    }
    userErrors { field code message }
  }
}
"""


def all_code_discounts(client):
    """Every code discount on the store, paged.

    Not a search: codeDiscountNodes(query:) matches the discount's *title*, so
    asking it for "WELCOME10" found nothing a minute after WELCOME10 was
    created — which would have let a second --apply run create a duplicate of a
    code that already existed. Reading the list and matching the codes here is
    the only way to be sure.
    """
    cursor, nodes = None, []
    while True:
        page = client.call(LIST_CODES, {"cursor": cursor})["codeDiscountNodes"]
        nodes.extend(page["nodes"])
        if not page["pageInfo"]["hasNextPage"]:
            return nodes
        cursor = page["pageInfo"]["endCursor"]


def find_existing(client, code):
    for node in all_code_discounts(client):
        discount = node.get("codeDiscount") or {}
        codes = [c["code"] for c in (discount.get("codes") or {}).get("nodes", [])]
        if any(c.upper() == code.upper() for c in codes):
            return node, discount, codes
    return None, None, None


def find_segment(client):
    data = client.call(LIST_SEGMENTS)
    normalised = FIRST_ORDER_QUERY.replace(" ", "").lower()
    for node in data["segments"]["nodes"]:
        if (node.get("query") or "").replace(" ", "").lower() == normalised:
            return node
    return None


def describe(discount):
    """Print a live discount's real terms, so a second run is also an audit."""
    percentage = ((discount.get("customerGets") or {}).get("value") or {}).get("percentage")
    selection = discount.get("customerSelection") or {}
    segments = selection.get("segments") or []
    combines = discount.get("combinesWith") or {}
    stacks = [name for name, on in
              (("product", combines.get("productDiscounts")),
               ("shipping", combines.get("shippingDiscounts")),
               ("order", combines.get("orderDiscounts"))) if on]
    print("  value          %s off the whole order"
          % ("%g%%" % (percentage * 100) if percentage else "?"))
    print("  who            %s" % (", ".join('%s (%s)' % (s["name"], s["query"]) for s in segments)
                                   or selection.get("__typename", "?")))
    minimum = discount.get("minimumRequirement") or {}
    floor = (minimum.get("greaterThanOrEqualToSubtotal") or {})
    if floor:
        print("  minimum        %s %s subtotal" % (floor.get("currencyCode"), floor.get("amount")))
    elif minimum.get("greaterThanOrEqualToQuantity"):
        print("  minimum        %s items" % minimum["greaterThanOrEqualToQuantity"])
    else:
        print("  minimum        none")
    print("  per customer   %s" % ("once, ever" if discount.get("appliesOncePerCustomer") else "unlimited"))
    print("  total uses     %s" % (discount.get("usageLimit") or "uncapped"))
    print("  starts         %s" % discount.get("startsAt"))
    print("  expires        %s" % (discount.get("endsAt") or "never"))
    print("  combines with  %s" % (", ".join(stacks) or "nothing"))


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--code", default="WELCOME10", help="discount code (default WELCOME10)")
    parser.add_argument("--percent", type=float, default=10.0, help="percent off (default 10)")
    parser.add_argument("--title", default=None, help="name shown in admin")
    parser.add_argument("--everyone", action="store_true",
                        help="offer it to all customers instead of first-time buyers only")
    parser.add_argument("--min-subtotal", type=float, default=None, metavar="AMOUNT",
                        help="only apply above this order subtotal, in store currency")
    parser.add_argument("--update", action="store_true",
                        help="change an existing code instead of refusing to touch it")
    parser.add_argument("--list", action="store_true",
                        help="print every code discount on the store and exit")
    parser.add_argument("--apply", action="store_true", help="actually create it")
    args = parser.parse_args()

    code = args.code.strip().upper()
    title = args.title or ("Welcome %g%% — first order" % args.percent)

    dotenv = sct.load_dotenv()
    store = sct.credential(dotenv, "SHOPIFY_STORE_DOMAIN")
    token = sct.credential(dotenv, "SHOPIFY_ADMIN_ACCESS_TOKEN")
    version = sct.credential(dotenv, "SHOPIFY_API_VERSION") or sct.DEFAULT_API_VERSION
    if not store or not token:
        sys.exit("%sMissing SHOPIFY_STORE_DOMAIN / SHOPIFY_ADMIN_ACCESS_TOKEN in .env%s"
                 % (RED, RESET))

    client = sct.Shopify(store, token, version)
    shop = client.call("""{ shop { name myshopifyDomain currencyCode
      currencyFormats { moneyFormat moneyWithCurrencyFormat } } }""")["shop"]
    print("%sStore%s %s (%s)" % (DIM, RESET, shop["name"], shop["myshopifyDomain"]))
    # The storefront repeats this discount's minimum in prose, so how the shop
    # renders money decides which Liquid filter reads like a sentence.
    formats = shop.get("currencyFormats") or {}
    print("%sMoney%s %s  |  with currency: %s"
          % (DIM, RESET, formats.get("moneyFormat"), formats.get("moneyWithCurrencyFormat")))
    print("%sMode %s %s\n" % (DIM, RESET,
                              (GREEN + "APPLY" + RESET) if args.apply else (YELLOW + "dry run" + RESET)))

    if args.list:
        for node in all_code_discounts(client):
            discount = node.get("codeDiscount") or {}
            codes = [c["code"] for c in (discount.get("codes") or {}).get("nodes", [])]
            # Buy-X-get-Y and free-shipping codes are their own GraphQL types,
            # so the DiscountCodeBasic fragment reads nothing off them. Name
            # them anyway: a listing that silently drops two of the store's
            # live discounts is worse than one that says "not read here".
            if not codes:
                print("%s(%s)%s — not a basic code discount, not described here"
                      % (DIM, discount.get("__typename", "unknown type"), RESET))
                print("")
                continue
            print("%s%s%s — %s, %s"
                  % (GREEN, "/".join(codes), RESET, discount.get("title"), discount.get("status")))
            describe(discount)
            print("")
        return

    node, discount, codes = find_existing(client, code)
    if node and not args.update:
        print("%s%s already exists%s — %s, %s"
              % (YELLOW, code, RESET, discount.get("title"), discount.get("status")))
        describe(discount)
        print("%sLeaving it alone. Re-run with --update to change it, or use a different --code.%s"
              % (DIM, RESET))
        return

    if args.update:
        if not node:
            sys.exit("%s%s does not exist — drop --update to create it.%s" % (RED, code, RESET))
        print("%s%s today%s" % (DIM, code, RESET))
        describe(discount)

        # Only the named fields travel. A DiscountCodeBasicInput carrying just
        # minimumRequirement leaves the value, the segment and the usage rules
        # exactly as they are, which is the point: this is an edit, not a
        # rebuild from whatever defaults this script happens to hold.
        changes = {}
        if args.min_subtotal is not None:
            changes["minimumRequirement"] = {
                "subtotal": {"greaterThanOrEqualToSubtotal": "%.2f" % args.min_subtotal}
            }
        if not changes:
            sys.exit("%sNothing to update — pass --min-subtotal.%s" % (RED, RESET))

        print("\n%s%s%s" % (DIM, "Would change" if not args.apply else "Changing", RESET))
        for field, value in changes.items():
            print("  %-14s %s" % (field, json.dumps(value)))
        if not args.apply:
            print("\n%sDry run — nothing was written. Re-run with --apply.%s" % (YELLOW, RESET))
            return

        result = client.call(UPDATE_DISCOUNT, {"id": node["id"], "d": changes})
        errors = result["discountCodeBasicUpdate"]["userErrors"]
        if errors:
            sys.exit("%sShopify rejected it: %s%s" % (RED, json.dumps(errors, indent=2), RESET))

        _, fresh, _ = find_existing(client, code)
        print("\n%sUpdated%s %s" % (GREEN, RESET, code))
        describe(fresh)
        return

    segment = None
    if not args.everyone:
        segment = find_segment(client)
        if segment:
            print("%sSegment%s reusing \"%s\" (%s)" % (DIM, RESET, segment["name"], segment["query"]))
        elif not args.apply:
            print("%sSegment%s would create \"%s\" where %s"
                  % (DIM, RESET, SEGMENT_NAME, FIRST_ORDER_QUERY))
        else:
            result = client.call(CREATE_SEGMENT, {"name": SEGMENT_NAME, "query": FIRST_ORDER_QUERY})
            errors = result["segmentCreate"]["userErrors"]
            if errors:
                sys.exit("%sCould not create the segment: %s%s"
                         % (RED, json.dumps(errors, indent=2), RESET))
            segment = result["segmentCreate"]["segment"]
            print("%sSegment%s created \"%s\"" % (GREEN, RESET, segment["name"]))

    if args.everyone:
        selection = {"all": True}
        who = "every customer"
    elif segment:
        selection = {"customerSegments": {"add": [segment["id"]]}}
        who = "customers with no orders yet"
    else:
        selection = None
        who = "customers with no orders yet (segment pending)"

    discount_input = {
        "title": title,
        "code": code,
        "startsAt": datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat(),
        "customerSelection": selection,
        "customerGets": {
            "value": {"percentage": args.percent / 100.0},
            "items": {"all": True},
        },
        # One per customer, forever — this is a first-order welcome, not a
        # coupon anyone can spend twice. No usageLimit: the cap is per person,
        # not a race for a fixed number of redemptions.
        "appliesOncePerCustomer": True,
        # Stacks with product markdowns and free shipping, but not with another
        # order-level code: two order discounts on one bag is how 10% quietly
        # becomes 40%.
        "combinesWith": {
            "orderDiscounts": False,
            "productDiscounts": True,
            "shippingDiscounts": True,
        },
    }
    if args.min_subtotal is not None:
        discount_input["minimumRequirement"] = {
            "subtotal": {"greaterThanOrEqualToSubtotal": "%.2f" % args.min_subtotal}
        }

    print("\n%sWould create%s" % (DIM, RESET) if not args.apply else "\n%sCreating%s" % (DIM, RESET))
    print("  code           %s" % code)
    print("  title          %s" % title)
    print("  value          %g%% off the whole order" % args.percent)
    print("  who            %s" % who)
    print("  minimum        %s" % ("%.2f subtotal" % args.min_subtotal
                                     if args.min_subtotal is not None else "none"))
    print("  per customer   once, ever")
    print("  expires        never")
    print("  combines with  product discounts, free shipping — not other order codes")

    if not args.apply:
        print("\n%sDry run — nothing was written. Re-run with --apply.%s" % (YELLOW, RESET))
        return

    result = client.call(CREATE_DISCOUNT, {"d": discount_input})
    errors = result["discountCodeBasicCreate"]["userErrors"]
    if errors:
        sys.exit("%sShopify rejected it: %s%s" % (RED, json.dumps(errors, indent=2), RESET))

    created = result["discountCodeBasicCreate"]["codeDiscountNode"]
    live = created["codeDiscount"]
    print("\n%sCreated%s %s — %s, starts %s"
          % (GREEN, RESET, ", ".join(c["code"] for c in live["codes"]["nodes"]),
             live["status"], live["startsAt"]))
    print("%sTheme settings › Welcome offer must name the same code.%s" % (DIM, RESET))


if __name__ == "__main__":
    main()
