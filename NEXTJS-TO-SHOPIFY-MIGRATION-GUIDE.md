# Next.js → Shopify (Liquid Theme) Migration Guide

A practical, reusable playbook for porting a Next.js / React storefront into a
native Shopify Liquid theme. Written from real migrations — every "Pitfall"
below is something that actually bit, not theory.

> **Mental model:** In Next.js *you* own the server, the data fetching, and the
> routing. In Shopify, **Shopify owns all three**. Your job shrinks to: (1) HTML
> templates in Liquid, (2) CSS/JS as static assets, (3) getting your content
> into Shopify's data model so Liquid can render it. Most "migration" effort is
> actually **data modeling**, not markup.

---

## 0. Architecture mapping

| Next.js concept | Shopify equivalent |
|---|---|
| `app/` / `pages/` routes | **Templates** (`templates/*.json`) — URLs are fixed by Shopify |
| React component | **Section** (`sections/*.liquid`) or **Snippet** (`snippets/*.liquid`) |
| Reusable presentational component | **Snippet** (`{% render 'card', product: p %}`) |
| Page-level composition | **Section group** (`header-group.json`, `footer-group.json`) + template JSON |
| Props | Snippet `{% render %}` params, or section/block **settings** |
| `getStaticProps` / API fetch | Liquid global objects (`product`, `collection`, `cart`, `linklists`, `settings`) |
| Tailwind / CSS Modules | One or more CSS files in `assets/`, linked from `layout/theme.liquid` |
| `useState` / client JS | Plain `assets/theme.js` (vanilla), or Web Components |
| CMS / DB (Sanity, Postgres) | **Products, Collections, Metafields, Metaobjects, Pages, Blogs, Menus** |
| Design tokens (CSS vars / config) | Theme **settings** (`config/settings_schema.json`) injected into `:root` |
| `<Image>` | `image_url` + `image_tag` filters (for Files/product images only — see §6) |
| i18n routes | Shopify **Markets** + `locales/*.json` |

**Routing is not yours to design.** Shopify dictates URLs:

| Template | URL | Main section |
|---|---|---|
| `index.json` | `/` | hero, carousels, banners |
| `product.json` | `/products/:handle` | `main-product` |
| `collection.json` | `/collections/:handle` | `main-collection` |
| `list-collections.json` | `/collections` | `main-list-collections` |
| `page.json` / `page.about.json` | `/pages/:handle` | `main-page` |
| `blog.json` / `article.json` | `/blogs/:blog/:article` | `main-blog` / `main-article` |
| `cart.json` | `/cart` | `main-cart` |
| `search.json` | `/search` | `main-search` |
| `404.json`, `password.liquid`, `gift_card.liquid` | system pages | |

You map your Next.js routes **onto** these. A custom Next.js route like
`/scent-quiz` becomes a Shopify **page** (`/pages/quiz`) with a custom template
(`page.quiz.json`).

---

## 1. Theme folder structure

```
layout/
  theme.liquid          ← the <html> shell (head, <body>, global CSS/JS, :root tokens)
  password.liquid
templates/
  *.json                ← page types → URLs (compose sections)
  customers/            ← account pages
sections/
  header.liquid, footer.liquid, hero.liquid, main-product.liquid, …
  header-group.json, footer-group.json   ← section groups (shared across pages)
snippets/
  product-card.liquid, icon.liquid, star-rating.liquid, …
assets/
  base.css, theme.js, *.png/jpg          ← served from Shopify CDN, no build step
config/
  settings_schema.json  ← theme-wide settings (design tokens, social links)
  settings_data.json    ← saved values for the above
locales/
  en.default.json       ← UI strings
```

**No build step is the default.** Plain CSS + vanilla JS served from the CDN.
(You *can* wire up a bundler, but for a port it's usually unnecessary and adds
friction.)

---

## 2. Phase 0 — Setup & access (do this first, it's the #1 time sink)

### 2.1 Create / pick a store
- New store from a description, or an existing one. Dev/affiliate stores are
  **password-protected** by default (Online Store → Preferences) — keep the
  storefront password handy; you can't anonymously `curl` the storefront.

### 2.2 Get an Admin API token — the reliable path
You'll need this to script products/collections/metafields/menus.

> **Pitfall — the wrong dashboards.** Shopify has *three* surfaces that look
> similar. The **Partner/Dev Dashboard** (`dev.shopify.com`) creates *apps* and
> only yields tokens via OAuth/`client_credentials` (which fail with
> `app_not_installed` / `shop_not_permitted` until the app is *distributed to
> and installed on* that exact store). Don't start there.

