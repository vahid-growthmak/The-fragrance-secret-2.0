# The Fragrance Secrets — Site Structure & Sitemap Coverage

Premium dark-theme luxury perfume mockups, built to the **buy-led / brand-anchored**
strategy in `the-fragrance-secrets-sitemap-strategy.docx` and the 39-page build CSV
`the-fragrance-secrets-sitemap.csv`. Static HTML on one shared design system.

## Architecture
| Layer | File(s) | Purpose |
|---|---|---|
| Design system | `assets/css/theme.css` | The home/product design system (tokens, buttons, cards, footer, responsive). |
| Component layer | `assets/css/pages.css` | Catalogue components: page-heroes, Shop mega-menu, filter bars, hub tiles, combo builder, checkout, brand cloud, legal prose, AI CTA, etc. |
| Shared runtime | `assets/js/app.js` | Injects chrome (announce, **Shop mega-menu header**, **locked 4-col footer**, WhatsApp float, AI concierge, Mix wizard); data, renderers, **Find-My-Scent quiz**, cart/toast, **exit-intent custom-blend offer**, base-path resolution. |
| Collection engine | `assets/js/collections.js` + `collection.html` | One template → all product-listing pages (categories, families, brands, occasions, weather, lifestyle, discovery-kits) from config. |

## The four locked decisions → how the build serves them
1. **Buy-led / shop-first hero** — home leads with product & brand; the quiz is a secondary assist band + `find-my-scent.html`, never the front door.
2. **Ready-buyer intent spine** — Shop-dominant mega-menu, brand/category/family/occasion collections, low-friction PDP buy box (COD + Tabby/Tamara + wallet), express Buy Now.
3. **Brand-led hierarchy, own brands elevated** — `brand-index.html` promotes Fragrance Secrets / Secret Scents / Paris Collection above the A-Z resale houses; transparent split.
4. **Launch vs Phase 2** — Custom Mixing (the "Mix into Spray" wizard) & Referral kept in-architecture; the **custom-blend offer surfaces via the AI concierge only on exit-intent**, never distracting the funnel.

## Sitemap (39 pages) → files
| Tier | Sitemap Page | Mockup file |
|---|---|---|
| 1 | Homepage | `index.html` |
| 1 | Shop (All Products) | `collection.html?c=all` |
| 1 | Brand Index (Our Brands elevated) | `brand-index.html` |
| 1 | Own-Brand Collection | `collection.html?c=own-brand` |
| 1 | Brand Collection | `collection.html?c=brand&brand=<slug>` |
| 1 | Product Detail Page | `product.html` |
| 1 | **Occasions & Gifts Hub** | `occasions-gifts.html` |
| 1 | **Sourcing Promise** (trust) | `sourcing-promise.html` |
| 2 | Category Collection | `collection.html?c=mens\|womens\|unisex\|kids` |
| 2 | Scent-Family Collection | `collection.html?c=scent-family&family=<x>` |
| 2 | Occasion Landing | `collection.html?c=eid\|wedding\|date-night\|gifts-for-him\|gifts-for-her` |
| 2 | Gift Sets | `gift-sets.html` |
| 2 | Discovery Kits | `collection.html?c=discovery-kits` |
| 2 | **Find My Scent (Quiz)** | `find-my-scent.html` |
| 2 | Guides Hub | `journal.html` |
| 2 | **Guide Article** | `guide-article.html` |
| 3 | About | `about.html` |
| 3 | Reviews | `reviews.html` |
| 3 | **Account & Reorder** | `account.html` (order history + one-tap reorder) |
| 3 | Contact | `contact.html` |
| 3 | FAQs | `faqs.html` |
| Util | **Wishlist** | `wishlist.html` (save → move-to-cart → product) |
| Util | **Cart** | `cart.html` |
| Util | Checkout (upsell/AOV + payment) | `checkout.html` |
| Util | **Order Confirmation** (post-payment) | `order-confirmation.html` (tracker → track order → account) |
| Util | **Search** | `search.html` |
| Legal | Shipping / Refund / **Payment** / Privacy / Terms | `legal/*.html` |
| Util | **Custom 404** | `404.html` |
| Util | LLMs.txt | `llm.txt` |
| P2 | Custom Mixing | Mix-into-Spray wizard on `product.html` (oil PDP) |
| P2 | Referral | Referral modal (sitewide) |
| T4 | Subscriptions / Arabic / Rewards | Reserved — not built (per strategy) |

