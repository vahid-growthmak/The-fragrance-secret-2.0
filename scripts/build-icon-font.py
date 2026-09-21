#!/usr/bin/env python3
"""Rebuild assets/material-symbols-subset.woff2 from the theme's own markup.

The theme draws every icon with a Material Symbols ligature —
`<span class="mi">shopping_bag</span>`. Fetched from Google, that font is the
whole variable family: 4,284 glyphs, four axes, 3.9 MB on every page view. It
was more than half the weight of the site and it competed with the hero image
for bandwidth on the connection speeds Lighthouse grades against.

This builds the same font cut down to the symbol names that actually appear in
this theme, with GRAD and opsz pinned and wght limited to 300-400 — the only
two instances theme.css renders (`.mi` and `.mi.mi-f`). That is ~61 KB, and
because the ligature substitutions survive, the markup does not change.

The scan is deliberately generous: any bare word anywhere in the theme source
that happens to be a valid Material Symbols name is kept, false positives
included, because a missed icon paints as its own name in plain text and a
spare glyph costs a few hundred bytes. Run this after adding an icon the theme
has never used before.

    python3 scripts/build-icon-font.py            # rebuild the asset
    python3 scripts/build-icon-font.py --check    # verify the committed one

Needs fonttools and brotli:  pip install fonttools brotli
"""

import argparse
import os
import re
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
ASSET = os.path.join(REPO, 'assets', 'material-symbols-subset.woff2')

# The axis query the theme used to request from fonts.googleapis.com. Kept
# verbatim so this builds from the same font the browser used to download.
CSS_URL = ('https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined'
           ':opsz,wght,FILL,GRAD@20..48,100..700,0..1,-50..200')
CODEPOINTS_URL = ('https://raw.githubusercontent.com/google/material-design-icons/'
                  'master/variablefont/MaterialSymbolsOutlined%5BFILL%2CGRAD%2Copsz%2Cwght%5D'
                  '.codepoints')
# css2 serves woff2 only to a browser UA; anything else gets the ttf fallback.
UA = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')

SCAN_DIRS = ('sections', 'snippets', 'layout', 'templates', 'assets', 'config', 'locales')
# .css is in here because two rules draw an icon from a `content:` string
# rather than from markup (pages.css's accordion chevron, for one).
SCAN_EXTS = ('.liquid', '.js', '.json', '.css')

# Every icon reaches the page either written into .mi markup or chosen in an
# `icon` section setting, so this is the set the build has to cover exactly —
# the wider scan above is only there for safety. An icon picked in the theme
# editor that no template has ever used is the one case this cannot see: it
# lands in config/settings_data.json, which the scan reads, but only after the
# settings are pulled back down into the repo.
MARKUP_ICON = re.compile(r'class="mi(?:\s[^"]*)?"[^>]*>\s*([a-z0-9_]+)')
SETTING_ICON = re.compile(r'"icon"\s*:\s*"([a-z0-9_]+)"')
CONTENT_ICON = re.compile(r"content:\s*'([a-z0-9_]+)'")


def fetch(url, binary=False):
    out = subprocess.run(['curl', '-sSL', '-A', UA, url],
                         capture_output=True, check=True).stdout
    return out if binary else out.decode()


def icon_codepoints():
    """name -> codepoint, for all 4,284 symbols."""
    table = {}
    for line in fetch(CODEPOINTS_URL).splitlines():
        if line.strip():
            name, code = line.split()
            table[name] = int(code, 16)
    return table


def scan(names):
    """Icon names appearing anywhere in the theme, and the ones in .mi markup."""
    found, in_markup = set(), set()
    for d in SCAN_DIRS:
        for root, _dirs, files in os.walk(os.path.join(REPO, d)):
            for f in files:
                if not f.endswith(SCAN_EXTS):
                    continue
                path = os.path.join(root, f)
                with open(path, encoding='utf-8', errors='ignore') as fh:
                    text = fh.read()
                found.update(w for w in re.findall(r'[a-z0-9_]+', text) if w in names)
                for pattern in (MARKUP_ICON, SETTING_ICON, CONTENT_ICON):
                    in_markup.update(m for m in pattern.findall(text) if m in names)
    return found, in_markup


