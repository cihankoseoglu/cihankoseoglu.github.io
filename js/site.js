// Loaded at the end of every page: the cookie banner, GA4 events and the Konami easter egg, in that order.

// Minimal cookie banner for Google Consent Mode. The default (denied) is set in each page's <head> (js/gtag.js);
// this asks once, remembers the answer in localStorage and updates consent when someone accepts.
(function () {
  function get() { try { return localStorage.getItem('consent'); } catch (e) { return null; } }
  function set(v) { try { localStorage.setItem('consent', v); } catch (e) {} }

  var css = '.consent{position:fixed;left:16px;right:16px;bottom:16px;z-index:50;max-width:520px;margin:0 auto;' +
    'display:flex;align-items:center;gap:12px;flex-wrap:wrap;padding:12px 14px;border:1px solid var(--line,#e6e1da);' +
    'border-radius:12px;background:var(--bg,#faf8f5);color:var(--text,#1d1b19);font:400 14px/1.4 var(--sans,system-ui),system-ui,sans-serif;' +
    'box-shadow:0 6px 24px rgba(0,0,0,.08)}' +
    '.consent p{margin:0;flex:1 1 220px}.consent>span{display:flex;gap:8px;margin-left:auto}' +
    '.consent button{font:inherit;padding:6px 14px;border-radius:999px;cursor:pointer;border:1px solid var(--line,#e6e1da);' +
    'background:transparent;color:inherit}' +
    '.consent button.ok{background:var(--text,#1d1b19);border-color:var(--text,#1d1b19);color:var(--bg,#faf8f5)}' +
    '.consent .short{display:none}' +
    // Phones: a slim one-line bar flush with the bottom edge.
    '@media (max-width:599px){.consent{left:0;right:0;bottom:0;max-width:none;flex-wrap:nowrap;gap:10px;padding:8px 12px;' +
    'padding-bottom:calc(8px + env(safe-area-inset-bottom));border-width:1px 0 0;border-radius:0;box-shadow:none;font-size:13px}' +
    '.consent p{flex:1 1 auto;min-width:0}.consent .long{display:none}.consent .short{display:inline}' +
    '.consent>span{gap:6px}.consent button{padding:4px 12px}}';
  var phone = window.matchMedia('(max-width: 599px)').matches;
  var albumPage = /^\/photography\/[^/]+\/?$/.test(location.pathname);

  function show() {
    if (document.querySelector('.consent')) return;
    if (!document.getElementById('consent-css')) {
      var st = document.createElement('style');
      st.id = 'consent-css';
      st.textContent = css;
      document.head.appendChild(st);
    }
    var box = document.createElement('div');
    box.className = 'consent';
    box.setAttribute('role', 'dialog');
    box.setAttribute('aria-label', 'Cookie consent');
    box.innerHTML = '<p><span class="long">I use cookies for anonymous analytics to see what people read.</span>' +
      '<span class="short">Anonymous analytics cookies?</span></p>' +
      '<span><button type="button" class="no">Decline</button><button type="button" class="ok">Accept</button></span>';
    box.querySelector('.ok').onclick = function () { choose('granted'); };
    box.querySelector('.no').onclick = function () { choose('denied'); };
    document.body.appendChild(box);
  }

  function choose(v) {
    set(v);
    if (typeof window.gtag === 'function') window.gtag('consent', 'update', { analytics_storage: v });
    var box = document.querySelector('.consent');
    if (box) box.remove();
  }

  window.showConsent = show;
  // On a phone, an album opened directly gets its photos to itself until the first scroll.
  if (!get()) {
    if (phone && albumPage) window.addEventListener('scroll', show, { once: true, passive: true });
    else show();
  }
})();

