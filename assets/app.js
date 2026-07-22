/* ═══════════════════════════════════════════════════════════════════
   THE FRAGRANCE SECRETS — SHARED RUNTIME (app.js)
   Loaded on every page. Injects site chrome (announce bar, header,
   footer, WhatsApp float, AI concierge, Mix-into-Spray wizard, referral
   modal), carries shared catalogue data + reusable renderers, and wires
   all shared behaviours. Everything is null-safe so a single file works
   across the whole multi-page site.
═══════════════════════════════════════════════════════════════════ */

/* ═══════════════════════════════════════
   CATALOGUE DATA
═══════════════════════════════════════ */
const products = []; // populated from the live store by loadLiveCatalog()

const reviews = [
  { name: 'Fatima Al Rashid', loc: 'Dubai, UAE', text: 'Smells exactly like luxury brands — insane quality for the price! My whole office was asking what I was wearing.', prod: 'Bouquet of Oud EDP', init: 'F', rating: 5 },
  { name: 'Mohammed Hassan', loc: 'Abu Dhabi, UAE', text: 'Finally found an authentic store in UAE. Packaging was perfect, scent is even better in person. Will definitely order again.', prod: 'Amber Oud Gold EDP', init: 'M', rating: 5 },
  { name: 'Sara Al Zaabi', loc: 'Sharjah, UAE', text: 'The fragrance notes described on the site were spot on. Long-lasting, beautiful, and arrived within 24 hours. Highly recommend!', prod: 'Club de Nuit Précieux', init: 'S', rating: 5 },
  { name: 'Khalid Ibrahim', loc: 'Dubai, UAE', text: 'Ordered 3 times now. Always authentic, always fast. Customer service on WhatsApp is incredible — super helpful.', prod: 'Badee Al Oud Honor & Glory', init: 'K', rating: 5 },
  { name: 'Aisha Mohammed', loc: 'Ajman, UAE', text: 'Perfect gift for my husband. He loved it and keeps asking me where I bought it from. Fragrance Secrets is now my go-to.', prod: 'Shaghaf Oud Elixir', init: 'A', rating: 5 },
  { name: 'Omar Al Mansouri', loc: 'Dubai, UAE', text: 'The quality guarantee gives me peace of mind. No more worrying about fakes. Fast delivery, great prices, genuine products.', prod: 'Hawas Fire EDP', init: 'O', rating: 5 },
];

const brands = []; // populated from live product vendors by loadLiveCatalog()

const blogs = [
  { cat: 'Comparison Guide', title: 'Best Oud Perfumes in UAE You Should Try in 2026', excerpt: 'Explore top oud fragrances ranked based on longevity, scent profile, and overall performance, from affordable everyday picks to premium luxury collections.', date: 'June 2, 2026', read: '8 min read', img: 'assets/img/ed-1.jpg' },
  { cat: 'Fragrance Comparison', title: 'Armaf Club De Nuit vs Creed Aventus: Which One Performs Better?', excerpt: 'Compare fragrance notes, longevity, projection, and overall value to understand how close this popular alternative really gets to the original.', date: 'May 24, 2026', read: '6 min read', img: 'assets/img/prod-club-de-nuit.jpg' },
  { cat: 'How-To Guide', title: 'How to Layer Fragrances for a Longer Lasting Scent', excerpt: 'Learn how combining perfume oils and fragrances correctly can improve longevity while creating a scent profile that feels completely your own.', date: 'May 11, 2026', read: '5 min read', img: 'assets/img/ed-2.jpg' },
  { cat: 'Expert Guide', title: 'How to Make Perfume Last Longer in UAE Weather', excerpt: 'Understand why fragrances fade faster in warm climates and learn simple application techniques that help improve scent longevity throughout the day.', date: 'April 28, 2026', read: '7 min read', img: 'assets/img/ed-3.jpg' },
  { cat: 'Buying Guide', title: 'How to Choose the Right Perfume Gift for Every Occasion', excerpt: 'From birthdays to Eid celebrations, learn how to choose fragrances that feel thoughtful, personal, and perfect for every special moment.', date: 'April 9, 2026', read: '6 min read', img: 'assets/img/kit-gift.jpg' },
  { cat: 'Fragrance Guide', title: 'EDP vs EDT vs Attar: Which Fragrance Lasts Longer?', excerpt: 'Understand fragrance concentration differences and learn which perfume type works best for everyday wear, special occasions, and long-lasting performance.', date: 'March 30, 2026', read: '5 min read', img: 'assets/img/cat-attar.jpg' },
];

const ugcImgs = [
  'assets/img/kit-gift.jpg',
  'assets/img/prod-bouquet-oud.png',
  'assets/img/hero-oud.jpg',
  'assets/img/prod-club-de-nuit.jpg',
  'assets/img/prod-hawas.jpg',
];

const discoveryKits = []; // no hardcoded kits — use a real discovery-kits collection

/* Shared image pool for hero / editorial imagery */
const IMG = {
  hero: 'assets/img/prod-bouquet-oud.png',
  oud: 'assets/img/hero-oud.jpg',
  bottles: 'assets/img/hero-bottles.jpg',
  gold: 'assets/img/hero-gold.png',
  rose: 'assets/img/prod-oud-roses.jpg',
  splash: 'assets/img/cat-luxury.jpg',
};

/* ═══════════════════════════════════════
   SMALL HELPERS
═══════════════════════════════════════ */
function money(n) { return (window.CURRENCY || 'AED') + ' ' + Number(n).toLocaleString('en-AE'); }
function savePct(price, was) { return Math.round((1 - price / was) * 100); }
function qs(name) { return new URLSearchParams(location.search).get(name); }
function el(id) { return document.getElementById(id); }
function esc(s) { return String(s).replace(/</g, '&lt;').replace(/>/g, '&gt;'); }

/* ═══════════════════════════════════════
   ASSET RESOLVER — Shopify flattens the assets/ folder, so an original
   path like "assets/img/prod-x.png" must resolve to the theme's flat CDN
   asset URL. theme.liquid sets window.ASSET_BASE = ".../assets/". We take
   the basename and prepend that base. Absolute/data URLs pass through.
═══════════════════════════════════════ */
function assetURL(p) {
  if (!p) return '';
  if (/^(https?:|\/\/|data:)/.test(p)) return p;
  return (window.ASSET_BASE || 'assets/img/') + String(p).split('/').pop();
}

/* ═══════════════════════════════════════
   LIVE CATALOGUE — replace the demo products with the store's real,
   published products (Shopify storefront /products.json) so the concierge
   recommends, links, and adds real items. Runs at init; the demo data
   remains only as an offline fallback.
═══════════════════════════════════════ */
const FAMILY_TAGS = {
  'family-oud-woody': 'Oud & Woody',
  'family-fresh-citrus': 'Fresh & Citrus',
  'family-floral-rose': 'Floral & Rose',
  'family-sweet-gourmand': 'Sweet & Gourmand',
  'family-spicy-oriental': 'Spicy & Oriental',
};
function loadLiveCatalog() {
  // Paginate — the storefront caps each page at 250 and the catalogue is larger
  var collected = [], MAX_PAGES = 8;
  function page(n) {
    return fetch('/products.json?limit=250&page=' + n, { headers: { 'Accept': 'application/json' } })
      .then(function (r) { if (!r.ok) throw 0; return r.json(); })
      .then(function (d) {
        var batch = d.products || [];
        collected = collected.concat(batch);
        if (batch.length === 250 && n < MAX_PAGES) return page(n + 1);
        return { products: collected };
      });
  }
  page(1)
    .then(function (data) {
      var live = (data.products || []).map(function (p) {
        var tags = Array.isArray(p.tags) ? p.tags : String(p.tags || '').split(',').map(function (t) { return t.trim(); });
        var v = (p.variants && p.variants[0]) || {};
        var family = '', gender = 'Unisex', badge = '', badgeClass = 'badge-best';
        tags.forEach(function (t) {
          if (FAMILY_TAGS[t]) family = FAMILY_TAGS[t];
          if (t === 'mens') gender = 'Men';
          if (t === 'womens') gender = 'Women';
          if (t === 'kids') gender = 'Kids';
        });
        if (tags.indexOf('bestseller') > -1) { badge = 'Bestseller'; badgeClass = 'badge-best'; }
        else if (tags.indexOf('new-arrival') > -1) { badge = 'New'; badgeClass = 'badge-new'; }
        else if (tags.indexOf('sale') > -1) { badge = 'Sale'; badgeClass = 'badge-sale'; }
        return {
          id: p.id, brand: p.vendor || '', name: p.title || '',
          price: parseFloat(v.price) || 0,
          was: parseFloat(v.compare_at_price) || 0,
          badge: badge, badgeClass: badgeClass,
          rating: 4.8, reviews: 0,
          family: family, gender: gender, occasion: '',
          img: (p.images && p.images[0] && p.images[0].src) || '',
          url: '/products/' + p.handle,
          variantId: v.id,
        };
      }).filter(function (p) { return p.name && p.price > 0; });
      if (live.length) {
        products.length = 0;
        Array.prototype.push.apply(products, live);
        // Teach the concierge any live vendor it doesn't already know
        var known = {};
        brands.forEach(function (b) { known[b.toLowerCase()] = 1; });
        live.forEach(function (p) {
          var b = (p.brand || '').trim();
          if (b && !known[b.toLowerCase()]) { known[b.toLowerCase()] = 1; brands.push(b); }
        });
        // Re-render any [data-render] grids so they show live data (fetch is async)
        try { hydrateRenderables(); observeFadeUps(); } catch (e) { }
      }
    })
    .catch(function () { /* offline/preview — keep the demo catalogue */ });
}

