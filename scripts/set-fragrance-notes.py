#!/usr/bin/env python3
"""Set the fragrance pyramid metafields from the notes spreadsheet.

Reads "Fragrance Note Missing Products - Sheet1.csv" and writes custom.notes_top,
custom.notes_heart and custom.notes_base for each product it names.

Rows whose three note columns are all "Not Available" (or blank, or
"(Discontinued Product)") get those metafields DELETED rather than filled. The
product template already hides the whole pyramid when all three are empty, so
clearing them is what makes the section disappear — leaving the literal text
"Not Available" on the page instead is the thing to avoid.

Matching, in order: unique SKU, then exact title, then a normalised title. Three
SKUs in the sheet are shared by two different products each (Pour Homme vs Pour
Femme, Blush vs Blush Intense, Ameera hamper vs Ameera), so SKU alone is not
enough and those fall through to the title. Anything unmatched is reported, never
guessed.

The definitions are single_line_text_field, so values are normalised to one line:
newlines and stray separators collapse to ", ".

Usage
-----
    python3 scripts/set-fragrance-notes.py             # dry run, changes nothing
    python3 scripts/set-fragrance-notes.py --apply     # write the changes
    python3 scripts/set-fragrance-notes.py --hide-only # only the clears
    python3 scripts/set-fragrance-notes.py --unmatched # just the match report

Credentials come from .env in the repo root (gitignored), falling back to the
environment:

    SHOPIFY_STORE_DOMAIN / SHOPIFY_STORE               your-store.myshopify.com
    SHOPIFY_ADMIN_ACCESS_TOKEN / SHOPIFY_ADMIN_TOKEN   shpat_xxxxxxxxxxxxxxxx
    SHOPIFY_API_VERSION                                optional, defaults below

The token needs write_products. Nothing is written without --apply.

Requires no third-party packages.
"""

import argparse
import csv
import json
import os
import re
import ssl
import sys
import time
import urllib.error
import urllib.request

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_CSV = os.path.join(REPO, "Fragrance Note Missing Products - Sheet1.csv")
NOTE_KEYS = ("notes_top", "notes_heart", "notes_base")

# A note column that means "we have no pyramid for this product".
UNAVAILABLE = re.compile(
    r"^\s*(not\s*available|not\s*applicable|n/?a|none|nil|-{1,3}|\(?discontinued(\s+product)?\)?)\s*$",
    re.I,
)

GREEN, YELLOW, RED, CYAN, DIM, RESET = ("\033[32m", "\033[33m", "\033[31m",
                                        "\033[36m", "\033[2m", "\033[0m")
DEFAULT_API_VERSION = "2025-01"

ALL_PRODUCTS = """
query AllProducts($after: String) {
  products(first: 100, after: $after) {
    nodes {
      id
      title
      handle
      variants(first: 20) { nodes { sku } }
      notesTop: metafield(namespace: "custom", key: "notes_top") { value }
      notesHeart: metafield(namespace: "custom", key: "notes_heart") { value }
      notesBase: metafield(namespace: "custom", key: "notes_base") { value }
    }
    pageInfo { hasNextPage endCursor }
  }
}
"""

SET_METAFIELDS = """
mutation SetNotes($metafields: [MetafieldsSetInput!]!) {
  metafieldsSet(metafields: $metafields) {
    metafields { key value }
    userErrors { field message }
  }
}
"""

DELETE_METAFIELDS = """
mutation ClearNotes($metafields: [MetafieldIdentifierInput!]!) {
  metafieldsDelete(metafields: $metafields) {
    deletedMetafields { key }
    userErrors { field message }
  }
}
"""


# ---------------------------------------------------------------- spreadsheet

def normalise_note(value):
    """One line, comma separated. The sheet mixes newlines and commas."""
    if value is None:
        return ""
    text = value.replace("\r", "\n")
    parts = [p.strip(" ,;\t") for p in text.split("\n")]
    parts = [p for p in parts if p]
    joined = ", ".join(parts)
    joined = re.sub(r"\s*,\s*", ", ", joined)
    joined = re.sub(r"(,\s*)+", ", ", joined)
    return re.sub(r"\s{2,}", " ", joined).strip(" ,")


def title_key(text):
    return re.sub(r"[^a-z0-9]+", " ", (text or "").lower()).strip()