// Sends site interactions straight to GA4 as events via gtag.
// Page views, scrolls and outbound clicks are left to GA4 enhanced measurement.
(function () {
  function track(event, params) {
    var out = {};
    for (var k in params) if (params[k] !== undefined) out[k] = params[k];
    if (typeof window.gtag === 'function') window.gtag('event', event, out);
  }
  window.siteTrack = track;

  function findAlbum(slug) {
    var albums = window.ALBUMS || [];
    for (var i = 0; i !== albums.length; i++) if (albums[i].slug === slug) return albums[i];
    return null;
  }
  // Album pages live at /photography/<slug>/ (old links used #/<slug>).
  function slugFromUrl(url) {
    var m = /^\/photography\/([^/]+)\/?$/.exec(url.pathname) || /^#\/([^/]+)/.exec(url.hash || '');
    return m ? m[1] : null;
  }


  // Clicks: album links (select_content) and social profile links.
  var SOCIAL = { 'x.com': 'x', 'twitter.com': 'x', 'youtube.com': 'youtube', 'linkedin.com': 'linkedin',
                 'open.spotify.com': 'spotify' };
  document.addEventListener('click', function (e) {
    var a = e.target.closest && e.target.closest('a');
    if (!a || !a.href) return;
    if (a.classList.contains('email')) {
      track('select_content', { content_type: 'contact', content_id: 'email', link_location: 'say_hi' });
      return;
    }
    var url = new URL(a.href, location.href);
    var host = url.hostname.replace(/^www\./, '');

    if (SOCIAL[host]) {
      track('select_content', { content_type: 'social_profile', content_id: SOCIAL[host],
                                social_platform: SOCIAL[host], link_location: a.closest('.links') ? 'say_hi' : 'outside_work' });
      return;
    }
    if (url.pathname.indexOf('/photography') !== 0) return;
    var slug = slugFromUrl(url);
    var where = a.classList.contains('photo-link') ? 'home_strip'
              : a.classList.contains('next') ? 'next_album'
              : a.classList.contains('cover') ? 'album_index'
              : a.closest('.row') ? 'album_row' : 'other';
    track('select_content', { content_type: slug ? 'album' : 'photography_index',
                              content_id: slug || 'photography', link_location: where });
  }, true);

  // Album views and how far into an album people scroll (photography page only).
  if (location.pathname.indexOf('/photography') === 0) {
    var current = null, marks = {};
    function onRoute() {
      var album = findAlbum(slugFromUrl(location));
      current = album;
      marks = {};
      if (album) {
        track('album_view', { album_id: album.slug, album_title: album.title, album_date: album.date || String(album.year),
                              photo_count: album.photos.length });
      }
    }
    window.addEventListener('albumchange', onRoute);
    window.addEventListener('scroll', function () {
      if (!current) return;
      var h = document.documentElement.scrollHeight - window.innerHeight;
      if (!(h > 0)) return;
      var pct = window.scrollY / h * 100;
      [25, 50, 75, 90].forEach(function (p) {
        if (pct >= p && !marks[p]) {
          marks[p] = true;
          track('album_progress', { album_id: current.slug, album_title: current.title, percent_scrolled: p });
        }
      });
    }, { passive: true });
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', onRoute);
    else onRoute();
  }

  // First time someone draws on the Game of Life band.
  var life = document.getElementById('life');
  if (life) {
    life.addEventListener('pointerdown', function () {
      track('game_of_life_play', { content_type: 'game_of_life', content_id: 'home_header' });
    }, { once: true });
  }
})();

// Konami code easter egg (up up down down left right left right B A), moved here from GTM.
(function () {
  var CODE = 'arrowup,arrowup,arrowdown,arrowdown,arrowleft,arrowright,arrowleft,arrowright,b,a', keys = [], done = false;
  var GIF = 'https://media.giphy.com/media/Vuw9m5wXviFIQ/giphy.gif';
  var MP3 = 'https://www.dropbox.com/s/80ozalto7b3fju2/donotdelete-rickroll.mp3?dl=1';
  var LINES = ['Never Gonna Give You Up', 'Never Gonna Let You Down'];
  var COLORS = ['#FF0000', '#00FF00', '#0000FF'];

  document.addEventListener('keyup', function (e) {
    if (done || !e.key) return;
    keys.push(e.key.toLowerCase());
    if (keys.length > 10) keys.shift();
    if (keys.join() === CODE) { done = true; rickroll(); }
  });

  function rickroll() {
    if (typeof window.gtag === 'function') window.gtag('event', 'konami_code');
    var audio = new Audio(MP3);

    // Lyrics jump around the screen in random colours, once a second, until the song ends.
    var el = document.createElement('div'), i = 0;
    el.style.position = 'fixed';
    el.style.fontSize = '40px';
    el.style.fontFamily = '"Comic Sans MS"';
    el.style.zIndex = 10000001;
    document.body.appendChild(el);
    var timer = setInterval(function () {
      el.textContent = LINES[i++ % LINES.length];
      el.style.left = Math.floor(Math.random() * (innerWidth - 200)) + 'px';
      el.style.top = Math.floor(Math.random() * (innerHeight - 26)) + 'px';
      el.style.color = COLORS[Math.floor(Math.random() * COLORS.length)];
    }, 1000);
    audio.addEventListener('ended', function () { clearInterval(timer); el.remove(); });
    audio.play().catch(function () {});

    var imgs = document.getElementsByTagName('img');
    for (var j = 0; j < imgs.length; j++) {
      if (imgs[j].hasAttribute('srcset')) imgs[j].srcset = GIF;
      imgs[j].src = GIF;
    }
  }
})();