**Do this instead — store-admin custom app (always works for a store you own):**
1. `https://admin.shopify.com/store/<store>/settings/apps/development`
2. If prompted, **Allow custom app development**.
3. **Create an app** → **Configure Admin API scopes** → tick what you need
   (typical: `write_products, read_products, write_inventory, read_inventory,
   read_locations, write_files, write_publications, write_online_store_navigation,
   write_theme_code`).
4. **Install app** → **Reveal Admin API access token** → `shpat_…`.
5. Store it in `.env` (gitignored) as `SHOPIFY_ADMIN_ACCESS_TOKEN`.

Sanity-check immediately:
```bash
curl -s "https://$STORE/admin/api/2024-10/shop.json" \
  -H "X-Shopify-Access-Token: $TOKEN" | jq .shop.name
# and confirm granted scopes:
curl -s "https://$STORE/admin/oauth/access_scopes.json" \
  -H "X-Shopify-Access-Token: $TOKEN" | jq '.access_scopes[].handle'
```

> **Pitfall — token types.** Only `shpat_` (Admin API) can create products.
> `shptka_` (Theme Access) is theme-files-only. "App Automation Tokens" are
> CLI/CI deploy-only. The name a UI gives you is not the type — *test it*.

### 2.3 CLI (optional but nice for theme dev)
```bash
npm i -g @shopify/cli @shopify/theme
shopify theme dev --store <store>          # hot-reload preview
shopify theme push --unpublished --store <store>
```
The CLI handles **theme** files. It **cannot** create products — that's the
Admin API.

---

## 3. Phase 1 — Scaffold the theme shell

`layout/theme.liquid` is your `_app` + `_document`:

```liquid
<!doctype html>
<html lang="{{ request.locale.iso_code }}">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  {{ content_for_header }}   {# Shopify injects analytics/scripts here — required #}
  {%- comment -%} Inject design tokens from settings into :root {%- endcomment -%}
  <style>
    :root {
      --ink: {{ settings.color_ink | default: '#141414' }};
      --font-display-stack: {{ settings.font_display.family }}, sans-serif;
    }
    {{ settings.font_display | font_face }}
  </style>
  {{ 'base.css' | asset_url | stylesheet_tag }}
</head>
<body class="template-{{ request.page_type | handle }}">
  {% sections 'header-group' %}
  <main id="MainContent" role="main">{{ content_for_layout }}</main>  {# the template renders here #}
  {% sections 'footer-group' %}
  {{ 'theme.js' | asset_url | script_tag }}
</body>
</html>
```

Key globals you get for free: `settings`, `cart`, `shop`, `routes`,
`linklists`, `request`, `localization`, plus the page object (`product`,
`collection`, `page`, `article`, `blog`, `search`).

---

## 4. Phase 2 — Port components → sections & snippets

### 4.1 The decision: section vs snippet
- **Section** = a page-level, merchant-configurable block with its own
  `{% schema %}` (settings, blocks, presets). Use for anything a merchant should
  rearrange or edit in the Theme Editor (hero, banners, carousels, the main
  product/collection body).
- **Snippet** = a pure, parameterized partial. Use for repeated presentational
  units (product card, star rating, icon, price). Receives data via
  `{% render 'name', param: value %}` (isolated scope — pass everything in).

### 4.2 The schema pattern (props → settings)
A React component's props become **section settings** + **block settings**, with
the saved values living in the template/section-group JSON (the "two-layer"
model: schema defines *what* exists, JSON defines *the values*).

```liquid
{# sections/hero.liquid #}
<section class="hero">
  <h1>{{ section.settings.heading }}</h1>
  {%- if section.settings.cta_label != blank -%}
    <a href="{{ section.settings.cta_url }}" class="btn">{{ section.settings.cta_label }}</a>
  {%- endif -%}
</section>
{% schema %}
{
  "name": "Hero",
  "settings": [
    { "type": "richtext", "id": "heading", "label": "Heading", "default": "<p>Hello</p>" },
    { "type": "text", "id": "cta_label", "label": "Button label" },
    { "type": "url", "id": "cta_url", "label": "Button link" },
    { "type": "image_picker", "id": "image", "label": "Background" }
  ],
  "presets": [ { "name": "Hero" } ]
}
{% endschema %}
```

```json
// templates/index.json — the "values" layer
{ "sections": { "hero": { "type": "hero",
    "settings": { "heading": "<p>Smell into <strong>the future</strong></p>",
                  "cta_label": "Shop", "cta_url": "shopify://collections/all" } } },
  "order": ["hero"] }
```

