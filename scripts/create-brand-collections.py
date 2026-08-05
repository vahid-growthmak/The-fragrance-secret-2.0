#!/usr/bin/env python3
"""Create the 49 brand collections the brand pages need, and publish them.

Each is a smart collection with a single rule, Vendor equals the brand, so it
fills itself from the catalogue and stays current as products are added. The
handle matches the slug used across the brand documents (and the template
suffix), so /collections/<slug> renders that brand's page.

Usage
-----
    python3 scripts/create-brand-collections.py            # dry run
    python3 scripts/create-brand-collections.py --apply    # create them

Credentials come from .env exactly as set-collection-templates.py reads them.
Collections that already exist are left untouched. Nothing is written without
--apply.
"""

import argparse
import importlib.util
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location(
    "sct", os.path.join(HERE, "set-collection-templates.py"))
sct = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sct)

GREEN, YELLOW, RED, DIM, RESET = sct.GREEN, sct.YELLOW, sct.RED, sct.DIM, sct.RESET

# (handle / template suffix, collection title, product vendor to match)
BRANDS = [
    ('ahmed-al-maghribi', 'Ahmed Al Maghribi Perfumes', 'Ahmed Al Maghribi'),
    ('secret-scents', 'Secret Scents Perfumes', 'Secret Scents'),
    ('al-haramain', 'Al Haramain Perfumes', 'Al Haramain'),
    ('alezz-oud', 'Alezz Oud Perfumes', 'Alezz Oud'),
    ('amouage', 'Amouage Perfumes', 'Amouage'),
    ('arabiyat-prestige', 'Arabiyat Prestige Perfumes', 'Arabiyat Prestige'),
    ('armaf', 'Armaf Perfumes', 'Armaf'),
    ('azzaro', 'Azzaro Perfumes', 'Azzaro'),
    ('billie-eilish', 'Billie Eilish Perfumes', 'Billie Eilish'),
    ('boadicea-the-victorious', 'Boadicea the Victorious Perfumes', 'Boadicea the Victorious'),
    ('borntostandout', 'Borntostandout Perfumes', 'Born To Stand Out'),
    ('calvin-klein', 'Calvin Klein Perfumes', 'Calvin Klein'),
    ('chanel', 'Chanel Perfumes', 'Chanel'),
    ('cristiano-ronaldo', 'Cristiano Ronaldo Perfumes', 'Cristiano Ronaldo'),
    ('davidoff', 'Davidoff Perfumes', 'Davidoff'),
    ('dior', 'Dior Perfumes', 'Dior'),
    ('dolce-and-gabbana', 'Dolce & Gabbana Perfumes', 'Dolce & Gabbana'),
    ('elan-dor', 'Elan Dor Perfumes', 'Elan Dor'),
    ('ex-nihilo', 'Ex Nihilo Perfumes', 'Ex Nihilo'),
    ('farzanas-collection', 'Farzanas Collection Perfumes', 'Farzanas Collection'),
    ('fragrance-secrets', 'Fragrance Secrets Perfumes', 'Fragrance Secrets'),
    ('french-avenue', 'French Avenue Perfumes', 'French Avenue'),
    ('giorgio-armani', 'Giorgio Armani Perfumes', 'Giorgio Armani'),
    ('hevora', 'Hevora Perfumes', 'Hevora'),
    ('house-of-morais', 'House of Morais Perfumes', 'House of Morais'),
    ('hugo-boss', 'Hugo Boss Perfumes', 'Hugo Boss'),
    ('ibrahim-al-qurashi', 'Ibrahim Al Qurashi Perfumes', 'Ibrahim Alqurashi'),
    ('jay-marley', 'Jay Marley Perfumes', 'Jay Marley'),
    ('jean-paul-gaultier', 'Jean Paul Gaultier Perfumes', 'Jean Paul Gaultier'),
    ('khaleej-pride', 'Khaleej Pride Perfumes', 'Khaleej Pride'),
    ('la-parfum-galleria', 'La Parfum Galleria Perfumes', 'La Parfum Galleria'),
    ('la-parfum-galleria-exclusif', 'La Parfum Galleria Exclusif Perfumes', 'La Parfum Galleria Exclusif'),
    ('lattafa', 'Lattafa Perfumes', 'Lattafa'),
    ('mancera', 'Mancera Perfumes', 'Mancera'),
    ('marxzelle', 'Marxzelle Perfumes', 'Marxzelle'),
    ('niche-profumo', 'Niche Profumo Perfumes', 'Niche Profumo'),
    ('orchid', 'Orchid Perfumes', 'Orchid'),
    ('paris-collection', 'Paris Collection Perfumes', 'Paris Collection'),
    ('parisbelle', 'Parisbelle Perfumes', 'Parisbelle'),
    ('prada', 'Prada Perfumes', 'Prada'),
    ('rafaan', 'Rafaan Perfumes', 'Rafaan'),
    ('ralph-lauren', 'Ralph Lauren Perfumes', 'Ralph Lauren'),
    ('rasasi', 'Rasasi Perfumes', 'Rasasi'),
    ('rayhaan', 'Rayhaan Perfumes', 'Rayhaan'),
    ('reef', 'Reef Perfumes', 'Reef'),
    ('riiffs', 'RiiFFS Perfumes', 'RiiFFS'),
    ('roberto-cavalli', 'Roberto Cavalli Perfumes', 'Roberto Cavalli'),
    ('sabrina-carpenter', 'Sabrina Carpenter Perfumes', 'Sabrina Carpenter'),
    ('swiss-arabian', 'Swiss Arabian Perfumes', 'Swiss Arabian'),
    ('yves-saint-laurent', 'Yves Saint Laurent Perfumes', 'Yves Saint Laurent'),
]