function starsHTML(r) {
  return Array.from({ length: 5 }, (_, i) =>
    `<span class="mi mi-f" aria-hidden="true" style="color:${i < Math.round(r) ? 'var(--gold)' : 'var(--cream-dk)'}">star</span>`
  ).join('');
}

/* ═══════════════════════════════════════
   REUSABLE CARD RENDERERS
═══════════════════════════════════════ */
function productCardHTML(p) {
  return `<div class="prod-card fade-up" onclick="location.href='${p.url || R('product.html')}'">
    <div class="prod-img-wrap">
      <img class="prod-img" src="${assetURL(p.img)}" alt="${esc(p.name)}" loading="lazy"/>
      ${p.badge ? `<div class="prod-badge ${p.badgeClass}">${p.badge}</div>` : ''}
      <div class="prod-actions">
        <button class="pa-btn" title="Wishlist" onclick="event.stopPropagation();toast('♡ Saved to wishlist')"><span class="mi" aria-hidden="true">favorite</span></button>
        <button class="pa-btn quick-add" onclick="event.stopPropagation();addLiveToCart(${p.variantId || 0}, '${esc(p.name).replace(/'/g, "\\'")}')"><span class="mi" aria-hidden="true">shopping_bag</span>Quick Add</button>
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

function reviewCardHTML(r) {
  return `<div class="rv-card fade-up">
    <div class="rv-top">
      <div class="rv-avatar">${r.init}</div>
      <div>
        <div class="rv-name">${esc(r.name)}</div>
        <div class="rv-meta">${esc(r.loc)}</div>
        <div class="rv-verify"><span class="mi" aria-hidden="true">check</span>Verified Purchase</div>
      </div>
      <div class="stars" style="margin-left:auto">${starsHTML(r.rating)}</div>
    </div>
    <div class="rv-text">${esc(r.text)}</div>
    <div class="rv-prod"> ${esc(r.prod)}</div>
  </div>`;
}

function kitCardHTML(k) {
  const save = savePct(k.price, k.was);
  return `<div class="prod-card fade-up" onclick="location.href='${R('product.html')}'">
    <div class="prod-img-wrap">
      <img class="prod-img" src="${assetURL(k.img)}" alt="${esc(k.name)}" loading="lazy"/>
      <div class="prod-badge badge-kit">${k.badge}</div>
      <div class="prod-actions">
        <button class="pa-btn" title="Wishlist" onclick="event.stopPropagation();toast('♡ Saved to wishlist')"><span class="mi" aria-hidden="true">favorite</span></button>
        <button class="pa-btn quick-add" onclick="event.stopPropagation();addToCart('${esc(k.name).replace(/'/g, "\\'")}')"><span class="mi" aria-hidden="true">shopping_bag</span>Quick Add</button>
      </div>
    </div>
    <div class="prod-info">
      <div class="kit-pieces"><span class="mi" aria-hidden="true">layers</span>${k.pieces}</div>
      <div class="prod-name">${esc(k.name)}</div>
      <div class="prod-rating"><div class="stars">${starsHTML(k.rating)}</div><span>(${k.reviews.toLocaleString()})</span></div>
      <div class="prod-price"><span class="price-from">From</span><span class="price-now">${money(k.price)}</span><span class="price-was">${money(k.was)}</span><span class="price-save">Save ${save}%</span></div>
    </div>
  </div>`;
}

function blogCardHTML(b) {
  return `<a class="bl-card" href="${R('journal.html')}">
    <div class="bl-img-wrap"><img class="bl-img" src="${assetURL(b.img)}" alt="${esc(b.title)}" loading="lazy"/></div>
    <div class="bl-cat">${b.cat}</div>
    <div class="bl-title">${esc(b.title)}</div>
    <div class="bl-excerpt">${esc(b.excerpt)}</div>
    <div class="bl-meta">${b.date}${b.read ? ' · ' + b.read : ''}</div>
  </a>`;
}

/* Fill any element that carries a data-render attribute */
function hydrateRenderables() {
  document.querySelectorAll('[data-render]').forEach(node => {
    const kind = node.getAttribute('data-render');
    const n = parseInt(node.getAttribute('data-count') || '0', 10);
    const from = parseInt(node.getAttribute('data-from') || '0', 10);
    let list;
    if (kind === 'products') list = n ? products.slice(from, from + n) : products, node.innerHTML = list.map(productCardHTML).join('');
    else if (kind === 'reviews') node.innerHTML = (n ? reviews.slice(0, n) : reviews).map(reviewCardHTML).join('');
    else if (kind === 'kits') node.innerHTML = discoveryKits.map(kitCardHTML).join('');
    else if (kind === 'blogs') node.innerHTML = (n ? blogs.slice(0, n) : blogs).map(blogCardHTML).join('');
    else if (kind === 'brands') node.innerHTML = brandsIndexHTML();
    else if (kind === 'brand-track') {
      // Curated marquee: top brands by live product count, junk vendors filtered
      const counts = {};
      products.forEach(p => { const b = (p.brand || '').trim(); if (b) counts[b] = (counts[b] || 0) + 1; });
      let names = Object.keys(counts).filter(b => !/offer|deal|^gift$/i.test(b));
      names.sort((a, b) => counts[b] - counts[a]);
      names = names.slice(0, 28);
      if (!names.length) names = brands.slice(0, 28);
      node.innerHTML = names.concat(names).map(b => `<a class="brand-item" href="${vendorURL(b)}">${esc(b)}</a>`).join('');
      // Constant scroll speed (~40px/s) no matter how many brands are in the track
      requestAnimationFrame(() => {
        const half = node.scrollWidth / 2;
        if (half > 0) node.style.animationDuration = Math.max(30, Math.round(half / 40)) + 's';
      });
    }
    else if (kind === 'ugc') node.innerHTML = ugcImgs.map(u => `
  <div class="ugc-item">
    <img src="${assetURL(u)}" alt="Customer" loading="lazy"/>
    <div class="ugc-hover"><svg viewBox="0 0 24 24"><rect x="2" y="2" width="20" height="20" rx="5"/><path d="M16 11.37A4 4 0 1 1 12.63 8 4 4 0 0 1 16 11.37z"/><line x1="17.5" y1="6.5" x2="17.51" y2="6.5"/></svg><span>View on Instagram</span></div>
  </div>`).join('');
  });
}

/* Compact alphabetical brand cloud (dense, low-scroll) */
function vendorURL(name) { return '/collections/vendors?q=' + encodeURIComponent(name); }

/* Brand index — built from the LIVE catalogue: one card per vendor with a real
   product photo from that brand, its product count, and a working vendor link.
   Falls back to plain chips when the live catalogue isn't available. */
function brandsIndexHTML() {
  const byBrand = {};
  products.forEach(p => {
    const b = (p.brand || '').trim();
    if (!b) return;
    if (!byBrand[b]) byBrand[b] = { name: b, img: '', count: 0 };
    byBrand[b].count++;
    if (!byBrand[b].img && p.img) byBrand[b].img = p.img;
  });
  const list = Object.keys(byBrand).map(k => byBrand[k]).sort((a, b) => a.name.localeCompare(b.name));
  if (!list.length) {
    return [...brands].sort((a, b) => a.localeCompare(b)).map(b =>
      `<a class="brand-chip" href="${vendorURL(b)}">${esc(b)}<span class="mi" aria-hidden="true">arrow_outward</span></a>`
    ).join('');
  }
  return list.map(b => `<a class="brand-card" href="${vendorURL(b.name)}">
    <span class="bc-img">${b.img ? `<img src="${assetURL(b.img)}" alt="${esc(b.name)}" loading="lazy"/>` : ''}</span>
    <span class="bc-txt">
      <span class="bc-name">${esc(b.name)}</span>
      <span class="bc-count">${b.count} fragrance${b.count === 1 ? '' : 's'}</span>
    </span>
    <span class="mi bc-go" aria-hidden="true">arrow_outward</span>
  </a>`).join('');
}

/* ═══════════════════════════════════════
   BASE PATH — resolve links relative to site root
   (so pages in subfolders like /legal/ still link correctly).
   Derived from this script's own src: "../assets/js/app.js" → "../".
═══════════════════════════════════════ */
const APP_SRC = (document.currentScript && document.currentScript.getAttribute('src')) || 'assets/js/app.js';
const BASE = APP_SRC.replace(/assets\/js\/app\.js(?:\?.*)?(?:#.*)?$/, '');
function R(path) { return /^(https?:|mailto:|tel:|#|\/)/.test(path) ? path : BASE + path; }

/* ═══════════════════════════════════════
   CHROME — ANNOUNCE / HEADER / FOOTER / FLOATS
═══════════════════════════════════════ */
const A_ITEMS = [
  'Complimentary delivery anywhere in the UAE on orders above AED 150',
  'Every fragrance is 100% authentic with fully verified sourcing',
  'Cash on delivery available across all Emirates for easy shopping',
  'Explore 218+ fragrance houses trusted by perfume lovers in the UAE',
  'Need assistance? Connect with our WhatsApp team daily from 10am to 7pm',
];

/* Buy-led, Shop-dominant nav (strategy Decision 3) */
const NAV_LINKS = [
  { label: 'Shop', href: 'collection.html?c=all', key: 'shop', mega: true },
  { label: 'Brands', href: 'brand-index.html', key: 'brands' },
  { label: 'Occasions &amp; Gifts', href: 'occasions-gifts.html', key: 'occasions' },
  { label: 'Guides', href: 'journal.html', key: 'guides' },
];

/* Shop mega-menu: Quick links · Shop by Category · Lifestyle · Weather & Season · Scent Family */
const SHOP_MEGA = [
  { title: 'Shop', links: [['All Products', 'collection.html?c=all'], ['Best Sellers', 'collection.html?c=best-sellers'], ['New Arrivals', 'collection.html?c=new-arrivals'], ['Crazy Deals', 'crazy-deals.html']] },
  { title: 'Shop by Category', links: [["Men's Perfumes", 'collection.html?c=mens'], ["Women's Perfumes", 'collection.html?c=womens'], ['Kids Perfumes', 'collection.html?c=kids'], ['Unisex Perfumes', 'collection.html?c=unisex'], ['Luxury Perfumes', 'collection.html?c=luxury'], ['Miracle Plant', 'collection.html?c=miracle-plant'], ['Perfume Oil', 'collection.html?c=perfume-oil'], ['Attar', 'collection.html?c=attar'], ['Arabic Perfumes', 'collection.html?c=arabic'], ['Inspired Perfumes', 'collection.html?c=inspired']] },
  { title: 'Shop by Lifestyle', links: [['Office Wear Fragrances', 'collection.html?c=office-wear'], ['Date Night Perfumes', 'collection.html?c=date-night'], ['Party &amp; Clubbing Fragrances', 'collection.html?c=party-clubbing'], ['Wedding &amp; Formal Event Perfumes', 'collection.html?c=wedding-formal'], ['Everyday Signature Scents', 'collection.html?c=everyday-signature'], ['Gym Perfumes', 'collection.html?c=gym'], ['Travel Friendly Fragrances', 'collection.html?c=travel-friendly'], ['Vacation &amp; Beach Perfumes', 'collection.html?c=vacation-beach'], ['Dinner &amp; Evening Wear Fragrances', 'collection.html?c=dinner-evening']] },
  { title: 'Shop by Weather &amp; Season', links: [['Desert Climate Perfumes', 'collection.html?c=desert-climate'], ['Humid Weather Fragrances', 'collection.html?c=humid-weather'], ['Rainy Day Perfumes', 'collection.html?c=rainy-day'], ['Snow Season Perfumes', 'collection.html?c=snow-season'], ['Beach Vacation Fragrances', 'collection.html?c=beach-vacation'], ['Tropical Climate Perfumes', 'collection.html?c=tropical-climate'], ['Dry Weather Perfumes', 'collection.html?c=dry-weather'], ['Monsoon Ready Fragrances', 'collection.html?c=monsoon-ready'], ['Winter Holiday Fragrances', 'collection.html?c=winter-holiday'], ['Spring Bloom Perfumes', 'collection.html?c=spring-bloom']] },
  { title: 'By Scent Family', links: [['Oud &amp; Woody', 'collection.html?c=scent-family&family=Oud%20%26%20Woody'], ['Fresh &amp; Citrus', 'collection.html?c=scent-family&family=Fresh%20%26%20Citrus'], ['Floral &amp; Rose', 'collection.html?c=scent-family&family=Floral%20%26%20Rose'], ['Sweet &amp; Gourmand', 'collection.html?c=scent-family&family=Sweet%20%26%20Gourmand'], ['Spicy &amp; Oriental', 'collection.html?c=scent-family&family=Spicy%20%26%20Oriental']] },
];

const WA_SVG = `<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413z"/></svg>`;

