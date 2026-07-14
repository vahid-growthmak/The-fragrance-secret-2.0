/* ═══════════════════════════════════════════════════════════════════
   COLLECTION ENGINE (collections.js)
   Renders any product-listing / collection page from a config object,
   selected via ?c=<slug>. One template (collection.html) → 35 pages,
   each honouring the exact section list from the sitemap. Loaded after
   app.js, which calls renderCollection() when [data-collection] exists.
═══════════════════════════════════════════════════════════════════ */

/* ── Shared content pools ────────────────────────────────────────── */
const FAM = ['Fresh & Citrus', 'Oud & Woody', 'Floral & Rose', 'Sweet & Gourmand', 'Spicy & Oriental'];

const FAQ_TRUST = [
  { q: 'Are your perfumes 100% authentic?', a: 'Yes. Every fragrance is either from our own manufactured brands or sourced through verified wholesalers and market-authorised channels — genuine, sealed stock. Questions about a specific item? Our human team confirms sourcing on WhatsApp before you buy.' },
  { q: 'Do you offer Cash on Delivery?', a: 'Absolutely. Cash on Delivery is available across all seven Emirates, alongside Tabby & Tamara interest-free instalments, Apple Pay, Google Pay and cards.' },
  { q: 'How fast is delivery in the UAE?', a: 'Free delivery on orders above AED 150. In-stock orders are dispatched within 48 hours, with same-day options available in Dubai for orders placed before 2 PM.' },
  { q: 'What is your return policy?', a: 'We offer 7-day hassle-free returns on unopened, sealed products. Message our team on WhatsApp and we will arrange a collection.' },
];

const XLINKS = [
  { label: 'Best Sellers', href: 'collection.html?c=best-sellers' },
  { label: 'New Arrivals', href: 'collection.html?c=new-arrivals' },
  { label: 'Gift Sets & Kits', href: 'gift-sets.html' },
  { label: 'Shop by Occasion', href: 'shop-by-lifestyle.html' },
  { label: 'Luxury Perfumes', href: 'collection.html?c=luxury' },
  { label: 'Attar & Oils', href: 'collection.html?c=attar' },
];

/* ── Section renderers ───────────────────────────────────────────── */
function crumbHTML(items) {
  if (!items || !items.length) return '';
  return `<div class="breadcrumb">` + items.map((c, i) => {
    const last = i === items.length - 1;
    const sep = last ? '' : '<span class="mi" aria-hidden="true">chevron_right</span>';
    return (last ? `<span>${c.label}</span>` : `<a href="${c.href || '#'}">${c.label}</a>`) + sep;
  }).join('') + `</div>`;
}

function secHeader(cfg) {
  const meta = (cfg.meta || []).map(m => `<span><span class="mi" aria-hidden="true">${m.ic}</span>${m.t}</span>`).join('');
  if (cfg.story && cfg.heroImg) {
    return `<section class="page-hero split tall">
      <div class="container">
        <div>
          ${crumbHTML(cfg.breadcrumb)}
          <span class="ph-eyebrow">${cfg.eyebrow}</span>
          <h1 class="ph-title">${cfg.title}</h1>
          <p class="ph-sub">${cfg.story}</p>
          ${meta ? `<div class="ph-meta">${meta}</div>` : ''}
        </div>
        <figure class="ph-figure"><img src="${cfg.heroImg}" alt="${cfg.titlePlain || 'Collection'}"/></figure>
      </div>
    </section>`;
  }
  return `<section class="page-hero tall">
    <div class="container">
      ${crumbHTML(cfg.breadcrumb)}
      <span class="ph-eyebrow">${cfg.eyebrow}</span>
      <h1 class="ph-title">${cfg.title}</h1>
      ${cfg.sub ? `<p class="ph-sub">${cfg.sub}</p>` : ''}
      ${meta ? `<div class="ph-meta">${meta}</div>` : ''}
    </div>
  </section>`;
}

function secTrust() {
  return `<section class="section-sm alt"><div class="container">
    <div class="trust-band">
      <div class="tb-item"><span class="mi" aria-hidden="true">verified_user</span><div><strong>100% Authentic</strong><span>Verified sourcing</span></div></div>
      <div class="tb-item"><span class="mi" aria-hidden="true">local_shipping</span><div><strong>Free UAE Delivery</strong><span>On orders above AED 150</span></div></div>
      <div class="tb-item"><span class="mi" aria-hidden="true">payments</span><div><strong>Cash on Delivery</strong><span>Available UAE-wide</span></div></div>
      <div class="tb-item"><span class="mi" aria-hidden="true">autorenew</span><div><strong>7-Day Returns</strong><span>No questions asked</span></div></div>
    </div>
    <div style="text-align:center;margin-top:22px"><a class="btn-ghost" href="sourcing-promise.html">See our Sourcing Promise <span class="mi" aria-hidden="true">arrow_forward</span></a></div>
  </div></section>`;
}

function secUsps(cfg) {
  if (!cfg.usps || !cfg.usps.length) return '';
  const cards = cfg.usps.map(u => `<div class="usp-card fade-up">
    <div class="usp-ic"><span class="mi" aria-hidden="true">${u.ic}</span></div>
    <h3>${u.title}</h3><p>${u.text}</p>
  </div>`).join('');
  return `<section class="section${cfg.uspsDark ? ' charcoal' : ''}"><div class="container">
    ${cfg.uspsHead ? `<div class="sec-head center"><span class="label">${cfg.uspsHead.label || 'Why This Collection'}</span><h2 class="sec-title">${cfg.uspsHead.title}</h2>${cfg.uspsHead.sub ? `<p class="sec-sub">${cfg.uspsHead.sub}</p>` : ''}</div>` : ''}
    <div class="usp-grid${cfg.usps.length === 4 ? ' four' : ''}">${cards}</div>
  </div></section>`;
}

/* Top toolbar — result count, mobile "Filters" toggle, sort. The faceted
   filter itself lives in the left sidebar rendered by secGrid(). */
function secFilter(cfg) {
  if (cfg.gridKind === 'kits') return '';
  return `<div class="filter-bar" id="filterBar"><div class="container"><div class="fb-inner">
    <button type="button" class="fb-toggle" id="fbToggle"><span class="mi" aria-hidden="true">tune</span>Filters &amp; Sort</button>
  </div></div></div>`;
}

/* Sort control — now lives inside the sidebar (top of the filter panel) */
function sidebarSortHTML() {
  return `<div class="sf-group sf-sortgroup">
    <div class="sf-gtitle sf-gtitle-static">Sort By</div>
    <div class="sf-gbody">
      <select class="sf-sort" id="fbSort">
        <option value="featured">Featured</option>
        <option value="low">Price: Low to High</option>
        <option value="high">Price: High to Low</option>
        <option value="rating">Top Rated</option>
      </select>
    </div>
  </div>`;
}

/* Category navigation groups (Category · Lifestyle · Weather) — sourced from
   the shared SHOP_MEGA so the menu and the sidebar stay in sync. */
function sidebarCatsHTML(cfg) {
  const cur = (typeof qs === 'function' ? qs('c') : '') || '';
  const groups = (typeof SHOP_MEGA !== 'undefined' ? SHOP_MEGA : []).filter(g => /^Shop by/i.test(g.title));
  return groups.map((g, gi) => {
    const links = g.links.map(([t, h]) => {
      const m = /[?&]c=([^&]+)/.exec(h);
      const slug = m ? m[1] : '';
      const active = slug && slug === cur ? ' sf-cat-active' : '';
      return `<a class="sf-cat${active}" href="${h}">${t}</a>`;
    }).join('');
    return `<details class="sf-group"${gi === 0 ? ' open' : ''}>
      <summary class="sf-gtitle">${g.title}<span class="mi sf-chev" aria-hidden="true">expand_more</span></summary>
      <div class="sf-gbody"><div class="sf-cats">${links}</div></div>
    </details>`;
  }).join('');
}

/* ── Faceted sidebar builders ────────────────────────────────────── */
function countBy(list, key) {
  const m = {};
  list.forEach(p => { const v = p[key]; if (v != null) m[v] = (m[v] || 0) + 1; });
  return m;
}

function facetGroup(title, name, items, opts) {
  opts = opts || {};
  const rows = items.map((it, i) => `<label class="sf-opt${opts.limit && i >= opts.limit ? ' sf-hidden' : ''}">
      <input type="checkbox" data-facet="${name}" value="${esc(it.value)}"/>
      <span class="sf-box"><span class="mi" aria-hidden="true">check</span></span>
      <span class="sf-label">${esc(it.label)}</span>
      ${it.count != null ? `<span class="sf-count">${it.count}</span>` : ''}
    </label>`).join('');
  const more = (opts.limit && items.length > opts.limit)
    ? `<button type="button" class="sf-more" data-more>+ ${items.length - opts.limit} more</button>` : '';
  const search = opts.search
    ? `<div class="sf-search"><span class="mi" aria-hidden="true">search</span><input type="text" placeholder="Search ${esc(opts.search)}" data-search="${name}"/></div>` : '';
  return `<details class="sf-group" open>
    <summary class="sf-gtitle">${title}<span class="mi sf-chev" aria-hidden="true">expand_more</span></summary>
    <div class="sf-gbody">${search}<div class="sf-opts" data-opts="${name}">${rows}</div>${more}</div>
  </details>`;
}

function facetsHTML(cfg) {
  const list = cfg._products || [];
  const famC = countBy(list, 'family');
  const famItems = FAM.filter(f => famC[f]).map(f => ({ value: f, label: f, count: famC[f] }));
  const brandC = countBy(list, 'brand');
  const brandItems = Object.keys(brandC).sort().map(b => ({ value: b, label: b, count: brandC[b] }));
  const genC = countBy(list, 'gender');
  const genItems = ['Men', 'Women', 'Unisex'].filter(g => genC[g]).map(g => ({ value: g, label: g, count: genC[g] }));
  const priceItems = [
    { value: '0-100', label: 'Under AED 100' },
    { value: '100-200', label: 'AED 100 – 200' },
    { value: '200-300', label: 'AED 200 – 300' },
    { value: '300-99999', label: 'AED 300 & above' },
  ].map(r => {
    const [lo, hi] = r.value.split('-').map(Number);
    return { ...r, count: list.filter(p => p.price >= lo && p.price < hi).length };
  }).filter(r => r.count);
  return `
    ${famItems.length ? facetGroup('Scent Family', 'fam', famItems) : ''}
    ${brandItems.length ? facetGroup('Brand', 'brand', brandItems, { limit: 6, search: 'brand' }) : ''}
    ${genItems.length ? facetGroup('Gender', 'gender', genItems) : ''}
    ${priceItems.length ? facetGroup('Price', 'price', priceItems) : ''}`;
}

function secGrid(cfg) {
  const head = `<div class="results-head">
      <div><span class="label">${cfg.gridLabel || 'The Collection'}</span><h2 class="sec-title" style="font-size:2rem">${cfg.gridTitle || 'Shop the Range'}</h2></div>
    </div>`;
  const pager = `<div class="pagination">
      <span class="current">1</span><a href="#grid">2</a><a href="#grid">3</a><span>…</span><a href="#grid">9</a>
      <a href="#grid" aria-label="Next page"><span class="mi" aria-hidden="true">chevron_right</span></a>
    </div>`;
  // Kits pages have no facetable attributes — render a plain full-width grid.
  if (cfg.gridKind === 'kits') {
    return `<section class="section" id="grid"><div class="container">
      ${head}<div class="products-grid" id="collGrid"></div>${pager}
    </div></section>`;
  }
  return `<section class="section" id="grid"><div class="container">
    ${head}
    <div class="shop-layout">
      <aside class="shop-filters" id="shopFilters" aria-label="Product filters">
        <div class="sf-head">
          <span class="sf-title"><span class="mi" aria-hidden="true">tune</span>Filters</span>
          <button type="button" class="sf-clear" id="sfClear">Clear all</button>
          <button type="button" class="sf-close" id="sfClose" aria-label="Close filters"><span class="mi" aria-hidden="true">close</span></button>
        </div>
        <div class="sf-scroll">${sidebarSortHTML()}${sidebarCatsHTML(cfg)}${facetsHTML(cfg)}</div>
      </aside>
      <div class="shop-results">
        <div class="products-grid" id="collGrid"></div>
        ${pager}
      </div>
    </div>
  </div></section>
  <div class="sf-overlay" id="sfOverlay"></div>`;
}

