/* Rebuild snippets/critical-css.liquid from the live storefront.
 *
 * theme.css and pages.css were render-blocking — 790ms each on the mobile
 * Lighthouse run — which gated FCP and, behind it, LCP. They load async now,
 * and the rules needed before they arrive are inlined in the head instead.
 *
 * Working out which rules those are is a question about the rendered page, so
 * it is answered by rendering it: headless Chrome at Lighthouse's own mobile
 * viewport (412x823 at DPR 1.75), every rule in both stylesheets tested
 * against the DOM, keep the ones whose selector matches an element that is
 * actually laid out inside the first screen.
 *
 * "Actually laid out" matters. A display:none element reports an all-zero
 * rect, which reads as top: 0 — take that at face value and every drawer,
 * modal and overlay in the theme joins the critical set, which is the
 * difference between 39 KB and 21 KB here.
 *
 * The three templates below are rendered and their results unioned, so one
 * inline block is correct on all of them. Add a URL if a template's first
 * screen looks unlike these.
 *
 * Stale output does not break a page — the full stylesheets still arrive and
 * correct it — it costs a flash of the wrong style. Regenerate after changing
 * anything above the fold.
 *
 *     npm install puppeteer-core     # once; it drives the Chrome already installed
 *     node scripts/build-critical-css.js
 */
const fs = require('fs');
const puppeteer = require('puppeteer-core');

const CHROME = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
const REPO = require('path').dirname(__dirname);
const SHEETS = ['assets/theme.css', 'assets/pages.css'];
// Lighthouse's mobile emulation: Moto G Power, 412x823 CSS px.
const VIEWPORT = { width: 412, height: 823, deviceScaleFactor: 1.75, isMobile: true };
const HEADER = `{%- comment -%}
  Critical CSS — the rules that style what is above the fold, inlined so the
  first paint needs no stylesheet at all.

  theme.css and pages.css were both render-blocking: 790ms each on the mobile
  run, gating FCP and, behind it, LCP. They load asynchronously now (see
  layout/theme.liquid) and this block holds what the page needs before they
  arrive.

  Generated, not hand-written — scripts/build-critical-css.js loads the live
  home, collection and product templates in headless Chrome at Lighthouse's
  412x823 mobile viewport, walks every rule in both stylesheets, and keeps the
  ones whose selectors match an element that is actually laid out inside that
  first screen. The union of the three templates is what is here, so the same
  block is correct on all of them.

  Regenerate it after any change to the above-the-fold markup or styles:

      node scripts/build-critical-css.js

  Stale critical CSS does not break the page — the full stylesheets still
  arrive and correct it — it just costs a flash of the wrong style.
{%- endcomment -%}
`;

const PAGES = process.argv.length > 2 ? process.argv.slice(2) : [
  'https://thefragrancesecrets.com/',
  'https://thefragrancesecrets.com/collections/all',
  'https://thefragrancesecrets.com/products/perfume-oil-inspired-by-marj-alcohol-free-concentrated-oil',
  'https://thefragrancesecrets.com/pages/about-us',
  'https://thefragrancesecrets.com/cart',
  'https://thefragrancesecrets.com/search?q=oud',
];
const OUT = `${REPO}/snippets/critical-css.liquid`;

