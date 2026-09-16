#!/usr/bin/env python3
"""Read the store's real policy text out of admin.

The theme's legal pages were written by hand in Liquid, so whatever the
merchant maintains in Settings › Policies (and in Online Store › Pages) never
reached the storefront. This reads both, so the two can be compared before
anything is changed.

Read-only: it writes nothing to Shopify. With --out it saves each body to a
file so the text can be diffed or inspected properly.

    python3 scripts/dump-policies.py                 # summary
    python3 scripts/dump-policies.py --full          # print whole bodies
    python3 scripts/dump-policies.py --out tmp/pol   # save each to a file
"""

import argparse
import html.parser
import importlib.util
import os
import re
import sys
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location(
    "sct", os.path.join(HERE, "set-collection-templates.py"))
sct = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sct)

GREEN, YELLOW, RED, DIM, RESET = sct.GREEN, sct.YELLOW, sct.RED, sct.DIM, sct.RESET

POLICIES = """
{
  shop {
    primaryDomain { url }
    shopPolicies { id type title body url }
  }
}
"""

DOMAIN = """
{ shop { primaryDomain { url } } }
"""

# The public URL each policy is published at, when it has been filled in.
PUBLIC_PATHS = {
    "PRIVACY_POLICY": "/policies/privacy-policy",
    "REFUND_POLICY": "/policies/refund-policy",
    "SHIPPING_POLICY": "/policies/shipping-policy",
    "TERMS_OF_SERVICE": "/policies/terms-of-service",
}

PAGES = """
query($cursor: String) {
  pages(first: 50, after: $cursor) {
    pageInfo { hasNextPage endCursor }
    nodes { id handle title bodySummary body templateSuffix }
  }
}
"""

# theme section -> the Liquid policy object that should feed it
THEME_PAGES = {
    "privacy-policy": "privacy_policy",
    "return-policy": "refund_policy",
    "shipping-policy": "shipping_policy",
    "terms-of-service": "terms_of_service",
    "payment-policy": None,          # Shopify has no payment policy type
}


class Text(html.parser.HTMLParser):
    """Strip tags so lengths and previews describe the words, not the markup."""

    def __init__(self):
        super().__init__()
        self.parts = []

    def handle_data(self, data):
        self.parts.append(data)

    @classmethod
    def of(cls, markup):
        parser = cls()
        parser.feed(markup or "")
        return re.sub(r"\s+", " ", "".join(parser.parts)).strip()


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--full", action="store_true", help="print each body in full")
    parser.add_argument("--out", metavar="DIR", help="save each body to DIR/<handle>.html")
    args = parser.parse_args()

    dotenv = sct.load_dotenv()
    store = sct.credential(dotenv, "SHOPIFY_STORE_DOMAIN")
    token = sct.credential(dotenv, "SHOPIFY_ADMIN_ACCESS_TOKEN")
    version = sct.credential(dotenv, "SHOPIFY_API_VERSION") or sct.DEFAULT_API_VERSION
    if not store or not token:
        sys.exit("%sMissing credentials in .env%s" % (RED, RESET))

    client = sct.Shopify(store, token, version)
    if args.out:
        os.makedirs(args.out, exist_ok=True)

    print("%sSettings › Policies%s" % (DIM, RESET))
    # A missing scope is a state to report and work around, not a crash: the
    # same text is published at /policies/* for anyone to read. Shopify's own
    # message is printed rather than a remembered scope name, because which
    # scope a field needs is Shopify's to say.
    body = client.call_raw(POLICIES)
    if body.get("errors"):
        for error in body["errors"]:
            message = str(error.get("message", error))
            # Shopify usually names the scope in the message itself; only add
            # the extension when it would say something new.
            required = (error.get("extensions") or {}).get("requiredAccess")
            if required and str(required).strip("`") not in message:
                message += " (needs %s)" % required
            print("  %s%s%s" % (YELLOW, message, RESET))
        print("  %sreading the published pages instead%s" % (DIM, RESET))
        policies = None
    else:
        policies = body["data"]["shop"]["shopPolicies"] or []

    if policies is None:
        domain = client.call(DOMAIN)["shop"]["primaryDomain"]["url"].rstrip("/")
        policies = []
        for kind, path in PUBLIC_PATHS.items():
            body, status = fetch(domain + path)
            if body is None:
                print("  %-22s %snot published (%s)%s" % (kind, YELLOW, status, RESET))
                continue
            words = Text.of(body)
            print("  %-22s %spublished%s  %d chars of text at %s"
                  % (kind, GREEN, RESET, len(words), path))
            print("    %s%s…%s" % (DIM, words[:160], RESET))
            policies.append({"type": kind, "title": kind.replace("_", " ").title(),
                             "body": body, "url": domain + path})
            if args.out:
                with open(os.path.join(args.out, "policy-%s.html" % kind.lower()),
                          "w", encoding="utf-8") as handle:
                    handle.write(body)
        print("")
        report_pages(client, args)
        report_mapping(policies)
        return
    by_type = {}
    for policy in policies:
        kind = policy["type"]
        by_type[kind] = policy
        words = Text.of(policy.get("body"))
        print("  %-22s %s%s%s  %d chars of markup, %d of text"
              % (kind, GREEN if words else YELLOW, policy.get("title") or "(untitled)", RESET,
                 len(policy.get("body") or ""), len(words)))
        if words:
            print("    %s%s…%s" % (DIM, words[:160], RESET))
        if args.out and policy.get("body"):
            path = os.path.join(args.out, "policy-%s.html" % kind.lower())
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(policy["body"])
        if args.full:
            print(policy.get("body") or "")

    report_pages(client, args)
    report_mapping(policies)


