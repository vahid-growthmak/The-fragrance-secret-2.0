#!/usr/bin/env python3
"""Rename the perfume oil products to the titles in Perfume_Oil_Titles_Final.xlsx.

The oils were listed under descriptive note names — "Fragrance Secrets Saffron
Jasmine Amberwood Perfume Oil" — which says what is in the bottle but not what
a shopper is searching for. The sheet maps each one to the inspiration it is
sold as ("Baccarat Rouge 540 Inspired Perfume Oil …").

Only the title changes. Handles stay as they are, deliberately: the sheet's own
legend says so, the existing slugs carry the SEO equity, and leaving them alone
means no redirects to create and none to get wrong.

Read-only unless --apply is passed. The dry run reports, per row, whether the
handle resolves, whether the store's current title still matches the sheet's
"Current Title" column (a mismatch means the sheet has gone stale and that row
is skipped unless --force), and whether the product is already renamed.

Note that the new titles drop the pack sizes that 23 of the live titles carry
in their name. That is the sheet's decision, not a bug here — the sizes are
variants, and the sheet's New Title column is the whole title.

    python3 scripts/apply-perfume-oil-titles.py               # dry run
    python3 scripts/apply-perfume-oil-titles.py --status Confirmed,Confident
    python3 scripts/apply-perfume-oil-titles.py --apply

Writes scripts/perfume-oil-titles-run.json on --apply.

Needs openpyxl:  pip install openpyxl
"""

import argparse
import importlib.util
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
SHEET = os.path.join(REPO, "Perfume_Oil_Titles_Final.xlsx")
RUN_LOG = os.path.join(HERE, "perfume-oil-titles-run.json")

spec = importlib.util.spec_from_file_location(
    "sct", os.path.join(HERE, "set-collection-templates.py"))
sct = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sct)
GREEN, YELLOW, RED, DIM, RESET = sct.GREEN, sct.YELLOW, sct.RED, sct.DIM, sct.RESET

LOOKUP = """
query($handle: String!) {
  productByHandle(handle: $handle) {
    id
    handle
    title
    status
    collections(first: 20) { nodes { handle } }
  }
}
"""

RENAME = """
mutation($id: ID!, $title: String!) {
  productUpdate(input: { id: $id, title: $title }) {
    product { id handle title }
    userErrors { field message }
  }
}
"""


def read_sheet(path):
    try:
        import openpyxl
    except ImportError:
        sys.exit("%sneeds openpyxl:  pip install openpyxl%s" % (RED, RESET))

    ws = openpyxl.load_workbook(path, data_only=True)["Perfume Oil Titles"]
    rows = []
    for values in ws.iter_rows(min_row=2, values_only=True):
        serial, fragrance, current, new, url, status = (list(values) + [None] * 6)[:6]
        if serial is None:
            continue
        missing = [name for name, v in (("New Title", new), ("Product URL", url)) if not v]
        if missing:
            sys.exit("%srow %s is missing %s%s" % (RED, serial, " and ".join(missing), RESET))
        rows.append({
            "serial": serial,
            "fragrance": (fragrance or "").strip(),
            "sheet_current": (current or "").strip(),
            "new": str(new).strip(),
            "handle": str(url).strip().rstrip("/").split("/")[-1],
            "status": (status or "").strip(),
        })

    handles = [r["handle"] for r in rows]
    dupes = sorted({h for h in handles if handles.count(h) > 1})
    if dupes:
        sys.exit("%sthe sheet points two rows at the same product: %s%s"
                 % (RED, ", ".join(dupes), RESET))
    return rows


# 23 of the 62 live titles carry the pack sizes and the sheet's "Current
# Title" column does not — "… Perfume Oil 100g, 250g, 500g, 1kg – Floral
# Unisex" against "… Perfume Oil – Floral Unisex". Every one of those 23
# differs by exactly that fragment and nothing else, so the sheet was built
# before the sizes were added rather than describing different products.
# Normalising it means the staleness check still catches a title that has
# genuinely moved on, instead of being blanket-disabled with --force.
SIZE_LIST = " 100g, 250g, 500g, 1kg"


def same_title(live_title, sheet_title):
    return live_title == sheet_title or live_title.replace(SIZE_LIST, "", 1) == sheet_title