### 4.3 Repeating children → **blocks**
A list of cards (`items.map(...)`) becomes section **blocks** the merchant can
add/remove/reorder:

```liquid
{%- for block in section.blocks -%}
  <a href="{{ block.settings.url }}" {{ block.shopify_attributes }}>{{ block.settings.title }}</a>
{%- endfor -%}
{% schema %}
{ "blocks": [ { "type": "card", "name": "Card",
    "settings": [ {"type":"text","id":"title","label":"Title"},
                  {"type":"url","id":"url","label":"Link"} ] } ] }
{% endschema %}
```
`{{ block.shopify_attributes }}` is **required** for Theme-Editor selection to work.

### 4.4 Section groups for shared chrome
Header and footer live in `header-group.json` / `footer-group.json` and are
rendered on every template via `{% sections 'header-group' %}`. Edit those JSON
files to assign menus and settings globally.

---

## 5. Phase 3 — Styling (Tailwind → CSS)

- **Don't ship Tailwind's full build.** Port the *computed* design into a small
  hand-written CSS file (or a compiled, purged Tailwind if you insist). Plain CSS
  is far easier to maintain in Liquid and needs no build step.
- **Design tokens → CSS custom properties**, fed from theme `settings` (see §3).
  This is the clean equivalent of `tailwind.config.js` theme values, and it lets
  merchants recolor in the editor.
- **Mobile-first**: base styles = mobile; enhance with `@media (min-width: …)`.
  Globally set `*,*::before,*::after { box-sizing: border-box }`,
  `html,body { width:100%; overflow-x:hidden }`,
  `img,svg,video,canvas { max-width:100% }`, and `min-width:0` on flex/grid
  children to kill horizontal scroll. (See the responsive checklist in §11.)

---

## 6. Phase 4 — Images & media (highest pitfall density)

> **Pitfall — `asset_url | image_tag` throws.** `image_tag` only accepts an
> **image object** or the output of **`image_url`**, which only work on **Files
> / product / collection images** — *not* theme assets. Piping a theme asset's
> `asset_url` (a plain CDN string) into `image_tag` (or `image_url`) errors:
> *"input to image_tag must be an image_url."* For a **static theme asset**, use
> a plain tag:
> ```liquid
> <img src="{{ 'hero.jpg' | asset_url }}" alt="…" width="2400" height="1600">
> ```
> For **merchant/product images**, the pipeline works:
> ```liquid
> {{ product.featured_image | image_url: width: 1000 | image_tag: loading: 'lazy', widths: '500,1000' }}
> ```

> **Pitfall — `sizes="100vw"` is fine.** That's a responsive-image *hint* in the
> `sizes` attribute, **not** a CSS width. It does not cause horizontal scroll.

### Uploading local images to the CDN by API
The built-in product-create tools want **public HTTPS URLs**. To get local files
in, use the **staged upload** flow:
1. `stagedUploadsCreate` → returns a presigned `url` + `parameters` + `resourceUrl`.
2. `POST` the bytes to that URL (multipart, parameters first, then `file=@path`) —
   no auth header, the token is in the URL.
3. Use the returned `resourceUrl` as `originalSource` in `productSet` /
   `productCreateMedia`, or pass to `fileCreate`.

> **Pitfall — Python 3.13+ `urllib` SSL.** On fresh macOS Pythons, `urllib` can't
> find CA certs (`CERTIFICATE_VERIFY_FAILED`). Just shell out to `curl` for HTTP.

---

## 7. Phase 5 — The data layer (this is the real migration)

Your CMS/DB content must become Shopify resources. Map it:

| Source data | Shopify target | Notes |
|---|---|---|
| Product records | **Products** + **Variants** | options (Size/Color) + per-variant price/inventory |
| Custom product fields (badges, ratings, "inspired by") | **Metafields** (`custom.*`) | simple types need no definition; **reference types do** |
| Reviews, FAQs, lookbook entries | **Metaobjects** + a `list.metaobject_reference` metafield | give the definition `access: { storefront: PUBLIC_READ }` to read in Liquid |
| Categories / nav groupings | **Collections** (smart or manual) | smart = rule-based (by tag/type), manual = hand-picked + ordered |
| Menus / nav | **Navigation menus** (`menuCreate`) | nested items → mega-menu columns |
| CMS pages | **Pages** / **Blogs** | |

### 7.1 Products & variants (`productSet`)
`productSet` is the declarative one-shot (title, description, type, tags, status,
options, variants, **metafields**, and **files** in a single call).

