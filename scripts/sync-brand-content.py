#!/usr/bin/env python3
"""Diff (and optionally apply) the 49 brand documents against their templates.

The brand collection templates were built from the source .docx files. When the
documents are revised, this re-reads them and reports exactly which fields moved,
so a content update is a reviewable diff rather than a regeneration -- the
templates keep their structure, key order and every field the documents do not
speak to.

Field mapping, per document section:

    1 Hero Section                     -> hero_eyebrow, hero_heading
    2 Collection Introduction          -> intro_heading, intro_text
    4 Why Choose ...                   -> cards_heading, card1..N
    5 Explore Other Brands             -> sibling_sub, sibling1..N, sibling_all_*
    6 Explore More Fragrance ...       -> explore_sub, explore1..N
    7 Frequently Asked Questions       -> faq1..N
    11 SEO Reference                   -> schema_name, schema_description

Hub URLs are deliberately NOT taken from the documents. The documents point at
/collections/lifestyle, /collections/shop-by-climate and /collections/brands,
while those hubs are implemented as pages on this store, so copying the document
URLs would produce 404s. URL differences are reported and skipped; see --urls.

Usage
-----
    python3 scripts/sync-brand-content.py                # diff, changes nothing
    python3 scripts/sync-brand-content.py --apply        # write the text changes
    python3 scripts/sync-brand-content.py --only armaf   # one brand; repeatable
    python3 scripts/sync-brand-content.py --urls         # just the URL differences
    python3 scripts/sync-brand-content.py --full         # untruncated before/after

Requires no third-party packages.
"""

import argparse
import glob
import html
import json
import os
import re
import sys
import zipfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCS = os.path.join(REPO, "49 Brands Content")

GREEN, YELLOW, RED, CYAN, DIM, RESET = ("\033[32m", "\033[33m", "\033[31m",
                                        "\033[36m", "\033[2m", "\033[0m")

# Fields holding a URL or a link label whose target lives on this store rather
# than in the documents. Reported, never overwritten.
URL_FIELDS = {"url", "sibling_all_url", "sibling_all_label"}


def docx_lines(path):
    with zipfile.ZipFile(path) as archive:
        xml = archive.read("word/document.xml").decode("utf-8", "replace")
    xml = re.sub(r"</w:p>", "\n", xml)
    xml = re.sub(r"<[^>]+>", "", xml)
    return [html.unescape(line).strip() for line in xml.split("\n") if html.unescape(line).strip()]


def split_sections(lines):
    """Group the document body by its numbered headings ("4   Why Choose ...")."""
    sections, current = {}, None
    for line in lines:
        heading = re.match(r"^(\d+)\s{2,}(.+)$", line)
        if heading:
            current = heading.group(2).strip()
            sections[current] = []
        elif current is not None:
            sections[current].append(line)
    return sections


def section(sections, *prefixes):
    for name, body in sections.items():
        for prefix in prefixes:
            if name.lower().startswith(prefix.lower()):
                return name, body
    return None, []


def emphasise(heading):
    """"Armaf Perfumes" -> "Armaf <em>Perfumes</em>", matching the built templates."""
    words = heading.rsplit(" ", 1)
    if len(words) == 1:
        return heading
    return "%s <em>%s</em>" % (words[0], words[1])