function announceHTML() {
  const items = [...A_ITEMS, ...A_ITEMS].map(t => `<div class="a-item">${t}<span class="dot">✦</span></div>`).join('');
  return `<div class="announce"><div class="announce-track">${items}</div></div>`;
}

function navItemHTML(l, active) {
  const activeCls = l.key === active ? ' nav-active' : '';
  if (l.mega) {
    const cols = SHOP_MEGA.map(g =>
      `<div class="nm-col"><h5>${g.title}</h5>${g.links.map(([t, h]) => `<a href="${h}">${t}</a>`).join('')}</div>`
    ).join('');
    return `<div class="nav-item has-mega">
      <a href="${l.href}" class="nav-toplink${activeCls}">${l.label}<span class="mi nav-caret" aria-hidden="true">expand_more</span></a>
      <div class="nav-mega"><div class="nav-mega-inner container">${cols}</div></div>
    </div>`;
  }
  return `<a href="${l.href}" class="nav-toplink${activeCls}">${l.label}</a>`;
}

function headerHTML(theme, active) {
  const links = NAV_LINKS.map(l => navItemHTML(l, active)).join('');
  return `<header id="hdr" class="${theme}">
    <div class="nav-wrap">
      <a href="${R('index.html')}" class="nav-logo" aria-label="The Fragrance Secrets — Home"><img src="${R('assets/img/logo.png')}" alt="The Fragrance Secrets" /></a>
      <button class="nav-burger" aria-label="Menu" onclick="toggleMobileNav()"><span class="mi" aria-hidden="true">menu</span></button>
      <nav class="nav-links" id="navLinks">${links}<a href="#" class="nav-toplink nav-quiz" onclick="openAI();toggleMobileNav();return false"><span class="mi" aria-hidden="true">auto_awesome</span>Find My Scent</a><a href="${R('search.html')}" class="nav-toplink nav-drawer-extra"><span class="mi" aria-hidden="true">search</span>Search</a><a href="${R('account.html')}" class="nav-toplink nav-drawer-extra"><span class="mi" aria-hidden="true">person</span>Account</a><a href="${R('wishlist.html')}" class="nav-toplink nav-drawer-extra"><span class="mi" aria-hidden="true">favorite</span>Wishlist</a></nav>
      <div class="nav-actions">
        <a class="ni" href="search.html" title="Search"><span class="mi" aria-hidden="true">search</span></a>
        <a class="ni" href="account.html" title="Account"><span class="mi" aria-hidden="true">person</span></a>
        <a class="ni" href="wishlist.html" title="Wishlist"><span class="mi" aria-hidden="true">favorite</span></a>
        <a class="ni" href="cart.html" title="Cart">
          <span class="mi" aria-hidden="true">shopping_bag</span>
          <span class="cbadge">3</span>
        </a>
      </div>
    </div>
  </header>
  <div class="nav-overlay" id="navOverlay" onclick="toggleMobileNav()" aria-hidden="true"></div>`;
}