def read_sheet(path):
    with open(path, newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.DictReader(handle))
    parsed = []
    for index, row in enumerate(rows, start=2):
        raw = {key: (row.get(key) or "") for key in NOTE_KEYS}
        unavailable = all(UNAVAILABLE.match(raw[key].strip()) or not raw[key].strip()
                          for key in NOTE_KEYS)
        notes = {key: normalise_note(raw[key]) for key in NOTE_KEYS}
        if not unavailable:
            # a single column reading "Not Available" inside an otherwise filled
            # row should still be dropped rather than printed on the page
            for key in NOTE_KEYS:
                if UNAVAILABLE.match(raw[key].strip()):
                    notes[key] = ""
        parsed.append({
            "line": index,
            "sku": (row.get("sku") or "").strip(),
            "title": (row.get("title") or "").strip(),
            "unavailable": unavailable,
            "notes": notes,
        })
    return parsed


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
            self.url, data=payload,
            headers={"Content-Type": "application/json",
                     "X-Shopify-Access-Token": self.token,
                     "Accept": "application/json"})
        try:
            with urllib.request.urlopen(request, timeout=60, context=self.ssl) as response:
                body = json.loads(response.read().decode())
        except urllib.error.HTTPError as exc:
            sys.exit("%sHTTP %s from Shopify: %s%s"
                     % (RED, exc.code, exc.read().decode(errors="replace")[:400], RESET))
        except urllib.error.URLError as exc:
            sys.exit("%sCould not reach %s: %s%s" % (RED, self.url, exc.reason, RESET))
        if body.get("errors"):
            sys.exit("%sGraphQL error: %s%s" % (RED, json.dumps(body["errors"], indent=2), RESET))
        return body["data"]

    def all_products(self):
        cursor, rows = None, []
        while True:
            data = self.call(ALL_PRODUCTS, {"after": cursor})["products"]
            rows.extend(data["nodes"])
            if not data["pageInfo"]["hasNextPage"]:
                break
            cursor = data["pageInfo"]["endCursor"]
            time.sleep(0.15)
        return rows


# ---------------------------------------------------------------- main