def classify(row, live, force):
    """What should happen to this row, and why."""
    if live is None:
        return "missing", "no product with handle %s" % row["handle"]
    if live["title"] == row["new"]:
        return "already", "already carries the new title"
    if row["sheet_current"] and not same_title(live["title"], row["sheet_current"]):
        if not force:
            return "stale", "store says %r, sheet expected %r" % (live["title"], row["sheet_current"])
        return "rename", "sheet is stale but --force was passed"
    return "rename", ""


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--apply", action="store_true",
                        help="write the titles (without this it only reports)")
    parser.add_argument("--status", default="",
                        help="only rows whose Verification Status is in this comma-separated list, "
                             "e.g. 'Confirmed,Confident'")
    parser.add_argument("--force", action="store_true",
                        help="rename even where the store's current title no longer matches the sheet")
    parser.add_argument("--sheet", default=SHEET, help="path to the xlsx")
    args = parser.parse_args()

    rows = read_sheet(args.sheet)
    if args.status:
        wanted = {s.strip().lower() for s in args.status.split(",") if s.strip()}
        before = len(rows)
        rows = [r for r in rows if r["status"].lower() in wanted]
        print("%s%d of %d rows match --status %s%s\n" % (DIM, len(rows), before, args.status, RESET))

    dotenv = sct.load_dotenv()
    store = sct.credential(dotenv, "SHOPIFY_STORE_DOMAIN")
    token = sct.credential(dotenv, "SHOPIFY_ADMIN_ACCESS_TOKEN")
    version = sct.credential(dotenv, "SHOPIFY_API_VERSION") or sct.DEFAULT_API_VERSION
    if not store or not token:
        sys.exit("%sSHOPIFY_STORE_DOMAIN and SHOPIFY_ADMIN_ACCESS_TOKEN must be set in .env%s"
                 % (RED, RESET))
    client = sct.Shopify(store, token, version)
    print("%sstore %s · api %s · %s%s\n"
          % (DIM, store, version, "APPLYING" if args.apply else "dry run", RESET))

    buckets = {"rename": [], "already": [], "stale": [], "missing": []}
    for row in rows:
        live = client.call(LOOKUP, {"handle": row["handle"]})["productByHandle"]
        action, note = classify(row, live, args.force)
        row["live"] = live
        row["note"] = note
        buckets[action].append(row)

        mark = {"rename": GREEN + "rename" + RESET, "already": DIM + "already" + RESET,
                "stale": YELLOW + "stale " + RESET, "missing": RED + "missing" + RESET}[action]
        print("%s  %-3s %s" % (mark, row["serial"], row["handle"]))
        if action == "rename":
            print("        %s- %s%s" % (DIM, live["title"], RESET))
            print("        %s+ %s%s" % (GREEN, row["new"], RESET))
            if row["status"].lower() == "check with supplier":
                print("        %s! sheet marks this \"Check with supplier\"%s" % (YELLOW, RESET))
        elif note:
            print("        %s%s%s" % (DIM, note, RESET))

    print("\n%d to rename · %d already done · %d stale · %d missing"
          % (len(buckets["rename"]), len(buckets["already"]),
             len(buckets["stale"]), len(buckets["missing"])))
    unverified = [r for r in buckets["rename"] if r["status"].lower() == "check with supplier"]
    if unverified:
        print("%s%d of those are marked \"Check with supplier\" — the sheet's own legend asks for "
              "the original to be confirmed against the supplier before publishing.%s"
              % (YELLOW, len(unverified), RESET))

    if not args.apply:
        print("\n%sdry run — nothing was written. Re-run with --apply.%s" % (DIM, RESET))
        return 0

    done, failed = [], []
    for row in buckets["rename"]:
        result = client.call(RENAME, {"id": row["live"]["id"], "title": row["new"]})["productUpdate"]
        errors = result.get("userErrors") or []
        if errors:
            failed.append({"handle": row["handle"], "errors": errors})
            print("%sfailed %s: %s%s" % (RED, row["handle"], json.dumps(errors), RESET))
        else:
            done.append({"handle": row["handle"], "old": row["live"]["title"],
                         "new": result["product"]["title"], "status": row["status"]})
            print("%srenamed%s %s" % (GREEN, RESET, row["handle"]))
        time.sleep(0.2)  # the Admin API's leaky bucket refills at 2/s on a standard plan

    with open(RUN_LOG, "w", encoding="utf-8") as handle:
        json.dump({"store": store, "when": time.strftime("%Y-%m-%dT%H:%M:%S"),
                   "renamed": done, "failed": failed,
                   "skipped_stale": [{"handle": r["handle"], "note": r["note"]} for r in buckets["stale"]],
                   "missing": [r["handle"] for r in buckets["missing"]]},
                  handle, indent=2, ensure_ascii=False)
    print("\n%d renamed, %d failed. Log: %s"
          % (len(done), len(failed), os.path.relpath(RUN_LOG, REPO)))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