def parse(path):
    """Pull every field the templates take out of one brand document."""
    lines = docx_lines(path)
    sections = split_sections(lines)
    out = {"doc": os.path.basename(path)}

    url = next((l for l in lines[:14] if "thefragrancesecrets.com/" in l), "")
    out["handle"] = url.rstrip("/").split("/")[-1] if url else None
    out["crumb_name"] = lines[2] if len(lines) > 2 else None

    _, hero = section(sections, "Hero Section")
    if hero:
        out["hero_eyebrow"] = hero[0].title()
        out["hero_heading"] = emphasise(hero[1])
        out["intro_eyebrow"] = hero[0].title()

    _, intro = section(sections, "Collection Introduction")
    if len(intro) >= 2:
        out["intro_heading"] = intro[0]
        out["intro_text"] = "<p>%s</p>" % intro[1]
        out["schema_name"] = intro[0]

    name, cards = section(sections, "Why Choose")
    if name:
        out["cards_heading"] = emphasise(name)
        # title / body / "LABEL   tag · tag · tag"
        parsed, index = [], 0
        while index + 2 < len(cards) + 1:
            if index + 2 >= len(cards) + 1:
                break
            chunk = cards[index:index + 3]
            if len(chunk) < 3:
                break
            tag = re.match(r"^([A-Z][A-Z\s]+?)\s{2,}(.+)$", chunk[2])
            if not tag:
                break
            parsed.append({"title": chunk[0], "body": chunk[1],
                           "tag_label": tag.group(1).title(),
                           "tags": tag.group(2).replace(" · ", ", ")})
            index += 3
        out["cards"] = parsed

    _, siblings = section(sections, "Explore Other Brands")
    if siblings:
        out["sibling_sub"] = siblings[0]
        pairs = []
        for line in siblings[1:]:
            if line.startswith("See All"):
                break
            if line.startswith("/"):
                if pairs:
                    pairs[-1]["url"] = line
            else:
                pairs.append({"label": line, "url": None})
        out["siblings"] = [p for p in pairs if p["url"]]

    _, explore = section(sections, "Explore More Fragrance", "Explore More")
    if explore:
        out["explore_sub"] = explore[0]
        tiles, pending = [], None
        for line in explore[1:]:
            if line.startswith("/"):
                if pending:
                    tiles.append({"label": pending, "url": line})
                    pending = None
            else:
                pending = line
        out["explore"] = tiles

    _, faqs = section(sections, "Frequently Asked Questions")
    if faqs:
        pairs = []
        for index in range(0, len(faqs) - 1, 2):
            question, answer = faqs[index], faqs[index + 1]
            if question.endswith("?"):
                pairs.append({"question": question, "answer": answer})
        out["faqs"] = pairs

    for index, line in enumerate(lines):
        if line == "Meta Description" and index + 1 < len(lines):
            out["schema_description"] = lines[index + 1]
            break
    return out


def load_template(path):
    raw = open(path, encoding="utf-8").read()
    header = re.match(r"^\s*/\*.*?\*/\s*", raw, flags=re.S)
    return json.loads(raw[header.end():] if header else raw), (header.group(0) if header else "")


def compare(doc, template):
    """List (path, current, new) for every field the document changes."""
    changes = []
    main = template["sections"]["main"]["settings"]
    editorial = template["sections"]["editorial"]
    settings, blocks = editorial["settings"], editorial["blocks"]

    def check(container, key, value, label):
        if value is None or key not in container:
            return
        if container[key] != value:
            changes.append((label, key, container[key], value, container))

    for key in ("hero_eyebrow", "hero_heading", "intro_eyebrow", "intro_heading", "intro_text"):
        check(main, key, doc.get(key), "main")
    for key in ("cards_heading", "sibling_sub", "explore_sub", "crumb_name",
                "schema_name", "schema_description"):
        check(settings, key, doc.get(key), "editorial")

    def blocks_of(kind):
        return [(name, blocks[name]) for name in editorial.get("block_order", blocks)
                if blocks.get(name, {}).get("type") == kind]

    for (name, block), new in zip(blocks_of("card"), doc.get("cards", [])):
        for key in ("title", "body", "tag_label", "tags"):
            check(block["settings"], key, new.get(key), name)
    for (name, block), new in zip(blocks_of("faq"), doc.get("faqs", [])):
        for key in ("question", "answer"):
            check(block["settings"], key, new.get(key), name)
    for (name, block), new in zip(blocks_of("sibling"), doc.get("siblings", [])):
        for key in ("label", "url"):
            check(block["settings"], key, new.get(key), name)
    for (name, block), new in zip(blocks_of("explore"), doc.get("explore", [])):
        for key in ("label", "url"):
            check(block["settings"], key, new.get(key), name)

    counts = {
        "card": (len(blocks_of("card")), len(doc.get("cards", []))),
        "faq": (len(blocks_of("faq")), len(doc.get("faqs", []))),
        "sibling": (len(blocks_of("sibling")), len(doc.get("siblings", []))),
    }
    return changes, counts


