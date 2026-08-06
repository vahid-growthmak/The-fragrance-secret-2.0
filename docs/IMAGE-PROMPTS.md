# Image Prompts — The Fragrance Secrets

Copy a prompt, paste it into ChatGPT (or any image model), save the result, and
hand me the folder. Every entry states the exact pixel size the theme expects and
where the text sits, so the subject never lands under an overlay.

**How to use this file**
1. Find the slot you need in the index below.
2. Paste the **House style block** first, then the prompt for that slot.
3. Ask for the stated size. If the model refuses a size, ask for the nearest
   allowed aspect ratio and I will resize — never accept a different *ratio*,
   because the theme crops from the centre and you will lose the subject.

---

## House style block — paste this before every prompt

> Luxury perfume e-commerce photography for an Indian premium fragrance retailer.
> Editorial product photography, shot on a full-frame camera with an 85mm lens,
> shallow depth of field, physically accurate reflections and soft falloff.
> Palette: near-black and deep charcoal (#0D0A06, #1C1812), warm antique gold
> (#C9A84C, #E2C97E), and warm cream (#F7F2EA). Lighting is warm, low-key and
> directional, with gold rim-light on glass and metal. Mood: quiet, expensive,
> restrained — not garish, no neon, no glitter, no lens flare.
> No text, no logos, no watermarks, no brand names, no packaging copy anywhere in
> the image. Photorealistic, not illustration, not 3D render.

**Why "no text":** the theme draws all headings itself. Generated lettering is
almost always misspelled and it will clash with the real heading on top of it.

---

## A note on "Arabian" vs India

Keep the two separate — they are not the same thing and conflating them will make
the imagery wrong:

- **The products are Arabian/oriental fragrances.** Oud, attar, bakhoor, amber,
  rose. That vocabulary stays in the *product* imagery regardless of where the
  business sits.
- **The business is India-based.** So *context* imagery — lifestyle, climate,
  festive, delivery, model shots — should read Indian: Indian interiors and
  architecture, Indian festive settings (Diwali, Eid in India, wedding season),
  the monsoon, Indian summer heat, Indian models where people appear.

A bottle of oud on dark marble is correct for both. A model in a *thobe* on a
Dubai skyline balcony is not — that would be a lifestyle shot for the old
positioning.

---

## Index

| # | Slot | Size | Count |
|---|---|---|---|
| 1 | Home hero | 2880 × 1620 | 1 |
| 2 | Collection / brand banner — desktop | 2880 × 1000 | 92 |
| 3 | Collection / brand banner — phone | 1200 × 417 | 92 |
| 4 | Signature-house & collection card | 1200 × 960 | as needed |
| 5 | Lifestyle / climate tile | 700 × 700 | 12 |
| 6 | Scent-family card | 700 × 700 | 5 |
| 7 | Category card | 600 × 600 | 8 |
| 8 | Hub-page hero (3 missing) | 2880 × 1000 | 3 |
| 9 | About page | 1400 × 1470 | 1 |
| 10 | Journal / guide article | 1200 × 750 | per article |
| 11 | Product photography fallback | 1200 × 1200 | — |

Existing files follow the naming the theme already reads: `<handle>-hero.webp`,
`<handle>-hero-sm.webp`, `<handle>-tile.webp`, `<handle>-card.webp`,
`cat-<name>.jpg`. Match those names and the swap is automatic.

---

## 1 — Home hero · 2880 × 1620 px (16:9)

**Safe zone:** the left 45% carries a dark scrim with the headline, eyebrow and
four trust points. Keep the subject **right of centre** and leave the left third
visually quiet and dark.

> A hero composition for a luxury Indian perfume house. Three to five ornate
> perfume bottles — faceted crystal, brushed gold caps, one deep sapphire, one
> amber — arranged at varying heights on a slab of dark veined marble. Behind
> them, softly out of focus, a carved jaali screen with warm candlelight glowing
> through the lattice. Thin ribbons of incense smoke drift upward on the right.
> Scattered rose petals and a few oud wood chips on the marble.
> **Composition: all bottles sit in the right two-thirds of the frame. The left
> third is deep shadow and empty — reserved for text.** Wide cinematic framing,
> 16:9.

---

## 2 — Collection & brand banner, desktop · 2880 × 1000 px

**Safe zone:** the heading and breadcrumb sit on the **left**. Left 40% must stay
dark and uncluttered. Very wide letterbox crop — do not put anything important in
the top or bottom 15%, it gets trimmed on tall screens.

**Base prompt** (swap the bracketed part per collection):

> An ultra-wide luxury banner, 2880 × 1000, letterbox. [SUBJECT]. Set on polished
> dark marble with a mirror-like reflection, warm gold rim-lighting, deep shadow
> falling across the left third of the frame. Background is dark and simple with
> soft bokeh. **The left 40% of the image must be near-black and empty — no
> objects there.** Subject sits right of centre.

**[SUBJECT] by collection type:**

| Collection | [SUBJECT] |
|---|---|
| Best Sellers | a tight cluster of six premium bottles, the tallest centred, gold caps catching the light |
| New Arrivals | three pristine bottles half wrapped in soft tissue, one sealed box just opened |
| Crazy Deals | a generous spread of eight bottles, abundant but neatly arranged, warm gold tones |
| All Products | a long receding row of many bottles fading into shadow, depth of field falling off |
| Men's | angular dark bottles — matte black, gunmetal, deep green — with leather and cedar wood |
| Women's | soft rounded bottles in blush, gold and crystal with fresh roses and jasmine |
| Kids' | small playful bottles in soft pastel with rounded caps, bright and clean, gentle lighting |
| Unisex | a balanced pair of one dark and one light bottle, symmetrical, neutral stone |
| Luxury | a single spotlit crystal flacon on a marble pedestal, extreme negative space |
| Attar | small traditional glass attar vials with gold stoppers on carved wood, no spray bottles |
| Perfume Oil | slim roll-on oil bottles, viscous amber oil visible, a dropper mid-pour |
| Arabic | ornate Arabian-style flacons with filigree metalwork beside a smoking bakhoor burner |
| Inspired | elegant unbranded bottles, clean and modern, deliberately anonymous |
| Oud & Woody | dark resinous oud wood chips, agarwood slivers, a deep brown-black bottle |
| Fresh & Citrus | bright citrus — bergamot, lime, grapefruit — sliced, water droplets, cool light |
| Floral & Rose | dense fresh roses and jasmine around a rose-tinted bottle |
| Sweet & Gourmand | vanilla pods, caramel, honey drizzle, warm amber bottle |
| Spicy & Oriental | saffron threads, cinnamon bark, cardamom pods, warm red-gold bottle |

**Brand banners (49 houses):** use the base prompt with

> [SUBJECT] = a refined arrangement of three to four perfume bottles in the visual
> character of a [luxury European designer house / traditional Arabian perfume
> house / modern niche house] — but **entirely unbranded and invented**, no real
> logos, no recognisable existing bottle designs.

⚠️ Do not ask for real brand names (Chanel, Dior, Armaf…). The model will produce
a poor imitation of a trademarked bottle and you cannot use it commercially.
Generate a *character* and let the collection title do the naming.

---

## 3 — Collection & brand banner, phone · 1200 × 417 px

Same subject, re-shot tighter — **not** a downscale of the wide one, or the
subject ends up microscopic.

> Same scene and palette as the desktop banner, recomposed for a narrow 1200 × 417
> letterbox. Two or three bottles only, larger in frame, centred slightly right.
> Left 30% dark and empty for the heading.

---

## 4 — Signature-house & collection card · 1200 × 960 px (5:4)

**Safe zone:** a dark gradient covers the **bottom third** and carries the
collection name and product count. Keep bottles in the upper two-thirds.

> A 5:4 portrait-ish card. Two or three perfume bottles standing on dark veined
> marble, lit warmly from the side, an out-of-focus carved lattice screen with
> candlelight behind. **Bottles occupy the upper two-thirds; the bottom third is
> plain dark marble and shadow with nothing important in it.** Rich, quiet,
> expensive.

---

## 5 — Lifestyle & climate tile · 700 × 700 px (square)

Also supply a 350 × 350 phone variant, or I will downscale it.

**Safe zone:** the label sits across the bottom on a dark gradient.

**Lifestyle** — these should read *Indian* context:

| Tile | Prompt subject |
|---|---|
| Everyday | a single bottle on a sunlit bedside table, linen, morning light through a window |
| Office Wear | a bottle beside a laptop and notebook on a clean desk, cool daylight, corporate calm |
| Date Night | a bottle on a restaurant table, warm candlelight, wine glass softly blurred behind |
| Party / Clubbing | a bottle with warm gold nightlife bokeh behind, energetic but tasteful |
| Wedding | a bottle among marigold garlands and red-and-gold Indian wedding textiles |
| Formal Event | a bottle beside cufflinks and a folded silk pocket square, low warm light |
| Gym | a bottle beside a rolled towel and water bottle, clean bright light, fresh and crisp |
| Travel | a compact bottle beside a passport and leather luggage tag, airport window light |
| Beach / Vacation | a bottle on warm sand with soft turquoise water blurred behind, bright daylight |
| Evening Wear | a bottle on a dark console table under a warm lamp, dusk through a window |

**Climate** — these should read *Indian* seasons:

| Tile | Prompt subject |
|---|---|
| Summer | a fresh bottle with condensation, bright hard sunlight, dry heat haze |
| Winter | a bottle beside a wool shawl, cool blue window light, cosy interior |
| Spring | a bottle among fresh blossoms, soft green light, gentle and airy |
| Monsoon / Rainy Day | a bottle on a windowsill with heavy rain streaming down the glass behind, grey-green light, wet foliage outside |
| Humid Weather | a light fresh bottle, misty warm air, soft diffused light, tropical greenery |
| Tropical | a bottle among palm and banana leaves, warm dappled sun |
| Dry Weather | a bottle on cracked warm earth, golden hour, arid and still |
| Hot Weather | a bottle in bright overhead sun, strong short shadows, shimmering heat |
| Cold Weather | a bottle beside a warm knit, frost on the window, blue-grey light |

---

## 6 — Scent-family card · 700 × 700 px

Use the scent-family subjects from section 2, recomposed square, ingredients
foregrounded and the bottle secondary. Bottom third stays quiet for the label.

---

## 7 — Category card · 600 × 600 px

> A clean square category card. [Men's / Women's / Kids' / Unisex / Luxury /
> Attar / Perfume Oil / Arabic] fragrance bottles, two or three, centred on a warm
> cream (#F7F2EA) seamless background with a soft drop shadow. Bright, even,
> catalogue-style lighting. Minimal props. Lots of breathing room around the
> subject.

Note these sit on the **light** part of the page, so unlike the banners they want
a cream background, not black.

---

## 8 — Hub-page heroes · 2880 × 1000 px — **currently missing**

Three hub pages have no banner at all. Same rules as section 2.

| Page | Save as | Subject |
|---|---|---|
| Shop by Lifestyle | `lifestyle-hub-hero.webp` | a row of bottles each in a different setting fading left to right — desk, restaurant table, gym bench, beach sand — unified by warm gold light |
| Shop by Climate | `weather-hub-hero.webp` | one bottle repeated across four seasonal moods in a single wide frame — monsoon rain, dry heat, winter cool, spring bloom |
| Shop by Scent Family | `scent-family-hub-hero.webp` | five ingredient groupings in a row — oud wood, citrus, roses, vanilla, saffron — on dark marble, each softly spotlit |

---

## 9 — About page · 1400 × 1470 px (portrait)

> A warm portrait-format editorial image for a fragrance company's story page.
> A perfumer's worktable seen from a slight angle: amber sample vials in a wooden
> rack, a brass funnel, blotter strips fanned out, a notebook with handwriting too
> small to read. Warm window light from the left. Shallow depth of field. Lived-in
> and craft-focused rather than clinical.

---

## 10 — Journal / guide article · 1200 × 750 px

> A wide editorial header for a fragrance article about [TOPIC]. [Subject matter
> for the topic]. Warm, magazine-quality, generous negative space in the upper
> left where a title will be placed. Photorealistic.

---

## 11 — Product photography · 1200 × 1200 px

Only for placeholders — real product shots should be actual photographs of the
actual bottle.

> A single perfume bottle centred on a seamless warm cream (#F7F2EA) background,
> soft even studio lighting from two large softboxes, gentle contact shadow
> beneath, subtle gradient falloff. Crisp, clean, catalogue-standard. Nothing else
> in frame.

---

## Delivery checklist

- [ ] Correct **pixel size**, not just the right ratio
- [ ] Subject respects the safe zone for that slot
- [ ] No text, letters, logos or watermarks anywhere
- [ ] No recognisable real-world trademarked bottle designs
- [ ] Save as PNG or JPEG — I convert to WebP and build the phone variant
- [ ] Name the file after the collection handle (`oud-woody-hero.png`) so it maps
      automatically

Drop them in a folder in the project root and tell me the folder name.