(Extra retained from the earlier descriptive sitemap: `crazy-deals.html`, the lifestyle &
weather collection sets, and the editorial guides — all reachable and on-brand.)

## Purchase funnel (fully interlinked)
Every step links forward and back, and each nav-bar icon lands on a real page:

`Product` → **Add to Cart** (badge bumps) or **Buy Now** → `Cart` → **Proceed to Checkout**
→ `Checkout` (contact + payment) → **Place Order** → `Order Confirmation`
→ **Track Your Order** → `Account`.

- Nav icons: **Search** → `search.html`, **Account** → `account.html`, **Wishlist** →
  `wishlist.html`, **Cart** → `cart.html` (all live pages, no dead ends).
- `Wishlist` → **Move to Cart** / item → `Product`; empty state → best-sellers + quiz.
- `Order Confirmation` has an order tracker, delivery ETA, invoice action, WhatsApp support,
  and a post-purchase cross-sell grid → `Product`.
- Cart/checkout/confirmation line items link back to `Product` / the relevant collection.

## Strategy features implemented this pass
- **Shop mega-menu** (Our Brands · Categories · Formats · Scent-family · Best-sellers) — desktop dropdown, mobile nested drawer.
- **Locked 4-column footer** — Shop · Discover · Help · Company (+ visible email, socials).
- **Occasions & Gifts** hub + Eid / Wedding / Gifts-for-Him / Gifts-for-Her occasion collections, each with an explicit **delivery-cutoff band**.
- **Sourcing Promise** page (own-brand vs verified-resale explainer, how-we-verify, counterfeit-trust framing, reviews) — linked from **6 surfaces** (footer, home, PDP, brand index, About, brand-collection trust band).
- **Exit-intent custom-blend**: the AI concierge offers a made-to-order custom spray only when the visitor is about to leave (desktop mouse-leave / mobile scroll-up), and is disabled on cart & checkout.
- **Cart** (free-delivery nudge + cross-sell) distinct from **Checkout** (upsell shelf + free-gift threshold).
- **Search** (predictive preview + no-results rescue) and **Custom 404** (rescue to shop + quiz).
- **Account & Reorder** dashboard with order history + one-tap reorder + saved details.

## Color system — 60 · 30 · 10 (proper color theory)
One warm, analogous luxury palette with a single disciplined accent. Documented as
semantic tokens in `theme.css` `:root` (and mirrored in `index.html`): `--c-dominant`,
`--c-secondary`, `--c-accent` (+ light/dark variants and `--on-dark`).

| Role | Share | Hue | Where it lives |
|---|---|---|---|
| **Dominant** | ~60% | Warm cream `#F7F2EA` (`--cream`, `--cream-mid` alt) | Page backgrounds, most content sections, product/rv cards. The airy canvas. |
| **Secondary** | ~30% | Espresso ink / charcoal `#0D0A06`→`#1C1812` | The "premium dark" structure — every page hero, the **testimonials band** (`.reviews`, now dark), CTA bands (`.cta-band`), the dark `.finder`/`.gender` feature bands, header-on-scroll and footer. Deployed at a ~1/3 cadence so each page has a deliberate dark rhythm. |
| **Accent** | ~10% | Antique gold `#C9A84C` (`--gold`) | CTAs, active nav, key icons, prices, labels, dividers, focus rings, hairline seams — **never a band background**. |

Rules enforced: gold stays small-area only (verified — no gold section fills); neutrals
stay in one warm family (analogous harmony); body text is ink-on-cream or cream-on-ink
(both > 4.5:1); dark bands carry a fine gold hairline (`border-top`) so seams read crisply
and never merge with an adjacent dark section. Flipping the *shared* `.reviews` band to the
secondary dark propagates the 30% to every page that shows social proof, in one change.

## Imagery
All product/scene imagery uses the real photos from `Website Assets/`, curated into
`assets/img/`. Team = monogram avatars; contact map = CSS street-map; only Google Fonts load remotely.

Open `index.html` and click through — all navigation is wired.
