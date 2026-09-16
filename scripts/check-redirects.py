#!/usr/bin/env python3
"""Audit the store's 301s against every old URL this repo knows about.

Two migrations renamed things out from under their URLs: 333 products
(scripts/handle-rename-run.json) and 121 collections
(scripts/retire-collections-plan.json). Both runs recorded creating redirects,
but a run log says what a script believed at the time — the only proof is the
store, and an old URL that 404s is an indexed page losing its traffic.

This compares the two, and can check what the live site actually answers.

    python3 scripts/check-redirects.py                 # coverage from the API
    python3 scripts/check-redirects.py --probe 40      # also HTTP-check 40 of them
    python3 scripts/check-redirects.py --missing-out gaps.json

Read-only.
"""

import argparse
import importlib.util
import json
import os
import random
import sys
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
spec = importlib.util.spec_from_file_location(
    "sct", os.path.join(HERE, "set-collection-templates.py"))
sct = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sct)

GREEN, YELLOW, RED, DIM, RESET = sct.GREEN, sct.YELLOW, sct.RED, sct.DIM, sct.RESET

REDIRECTS = """
query($cursor: String) {
  urlRedirects(first: 250, after: $cursor) {
    pageInfo { hasNextPage endCursor }
    nodes { id path target }
  }
}
"""


def old_urls():
    """Every path this repo knows used to resolve, with where it should go now."""
    wanted = {}

    renames = os.path.join(HERE, "handle-rename-run.json")
    if os.path.exists(renames):
        with open(renames, encoding="utf-8") as handle:
            for row in json.load(handle).get("done", []):
                if row.get("old") and row.get("new") and row["old"] != row["new"]:
                    wanted["/products/%s" % row["old"]] = ("/products/%s" % row["new"], "product rename")

    plan = os.path.join(HERE, "retire-collections-plan.json")
    if os.path.exists(plan):
        with open(plan, encoding="utf-8") as handle:
            for old, spec_ in json.load(handle).items():
                target = spec_.get("redirect_to") or spec_.get("target") or spec_.get("keep")
                if target:
                    if not str(target).startswith("/"):
                        target = "/collections/%s" % target
                    wanted["/collections/%s" % old] = (target, "collection retired")
    return wanted


def live_redirects(client):
    cursor, rows = None, {}
    while True:
        page = client.call(REDIRECTS, {"cursor": cursor})["urlRedirects"]
        for node in page["nodes"]:
            rows[node["path"]] = node["target"]
        if not page["pageInfo"]["hasNextPage"]:
            return rows
        cursor = page["pageInfo"]["endCursor"]


def probe(url):
    """What the live site answers, without following the hop."""
    request = urllib.request.Request(url, method="HEAD",
                                     headers={"User-Agent": "tfs-redirect-audit"})

    class NoFollow(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, *args, **kwargs):
            return None

    opener = urllib.request.build_opener(NoFollow,
                                         urllib.request.HTTPSHandler(context=sct.ssl_context()))
    try:
        with opener.open(request, timeout=20) as response:
            return response.status, response.headers.get("Location")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.headers.get("Location")
    except urllib.error.URLError as exc:
        return None, str(exc.reason)


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--probe", type=int, default=0, metavar="N",
                        help="HTTP-check N old URLs on the live domain (0 = none)")
    parser.add_argument("--missing-out", metavar="FILE", help="write the uncovered paths to a JSON file")
    args = parser.parse_args()

    dotenv = sct.load_dotenv()
    store = sct.credential(dotenv, "SHOPIFY_STORE_DOMAIN")
    token = sct.credential(dotenv, "SHOPIFY_ADMIN_ACCESS_TOKEN")
    version = sct.credential(dotenv, "SHOPIFY_API_VERSION") or sct.DEFAULT_API_VERSION
    if not store or not token:
        sys.exit("%sMissing credentials in .env%s" % (RED, RESET))

    client = sct.Shopify(store, token, version)
    shop = client.call("{ shop { name primaryDomain { url } } }")["shop"]
    domain = shop["primaryDomain"]["url"].rstrip("/")
    print("%sStore%s %s (%s)\n" % (DIM, RESET, shop["name"], domain))

    wanted = old_urls()
    existing = live_redirects(client)
    print("%sold URLs in this repo%s   %d" % (DIM, RESET, len(wanted)))
    print("%sredirects on the store%s  %d\n" % (DIM, RESET, len(existing)))

    missing, wrong, covered = {}, {}, {}
    for path, (target, why) in sorted(wanted.items()):
        if path not in existing:
            missing[path] = (target, why)
        elif existing[path].rstrip("/") != target.rstrip("/"):
            wrong[path] = (existing[path], target)
        else:
            covered[path] = target

    print("  %scovered%s %d" % (GREEN, RESET, len(covered)))
    if wrong:
        print("  %spointing elsewhere%s %d" % (YELLOW, RESET, len(wrong)))
        for path, (has, want) in list(wrong.items())[:10]:
            print("    %s\n      is   %s\n      want %s" % (path, has, want))
    if missing:
        print("  %sno redirect%s %d" % (RED, RESET, len(missing)))
        for path, (target, why) in list(missing.items())[:12]:
            print("    %-72s -> %s  (%s)" % (path, target, why))
        if len(missing) > 12:
            print("    %s… and %d more%s" % (DIM, len(missing) - 12, RESET))

    if args.missing_out:
        with open(args.missing_out, "w", encoding="utf-8") as handle:
            json.dump([{"path": p, "target": t, "why": w} for p, (t, w) in missing.items()],
                      handle, indent=2)
        print("\n%swrote %d to %s%s" % (DIM, len(missing), args.missing_out, RESET))

    if args.probe:
        sample = random.sample(sorted(wanted), min(args.probe, len(wanted)))
        print("\n%sWhat the live site answers%s" % (DIM, RESET))
        counts = {}
        for path in sample:
            status, location = probe(domain + path)
            counts[status] = counts.get(status, 0) + 1
            if status != 301:
                print("  %s%-6s%s %s -> %s" % (RED, status, RESET, path, location))
        for status, count in sorted(counts.items(), key=lambda kv: -kv[1]):
            colour = GREEN if status == 301 else RED
            print("  %s%s%s  %d of %d" % (colour, status, RESET, count, len(sample)))


if __name__ == "__main__":
    main()