> **Pitfall — `productSet` is declarative.** Omitting `files`/`variants` on an
> update can **wipe** existing media/variants. For incremental updates use
> targeted mutations (`productUpdate`, `productVariantsBulkUpdate/Create`,
> `metafieldsSet`) instead.

### 7.2 Metafields → cards/PDP
Read in Liquid with sensible fallbacks so a bare product still renders:
```liquid
{% assign brand = product.metafields.custom.inspired_by_brand.value %}
{% assign rating = product.metafields.reviews.rating.value.rating
                   | default: product.metafields.custom.rating.value %}
```

> **Pitfall — reference metafields need a definition.** A
> `list.metaobject_reference` (or any reference) metafield **cannot be set** via
> `metafieldsSet` until a **metafield definition** for that key exists, scoped to
> the target metaobject type. And `metafieldsSet` is **atomic** — one bad entry
> rolls back the whole batch. Create the definition first.

### 7.3 Metaobjects (e.g. reviews)
1. `metaobjectDefinitionCreate` with fields + `access: { storefront: PUBLIC_READ }`.
2. `metaobjectCreate` per entry.
3. `metafieldDefinitionCreate` for `custom.reviews` as `list.metaobject_reference`
   with a `metaobject_definition_id` validation.
4. `metafieldsSet` the product's `custom.reviews` to the list of metaobject GIDs.

```liquid
{%- assign reviews = product.metafields.custom.reviews.value -%}
{%- if reviews and reviews.size > 0 -%}   {# arrays use .size, NOT .count #}
  {%- for r in reviews -%}{{ r.author.value }} — {{ r.body.value }}{%- endfor -%}
{%- endif -%}
```

> **Pitfall — `.size` not `.count`.** Liquid arrays expose `.size`. `.count`
> silently returns `nil`, so `list.count > 0` is always false and your list
> renders empty. Classic "why are my reviews not showing."

### 7.4 Collections
- **Smart** collection = `ruleSet` (e.g. `TAG EQUALS "bestseller"`). Auto-populates;
  great for gender/family/bestseller groupings if you tag products consistently.
- **Manual** collection + `sortOrder: MANUAL` + `collectionAddProductsV2` in order
  = when you need a **specific curated order** (smart collections can't be manually
  ordered).

> **Pitfall — smart-collection reindex lag.** `productsCount` reads `0` for a few
> seconds after creating a smart collection or tagging products. It's not broken;
> re-query after a short wait.

> **Pitfall — publish to the Online Store.** Creating a product/collection isn't
> enough — it must be **published to the Online Store publication**
> (`publishablePublish` to the Online Store publication GID) to appear on the
> storefront. `status: ACTIVE` ≠ published.

### 7.5 Navigation menus
`menuCreate` builds nav (the footer columns and the header mega-menu read
`linklists[handle]`). Nested items become mega-menu columns + children:
```
menuCreate(handle:"header-perfumes", items:[
  { title:"Shop", type:HTTP, url:"/collections/all", items:[ {title:"Impressions", …}, … ] },
  { title:"By Gender", …, items:[ … ] }
])
```
Then assign the handle in the section's settings (e.g. `menu_perfumes` in
`header-group.json`). The theme renders top-level items as columns and their
`link.links` as the list.

---

## 8. Phase 6 — Search, filters, dynamic behavior

- **Storefront search** → a simple `<form action="{{ routes.search_url }}" method="get">`
  with `name="q"` and `type=product`.
- **Faceted filters** (Gender / Price / etc.) → `collection.filters` in Liquid,
  but the **available facets are configured in the Search & Discovery app**, not
  the theme. Create **metafield definitions** for the fields you want filterable,
  then add them as filters in **Apps → Search & Discovery → Filters**. There is
  **no Admin API** to add storefront filters — it's a manual step; document it.
- **Client interactivity** (cart drawer, accordions, dropdown toggles, carousels)
  → vanilla JS in `theme.js`, toggling classes (`.is-open`, `body.cart-open`).
  Keep CSS and JS in agreement: if JS toggles `.facet.is-open`, the CSS reveal
  rule must key off `.is-open` (not `:hover`), or they fight each other.

---

## 9. Phase 7 — Deployment & the GitHub ↔ Shopify sync

Two ways to ship theme code:

1. **Admin API asset push** (immediate, scriptable):
   `PUT /admin/api/2024-10/themes/<theme_id>/assets.json` with
   `{ "asset": { "key": "sections/x.liquid", "value": "<contents>" } }`.
   Theme-file writes are allowed on **unpublished** themes by some tools; the
   Admin API with `write_theme_code` can update the live theme too.