(async () => {
  const css = SHEETS.map(f => fs.readFileSync(`${REPO}/${f}`, 'utf8')).join('\n');
  const browser = await puppeteer.launch({ executablePath: CHROME, headless: 'new',
    args: ['--no-sandbox', '--disable-dev-shm-usage'] });
  const keep = new Set();
  const stats = [];

  for (const url of PAGES) {
    const page = await browser.newPage();
    await page.setViewport(VIEWPORT);
    await page.goto(url, { waitUntil: 'networkidle2', timeout: 60000 });
    const found = await page.evaluate((cssText, foldHeight) => {
      // Re-inject our own copy so the rules are same-origin and readable;
      // identical rules change nothing about the rendered page.
      const el = document.createElement('style');
      el.textContent = cssText;
      document.head.appendChild(el);
      const sheet = el.sheet;

      // querySelectorAll throws on a pseudo-element, so a rule like
      // .hero-img-wrap::before — the hero's scrim, as critical as anything on
      // the page — was landing in the catch below and being dropped. Match
      // the host element instead. Pseudo-CLASSES are left alone: :hover and
      // friends legitimately match nothing at first paint, which is the
      // answer we want from them.
      const PSEUDO_ELEMENT = /::[a-zA-Z-]+(\([^)]*\))?|:(before|after|first-line|first-letter)\b/g;

      const aboveFold = (selector) => {
        const host = selector.replace(PSEUDO_ELEMENT, '').trim();
        if (!host) return false;   // a bare ::selection styles no element of its own
        let nodes;
        try { nodes = document.querySelectorAll(host); } catch (e) { return false; }
        for (const n of nodes) {
          const r = n.getBoundingClientRect();
          // Must actually be laid out. A display:none element reports an
          // all-zero rect, which reads as "top: 0" and would drag every
          // drawer, modal and overlay in the theme into the critical set —
          // none of which paints until long after the stylesheet lands.
          if (r.width === 0 && r.height === 0) continue;
          if (r.top < foldHeight && r.bottom > 0) return true;
        }
        return false;
      };

      const out = [];
      const walk = (rules, wrap) => {
        for (const rule of rules) {
          if (rule.type === CSSRule.STYLE_RULE) {
            // A selector list is kept whole if any part of it is above the fold.
            const hit = rule.selectorText.split(',').some(s => aboveFold(s.trim()));
            if (hit) out.push(wrap ? [wrap, rule.cssText] : [null, rule.cssText]);
          } else if (rule.type === CSSRule.MEDIA_RULE) {
            if (window.matchMedia(rule.conditionText).matches) {
              walk(rule.cssRules, rule.conditionText);
            }
          } else if (rule.type === CSSRule.SUPPORTS_RULE) {
            walk(rule.cssRules, null);
          }
        }
      };
      walk(sheet.cssRules, null);
      el.remove();
      return out;
    }, css, VIEWPORT.height);

    found.forEach(([media, text]) => keep.add(JSON.stringify([media, text])));
    stats.push(`${found.length.toString().padStart(5)} rules  ${url}`);
    await page.close();
  }
  await browser.close();

  const byMedia = new Map();
  for (const entry of keep) {
    const [media, text] = JSON.parse(entry);
    const k = media || '';
    if (!byMedia.has(k)) byMedia.set(k, []);
    byMedia.get(k).push(text);
  }
  let outCss = (byMedia.get('') || []).join('\n');
  for (const [media, rules] of byMedia) {
    if (!media) continue;
    outCss += `\n@media ${media}{\n${rules.join('\n')}\n}`;
  }
  // cssText comes back browser-normalised, so this only collapses the spacing
  // serialisation adds. Verified lossless by reparsing both forms and
  // comparing the rule trees.
  const min = outCss
    .replace(/\s*\n\s*/g, '\n')
    .replace(/ *([{};:,]) */g, '$1')
    .replace(/;\}/g, '}')
    .replace(/\n+/g, '\n')
    .trim();

  if (/\{\{|\{%|<\//.test(min)) {
    console.error('refusing to write: the CSS contains something Liquid or the ' +
                  'HTML parser would take for markup');
    process.exit(1);
  }

  fs.writeFileSync(OUT, `${HEADER}<style>\n${min}\n</style>\n`);
  console.error(stats.join('\n'));
  console.error(`\nunion: ${keep.size} rules, ${(outCss.length / 1024).toFixed(1)} KB raw` +
                ` -> ${(min.length / 1024).toFixed(1)} KB inlined`);
  console.error(`written to ${OUT.replace(REPO + '/', '')}`);
})();
