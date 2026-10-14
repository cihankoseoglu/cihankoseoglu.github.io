// Google tag (GA4) with Consent Mode. Loaded first thing in every page's <head>.
// Analytics cookies stay off until the visitor accepts (see /js/consent.js), so the
// consent default has to be set before the config call.
window.dataLayer = window.dataLayer || [];
function gtag(){dataLayer.push(arguments);}
(function () {
  var consent; try { consent = localStorage.getItem('consent'); } catch (e) {}
  gtag('consent', 'default', { ad_storage: 'denied', ad_user_data: 'denied', ad_personalization: 'denied',
                               analytics_storage: consent === 'granted' ? 'granted' : 'denied' });
  gtag('js', new Date());
  gtag('config', 'G-1LPFGZTQRZ');
  var s = document.createElement('script');
  s.async = true;
  s.src = 'https://www.googletagmanager.com/gtag/js?id=G-1LPFGZTQRZ';
  document.head.appendChild(s);
})();
