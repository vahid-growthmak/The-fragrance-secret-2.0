#!/usr/bin/env python3
"""Create the Custom Mixed Spray product the Mix-into-Spray wizard sells.

The wizard has been live on 140 oil and attar product pages since the theme
port, walking a shopper through bottle size and strength, quoting a total, and
ending on a button reading "Add Mixed Spray — AED 319". That button called
addToCart(), a demo stub carried over from the static prototype that shows a
toast and adds nothing. There was no product behind it: nothing in the 1,350
live products matches, so there was no variant to add even if it had been
wired up.

This creates the product it should have been selling. Six variants, one per
bottle size and strength, at the prices the storefront has been advertising:

    50ml   Eau de Toilette  149    100ml  Eau de Toilette  249
    50ml   Eau de Parfum    179    100ml  Eau de Parfum    279
    50ml   Extrait          219    100ml  Extrait          319

The base scent is not a variant — any of the 140 oils can be one, and 840
variants is not a product. It travels as a line-item property set by the
wizard, so the order tells whoever blends it which oil to use.

Inventory is untracked: it is made to order, so it never goes out of stock.

Read-only unless --apply. Safe to re-run: it looks the handle up first and
will not create a second copy.

    python3 scripts/create-mix-spray-product.py            # dry run
    python3 scripts/create-mix-spray-product.py --apply

Writes scripts/mix-spray-product.json on --apply — the theme reads the
product by handle, so that file is a record, not a dependency.
"""

import argparse
import importlib.util
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
RUN_LOG = os.path.join(HERE, "mix-spray-product.json")

spec = importlib.util.spec_from_file_location(
    "sct", os.path.join(HERE, "set-collection-templates.py"))
sct = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sct)
GREEN, YELLOW, RED, DIM, RESET = sct.GREEN, sct.YELLOW, sct.RED, sct.DIM, sct.RESET

HANDLE = "custom-mixed-spray"
SIZES = ["50ml", "100ml"]
STRENGTHS = ["Eau de Toilette", "Eau de Parfum", "Extrait"]
# size -> strength -> price. Lifted from the wizard's own constants so the
# storefront keeps quoting what it has always quoted; change them here or in
# admin, and the wizard follows, because it reads the product.
PRICES = {
    "50ml":  {"Eau de Toilette": "149.00", "Eau de Parfum": "179.00", "Extrait": "219.00"},
    "100ml": {"Eau de Toilette": "249.00", "Eau de Parfum": "279.00", "Extrait": "319.00"},
}

DESCRIPTION = """<p>Choose any Fragrance Secrets perfume oil and we hand-blend it into a
ready-to-wear alcohol spray, made to order in the strength you pick.</p>
<p>Select your bottle size and strength above. The oil itself is chosen on its own
product page, through <strong>Mix It Into a Spray</strong>, and travels with the order.</p>
<p><strong>Made to order</strong> — hand-blended and dispatched in 3–5 working days.
In-stock bottles still arrive in 48 hours.</p>"""

LOOKUP = """
query($handle: String!) {
  productByHandle(handle: $handle) {
    id handle title status onlineStoreUrl
    variants(first: 20) { nodes { id title price selectedOptions { name value } } }
  }
}
"""

CREATE = """
mutation($input: ProductInput!) {
  productCreate(input: $input) {
    product { id handle title }
    userErrors { field message }
  }
}
"""

VARIANTS = """
mutation($productId: ID!, $variants: [ProductVariantsBulkInput!]!) {
  productVariantsBulkCreate(productId: $productId, variants: $variants, strategy: REMOVE_STANDALONE_VARIANT) {
    productVariants { id title price selectedOptions { name value } }
    userErrors { field message }
  }
}
"""

PUBLICATIONS = """
query { publications(first: 20) { nodes { id name } } }
"""

PUBLISH = """
mutation($id: ID!, $input: [PublicationInput!]!) {
  publishablePublish(id: $id, input: $input) {
    userErrors { field message }
  }
}
"""


def planned_variants():
    rows = []
    for size in SIZES:
        for strength in STRENGTHS:
            rows.append({
                "optionValues": [
                    {"optionName": "Size", "name": size},
                    {"optionName": "Strength", "name": strength},
                ],
                "price": PRICES[size][strength],
                "inventoryItem": {"tracked": False, "requiresShipping": True},
            })
    return rows


def publish(client, product_id):
    """Publish to the Online Store, and only there.

    Not to Google, Facebook or TikTok: this is a configurator, priced without
    a base scent and meaningless in a shopping feed. It needs write_publications
    — call_raw rather than call, so a missing scope is reported instead of
    killing a run that has already created the product."""
    body = client.call_raw(PUBLICATIONS)
    if body.get("errors"):
        return False
    online = next((p for p in body["data"]["publications"]["nodes"]
                   if p["name"] == "Online Store"), None)
    if not online:
        return False
    result = client.call_raw(PUBLISH, {"id": product_id,
                                       "input": [{"publicationId": online["id"]}]})
    if result.get("errors"):
        return False
    fail_on(result["data"]["publishablePublish"], "publishablePublish")
    return True


