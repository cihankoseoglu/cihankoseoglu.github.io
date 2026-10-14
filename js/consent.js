// Minimal cookie banner for Google Consent Mode. The default (denied) is set in each page's <head>;
// this asks once, remembers the answer in localStorage and updates consent when someone accepts.
(function () {
  function get() { try { return localStorage.getItem('consent'); } catch (e) { return null; } }
  function set(v) { try { localStorage.setItem('consent', v); } catch (e) {} }

  var css = '.consent{position:fixed;left:16px;right:16px;bottom:16px;z-index:50;max-width:520px;margin:0 auto;' +
    'display:flex;align-items:center;gap:12px;flex-wrap:wrap;padding:12px 14px;border:1px solid var(--line,#e6e1da);' +
    'border-radius:12px;background:var(--bg,#faf8f5);color:var(--text,#1d1b19);font:400 14px/1.4 Inter,system-ui,sans-serif;' +
    'box-shadow:0 6px 24px rgba(0,0,0,.08)}' +
    '.consent p{margin:0;flex:1 1 220px}.consent span{display:flex;gap:8px;margin-left:auto}' +
    '.consent button{font:inherit;padding:6px 14px;border-radius:999px;cursor:pointer;border:1px solid var(--line,#e6e1da);' +
    'background:transparent;color:inherit}' +
    '.consent button.ok{background:var(--text,#1d1b19);border-color:var(--text,#1d1b19);color:var(--bg,#faf8f5)}';

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
    box.innerHTML = '<p>I use cookies for anonymous analytics to see what people read.</p>' +
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
  if (!get()) show();
})();
