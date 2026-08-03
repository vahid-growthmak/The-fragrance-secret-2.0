# Going live: deploying this theme onto the production store

## What this is — and what it is not

This is **not** a store migration. The production store has real orders, customers,
a domain and SEO history; transferring the Partner dev store would abandon all of
it. What happens instead is a one-way deployment:

- **Theme code** → pushed to the live store (portable; no dev domain is hardcoded anywhere).
- **Supporting store data** the theme depends on — collections, template
  assignments, pages → recreated on the live store.
- **Products, prices, descriptions, inventory, customers, orders** → left completely
  untouched on the live store.

That last line is a hard rule, not a preference. See [Never do this](#never-do-this).

---

## Pre-flight: what the theme depends on

The theme reads store state that must already exist, or pages silently fall back to
default layouts. Counted from the repo:

| Dependency | Count | Consequence if missing |
|---|---|---|
| Collections with matching handle **and `templateSuffix` set** | **89** | Collection renders the default layout — all SEO copy, FAQs and internal links vanish |
| Pages with matching handle and template suffix | **30** | 404 |
| Brand handles inside section settings (`brand_collections`) | 12 | "Explore Other Brands" strip renders empty |
| Product metafields (see [Step 4](#step-4-verify-metafield-keys--do-this-before-anything-else)) | per product | Scent pyramid, FAQ schema, badges, ratings disappear from PDPs |
| Theme app embeds — Judge.me `judgeme_core`, Chizy `chat-bubble` | 2 | Reviews and chat don't load |

The two app-embed IDs in `config/settings_data.json` are tied to **this** store's app
installations. They do not carry over. Both apps must be installed on the live store
and their embeds re-enabled there.

---

## Step 1 — Create the API token

In the **live store's admin** (not the Partner dashboard — those apps are for
distributable apps; a custom app is simpler here and its token doesn't expire):

    Settings → Apps and sales channels → Develop apps → Create an app

Admin API scopes to enable:

| Scope | Needed for |
|---|---|
| `read_products`, `write_products` | reading the catalog, creating collections, writing product metafields |
| `read_publications`, `write_publications` | publishing collections to the Online Store channel |
| `read_content`, `write_content` | pages and URL redirects |
| `read_themes`, `write_themes` | theme inspection |

> `read_publications` is not optional. Its absence on the dev store is exactly what
> silently created all 49 brand collections **unpublished** — every brand page 404'd
> and looked fine in the admin.

Install the app, reveal the Admin API access token (`shpat_…`), and store it in
`.env.live` — a **separate file** from the dev `.env`:

```
SHOPIFY_STORE_DOMAIN=<live>.myshopify.com
SHOPIFY_ADMIN_ACCESS_TOKEN=shpat_…
SHOPIFY_API_VERSION=2025-01
```

`.env*` is gitignored. Keep it that way — never commit a token.

Both scripts in `scripts/` need a `--store` flag added so dev and live credentials
can't be confused. Do that before the first live write.

---

## Step 2 — Audit before writing anything

Read-only, and it determines everything after it. With the live token, produce a diff:

- Which of the 89 collection handles already exist on live, and what their current
  `templateSuffix` is.
- Which of the 30 page handles exist.
- Current live URLs for collections and pages — this is the input to
  [Step 8](#step-8--url-redirects).
- Which products carry which metafield keys.

Write nothing until this diff has been read.

---

## Step 3 — Install the apps

Install **Judge.me** and **Chizy AI Chatbot** on the live store, on whatever plan is
required, then enable both theme app embeds. Verify in the live theme editor that the
embeds appear — the IDs in `config/settings_data.json` will be regenerated for the
live installs, which is expected.

Chizy also carries settings that live outside the theme: `data-bubble-color`,
`data-initial-message`, `data-brand-name`, and the pre-chat/lead-capture form if it
offers one. Those must be re-entered in Chizy's admin on the live store; the gold
restyle in `assets/theme.css` travels with the theme, but their settings don't.

---

## Step 4 — Verify metafield keys — do this before anything else

**This is the step most likely to break silently**, because the live store's product
content has diverged from dev: descriptions were rewritten and new metafields were
added. If the live keys don't match what the theme reads, PDP sections render empty
with no error.

The theme reads exactly these:

| Namespace / key | Used by |
|---|---|
| `custom.faq_schema`, `custom.faq` | FAQPage structured data (`snippets/product-schema.liquid`) |
| `custom.notes_top`, `custom.notes_heart`, `custom.notes_base` | scent pyramid |
| `custom.longevity`, `custom.sillage` | performance row |
| `custom.badge`, `custom.badge_class` | product card badge |
| `custom.rating`, `custom.review_count` | rating display |
| `custom.origin`, `custom.best_for`, `custom.related`, `custom.hero_image` | PDP detail blocks |
| `reviews.rating`, `reviews.rating_count` | Shopify review aggregates |
| `judgeme.widget`, `judgeme.review_widget_data`, `judgeme.badge`, `judgeme.shop_reviews_count` | Judge.me widgets |

For each one, check on live: does the key exist, and is the **type** the same? Then
either

- **rename the live metafield** to match the theme, or
- **update the theme** to read the live key name.

Updating the theme is usually the better call — the live data is the source of truth
and other systems may already depend on those keys. Decide per key, don't bulk-rename.

`custom.faq_schema` and `custom.faq` are the two most likely to be absent, since they
were created on the dev store for the schema work. Those *can* be copied from dev
(they're content this project authored) — matched by product handle, writing only
those two keys and nothing else on the product.

---

## Step 5 — Collections

89 collections need to exist with the right handle, be published to the Online Store,
and carry the right `templateSuffix`.

```bash
# 49 brand smart collections (vendor rule). Dry-run first — it defaults to dry-run.
python3 scripts/create-brand-collections.py --store live
python3 scripts/create-brand-collections.py --store live --apply

# repair anything that was created unpublished
python3 scripts/create-brand-collections.py --store live --publish

# assign templateSuffix for all 89
python3 scripts/set-collection-templates.py --store live
python3 scripts/set-collection-templates.py --store live --apply
```

Then verify **zero** unpublished collections remain, and that every handle in
`templates/collection.*.json` has a matching collection whose `templateSuffix` is set.
A missing suffix is invisible in the admin and silently drops the whole page body.

Collections that already exist on live keep their products — the scripts set the
template and publication, not the membership.

---

## Step 6 — Pages

30 page templates need matching pages. Needs a small script (export from dev by
handle → create on live with the right `template_suffix`); doesn't exist yet.

Before publishing, the **Accessibility Statement** and **Copyright Notice** drafts
need a legal review. They're legal-adjacent copy generated for this project and have
never been reviewed.

---

## Step 7 — Deploy the theme, unpublished

    Online Store → Themes → Add theme → Connect from GitHub

Point it at a **`production` branch**, not `main`. The dev store currently pushes its
own theme-editor edits to `main` (see the `Update from Shopify for theme…` commits);
if live also tracked `main`, every dev-store tweak would deploy straight to the live
storefront with no gate. Releasing then means merging `main → production`
deliberately.

The theme installs **unpublished**. Nothing customer-facing changes yet.

---

## Step 8 — Preview QA on live data

Preview the unpublished theme (Actions → Preview) and walk through, on real products:

- A PDP: scent pyramid, badges, FAQ accordion, ratings, "More from this brand",
  "Explore Other Brands", Best Sellers, "Why Customers Choose".
- 3–4 collection pages across different families: hero, intro, filters (AJAX, no page
  reload), price filter, sticky filter panel, sibling image cards, FAQs.
- All 4 parent hub pages.
- A brand page — the failure mode to watch for is an empty product grid, which means
  the vendor rule didn't match live vendor strings.
- Header/footer: nav, social links, payment icons, policy row.
- Chat launcher and WhatsApp float — they must not overlap.
- View source on a PDP and a collection: Product, FAQPage, BreadcrumbList and
  CollectionPage schema present, and `offers` populated (it's omitted when price is 0).

---

## Step 9 — URL redirects

**The single biggest risk to existing traffic.** Any live collection or page URL that
differs from the new handle loses its rankings the moment the theme is published.

Using the Step 2 diff, list every changed URL and create a 301 for each **before**
publishing:

    Online Store → Navigation → URL Redirects

Bulk CSV import is supported. Also confirm `layout/theme.liquid`'s `noindex` on
filtered collection URLs behaves correctly on the live domain.

---

## Step 10 — Publish, with a rollback ready

1. **Duplicate the current live theme** (Actions → Duplicate) and name it
   `BACKUP pre-launch <date>`. This is the instant rollback — do not skip it.
2. Publish the new theme.
3. Immediately verify on the live domain: a complete checkout, PDP rendering, reviews
   loading, chat opening, and the 301s resolving.
4. Rollback if needed: publish the backup theme. Seconds, not minutes.

---

## Post-launch

- **Meta titles and descriptions** for the 89 collections still aren't entered. The
  copy exists in the source documents and can be pushed in bulk via the API.
- `la-parfum-galleria-exclusif` is empty — no live vendor matches its rule.
- Three brand pages link to `/collections/afnan`, which has no collection or document.
- `/collections/all` is a built-in route; `templates/collection.all-products.json`
  exists but is unused.
- No Climate hub document exists, so `/pages/shop-by-weather` still runs its original
  layout.
- The brand scroller in `sections/home.liquid` falls back to brand names because no
  logo assets exist. Real logos need licensing, or the typographic-wordmark
  alternative.
- Source content folders (`Shop by Category/`, `49 Brands Content/`, etc.) and
  `mens.webp` are untracked. Decide whether they belong in the repo.

---

## Never do this

The live store's product content has diverged from dev — descriptions were rewritten
and metafields were added. Therefore:

- **Never push dev product descriptions to live.** They are older and would silently
  overwrite the current copy.
- **Never push dev prices to live.** All 928 dev products are AED 0.00. Pushing them
  would zero out the real catalog.
- **Never bulk-write product metafields** without an explicit key allow-list. Writing
  a whole metafield set would clobber the new keys added on live.
- **Never `--apply` before reading the dry-run output.** Both scripts default to
  dry-run for this reason.
- **Never publish the new theme before the backup duplicate exists.**

Any product-touching script must name the exact fields it writes and touch nothing
else.