LOOKUP = """
query Existing($q: String!) {
  collections(first: 250, query: $q) { nodes { id handle templateSuffix } }
}
"""

ONLINE_STORE = """
query OnlineStore { channels(first: 25) { nodes { id name } } }
"""

CREATE = """
mutation CreateBrandCollection($input: CollectionInput!) {
  collectionCreate(input: $input) {
    collection { id handle title templateSuffix }
    userErrors { field message }
  }
}
"""

PUBLISH = """
mutation Publish($id: ID!, $input: [PublicationInput!]!) {
  publishablePublish(id: $id, input: $input) {
    userErrors { field message }
  }
}
"""

PUBLISH_STATUS = """
query PublishStatus($q: String!) {
  collections(first: 250, query: $q) {
    nodes { id handle resourcePublicationsCount { count } }
  }
}
"""


def online_store_publication(client):
    """The Online Store publication shares its numeric id with the channel."""
    for node in client.call(ONLINE_STORE)["channels"]["nodes"]:
        if node["name"] == "Online Store":
            return node["id"].replace("/Channel/", "/Publication/")
    return None


def publish_all(client, existing, apply):
    """Publish brand collections to the Online Store. Shopify creates
    collections unpublished via the API, and an unpublished collection is
    invisible to Liquid — its page 404s and it cannot be looked up."""
    publication = online_store_publication(client)
    if not publication:
        sys.exit("%sCould not find the Online Store channel.%s" % (RED, RESET))

    handles = [h for h, _, _ in BRANDS if h in existing]
    counts = client.call(PUBLISH_STATUS, {"q": " OR ".join("handle:%s" % h for h in handles)})
    unpublished = [n for n in counts["collections"]["nodes"]
                   if n["resourcePublicationsCount"]["count"] == 0]

    print("%d brand collections | %d already published | %d to publish"
          % (len(handles), len(handles) - len(unpublished), len(unpublished)))
    if not unpublished:
        return
    for node in unpublished:
        print("  %s-> %s %s" % (YELLOW, RESET, node["handle"]))
    if not apply:
        print("\n%sDry run — nothing written. Add --apply.%s" % (DIM, RESET))
        return

    print("\nPublishing...")
    failures = 0
    for node in unpublished:
        result = client.call(PUBLISH, {"id": node["id"],
                                      "input": [{"publicationId": publication}]})
        errors = result["publishablePublish"]["userErrors"]
        if errors:
            failures += 1
            print("  %s !! %s %-30s %s" % (RED, RESET, node["handle"],
                                           "; ".join(e["message"] for e in errors)))
        else:
            print("  %s ok %s %s" % (GREEN, RESET, node["handle"]))
        time.sleep(0.15)
    print("\n%d published, %d failed" % (len(unpublished) - failures, failures))
    if failures:
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--apply", action="store_true", help="create the collections")
    parser.add_argument("--publish", action="store_true",
                        help="publish existing brand collections to the Online Store "
                             "(a collection Shopify has not published is invisible to Liquid)")
    parser.add_argument("--resolve-ip", help="see set-collection-templates.py")
    args = parser.parse_args()

    dotenv = sct.load_dotenv()
    store = sct.credential(dotenv, "SHOPIFY_STORE_DOMAIN", "SHOPIFY_STORE")
    token = sct.credential(dotenv, "SHOPIFY_ADMIN_ACCESS_TOKEN", "SHOPIFY_ADMIN_TOKEN")
    version = sct.credential(dotenv, "SHOPIFY_API_VERSION") or sct.DEFAULT_API_VERSION
    if not store or not token:
        sys.exit("No credentials found — see --help.")

    host = store.replace("https://", "").replace("http://", "").strip("/")
    if args.resolve_ip:
        sct.pin_host(host, args.resolve_ip)
    client = sct.Shopify(host, token, version)
    print("%sStore:%s %s\n" % (DIM, RESET, host))

    query = " OR ".join("handle:%s" % h for h, _, _ in BRANDS)
    existing = {n["handle"]: n for n in client.call(LOOKUP, {"q": query})["collections"]["nodes"]}

    if args.publish:
        publish_all(client, existing, args.apply)
        return

    todo = [b for b in BRANDS if b[0] not in existing]
    for handle, title, vendor in BRANDS:
        if handle in existing:
            print("  %s ok %s %-30s exists" % (GREEN, RESET, handle))
        elif vendor:
            print("  %s-> %s %-30s create, vendor = %s" % (YELLOW, RESET, handle, vendor))
        else:
            print("  %s-> %s %-30s create, %sno vendor rule — add products by hand%s"
                  % (YELLOW, RESET, handle, RED, RESET))

    print("\n%d to create, %d already exist" % (len(todo), len(existing)))
    if not todo:
        return
    if not args.apply:
        print("\n%sDry run — nothing written. Re-run with --apply.%s" % (DIM, RESET))
        return

    publication = online_store_publication(client)
    if not publication:
        print("%sCould not find the Online Store publication; collections will be created "
              "unpublished.%s" % (YELLOW, RESET))

    print("\nCreating...")
    failures = 0
    for handle, title, vendor in todo:
        payload = {"title": title, "handle": handle}
        # Pointing a collection at a template the theme does not contain breaks
        # its page, so only set the suffix when the file is really there.
        template = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                "templates", "collection.%s.json" % handle)
        if os.path.exists(template):
            payload["templateSuffix"] = handle
        if vendor:
            payload["ruleSet"] = {
                "appliedDisjunctively": False,
                "rules": [{"column": "VENDOR", "relation": "EQUALS", "condition": vendor}],
            }
        result = client.call(CREATE, {"input": payload})["collectionCreate"]
        if result["userErrors"]:
            failures += 1
            print("  %s !! %s %-30s %s" % (RED, RESET, handle,
                                           "; ".join(e["message"] for e in result["userErrors"])))
            continue
        collection = result["collection"]
        note = ""
        if publication:
            pub = client.call(PUBLISH, {"id": collection["id"],
                                        "input": [{"publicationId": publication}]})
            errors = pub["publishablePublish"]["userErrors"]
            note = " (publish failed: %s)" % errors[0]["message"] if errors else " + published"
        print("  %s ok %s %-30s template: %s%s"
              % (GREEN, RESET, collection["handle"], collection["templateSuffix"], note))

    print("\n%d created, %d failed" % (len(todo) - failures, failures))
    if failures:
        sys.exit(1)


if __name__ == "__main__":
    main()
