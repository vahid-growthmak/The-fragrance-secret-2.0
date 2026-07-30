# Product upload template — guide

Fill **`product-upload-template.csv`** (open in Excel or Google Sheets), one product per row,
then send it back and I'll create/update the products in Shopify (metafields, tags, collections,
publishing — all handled automatically). Row 1 is **Khadlaj Titan**, filled in as a reference —
copy its style. There are two blank rows to start; add as many rows as you need.

> Tip: for the multi-line fields (`description`, `why_youll_love`, `best_for_details`, `faq`)
> use a new line **inside the cell** (Alt+Enter in Excel, Ctrl/⌘+Enter in Google Sheets).

## Columns

### Core
| Column | Required | Notes |
|---|---|---|
| `title` | ✅ | Full product title (used verbatim). |
| `vendor` | ✅ | Brand name (e.g. Khadlaj). Powers "More from [Brand]" + the brand link. |
| `product_type` | ✅ | e.g. `Eau de Parfum`. |
| `status` | – | `active` (live) or `draft`. Default `active`. |
| `price` | ✅ | Number only, no currency symbol (e.g. `24.99`). |
| `compare_at_price` | – | Original price for the strike-through / "Save %". Leave blank for no discount. |
| `sku` | – | Optional stock code. |
| `size` | – | Variant size shown/added to cart (e.g. `100ML`). Default `100ML`. |

### Merchandising (drives collections & badges)
| Column | Notes |
|---|---|
| `gender` | One of: `Men`, `Women`, `Unisex`, `Kids`. → adds to the matching collection. |
| `fragrance_family` | Display text for the tile/specs (e.g. `Spicy, Amber, Woody`). |
| `family_collection` | Scent-family **collection handle** — one of: `oud-woody`, `fresh-citrus`, `floral-rose`, `sweet-gourmand`, `spicy-oriental`. |
| `badge` | `New`, `Bestseller`, `Sale`, `Luxury`, or blank. Shows on the card + adds to New Arrivals / Best Sellers / Crazy Deals accordingly. |
| `collections_extra` | Optional extra collection handles, comma-separated (e.g. `office-wear,date-night,winter-holiday`). See the handle list below. |
| `image_url` | Public **https** image URL. Leave blank and attach the image file(s) in chat instead — I'll upload them. |

### Key-info tiles (top of PDP)
| Column | Example |
|---|---|
| `longevity` | `Long Lasting` |
| `projection` | `Moderate to Strong` |
| `best_for` | `Evening & Formal` (short tile value) |
| `made_in` | `UAE` |

### Fragrance notes
`notes_top`, `notes_heart`, `notes_base` — comma-separated (e.g. `Pink Pepper, Grapefruit, Mandarin`).

### Specifications tab
`concentration`, `product_form`, `dispenser`, `occasion`, `bottle_colour`, `ships_to`, `barcode`.
Any left blank are simply omitted from the specs table.

### Long-form content
| Column | Format |
|---|---|
| `description` | The main paragraph (Description tab). Plain text is fine. |
| `why_youll_love` | One benefit **per line** in the cell (appears under the description). |
| `best_for_details` | One bullet **per line** (the "Best For" tab). |
| `faq` | One Q&A **per line**, formatted `Question :: Answer` (use ` :: ` between question and answer). |

## Collection handles you can use in `collections_extra`
`best-sellers, new-arrivals, crazy-deals, mens, womens, kids, unisex, luxury, own-brand,
oud-woody, fresh-citrus, floral-rose, sweet-gourmand, spicy-oriental, attar, perfume-oil,
arabic, inspired, miracle-plant, gift-sets, discovery-kits, office-wear, date-night,
party-clubbing, wedding-formal, everyday-signature, gym, travel-friendly, vacation-beach,
dinner-evening, desert-climate, humid-weather, rainy-day, snow-season, beach-vacation,
tropical-climate, dry-weather, monsoon-ready, winter-holiday, spring-bloom`

## What I do with the sheet
For each row I: create the product (variant price/compare-at, SKU), set every metafield,
generate the collection tags (from gender / family_collection / badge / vendor / collections_extra),
upload the image if provided, set the description (paragraph + Why You'll Love + notes), set
Best For + FAQ, mark it ACTIVE, and publish it to the Online Store. Then it auto-appears in the
right collections and renders with the full PDP layout.
