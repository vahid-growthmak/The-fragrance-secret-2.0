#!/usr/bin/env python3
"""Set the SEO meta title and description on every collection and hub page.

The copy is read straight out of the source .docx files, from the "Meta Title" /
"Meta Description" pair in each document's on-page SEO section, so the store
always matches the signed-off content rather than a transcription of it.

Two things make the mapping non-obvious, and both are handled here:

  * The canonical URLs in the documents do not match the store's real handles --
    the docs say /collections/mens-perfumes while the collection is "mens". Docs
    are matched to the store by exact handle, then by dropping a trailing
    -perfumes/-perfume/-scents, then through ALIASES for the genuinely renamed
    ones. Anything still unmatched is reported, never guessed.
  * The four hub documents are pages, not collections, so they are listed
    explicitly in HUBS.

Collections are written with collectionUpdate's typed seo field. Pages have no
equivalent, so they get the global.title_tag / global.description_tag metafields
that Shopify itself uses -- the same values page_title and page_description read
in Liquid.

Usage
-----
    python3 scripts/set-seo-meta.py                 # dry run, changes nothing
    python3 scripts/set-seo-meta.py --apply         # write the changes
    python3 scripts/set-seo-meta.py --only mens     # one handle (repeatable)
    python3 scripts/set-seo-meta.py --unmatched     # just the mapping report

Credentials come from .env in the repo root (gitignored), falling back to the
environment:

    SHOPIFY_STORE_DOMAIN / SHOPIFY_STORE               your-store.myshopify.com
    SHOPIFY_ADMIN_ACCESS_TOKEN / SHOPIFY_ADMIN_TOKEN   shpat_xxxxxxxxxxxxxxxx
    SHOPIFY_API_VERSION                                optional, defaults below

The token needs write_products for collections and write_content for pages.
Nothing is written without --apply.

Requires no third-party packages.
"""

import argparse
import glob
import html
import json
import os
import re
import ssl
import sys
import time
import urllib.error
import urllib.request
import zipfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Documents whose canonical URL cannot be reduced to the store handle by rule.
ALIASES = {
    "perfume-oils": "perfume-oil",
    "party-wear-perfumes": "party-clubbing",
    "formal-event-perfumes": "wedding-formal",
    "evening-wear-perfumes": "dinner-evening",
    "travel-perfumes": "travel-friendly",
    "beach-perfumes": "beach-vacation",
    "vacation-perfumes": "vacation-beach",
}

# Hub documents are pages. doc handle -> page handle.
HUBS = {
    "brands": "brands",
    "lifestyle": "shop-by-lifestyle",
    "shop-by-scent-family": "shop-by-scent-family",
}

# Google truncates around these; the documents' copy deliberately runs longer in
# places, so this only warns.
TITLE_LIMIT, DESCRIPTION_LIMIT = 60, 160

ALL_COLLECTIONS = """
query AllCollections($after: String) {
  collections(first: 250, after: $after) {
    nodes { id handle title seo { title description } }
    pageInfo { hasNextPage endCursor }
  }
}
"""

ALL_PAGES = """
query AllPages($after: String) {
  pages(first: 250, after: $after) {
    nodes {
      id handle title
      titleTag: metafield(namespace: "global", key: "title_tag") { value }
      descriptionTag: metafield(namespace: "global", key: "description_tag") { value }
    }
    pageInfo { hasNextPage endCursor }
  }
}
"""

COLLECTION_SEO = """
mutation SetCollectionSeo($input: CollectionInput!) {
  collectionUpdate(input: $input) {
    collection { handle seo { title description } }
    userErrors { field message }
  }
}
"""

PAGE_SEO = """
mutation SetPageSeo($metafields: [MetafieldsSetInput!]!) {
  metafieldsSet(metafields: $metafields) {
    metafields { key value }
    userErrors { field message }
  }
}
"""

GREEN, YELLOW, RED, DIM, RESET = "\033[32m", "\033[33m", "\033[31m", "\033[2m", "\033[0m"

DEFAULT_API_VERSION = "2025-01"


