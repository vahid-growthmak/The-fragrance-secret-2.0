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

/* Formats cents through the store's own money_format, so JS-rebuilt prices match
   the ones Liquid rendered. Covers the four placeholder forms Shopify allows. */
function formatMoney(cents) {
  var fmt = window.MONEY_FORMAT || '{{amount}}';
  var n = (cents || 0) / 100;
  function group(v, dec) {
    var parts = v.toFixed(dec).split('.');
    parts[0] = parts[0].replace(/\B(?=(\d{3})+(?!\d))/g, ',');
    return parts.join('.');
  }
  return fmt.replace(/\{\{\s*(\w+)\s*\}\}/g, function (_, name) {
    switch (name) {
      case 'amount_no_decimals': return group(n, 0);
      case 'amount_with_comma_separator': return group(n, 2).replace(/,/g, ' ').replace('.', ',');
      case 'amount_no_decimals_with_comma_separator': return group(n, 0).replace(/,/g, ' ');
      default: return group(n, 2);
    }
  });
}
window.formatMoney = formatMoney;
function savePct(price, was) { return Math.round((1 - price / was) * 100); }
/* Struck-through price + "Save N%", only for a real markdown. Live products with
   no compare-at price come through as 0, which printed "AED 0 · Save -Infinity%". */
function wasPriceHTML(price, was) {
  if (!(was > price)) return '';
  return `<span class="price-was">${money(was)}</span><span class="price-save">Save ${savePct(price, was)}%</span>`;
}
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
/* Bucket any family-* tag (the catalogue has 144 distinct slugs) into the
   five broad families the concierge and quiz reason about. */
function familyBucket(tag) {
  const t = String(tag).replace(/^family-/, '');
  if (/oud/.test(t)) return 'Oud & Woody';
  if (/floral|rose|jasmine/.test(t)) return 'Floral & Rose';
  if (/gourmand|sweet|vanilla|coffee/.test(t)) return 'Sweet & Gourmand';
  if (/fresh|citrus|aquatic|green|fruity|clean/.test(t)) return 'Fresh & Citrus';
  if (/spicy|oriental|amber|tobacco|leather|saffron|incense|musk/.test(t)) return 'Spicy & Oriental';
  if (/woody|wood|smoky|earthy|creamy|aromatic|chypre/.test(t)) return 'Oud & Woody';
  return '';
}
/* The live catalogue feeds exactly one thing: the [data-render] grids that
   hydrateRenderables() fills. Nothing else on the site reads `products` or
   `brands`.

   It was fetched on every page regardless. On the home page — which has no
   [data-render] hook at all — that is /products.json?limit=250 arriving 1.4s
   in and 65 KB wide, the longest chain in the critical path, for a list
   nothing on the page displays. Worse on a template that does need it: the
   fetch paginates, so a 1,400-product catalogue is six round trips in series.

   Asking the DOM what this page actually renders costs one querySelector. */
