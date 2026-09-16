#!/usr/bin/env python3
"""Repoint every /collections/<handle> in the theme at the renamed slugs.

Run after scripts/apply-url-slugs.py, which renames the collections on the
store and writes scripts/url-slug-plan.json. The theme links to those handles
from 50-odd files — the mega-menu, the hub pages, the editorial sections, the
collection templates' cross-links and app.js — and every one of them would
otherwise take a shopper through a redirect to reach a page the menu could
have pointed at directly.

Handles are replaced on a boundary, never as plain substrings. /collections/
wedding is a prefix of /collections/wedding-formal, and /collections/inspired
of /collections/inspired-impression: a careless replace turns a working link
into /collections/wedding-perfumes-formal, which exists nowhere.

    python3 scripts/update-collection-links.py           # dry run
    python3 scripts/update-collection-links.py --apply

Nothing is written without --apply.
"""

import argparse
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
PLAN = os.path.join(HERE, "url-slug-plan.json")

GREEN, YELLOW, RED, DIM, RESET = "\033[32m", "\033[33m", "\033[31m", "\033[2m", "\033[0m"

FOLDERS = ["sections", "snippets", "assets", "templates", "layout", "config", "locales"]
SUFFIXES = (".liquid", ".js", ".json", ".css")


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--apply", action="store_true", help="actually rewrite the files")
    args = parser.parse_args()

    if not os.path.exists(PLAN):
        sys.exit("%sNo plan at %s — run apply-url-slugs.py first.%s" % (RED, PLAN, RESET))
    with open(PLAN, encoding="utf-8") as handle:
        plan = json.load(handle)["plan"]
    mapping = {row["old"]: row["new"] for row in plan}
    if not mapping:
        sys.exit("%sThe plan is empty.%s" % (YELLOW, RESET))

    # Longest first so a handle that is a prefix of another is never matched
    # by the shorter rule, and a trailing boundary so the match ends where the
    # handle does.
    pattern = re.compile(
        r"/collections/(%s)(?![a-z0-9-])" % "|".join(sorted(map(re.escape, mapping), key=len, reverse=True)))

    total, touched = 0, []
    for folder in FOLDERS:
        root = os.path.join(REPO, folder)
        if not os.path.isdir(root):
            continue
        for base, _, names in os.walk(root):
            for name in sorted(names):
                if not name.endswith(SUFFIXES):
                    continue
                path = os.path.join(base, name)
                with open(path, encoding="utf-8") as handle:
                    before = handle.read()
                after, count = pattern.subn(lambda m: "/collections/" + mapping[m.group(1)], before)
                if not count:
                    continue
                total += count
                touched.append((os.path.relpath(path, REPO), count))
                if args.apply:
                    with open(path, "w", encoding="utf-8") as handle:
                        handle.write(after)

    for path, count in touched:
        print("  %-52s %d" % (path, count))
    print("\n%s%d links in %d files%s" % (GREEN if args.apply else DIM, total, len(touched), RESET))

    if not args.apply:
        print("\n%sDry run — nothing was written. Re-run with --apply.%s" % (YELLOW, RESET))


if __name__ == "__main__":
    main()