# ---------------------------------------------------------------- documents

def docx_lines(path):
    with zipfile.ZipFile(path) as archive:
        xml = archive.read("word/document.xml").decode("utf-8", "replace")
    xml = re.sub(r"</w:p>", "\n", xml)
    xml = re.sub(r"<[^>]+>", "", xml)
    return [html.unescape(line).strip() for line in xml.split("\n") if html.unescape(line).strip()]


def read_documents(root):
    """Pull the Meta Title / Meta Description pair out of every source document.

    The labels appear twice per document: once as the values themselves, and
    again in ALL CAPS in the commentary that follows, where the text is a note
    about character counts rather than the tag. Only the exact-case labels are
    read, and only the first of each.
    """
    found, skipped = [], []
    for path in sorted(glob.glob(os.path.join(root, "*", "*.docx"))):
        lines = docx_lines(path)
        url = next((line for line in lines[:14] if "thefragrancesecrets.com/" in line), None)
        title = description = None
        for index, line in enumerate(lines):
            if line == "Meta Title" and title is None and index + 1 < len(lines):
                title = lines[index + 1]
            elif line == "Meta Description" and description is None and index + 1 < len(lines):
                description = lines[index + 1]

        name = os.path.relpath(path, root)
        if not url:
            skipped.append((name, "no canonical URL line"))
            continue
        if not (title and description):
            skipped.append((name, "no Meta Title / Meta Description pair"))
            continue

        path_part = url.split("thefragrancesecrets.com", 1)[1].split()[0]
        handle = path_part.rstrip("/").split("/")[-1]
        if "/collections/" in path_part:
            kind = "collection"
        elif "/pages/" in path_part:
            kind = "page"
        else:
            skipped.append((name, "URL %s is not a collection or page" % path_part))
            continue
        found.append({"doc": name, "kind": kind, "handle": handle,
                      "title": title, "description": description})
    return found, skipped


def candidates(handle):
    """Store handles this document handle might refer to, best guess first."""
    yield handle
    if handle in ALIASES:
        yield ALIASES[handle]
    for suffix in ("-perfumes", "-perfume", "-scents"):
        if handle.endswith(suffix):
            yield handle[: -len(suffix)]


# ---------------------------------------------------------------- transport

def load_dotenv():
    path = os.path.join(REPO, ".env")
    values = {}
    if not os.path.exists(path):
        return values
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            values[key.strip()] = value.strip().strip("'\"")
    return values


def credential(dotenv, *names):
    for name in names:
        value = os.environ.get(name) or dotenv.get(name)
        if value:
            return value
    return None


def ssl_context():
    """Some macOS Pythons ship without a usable CA bundle; find one rather than
    disabling verification."""
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        pass
    if not ssl.create_default_context().cert_store_stats()["x509_ca"]:
        for candidate in ("/etc/ssl/cert.pem", "/usr/local/etc/openssl@3/cert.pem",
                          "/opt/homebrew/etc/openssl@3/cert.pem",
                          "/etc/pki/tls/certs/ca-bundle.crt"):
            if os.path.exists(candidate):
                return ssl.create_default_context(cafile=candidate)
    return ssl.create_default_context()


def pin_host(hostname, address):
    """Work around a local resolver that NXDOMAINs a host public DNS resolves
    fine. TLS still verifies the certificate against the hostname."""
    import socket
    original = socket.getaddrinfo

    def patched(host, port, *args, **kwargs):
        if host == hostname:
            host = address
        return original(host, port, *args, **kwargs)

    socket.getaddrinfo = patched