def verify(path, required):
    """Check each required name still resolves through a ligature to a real glyph."""
    from fontTools.ttLib import TTFont

    font = TTFont(path)
    cmap = font.getBestCmap()
    glyphs = set(font.getGlyphOrder())
    ligatures = {}
    for lookup in font['GSUB'].table.LookupList.Lookup:
        for sub in lookup.SubTable:
            if lookup.LookupType == 7:
                sub = sub.ExtSubTable
            for first, entries in getattr(sub, 'ligatures', {}).items():
                for lig in entries:
                    ligatures[(first,) + tuple(lig.Component)] = lig.LigGlyph

    broken = []
    for name in sorted(required):
        try:
            chain = tuple(cmap[ord(ch)] for ch in name)
        except KeyError:
            broken.append(name)
            continue
        if ligatures.get(chain) not in glyphs:
            broken.append(name)
    return broken


def build(dest):
    from fontTools.ttLib import TTFont  # noqa: F401  (fail early if missing)

    names = icon_codepoints()
    found, in_markup = scan(names)
    print('%d symbol names found in the theme (%d of them in .mi markup)'
          % (len(found), len(in_markup)))

    unicodes = ','.join('U+%04X' % names[n] for n in sorted(found))
    css = fetch(CSS_URL)
    url = re.search(r'url\((https://[^)]+\.woff2)\)', css).group(1)
    source = fetch(url, binary=True)

    with tempfile.TemporaryDirectory() as tmp:
        full = os.path.join(tmp, 'full.woff2')
        subsetted = os.path.join(tmp, 'subset.ttf')
        instanced = os.path.join(tmp, 'instance.ttf')
        with open(full, 'wb') as fh:
            fh.write(source)

        py = sys.executable
        # --no-layout-closure: without it the subsetter follows every ligature
        # rule out of the letters a-z and drags all 4,284 icons back in.
        # rclt/rlig are where Material Symbols keeps those rules.
        subprocess.run([py, '-m', 'fontTools.subset', full,
                        '--unicodes=U+0030-0039,U+0041-005A,U+005F,U+0061-007A,' + unicodes,
                        '--layout-features=liga,dlig,ccmp,rlig,rclt',
                        '--no-layout-closure',
                        '--output-file=' + subsetted], check=True)
        # FILL 0/1 and wght 300/400 are both rendered; GRAD and opsz never vary.
        subprocess.run([py, '-m', 'fontTools.varLib.instancer', '-q', '-o', instanced,
                        subsetted, 'GRAD=0', 'opsz=24', 'wght=300:400', 'FILL=0:1'], check=True)
        subprocess.run([py, '-m', 'fontTools.ttLib.woff2', 'compress', '-o', dest, instanced],
                       check=True, stdout=subprocess.DEVNULL)

    broken = verify(dest, in_markup)
    if broken:
        print('BROKEN — these icons no longer resolve: %s' % ', '.join(broken))
        return 1
    print('%s: %.1f KB (Google serves %.1f KB), %d icons verified'
          % (os.path.relpath(dest, REPO), os.path.getsize(dest) / 1024,
             len(source) / 1024, len(in_markup)))
    return 0


def check():
    if not os.path.exists(ASSET):
        print('missing: %s — run this script without --check' % os.path.relpath(ASSET, REPO))
        return 1
    names = icon_codepoints()
    _found, in_markup = scan(names)
    broken = verify(ASSET, in_markup)
    if broken:
        print('%d icon(s) used by the theme are not in the font: %s'
              % (len(broken), ', '.join(broken)))
        print('run: python3 scripts/build-icon-font.py')
        return 1
    print('all %d icons used by the theme resolve in %s (%.1f KB)'
          % (len(in_markup), os.path.relpath(ASSET, REPO), os.path.getsize(ASSET) / 1024))
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--check', action='store_true',
                    help='verify the committed font covers every icon the theme uses')
    args = ap.parse_args()
    try:
        return check() if args.check else build(ASSET)
    except ImportError:
        print('needs fonttools and brotli:  pip install fonttools brotli')
        return 1


if __name__ == '__main__':
    sys.exit(main())