function secCrosslinks(cfg) {
  const links = (cfg.crosslinks || XLINKS).map(l =>
    `<a class="crosslink" href="${l.href}"><span>${l.label}</span><span class="mi" aria-hidden="true">arrow_forward</span></a>`
  ).join('');
  return `<section class="section alt"><div class="container">
    <div class="sec-head center"><span class="label">${cfg.xHead || 'Keep Exploring'}</span><h2 class="sec-title">${cfg.xTitle || 'You Might Also <em>Love</em>'}</h2></div>
    <div class="crosslink-grid">${links}</div>
  </div></section>`;
}

function secFindscent() {
  return `<section class="finder"><div class="finder-inner">
    <div class="finder-head fade-up">
      <span class="label">Personalised Recommendation</span>
      <h2 class="sec-title" style="color:var(--white)">Not Sure What to <em>Pick?</em></h2>
      <p class="sec-sub">Answer 3 quick questions and we'll find your perfect fragrance match.</p>
    </div>
    <div class="quiz-progress quiz-progress-wrap"></div>
    <div class="quiz-container-wrap"></div>
  </div></section>`;
}

function secReviews(cfg) {
  return `<section class="reviews"><div class="reviews-inner">
    <div class="reviews-head fade-up"><span class="label">${cfg.rvLabel || 'What Customers Say'}</span><h2 class="sec-title">Loved by <em>Fragrance Lovers</em></h2></div>
    <div class="rv-summary fade-up"><div class="rv-big">4.8</div><div class="rv-details"><div class="stars">${starsHTML(5)}</div><p>Based on 10,284 verified reviews</p></div></div>
    <div class="rv-grid" data-render="reviews" data-count="3"></div>
  </div></section>`;
}

function secFaq(cfg) {
  const items = (cfg.faqs || FAQ_TRUST).map(f => `<details class="faq-item">
    <summary class="faq-q">${f.q}<span class="mi" aria-hidden="true">add</span></summary>
    <div class="faq-a">${f.a}</div>
  </details>`).join('');
  return `<section class="faq"><div class="faq-inner">
    <div class="faq-head fade-up"><span class="label">Your Questions, Answered</span><h2 class="sec-title">Frequently Asked <em>Questions</em></h2></div>
    <div class="faq-list fade-up">${items}</div>
  </div></section>`;
}

function secCta(cfg) {
  const c = cfg.cta || {};
  const primary = c.primary || { label: 'Take the Scent Quiz', href: '#', onclick: 'openAI()' };
  const secondary = c.secondary || { label: 'Browse Best Sellers', href: 'collection.html?c=best-sellers' };
  const pClick = primary.onclick ? `onclick="${primary.onclick}"` : '';
  return `<section class="section"><div class="container"><div class="cta-band">
    <span class="label" style="color:var(--gold)">${c.label || 'Ready When You Are'}</span>
    <h2 class="sec-title">${c.title || 'Find a Scent That <em>Feels Like You</em>'}</h2>
    <p class="sec-sub">${c.sub || 'Take our 30-second Find My Scent quiz or talk to our AI concierge — 100% authentic, delivered across the UAE.'}</p>
    <div class="cta-actions">
      <a class="btn-g" href="${primary.href}" ${pClick}><span class="mi" aria-hidden="true">auto_awesome</span>${primary.label}</a>
      <a class="btn-o" href="${secondary.href}">${secondary.label}</a>
    </div>
  </div></div></section>`;
}

function secHowitworks(cfg) {
  if (!cfg.how) return '';
  const steps = cfg.how.steps.map(s => `<div class="how-step fade-up"><span class="mi" aria-hidden="true">${s.ic}</span><h3>${s.title}</h3><p>${s.text}</p></div>`).join('');
  return `<section class="section alt"><div class="container">
    <div class="sec-head center"><span class="label">${cfg.how.label || 'How It Works'}</span><h2 class="sec-title">${cfg.how.title}</h2>${cfg.how.sub ? `<p class="sec-sub">${cfg.how.sub}</p>` : ''}</div>
    <div class="how-grid">${steps}</div>
  </div></section>`;
}

function secPricing(cfg) {
  if (!cfg.pricing) return '';
  const cards = cfg.pricing.tiers.map(t => `<div class="price-card${t.featured ? ' featured' : ''}">
    <h3>${t.name}</h3><div class="price-tag">${t.price}<small>${t.unit || ''}</small></div>
    <p class="pc-desc">${t.desc}</p>
    <ul class="price-list">${t.features.map(f => `<li><span class="mi" aria-hidden="true">check</span>${f}</li>`).join('')}</ul>
    <a class="${t.featured ? 'btn-g' : 'btn-ol'}" href="${t.href || '#grid'}" style="justify-content:center">${t.cta || 'Shop Now'}</a>
  </div>`).join('');
  return `<section class="section"><div class="container">
    <div class="sec-head center"><span class="label">${cfg.pricing.label || 'Value Sets'}</span><h2 class="sec-title">${cfg.pricing.title}</h2>${cfg.pricing.sub ? `<p class="sec-sub">${cfg.pricing.sub}</p>` : ''}</div>
    <div class="pricing-grid">${cards}</div>
  </div></section>`;
}

function secBenefits(cfg) {
  if (!cfg.benefits) return '';
  const items = cfg.benefits.items.map((b, i) => `<div class="benefit-item fade-up"><span class="benefit-num">${String(i + 1).padStart(2, '0')}</span><div><h3>${b.title}</h3><p>${b.text}</p></div></div>`).join('');
  return `<section class="section${cfg.benefits.alt ? ' alt' : ''}"><div class="container-narrow">
    <div class="sec-head center"><span class="label">${cfg.benefits.label || 'Why Choose It'}</span><h2 class="sec-title">${cfg.benefits.title}</h2></div>
    <div class="benefit-grid">${items}</div>
  </div></section>`;
}

function secGallery(cfg) {
  if (!cfg.gallery) return '';
  const figs = cfg.gallery.imgs.map((g, i) => `<figure class="${g.cls || ''}"><img src="${g.src}" alt="${g.cap || 'Lifestyle'}" loading="lazy"/>${g.cap ? `<figcaption class="gallery-cap">${g.cap}</figcaption>` : ''}</figure>`).join('');
  return `<section class="section alt"><div class="container">
    <div class="sec-head center"><span class="label">${cfg.gallery.label || 'In Real Life'}</span><h2 class="sec-title">${cfg.gallery.title || 'See It <em>Worn</em>'}</h2></div>
    <div class="gallery-grid">${figs}</div>
  </div></section>`;
}

function secHero2(cfg) {
  if (!cfg.hero2) return '';
  const h = cfg.hero2;
  return `<section class="page-hero split"><div class="container">
    <div>
      <span class="ph-eyebrow">${h.eyebrow || 'Featured'}</span>
      <h2 class="ph-title" style="font-size:clamp(2rem,4vw,3rem)">${h.title}</h2>
      <p class="ph-sub">${h.sub}</p>
      <div class="ph-meta" style="margin-top:28px"><a class="btn-g" href="${h.href || '#grid'}">${h.cta || 'Shop Now'}</a></div>
    </div>
    <figure class="ph-figure"><img src="${h.img}" alt="${h.title}"/></figure>
  </div></section>`;
}

function secStory(cfg) {
  if (!cfg.storyBlock) return '';
  const s = cfg.storyBlock;
  return `<section class="section"><div class="about-split container">
    <figure class="about-figure"><img src="${s.img}" alt="${s.title}"/></figure>
    <div class="about-body">
      <span class="label">${s.label || 'Our Heritage'}</span>
      <h2 class="sec-title" style="margin-bottom:6px">${s.title}</h2>
      ${s.paras.map(p => `<p>${p}</p>`).join('')}
    </div>
  </div></section>`;
}

function secCombo(cfg) {
  if (!cfg.combo) return '';
  return comboHTML(cfg.combo);
}

/* ── Combo / bundle builder ──────────────────────────────────────── */
function comboHTML(combo) {
  const brands = combo.brands || ['Lattafa', 'Armaf', 'Swiss Arabian', 'Al Haramain'];
  const brandBtns = brands.map((b, i) => `<button class="combo-brand${i === 0 ? ' active' : ''}" onclick="comboBrand(this,'${b}')">${b}</button>`).join('');
  return `<section class="section"><div class="container"><div class="combo">
    <div class="combo-head">
      <span class="label" style="color:var(--gold-lt)">Build a Set · Save More</span>
      <h2 class="sec-title">Create Your <em>Brand Combo</em></h2>
      <p class="sec-sub" style="color:rgba(255,255,255,.6);margin:10px auto 0">Pick any 3 fragrances from a single house and save 15% — the perfect curated gift, or your own signature wardrobe.</p>
    </div>
    <div class="combo-brandbar">${brandBtns}</div>
    <div class="combo-grid" id="comboGrid"></div>
    <div class="combo-bar">
      <div>
        <div class="combo-summary"><span id="comboCount">0 of 3 selected</span> · <b id="comboTotal">AED 0</b><span class="combo-save" id="comboSave"></span></div>
        <div class="combo-hint">Select 3 to unlock the 15% combo discount.</div>
      </div>
      <button class="btn-g" id="comboAdd" onclick="comboAddToCart()" disabled>Add Combo to Cart</button>
    </div>
  </div></div></section>`;
}
let COMBO = { brand: 'Lattafa', picks: [] };
function comboPool(brand) {
  // Build a 4-item pool for the brand from catalogue, padding with brand-styled variants
  let pool = products.filter(p => p.brand === brand);
  const extra = products.filter(p => p.brand !== brand);
  let i = 0;
  while (pool.length < 4) { const e = extra[i++ % extra.length]; pool.push({ ...e, brand, name: e.name.replace(/^\w+\s/, '') }); }
  return pool.slice(0, 4);
}
function renderComboGrid() {
  const grid = el('comboGrid'); if (!grid) return;
  const pool = comboPool(COMBO.brand);
  grid.innerHTML = pool.map((p, i) => `<div class="combo-pick${COMBO.picks.includes(i) ? ' selected' : ''}" onclick="comboToggle(${i})" data-price="${p.price}">
    <span class="cp-check"><span class="mi" aria-hidden="true">check</span></span>
    <img src="${p.img}" alt="${esc(p.name)}"/>
    <div class="cp-name">${esc(p.name)}</div>
    <div class="cp-price">${money(p.price)}</div>
  </div>`).join('');
  updateCombo(pool);
}
function comboBrand(btn, brand) {
  document.querySelectorAll('.combo-brand').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  COMBO.brand = brand; COMBO.picks = [];
  renderComboGrid();
}
function comboToggle(i) {
  const idx = COMBO.picks.indexOf(i);
  if (idx > -1) COMBO.picks.splice(idx, 1);
  else { if (COMBO.picks.length >= 3) COMBO.picks.shift(); COMBO.picks.push(i); }
  renderComboGrid();
}
function updateCombo(pool) {
  const sel = COMBO.picks.map(i => pool[i]);
  const raw = sel.reduce((s, p) => s + p.price, 0);
  const three = COMBO.picks.length === 3;
  const total = three ? Math.round(raw * 0.85) : raw;
  const cnt = el('comboCount'); if (cnt) cnt.textContent = `${COMBO.picks.length} of 3 selected`;
  const tot = el('comboTotal'); if (tot) tot.textContent = money(total);
  const save = el('comboSave'); if (save) save.textContent = three ? `You save ${money(raw - total)} (15%)` : '';
  const add = el('comboAdd'); if (add) add.disabled = !three;
}
function comboAddToCart() {
  if (COMBO.picks.length !== 3) return;
  addToCart(`${COMBO.brand} Combo Set (3 fragrances, 15% off)`, 3);
}

/* ── Product card w/ filter data attributes ──────────────────────── */
function collCardHTML(p) {
  return `<div class="prod-card fade-up" onclick="location.href='${R('product.html')}'" data-fam="${p.family}" data-brand="${esc(p.brand)}" data-gender="${p.gender}" data-price="${p.price}" data-rating="${p.rating}">
    <div class="prod-img-wrap">
      <img class="prod-img" src="${p.img}" alt="${esc(p.name)}" loading="lazy"/>
      <div class="prod-badge ${p.badgeClass}">${p.badge}</div>
      <div class="prod-actions">
        <button class="pa-btn" title="Wishlist" onclick="event.stopPropagation();toast('♡ Saved to wishlist')"><span class="mi" aria-hidden="true">favorite</span></button>
        <button class="pa-btn quick-add" onclick="event.stopPropagation();addToCart('${esc(p.name).replace(/'/g, "\\'")}')"><span class="mi" aria-hidden="true">shopping_bag</span>Quick Add</button>
      </div>
    </div>
    <div class="prod-info">
      <div class="prod-brand">${esc(p.brand)}</div>
      <div class="prod-name">${esc(p.name)}</div>
      <div class="prod-rating"><div class="stars">${starsHTML(p.rating)}</div><span>(${p.reviews.toLocaleString()})</span></div>
      <div class="prod-price"><span class="price-now">${money(p.price)}</span><span class="price-was">${money(p.was)}</span><span class="price-save">Save ${savePct(p.price, p.was)}%</span></div>
    </div>
  </div>`;
}