function needsLiveCatalog() {
  return !!document.querySelector(
    '[data-render="products"],[data-render="brands"],[data-render="brand-track"]'
  );
}

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
          if (!family && t.indexOf('family-') === 0) family = familyBucket(t);
          if (t === 'mens') gender = 'Men';
          if (t === 'womens') gender = 'Women';
          if (t === 'kids') gender = 'Kids';
        });
        if (tags.indexOf('bestseller') > -1) { badge = 'Bestseller'; badgeClass = 'badge-best'; }
        else if (tags.indexOf('new-arrival') > -1) { badge = 'New'; badgeClass = 'badge-new'; }
        else if (tags.indexOf('sale') > -1) { badge = 'Sale'; badgeClass = 'badge-sale'; }
        /* Quote the cheapest sellable variant, not variants[0]. On the oils
           that ladder 100g → 1kg the first variant is the 1kg, so the card
           advertised the dearest size while the Liquid cards next to it
           quoted the range's low end. */
        var all = (p.variants || []).filter(function (x) { return x && x.price != null; });
        var live = all.filter(function (x) { return x.available; });
        var cheapest = (live.length ? live : all).slice().sort(function (a, b) {
          return parseFloat(a.price) - parseFloat(b.price);
        })[0] || v;
        return {
          id: p.id, brand: p.vendor || '', name: p.title || '',
          price: parseFloat(cheapest.price) || 0,
          was: parseFloat(cheapest.compare_at_price) || 0,
          multi: all.length > 1,
          badge: badge, badgeClass: badgeClass,
          rating: 4.8, reviews: 0,
          family: family, gender: gender, occasion: '',
          img: (p.images && p.images[0] && p.images[0].src) || '',
          img2: (p.images && p.images[1] && p.images[1].src) || '',   // hover image
          url: '/products/' + p.handle,
          handle: p.handle,          // wishlist keys off the handle
          variantId: cheapest.id || v.id,
        };
      }).filter(function (p) { return p.name && p.variantId; }); // price may be 0 pre-launch
      if (live.length) {
        products.length = 0;
        Array.prototype.push.apply(products, live);
        // Teach the concierge any live vendor it doesn't already know
        var known = {};
        brands.forEach(function (b) { known[b.toLowerCase()] = 1; });
        live.forEach(function (p) {
          var b = (p.brand || '').trim();
          // skip junk vendor names ("Gift", "Valentine's Day Offer") — they'd
          // hijack brand matching in the concierge ("a gift for him" -> brand "Gift")
          if (/offer|deal|^gift$/i.test(b)) return;
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
  return `<div class="prod-card fade-up">
    <div class="prod-img-wrap">
      <img class="prod-img" src="${assetURL(p.img)}" alt="${esc(p.name)}" loading="lazy"/>
      ${p.img2 ? `<img class="prod-img prod-img-hover" src="${assetURL(p.img2)}" alt="" aria-hidden="true" loading="lazy"/>` : ''}
      ${p.badge ? `<div class="prod-badge ${p.badgeClass}">${p.badge}</div>` : ''}
      <div class="prod-actions">
        <button type="button" class="pa-btn pa-wish" data-wish="${esc(p.handle || '')}" data-wish-label="${esc(p.name)}" aria-pressed="false" title="Save to wishlist" onclick="event.stopPropagation();TFSWishlist.toggle(this.dataset.wish, this.dataset.wishLabel)"><span class="mi" aria-hidden="true">favorite</span></button>
        ${p.multi
      /* A multi-size product has nothing to quick-add: the size is the
         customer's choice, so the button goes to the picker on the PDP. */
      ? `<a class="pa-btn quick-add" href="${p.url || R('product.html')}" onclick="event.stopPropagation()"><span class="mi" aria-hidden="true">shopping_bag</span>Choose Size</a>`
      : `<button class="pa-btn quick-add" onclick="event.stopPropagation();addLiveToCart(${p.variantId || 0}, '${esc(p.name).replace(/'/g, "\\'")}')"><span class="mi" aria-hidden="true">shopping_bag</span>Quick Add</button>`}
      </div>
    </div>
    <div class="prod-info">
      <div class="prod-brand">${esc(p.brand)}</div>
      <div class="prod-name"><a class="prod-link" href="${p.url || R('product.html')}">${esc(p.name)}</a></div>
      <div class="prod-rating"><div class="stars">${starsHTML(p.rating)}</div><span>(${p.reviews.toLocaleString()})</span></div>
      <div class="prod-price">${p.multi ? '<span class="price-from">From</span>' : ''}<span class="price-now">${money(p.price)}</span>${wasPriceHTML(p.price, p.was)}</div>
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
  return `<div class="prod-card fade-up">
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
      <div class="prod-name"><a class="prod-link" href="${R('product.html')}">${esc(k.name)}</a></div>
      <div class="prod-rating"><div class="stars">${starsHTML(k.rating)}</div><span>(${k.reviews.toLocaleString()})</span></div>
      <div class="prod-price"><span class="price-from">From</span><span class="price-now">${money(k.price)}</span>${wasPriceHTML(k.price, k.was)}</div>
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
  });
  /* Cards injected here miss wishlist.js's own load-time pass, so repaint the
     saved state for anything that just appeared. */
  if (window.TFSWishlist) window.TFSWishlist.sync();
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
  'Complimentary delivery anywhere in the UAE on orders above AED ' + (window.FREE_SHIPPING_THRESHOLD || 250),
  'Every fragrance is 100% authentic with fully verified sourcing',
  'Cash on delivery available across all Emirates for easy shopping',
  'Explore 218+ fragrance houses trusted by perfume lovers in the UAE',
  'Need assistance? Connect with our WhatsApp team daily from 10am to 7pm',
];

/* Buy-led, Shop-dominant nav (strategy Decision 3) */
const NAV_LINKS = [
  { label: 'Shop', href: 'collection.html?c=all', key: 'shop', mega: true },
  { label: 'Brands', href: 'brand-index.html', key: 'brands' },
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
      <nav class="nav-links" id="navLinks">${links}<a href="#" class="nav-toplink nav-quiz" onclick="openAI();closeMobileNav();return false"><span class="mi" aria-hidden="true">auto_awesome</span>Find My Scent</a><a href="${R('search.html')}" class="nav-toplink nav-drawer-extra"><span class="mi" aria-hidden="true">search</span>Search</a><a href="${R('account.html')}" class="nav-toplink nav-drawer-extra"><span class="mi" aria-hidden="true">person</span>Account</a><a href="${R('wishlist.html')}" class="nav-toplink nav-drawer-extra"><span class="mi" aria-hidden="true">favorite</span>Wishlist</a></nav>
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
          <h2>Shop</h2>
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
          <h2>Discover</h2>
          <ul>
            <li><a href="journal.html">Guides</a></li>
            <li><a href="find-my-scent.html">Find My Scent</a></li>
            <li><a href="product.html">Custom Mixing <span class="fg-phase">Phase 2</span></a></li>
          </ul>
        </div>
        <div class="fg-col">
          <h2>Help</h2>
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
          <h2>Company</h2>
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

/* The float is a real control, not a div with an onclick: a div takes no
   focus and carries no role, so a keyboard could not reach it and an ARIA
   label was not allowed on it. sections/overlays.liquid renders the same
   thing for the live theme — this copy only runs for a page that mounts its
   chrome from JS, and the two are kept in step. */
function waFloatHTML() {
  const digits = String(window.WHATSAPP_NUMBER || '').replace(/[^0-9]/g, '');
  const attrs = 'class="wa-float" title="Chat with a human on WhatsApp" aria-label="WhatsApp support"';
  return digits
    ? `<a ${attrs} href="https://wa.me/${digits}" target="_blank" rel="noopener">${WA_SVG}</a>`
    : `<button type="button" ${attrs} onclick="waChat()">${WA_SVG}</button>`;
}

function overlaysHTML() {
  return `
  ${waFloatHTML()}

  <div class="tfs-overlay" id="refOverlay" onclick="if(event.target===this)closeReferral()">
    <div class="tfs-modal">
      <button class="tfs-close" onclick="closeReferral()" aria-label="Close"><span class="mi" aria-hidden="true">close</span></button>
      <div class="ref-modal">
        <div class="ref-icon"><span class="mi" aria-hidden="true">redeem</span></div>
        <span class="label">Refer a Friend</span>
        <h2 class="ref-title">Give AED 30,<br><em>Get AED 30</em></h2>
        <div class="ref-offer"><span class="ref-give">Both of you save AED 30</span><span class="ref-was">AED 60 value</span></div>
        <p class="ref-sub">Share your link. Your friend gets AED 30 off their first order — and you get AED 30 in store credit the moment they buy.</p>
        <div class="ref-code-row"><input type="text" id="refLink" aria-label="Your referral link" value="thefragrancesecrets.com/r/SARA-30" readonly/><button class="ref-copy" onclick="copyRef(this)">Copy</button></div>
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

/* Close-only companion to toggleMobileNav. The Find My Scent link used to call
   the toggle, which on desktop — where the drawer is never open — opened it
   instead, leaving the blurred overlay and the body scroll lock in place with no
   way to clear them. */
function closeMobileNav() {
  const n = el('navLinks');
  if (n && n.classList.contains('open')) toggleMobileNav();
}

/* Mobile nav accordions. The mega-menu is a five-column grid on desktop; in
   the drawer it used to render every column expanded, which is why the menu
   was an unbroken list of ~40 links. Each column heading now toggles its own
   group, and Shop toggles the whole mega. Desktop is untouched — these only
   bind below the drawer breakpoint. */
function toggleNavGroup(node, event) {
  if (window.innerWidth > 1024) return;          // desktop hover menu, leave it
  if (event && event.target.closest('a')) return; // let the heading's own link work
  if (event) event.preventDefault();
  node.classList.toggle('open');
}

function toggleShopGroup(node, event) {
  if (window.innerWidth > 1024) return;
  if (event) event.preventDefault();
  node.closest('.nav-item').classList.toggle('open');
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

/* The legal pages' "On This Page" rail.

   Their text now comes from Settings › Policies, and admin HTML carries no
   anchors — the merchant writes headings, not ids. So the rail is built from
   whatever headings arrive: ids are added where missing, links are generated
   in document order, and the aside stays hidden if the policy has no headings
   at all rather than leaving an empty rail pinned beside the text. */
function initLegalToc() {
  const nav = document.querySelector('[data-legal-toc]');
  const body = document.querySelector('[data-legal-body]');
  if (!nav || !body) return;

  /* The five documents disagree about heading levels, because five different
     people typed them into admin: the privacy policy and the terms put their
     sections at h1, shipping and payment at h2, and the refund policy has
     seven sections at h2 with a single stray h1 at the end. The theme is not
     going to rewrite anyone's legal text, so it works out which level this
     document means by "section" and shifts everything to match — leaving the
     page with exactly one h1, its own title in the hero.

     Whichever level is more numerous wins. When h1 is the section level the
     whole document shifts down one, so sub-headings stay a step below their
     section; when h2 is, only the strays move, joining the sections they read
     as peers of. Deepest first, or a heading demoted twice would land two
     levels down. */
  const demote = (tags) => tags.forEach((tag) => {
    body.querySelectorAll(tag).forEach((el) => {
      const next = document.createElement('h' + (Number(tag[1]) + 1));
      next.innerHTML = el.innerHTML;
      if (el.id) next.id = el.id;
      el.replaceWith(next);
    });
  });

  const tops = body.querySelectorAll('h1').length;
  if (tops) demote(tops >= body.querySelectorAll('h2').length ? ['h3', 'h2', 'h1'] : ['h1']);

  const heads = body.querySelectorAll('h2');
  if (!heads.length) return;

  const used = {};
  heads.forEach((h, i) => {
    if (!h.id) {
      /* Slug from the heading's own words, so the URL a reader copies still
         says what it points at. Deduped, because "Contact Us" appears twice
         in more than one of these documents. */
      let slug = (h.textContent || '').toLowerCase().trim()
        .replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '').slice(0, 60) || ('section-' + i);
      if (used[slug]) slug += '-' + (++used[slug]);
      else used[slug] = 1;
      h.id = slug;
    }
    const a = document.createElement('a');
    a.href = '#' + h.id;
    a.textContent = h.textContent;
    nav.appendChild(a);
  });

  nav.hidden = false;
}

/* ═══════════════════════════════════════
   HEADER SEARCH + PREDICTIVE SUGGESTIONS
═══════════════════════════════════════ */
/* The search icon used to leave for /search on the first click, which made
   every search a page load before a single character was typed. It now opens
   a panel in the header and suggests as you type; the search page is reached
   only by a real search — Enter, the See-all row, or picking a suggestion.

   Suggestions are rendered by Shopify (sections/predictive-search.liquid) and
   dropped in as HTML, so prices come out of the same money filter as the rest
   of the site rather than being formatted by hand here.

   Works on any form marked [data-predictive-search], which is both this panel
   and the search page's own field. */
function initSearchSuggest() {
  const panel = document.getElementById('hdrSearch');
  const toggles = [...document.querySelectorAll('[data-search-toggle]')];
  /* The header icon is the one that reports state; the drawer's link is a
     second way in, not a second combobox. */
  const toggle = toggles.find((t) => t.classList.contains('ni')) || toggles[0];

  function openPanel() {
    if (!panel) return;
    panel.hidden = false;
    if (toggle) toggle.setAttribute('aria-expanded', 'true');
    const input = panel.querySelector('[data-search-input]');
    if (input) input.focus();
  }

  function closePanel() {
    if (!panel || panel.hidden) return;
    panel.hidden = true;
    if (toggle) toggle.setAttribute('aria-expanded', 'false');
    const results = panel.querySelector('[data-search-results]');
    if (results) results.innerHTML = '';
  }

  if (toggles.length && panel) {
    toggles.forEach((t) => t.addEventListener('click', (e) => {
      e.preventDefault();
      /* Opened from inside the mobile drawer, the panel would be behind it. */
      if (t.classList.contains('nav-drawer-extra') && typeof closeMobileNav === 'function') {
        closeMobileNav();
      }
      if (panel.hidden) openPanel(); else closePanel();
    }));
    /* A click anywhere outside closes it, but not one inside — the panel
       contains links, and mousedown on a link must not remove it before the
       click lands. */
    document.addEventListener('mousedown', (e) => {
      if (panel.hidden) return;
      if (panel.contains(e.target)) return;
      if (toggles.some((t) => t.contains(e.target))) return;
      closePanel();
    });
    const closeBtn = panel.querySelector('[data-search-close]');
    if (closeBtn) closeBtn.addEventListener('click', closePanel);
  }

  document.querySelectorAll('[data-predictive-search]').forEach((form) => {
    const input = form.querySelector('[data-search-input]') || form.querySelector('input[name="q"]');
    if (!input) return;
    const results = (form.closest('#hdrSearch') || form.parentElement)
      .querySelector('[data-search-results]') || form.parentElement.querySelector('[data-search-results]');
    const status = (form.closest('#hdrSearch') || document).querySelector('[data-search-status]');
    if (!results) return;

    const base = (window.routes && window.routes.predictive_search_url) || '/search/suggest';
    let timer = null, inflight = null, lastTerm = '';

    const options = () => [...results.querySelectorAll('[role="option"]')];

    function clearSelection() {
      options().forEach((o) => o.setAttribute('aria-selected', 'false'));
      input.removeAttribute('aria-activedescendant');
    }

    function select(index) {
      const rows = options();
      if (!rows.length) return;
      /* Wrap at both ends: arrowing down past the last row returns to the
         first, which is what a shopper flicking through six results expects. */
      const at = ((index % rows.length) + rows.length) % rows.length;
      rows.forEach((o, i) => o.setAttribute('aria-selected', i === at ? 'true' : 'false'));
      input.setAttribute('aria-activedescendant', rows[at].id);
      rows[at].scrollIntoView({ block: 'nearest' });
    }

    function selectedIndex() {
      return options().findIndex((o) => o.getAttribute('aria-selected') === 'true');
    }

    function render(html) {
      results.innerHTML = html;
      const count = options().length;
      input.setAttribute('aria-expanded', count ? 'true' : 'false');
      if (status) {
        status.textContent = count
          ? count + ' suggestion' + (count === 1 ? '' : 's') + ' available'
          : 'No suggestions';
      }
    }

    function suggest(term) {
      /* One character matches most of the catalogue and tells the shopper
         nothing, so wait for two. */
      if (term.length < 2) {
        render('');
        return;
      }
      if (term === lastTerm) return;
      lastTerm = term;

      if (inflight) inflight.abort();
      inflight = new AbortController();
      const url = base + '?q=' + encodeURIComponent(term) +
        '&resources[type]=product,collection,query&resources[limit]=6' +
        '&section_id=predictive-search';

      fetch(url, { signal: inflight.signal, headers: { 'Accept': 'text/html' } })
        .then((r) => (r.ok ? r.text() : Promise.reject(r.status)))
        .then((html) => {
          /* The section comes back wrapped in Shopify's section div; take the
             part we rendered and leave the wrapper behind. */
          const doc = new DOMParser().parseFromString(html, 'text/html');
          const body = doc.querySelector('.ps-results, .ps-empty');
          render(body ? body.outerHTML : '');
        })
        .catch((err) => {
          if (err && err.name === 'AbortError') return;
          /* A failed suggestion must not break searching: the form still
             submits, so say nothing and let Enter do its job. */
          render('');
        });
    }

    input.addEventListener('input', () => {
      const term = input.value.trim();
      clearTimeout(timer);
      timer = setTimeout(() => suggest(term), 220);
    });

    input.addEventListener('keydown', (e) => {
      const rows = options();
      if (e.key === 'ArrowDown' && rows.length) {
        e.preventDefault(); select(selectedIndex() + 1);
      } else if (e.key === 'ArrowUp' && rows.length) {
        e.preventDefault(); select(selectedIndex() - 1);
      } else if (e.key === 'Enter') {
        /* A highlighted suggestion wins; otherwise the form submits and the
           search page opens, which is the only time we leave. */
        const at = selectedIndex();
        if (at > -1) { e.preventDefault(); rows[at].click(); }
      } else if (e.key === 'Escape') {
        /* type="search" empties itself on Escape in Chrome and Safari, which
           threw away the term along with the list — press Escape to dismiss
           the suggestions and Enter no longer had anything to search. The
           first Escape closes the list and keeps the text; a second closes
           the panel. */
        e.preventDefault();
        if (rows.length) { render(''); clearSelection(); }
        else if (panel && !panel.hidden) closePanel();
      }
    });

    /* Never submit an empty search: it lands on a page listing nothing. */
    form.addEventListener('submit', (e) => {
      if (!input.value.trim()) e.preventDefault();
    });
  });
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
/* Fallback for callers that have no variant id and so cannot reach the real
   cart. It deliberately does NOT move the badge: incrementing a counter while
   Shopify's cart stayed empty is exactly what made Quick Add look like it had
   worked. Anything with a variant id should call addLiveToCart instead. */
function addToCart(name) {
  toast('Open the product page to add ' + name + ' to your cart');
}

/* Real Shopify cart add by variant id (used by the concierge and any live card).
   Falls back to the demo toast when no variant id is available. */
function addLiveToCart(variantId, name, qty, properties) {
  if (!variantId) { addToCart(name, qty); return; }
  const item = { id: variantId, quantity: qty || 1 };
  /* Line-item properties ride along to the order and show on the cart line.
     Optional, so every existing caller is unaffected. */
  if (properties && Object.keys(properties).length) item.properties = properties;
  /* Quick Add and the concierge go through the drawer as well, so every add on
     the site ends in the same place instead of only the product form doing so. */
  if (typeof window.cartDrawerAdd === 'function' && document.getElementById('cartDrawer')) {
    window.cartDrawerAdd([item]);
    return;
  }
  fetch((window.routes && window.routes.cart_add_url) || '/cart/add.js', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
    body: JSON.stringify({ items: [item] })
  }).then(function (r) { if (!r.ok) throw 0; return r.json(); })
    .then(function () {
      return fetch('/cart.js', { headers: { 'Accept': 'application/json' } }).then(function (r) { return r.json(); });
    })
    .then(function (c) {
      cartCount = c.item_count;
      document.querySelectorAll('.cbadge').forEach(function (b) { b.textContent = cartCount; });
      toast('✓ Added to cart — ' + name);
      /* The cart page listens for this so an add from its own cross-sell
         updates the lines above, instead of only moving the badge. */
      document.dispatchEvent(new CustomEvent('cart:updated', { detail: c }));
    })
    .catch(function () { toast('Could not add to cart — please try again'); });
}

/* Native Shopify cart line change by line-item key.

   The cart page no longer uses this — it updates the row, the totals and the
   free-delivery bar in place from the response instead, so changing a quantity
   does not throw the whole page away. Kept as a null-safe fallback for any
   caller that has no UI to update; it still reloads, which is correct when
   there is nothing else to repaint. */
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
   JUDGE.ME MODAL STATE
   The "Write a review" form opens in Judge.me's own modal, which does not lock
   the page behind it. On a phone that leaves two scrollbars — the modal's and
   the document's — and the floating buttons sit half-under the overlay, which
   reads as the WhatsApp icon vanishing.

   Judge.me gives us no open/close event, so watch the DOM for its modal and
   mirror the state onto <body>. Everything visual is then CSS, and the floats
   are guaranteed to come back when the modal closes.
═══════════════════════════════════════ */
(function () {
  if (!window.MutationObserver) return;
  var SEL = '.jdgm-modal, .jdgm-rev-modal, .jdgm-form-modal, [class*="jdgm"][class*="modal"]';

  /* Being merely present and not display:none was far too loose a test. SEL ends
     in [class*="jdgm"][class*="modal"], which matches any Judge.me element whose
     class list contains both substrings — and the review widget renders its
     modal scaffolding inline on the product page, closed. So on every PDP the
     check returned true, jdgm-modal-open latched onto <body> permanently, and
     the rule in pages.css took the WhatsApp float and the sticky Add to Cart to
     opacity:0 / pointer-events:none for the whole visit. Nothing ever cleared
     it, because the element it tripped on never went away.

     A real open modal is an overlay: taken out of flow, sizeable, and actually
     on screen. Requiring all three keeps the scaffolding from counting.

     Deliberately biased toward "closed". A false positive costs the two floats
     for the entire session; a false negative merely leaves them visible over a
     modal for a moment. */
  function isOpen() {
    var nodes = document.querySelectorAll(SEL);
    var vw = window.innerWidth, vh = window.innerHeight;
    for (var i = 0; i < nodes.length; i++) {
      var el = nodes[i];
      var cs = window.getComputedStyle(el);
      if (cs.display === 'none' || cs.visibility === 'hidden' || parseFloat(cs.opacity) === 0) continue;
      if (cs.position !== 'fixed' && cs.position !== 'absolute') continue;
      var r = el.getBoundingClientRect();
      if (r.width < 200 || r.height < 200) continue;
      // must actually intersect the viewport, not sit parked off-screen
      if (r.bottom <= 0 || r.top >= vh || r.right <= 0 || r.left >= vw) continue;
      return true;
    }
    return false;
  }

  var last = false, queued = false;
  function apply() {
    queued = false;
    var open = isOpen();
    if (open === last) return;
    last = open;
    document.body.classList.toggle('jdgm-modal-open', open);
  }
  /* Coalesce to one check per frame — the observer watches the whole subtree
     and Judge.me mutates it heavily while the form renders. */
  function schedule() {
    if (queued) return;
    queued = true;
    requestAnimationFrame(apply);
  }

  function start() {
    new MutationObserver(schedule).observe(document.body, {
      childList: true, subtree: true, attributes: true, attributeFilter: ['class', 'style']
    });
    apply();
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start);
  else start();
})();

/* ═══════════════════════════════════════
   FIND MY SCENT — QUIZ
═══════════════════════════════════════ */
const quizData = [
  { q: 'What scent family speaks to you?', opts: ['Fresh & Citrus', 'Deep Oud & Woody', 'Floral & Rose', 'Sweet & Gourmand', 'Spicy & Oriental'] },
  { q: 'How strong do you want the fragrance?', opts: ['Light & Subtle', 'Moderate & Balanced', 'Bold & Strong', 'Beast Mode — Maximum Projection'] },
  { q: 'What\'s the main occasion?', opts: ['Daily Wear', 'Work & Office', 'Evening & Dates', 'Special Events', 'Travel & Casual'] },
];
let qStep = 0, qAnswers = [];
/* The quiz's first answer is a scent family, and each one is a real collection
   — so the result can send people somewhere specific instead of a generic list.
   Falls back to best sellers if the answer is ever unrecognised. */
const QUIZ_FAMILY_URL = {
  'Fresh & Citrus': '/collections/fresh-citrus-perfumes',
  'Deep Oud & Woody': '/collections/oud-woody-perfumes',
  'Floral & Rose': '/collections/floral-rose-perfumes',
  'Sweet & Gourmand': '/collections/sweet-gourmand-perfumes',
  'Spicy & Oriental': '/collections/spicy-oriental-perfumes',
};
function quizResultURL() {
  return QUIZ_FAMILY_URL[qAnswers[0]] || '/collections/best-sellers';
}

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
          <a class="btn-o" href="${quizResultURL()}">See Recommendations</a>
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
   FIND MY SCENT → CHAT APP BRIDGE
   The in-theme concierge was removed; chat is handled by the Chizy AI chatbot
   app, which injects its own launcher. Every "Find My Scent" action in the
   theme calls openAI(), so this one function decides what that means: open the
   chat app when it is on the page, otherwise fall back to the quiz page.
═══════════════════════════════════════ */
const FIND_MY_SCENT_URL = '/pages/find-my-scent';

/* Chat itself is the Chizy app's own bubble, which it renders and controls. The
   theme does not hide, move or click it — earlier attempts to drive it from here
   guessed at its markup and left nothing openable. So openAI() only handles the
   theme's own "Find My Scent" actions: use a public API if the app exposes one,
   otherwise send the visitor to the quiz page, which always works. */
function chatApi() {
  const api = window.Chizy || window.chizy || window.ChizyChat || window.ChizyWidget;
  if (api && typeof api.open === 'function') return () => api.open();
  if (api && typeof api.toggle === 'function') return () => api.toggle();
  return null;
}

/* The app mounts into #chizy-chat-root and renders its own launcher inside.
   An earlier attempt to drive the bubble guessed at class names and opened
   nothing, so this does not assume any: it takes the first genuinely
   clickable node within the app's own root (shadow DOM included, since the
   widget may be encapsulated) and clicks that. If the root is absent or holds
   nothing clickable, the caller falls through to the quiz page. */
function chatLauncher() {
  const root = document.getElementById('chizy-chat-root');
  if (!root) return null;
  const scopes = [root];
  if (root.shadowRoot) scopes.push(root.shadowRoot);
  const sel = 'button, [role="button"], a[href="#"], .chizy-chat-logo-default';
  for (const scope of scopes) {
    const hit = scope.querySelector(sel);
    if (hit) return hit.closest('button, [role="button"], a') || hit;
  }
  return null;
}

function openAI() {
  const open = chatApi();
  if (open) { open(); return; }
  const launcher = chatLauncher();
  if (launcher) { launcher.click(); return; }
  if (location.pathname !== FIND_MY_SCENT_URL) location.href = FIND_MY_SCENT_URL;
}
function closeAI() { /* the chat app owns its own close control */ }
function openAIFromQuiz() { openAI(); }

/* ═══════════════════════════════════════
   MIX-YOUR-OWN-SPRAY (oil PDP)
═══════════════════════════════════════ */
const MIX = { base: 'Bouquet of Oud', step: 1, size: null, conc: null };
/* `opt` is the option value on the Shopify product (Size / Strength) and is
   what these rows are matched to a variant by. The copy beside it is the
   theme's; the money is not. */
const MIX_SIZES = [
  { id: '50', opt: '50ml', label: '50ml Spray', meta: 'Everyday carry · ~500 sprays' },
  { id: '100', opt: '100ml', label: '100ml Spray', meta: 'Best value · ~1,000 sprays' },
];
const MIX_CONC = [
  { id: 'edt', opt: 'Eau de Toilette', label: 'Eau de Toilette', longevity: '4–6 hrs', sillage: 'Soft', note: 'Light & fresh' },
  { id: 'edp', opt: 'Eau de Parfum', label: 'Eau de Parfum', longevity: '7–9 hrs', sillage: 'Moderate', note: 'Our most popular' },
  { id: 'extrait', opt: 'Extrait', label: 'Extrait', longevity: '10–14 hrs', sillage: 'Strong', note: 'Maximum depth' },
];
const arrowSVG = '<span class="mi" aria-hidden="true" style="font-size:17px">arrow_forward</span>';

/* Every price in this wizard comes from the Custom Mixed Spray product, which
   sections/overlays.liquid writes into window.MIX_PRODUCT. It used to quote
   numbers held in this file, which would have been a storefront and a cart
   disagreeing about the total the moment anyone edited a price in admin —
   and there was no product to disagree with anyway: the last step called
   addToCart(), the demo stub, and added nothing at all.

   No product, no variants, nothing to sell: the PDP button is not rendered in
   that case either, so this only has to fail quietly. */
function mixVariants() { return (window.MIX_PRODUCT && window.MIX_PRODUCT.variants) || []; }
function mixFind(sizeOpt, concOpt) {
  return mixVariants().find(v => v.size === sizeOpt && v.strength === concOpt) || null;
}
function mixVariant() { return MIX.size && MIX.conc ? mixFind(MIX.size.opt, MIX.conc.opt) : null; }
function mixPrice() { const v = mixVariant(); return v ? v.price : 0; }
/* The cheapest strength in a size, for the "from" price on step 1. */
function mixSizeFrom(sizeOpt) {
  const prices = mixVariants().filter(v => v.size === sizeOpt).map(v => v.price);
  return prices.length ? Math.min.apply(null, prices) : 0;
}
/* What a strength adds at the size already chosen, for step 2. Derived rather
   than stored, so a price change in admin moves the premium with it. */
function mixConcPremium(concOpt) {
  if (!MIX.size) return 0;
  const v = mixFind(MIX.size.opt, concOpt);
  return v ? v.price - mixSizeFrom(MIX.size.opt) : 0;
}
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
function mixAddToCart() {
  const v = mixVariant();
  if (!v || !v.available) { toast('That combination is unavailable — please pick another'); return; }
  /* The base scent is a line-item property, not a variant. Any of the 140 oils
     and attars that show the button can be one, and six sizes across all of
     them is 840 variants. As a property it travels onto the order, which is
     where whoever blends it needs to read it. */
  addLiveToCart(v.id, `${MIX.base} — ${MIX.size.label}, ${MIX.conc.label}`, 1,
    { 'Base scent': MIX.base, 'Blend': `${MIX.size.label} · ${MIX.conc.label}` });
  closeMix();
}
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
            <span class="mix-opt-price">${formatMoney(mixSizeFrom(s.opt))}<small>from</small></span>
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
            <span class="mix-opt-price">${mixConcPremium(c.opt) ? '+' + formatMoney(mixConcPremium(c.opt)) : 'Included'}</span>
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
          <div class="mix-sum-row total"><span>Total</span><b>${formatMoney(total)}</b></div>
        </div>
        <div class="mix-eta">
          <span class="mi" aria-hidden="true">schedule</span>
          <span><b>Made to order</b> — hand-blended &amp; dispatched in <b>3–5 working days</b>. We'll WhatsApp you when it ships. (In-stock bottles still arrive in 48 hrs.)</span>
        </div>
      </div>
      <div class="mix-foot">
        <button class="mix-back" onclick="mixBack()">Back</button>
        <button class="mix-next" onclick="mixAddToCart()">Add Mixed Spray — ${formatMoney(total)}</button>
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
/* ── PDP variant picker ──
   The buttons carry their option index and value, and main-product.liquid
   ships the variant list as JSON beside them. Picking a value re-resolves the
   variant and updates everything that quotes it: the price (including the
   struck compare-at and the saving), the stock line, add-to-cart, the sticky
   bar and ?variant= in the URL, so a copied link reopens the same size.
   Prices arrive pre-formatted by Liquid, so the store's money format holds. */
function initVariantPicker() {
  var wrap = document.querySelector('[data-variant-picker]');
  if (!wrap) return;
  var src = wrap.querySelector('[data-variant-data]');
  var variants;
  try { variants = JSON.parse(src.textContent); } catch (e) { return; }
  if (!variants || !variants.length) return;

  var groups = [].slice.call(wrap.querySelectorAll('.var-group'));

  function selection() {
    return groups.map(function (g) {
      var on = g.querySelector('.var-btn.active');
      return on ? on.getAttribute('data-option-value') : null;
    });
  }

  function find(sel) {
    return variants.filter(function (v) {
      return sel.every(function (val, i) { return val === null || v.options[i] === val; });
    })[0];
  }

  /* Liquid marks the selected value, but if nothing came through marked, sync
     the buttons to the variant the form is actually going to post so the
     highlight never contradicts the price. */
  if (!wrap.querySelector('.var-btn.active')) {
    var form0 = document.getElementById('product-form');
    var id0 = form0 && form0.querySelector('input[name="id"]');
    var current = id0 && variants.filter(function (v) { return String(v.id) === String(id0.value); })[0];
    if (current) {
      groups.forEach(function (g, gi) {
        g.querySelectorAll('.var-btn').forEach(function (b) {
          var on = b.getAttribute('data-option-value') === current.options[gi];
          b.classList.toggle('active', on);
          b.setAttribute('aria-checked', on ? 'true' : 'false');
        });
      });
    }
  }

  /* A value is dead when no variant carrying it can be bought at all, so the
     button says so up front rather than only after it is picked. */
  groups.forEach(function (g, gi) {
    g.querySelectorAll('.var-btn').forEach(function (b) {
      var val = b.getAttribute('data-option-value');
      var live = variants.some(function (v) { return v.options[gi] === val && v.available; });
      if (!live) b.classList.add('is-unavailable');
    });
  });

  function apply(v) {
    var form = document.getElementById('product-form');
    var idInput = form && form.querySelector('input[name="id"]');
    if (idInput && v) idInput.value = v.id;

    var row = document.querySelector('[data-price-row]');
    if (row && v) {
      var html = '<span class="pdp-price-now">' + v.price + '</span>';
      if (v.compare) {
        html += '<span class="pdp-price-was">' + v.compare + '</span>' +
                '<span class="pdp-price-save">Save ' + v.save + '%</span>';
      }
      row.innerHTML = html;
    }

    var mini = document.querySelector('.price-mini');
    if (mini && v) mini.textContent = v.price;

    var stock = document.querySelector('.ub-stock');
    if (stock) {
      stock.innerHTML = '<span class="mi" aria-hidden="true">local_shipping</span>' +
        (v && v.available ? 'In stock — ships within 48 hours' : 'Currently out of stock');
    }

    /* Both add-to-cart buttons: the one in the page and the sticky bar's. */
    var sellable = !!(v && v.available);
    var label = v ? (v.available ? 'Add to Cart' : 'Sold Out') : 'Unavailable';
    var atc = document.querySelector('.atc-btn');
    if (atc) {
      atc.disabled = !sellable;
      atc.innerHTML = '<span class="mi" aria-hidden="true">shopping_bag</span>' + label;
    }
    var atcMini = document.querySelector('.atc-mini');
    if (atcMini) {
      atcMini.disabled = !sellable;
      atcMini.textContent = label;
    }

    if (v && v.img) {
      var main = el('mainimg');
      if (main) main.src = v.img;
    }

    if (v && window.history && history.replaceState) {
      try {
        var u = new URL(location.href);
        u.searchParams.set('variant', v.id);
        history.replaceState({}, '', u);
      } catch (e) { /* older browsers keep the unparameterised URL */ }
    }
  }

  wrap.addEventListener('click', function (e) {
    var btn = e.target.closest && e.target.closest('.var-btn');
    if (!btn || btn.classList.contains('active')) return;
    var gi = parseInt(btn.getAttribute('data-option-index'), 10) || 0;
    var group = groups[gi];
    if (group) {
      group.querySelectorAll('.var-btn').forEach(function (b) {
        b.classList.remove('active');
        b.setAttribute('aria-checked', 'false');
      });
    }
    btn.classList.add('active');
    btn.setAttribute('aria-checked', 'true');
    apply(find(selection()));
  });
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
/* The bar is there for when the real Add to Cart has scrolled out of reach, so
   that button is now what drives it. The previous version had three problems:

   - It only ever assigned display inside the scroll handler, so the bar kept
     whatever the stylesheet said until the first scroll. Open a product at a
     restored scroll position (back navigation) or via an #anchor and it stayed
     hidden with the real button already far above.
   - It assigned an INLINE display, which outranks any stylesheet rule. The
     @media(max-width:900px) rule that wants the bar permanently visible on
     phones was therefore dead from the first scroll event onward.
   - It keyed off a flat 500px, which has no relationship to where a given
     product's button actually sits. Long-titled or variant-heavy products push
     it well past 500px, so the bar appeared while the real button was still on
     screen; short ones the other way. Hence "not there on all products".

   Toggling a class instead leaves the cascade in charge, and keying off the
   button makes the trigger identical on every product.

   That trigger is measured, not observed. An IntersectionObserver here only
   showed the bar some of the time, because it reports state CHANGES: the button
   is small, intersections are recomputed about once a frame, and a fast flick,
   a scrollbar drag or an #anchor jump can carry it from below the fold to well
   above it inside a single frame. Intersecting never became true, so the state
   never changed, so no callback ever ran and the bar stayed hidden — while a
   slow scroll over the same button passed through the intersecting state and
   worked. Reading live geometry each frame has no such gap. */
function initStickyAtc() {
  const bar = el('stickyatc'); if (!bar) return;
  const show = on => bar.classList.toggle('is-visible', on);
  const real = document.querySelector('.atc-btn');

  if (!real) {
    // Not a product page layout we recognise: fall back to a plain threshold,
    // and seed the opening state rather than waiting for a scroll.
    const onScroll = () => show(window.scrollY > 500);
    window.addEventListener('scroll', onScroll, { passive: true });
    onScroll();
    return;
  }

  const header = el('hdr');

  function update() {
    /* The header's BOTTOM edge, not its height: initHeaderScroll toggles
       .scrolled which changes that height, and reading the live edge also stays
       correct if the header is ever translated out of the way — height would
       still report a full-size bar covering nothing. Clamped at 0 so a header
       scrolled above the viewport contributes no offset. */
    const rect = header ? header.getBoundingClientRect() : null;
    const offset = rect ? Math.max(0, rect.bottom) : 0;
    // Behind the sticky header counts as gone — it is unreachable there, which
    // is the whole reason the bar exists.
    show(real.getBoundingClientRect().bottom <= offset);
  }

  let ticking = false;
  function onScroll() {
    if (ticking) return;
    ticking = true;
    requestAnimationFrame(function () { update(); ticking = false; });
  }

  window.addEventListener('scroll', onScroll, { passive: true });
  window.addEventListener('resize', onScroll, { passive: true });
  // Images settling below the fold move the button with no scroll event.
  window.addEventListener('load', update);
  /* Restored from the back/forward cache the listeners survive but no scroll
     fires, so the bar would keep whatever state it had when the page was left. */
  window.addEventListener('pageshow', update);
  /* Judge.me's review badge and other app widgets inject above the button long
     after load, moving it while the visitor sits still — no scroll, resize or
     load event covers that, and the bar would hold a stale state until the next
     touch of the wheel. */
  if ('ResizeObserver' in window) new ResizeObserver(onScroll).observe(document.body);
  update();
}
/* Featured-product widget (home) */
function swapFpImg(node, src) {
  document.querySelectorAll('.fp-thumb').forEach(t => t.classList.remove('active'));
  node.classList.add('active');
  const m = el('fp-main-img'); if (m) m.src = src;
}
function changeFpQty(v) { const q = el('fp-qty'); if (q) { let val = parseInt(q.value) + v; if (val < 1) val = 1; q.value = val; } }

/* ═══════════════════════════════════════
   BRAND TABS (home "Shop by Brand")
═══════════════════════════════════════ */
function switchBrandTab(btn) {
  const wrap = btn.closest('.brandtabs'); if (!wrap) return;
  const id = btn.getAttribute('aria-controls');
  wrap.querySelectorAll('.bt-tab').forEach(t => {
    const on = t === btn;
    t.classList.toggle('active', on);
    t.setAttribute('aria-selected', on ? 'true' : 'false');
  });
  /* hidden, not display:none in CSS — the attribute keeps the panel out of the
     accessibility tree as well as out of the layout. */
  wrap.querySelectorAll('.bt-panel').forEach(p => {
    const on = p.id === id;
    p.classList.toggle('active', on);
    p.hidden = !on;
  });
}
/* Left/right arrows move between tabs, which is what a tablist is expected to
   do once it announces itself as one. */
document.addEventListener('keydown', e => {
  if (e.key !== 'ArrowRight' && e.key !== 'ArrowLeft') return;
  const cur = document.activeElement;
  if (!cur || !cur.classList || !cur.classList.contains('bt-tab')) return;
  const tabs = [...cur.closest('.bt-tabs').querySelectorAll('.bt-tab')];
  const next = tabs[(tabs.indexOf(cur) + (e.key === 'ArrowRight' ? 1 : -1) + tabs.length) % tabs.length];
  if (next) { next.focus(); switchBrandTab(next); e.preventDefault(); }
});

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
  if (needsLiveCatalog()) loadLiveCatalog();
  hydrateRenderables();
  initHeaderScroll();
  initThumbs();
  initVariantPicker();
  initStickyAtc();
  initCountdowns();
  initLegalToc();
  initSearchSuggest();
  document.querySelectorAll('.quiz-container-wrap').length && renderQuiz();
  observeFadeUps();
  // Collection engine, if present on this page
  if (typeof renderCollection === 'function' && document.querySelector('[data-collection]')) renderCollection();
  // Standalone combo builder (e.g. gift-sets.html) — collection pages handle their own combo
  if (typeof renderComboGrid === 'function' && document.getElementById('comboGrid') && !document.querySelector('[data-collection]')) renderComboGrid();
  observeFadeUps();
}
document.addEventListener('keydown', e => { if (e.key === 'Escape') { closeAI(); closeMix(); closeReferral(); closeMobileNav(); } });
// Defer to DOMContentLoaded so a later <script> (e.g. collections.js) is parsed
// and its globals (renderCollection, COLLECTIONS) are available before initApp runs.
if (document.readyState === 'complete') initApp();
else document.addEventListener('DOMContentLoaded', initApp);

/* ═══════════════════════════════════════
   CART DRAWER

   Adding to the cart used to hand the shopper to /cart, which ends the
   browsing session at exactly the moment they are most willing to keep going.
   The panel keeps them where they were; Checkout inside it is the only thing
   that still leaves the page.

   The panel's contents are re-rendered by Shopify rather than assembled here,
   so prices, discounts and line properties stay formatted by the same Liquid
   the cart page uses. Only [data-cd-body] and the footer are swapped, because
   the scrim and panel carry the open/close transition and replacing them
   mid-animation would restart it.
═══════════════════════════════════════ */
(function () {
  var root = null, lastFocus = null, busy = false;

  function el() { return document.getElementById('cartDrawer'); }

  function openCart() {
    root = el(); if (!root) return;
    lastFocus = document.activeElement;
    root.hidden = false;
    /* Force a reflow so the transform transition runs from its start value —
       without it the panel would appear already open. */
    void root.offsetWidth;
    root.classList.add('is-open');
    document.documentElement.style.overflow = 'hidden';
    var panel = root.querySelector('.cd-panel');
    if (panel) panel.focus();
  }

  function closeCart() {
    root = el(); if (!root || root.hidden) return;
    root.classList.remove('is-open');
    document.documentElement.style.overflow = '';
    /* Wait out the slide before hiding, or it vanishes instead of sliding. */
    setTimeout(function () { if (root && !root.classList.contains('is-open')) root.hidden = true; }, 380);
    if (lastFocus && lastFocus.focus) lastFocus.focus();
  }

  /* Pull a freshly rendered drawer from Shopify and swap the parts that change. */
  function refresh() {
    var base = (window.routes && window.routes.root_url) || '/';
    if (base.slice(-1) !== '/') base += '/';
    return fetch(base + '?section_id=cart-drawer', { headers: { 'Accept': 'text/html' } })
      .then(function (r) { if (!r.ok) throw 0; return r.text(); })
      .then(function (html) {
        var next = new DOMParser().parseFromString(html, 'text/html');
        var live = el(); if (!live) return;
        var a = next.querySelector('[data-cd-body]'), b = live.querySelector('[data-cd-body]');
        if (a && b) b.innerHTML = a.innerHTML;
        /* The footer is absent when the cart is empty, so swap the element
           itself rather than its contents. */
        var nf = next.querySelector('.cd-foot'), lf = live.querySelector('.cd-foot');
        var panel = live.querySelector('.cd-panel');
        if (nf && lf) lf.replaceWith(nf);
        else if (nf && !lf && panel) panel.appendChild(nf);
        else if (!nf && lf) lf.remove();
        var nt = next.querySelector('.cd-title'), lt = live.querySelector('.cd-title');
        if (nt && lt) lt.innerHTML = nt.innerHTML;

        /* Shopify renders this drawer at /?section_id=cart-drawer, so any
           Liquid that asked for request.path was told "/" — the welcome
           discount link would have applied the code and then dropped the
           shopper on the homepage, losing the page they were browsing. Point
           it back at where they actually are. */
        var apply = live.querySelector('a.wo-row[href*="/discount/"]');
        if (apply) {
          apply.href = apply.href.replace(/([?&]redirect=)[^&]*/,
            '$1' + encodeURIComponent(location.pathname));
        }
      });
  }

  function syncBadges(count) {
    if (typeof count !== 'number') return;
    cartCount = count;
    document.querySelectorAll('.cbadge').forEach(function (b) { b.textContent = count; });
  }

  /* Shared by every add path: the product form, Quick Add, the concierge. */
  function addItems(items) {
    if (busy) return Promise.resolve(false);
    busy = true;
    return fetch((window.routes && window.routes.cart_add_url) || '/cart/add.js', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
      body: JSON.stringify({ items: items })
    })
      .then(function (r) {
        if (!r.ok) return r.json().then(function (d) { throw new Error(d && d.description); }, function () { throw new Error(); });
        return r.json();
      })
      .then(function () { return fetch('/cart.js', { headers: { 'Accept': 'application/json' } }).then(function (r) { return r.json(); }); })
      .then(function (cart) {
        syncBadges(cart.item_count);
        document.dispatchEvent(new CustomEvent('cart:updated', { detail: cart }));
        return refresh().then(function () { openCart(); return true; });
      })
      .catch(function (e) {
        if (typeof toast === 'function') toast((e && e.message) || 'Could not add to cart — please try again');
        return false;
      })
      .then(function (ok) { busy = false; return ok; });
  }

  /* Quantity and remove inside the panel, against the same endpoint the cart
     page uses so the two can never disagree. */
  function change(key, quantity) {
    if (busy) return;
    busy = true;
    var live = el();
    var body = live && live.querySelector('.cd-body');
    if (body) body.style.opacity = '.55';
    fetch((window.routes && window.routes.cart_change_url) || '/cart/change.js', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
      body: JSON.stringify({ id: key, quantity: quantity })
    })
      .then(function (r) { if (!r.ok) throw 0; return r.json(); })
      .then(function (cart) {
        syncBadges(cart.item_count);
        document.dispatchEvent(new CustomEvent('cart:updated', { detail: cart }));
        return refresh();
      })
      .catch(function () { if (typeof toast === 'function') toast('Could not update cart'); })
      .then(function () {
        busy = false;
        var l = el(), lb = l && l.querySelector('.cd-body');
        if (lb) lb.style.opacity = '';
      });
  }

  document.addEventListener('click', function (e) {
    var t = e.target;

    if (t.closest && t.closest('[data-cd-close]')) { e.preventDefault(); closeCart(); return; }

    /* Header bag opens the panel. The href stays /cart so it still works with
       no JS and still opens in a new tab on middle-click. Links inside the
       panel are left alone: "View full cart" also ends in /cart, so it was
       re-opening the already-open panel instead of going to the cart page. */
    var bag = t.closest && t.closest('a[href$="/cart"], a.ni[title="Cart"]');
    if (bag && !bag.closest('#cartDrawer') && el() && !e.metaKey && !e.ctrlKey && !e.shiftKey && e.button === 0) {
      e.preventDefault(); openCart(); return;
    }

    var drawer = t.closest && t.closest('#cartDrawer');
    if (!drawer) return;
    var row = t.closest('.co-line');
    if (!row) return;
    var key = row.getAttribute('data-key');

    if (t.closest('[data-cart-remove]')) { change(key, 0); return; }
    var step = t.closest('[data-cart-step]');
    if (step) {
      var q = parseInt(row.getAttribute('data-qty'), 10) || 1;
      change(key, Math.max(0, q + parseInt(step.getAttribute('data-cart-step'), 10)));
    }
  });

  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') closeCart();
  });

  /* The product form is a native Shopify form, so without this it POSTs and
     Shopify redirects to /cart — the behaviour this replaces. */
  document.addEventListener('submit', function (e) {
    var form = e.target;
    if (!form.matches || !form.matches('form[action*="/cart/add"]')) return;
    if (!el()) return;                       // no drawer on the page: let it post
    e.preventDefault();
    var fd = new FormData(form);
    var id = fd.get('id');
    if (!id) { form.submit(); return; }       // nothing we can post as JSON
    var btn = form.querySelector('[type="submit"][name="add"]');
    if (btn) btn.disabled = true;
    addItems([{ id: id, quantity: parseInt(fd.get('quantity'), 10) || 1 }])
      .then(function () { if (btn) btn.disabled = false; });
  });

  window.openCart = openCart;
  window.closeCart = closeCart;
  window.cartDrawerAdd = addItems;
  window.refreshCartDrawer = refresh;
})();