def cannot_publish():
    print("%snot published — this app has no write_publications scope.%s" % (YELLOW, RESET))
    print("%sPublish it by hand: admin > Products > Custom Mixed Spray >%s" % (DIM, RESET))
    print("%sSales channels > Online Store. Until then the storefront 404s the%s" % (DIM, RESET))
    print("%sproduct, and the wizard's button stays hidden by design.%s" % (DIM, RESET))


def fail_on(result, label):
    errors = result.get("userErrors") or []
    if errors:
        sys.exit("%s%s failed: %s%s" % (RED, label, json.dumps(errors, indent=2), RESET))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--apply", action="store_true", help="create it (without this it only reports)")
    args = parser.parse_args()

    dotenv = sct.load_dotenv()
    store = sct.credential(dotenv, "SHOPIFY_STORE_DOMAIN")
    token = sct.credential(dotenv, "SHOPIFY_ADMIN_ACCESS_TOKEN")
    version = sct.credential(dotenv, "SHOPIFY_API_VERSION") or sct.DEFAULT_API_VERSION
    if not store or not token:
        sys.exit("%sSHOPIFY_STORE_DOMAIN and SHOPIFY_ADMIN_ACCESS_TOKEN must be set in .env%s" % (RED, RESET))
    client = sct.Shopify(store, token, version)
    print("%sstore %s · api %s · %s%s\n" % (DIM, store, version,
                                            "APPLYING" if args.apply else "dry run", RESET))

    existing = client.call(LOOKUP, {"handle": HANDLE})["productByHandle"]
    if existing:
        print("%salready exists%s  %s (%s)" % (GREEN, RESET, existing["handle"], existing["status"]))
        for v in existing["variants"]["nodes"]:
            opts = " / ".join(o["value"] for o in v["selectedOptions"])
            print("    %-34s %8s" % (opts, v["price"]))
        if existing["onlineStoreUrl"]:
            print("\npublished: %s" % existing["onlineStoreUrl"])
            print("Nothing to do. Delete it in admin first if it needs rebuilding.")
            return 0
        print("\n%snot published to the Online Store — the storefront 404s it and the%s"
              % (YELLOW, RESET))
        print("%swizard's button stays hidden.%s" % (YELLOW, RESET))
        if not args.apply:
            print("\n%sdry run — re-run with --apply to publish it.%s" % (DIM, RESET))
            return 0
        if publish(client, existing["id"]):
            print("%spublished%s to Online Store" % (GREEN, RESET))
            return 0
        cannot_publish()
        return 1

    print("would create  %s" % HANDLE)
    for row in planned_variants():
        opts = " / ".join(o["name"] for o in row["optionValues"])
        print("    %-34s %8s   untracked, ships" % (opts, row["price"]))

    if not args.apply:
        print("\n%sdry run — nothing was written. Re-run with --apply.%s" % (DIM, RESET))
        return 0

    created = fail_on(client.call(CREATE, {"input": {
        "handle": HANDLE,
        "title": "Custom Mixed Spray",
        "descriptionHtml": DESCRIPTION,
        "vendor": "The Fragrance Secrets",
        "productType": "Perfume Oil",
        "status": "ACTIVE",
        "tags": ["custom-mix", "made-to-order"],
        "productOptions": [
            {"name": "Size", "values": [{"name": s} for s in SIZES]},
            {"name": "Strength", "values": [{"name": s} for s in STRENGTHS]},
        ],
    }})["productCreate"], "productCreate")
    product_id = created["product"]["id"]
    print("%screated%s %s" % (GREEN, RESET, product_id))

    made = fail_on(client.call(VARIANTS, {
        "productId": product_id, "variants": planned_variants(),
    })["productVariantsBulkCreate"], "productVariantsBulkCreate")
    for v in made["productVariants"]:
        opts = " / ".join(o["value"] for o in v["selectedOptions"])
        print("    %-34s %8s" % (opts, v["price"]))

    published = publish(client, product_id)
    if published:
        print("%spublished%s to Online Store" % (GREEN, RESET))
    else:
        cannot_publish()

    with open(RUN_LOG, "w", encoding="utf-8") as handle:
        json.dump({"store": store, "handle": HANDLE, "product_id": product_id,
                   "published": published,
                   "variants": made["productVariants"]}, handle, indent=2, ensure_ascii=False)
    print("\nLog: %s" % os.path.relpath(RUN_LOG, REPO))
    return 0


if __name__ == "__main__":
    sys.exit(main())