function footerHTML() {
  return `<footer id="site-footer">
    <div class="footer-inner">
      <div class="footer-grid">
        <div class="fg-brand">
          <span class="nav-logo"><img src="${R('assets/img/logo.png')}" alt="The Fragrance Secrets" /></span>
          <p>Your trusted destination for authentic fragrances, premium scents, and unforgettable perfume experiences across the UAE.</p>
          <a href="mailto:info@thefragrancesecrets.com" class="fg-email"><span class="mi" aria-hidden="true">mail</span>info@thefragrancesecrets.com</a>
          <div class="socials">
            <a href="#" class="soc-btn" title="Instagram" aria-label="Instagram"><svg viewBox="0 0 24 24"><rect x="2" y="2" width="20" height="20" rx="5" ry="5"/><path d="M16 11.37A4 4 0 1 1 12.63 8 4 4 0 0 1 16 11.37z"/><line x1="17.5" y1="6.5" x2="17.51" y2="6.5"/></svg></a>
            <a href="#" class="soc-btn" title="Facebook" aria-label="Facebook"><svg viewBox="0 0 24 24"><path d="M18 2h-3a5 5 0 0 0-5 5v3H7v4h3v8h4v-8h3l1-4h-4V7a1 1 0 0 1 1-1h3z"/></svg></a>
            <a href="#" class="soc-btn" title="TikTok" aria-label="TikTok"><svg viewBox="0 0 24 24"><path d="M9 12a4 4 0 1 0 4 4V4a5 5 0 0 0 5 5"/></svg></a>
            <a href="#" class="soc-btn" title="YouTube" aria-label="YouTube"><svg viewBox="0 0 24 24"><path d="M22.54 6.42a2.78 2.78 0 0 0-1.95-1.96C18.88 4 12 4 12 4s-6.88 0-8.59.46a2.78 2.78 0 0 0-1.95 1.96A29 29 0 0 0 1 12a29 29 0 0 0 .46 5.58A2.78 2.78 0 0 0 3.41 19.6C5.12 20 12 20 12 20s6.88 0 8.59-.4a2.78 2.78 0 0 0 1.95-1.95A29 29 0 0 0 23 12a29 29 0 0 0-.46-5.58z"/><polygon points="9.75 15.02 15.5 12 9.75 8.98 9.75 15.02"/></svg></a>
          </div>
        </div>
        <div class="fg-col">
          <h4>Shop</h4>
          <ul>
            <li><a href="brand-index.html#our-brands">Our Brands</a></li>
            <li><a href="brand-index.html">All Brands</a></li>
            <li><a href="collection.html?c=mens">Men's Perfumes</a></li>
            <li><a href="collection.html?c=womens">Women's Perfumes</a></li>
            <li><a href="collection.html?c=unisex">Unisex</a></li>
            <li><a href="collection.html?c=best-sellers">Best Sellers</a></li>
            <li><a href="gift-sets.html">Gift Sets</a></li>
          </ul>
        </div>
        <div class="fg-col">
          <h4>Discover</h4>
          <ul>
            <li><a href="occasions-gifts.html">Occasions &amp; Gifts</a></li>
            <li><a href="collection.html?c=discovery-kits">Discovery Kits</a></li>
            <li><a href="journal.html">Guides</a></li>
            <li><a href="find-my-scent.html">Find My Scent</a></li>
            <li><a href="product.html">Custom Mixing <span class="fg-phase">Phase 2</span></a></li>
          </ul>
        </div>
        <div class="fg-col">
          <h4>Help</h4>
          <ul>
            <li><a href="contact.html">Contact</a></li>
            <li><a href="faqs.html">FAQs</a></li>
            <li><a href="legal/shipping-policy.html">Shipping</a></li>
            <li><a href="legal/return-policy.html">Returns &amp; Refund</a></li>
            <li><a href="legal/payment-policy.html">Payment</a></li>
            <li><a href="account.html">Track Order</a></li>
          </ul>
        </div>
        <div class="fg-col">
          <h4>Company</h4>
          <ul>
            <li><a href="about.html">About</a></li>
            <li><a href="sourcing-promise.html">Sourcing Promise</a></li>
            <li><a href="reviews.html">Reviews</a></li>
            <li><a href="legal/privacy-policy.html">Privacy Policy</a></li>
            <li><a href="legal/terms.html">Terms of Service</a></li>
            <li><a href="#" onclick="openReferral();return false">Refer a Friend <span class="fg-phase">Phase 2</span></a></li>
          </ul>
        </div>
      </div>
    </div>
    <div class="footer-inner">
      <div class="footer-bottom">
        <p>© 2026 The Fragrance Secrets. All rights reserved. Dubai, UAE</p>
        <div class="pay-icons">
          <span class="pay-icon">VISA</span><span class="pay-icon">MC</span><span class="pay-icon">Apple Pay</span><span class="pay-icon">COD</span><span class="pay-icon">Tabby</span>
        </div>
      </div>
    </div>
  </footer>`;
}

function overlaysHTML() {
  return `
  <div class="wa-float" title="Chat with a human on WhatsApp" aria-label="WhatsApp support" onclick="waChat()">${WA_SVG}</div>

  <button class="ai-launcher" id="aiLauncher" title="Find My Scent — AI fragrance concierge" aria-label="Find My Scent — AI fragrance concierge" onclick="openAI()">
    <span class="ai-pulse"></span><span class="mi" aria-hidden="true">auto_awesome</span>Find My Scent
  </button>

  <div class="ai-panel" id="aiPanel" role="dialog" aria-label="AI Fragrance Concierge">
    <div class="ai-head">
      <div class="ai-head-avatar"><span class="mi" aria-hidden="true">auto_awesome</span></div>
      <div class="ai-head-txt"><h4>Find My Scent</h4><span>AI Fragrance Concierge</span></div>
      <button class="ai-close" onclick="closeAI()" aria-label="Close concierge"><span class="mi" aria-hidden="true">close</span></button>
    </div>
    <div class="ai-body" id="aiBody"></div>
    <div class="ai-escalate">
      <a href="#" onclick="waChat();return false">${WA_SVG}Talk to a human on WhatsApp</a>
    </div>
    <div class="ai-input-row">
      <input type="text" id="aiInput" placeholder="Ask anything — e.g. &ldquo;Do you have Lattafa?&rdquo;" onkeydown="if(event.key==='Enter')aiSend()"/>
      <button class="ai-send" onclick="aiSend()" aria-label="Send"><span class="mi" aria-hidden="true">send</span></button>
    </div>
  </div>

  <div class="tfs-overlay" id="refOverlay" onclick="if(event.target===this)closeReferral()">
    <div class="tfs-modal">
      <button class="tfs-close" onclick="closeReferral()" aria-label="Close"><span class="mi" aria-hidden="true">close</span></button>
      <div class="ref-modal">
        <div class="ref-icon"><span class="mi" aria-hidden="true">redeem</span></div>
        <span class="label">Refer a Friend</span>
        <h2 class="ref-title">Give AED 30,<br><em>Get AED 30</em></h2>
        <div class="ref-offer"><span class="ref-give">Both of you save AED 30</span><span class="ref-was">AED 60 value</span></div>
        <p class="ref-sub">Share your link. Your friend gets AED 30 off their first order — and you get AED 30 in store credit the moment they buy.</p>
        <div class="ref-code-row"><input type="text" id="refLink" value="thefragrancesecrets.com/r/SARA-30" readonly/><button class="ref-copy" onclick="copyRef(this)">Copy</button></div>
        <a href="#" class="ref-share" onclick="waChat();return false">${WA_SVG}Share on WhatsApp</a>
        <p class="ref-terms">Credit applied after your friend's first delivered order. T&amp;Cs apply.</p>
      </div>
    </div>
  </div>

  <div class="tfs-overlay" id="mixOverlay" onclick="if(event.target===this)closeMix()">
    <div class="tfs-modal mix-modal">
      <button class="tfs-close" onclick="closeMix()" aria-label="Close"><span class="mi" aria-hidden="true">close</span></button>
      <div class="mix-head">
        <span class="label">Personalise It</span>
        <h3>Mix It Into <em>Your Spray</em></h3>
        <p id="mixHeadSub">We blend this oil into a ready-to-wear alcohol spray, made to order just for you.</p>
        <div class="mix-prog" id="mixProg"></div>
      </div>
      <div id="mixStepArea"></div>
    </div>
  </div>`;
}

