#!/usr/bin/env python3
"""Generate the AVIF companions for the home page hero.

The hero is the LCP element on the page Lighthouse grades, so its weight is
the metric. The same picture at the same quality is about 30% smaller as AVIF
than as WebP — 49 KB against 69 KB on the phone variant, measured at 38.7 dB
PSNR, which is a format saving rather than a quality one.

sections/home.liquid serves the AVIF through a <picture> source and keeps the
WebP on the <img>, because AVIF needs Safari 16.4 and an older phone must
still get a hero. Both files therefore have to exist and show the same
artwork: replace a hero and run this, or a visitor on a current browser is
served the picture you replaced.

    python3 scripts/build-hero-avif.py            # rebuild from the .webp pair
    python3 scripts/build-hero-avif.py --quality 60

Needs Pillow with AVIF support:  pip install 'pillow>=11.3'
"""

import argparse
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(os.path.dirname(HERE), "assets")
# Whatever sections/home.liquid's hero_image_asset / _sm settings default to.
HEROES = ("home-hero.webp", "home-hero-sm.webp")


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    # 65 was picked by measuring PSNR against the WebP rather than by eye: 72
    # saved almost nothing, 55 was visibly softer on the hero's gradients.
    parser.add_argument("--quality", type=int, default=65, help="AVIF quality (default 65)")
    parser.add_argument("--file", action="append", help="a .webp in assets/ to convert; repeatable")
    args = parser.parse_args()

    try:
        from PIL import Image, features
    except ImportError:
        sys.exit("needs Pillow:  pip install 'pillow>=11.3'")
    if not features.check("avif"):
        sys.exit("this Pillow has no AVIF support:  pip install --upgrade 'pillow>=11.3'")

    for name in (args.file or HEROES):
        src = os.path.join(ASSETS, name)
        if not os.path.exists(src):
            sys.exit("missing: %s" % src)
        dest = os.path.splitext(src)[0] + ".avif"
        image = Image.open(src).convert("RGB")
        image.save(dest, "AVIF", quality=args.quality, speed=4)
        was, now = os.path.getsize(src), os.path.getsize(dest)
        print("%-20s %7.1f KB -> %7.1f KB  (-%.0f%%)  %dx%d"
              % (os.path.basename(dest), was / 1024, now / 1024,
                 100 * (1 - now / was), image.width, image.height))
    return 0


if __name__ == "__main__":
    sys.exit(main())