def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--apply", action="store_true", help="write the changes")
    parser.add_argument("--hide-only", action="store_true",
                        help="only clear the notes on unavailable products")
    parser.add_argument("--unmatched", action="store_true",
                        help="just report which sheet rows matched a product")
    parser.add_argument("--csv", default=DEFAULT_CSV, help="path to the notes sheet")
    parser.add_argument("--store", help="myshopify domain")
    parser.add_argument("--token", help="Admin API token")
    parser.add_argument("--api-version", help="defaults to .env or %s" % DEFAULT_API_VERSION)
    parser.add_argument("--resolve-ip", help="connect to this IP for the store host")
    args = parser.parse_args()

    sheet = read_sheet(args.csv)
    hide_count = sum(1 for row in sheet if row["unavailable"])
    print("%sRead %d rows: %d with notes, %d marked unavailable%s"
          % (DIM, len(sheet), len(sheet) - hide_count, hide_count, RESET))

    dotenv = load_dotenv()
    store = args.store or credential(dotenv, "SHOPIFY_STORE_DOMAIN", "SHOPIFY_STORE")
    token = args.token or credential(dotenv, "SHOPIFY_ADMIN_ACCESS_TOKEN", "SHOPIFY_ADMIN_TOKEN")
    api_version = args.api_version or credential(dotenv, "SHOPIFY_API_VERSION") or DEFAULT_API_VERSION
    if not store or not token:
        sys.exit("No credentials found. Add SHOPIFY_STORE_DOMAIN and "
                 "SHOPIFY_ADMIN_ACCESS_TOKEN to .env, or pass --store / --token.")

    host = store.replace("https://", "").replace("http://", "").strip("/")
    if args.resolve_ip:
        pin_host(host, args.resolve_ip)
    client = Shopify(host, token, api_version)
    print("%sStore:%s %s   %sAPI:%s %s\n" % (DIM, RESET, host, DIM, RESET, api_version))

    products = client.all_products()
    print("%s%d products in the store%s\n" % (DIM, len(products), RESET))

    by_sku, by_title, by_norm = {}, {}, {}
    for product in products:
        for variant in product["variants"]["nodes"]:
            sku = (variant["sku"] or "").strip()
            if sku:
                by_sku.setdefault(sku, []).append(product)
        by_title.setdefault(product["title"].strip(), []).append(product)
        by_norm.setdefault(title_key(product["title"]), []).append(product)

    planned_set, planned_clear, unchanged, unmatched, ambiguous = [], [], [], [], []
    for row in sheet:
        matches = by_sku.get(row["sku"], [])
        how = "sku"
        if len(matches) != 1:
            exact = by_title.get(row["title"], [])
            if len(exact) == 1:
                matches, how = exact, "title"
            else:
                norm = by_norm.get(title_key(row["title"]), [])
                if len(norm) == 1:
                    matches, how = norm, "title~"
                elif matches:
                    ambiguous.append((row, len(matches)))
                    continue
        if len(matches) != 1:
            unmatched.append(row)
            continue
        product = matches[0]
        current = {
            "notes_top": (product.get("notesTop") or {}).get("value") or "",
            "notes_heart": (product.get("notesHeart") or {}).get("value") or "",
            "notes_base": (product.get("notesBase") or {}).get("value") or "",
        }
        if row["unavailable"]:
            present = [key for key in NOTE_KEYS if current[key]]
            if present:
                planned_clear.append((row, product, present, how))
            else:
                unchanged.append((row, product, "already empty"))
        else:
            if args.hide_only:
                continue
            if all(current[key] == row["notes"][key] for key in NOTE_KEYS):
                unchanged.append((row, product, "already correct"))
            else:
                planned_set.append((row, product, current, how))

    if args.unmatched:
        for row, product, current, how in planned_set:
            print("  %s ok %s %-6s %s" % (GREEN, RESET, how, product["title"][:70]))
        for row, product, present, how in planned_clear:
            print("  %s hide %s %-5s %s" % (YELLOW, RESET, how, product["title"][:70]))
    else:
        for row, product, current, how in planned_set:
            print("\n%s%s%s %s(line %d, %s)%s" % (CYAN, product["title"][:72], RESET,
                                                  DIM, row["line"], how, RESET))
            for key in NOTE_KEYS:
                if current[key] != row["notes"][key]:
                    label = key.replace("notes_", "")
                    if current[key]:
                        print("  %s%-6s- %s%s" % (RED, label, current[key][:88], RESET))
                    print("  %s%-6s+ %s%s" % (GREEN, label, row["notes"][key][:88] or "(empty)", RESET))
        if planned_clear:
            print("\n%sNotes to clear — the pyramid hides itself once all three are empty%s"
                  % (YELLOW, RESET))
            for row, product, present, how in planned_clear:
                print("  %s hide %s %-64s clearing: %s"
                      % (YELLOW, RESET, product["title"][:64], ", ".join(present)))

    if ambiguous:
        print("\n%sSKU matched more than one product and the title did not resolve it%s" % (RED, RESET))
        for row, count in ambiguous:
            print("  line %-5d sku=%-30s %d products  %s" % (row["line"], row["sku"], count, row["title"][:50]))
    if unmatched:
        print("\n%s%d sheet rows matched no product%s" % (RED, len(unmatched), RESET))
        for row in unmatched:
            print("  line %-5d sku=%-30s %s" % (row["line"], row["sku"] or "(blank)", row["title"][:60]))

    print("\n%d to write, %d to clear, %d already correct, %d unmatched, %d ambiguous"
          % (len(planned_set), len(planned_clear), len(unchanged), len(unmatched), len(ambiguous)))

    if not (planned_set or planned_clear):
        return
    if not args.apply:
        print("%sDry run — nothing written. Re-run with --apply to make these changes.%s"
              % (DIM, RESET))
        return

    print("\nApplying...")
    failures = 0
    for row, product, current, how in planned_set:
        fields = [{"ownerId": product["id"], "namespace": "custom", "key": key,
                   "type": "single_line_text_field", "value": row["notes"][key]}
                  for key in NOTE_KEYS if row["notes"][key]]
        blanks = [key for key in NOTE_KEYS if not row["notes"][key] and current[key]]
        result = client.call(SET_METAFIELDS, {"metafields": fields})["metafieldsSet"]
        errors = result["userErrors"]
        if blanks and not errors:
            drop = [{"ownerId": product["id"], "namespace": "custom", "key": key} for key in blanks]
            errors = client.call(DELETE_METAFIELDS, {"metafields": drop})["metafieldsDelete"]["userErrors"]
        if errors:
            failures += 1
            print("  %s !! %s %-60s %s" % (RED, RESET, product["title"][:60],
                                           "; ".join(e["message"] for e in errors)))
        else:
            print("  %s ok %s %s" % (GREEN, RESET, product["title"][:70]))
        time.sleep(0.2)

    for row, product, present, how in planned_clear:
        drop = [{"ownerId": product["id"], "namespace": "custom", "key": key} for key in present]
        errors = client.call(DELETE_METAFIELDS, {"metafields": drop})["metafieldsDelete"]["userErrors"]
        if errors:
            failures += 1
            print("  %s !! %s %-60s %s" % (RED, RESET, product["title"][:60],
                                           "; ".join(e["message"] for e in errors)))
        else:
            print("  %s hide %s %s" % (YELLOW, RESET, product["title"][:70]))
        time.sleep(0.2)

    total = len(planned_set) + len(planned_clear)
    print("\n%d updated, %d failed" % (total - failures, failures))
    if failures:
        sys.exit(1)


if __name__ == "__main__":
    main()
