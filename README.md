# The Fragrance Secrets — Shopify Liquid theme

Ported from the static HTML build (`/*.html`, `assets/css`, `assets/js`) to a
native Shopify Online Store 2.0 theme, following `NEXTJS-TO-SHOPIFY-MIGRATION-GUIDE.md`.

## Structure
```
layout/theme.liquid        The HTML shell: head, fonts, design tokens (:root from settings),
                           section groups (header / footer / overlays), global CSS + JS.
layout/password.liquid     Storefront password page shell.
sections/
  header.liquid            Shop mega-menu header (native /collections, /pages, /blogs links).
  footer.liquid            Locked 4-column footer (link columns are editable blocks).
  announcement-bar.liquid  Scrolling marquee (message blocks).
  overlays.liquid          WhatsApp float, AI "Find My Scent" concierge, referral + Mix modals.
  header-group.json /
  footer-group.json /
  overlay-group.json       Section groups rendered on every template.
  main-product.liquid      PDP driven by the `product` object (gallery, variants, price,
                           metafields, product form + payment button).
  main-collection.liquid   Native collection: collection.filters + collection.products + paginate.
  main-cart.liquid         Native cart from the `cart` object (qty change / remove / totals).
  main-search.liquid       Native search (form → routes.search_url, renders search.results).
  main-list-collections /
  main-blog / main-article / main-page / main-404 / main-password
  main-login / main-register / main-account / main-order /
  main-addresses / main-reset-password / main-activate-account
  page-<handle>.liquid     28 ported content pages (about, faqs, brands, gift-sets, legal, …).
snippets/
  product-card.liquid      Native product card (Shopify product → the .prod-card markup).
  star-rating.liquid       5-star renderer.
assets/
  theme.css, pages.css     Design system (ported verbatim — no build step).
  app.js                   Shared runtime: interactivity + demo-data hydration of [data-render].
  collections.js           Legacy collection-config engine (retained, dormant — see note).
  *.png / *.jpg / *.webp    All imagery, flattened (Shopify serves assets/ flat).
config/settings_schema.json, settings_data.json   Design tokens + layout settings.
locales/en.default.json                            UI strings.
templates/*.json           One per page type → URL (see the migration guide §0).
```

## Design tokens
`layout/theme.liquid` injects `--gold / --cream / --ink / --charcoal` into `:root` from
theme settings, overriding the CSS defaults so merchants can recolour in the editor.

## How dynamic content renders
- **Commerce pages** (product, collection, cart, search, list-collections, blog, article,
  customer/*) are **native Liquid** — they read `product`, `collection`, `cart`, `search`,
  `customer`, `blog`, `article` directly.
- **Marketing / content pages** keep their `[data-render="products|reviews|kits|blogs|brands|
  brand-track|ugc"]` hooks, hydrated client-side by `app.js` from its built-in demo catalogue,
  so the theme renders fully in preview before products exist. Home product grids and the
  search "popular" grid fall back to native `collection.products` loops when real data exists.

> `collections.js` is retained for reference but **dormant**: the collection template is native
> Liquid, so nothing carries the `[data-collection]` attribute that would wake the JS engine.

## Remaining data-layer work (manual, needs a store + Admin API — see migration guide §7)
The theme markup is complete. To make it a live store, populate Shopify's data model:
1. **Products & variants** (`productSet`) — vendor = brand; Size options; `compare_at_price`
   for the strike-through; images uploaded via staged upload.
2. **Metafields** read by the theme (all optional, with fallbacks):
   `custom.badge`, `custom.badge_class`, `custom.rating` / `reviews.rating`,
   `custom.review_count` / `reviews.rating_count`, `custom.longevity`, `custom.sillage`,
   `custom.best_for`, `custom.origin`, `custom.notes_top/heart/base`, `custom.hook`,
   `custom.barcode`, `custom.hero_image` (collections). Reference metafields need a
   **definition** first; `metafieldsSet` is atomic.
3. **Collections** — create these handles (referenced by the header/footer/links):
   `all, best-sellers, new-arrivals, crazy-deals, discovery-kits, gift-sets, own-brand,
   mens, womens, kids, unisex, luxury, miracle-plant, perfume-oil, attar, arabic, inspired,
   office-wear, date-night, party-clubbing, wedding-formal, everyday-signature, gym,
   travel-friendly, vacation-beach, dinner-evening, desert-climate, humid-weather, rainy-day,
   snow-season, beach-vacation, tropical-climate, dry-weather, monsoon-ready, winter-holiday,
   spring-bloom, oud-woody, fresh-citrus, floral-rose, sweet-gourmand, spicy-oriental`.
   Publish each to the **Online Store** publication (`status: ACTIVE` ≠ published).
4. **Pages** — create pages with these handles: `about, contact, faqs, reviews,
   sourcing-promise, brands, gift-sets, occasions-gifts, find-my-scent, wishlist, checkout,
   order-confirmation, crazy-deals, shop-by-lifestyle, shop-by-weather, scent-education,
   buying-guides, care-storage, luxury-recommendations, seasonal-trends, category-collection,
   account-page, shipping-policy, return-policy, payment-policy, privacy-policy,
   terms-of-service, guide-article`. Each already has a `page.<handle>.json` template.
5. **Blog** — create a blog with handle `journal` for the Guides hub.
6. **Search & Discovery app** — add the storefront **filters** you want on collection pages
   (Gender / Scent family / Price). There is no Admin API for this; it's a manual step.
7. Optionally swap the `[data-render]` demo grids on marketing pages for real
   `{% for product in collections['x'].products %}` loops once collections are populated.
