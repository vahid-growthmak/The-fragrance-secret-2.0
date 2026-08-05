/* ═══════════════════════════════════════════════════════════════════════
   WISHLIST

   Saved fragrances, persisted in localStorage and keyed by product handle.

   The wishlist used to be a mockup: the heart on every card called
   toast('Saved to wishlist') and nothing else, so the icon never changed,
   a second click could not remove anything, and /pages/wishlist rendered
   four hardcoded demo products. This module is the real store behind it.

   Handles are stored rather than product IDs because the wishlist page
   rehydrates each entry from /products/<handle>.js, which gives live
   title, price, image and variant id without us caching stale copies.

   Guests are supported — nothing here requires a customer account. The
   trade-off is that the list lives in one browser and does not follow the
   shopper across devices.

   Public API (window.TFSWishlist):
     .all()            → array of handles, most recently added first
     .count()          → number saved
     .has(handle)      → boolean
     .add / .remove    → explicit
     .toggle(handle)   → returns true when the item ended up saved
     .sync()           → repaint every button and badge on the page

   Fires a 'wishlist:change' event on document for anything that needs it.
═══════════════════════════════════════════════════════════════════════ */
(function (window, document) {
  'use strict';

  var KEY = 'tfs:wishlist:v1';

  /* localStorage throws in Safari private mode and when storage is
     disabled entirely. Fall back to memory so the wishlist still works
     for the length of the visit instead of breaking every card. */
  var memory = null;

  function read() {
    if (memory) return memory.slice();
    try {
      var raw = window.localStorage.getItem(KEY);
      var list = raw ? JSON.parse(raw) : [];
      return Array.isArray(list) ? list.filter(function (h) { return typeof h === 'string' && h; }) : [];
    } catch (e) {
      memory = [];
      return [];
    }
  }

  function write(list) {
    try {
      window.localStorage.setItem(KEY, JSON.stringify(list));
    } catch (e) {
      memory = list.slice();
    }
    announce(list);
  }

  function announce(list) {
    sync();
    document.dispatchEvent(new CustomEvent('wishlist:change', {
      detail: { handles: list.slice(), count: list.length }
    }));
  }

  var Wishlist = {
    all: function () { return read(); },
    count: function () { return read().length; },
    has: function (handle) { return read().indexOf(handle) !== -1; },

    add: function (handle) {
      if (!handle) return false;
      var list = read();
      if (list.indexOf(handle) !== -1) return false;
      list.unshift(handle);          // newest first, so the page reads chronologically
      write(list);
      return true;
    },

    remove: function (handle) {
      var list = read();
      var i = list.indexOf(handle);
      if (i === -1) return false;
      list.splice(i, 1);
      write(list);
      return true;
    },

    /* Returns true when the product is now saved, false when it was removed,
       so callers can word their own toast without re-reading the store. */
    toggle: function (handle, label) {
      if (!handle) return false;
      var saved = this.has(handle) ? (this.remove(handle), false) : (this.add(handle), true);
      if (typeof window.toast === 'function') {
        var name = label ? ' — ' + label : '';
        window.toast(saved ? '♥ Saved to wishlist' + name : 'Removed from wishlist' + name);
      }
      return saved;
    },

    clear: function () { write([]); },

    sync: function () { sync(); }
  };

  /* Repaint state. Called after every change, on load, and when another tab
     writes — buttons are keyed by data-wish so late-rendered cards (the
     concierge, collection filters) pick up the right state on their own. */
  function sync() {
    var list = read();
    var count = list.length;

    document.querySelectorAll('[data-wish]').forEach(function (btn) {
      var on = list.indexOf(btn.getAttribute('data-wish')) !== -1;
      btn.classList.toggle('is-wished', on);
      btn.setAttribute('aria-pressed', on ? 'true' : 'false');
      var icon = btn.querySelector('.mi');
      if (icon) icon.classList.toggle('mi-f', on);   // Material Symbols FILL axis
      var base = btn.getAttribute('data-wish-label') || 'this fragrance';
      btn.setAttribute('title', on ? 'Remove from wishlist' : 'Save to wishlist');
      btn.setAttribute('aria-label', (on ? 'Remove ' : 'Save ') + base + (on ? ' from wishlist' : ' to wishlist'));
    });

    document.querySelectorAll('.wbadge').forEach(function (b) {
      b.textContent = count;
      b.hidden = count === 0;          // an empty heart badge reading "0" is just noise
    });
  }

  /* Keep tabs in step — the storage event only fires in the *other* tabs. */
  window.addEventListener('storage', function (e) {
    if (e.key === KEY) sync();
  });

  document.addEventListener('DOMContentLoaded', sync);
  if (document.readyState !== 'loading') sync();

  window.TFSWishlist = Wishlist;
})(window, document);