class Shopify:
    def __init__(self, store, token, api_version):
        self.url = "https://%s/admin/api/%s/graphql.json" % (store, api_version)
        self.token = token
        self.ssl = ssl_context()

    def call(self, query, variables=None):
        payload = json.dumps({"query": query, "variables": variables or {}}).encode()
        request = urllib.request.Request(
            self.url,
            data=payload,
            headers={
                "Content-Type": "application/json",
                "X-Shopify-Access-Token": self.token,
                "Accept": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=30, context=self.ssl) as response:
                body = json.loads(response.read().decode())
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode(errors="replace")[:400]
            sys.exit("%sHTTP %s from Shopify: %s%s" % (RED, exc.code, detail, RESET))
        except urllib.error.URLError as exc:
            sys.exit("%sCould not reach %s: %s%s" % (RED, self.url, exc.reason, RESET))
        if body.get("errors"):
            sys.exit("%sGraphQL error: %s%s" % (RED, json.dumps(body["errors"], indent=2), RESET))
        return body["data"]

    def all_nodes(self, query, field):
        cursor, rows = None, []
        while True:
            data = self.call(query, {"after": cursor})[field]
            rows.extend(data["nodes"])
            if not data["pageInfo"]["hasNextPage"]:
                break
            cursor = data["pageInfo"]["endCursor"]
        return rows


# ---------------------------------------------------------------- main

def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--apply", action="store_true", help="write the changes (default is a dry run)")
    parser.add_argument("--only", action="append", metavar="HANDLE",
                        help="limit to this store handle; repeatable")
    parser.add_argument("--unmatched", action="store_true",
                        help="just report the document-to-store mapping and exit")
    parser.add_argument("--docs", default=REPO, help="folder holding the source .docx folders")
    parser.add_argument("--store", help="myshopify domain (defaults to .env SHOPIFY_STORE_DOMAIN)")
    parser.add_argument("--token", help="Admin API token (defaults to .env SHOPIFY_ADMIN_ACCESS_TOKEN)")
    parser.add_argument("--api-version",
                        help="defaults to .env SHOPIFY_API_VERSION or %s" % DEFAULT_API_VERSION)
    parser.add_argument("--resolve-ip", help="connect to this IP for the store host, for when the "
                                             "local resolver fails on a name public DNS resolves")
    args = parser.parse_args()

    documents, skipped = read_documents(args.docs)
    if not documents:
        sys.exit("No documents with a Meta Title / Meta Description pair under %s" % args.docs)
    print("%sRead %d documents%s" % (DIM, len(documents), RESET))
    for name, why in skipped:
        print("  %s -- %s %s(skipped)%s" % (name, why, DIM, RESET))

    dotenv = load_dotenv()
    store = args.store or credential(dotenv, "SHOPIFY_STORE_DOMAIN", "SHOPIFY_STORE")
    token = args.token or credential(dotenv, "SHOPIFY_ADMIN_ACCESS_TOKEN", "SHOPIFY_ADMIN_TOKEN")
    api_version = args.api_version or credential(dotenv, "SHOPIFY_API_VERSION") or DEFAULT_API_VERSION
    if not store or not token:
        sys.exit("No credentials found. Add SHOPIFY_STORE_DOMAIN and SHOPIFY_ADMIN_ACCESS_TOKEN to "
                 ".env, or pass --store / --token. See --help.")

    host = store.replace("https://", "").replace("http://", "").strip("/")
    if args.resolve_ip:
        pin_host(host, args.resolve_ip)
    client = Shopify(host, token, api_version)
    print("%sStore:%s %s   %sAPI:%s %s\n" % (DIM, RESET, host, DIM, RESET, api_version))

    collections = {node["handle"]: node for node in client.all_nodes(ALL_COLLECTIONS, "collections")}
    pages = {node["handle"]: node for node in client.all_nodes(ALL_PAGES, "pages")}
    print("%s%d collections, %d pages in the store%s\n" % (DIM, len(collections), len(pages), RESET))

    planned, unchanged, unmatched = [], [], []
    for doc in documents:
        node = kind = None
        if doc["handle"] in HUBS:
            node, kind = pages.get(HUBS[doc["handle"]]), "page"
        if node is None:
            for candidate in candidates(doc["handle"]):
                if candidate in collections:
                    node, kind = collections[candidate], "collection"
                    break
        if node is None and doc["handle"] in pages:
            node, kind = pages[doc["handle"]], "page"
        if node is None:
            unmatched.append(doc)
            continue
        if args.only and node["handle"] not in args.only:
            continue
        if kind == "collection":
            current = node.get("seo") or {}
        else:
            # pages keep SEO in the metafields Shopify itself reads
            current = {"title": (node.get("titleTag") or {}).get("value"),
                       "description": (node.get("descriptionTag") or {}).get("value")}
        if current.get("title") == doc["title"] and current.get("description") == doc["description"]:
            unchanged.append((node, kind))
        else:
            planned.append((node, kind, doc))

    if unmatched:
        print("%s%d documents matched no collection or page:%s" % (RED, len(unmatched), RESET))
        for doc in unmatched:
            print("  %s !! %s %-32s %s" % (RED, RESET, doc["handle"], doc["doc"][:54]))
        print("%s  Add these to ALIASES (or HUBS, if the content lives on a page) at the top\n"
              "  of this script. Nothing is guessed.%s\n" % (DIM, RESET))

    if args.unmatched:
        for node, kind, doc in planned:
            print("  %s ok %s %-9s %-32s <- %s" % (GREEN, RESET, kind, node["handle"], doc["doc"][:48]))
        print("\n%d mapped, %d unmatched" % (len(planned) + len(unchanged), len(unmatched)))
        return

    long_titles = long_descriptions = 0
    for node, kind, doc in planned:
        title_length, description_length = len(doc["title"]), len(doc["description"])
        title_flag = description_flag = " "
        if title_length > TITLE_LIMIT:
            title_flag, long_titles = "!", long_titles + 1
        if description_length > DESCRIPTION_LIMIT:
            description_flag, long_descriptions = "!", long_descriptions + 1
        print("  %s->%s %-9s %-30s T%s%3d %sD%s%3d" % (YELLOW, RESET, kind, node["handle"],
                                                       title_flag, title_length,
                                                       DIM if description_flag == " " else "",
                                                       description_flag, description_length))
        print("        %s%s%s" % (DIM, doc["title"][:96], RESET))

    for node, kind in unchanged:
        print("  %s ok %s %-9s %-30s already correct" % (GREEN, RESET, kind, node["handle"]))

    print("\n%d to write, %d already correct, %d unmatched" % (len(planned), len(unchanged), len(unmatched)))
    if long_titles or long_descriptions:
        print("%s%d titles over %d chars and %d descriptions over %d will be trimmed in search\n"
              "results. The source documents call this out and mark the copy final, so it is\n"
              "written verbatim -- shorten it in the documents if you want it to fit.%s"
              % (YELLOW, long_titles, TITLE_LIMIT, long_descriptions, DESCRIPTION_LIMIT, RESET))

    if not planned:
        return
    if not args.apply:
        print("\n%sDry run -- nothing written. Re-run with --apply to make these changes.%s" % (DIM, RESET))
        return

    print("\nApplying...")
    failures = 0
    for node, kind, doc in planned:
        if kind == "collection":
            result = client.call(COLLECTION_SEO, {"input": {
                "id": node["id"],
                "seo": {"title": doc["title"], "description": doc["description"]},
            }})["collectionUpdate"]
        else:
            result = client.call(PAGE_SEO, {"metafields": [
                {"ownerId": node["id"], "namespace": "global", "key": "title_tag",
                 "type": "single_line_text_field", "value": doc["title"]},
                {"ownerId": node["id"], "namespace": "global", "key": "description_tag",
                 "type": "multi_line_text_field", "value": doc["description"]},
            ]})["metafieldsSet"]
        errors = result["userErrors"]
        if errors:
            failures += 1
            print("  %s !! %s %-30s %s" % (RED, RESET, node["handle"],
                                           "; ".join(e["message"] for e in errors)))
        else:
            print("  %s ok %s %-9s %s" % (GREEN, RESET, kind, node["handle"]))
        time.sleep(0.2)  # stay well inside the GraphQL cost bucket

    print("\n%d written, %d failed" % (len(planned) - failures, failures))
    if failures:
        sys.exit(1)


if __name__ == "__main__":
    main()