def fetch(url):
    """A policy page as published. 404 means the merchant never filled it in."""
    request = urllib.request.Request(url, headers={"User-Agent": "tfs-policy-audit"})
    try:
        with urllib.request.urlopen(request, timeout=30, context=sct.ssl_context()) as response:
            return response.read().decode("utf-8", "replace"), response.status
    except urllib.error.HTTPError as exc:
        return None, "HTTP %s" % exc.code
    except urllib.error.URLError as exc:
        return None, exc.reason


def report_pages(client, args):
    print("\n%sOnline Store › Pages (legal handles only)%s" % (DIM, RESET))
    cursor, pages = None, []
    while True:
        page = client.call(PAGES, {"cursor": cursor})["pages"]
        pages.extend(page["nodes"])
        if not page["pageInfo"]["hasNextPage"]:
            break
        cursor = page["pageInfo"]["endCursor"]

    for handle in THEME_PAGES:
        match = next((p for p in pages if p["handle"] == handle), None)
        if not match:
            print("  %-22s %sno page with this handle%s" % (handle, YELLOW, RESET))
            continue
        words = Text.of(match.get("body"))
        print("  %-22s %s  suffix=%s, %d chars of text"
              % (handle, match["title"], match.get("templateSuffix"), len(words)))
        if words:
            print("    %s%s…%s" % (DIM, words[:160], RESET))
        if args.out and match.get("body"):
            path = os.path.join(args.out, "page-%s.html" % handle)
            with open(path, "w", encoding="utf-8") as out:
                out.write(match["body"])

def report_mapping(policies):
    print("\n%sWhat the theme should read%s" % (DIM, RESET))
    for handle, liquid in THEME_PAGES.items():
        if liquid is None:
            print("  %-22s %sno Shopify policy of this kind%s" % (handle, YELLOW, RESET))
            continue
        kind = liquid.upper()
        present = any(p["type"].upper().replace("_", "") == kind.replace("_", "")
                      for p in policies)
        print("  %-22s shop.%-18s %s" % (handle, liquid,
                                         (GREEN + "has content" + RESET) if present
                                         else (YELLOW + "empty in admin" + RESET)))


if __name__ == "__main__":
    main()
