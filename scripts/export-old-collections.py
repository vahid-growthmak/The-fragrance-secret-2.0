#!/usr/bin/env python3
"""Export every old collection URL, where it points now, and whether it works.

The old site had 121 brand and category collections that this build retired or
renamed. Three files in this repo each hold part of the story — the plan that
decided where each one should go, the run log of what was done, and the backup
of the collections themselves — and the store holds the fourth part: whether
the redirect is actually there today. This puts all four in one CSV.

    python3 scripts/export-old-collections.py
    python3 scripts/export-old-collections.py --out somewhere-else.csv
    python3 scripts/export-old-collections.py --offline   # skip the store check

Read-only.
"""

import argparse
import csv
import importlib.util
import json
import os
import sys

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
    nodes { path target }
  }
}
"""


def load(path, default):
    full = os.path.join(HERE, path)
    if not os.path.exists(full):
        return default
    with open(full, encoding="utf-8") as handle:
        return json.load(handle)


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", default=os.path.join(REPO, "old-collection-urls.csv"))
    parser.add_argument("--offline", action="store_true", help="do not check the store")
    args = parser.parse_args()

    plan = load("retire-collections-plan.json", {})
    log = load("retire-collections-run-log.json", [])

    # Titles and ids come from the backup taken before the collections were
    # deleted — the only place the old titles still exist.
    titles, ids = {}, {}
    backups = os.path.join(REPO, "live-backups")
    if os.path.isdir(backups):
        for name in sorted(os.listdir(backups)):
            if not name.startswith("retired-collections"):
                continue
            with open(os.path.join(backups, name), encoding="utf-8") as handle:
                for row in json.load(handle).get("collections", []):
                    titles[row["handle"]] = row.get("title", "")
                    ids[row["handle"]] = row.get("id", "")

    # What the run log says happened to each one.
    actions = {}
    for entry in log:
        path = entry.get("path") or ""
        handle = path.rsplit("/", 1)[-1]
        actions.setdefault(handle, {})[entry.get("step")] = entry.get("ok")

    live = {}
    if not args.offline:
        dotenv = sct.load_dotenv()
        store = sct.credential(dotenv, "SHOPIFY_STORE_DOMAIN")
        token = sct.credential(dotenv, "SHOPIFY_ADMIN_ACCESS_TOKEN")
        version = sct.credential(dotenv, "SHOPIFY_API_VERSION") or sct.DEFAULT_API_VERSION
        if store and token:
            client = sct.Shopify(store, token, version)
            cursor = None
            while True:
                page = client.call(REDIRECTS, {"cursor": cursor})["urlRedirects"]
                for node in page["nodes"]:
                    live[node["path"]] = node["target"]
                if not page["pageInfo"]["hasNextPage"]:
                    break
                cursor = page["pageInfo"]["endCursor"]

    rows = []
    for handle in sorted(plan):
        old_path = "/collections/%s" % handle
        target = plan[handle].get("target") or ""
        on_store = live.get(old_path)
        rows.append({
            "old_url": old_path,
            "old_handle": handle,
            "old_title": titles.get(handle, ""),
            "redirects_to": target,
            "mapping": plan[handle].get("how", ""),
            "redirect_live": "" if args.offline else ("yes" if on_store else "no"),
            "redirect_live_target": on_store or "",
            "matches_plan": "" if args.offline else
                            ("yes" if on_store and on_store.rstrip("/") == target.rstrip("/")
                             else ("no" if on_store else "")),
            "deleted": "yes" if actions.get(handle, {}).get("delete") else "",
            "old_collection_id": ids.get(handle, ""),
        })

    with open(args.out, "w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    live_count = sum(1 for r in rows if r["redirect_live"] == "yes")
    print("%s%d old collection URLs%s -> %s" % (GREEN, len(rows), RESET, args.out))
    if not args.offline:
        print("  %s%d redirect on the store, %d do not%s"
              % (DIM, live_count, len(rows) - live_count, RESET))
        off_plan = [r for r in rows if r["matches_plan"] == "no"]
        if off_plan:
            print("  %s%d point somewhere other than the plan%s" % (YELLOW, len(off_plan), RESET))
            for row in off_plan[:5]:
                print("    %s  is %s, plan said %s"
                      % (row["old_url"], row["redirect_live_target"], row["redirects_to"]))


if __name__ == "__main__":
    main()