function mountChrome() {
  const b = document.body;
  const theme = b.dataset.nav === 'dark' ? 'dark' : 'light';
  const active = b.dataset.active || '';
  b.insertAdjacentHTML('afterbegin', announceHTML() + headerHTML(theme, active));
  b.insertAdjacentHTML('beforeend', footerHTML() + overlaysHTML());
  // Rewrite relative links in injected chrome so subfolder pages (e.g. /legal/) resolve to site root.
  if (BASE) {
    document.querySelectorAll('#hdr a[href], #site-footer a[href]').forEach(a => {
      const h = a.getAttribute('href');
      if (h && !/^(https?:|mailto:|tel:|#|\/)/.test(h)) a.setAttribute('href', BASE + h);
    });
  }
}

function toggleMobileNav() {
  const n = el('navLinks');
  if (!n) return;
  const open = n.classList.toggle('open');
  const o = el('navOverlay'); if (o) o.classList.toggle('open', open);
  document.body.classList.toggle('nav-open', open);
  const b = document.querySelector('.nav-burger');
  if (b) {
    b.setAttribute('aria-expanded', open ? 'true' : 'false');
    const ic = b.querySelector('.mi'); if (ic) ic.textContent = open ? 'close' : 'menu';
  }
}
function waChat() {
  if (window.WHATSAPP_NUMBER) {
    window.open('https://wa.me/' + String(window.WHATSAPP_NUMBER).replace(/[^0-9]/g, ''), '_blank');
  } else {
    toast('Opening WhatsApp chat with our team…');
  }
}

/* ═══════════════════════════════════════
   HEADER SCROLL + FADE-UP OBSERVER
═══════════════════════════════════════ */
function initHeaderScroll() {
  const hdr = el('hdr');
  if (!hdr) return;
  const onScroll = () => { hdr.classList.toggle('scrolled', window.scrollY > 60); };
  window.addEventListener('scroll', onScroll, { passive: true });
  onScroll();
}

function observeFadeUps() {
  const els = document.querySelectorAll('.fade-up:not(.visible)');
  if (!('IntersectionObserver' in window)) { els.forEach(e => e.classList.add('visible')); return; }
  const obs = new IntersectionObserver((entries) => {
    entries.forEach(e => { if (e.isIntersecting) { e.target.classList.add('visible'); obs.unobserve(e.target); } });
  }, { threshold: .1, rootMargin: '0px 0px -40px 0px' });
  els.forEach(el => obs.observe(el));
}

/* ═══════════════════════════════════════
   CART + TOAST
═══════════════════════════════════════ */
let cartCount = 0; // synced from the Liquid-rendered badge at init
function bumpCart(n) { cartCount += (n || 1); document.querySelectorAll('.cbadge').forEach(b => b.textContent = cartCount); }
function toast(msg) {
  const t = document.createElement('div');
  t.textContent = msg;
  t.style.cssText = 'position:fixed;left:50%;bottom:96px;transform:translateX(-50%) translateY(10px);background:#0D0A06;color:#E2C97E;padding:13px 22px;border-radius:6px;font-family:var(--fb);font-size:.8rem;letter-spacing:.02em;z-index:1300;box-shadow:0 12px 34px rgba(0,0,0,.34);opacity:0;transition:all .3s;max-width:90vw;text-align:center';
  document.body.appendChild(t);
  requestAnimationFrame(() => { t.style.opacity = '1'; t.style.transform = 'translateX(-50%) translateY(0)'; });
  setTimeout(() => { t.style.opacity = '0'; t.style.transform = 'translateX(-50%) translateY(10px)'; setTimeout(() => t.remove(), 350); }, 2300);
}
function addToCart(name, qty) { bumpCart(qty || 1); toast('✓ Added to cart — ' + name); }

/* Real Shopify cart add by variant id (used by the concierge and any live card).
   Falls back to the demo toast when no variant id is available. */
function addLiveToCart(variantId, name, qty) {
  if (!variantId) { addToCart(name, qty); return; }
  fetch((window.routes && window.routes.cart_add_url) || '/cart/add.js', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
    body: JSON.stringify({ items: [{ id: variantId, quantity: qty || 1 }] })
  }).then(function (r) { if (!r.ok) throw 0; return r.json(); })
    .then(function () {
      return fetch('/cart.js', { headers: { 'Accept': 'application/json' } }).then(function (r) { return r.json(); });
    })
    .then(function (c) {
      cartCount = c.item_count;
      document.querySelectorAll('.cbadge').forEach(function (b) { b.textContent = cartCount; });
      toast('✓ Added to cart — ' + name);
    })
    .catch(function () { toast('Could not add to cart — please try again'); });
}

/* Native Shopify cart line change (quantity update / remove). Posts to the
   cart change endpoint by line-item key, then reloads to re-render totals. */
function cartChangeQty(key, quantity) {
  fetch((window.routes && window.routes.cart_change_url) || '/cart/change.js', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
    body: JSON.stringify({ id: key, quantity: quantity })
  }).then(function (r) { return r.json(); })
    .then(function () { window.location.reload(); })
    .catch(function () { toast('Could not update cart'); });
}