2. **GitHub integration** (Online Store → Themes → connect a branch). Pushing to
   the branch deploys to the theme.

> **Pitfall — the integration is BIDIRECTIONAL.** Theme-editor / Admin-API edits
> get **auto-committed back to GitHub** as *"Update from Shopify…"*. So:
> - Pushing a file to the live theme can trigger a commit that **reverts** a
>   newer Git change if the live theme was behind.
> - Your local `git push` may be rejected (non-fast-forward) by these auto
>   commits; `git fetch && git rebase origin/main` (identical changes get
>   dropped as "already upstream").
> **Rule:** pick **one source of truth** (edit code in Git, let it deploy; use the
> Shopify editor for *content/settings only*). Don't edit the same files in both.

> **Pitfall — `*-group.json` / `templates/*.json` get an auto-generated header
> comment** ("auto-generated… may be overwritten") after a Theme-Editor/sync
> round-trip. That's expected; don't fight it.

---

## 10. Liquid quick-reference for React devs

| You want… | Liquid |
|---|---|
| `{condition && <X/>}` | `{%- if condition -%}…{%- endif -%}` |
| `{items.map(i => …)}` | `{%- for i in items -%}…{%- endfor -%}` (`forloop.index`, `forloop.first`) |
| `arr.length` | `arr.size` (**not** `.count`) |
| Ternary / fallback | `{{ value | default: 'fallback' }}` |
| Component with props | `{% render 'snippet', a: x, b: y %}` (isolated scope) |
| String/number ops | filters: `| upcase`, `| money`, `| times: 100`, `| split: ','`, `| slice:` |
| Money | `{{ price | money }}` (price is in **cents**; renders shop currency) |
| Internal URL | `{{ routes.search_url }}`, `{{ product.url }}`, `shopify://collections/x` |
| Whitespace control | `{%-` / `-%}` trims surrounding whitespace |

---

## 11. Pre-launch checklist

**Data**
- [ ] Products created, `ACTIVE`, **published to Online Store**, with images.
- [ ] Variants priced; inventory tracked or `inventoryPolicy: CONTINUE` so they're buyable.
- [ ] Metafields populated; reference metafields have definitions.
- [ ] Collections (smart + manual) populated and published; curated order where needed.
- [ ] Nav menus created and assigned in `header-group`/`footer-group`.
- [ ] Search & Discovery filters configured (manual step).

**Theme**
- [ ] No `asset_url | image_tag` (use plain `<img>` for assets).
- [ ] Arrays use `.size`. Reference lists read via `.value`.
- [ ] JS class toggles match CSS reveal selectors.
- [ ] Currency: numeric prices set; if the design shows `$` but the store is in
      another currency, that's a **store-level** Markets/currency setting.

**Responsive (mobile-first)**
- [ ] `box-sizing:border-box` global; `html,body { overflow-x:hidden; width:100% }`.
- [ ] `img,svg,video,canvas { max-width:100% }`; `min-width:0` on flex/grid children.
- [ ] Long names/prices wrap (`overflow-wrap:break-word`).
- [ ] 2-/3-col desktop grids stack; CTAs full-width where needed.
- [ ] Verified at 320 / 360 / 390px (iPhone SE is the priority screen).

**Deploy**
- [ ] One source of truth chosen (Git vs editor).
- [ ] Live theme + GitHub `main` verified identical after the round-trip.

---

## 12. The pitfalls, condensed (print this)

1. Start auth at the **store-admin custom app**, not the Partner/Dev Dashboard.
2. Only `shpat_` tokens create products. Test the token immediately.
3. `asset_url | image_tag` → error. Plain `<img>` for theme assets.
4. Liquid arrays use **`.size`**, never `.count`.
5. Reference metafields need a **definition** first; `metafieldsSet` is atomic.
6. Metaobjects/reference fields need **`storefront: PUBLIC_READ`** to render.
7. `status: ACTIVE` ≠ visible — **publish to the Online Store publication**.
8. Smart collections reindex with a delay; don't trust an instant `0` count.
9. `productSet` is declarative — omitting fields can delete media/variants.
10. Storefront **filters live in Search & Discovery**, not the theme (manual step).
11. GitHub↔Shopify sync is **bidirectional** — pick one source of truth.
12. Dev stores are **password-protected** — you can't anonymously fetch the storefront.
13. Don't redesign desktop when fixing mobile — add mobile-first layers only.
</content>
</invoke>
