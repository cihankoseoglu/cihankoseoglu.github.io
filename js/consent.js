// Minimal cookie banner for Google Consent Mode. The default (denied) is set in each page's <head>;
// this asks once, remembers the answer in localStorage and updates consent when someone accepts.
(function () {
  function get() { try { return localStorage.getItem('consent'); } catch (e) { return null; } }
  function set(v) { try { localStorage.setItem('consent', v); } catch (e) {} }

  var css = '.consent{position:fixed;left:16px;right:16px;bottom:16px;z-index:50;max-width:520px;margin:0 auto;' +
    'display:flex;align-items:center;gap:12px;flex-wrap:wrap;padding:12px 14px;border:1px solid var(--line,#e6e1da);' +
    'border-radius:12px;background:var(--bg,#faf8f5);color:var(--text,#1d1b19);font:400 14px/1.4 Inter,system-ui,sans-serif;' +
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
  var albumPage = location.pathname.indexOf('/photography') === 0 && /^#\/./.test(location.hash);

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