function fillCollectionGrid(cfg) {
  const grid = el('collGrid'); if (!grid) return;
  if (cfg.gridKind === 'kits') {
    grid.innerHTML = discoveryKits.concat(discoveryKits.slice(0, 4)).map(kitCardHTML).join('');
  } else {
    grid.innerHTML = cfg._products.map(collCardHTML).join('');
  }
  observeFadeUps();
}

/* Delivery-cutoff band — every occasion page carries explicit delivery messaging (strategy) */
function secDelivery() {
  return `<section class="section-sm"><div class="container"><div class="trust-band">
    <div class="tb-item"><span class="mi" aria-hidden="true">bolt</span><div><strong>Order by 2 PM</strong><span>Same-day dispatch in Dubai</span></div></div>
    <div class="tb-item"><span class="mi" aria-hidden="true">local_shipping</span><div><strong>Next-Day UAE</strong><span>Free over AED 150</span></div></div>
    <div class="tb-item"><span class="mi" aria-hidden="true">card_giftcard</span><div><strong>Gift Wrapping</strong><span>Premium, ready to give</span></div></div>
    <div class="tb-item"><span class="mi" aria-hidden="true">payments</span><div><strong>Cash on Delivery</strong><span>Pay when it arrives</span></div></div>
  </div></div></section>`;
}

/* ── Faceted filter / sort behaviour ─────────────────────────────── */
function initFilterBar(cfg) {
  const grid = el('collGrid'); if (!grid) return;
  const sel = { fam: new Set(), brand: new Set(), gender: new Set(), price: new Set() };
  const inRange = (price, ranges) => [...ranges].some(r => {
    const [lo, hi] = r.split('-').map(Number); return price >= lo && price < hi;
  });
  const apply = () => {
    let shown = 0;
    [...grid.children].forEach(card => {
      const ok = (!sel.fam.size || sel.fam.has(card.dataset.fam))
        && (!sel.brand.size || sel.brand.has(card.dataset.brand))
        && (!sel.gender.size || sel.gender.has(card.dataset.gender))
        && (!sel.price.size || inRange(+card.dataset.price, sel.price));
      card.style.display = ok ? '' : 'none';
      if (ok) shown++;
    });
    const c = el('fbCount'); if (c) c.textContent = shown;
    const empty = el('sfEmpty'); if (empty) empty.style.display = shown ? 'none' : '';
  };

  // Checkbox facets
  document.querySelectorAll('.shop-filters input[type="checkbox"][data-facet]').forEach(cb => {
    cb.addEventListener('change', () => {
      const set = sel[cb.dataset.facet]; if (!set) return;
      cb.checked ? set.add(cb.value) : set.delete(cb.value);
      apply();
    });
  });

  // Brand search — filter the visible checkbox rows
  document.querySelectorAll('.shop-filters input[data-search]').forEach(inp => {
    inp.addEventListener('input', () => {
      const q = inp.value.trim().toLowerCase();
      const body = inp.closest('.sf-gbody');
      body.querySelectorAll('.sf-opt').forEach(opt => {
        const hit = opt.querySelector('.sf-label').textContent.toLowerCase().includes(q);
        opt.classList.toggle('sf-hidden', q ? !hit : opt.classList.contains('sf-was-hidden'));
      });
      const more = body.querySelector('.sf-more'); if (more) more.style.display = q ? 'none' : '';
    });
  });
  // Remember which rows were hidden by the "+more" limit so search can restore them
  document.querySelectorAll('.shop-filters .sf-opt.sf-hidden').forEach(o => o.classList.add('sf-was-hidden'));

  // "+N more" — reveal the rest
  document.querySelectorAll('.shop-filters [data-more]').forEach(btn => {
    btn.addEventListener('click', () => {
      btn.closest('.sf-gbody').querySelectorAll('.sf-opt.sf-hidden').forEach(o => {
        o.classList.remove('sf-hidden'); o.classList.remove('sf-was-hidden');
      });
      btn.remove();
    });
  });

  // Clear all
  const clear = el('sfClear');
  if (clear) clear.addEventListener('click', () => {
    Object.values(sel).forEach(s => s.clear());
    document.querySelectorAll('.shop-filters input[type="checkbox"]').forEach(cb => cb.checked = false);
    apply();
  });

  // Sort
  const s = el('fbSort');
  if (s) s.addEventListener('change', () => {
    const cards = [...grid.children], val = s.value;
    cards.sort((a, b) => {
      if (val === 'low') return a.dataset.price - b.dataset.price;
      if (val === 'high') return b.dataset.price - a.dataset.price;
      if (val === 'rating') return b.dataset.rating - a.dataset.rating;
      return 0;
    });
    cards.forEach(c => grid.appendChild(c));
  });

  // Mobile drawer
  const filters = el('shopFilters'), overlay = el('sfOverlay');
  const open = () => { filters && filters.classList.add('open'); overlay && overlay.classList.add('show'); document.body.style.overflow = 'hidden'; };
  const close = () => { filters && filters.classList.remove('open'); overlay && overlay.classList.remove('show'); document.body.style.overflow = ''; };
  const t = el('fbToggle'); if (t) t.addEventListener('click', open);
  const x = el('sfClose'); if (x) x.addEventListener('click', close);
  if (overlay) overlay.addEventListener('click', close);
}

/* ── Section dispatch ────────────────────────────────────────────── */
const SECTIONS = {
  header: secHeader, trust: secTrust, usps: secUsps, filter: secFilter, grid: secGrid,
  crosslinks: secCrosslinks, findscent: secFindscent, reviews: secReviews, testimonials: secReviews,
  faq: secFaq, cta: secCta, howitworks: secHowitworks, pricing: secPricing, benefits: secBenefits,
  gallery: secGallery, hero2: secHero2, story: secStory, combo: secCombo, delivery: secDelivery,
};

function buildProducts(cfg) {
  let list = products.slice();
  if (cfg.filterFam) list = list.filter(p => p.family === cfg.filterFam).concat(list.filter(p => p.family !== cfg.filterFam));
  if (cfg.filterGender) list = list.filter(p => p.gender === cfg.filterGender).concat(list.filter(p => p.gender !== cfg.filterGender));
  if (cfg.filterBrand) list = list.filter(p => p.brand === cfg.filterBrand).concat(list.filter(p => p.brand !== cfg.filterBrand));
  return list.slice(0, cfg.limit || 12);
}

function renderCollection() {
  const slug = qs('c') || 'all';
  let cfg = COLLECTIONS[slug] || COLLECTIONS['all'];
  // Dynamic brand / family collections via query params
  if (slug === 'brand' && qs('brand')) { cfg = brandCollection(qs('brand')); }
  if (slug === 'scent-family' && qs('family')) { cfg = familyCollection(qs('family')); }
  cfg._products = buildProducts(cfg);
  document.title = (cfg.titlePlain || 'Collection') + ' — The Fragrance Secrets';
  const active = el('hdr'); // header already mounted by app.js
  const order = cfg.sections || ['header', 'filter', 'grid', 'crosslinks', 'findscent', 'faq', 'cta'];
  const root = document.querySelector('[data-collection]');
  root.innerHTML = order.map(name => (SECTIONS[name] ? SECTIONS[name](cfg) : '')).join('');
  fillCollectionGrid(cfg);
  if (document.querySelector('.quiz-container-wrap')) renderQuiz();
  if (cfg.combo || document.getElementById('comboGrid')) renderComboGrid();
  initFilterBar(cfg);
  observeFadeUps();
}

/* Dynamic brand collection generator */
function brandCollection(brand) {
  return {
    titlePlain: brand + ' Perfumes',
    eyebrow: 'Fragrance House',
    title: `${brand} <em>Perfumes</em>`,
    story: `Discover the complete ${brand} collection at The Fragrance Secrets — 100% authentic, verified-sourced, and delivered across the UAE. From signature bestsellers to rare finds, every bottle is genuine sealed stock.`,
    heroImg: IMG.oud,
    breadcrumb: [{ label: 'Home', href: 'index.html' }, { label: 'Brands', href: 'brand-index.html' }, { label: brand }],
    meta: [{ ic: 'verified', t: 'Authorised Sourcing' }, { ic: 'inventory_2', t: 'Sealed Stock' }],
    count: 46, filterBrand: brand,
    sections: ['header', 'trust', 'filter', 'grid', 'combo', 'crosslinks'],
    combo: { brands: [brand, 'Lattafa', 'Armaf', 'Swiss Arabian'] },
    xHead: 'Related Houses', xTitle: 'Explore <em>Similar Brands</em>',
    crosslinks: brands.slice(0, 8).filter(b => b !== brand).slice(0, 6).map(b => ({ label: b, href: 'collection.html?c=brand&brand=' + encodeURIComponent(b) })),
  };
}
function familyCollection(family) {
  return {
    titlePlain: family, eyebrow: 'Scent Family',
    title: `${family} <em>Fragrances</em>`,
    sub: `Everything in the ${family} family — curated so you can shop by the notes you love most.`,
    breadcrumb: [{ label: 'Home', href: 'index.html' }, { label: 'Scent Families', href: 'category-collection.html' }, { label: family }],
    count: 38, filterFam: family,
    sections: ['header', 'filter', 'grid', 'crosslinks'],
    crosslinks: FAM.filter(f => f !== family).map(f => ({ label: f, href: 'collection.html?c=scent-family&family=' + encodeURIComponent(f) })).concat([{ label: 'All Products', href: 'collection.html?c=all' }]),
  };
}