def show(value, full, width=104):
    value = value.replace("\n", " ")
    return value if full or len(value) <= width else value[: width - 1] + "…"


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--apply", action="store_true", help="write the text changes")
    parser.add_argument("--only", action="append", metavar="HANDLE", help="one brand; repeatable")
    parser.add_argument("--urls", action="store_true", help="only report URL/link differences")
    parser.add_argument("--full", action="store_true", help="do not truncate before/after text")
    parser.add_argument("--docs", default=DOCS, help="folder holding the brand .docx files")
    args = parser.parse_args()

    paths = sorted(glob.glob(os.path.join(args.docs, "*.docx")))
    if not paths:
        sys.exit("No .docx files in %s" % args.docs)

    touched = text_changes = url_changes = 0
    missing, mismatched, url_rows = [], [], []

    for path in paths:
        doc = parse(path)
        if not doc.get("handle"):
            missing.append((os.path.basename(path), "no canonical URL"))
            continue
        if args.only and doc["handle"] not in args.only:
            continue
        template_path = os.path.join(REPO, "templates", "collection.%s.json" % doc["handle"])
        if not os.path.exists(template_path):
            missing.append((doc["doc"], "no template collection.%s.json" % doc["handle"]))
            continue

        template, header = load_template(template_path)
        changes, counts = compare(doc, template)
        for kind, (have, want) in counts.items():
            if have != want:
                mismatched.append((doc["handle"], kind, have, want))

        text, urls = [], []
        for change in changes:
            (urls if change[1] in URL_FIELDS else text).append(change)
        url_rows.extend((doc["handle"],) + c[:4] for c in urls)
        url_changes += len(urls)

        if not text:
            continue
        touched += 1
        text_changes += len(text)
        if not args.urls:
            print("\n%s%s%s  %s(%d field%s)%s" % (CYAN, doc["handle"], RESET, DIM,
                                                  len(text), "" if len(text) == 1 else "s", RESET))
            for label, key, current, new, container in text:
                print("  %s%s.%s%s" % (DIM, label, key, RESET))
                print("    %s- %s%s" % (RED, show(current, args.full), RESET))
                print("    %s+ %s%s" % (GREEN, show(new, args.full), RESET))
                if args.apply:
                    container[key] = new

        if args.apply and text:
            with open(template_path, "w", encoding="utf-8") as handle:
                handle.write(header + json.dumps(template, indent=2, ensure_ascii=False) + "\n")

    if url_rows and (args.urls or not args.apply):
        print("\n%sURL and link-label differences -- reported, never written%s" % (YELLOW, RESET))
        print("%s  The documents point hub links at /collections/..., but those hubs are pages on\n"
              "  this store. Copying the document URLs would 404.%s" % (DIM, RESET))
        for handle, label, key, current, new in url_rows[:40]:
            print("  %-22s %-10s %-16s %s%s%s -> %s%s%s"
                  % (handle, label, key, RED, current, RESET, GREEN, new, RESET))
        if len(url_rows) > 40:
            print("  %s… and %d more (same pattern)%s" % (DIM, len(url_rows) - 40, RESET))

    if mismatched:
        print("\n%sBlock-count differences -- need a template change, not a text edit%s" % (YELLOW, RESET))
        for handle, kind, have, want in mismatched:
            print("  %-22s %-8s template has %d, document has %d" % (handle, kind, have, want))

    if missing:
        print("\n%sSkipped%s" % (RED, RESET))
        for name, why in missing:
            print("  %s -- %s" % (name, why))

    print("\n%d brands with text changes, %d text fields, %d URL differences held back"
          % (touched, text_changes, url_changes))
    if not args.apply and text_changes:
        print("%sDiff only -- nothing written. Re-run with --apply to make the text changes.%s"
              % (DIM, RESET))


if __name__ == "__main__":
    main()