/* ═══════════════════════════════════════
   FIND MY SCENT — QUIZ
═══════════════════════════════════════ */
const quizData = [
  { q: 'What scent family speaks to you?', opts: ['Fresh & Citrus', 'Deep Oud & Woody', 'Floral & Rose', 'Sweet & Gourmand', 'Spicy & Oriental'] },
  { q: 'How strong do you want the fragrance?', opts: ['Light & Subtle', 'Moderate & Balanced', 'Bold & Strong', 'Beast Mode — Maximum Projection'] },
  { q: 'What\'s the main occasion?', opts: ['Daily Wear', 'Work & Office', 'Evening & Dates', 'Special Events', 'Travel & Casual'] },
];
let qStep = 0, qAnswers = [];
function renderQuiz() {
  document.querySelectorAll('.quiz-progress-wrap').forEach(prog => {
    prog.innerHTML = quizData.map((_, i) => `<div class="qp-dot${i <= qStep ? ' active' : ''}"></div>`).join('');
  });
  document.querySelectorAll('.quiz-container-wrap').forEach(container => {
    if (qStep >= quizData.length) {
      container.innerHTML = `<div class="quiz-result fade-up visible">
        <h3 class="sec-title" style="color:var(--white);font-size:2rem;margin-bottom:12px">Your Perfect Match <em>Found!</em></h3>
        <p style="color:rgba(255,255,255,.55);margin-bottom:28px">Based on your answers, we've narrowed it down. Want to refine further? Ask our AI stylist anything — budget, similar scents, gifting.</p>
        <div style="display:flex;flex-wrap:wrap;gap:12px;justify-content:center;align-items:center">
          <button class="btn-g" onclick="openAIFromQuiz()"><span class="mi" aria-hidden="true">forum</span> Refine with our AI Stylist</button>
          <a class="btn-o" href="collection.html?c=best-sellers">See Recommendations</a>
          <button class="btn-o" onclick="qStep=0;qAnswers=[];renderQuiz()">Retake Quiz</button>
        </div>
      </div>`;
      return;
    }
    const q = quizData[qStep];
    container.innerHTML = `<div class="quiz-steps active fade-up visible">
      <span class="q-label">Question ${qStep + 1} of ${quizData.length}</span>
      <div class="q-title">${q.q}</div>
      <div class="q-options">${q.opts.map(o => `<button class="q-opt" onclick="selectQuiz(this,'${o.replace(/'/g, "\\'")}')">${o}</button>`).join('')}</div>
    </div>`;
  });
}
function selectQuiz(node, val) {
  document.querySelectorAll('.q-opt').forEach(x => x.classList.remove('selected'));
  node.classList.add('selected');
  qAnswers.push(val);
  setTimeout(() => { qStep++; renderQuiz(); }, 400);
}

/* ═══════════════════════════════════════
   AI FRAGRANCE CONCIERGE
═══════════════════════════════════════ */
let aiStarted = false;
function openAI() {
  const panel = el('aiPanel'); if (!panel) return;
  panel.classList.add('open');
  const l = el('aiLauncher'); if (l) l.classList.add('hidden');
  const pulse = document.querySelector('.ai-launcher .ai-pulse'); if (pulse) pulse.remove();
  if (!aiStarted) { aiStarted = true; aiWelcome(); }
  setTimeout(() => { const i = el('aiInput'); if (i) i.focus(); }, 320);
}
function closeAI() {
  const panel = el('aiPanel'); if (panel) panel.classList.remove('open');
  const l = el('aiLauncher'); if (l) l.classList.remove('hidden');
}
function aiScroll() { const b = el('aiBody'); if (b) b.scrollTop = b.scrollHeight; }
function aiPush(html, who) {
  const b = el('aiBody'); if (!b) return;
  const d = document.createElement('div');
  d.className = 'ai-msg ' + (who || 'bot');
  d.innerHTML = html;
  b.appendChild(d); aiScroll(); return d;
}
function aiChips(items) {
  const b = el('aiBody'); if (!b) return;
  const w = document.createElement('div'); w.className = 'ai-chips';
  w.innerHTML = items.map(() => `<button class="ai-chip"></button>`).join('');
  [...w.children].forEach((c, i) => { c.textContent = items[i]; c.onclick = () => aiUser(items[i]); });
  b.appendChild(w); aiScroll();
}
function aiRecCard(p) {
  const safeName = esc(p.name).replace(/'/g, "\\'");
  const go = p.url ? ` style="cursor:pointer" onclick="location.href='${p.url}'"` : '';
  return `<div class="ai-rec">
    <img src="${assetURL(p.img)}" alt="${esc(p.name)}"${go}/>
    <div class="ai-rec-info"${go}>
      <div class="ai-rec-brand">${esc(p.brand)}</div>
      <div class="ai-rec-name">${esc(p.name)}</div>
      <div class="ai-rec-price">${money(p.price)}${p.was ? ` <s>${money(p.was)}</s>` : ''}</div>
    </div>
    <button class="ai-rec-add" onclick="event.stopPropagation();addLiveToCart(${p.variantId || 0}, '${safeName}')">Add</button>
  </div>`;
}
function aiPushRec(p) { const b = el('aiBody'); if (b) { b.insertAdjacentHTML('beforeend', aiRecCard(p)); aiScroll(); } }
function aiPushAction(label, onclick) {
  const b = el('aiBody'); if (!b) return;
  b.insertAdjacentHTML('beforeend', `<button class="ai-cta" onclick="${onclick}"><span class="mi" aria-hidden="true">science</span>${label}</button>`);
  aiScroll();
}
function aiTyping(cb, delay) {
  const b = el('aiBody'); if (!b) { cb(); return; }
  const t = document.createElement('div'); t.className = 'ai-typing';
  t.innerHTML = '<span></span><span></span><span></span>';
  b.appendChild(t); aiScroll();
  setTimeout(() => { t.remove(); cb(); }, delay || 750);
}
function aiUser(text) {
  if (!text || !text.trim()) return;
  aiPush(esc(text), 'user');
  const i = el('aiInput'); if (i) i.value = '';
  aiTyping(() => aiRespond(text.toLowerCase()));
}
function aiSend() { const i = el('aiInput'); if (i) aiUser(i.value); }
function pickProducts(keys) {
  const res = products.filter(p => keys.some(k => (p.name + ' ' + p.brand).toLowerCase().includes(k.toLowerCase())));
  return (res.length ? res : products).slice(0, 3);
}
/* Live-catalogue pickers — match on the mapped family/gender/badge fields
   (set by loadLiveCatalog) rather than demo product names. */
function pickByFamily(fams) {
  let res = products.filter(p => fams.indexOf(p.family) > -1);
  if (!res.length) res = products.filter(p => p.badge === 'Bestseller');
  if (!res.length) res = products;
  return res.slice(0, 3);
}
function bestsellers(pool) {
  pool = pool || products;
  let res = pool.filter(p => p.badge === 'Bestseller');
  if (!res.length) res = pool;
  return res.slice(0, 3);
}
function flashEscalate() {
  const e = document.querySelector('.ai-escalate'); if (!e) return;
  e.style.background = 'rgba(37,211,102,.24)';
  setTimeout(() => { e.style.background = ''; }, 1000);
}
function aiWelcome() {
  aiPush("Hi! I'm your AI fragrance concierge 🌙<br>I can help you <strong>discover a scent</strong>, <strong>find a specific brand</strong>, or <strong>compare options</strong> — all 100% authentic. What are you looking for?");
  aiChips(['Find my signature scent', 'Do you have Lattafa?', 'Best oud under AED 150', 'A gift for him']);
}
function aiRespond(q) {
  if (/(authentic|fake|counterfeit|genuine|\breal\b|original|refund|return|deliver|shipping|track|where.*(order|parcel)|\bcod\b|cash on)/.test(q)) {
    aiPush("That's an important one — and because <strong>authenticity &amp; orders</strong> are where trust matters most, our human team answers these personally on WhatsApp so you get a guaranteed answer. Tap below to chat with them 👇");
    flashEscalate();
    return;
  }
  /* Custom-blend intent — the personalisation moat, surfaced here (not in the main funnel) */
  if (/custom blend|mix (my )?own|create my|make my own|my own (scent|spray|blend)|personali[sz]e|bespoke|\bblend\b/.test(q)) {
    aiPush("Amazing — a scent that exists nowhere else. Here's how it works: pick an oil, choose your <strong>strength</strong> and <strong>bottle size</strong>, and we hand-blend it into a ready-to-wear spray, made to order and dispatched in <strong>3–5 days</strong>. Tap below to start 👇");
    aiPushAction('Start My Custom Blend', 'openMix()');
    aiChips(['What does it cost?', 'Show me oils to start with', 'Maybe later']);
    return;
  }
  if (/oils? to start|show me oils|perfume oil/.test(q)) {
    aiPush("Great base oils to build a custom spray from — each blends beautifully:");
    products.filter(p => /oud|attar|rose|coffee/i.test(p.name)).slice(0, 2).forEach(aiPushRec);
    aiPushAction('Build My Custom Blend', 'openMix()');
    return;
  }
  const brandHit = brands.find(b => q.includes(b.toLowerCase()));
  if (brandHit || /do you (have|stock|carry)|in stock|available|looking for/.test(q)) {
    if (brandHit) {
      const matches = products.filter(p => p.brand.toLowerCase() === brandHit.toLowerCase());
      aiPush(`Yes — we stock <strong>${brandHit}</strong> ✦ ${matches.length ? "here are popular picks, all 100% authentic:" : "it's one of our 218+ brands. Here are similar bestsellers you'll love:"}`);
      (matches.length ? matches : products.filter(p => p.badge === 'Bestseller')).slice(0, 2).forEach(aiPushRec);
      aiChips(['Something similar but cheaper', 'For evenings', 'A gift for him']);
    } else {
      aiPush("We carry 218+ brands. Which are you after — or shall I recommend by scent?");
      aiChips(['Lattafa', 'Armaf', 'Recommend by scent']);
    }
    return;
  }
  let recs = [];
  if (/under|budget|cheap|affordable|less than|below|\bmax\b/.test(q)) {
    // Budget intent — honour a number if the visitor gave one ("under 120")
    const m = q.match(/\b(\d{2,4})\b/);
    const cap = m ? parseInt(m[1], 10) : 150;
    recs = products.filter(p => p.price > 0 && p.price <= cap).sort((a, b) => b.price - a.price).slice(0, 3);
    if (!recs.length) recs = products.slice().sort((a, b) => a.price - b.price).slice(0, 3);
  }
  else if (/oud|woody|\bwood\b/.test(q)) recs = pickByFamily(['Oud & Woody']);
  else if (/spic|oriental|amber|\bwarm\b/.test(q)) recs = pickByFamily(['Spicy & Oriental', 'Oud & Woody']);
  else if (/fresh|citrus|light|summer|clean|sport|gym/.test(q)) recs = pickByFamily(['Fresh & Citrus']);
  else if (/floral|rose|\bsoft\b/.test(q)) recs = pickByFamily(['Floral & Rose']);
  else if (/sweet|gourmand|vanilla|coffee/.test(q)) recs = pickByFamily(['Sweet & Gourmand']);
  else if (/gift|present|eid|\bhim\b|\bher\b|husband|wife|father|mother|\bdad\b|\bmom\b|brother|sister/.test(q)) {
    let pool = products;
    if (/\bhim\b|husband|father|\bdad\b|brother/.test(q)) pool = products.filter(p => p.gender === 'Men' || p.gender === 'Unisex');
    else if (/\bher\b|wife|mother|\bmom\b|sister/.test(q)) pool = products.filter(p => p.gender === 'Women' || p.gender === 'Unisex');
    recs = bestsellers(pool.length ? pool : products);
  }
  else if (/\bmen\b|masculine|for guys/.test(q)) recs = bestsellers(products.filter(p => p.gender === 'Men' || p.gender === 'Unisex'));
  else if (/women|feminine|for ladies/.test(q)) recs = bestsellers(products.filter(p => p.gender === 'Women' || p.gender === 'Unisex'));
  else if (/evening|night|date|long|last|strong|projection|beast/.test(q)) recs = pickByFamily(['Oud & Woody', 'Spicy & Oriental']);
  else if (/signature|recommend|suggest|match|best|popular|surprise|not sure|don.?t know/.test(q)) recs = bestsellers();
  if (recs.length) {
    aiPush("Based on that, here's what I'd reach for — all in stock and great value:");
    recs.forEach(aiPushRec);
    aiPush("Want me to narrow it down further?");
    aiChips(['Under AED 120', 'For evenings', 'Make it a gift']);
    return;
  }
  aiPush("I can help you <strong>discover a scent</strong>, <strong>find a brand</strong>, or <strong>compare options</strong>. Which sounds right?");
  aiChips(['Find my signature scent', 'Do you have Lattafa?', 'Best oud under AED 150', 'A gift for him']);
}
function openAIFromQuiz() {
  openAI();
  const fam = qAnswers[0], strength = qAnswers[1], occ = qAnswers[2];
  setTimeout(() => {
    aiUser(`I like ${fam ? fam.toLowerCase() : 'oud'} scents, ${strength ? strength.toLowerCase() : 'balanced'} strength, mostly for ${occ ? occ.toLowerCase() : 'daily wear'}.`);
  }, 480);
}

/* ═══ EXIT-INTENT CUSTOM-BLEND OFFER ═══
   Strategy: the custom-blend offer surfaces via the AI concierge ONLY when the
   visitor is about to leave — so it never distracts from the main sales funnel. */
let exitOffered = false;
function aiPanelOpen() { const p = el('aiPanel'); return p && p.classList.contains('open'); }
function offerCustomBlend() {
  if (exitOffered || aiPanelOpen()) return;
  exitOffered = true;
  aiStarted = true; // skip the generic welcome; lead with the exit-intent pitch
  openAI();
  setTimeout(() => {
    aiPush("Before you go — want a scent that's <strong>truly one of a kind?</strong> 🌙<br>I can hand-blend an oil into a ready-to-wear spray at your chosen strength — a signature that exists nowhere else.");
    aiChips(['✨ Create my custom blend', 'Show me best-sellers', 'No thanks, just browsing']);
  }, 360);
}
function initExitIntent() {
  if (/checkout|cart/.test(location.pathname)) return; // never interrupt the funnel
  // Desktop: cursor leaves through the top of the viewport.
  document.addEventListener('mouseout', e => {
    if (exitOffered) return;
    if (!e.relatedTarget && !e.toElement && e.clientY <= 6) offerCustomBlend();
  });
  // Mobile fallback: a decisive upward flick near the top, after some dwell time.
  let lastY = window.scrollY, dwell = false;
  setTimeout(() => { dwell = true; }, 9000);
  window.addEventListener('scroll', () => {
    if (exitOffered || !dwell) { lastY = window.scrollY; return; }
    if (window.scrollY < 140 && lastY - window.scrollY > 48) offerCustomBlend();
    lastY = window.scrollY;
  }, { passive: true });
}

/* ═══════════════════════════════════════
   MIX-YOUR-OWN-SPRAY (oil PDP)
═══════════════════════════════════════ */
const MIX = { base: 'Bouquet of Oud', step: 1, size: null, conc: null };
const MIX_SIZES = [
  { id: '50', label: '50ml Spray', price: 149, meta: 'Everyday carry · ~500 sprays' },
  { id: '100', label: '100ml Spray', price: 249, meta: 'Best value · ~1,000 sprays' },
];
const MIX_CONC = [
  { id: 'edt', label: 'Eau de Toilette', premium: 0, longevity: '4–6 hrs', sillage: 'Soft', note: 'Light & fresh' },
  { id: 'edp', label: 'Eau de Parfum', premium: 30, longevity: '7–9 hrs', sillage: 'Moderate', note: 'Our most popular' },
  { id: 'extrait', label: 'Extrait (Pure)', premium: 70, longevity: '10–14 hrs', sillage: 'Strong', note: 'Maximum depth' },
];
const arrowSVG = '<span class="mi" aria-hidden="true" style="font-size:17px">arrow_forward</span>';
function mixPrice() { return MIX.size ? MIX.size.price + (MIX.conc ? MIX.conc.premium : 0) : 0; }
function openMix(base) {
  if (base) MIX.base = base;
  MIX.step = 1; MIX.size = null; MIX.conc = null;
  const o = el('mixOverlay'); if (!o) return;
  o.classList.add('open'); document.body.style.overflow = 'hidden';
  renderMix();
}
function closeMix() { const o = el('mixOverlay'); if (o) o.classList.remove('open'); document.body.style.overflow = ''; }
function mixSelectSize(id) { MIX.size = MIX_SIZES.find(s => s.id === id); renderMix(); }
function mixSelectConc(id) { MIX.conc = MIX_CONC.find(c => c.id === id); renderMix(); }
function mixNext() { if (MIX.step < 3) { MIX.step++; renderMix(); } }
function mixBack() { if (MIX.step > 1) { MIX.step--; renderMix(); } }
function mixAddToCart() { addToCart(`${MIX.base} — Custom ${MIX.size.label}, ${MIX.conc.label}`); closeMix(); }
function renderMix() {
  const prog = el('mixProg'); if (!prog) return;
  prog.innerHTML = [1, 2, 3].map(n => `<div class="mp-dot${n <= MIX.step ? ' active' : ''}"></div>`).join('');
  const sub = el('mixHeadSub');
  const area = el('mixStepArea');
  if (MIX.step === 1) {
    sub.textContent = 'We hand-blend this oil into a ready-to-wear alcohol spray, made to order just for you.';
    area.innerHTML = `
      <div class="mix-step">
        <div class="mix-step-label">Step 1 of 3</div>
        <div class="mix-q">Choose your bottle size</div>
        <div class="mix-opts">
          ${MIX_SIZES.map(s => `<button class="mix-opt${MIX.size && MIX.size.id === s.id ? ' selected' : ''}" onclick="mixSelectSize('${s.id}')">
            <span class="mix-opt-ic"><span class="mi" aria-hidden="true">water_drop</span></span>
            <span class="mix-opt-body"><span class="mix-opt-title">${s.label}</span><span class="mix-opt-meta">${s.meta}</span></span>
            <span class="mix-opt-price">AED ${s.price}<small>from</small></span>
          </button>`).join('')}
        </div>
      </div>
      <div class="mix-foot">
        <button class="mix-next" onclick="mixNext()" ${MIX.size ? '' : 'disabled'}>Continue ${arrowSVG}</button>
      </div>`;
  } else if (MIX.step === 2) {
    sub.textContent = 'Strength sets how long it lasts and how far it projects — same scent, your intensity.';
    area.innerHTML = `
      <div class="mix-step">
        <div class="mix-step-label">Step 2 of 3</div>
        <div class="mix-q">Choose your strength</div>
        <div class="mix-opts">
          ${MIX_CONC.map(c => `<button class="mix-opt${MIX.conc && MIX.conc.id === c.id ? ' selected' : ''}" onclick="mixSelectConc('${c.id}')">
            <span class="mix-opt-ic"><span class="mi" aria-hidden="true">air</span></span>
            <span class="mix-opt-body"><span class="mix-opt-title">${c.label}</span>
              <span class="mix-opt-meta"><span><span class="mi" aria-hidden="true" style="font-size:14px;vertical-align:-3px">schedule</span> Longevity <b>${c.longevity}</b></span><span><span class="mi" aria-hidden="true" style="font-size:14px;vertical-align:-3px">air</span> Sillage <b>${c.sillage}</b></span></span>
            </span>
            <span class="mix-opt-price">${c.premium ? '+AED ' + c.premium : 'Included'}</span>
          </button>`).join('')}
        </div>
      </div>
      <div class="mix-foot">
        <button class="mix-back" onclick="mixBack()">Back</button>
        <button class="mix-next" onclick="mixNext()" ${MIX.conc ? '' : 'disabled'}>Review ${arrowSVG}</button>
      </div>`;
  } else {
    const total = mixPrice();
    sub.textContent = 'Almost there — review your custom blend.';
    area.innerHTML = `
      <div class="mix-step">
        <div class="mix-step-label">Step 3 of 3</div>
        <div class="mix-q">Your custom spray</div>
        <div class="mix-summary">
          <div class="mix-sum-row"><span>Base scent</span><b>${MIX.base}</b></div>
          <div class="mix-sum-row"><span>Bottle size</span><b>${MIX.size.label}</b></div>
          <div class="mix-sum-row"><span>Strength</span><b>${MIX.conc.label} · ${MIX.conc.longevity}</b></div>
          <div class="mix-sum-row total"><span>Total</span><b>AED ${total}</b></div>
        </div>
        <div class="mix-eta">
          <span class="mi" aria-hidden="true">schedule</span>
          <span><b>Made to order</b> — hand-blended &amp; dispatched in <b>3–5 working days</b>. We'll WhatsApp you when it ships. (In-stock bottles still arrive in 48 hrs.)</span>
        </div>
      </div>
      <div class="mix-foot">
        <button class="mix-back" onclick="mixBack()">Back</button>
        <button class="mix-next" onclick="mixAddToCart()">Add Mixed Spray — AED ${total}</button>
      </div>`;
  }
}

/* ═══════════════════════════════════════
   REFERRAL MODAL
═══════════════════════════════════════ */
function openReferral() { const o = el('refOverlay'); if (o) { o.classList.add('open'); document.body.style.overflow = 'hidden'; } }
function closeReferral() { const o = el('refOverlay'); if (o) o.classList.remove('open'); document.body.style.overflow = ''; }
function copyRef(btn) {
  const input = el('refLink'); if (!input) return;
  input.select();
  if (navigator.clipboard) navigator.clipboard.writeText(input.value).catch(() => { });
  const old = btn.textContent; btn.textContent = 'Copied!';
  setTimeout(() => { btn.textContent = old; }, 1600);
}

/* ═══════════════════════════════════════
   PDP HELPERS (product.html)
═══════════════════════════════════════ */
function switchTab(btn, id) {
  const wrap = btn.closest('.pdp-tabs, .tabbed') || document;
  wrap.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
  wrap.querySelectorAll('.tab-pane').forEach(p => p.classList.remove('active'));
  btn.classList.add('active');
  const pane = el(id); if (pane) pane.classList.add('active');
}
function changeQty(d) { const e = el('qtynum'); if (e) e.value = Math.max(1, parseInt(e.value) + d); }
/* Home featured-product gallery + quantity (ported from the index SPA). */
function swapFpImg(node, src) {
  document.querySelectorAll('.fp-thumb').forEach(t => t.classList.remove('active'));
  node.classList.add('active');
  const m = el('fp-main-img'); if (m) m.src = assetURL(src);
}
function changeFpQty(v) {
  const q = el('fp-qty'); if (!q) return;
  q.value = Math.max(1, (parseInt(q.value) || 1) + v);
}
function selectVar(btn, size, price) {
  document.querySelectorAll('.var-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  const now = document.querySelector('.pdp-price-now'); if (now) now.textContent = price;
}
/* Native Shopify variant switch — updates the product form's hidden id,
   the visible price and the sticky bar price from the button's data-*. */
function selectShopifyVariant(btn, variantId) {
  document.querySelectorAll('[data-variant-picker] .var-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  const idInput = document.querySelector('#product-form input[name="id"]');
  if (idInput) idInput.value = variantId;
  const price = btn.getAttribute('data-variant-price');
  if (price) {
    const now = document.querySelector('.pdp-price-now'); if (now) now.textContent = price;
    const mini = document.querySelector('.price-mini'); if (mini) mini.textContent = price;
  }
}
function initThumbs() {
  const list = el('thumblist'); if (!list) return;
  list.querySelectorAll('.thumb').forEach(t => {
    t.addEventListener('click', () => {
      list.querySelectorAll('.thumb').forEach(x => x.classList.remove('active'));
      t.classList.add('active');
      const main = el('mainimg'); const src = t.getAttribute('data-full');
      if (main && src) main.src = src;
    });
  });
}
function initStickyAtc() {
  const bar = el('stickyatc'); if (!bar) return;
  window.addEventListener('scroll', () => { bar.style.display = window.scrollY > 500 ? 'block' : 'none'; }, { passive: true });
}
/* Featured-product widget (home) */
function swapFpImg(node, src) {
  document.querySelectorAll('.fp-thumb').forEach(t => t.classList.remove('active'));
  node.classList.add('active');
  const m = el('fp-main-img'); if (m) m.src = src;
}
function changeFpQty(v) { const q = el('fp-qty'); if (q) { let val = parseInt(q.value) + v; if (val < 1) val = 1; q.value = val; } }

/* ═══════════════════════════════════════
   COUNTDOWN TIMER (deals)
═══════════════════════════════════════ */
function initCountdowns() {
  document.querySelectorAll('[data-countdown]').forEach(node => {
    const hrs = parseFloat(node.getAttribute('data-countdown')) || 12;
    let remaining = hrs * 3600;
    const tick = () => {
      remaining = Math.max(0, remaining - 1);
      const h = String(Math.floor(remaining / 3600)).padStart(2, '0');
      const m = String(Math.floor((remaining % 3600) / 60)).padStart(2, '0');
      const s = String(remaining % 60).padStart(2, '0');
      node.innerHTML = `<span class="cd-unit"><b>${h}</b><small>Hrs</small></span><span class="cd-sep">:</span><span class="cd-unit"><b>${m}</b><small>Min</small></span><span class="cd-sep">:</span><span class="cd-unit"><b>${s}</b><small>Sec</small></span>`;
    };
    tick();
    setInterval(tick, 1000);
  });
}

/* ═══════════════════════════════════════
   INIT
═══════════════════════════════════════ */
function initApp() {
  if (!document.body.hasAttribute('data-no-chrome')) mountChrome();
  // Sync the JS cart counter with the Liquid-rendered badge (real cart count)
  const badge = document.querySelector('.cbadge');
  if (badge) cartCount = parseInt(badge.textContent, 10) || 0;
  loadLiveCatalog();
  hydrateRenderables();
  initHeaderScroll();
  initThumbs();
  initStickyAtc();
  initCountdowns();
  initExitIntent();
  document.querySelectorAll('.quiz-container-wrap').length && renderQuiz();
  observeFadeUps();
  // Collection engine, if present on this page
  if (typeof renderCollection === 'function' && document.querySelector('[data-collection]')) renderCollection();
  // Standalone combo builder (e.g. gift-sets.html) — collection pages handle their own combo
  if (typeof renderComboGrid === 'function' && document.getElementById('comboGrid') && !document.querySelector('[data-collection]')) renderComboGrid();
  observeFadeUps();
}
document.addEventListener('keydown', e => { if (e.key === 'Escape') { closeAI(); closeMix(); closeReferral(); } });
// Defer to DOMContentLoaded so a later <script> (e.g. collections.js) is parsed
// and its globals (renderCollection, COLLECTIONS) are available before initApp runs.
if (document.readyState === 'complete') initApp();
else document.addEventListener('DOMContentLoaded', initApp);