/* ═══════════════════════════════════════════════════════════════════
   COLLECTIONS CONFIG — one entry per sitemap PLP page
═══════════════════════════════════════════════════════════════════ */
const HOME_CRUMB = { label: 'Home', href: 'index.html' };
const COLLECTIONS = {

  'all': {
    titlePlain: 'Shop All Products', eyebrow: 'The Full Catalogue',
    title: 'Shop <em>All Perfumes</em>',
    sub: 'Browse every fragrance in one place — 218+ authentic perfumes, oils and attars from 47+ houses, filtered exactly how you like.',
    breadcrumb: [HOME_CRUMB, { label: 'Shop All' }],
    meta: [{ ic: 'inventory_2', t: '218+ Fragrances' }, { ic: 'storefront', t: '47+ Brands' }],
    count: 218,
    sections: ['header', 'filter', 'grid', 'findscent', 'crosslinks', 'faq', 'cta'],
  },

  'best-sellers': {
    titlePlain: 'Best Sellers', eyebrow: 'Most Loved',
    title: 'The <em>Best Sellers</em>',
    sub: 'The fragrances our UAE customers reorder most — ranked by real sales, reviews and repeat purchases.',
    breadcrumb: [HOME_CRUMB, { label: 'Best Sellers' }],
    meta: [{ ic: 'trending_up', t: 'Ranked by Sales' }, { ic: 'star', t: '4.8 Avg Rating' }],
    count: 60,
    sections: ['header', 'filter', 'grid', 'findscent', 'faq', 'cta'],
  },

  'new-arrivals': {
    titlePlain: 'New Arrivals', eyebrow: 'Just Landed',
    title: 'New <em>Arrivals</em>',
    sub: 'Fresh drops, exclusive launches and editor\'s picks — be the first to wear the season\'s most talked-about scents.',
    breadcrumb: [HOME_CRUMB, { label: 'New Arrivals' }],
    meta: [{ ic: 'fiber_new', t: 'Weekly Drops' }, { ic: 'auto_awesome', t: 'Editor\'s Picks' }],
    count: 42,
    uspsHead: { label: 'What\'s New', title: 'Trending <em>Right Now</em>' },
    usps: [
      { ic: 'local_fire_department', title: 'Trending Launches', text: 'The new releases racking up the fastest reorders and the most WhatsApp questions this month.' },
      { ic: 'lock', title: 'Exclusive Drops', text: 'Limited allocations and house exclusives you won\'t find on the marketplace sites.' },
      { ic: 'auto_awesome', title: 'Editor\'s Picks', text: 'Hand-selected by our fragrance team for standout quality, longevity and value.' },
    ],
    sections: ['header', 'usps', 'filter', 'grid', 'findscent', 'reviews', 'faq', 'cta'],
    cta: { label: 'Never Miss a Drop', title: 'Get Early Access to <em>New Arrivals</em>', sub: 'Subscribe for first dibs on limited editions and exclusive launches — plus 10% off your first order.', primary: { label: 'Subscribe for Updates', href: '#', onclick: 'openReferral()' } },
  },

  'mens': {
    titlePlain: "Men's Perfumes", eyebrow: 'For Him',
    title: "Men's <em>Perfumes</em>",
    sub: 'Long-lasting designer and niche fragrances built for confidence — from fresh daily signatures to bold evening statements.',
    breadcrumb: [HOME_CRUMB, { label: 'Categories', href: 'category-collection.html' }, { label: "Men's Perfumes" }],
    meta: [{ ic: 'schedule', t: '8–12hr Longevity' }, { ic: 'workspace_premium', t: 'Designer & Niche' }],
    count: 84, filterGender: 'Men',
    how: {
      label: 'Choosing His Scent', title: 'How to Pick a Men\'s Fragrance',
      sub: 'Match the scent to the moment in four simple steps.',
      steps: [
        { ic: 'wb_sunny', title: 'By Season', text: 'Fresh, citrus and aquatic for heat; woody, spicy and oud for cooler evenings.' },
        { ic: 'event', title: 'By Occasion', text: 'Clean and subtle for the office; bold projection for nights out and events.' },
        { ic: 'air', title: 'By Strength', text: 'EDT for a soft trail, EDP for all-day presence, Extrait for maximum depth.' },
        { ic: 'favorite', title: 'By Signature', text: 'Not sure? Take the Find My Scent quiz and we\'ll shortlist your matches.' },
      ],
    },
    uspsHead: { label: 'The Men\'s Edit', title: 'Built to <em>Last</em>' },
    usps: [
      { ic: 'schedule', title: 'Long-Lasting Scents', text: 'Curated for UAE heat — profiles that project for 8–12 hours without fading by noon.' },
      { ic: 'workspace_premium', title: 'Designer & Niche', text: 'From accessible everyday icons to rare niche houses, all 100% authentic.' },
      { ic: 'star', title: 'Exclusive Picks', text: 'Community-favourite bestsellers and our own-brand signatures at smart prices.' },
    ],
    pricing: {
      label: 'Value Sets', title: 'Men\'s <em>Value Tiers</em>',
      sub: 'Optional bundles that make gifting — or building a wardrobe — effortless.',
      tiers: [
        { name: 'Everyday', price: 'AED 89+', desc: 'Reliable daily signatures with great longevity.', features: ['Fresh & clean profiles', 'Office-friendly projection', '50–100ml bottles'], cta: 'Shop Everyday' },
        { name: 'Signature', price: 'AED 149+', desc: 'Standout scents that become "your" smell.', featured: true, features: ['Bold designer & niche', 'All-day performance', 'Gift-ready packaging'], cta: 'Shop Signature' },
        { name: 'Collector', price: 'AED 260+', desc: 'Rare niche and luxury statement pieces.', features: ['Niche & extrait strength', 'Exceptional sillage', 'Limited allocations'], cta: 'Shop Collector' },
      ],
    },
    // Shop-first flow to match Women's: products up top, supporting content below.
    sections: ['header', 'filter', 'grid', 'usps', 'howitworks', 'pricing', 'crosslinks', 'findscent', 'faq', 'cta'],
    xHead: 'Discover More', xTitle: 'Shop by <em>Mood & Moment</em>',
    crosslinks: [
      { label: 'Date Night', href: 'collection.html?c=date-night' },
      { label: 'Office & Everyday', href: 'collection.html?c=everyday-signature' },
      { label: 'Oud & Woody Family', href: 'collection.html?c=scent-family&family=Oud%20%26%20Woody' },
      { label: 'Best Sellers', href: 'collection.html?c=best-sellers' },
      { label: 'Luxury Perfumes', href: 'collection.html?c=luxury' },
      { label: 'Gift Sets for Him', href: 'gift-sets.html' },
    ],
    cta: { title: 'Find <em>His</em> Signature Scent', sub: 'Take the Find My Scent quiz, or explore gift-ready sets for him.', secondary: { label: 'Shop Gift Sets', href: 'gift-sets.html' } },
    faqs: [
      { q: 'What are the longest-lasting men\'s perfumes?', a: 'Oud, amber and woody EDPs and extraits perform best in UAE heat. Look for our 8–12 hour longevity tags, or ask the AI concierge for beast-mode recommendations.' },
      ...FAQ_TRUST.slice(0, 3),
    ],
  },

  'womens': {
    titlePlain: "Women's Perfumes", eyebrow: 'For Her',
    title: "Women's <em>Perfumes</em>",
    sub: 'From luminous florals to warm gourmands and elegant orientals — discover a scent as memorable as you are.',
    breadcrumb: [HOME_CRUMB, { label: 'Categories', href: 'category-collection.html' }, { label: "Women's Perfumes" }],
    meta: [{ ic: 'local_florist', t: 'Floral to Oriental' }, { ic: 'star', t: 'Top-Rated' }],
    count: 72, filterGender: 'Women',
    sections: ['header', 'filter', 'grid', 'crosslinks', 'findscent'],
    xHead: 'Discover More', xTitle: 'Shop by <em>Mood & Moment</em>',
    crosslinks: [
      { label: 'Date Night Perfumes', href: 'collection.html?c=date-night' },
      { label: 'Everyday Signature', href: 'collection.html?c=everyday-signature' },
      { label: 'Floral & Rose Family', href: 'collection.html?c=scent-family&family=Floral%20%26%20Rose' },
      { label: 'Best Sellers', href: 'collection.html?c=best-sellers' },
      { label: 'Luxury Perfumes', href: 'collection.html?c=luxury' },
      { label: 'Gift Sets', href: 'gift-sets.html' },
    ],
  },

  'kids': {
    titlePlain: 'Kids Perfumes', eyebrow: 'Gentle & Playful',
    title: 'Kids <em>Perfumes</em>',
    sub: 'Soft, skin-friendly and alcohol-light fragrances made for little ones — playful scents parents can trust.',
    breadcrumb: [HOME_CRUMB, { label: 'Categories', href: 'category-collection.html' }, { label: 'Kids Perfumes' }],
    meta: [{ ic: 'child_care', t: 'Age-Appropriate' }, { ic: 'spa', t: 'Gentle Formulas' }],
    count: 16,
    uspsHead: { label: 'Made for Little Ones', title: 'Safe, Gentle &amp; <em>Fun</em>' },
    usps: [
      { ic: 'verified_user', title: 'Skin-Friendly', text: 'Gentle, low-alcohol and dermatologically considerate formulations designed for delicate skin.' },
      { ic: 'spa', title: 'Soft & Subtle', text: 'Light, playful scents that are never overpowering — perfect for school, play and special days.' },
      { ic: 'child_care', title: 'Age-Appropriate', text: 'Clear guidance on suitable ages, with parent-approved picks and easy returns.' },
    ],
    sections: ['header', 'usps', 'filter', 'grid', 'trust', 'crosslinks', 'reviews', 'faq'],
    xHead: 'For the Whole Family', xTitle: 'Explore <em>Family Favourites</em>',
    crosslinks: [
      { label: 'Kids Gift Sets', href: 'gift-sets.html' },
      { label: 'Shop by Occasion', href: 'shop-by-lifestyle.html' },
      { label: 'Women\'s Perfumes', href: 'collection.html?c=womens' },
      { label: 'Men\'s Perfumes', href: 'collection.html?c=mens' },
    ],
    faqs: [
      { q: 'Are kids perfumes safe for sensitive skin?', a: 'Our kids range is chosen for gentle, low-alcohol formulations. As with any fragrance, we recommend a small patch test and applying to clothing rather than directly to skin for very young children.' },
      { q: 'What age are these fragrances suitable for?', a: 'Each product lists a recommended age range. Most are designed for ages 3+ as light body mists. Message our team on WhatsApp for a specific recommendation.' },
      ...FAQ_TRUST.slice(3),
    ],
  },

  'unisex': {
    titlePlain: 'Unisex Perfumes', eyebrow: 'For Everyone',
    title: 'Unisex <em>Perfumes</em>',
    sub: 'Boundary-free fragrances designed to be shared — versatile, modern scents that suit any wearer and any day.',
    breadcrumb: [HOME_CRUMB, { label: 'Categories', href: 'category-collection.html' }, { label: 'Unisex Perfumes' }],
    meta: [{ ic: 'all_inclusive', t: 'Gender-Free' }, { ic: 'auto_awesome', t: 'Versatile' }],
    count: 46, filterGender: 'Unisex',
    uspsHead: { label: 'Why Unisex', title: 'One Scent, <em>No Rules</em>' },
    usps: [
      { ic: 'all_inclusive', title: 'Made to Share', text: 'Balanced compositions that flatter every wearer — perfect for couples and gifting.' },
      { ic: 'wb_twilight', title: 'Day to Night', text: 'Versatile profiles that transition effortlessly from desk to dinner.' },
      { ic: 'workspace_premium', title: 'Modern & Niche', text: 'Contemporary and niche-inspired blends that feel distinctly you.' },
    ],
    sections: ['header', 'usps', 'filter', 'grid', 'crosslinks', 'findscent'],
    crosslinks: [
      { label: 'Oud & Woody', href: 'collection.html?c=scent-family&family=Oud%20%26%20Woody' },
      { label: 'Fresh & Citrus', href: 'collection.html?c=scent-family&family=Fresh%20%26%20Citrus' },
      { label: 'Best Sellers', href: 'collection.html?c=best-sellers' },
      { label: 'Luxury Perfumes', href: 'collection.html?c=luxury' },
    ],
  },

  'luxury': {
    titlePlain: 'Luxury Perfumes', eyebrow: 'The Finest',
    title: 'Luxury <em>Perfumes</em>',
    sub: 'Rare ingredients, artisanal craftsmanship and exclusive house collaborations — the pinnacle of our catalogue.',
    breadcrumb: [HOME_CRUMB, { label: 'Categories', href: 'category-collection.html' }, { label: 'Luxury Perfumes' }],
    meta: [{ ic: 'diamond', t: 'Rare Ingredients' }, { ic: 'workspace_premium', t: 'Niche Houses' }],
    count: 54,
    uspsHead: { label: 'What Makes It Luxury', title: 'Craft You Can <em>Smell</em>' },
    usps: [
      { ic: 'diamond', title: 'Rare Ingredients', text: 'Precious oud, saffron, orris and natural absolutes sourced for depth and character.' },
      { ic: 'handyman', title: 'Artisanal Craft', text: 'Small-batch compositions from master perfumers, aged for richness and balance.' },
      { ic: 'workspace_premium', title: 'Exclusive Houses', text: 'Niche and prestige collaborations you won\'t find on the mainstream marketplaces.' },
    ],
    sections: ['header', 'usps', 'filter', 'grid', 'crosslinks', 'trust'],
    xHead: 'Continue Exploring', xTitle: 'More <em>Elevated</em> Choices',
    crosslinks: [
      { label: 'Luxury Recommendations', href: 'luxury-recommendations.html' },
      { label: 'Shop by Brand', href: 'brand-index.html' },
      { label: 'Own-Brand Collection', href: 'collection.html?c=own-brand' },
      { label: 'Gift Sets & Kits', href: 'gift-sets.html' },
    ],
  },

  'miracle-plant': {
    titlePlain: 'Miracle Plant', eyebrow: 'Botanical Rarity',
    title: 'The <em>Miracle Plant</em> Collection',
    story: 'Rooted in nature and centuries of tradition, the Miracle Plant collection captures rare botanical extracts prized for their depth, warmth and natural beauty — a distinctive range unlike anything on the marketplace.',
    heroImg: IMG.rose,
    breadcrumb: [HOME_CRUMB, { label: 'Categories', href: 'category-collection.html' }, { label: 'Miracle Plant' }],
    meta: [{ ic: 'eco', t: 'Natural Origins' }, { ic: 'verified', t: 'Authenticity Assured' }],
    count: 18,
    storyBlock: {
      label: 'Its Heritage', title: 'Nature, <em>Bottled</em>', img: IMG.gold,
      paras: [
        'The Miracle Plant has been revered across the region for generations — its botanical extract lends a warmth and natural sweetness that synthetics simply cannot replicate.',
        'Every fragrance in this range is built around responsibly sourced natural material, then blended and quality-checked to our own exacting standards before it reaches you.',
      ],
    },
    sections: ['header', 'story', 'grid', 'trust', 'testimonials', 'cta'],
    cta: { label: 'Discover the Range', title: 'Experience the <em>Miracle Plant</em>', sub: 'Learn more about its natural origins or shop the full collection — 100% authentic, delivered UAE-wide.' },
  },

  'perfume-oil': {
    titlePlain: 'Perfume Oil', eyebrow: 'Concentrated & Pure',
    title: 'Perfume <em>Oil</em>',
    sub: 'Alcohol-free, long-lasting and skin-kind — concentrated fragrance oils in the region\'s richest tradition. Mix any oil into a ready-to-wear spray, made to order.',
    breadcrumb: [HOME_CRUMB, { label: 'Categories', href: 'category-collection.html' }, { label: 'Perfume Oil' }],
    meta: [{ ic: 'water_drop', t: 'Alcohol-Free' }, { ic: 'science', t: 'Mix Into a Spray' }],
    count: 40, filterFam: 'Oud & Woody',
    uspsHead: { label: 'Why Oils', title: 'The Case for <em>Oil</em>' },
    usps: [
      { ic: 'block', title: 'Alcohol-Free', text: 'Gentle on skin and long-wearing — ideal for sensitive skin and modest, intimate sillage.' },
      { ic: 'schedule', title: 'Long-Lasting', text: 'A single dab lingers for hours; the concentrated format means a little goes a long way.' },
      { ic: 'science', title: 'Mix Into a Spray', text: 'Love an oil? Have us hand-blend it into a 50/100ml alcohol spray at your chosen strength.' },
    ],
    sections: ['header', 'usps', 'filter', 'grid', 'trust', 'crosslinks', 'testimonials', 'cta'],
    xHead: 'Explore More', xTitle: 'Other Ways to <em>Wear It</em>',
    crosslinks: [
      { label: 'Attar', href: 'collection.html?c=attar' },
      { label: 'Perfume Sprays', href: 'collection.html?c=all' },
      { label: 'Gift Sets', href: 'gift-sets.html' },
      { label: 'Arabic Perfumes', href: 'collection.html?c=arabic' },
    ],
    cta: { label: 'Try Before You Commit', title: 'Start With a <em>Sampler</em>', sub: 'Explore our discovery kits and gift sets — the easiest way to find your signature oil.', primary: { label: 'Shop Discovery Kits', href: 'gift-sets.html', onclick: '' } },
  },

  'attar': {
    titlePlain: 'Attar', eyebrow: 'Timeless Tradition',
    title: '<em>Attar</em> Collection',
    story: 'For centuries, attar — pure, alcohol-free fragrance oil distilled from flowers, wood and resin — has been the heart of Arabian perfumery. Each drop is an artisanal craft, worn close to the skin and treasured for its depth.',
    heroImg: IMG.oud,
    breadcrumb: [HOME_CRUMB, { label: 'Categories', href: 'category-collection.html' }, { label: 'Attar' }],
    meta: [{ ic: 'history_edu', t: 'Artisanal Craft' }, { ic: 'water_drop', t: 'Alcohol-Free' }],
    count: 34, filterFam: 'Spicy & Oriental',
    uspsHead: { label: 'The Attar Difference', title: 'Heritage in <em>Every Drop</em>' },
    usps: [
      { ic: 'block', title: 'Alcohol-Free', text: 'Traditionally distilled and alcohol-free — pure oil that melds beautifully with your skin.' },
      { ic: 'schedule', title: 'Long-Lasting', text: 'Deep, resinous and enduring — attar develops on the skin over many hours.' },
      { ic: 'flight', title: 'Travel-Friendly', text: 'Compact roll-ons and vials, spill-safe and perfectly carry-on sized.' },
    ],
    benefits: {
      label: 'Personal & Gifting', title: 'Why Choose <em>Attar</em>', alt: true,
      items: [
        { title: 'A More Intimate Trail', text: 'Attar sits close to the skin — a personal signature noticed only by those near you.' },
        { title: 'Rich, Natural Depth', text: 'Oud, rose, musk and amber shine in their purest, most concentrated form.' },
        { title: 'A Meaningful Gift', text: 'Presented in ornate bottles, attar is a treasured, timeless present for any occasion.' },
        { title: 'Layer & Personalise', text: 'Combine attars, or have us mix one into a spray, to craft a scent that is entirely yours.' },
      ],
    },
    pricing: {
      label: 'Attar Value Tiers', title: 'Find Your <em>Price Point</em>',
      tiers: [
        { name: 'Discovery', price: 'AED 39+', desc: '3ml roll-ons to explore the tradition.', features: ['Try before a full bottle', 'Travel-safe vials', 'Perfect first attar'], cta: 'Shop Discovery' },
        { name: 'Signature', price: 'AED 79+', desc: 'Full-size artisanal attars.', featured: true, features: ['6–12ml ornate bottles', 'Rich oud, rose & musk', 'Gift-ready presentation'], cta: 'Shop Signature' },
        { name: 'Heritage', price: 'AED 180+', desc: 'Rare, aged and premium distillations.', features: ['Precious aged oud', 'Collector bottles', 'Limited batches'], cta: 'Shop Heritage' },
      ],
    },
    sections: ['header', 'usps', 'benefits', 'pricing', 'filter', 'grid', 'crosslinks', 'testimonials', 'cta', 'faq'],
    xHead: 'Explore More', xTitle: 'You May Also <em>Enjoy</em>',
    crosslinks: [
      { label: 'Perfume Oil', href: 'collection.html?c=perfume-oil' },
      { label: 'Luxury Perfumes', href: 'collection.html?c=luxury' },
      { label: 'Unisex Perfumes', href: 'collection.html?c=unisex' },
      { label: 'Arabic Perfumes', href: 'collection.html?c=arabic' },
    ],
    cta: { label: 'New to Attar?', title: 'Try, Wear or <em>Gift</em> an Attar', sub: 'Start with a discovery roll-on, or let our concierge suggest your first attar.' },
    faqs: [
      { q: 'How do I apply attar?', a: 'Dab a small amount on pulse points — wrists, neck, behind the ears. A little goes a long way; the scent blooms and deepens over the hours.' },
      { q: 'How should I store attar?', a: 'Keep it away from direct sunlight and heat in its sealed bottle. Stored well, quality attar can last for years and often improves with age.' },
      { q: 'Is attar the same as perfume oil?', a: 'Both are alcohol-free oils. Attar traditionally refers to natural distillations (often oud, rose, musk), while perfume oils can also include modern blended compositions.' },
      ...FAQ_TRUST.slice(0, 2),
    ],
  },

  'arabic': {
    titlePlain: 'Arabic Perfumes', eyebrow: 'The Orient',
    title: 'Arabic <em>Perfumes</em>',
    sub: 'Opulent oud, warm amber, smoky incense and rich rose — the unmistakable, long-lasting signatures of Arabian perfumery.',
    breadcrumb: [HOME_CRUMB, { label: 'Categories', href: 'category-collection.html' }, { label: 'Arabic Perfumes' }],
    meta: [{ ic: 'local_fire_department', t: 'Oud & Amber' }, { ic: 'schedule', t: 'Long-Lasting' }],
    count: 88, filterFam: 'Spicy & Oriental',
    sections: ['header', 'filter', 'grid', 'crosslinks', 'faq', 'cta'],
    xHead: 'Related Collections', xTitle: 'Deepen the <em>Journey</em>',
    crosslinks: [
      { label: 'Oud Fragrances', href: 'collection.html?c=scent-family&family=Oud%20%26%20Woody' },
      { label: 'Attar', href: 'collection.html?c=attar' },
      { label: 'Unisex Arabic Scents', href: 'collection.html?c=unisex' },
      { label: 'Luxury Perfumes', href: 'collection.html?c=luxury' },
    ],
    faqs: [
      { q: 'What defines an Arabic perfume?', a: 'Arabic perfumery centres on rich, long-lasting notes — oud, amber, musk, saffron, rose and incense — often at high concentration for exceptional projection and longevity.' },
      { q: 'Why do Arabic perfumes last so long?', a: 'They typically use higher oil concentrations and heavier base notes (oud, amber, resins) that cling to skin and fabric, performing especially well in warm climates.' },
      ...FAQ_TRUST.slice(0, 3),
    ],
  },

  'inspired': {
    titlePlain: 'Inspired Perfumes', eyebrow: 'Smart Luxury',
    title: 'Inspired <em>Perfumes</em>',
    sub: 'The artistry of the world\'s most-loved fragrances, reimagined at a fraction of the price — labelled honestly as inspired-by, never as the original.',
    breadcrumb: [HOME_CRUMB, { label: 'Categories', href: 'category-collection.html' }, { label: 'Inspired Perfumes' }],
    meta: [{ ic: 'savings', t: 'Smart Prices' }, { ic: 'verified', t: 'Honestly Labelled' }],
    count: 64,
    uspsHead: { label: 'The Honest Approach', title: 'Great Scent, <em>Fair Price</em>' },
    usps: [
      { ic: 'palette', title: 'Faithful Artistry', text: 'Carefully composed to echo the character of iconic scents you already love.' },
      { ic: 'savings', title: 'A Fraction of the Cost', text: 'Enjoy designer-style sophistication without the designer price tag.' },
      { ic: 'verified', title: 'Always Transparent', text: 'We label inspired-by lines clearly as inspired — never claimed as the genuine original.' },
    ],
    sections: ['header', 'usps', 'filter', 'grid', 'trust', 'crosslinks'],
    crosslinks: [
      { label: 'Own-Brand Collection', href: 'collection.html?c=own-brand' },
      { label: 'Best Sellers', href: 'collection.html?c=best-sellers' },
      { label: 'Everyday Signature', href: 'collection.html?c=everyday-signature' },
      { label: 'Gift Sets', href: 'gift-sets.html' },
    ],
  },

  'own-brand': {
    titlePlain: 'Own-Brand Collection', eyebrow: 'Made By Us',
    title: 'Our <em>Own Brands</em>',
    story: 'Fragrance Secrets, Secret Scents and Paris Collection are our in-house lines — developed and manufactured to our own standards through certified UAE partners, and tuned for the way the region actually wears fragrance.',
    heroImg: IMG.bottles,
    breadcrumb: [HOME_CRUMB, { label: 'Brands', href: 'brand-index.html' }, { label: 'Own-Brand' }],
    meta: [{ ic: 'factory', t: 'Made in the UAE' }, { ic: 'workspace_premium', t: 'Our Standards' }],
    count: 32, filterBrand: 'Fragrance Secrets',
    sections: ['header', 'grid', 'trust', 'cta'],
    cta: { label: 'Authenticity, Always', title: 'Originals, <em>Never Fakes</em>', sub: 'Our own creations are exactly that — original compositions made to our standards, never counterfeits of anyone else\'s house.', primary: { label: 'Read Our Sourcing Promise', href: 'about.html', onclick: '' } },
  },

  /* ── Lifestyle sub-pages ──────────────────────────────────────── */
  'office-wear': {
    titlePlain: 'Office Wear Fragrances', eyebrow: 'Nine to Five',
    title: 'Office Wear <em>Fragrances</em>',
    sub: 'Clean, sophisticated and never intrusive — polished scents that earn compliments without overwhelming the meeting room.',
    breadcrumb: [HOME_CRUMB, { label: 'Shop by Lifestyle', href: 'shop-by-lifestyle.html' }, { label: 'Office Wear' }],
    meta: [{ ic: 'business_center', t: 'Professional' }, { ic: 'air', t: 'Subtle Projection' }],
    count: 38, filterFam: 'Fresh & Citrus',
    uspsHead: { label: 'The Office Edit', title: 'Confidence, <em>Not Clouds</em>' },
    usps: [
      { ic: 'air', title: 'Subtle & Clean', text: 'Fresh, soapy and citrus profiles that stay close and read as effortlessly put-together.' },
      { ic: 'schedule', title: 'All-Day Wear', text: 'Balanced longevity that lasts your workday without needing a top-up or overpowering colleagues.' },
      { ic: 'verified', title: 'Universally Liked', text: 'Crowd-pleasing, inoffensive signatures that suit any professional environment.' },
    ],
    gallery: {
      label: 'At Work', title: 'Dressed for the <em>Day</em>',
      imgs: [
        { src: 'assets/img/cat-men.jpg', cap: 'Desk to dinner', cls: 'wide' },
        { src: 'assets/img/cat-luxury.jpg', cap: 'Clean & crisp' },
        { src: 'assets/img/prod-club-de-nuit.jpg', cap: 'Boardroom ready' },
        { src: 'assets/img/kit-gift.jpg' },
      ],
    },
    pricing: {
      label: 'Office Bundles', title: 'Work <em>Sets</em>',
      tiers: [
        { name: 'Daily Fresh', price: 'AED 89', desc: 'A dependable clean signature for every weekday.', features: ['Citrus & aquatic', '50ml everyday size', 'Subtle projection'], cta: 'Shop Set' },
        { name: 'Desk-to-Dinner', price: 'AED 159', desc: 'One fresh, one warmer — cover the whole day.', featured: true, features: ['Two versatile scents', 'Day & evening pairing', 'Gift-ready box'], cta: 'Shop Set' },
        { name: 'Executive', price: 'AED 240', desc: 'Refined niche polish for leadership presence.', features: ['Sophisticated niche', 'Memorable but subtle', 'Premium packaging'], cta: 'Shop Set' },
      ],
    },
    sections: ['header', 'usps', 'pricing', 'grid', 'gallery', 'cta', 'faq'],
    cta: { label: 'Not Sure Where to Start', title: 'Sample the <em>Office Edit</em>', sub: 'Try a discovery set of workplace-friendly scents before committing to a full bottle.', primary: { label: 'Shop Sampler Sets', href: 'gift-sets.html', onclick: '' } },
    faqs: [
      { q: 'What makes a fragrance office-appropriate?', a: 'Moderate longevity with soft projection (sillage), and clean, universally-liked notes — fresh, citrus, light woods — so your scent stays a personal detail rather than filling the room.' },
      { q: 'How much should I apply for work?', a: 'One to two sprays on pulse points is plenty for an EDP. If in doubt, spray onto clothing for an even softer trail.' },
      ...FAQ_TRUST.slice(0, 2),
    ],
  },

  'date-night': {
    titlePlain: 'Date Night Perfumes', eyebrow: 'After Dark',
    title: 'Date Night <em>Perfumes</em>',
    sub: 'Warm, alluring and unforgettable — magnetic scents engineered to draw people closer and linger long after the evening ends.',
    breadcrumb: [HOME_CRUMB, { label: 'Shop by Lifestyle', href: 'shop-by-lifestyle.html' }, { label: 'Date Night' }],
    meta: [{ ic: 'favorite', t: 'Alluring' }, { ic: 'nightlife', t: 'Evening Ready' }],
    count: 44, filterFam: 'Sweet & Gourmand',
    hero2: {
      eyebrow: 'The Signature Move', title: 'Scents That <em>Get Noticed</em>',
      sub: 'Gourmand sweetness, warm amber and a whisper of oud — the notes proven to intrigue. Shop the edit our customers reach for on the nights that matter.',
      img: IMG.gold, cta: 'Shop Date Night Scents', href: '#grid',
    },
    uspsHead: { label: 'Why These Work', title: 'Built to <em>Captivate</em>' },
    usps: [
      { ic: 'schedule', title: 'Long-Lasting', text: 'Stays with you from dinner to the last goodbye — no fading at the crucial moment.' },
      { ic: 'favorite', title: 'Alluring Notes', text: 'Vanilla, amber, rose and oud — the warm, close-wearing notes that invite a second lean-in.' },
      { ic: 'trending_up', title: 'Top-Seller Picks', text: 'The compliment-magnets our community rates highest for romantic evenings.' },
    ],
    sections: ['header', 'hero2', 'usps', 'grid', 'faq', 'cta'],
    cta: { label: 'Find The One', title: 'Discover <em>Your</em> Date Night Scent', sub: 'Take the Find My Scent quiz for a personalised match, or explore related evening collections.', secondary: { label: 'Dinner & Evening Wear', href: 'collection.html?c=dinner-evening' } },
    faqs: [
      { q: 'What are the best notes for a date?', a: 'Warm, sweet and skin-close notes work best — vanilla, amber, tonka, rose and a touch of oud or musk. They create an intimate, inviting trail rather than a loud announcement.' },
      { q: 'Should date-night scents be strong?', a: 'Aim for moderate-to-strong longevity but controlled projection — you want them noticed up close, not from across the restaurant.' },
      ...FAQ_TRUST.slice(0, 2),
    ],
  },

  'party-clubbing': {
    titlePlain: 'Party & Clubbing Fragrances', eyebrow: 'Turn It Up',
    title: 'Party &amp; Clubbing <em>Fragrances</em>',
    sub: 'Bold, high-projection statement scents that cut through the crowd and last until the lights come up.',
    breadcrumb: [HOME_CRUMB, { label: 'Shop by Lifestyle', href: 'shop-by-lifestyle.html' }, { label: 'Party & Clubbing' }],
    meta: [{ ic: 'graphic_eq', t: 'Beast Mode' }, { ic: 'nightlife', t: 'High Projection' }],
    count: 40, filterFam: 'Sweet & Gourmand',
    uspsHead: { label: 'Made for the Night', title: 'Loud &amp; <em>Proud</em>' },
    usps: [
      { ic: 'graphic_eq', title: 'Massive Projection', text: 'Scent bombs designed to fill a room and leave a trail people follow.' },
      { ic: 'schedule', title: 'All-Night Longevity', text: 'Built to survive heat, dancing and hours out — still there at 2 AM.' },
      { ic: 'auto_awesome', title: 'Statement Notes', text: 'Sweet, boozy, spicy and bold — unforgettable signatures that own the moment.' },
    ],
    sections: ['header', 'usps', 'filter', 'grid', 'faq', 'cta'],
    cta: { title: 'Match the <em>Energy</em>', sub: 'Let the AI concierge pick your loudest, longest-lasting options.', secondary: { label: 'Party Gift Sets', href: 'gift-sets.html' } },
    faqs: [
      { q: 'Which fragrances project the most?', a: 'Sweet gourmands, boozy ambers and intense EDPs/extraits project hardest. Look for our "beast mode" tags or ask the concierge for maximum-projection picks.' },
      ...FAQ_TRUST.slice(0, 3),
    ],
  },

  'wedding-formal': {
    titlePlain: 'Wedding & Formal Event Perfumes', eyebrow: 'The Big Day',
    title: 'Wedding &amp; Formal <em>Perfumes</em>',
    sub: 'Elegant, refined and long-lasting fragrances worthy of the moments you\'ll remember forever.',
    breadcrumb: [HOME_CRUMB, { label: 'Shop by Lifestyle', href: 'shop-by-lifestyle.html' }, { label: 'Wedding & Formal' }],
    meta: [{ ic: 'celebration', t: 'Occasion-Ready' }, { ic: 'diamond', t: 'Elegant' }],
    count: 46,
    hero2: {
      eyebrow: 'Dressed in Scent', title: 'A Fragrance for the <em>Aisle</em>',
      sub: 'Sophisticated florals, luminous oud and timeless rose — chosen to complement the occasion and last from ceremony to celebration.',
      img: IMG.rose, cta: 'Shop the Edit', href: '#grid',
    },
    uspsHead: { label: 'For the Occasion', title: 'Elegance That <em>Endures</em>' },
    usps: [
      { ic: 'schedule', title: 'Lasting Power', text: 'All-day longevity so your scent is as memorable in the last photo as the first.' },
      { ic: 'diamond', title: 'Refined Elegance', text: 'Graceful, sophisticated compositions befitting the most important occasions.' },
      { ic: 'celebration', title: 'Occasion-Appropriate', text: 'Balanced projection — beautiful up close, never overwhelming in a crowded hall.' },
    ],
    sections: ['header', 'hero2', 'usps', 'grid', 'faq', 'cta'],
    cta: { label: 'Gifting the Couple?', title: 'Consult a <em>Fragrance Expert</em>', sub: 'Explore more or ask our team for help selecting the perfect wedding or gifting fragrance.', secondary: { label: 'Shop Gift Sets', href: 'gift-sets.html' } },
    faqs: [
      { q: 'What perfume should a bride wear?', a: 'Choose something elegant and lasting that you love — often soft florals, rose or luminous oud. Consider a signature you can re-wear to relive the memory.' },
      ...FAQ_TRUST.slice(0, 3),
    ],
  },

  'everyday-signature': {
    titlePlain: 'Everyday Signature Scents', eyebrow: 'Your Daily',
    title: 'Everyday Signature <em>Scents</em>',
    sub: 'Versatile, subtle-yet-memorable fragrances that become "your" smell — effortless enough for any day, distinctive enough to be remembered.',
    breadcrumb: [HOME_CRUMB, { label: 'Shop by Lifestyle', href: 'shop-by-lifestyle.html' }, { label: 'Everyday Signature' }],
    meta: [{ ic: 'wb_sunny', t: 'Any Occasion' }, { ic: 'favorite', t: 'Memorable' }],
    count: 52, filterFam: 'Fresh & Citrus',
    uspsHead: { label: 'The Everyday Edit', title: 'Effortless, <em>Every Day</em>' },
    usps: [
      { ic: 'all_inclusive', title: 'Goes With Anything', text: 'Balanced profiles that suit work, weekend and everything in between.' },
      { ic: 'air', title: 'Subtle Yet Memorable', text: 'Close-wearing warmth that people associate with you, without shouting.' },
      { ic: 'water_drop', title: 'Long-Lasting Freshness', text: 'Reliable staying power to carry you comfortably from morning to evening.' },
    ],
    sections: ['header', 'usps', 'filter', 'grid', 'crosslinks', 'reviews', 'cta'],
    crosslinks: [
      { label: 'Office Wear', href: 'collection.html?c=office-wear' },
      { label: 'Date Night', href: 'collection.html?c=date-night' },
      { label: 'Vacation & Beach', href: 'collection.html?c=vacation-beach' },
      { label: 'Best Sellers', href: 'collection.html?c=best-sellers' },
    ],
    cta: { title: 'Find <em>Your</em> Signature', sub: 'Take the Find My Scent quiz and we\'ll shortlist the everyday scents made for you.' },
  },

  'gym': {
    titlePlain: 'Gym Perfumes', eyebrow: 'Active Life',
    title: 'Gym <em>Perfumes</em>',
    sub: 'Fresh, clean and lightweight scents that keep you smelling great through the workout — energising without overpowering.',
    breadcrumb: [HOME_CRUMB, { label: 'Shop by Lifestyle', href: 'shop-by-lifestyle.html' }, { label: 'Gym Perfumes' }],
    meta: [{ ic: 'fitness_center', t: 'Sweat-Friendly' }, { ic: 'air', t: 'Lightweight' }],
    count: 30, filterFam: 'Fresh & Citrus',
    uspsHead: { label: 'Built to Move', title: 'Fresh Through the <em>Burn</em>' },
    usps: [
      { ic: 'shower', title: 'Sweat-Friendly', text: 'Clean, sporty freshness that layers well with activity instead of turning cloying.' },
      { ic: 'air', title: 'Lightweight Formulas', text: 'Airy citrus and aquatic profiles that energise without weighing you down.' },
      { ic: 'groups', title: 'Considerate Projection', text: 'Present but polite — great in shared spaces and studios.' },
    ],
    sections: ['header', 'usps', 'filter', 'grid', 'crosslinks', 'reviews', 'cta'],
    crosslinks: [
      { label: 'Summer Perfumes', href: 'collection.html?c=tropical-climate' },
      { label: 'Everyday Signature', href: 'collection.html?c=everyday-signature' },
      { label: 'Travel-Friendly', href: 'collection.html?c=travel-friendly' },
      { label: 'Best Sellers', href: 'collection.html?c=best-sellers' },
    ],
    cta: { title: 'Find Your <em>Fresh</em>', sub: 'Ask the concierge for the cleanest, most breathable picks — or browse our bestsellers.' },
  },

  'travel-friendly': {
    titlePlain: 'Travel Friendly Fragrances', eyebrow: 'On the Go',
    title: 'Travel-Friendly <em>Fragrances</em>',
    sub: 'Leak-proof, compact and TSA-smart minis and travel sprays — your signature scent, ready for the carry-on.',
    breadcrumb: [HOME_CRUMB, { label: 'Shop by Lifestyle', href: 'shop-by-lifestyle.html' }, { label: 'Travel-Friendly' }],
    meta: [{ ic: 'flight', t: 'Cabin-Ready' }, { ic: 'water_drop', t: 'Leak-Proof' }],
    count: 36,
    uspsHead: { label: 'Pack Light', title: 'Big Scent, <em>Small Bottle</em>' },
    usps: [
      { ic: 'lock', title: 'Leak-Proof', text: 'Secure atomisers and roll-ons engineered to survive the bottom of your bag.' },
      { ic: 'luggage', title: 'Compact Sizes', text: '5–30ml formats that slip into pockets and pass carry-on liquid limits.' },
      { ic: 'schedule', title: 'Long-Lasting', text: 'Full-strength juice in a travel body — no compromise on performance.' },
    ],
    sections: ['header', 'usps', 'filter', 'grid', 'crosslinks', 'testimonials', 'cta'],
    crosslinks: [
      { label: 'Gym Perfumes', href: 'collection.html?c=gym' },
      { label: 'Vacation & Beach', href: 'collection.html?c=vacation-beach' },
      { label: 'Gift Sets for Travellers', href: 'gift-sets.html' },
      { label: 'Discovery Kits', href: 'gift-sets.html' },
    ],
    cta: { label: 'Travel Minis', title: 'Shop <em>Travel Sizes</em>', sub: 'Grab a mini of your signature — or try the Find My Scent assist for your next destination.', secondary: { label: 'Shop Discovery Kits', href: 'gift-sets.html' } },
  },

  'vacation-beach': {
    titlePlain: 'Vacation & Beach Perfumes', eyebrow: 'Sun & Sea',
    title: 'Vacation &amp; Beach <em>Perfumes</em>',
    sub: 'Breezy, sun-kissed and tropical scents that capture the holiday feeling — perfect for getaways and coastal escapes.',
    breadcrumb: [HOME_CRUMB, { label: 'Shop by Lifestyle', href: 'shop-by-lifestyle.html' }, { label: 'Vacation & Beach' }],
    meta: [{ ic: 'beach_access', t: 'Coastal Fresh' }, { ic: 'wb_sunny', t: 'Summer Ready' }],
    count: 34, filterFam: 'Fresh & Citrus',
    sections: ['header', 'filter', 'grid', 'crosslinks'],
    crosslinks: [
      { label: 'Tropical Climate', href: 'collection.html?c=tropical-climate' },
      { label: 'Travel-Friendly', href: 'collection.html?c=travel-friendly' },
      { label: 'Long-Lasting Scents', href: 'collection.html?c=best-sellers' },
      { label: 'Everyday Signature', href: 'collection.html?c=everyday-signature' },
    ],
  },

  'dinner-evening': {
    titlePlain: 'Dinner & Evening Wear Fragrances', eyebrow: 'Evening Elegance',
    title: 'Dinner &amp; Evening <em>Wear</em>',
    sub: 'Sophisticated, sensual scents for candle-lit dinners and evenings out — refined warmth that lingers beautifully.',
    breadcrumb: [HOME_CRUMB, { label: 'Shop by Lifestyle', href: 'shop-by-lifestyle.html' }, { label: 'Dinner & Evening' }],
    meta: [{ ic: 'restaurant', t: 'Evening Wear' }, { ic: 'nightlife', t: 'Sophisticated' }],
    count: 42, filterFam: 'Spicy & Oriental',
    uspsHead: { label: 'What Defines It', title: 'The Art of the <em>Evening Scent</em>' },
    usps: [
      { ic: 'restaurant', title: 'Dinner-Considerate', text: 'Warm but controlled — beautiful at the table without competing with the food.' },
      { ic: 'schedule', title: 'Lasting Warmth', text: 'Amber, spice and woods that glow softly across the whole evening.' },
      { ic: 'layers', title: 'Layer to Deepen', text: 'Pair with an oil or attar for a richer, more personal evening trail.' },
    ],
    sections: ['header', 'usps', 'filter', 'grid', 'crosslinks', 'faq'],
    crosslinks: [
      { label: 'Date Night', href: 'collection.html?c=date-night' },
      { label: 'Party & Clubbing', href: 'collection.html?c=party-clubbing' },
      { label: 'Wedding & Formal', href: 'collection.html?c=wedding-formal' },
      { label: 'Luxury Perfumes', href: 'collection.html?c=luxury' },
    ],
    faqs: [
      { q: 'How do I make an evening scent last?', a: 'Apply to moisturised pulse points and layer with a matching body oil or unscented lotion. Amber, oud and gourmand bases naturally last longest into the night.' },
      ...FAQ_TRUST.slice(0, 3),
    ],
  },

  /* ── Weather & Season sub-pages ───────────────────────────────── */
  'desert-climate': {
    titlePlain: 'Desert Climate Perfumes', eyebrow: 'Heat-Proof',
    title: 'Desert Climate <em>Perfumes</em>',
    sub: 'Engineered to perform in hot, arid heat — long-lasting compositions that hold their character when the mercury climbs.',
    breadcrumb: [HOME_CRUMB, { label: 'Shop by Weather', href: 'shop-by-weather.html' }, { label: 'Desert Climate' }],
    meta: [{ ic: 'thermostat', t: 'Heat-Resistant' }, { ic: 'schedule', t: 'Holds in Heat' }],
    count: 40, filterFam: 'Spicy & Oriental',
    uspsHead: { label: 'Made for the Heat', title: 'Performance in the <em>Sun</em>' },
    usps: [
      { ic: 'thermostat', title: 'Heat-Resistant', text: 'Notes selected to stay true and avoid turning sharp under intense sun and dry air.' },
      { ic: 'schedule', title: 'Long-Lasting', text: 'Rich oud, amber and spicy bases that cling and last through desert temperatures.' },
      { ic: 'forest', title: 'Fresh, Woody & Spicy', text: 'The scent families proven to project best in hot, arid conditions.' },
    ],
    sections: ['header', 'usps', 'filter', 'grid', 'crosslinks', 'testimonials', 'cta'],
    crosslinks: [
      { label: 'Summer Perfumes', href: 'collection.html?c=tropical-climate' },
      { label: 'UAE Heat Perfumes', href: 'collection.html?c=dry-weather' },
      { label: 'Long-Lasting Perfumes', href: 'collection.html?c=best-sellers' },
      { label: 'Arabic Perfumes', href: 'collection.html?c=arabic' },
    ],
    cta: { title: 'Beat the <em>Heat</em>', sub: 'Ask the concierge which scents perform best in your climate.' },
  },

  'humid-weather': {
    titlePlain: 'Humid Weather Fragrances', eyebrow: 'High Humidity',
    title: 'Humid Weather <em>Fragrances</em>',
    sub: 'Scents that thrive when the air is heavy — bright, clean and airy profiles that stay crisp in humidity.',
    breadcrumb: [HOME_CRUMB, { label: 'Shop by Weather', href: 'shop-by-weather.html' }, { label: 'Humid Weather' }],
    meta: [{ ic: 'water', t: 'Humidity-Ready' }, { ic: 'air', t: 'Stays Crisp' }],
    count: 34, filterFam: 'Fresh & Citrus',
    sections: ['header', 'filter', 'grid', 'crosslinks'],
    crosslinks: [
      { label: 'Tropical Climate', href: 'collection.html?c=tropical-climate' },
      { label: 'Monsoon Ready', href: 'collection.html?c=monsoon-ready' },
      { label: 'Beach Vacation', href: 'collection.html?c=beach-vacation' },
      { label: 'Summer Perfumes', href: 'collection.html?c=vacation-beach' },
    ],
  },

  'rainy-day': {
    titlePlain: 'Rainy Day Perfumes', eyebrow: 'Petrichor',
    title: 'Rainy Day <em>Perfumes</em>',
    sub: 'Cozy, earthy and comforting scents that match the mood of a grey, rain-washed afternoon.',
    breadcrumb: [HOME_CRUMB, { label: 'Shop by Weather', href: 'shop-by-weather.html' }, { label: 'Rainy Day' }],
    meta: [{ ic: 'rainy', t: 'Cozy Mood' }, { ic: 'park', t: 'Earthy Notes' }],
    count: 28, filterFam: 'Oud & Woody',
    sections: ['header', 'filter', 'grid', 'crosslinks'],
    crosslinks: [
      { label: 'Humid Weather', href: 'collection.html?c=humid-weather' },
      { label: 'Monsoon Ready', href: 'collection.html?c=monsoon-ready' },
      { label: 'Everyday Signature', href: 'collection.html?c=everyday-signature' },
      { label: 'Winter Holiday', href: 'collection.html?c=winter-holiday' },
    ],
  },

  'snow-season': {
    titlePlain: 'Snow Season Perfumes', eyebrow: 'Cold Weather',
    title: 'Snow Season <em>Perfumes</em>',
    sub: 'Warm, enveloping and rich — the spiced, resinous scents that come alive in cold, crisp air.',
    breadcrumb: [HOME_CRUMB, { label: 'Shop by Weather', href: 'shop-by-weather.html' }, { label: 'Snow Season' }],
    meta: [{ ic: 'ac_unit', t: 'Cold-Weather' }, { ic: 'local_fire_department', t: 'Warm & Rich' }],
    count: 30, filterFam: 'Spicy & Oriental',
    sections: ['header', 'filter', 'grid', 'crosslinks'],
    crosslinks: [
      { label: 'Winter Holiday', href: 'collection.html?c=winter-holiday' },
      { label: 'Spring Bloom', href: 'collection.html?c=spring-bloom' },
      { label: 'Humid Weather', href: 'collection.html?c=humid-weather' },
      { label: 'Oud & Woody', href: 'collection.html?c=scent-family&family=Oud%20%26%20Woody' },
    ],
  },

  'beach-vacation': {
    titlePlain: 'Beach Vacation Fragrances', eyebrow: 'Salt & Sun',
    title: 'Beach Vacation <em>Fragrances</em>',
    sub: 'Aquatic, coconut-kissed and breezy — bottle the feeling of sand between your toes and sun on your skin.',
    breadcrumb: [HOME_CRUMB, { label: 'Shop by Weather', href: 'shop-by-weather.html' }, { label: 'Beach Vacation' }],
    meta: [{ ic: 'beach_access', t: 'Aquatic Fresh' }, { ic: 'wb_sunny', t: 'Holiday Ready' }],
    count: 32, filterFam: 'Fresh & Citrus',
    sections: ['header', 'filter', 'grid', 'crosslinks'],
    crosslinks: [
      { label: 'Tropical Climate', href: 'collection.html?c=tropical-climate' },
      { label: 'Travel-Friendly', href: 'collection.html?c=travel-friendly' },
      { label: 'Summer Scents', href: 'collection.html?c=vacation-beach' },
      { label: 'Humid Weather', href: 'collection.html?c=humid-weather' },
    ],
  },

  'tropical-climate': {
    titlePlain: 'Tropical Climate Perfumes', eyebrow: 'Heat & Humidity',
    title: 'Tropical Climate <em>Perfumes</em>',
    sub: 'Fresh, light and long-lasting — aquatic notes, citrus bursts and airy florals built for heat and humidity.',
    breadcrumb: [HOME_CRUMB, { label: 'Shop by Weather', href: 'shop-by-weather.html' }, { label: 'Tropical Climate' }],
    meta: [{ ic: 'humidity_high', t: 'Heat & Humidity' }, { ic: 'air', t: 'Light & Fresh' }],
    count: 36, filterFam: 'Fresh & Citrus',
    uspsHead: { label: 'For the Tropics', title: 'Fresh in the <em>Heat</em>' },
    usps: [
      { ic: 'water', title: 'Aquatic Notes', text: 'Cool, marine freshness that reads clean even as the temperature rises.' },
      { ic: 'nutrition', title: 'Citrus Bursts', text: 'Bright bergamot, lemon and grapefruit for an instant lift.' },
      { ic: 'local_florist', title: 'Airy Florals', text: 'Light, transparent florals that never turn heavy or cloying in humidity.' },
    ],
    sections: ['header', 'usps', 'filter', 'grid', 'crosslinks', 'testimonials', 'cta'],
    crosslinks: [
      { label: 'Beach Vacation', href: 'collection.html?c=beach-vacation' },
      { label: 'Humid Weather', href: 'collection.html?c=humid-weather' },
      { label: 'Summer Perfumes', href: 'collection.html?c=vacation-beach' },
      { label: 'Gym Perfumes', href: 'collection.html?c=gym' },
    ],
    cta: { title: 'Find Your <em>Tropical</em> Scent', sub: 'Take the quiz for fresh, heat-proof recommendations tailored to you.' },
  },

  'dry-weather': {
    titlePlain: 'Dry Weather Perfumes', eyebrow: 'Arid Air',
    title: 'Dry Weather <em>Perfumes</em>',
    sub: 'Curated for arid, low-humidity conditions — hydrating, creamy and long-clinging scents that won\'t vanish in dry air.',
    breadcrumb: [HOME_CRUMB, { label: 'Shop by Weather', href: 'shop-by-weather.html' }, { label: 'Dry Weather' }],
    meta: [{ ic: 'wb_sunny', t: 'Arid-Ready' }, { ic: 'spa', t: 'Creamy Bases' }],
    count: 30, filterFam: 'Sweet & Gourmand',
    uspsHead: { label: 'For Arid Air', title: 'Scents That <em>Stay</em>' },
    usps: [
      { ic: 'spa', title: 'Creamy & Hydrating', text: 'Musk, sandalwood and vanilla bases that stay rich even in dry, low-humidity air.' },
      { ic: 'schedule', title: 'Long-Clinging', text: 'Heavier molecules that resist the quick evaporation dry climates cause.' },
      { ic: 'layers', title: 'Layer-Friendly', text: 'Pair with an oil to lock in longevity when the air is at its driest.' },
    ],
    sections: ['header', 'usps', 'filter', 'grid', 'crosslinks'],
    crosslinks: [
      { label: 'Desert Climate', href: 'collection.html?c=desert-climate' },
      { label: 'Humid Weather', href: 'collection.html?c=humid-weather' },
      { label: 'Travel-Friendly', href: 'collection.html?c=travel-friendly' },
      { label: 'Attar & Oils', href: 'collection.html?c=attar' },
    ],
  },

  'monsoon-ready': {
    titlePlain: 'Monsoon Ready Fragrances', eyebrow: 'Rain or Shine',
    title: 'Monsoon Ready <em>Fragrances</em>',
    sub: 'Fresh, resilient scents made for wet season air — clean profiles that shrug off dampness and lift the mood.',
    breadcrumb: [HOME_CRUMB, { label: 'Shop by Weather', href: 'shop-by-weather.html' }, { label: 'Monsoon Ready' }],
    meta: [{ ic: 'rainy', t: 'Wet Season' }, { ic: 'air', t: 'Fresh & Clean' }],
    count: 28, filterFam: 'Fresh & Citrus',
    sections: ['header', 'filter', 'grid', 'crosslinks'],
    crosslinks: [
      { label: 'Rainy Day Perfumes', href: 'collection.html?c=rainy-day' },
      { label: 'Humid Weather', href: 'collection.html?c=humid-weather' },
      { label: 'Tropical Climate', href: 'collection.html?c=tropical-climate' },
      { label: 'Everyday Signature', href: 'collection.html?c=everyday-signature' },
    ],
  },

  'winter-holiday': {
    titlePlain: 'Winter Holiday Fragrances', eyebrow: 'Festive Season',
    title: 'Winter Holiday <em>Fragrances</em>',
    sub: 'Cozy spices, warm vanilla and festive resins — gift-ready scents that wrap the season in warmth.',
    breadcrumb: [HOME_CRUMB, { label: 'Shop by Weather', href: 'shop-by-weather.html' }, { label: 'Winter Holiday' }],
    meta: [{ ic: 'celebration', t: 'Festive' }, { ic: 'card_giftcard', t: 'Gift-Ready' }],
    count: 38, filterFam: 'Sweet & Gourmand',
    uspsHead: { label: 'Season\'s Warmth', title: 'Cozy, Festive &amp; <em>Gift-Ready</em>' },
    usps: [
      { ic: 'local_fire_department', title: 'Cozy Scents', text: 'Warm amber, cinnamon and vanilla that feel like a fireside on a cold night.' },
      { ic: 'celebration', title: 'Festive Notes', text: 'Spiced, resinous and rich — the signatures of the holiday season.' },
      { ic: 'card_giftcard', title: 'Gift-Ready Picks', text: 'Beautifully boxed sets that make effortless, memorable presents.' },
    ],
    sections: ['header', 'usps', 'filter', 'grid', 'crosslinks', 'testimonials', 'faq'],
    crosslinks: [
      { label: 'Shop All Gift Sets', href: 'gift-sets.html' },
      { label: 'Snow Season', href: 'collection.html?c=snow-season' },
      { label: 'Festive Best-Sellers', href: 'collection.html?c=best-sellers' },
      { label: 'Holiday Guides', href: 'seasonal-trends.html' },
    ],
    faqs: [
      { q: 'What are the best winter scents?', a: 'Warm, spicy and gourmand fragrances — amber, cinnamon, vanilla, oud and resins — perform beautifully in cold air and evoke the festive mood.' },
      { q: 'Can I still get holiday delivery in time?', a: 'In-stock orders dispatch within 48 hours across the UAE. For guaranteed festive delivery, order early and choose an express option at checkout where available.' },
      ...FAQ_TRUST.slice(0, 2),
    ],
  },

  'spring-bloom': {
    titlePlain: 'Spring Bloom Perfumes', eyebrow: 'Fresh Blossom',
    title: 'Spring Bloom <em>Perfumes</em>',
    sub: 'Fresh, floral and uplifting — green, airy and blossoming scents that capture the optimism of spring.',
    breadcrumb: [HOME_CRUMB, { label: 'Shop by Weather', href: 'shop-by-weather.html' }, { label: 'Spring Bloom' }],
    meta: [{ ic: 'local_florist', t: 'Floral & Green' }, { ic: 'air', t: 'Airy & Fresh' }],
    count: 34, filterFam: 'Floral & Rose',
    uspsHead: { label: 'The Spring Edit', title: 'Bloom &amp; <em>Bloom Again</em>' },
    usps: [
      { ic: 'local_florist', title: 'Floral Notes', text: 'Rose, peony, jasmine and blossom for a fresh, romantic lift.' },
      { ic: 'grass', title: 'Green & Airy', text: 'Dewy greens and transparent musks that feel like a spring morning.' },
      { ic: 'wb_sunny', title: 'Uplifting', text: 'Bright, optimistic compositions that carry beautifully through mild days.' },
    ],
    sections: ['header', 'usps', 'filter', 'grid', 'crosslinks', 'faq'],
    crosslinks: [
      { label: 'Summer & UAE-Heat', href: 'collection.html?c=tropical-climate' },
      { label: 'Everyday Signature', href: 'collection.html?c=everyday-signature' },
      { label: 'Gift Sets', href: 'gift-sets.html' },
      { label: 'Floral & Rose Family', href: 'collection.html?c=scent-family&family=Floral%20%26%20Rose' },
    ],
    faqs: [
      { q: 'How do I choose a spring scent?', a: 'Look for lighter florals, greens and citrus that feel fresh in mild weather. If you love layering, pair a floral with a soft musk for a longer-lasting spring signature.' },
      ...FAQ_TRUST.slice(0, 3),
    ],
  },

  /* ── Occasion landings (Gifter, Tier 2) ───────────────────────── */
  'eid': {
    titlePlain: 'Eid Gifts', eyebrow: 'Celebrate the Season',
    title: 'Eid <em>Gifts &amp; Scents</em>',
    story: 'Mark the occasion with a fragrance worth remembering. Our Eid edit brings together rich oud, warm amber and gift-ready sets — beautifully boxed, 100% authentic, and delivered across the UAE in time to celebrate.',
    heroImg: IMG.gold,
    breadcrumb: [HOME_CRUMB, { label: 'Occasions & Gifts', href: 'occasions-gifts.html' }, { label: 'Eid' }],
    meta: [{ ic: 'celebration', t: 'Eid-Ready' }, { ic: 'card_giftcard', t: 'Gift Wrapped' }],
    count: 46, filterFam: 'Spicy & Oriental',
    sections: ['header', 'delivery', 'filter', 'grid', 'crosslinks', 'cta'],
    xHead: 'More Occasions', xTitle: 'Other <em>Moments to Gift</em>',
    crosslinks: [
      { label: 'Wedding Gifts', href: 'collection.html?c=wedding' },
      { label: 'Gifts for Him', href: 'collection.html?c=gifts-for-him' },
      { label: 'Gifts for Her', href: 'collection.html?c=gifts-for-her' },
      { label: 'Gift Sets', href: 'gift-sets.html' },
    ],
    cta: { label: 'Make It Effortless', title: 'Let Us Build the <em>Perfect Gift</em>', sub: 'Tell our concierge who it\'s for and your budget — we\'ll curate the ideal Eid gift in seconds.', secondary: { label: 'Shop Gift Sets', href: 'gift-sets.html' } },
  },

  'wedding': {
    titlePlain: 'Wedding Gifts', eyebrow: 'The Big Day',
    title: 'Wedding <em>Gifts &amp; Scents</em>',
    story: 'Elegant, lasting fragrances for the couple, the party, and the moments in between — refined signatures and premium sets that feel as special as the occasion.',
    heroImg: IMG.rose,
    breadcrumb: [HOME_CRUMB, { label: 'Occasions & Gifts', href: 'occasions-gifts.html' }, { label: 'Wedding' }],
    meta: [{ ic: 'diamond', t: 'Elegant' }, { ic: 'card_giftcard', t: 'Gift Wrapped' }],
    count: 42, filterFam: 'Floral & Rose',
    sections: ['header', 'delivery', 'filter', 'grid', 'crosslinks', 'cta'],
    xHead: 'More Occasions', xTitle: 'Other <em>Moments to Gift</em>',
    crosslinks: [
      { label: 'Eid Gifts', href: 'collection.html?c=eid' },
      { label: 'Wedding & Formal Wear', href: 'collection.html?c=wedding-formal' },
      { label: 'Gifts for Her', href: 'collection.html?c=gifts-for-her' },
      { label: 'Gift Sets', href: 'gift-sets.html' },
    ],
    cta: { title: 'Need a Hand <em>Choosing?</em>', sub: 'Our concierge can build the perfect wedding gift for any budget.', secondary: { label: 'Shop Gift Sets', href: 'gift-sets.html' } },
  },

  'gifts-for-him': {
    titlePlain: 'Gifts for Him', eyebrow: 'For Him',
    title: 'Gifts <em>for Him</em>',
    sub: 'Confident, long-lasting fragrances he\'ll actually reach for — from fresh daily signatures to bold oud statements, gift-wrapped and ready.',
    breadcrumb: [HOME_CRUMB, { label: 'Occasions & Gifts', href: 'occasions-gifts.html' }, { label: 'Gifts for Him' }],
    meta: [{ ic: 'redeem', t: 'Gift-Ready' }, { ic: 'schedule', t: '8–12hr Longevity' }],
    count: 64, filterGender: 'Men',
    sections: ['header', 'delivery', 'filter', 'grid', 'crosslinks', 'cta'],
    xHead: 'More Occasions', xTitle: 'Keep <em>Gifting</em>',
    crosslinks: [
      { label: 'Gifts for Her', href: 'collection.html?c=gifts-for-her' },
      { label: 'Eid Gifts', href: 'collection.html?c=eid' },
      { label: 'Men\'s Best Sellers', href: 'collection.html?c=mens' },
      { label: 'Gift Sets', href: 'gift-sets.html' },
    ],
    cta: { title: 'Not Sure What He\'d <em>Love?</em>', sub: 'Answer a couple of questions and we\'ll shortlist the perfect gift for him.' },
  },

  'gifts-for-her': {
    titlePlain: 'Gifts for Her', eyebrow: 'For Her',
    title: 'Gifts <em>for Her</em>',
    sub: 'Luminous florals, warm gourmands and elegant orientals — memorable fragrances and sets that make a beautiful gift, wrapped and delivered fast.',
    breadcrumb: [HOME_CRUMB, { label: 'Occasions & Gifts', href: 'occasions-gifts.html' }, { label: 'Gifts for Her' }],
    meta: [{ ic: 'redeem', t: 'Gift-Ready' }, { ic: 'local_florist', t: 'Floral to Oriental' }],
    count: 58, filterGender: 'Women',
    sections: ['header', 'delivery', 'filter', 'grid', 'crosslinks', 'cta'],
    xHead: 'More Occasions', xTitle: 'Keep <em>Gifting</em>',
    crosslinks: [
      { label: 'Gifts for Him', href: 'collection.html?c=gifts-for-him' },
      { label: 'Wedding Gifts', href: 'collection.html?c=wedding' },
      { label: 'Women\'s Best Sellers', href: 'collection.html?c=womens' },
      { label: 'Gift Sets', href: 'gift-sets.html' },
    ],
    cta: { title: 'Not Sure What She\'d <em>Love?</em>', sub: 'Answer a couple of questions and we\'ll shortlist the perfect gift for her.' },
  },

  'discovery-kits': {
    titlePlain: 'Discovery Kits', eyebrow: 'Try Before You Commit',
    title: 'Discovery <em>Kits</em>',
    sub: 'Sample our bestsellers in travel vials before investing in a full bottle — the low-commitment way to find your signature, and a lovely little gift. Kit credit applies toward your first full-size order.',
    breadcrumb: [HOME_CRUMB, { label: 'Occasions & Gifts', href: 'occasions-gifts.html' }, { label: 'Discovery Kits' }],
    meta: [{ ic: 'science', t: 'Sample First' }, { ic: 'redeem', t: 'Credit to Full-Size' }],
    count: 12, gridKind: 'kits',
    sections: ['header', 'grid', 'trust', 'crosslinks', 'cta'],
    gridLabel: 'Low Commitment', gridTitle: 'Shop the <em>Kits</em>',
    xHead: 'Keep Exploring', xTitle: 'You Might Also <em>Like</em>',
    crosslinks: [
      { label: 'Gift Sets', href: 'gift-sets.html' },
      { label: 'Best Sellers', href: 'collection.html?c=best-sellers' },
      { label: 'Perfume Oil', href: 'collection.html?c=perfume-oil' },
      { label: 'Occasions & Gifts', href: 'occasions-gifts.html' },
    ],
    cta: { label: 'Ready to Commit?', title: 'Upgrade to a <em>Full Bottle</em>', sub: 'Loved a sample? Your discovery-kit credit applies toward any full-size fragrance.', primary: { label: 'Shop All Products', href: 'collection.html?c=all', onclick: '' } },
  },

};
