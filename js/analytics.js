// Sends site interactions to the GTM dataLayer. GTM turns these into GA4 events.
// Page views, scrolls and outbound clicks are left to GA4 enhanced measurement.
(function () {
  var dl = window.dataLayer = window.dataLayer || [];

  // Every push lists all our keys so values from one event never leak into the next.
  var KEYS = ['content_type', 'content_id', 'link_location', 'album_id', 'album_title',
              'album_date', 'photo_count', 'percent_scrolled', 'social_platform'];
  function track(event, params) {
    var msg = { event: event };
    KEYS.forEach(function (k) { msg[k] = undefined; });
    for (var k in params) msg[k] = params[k];
    dl.push(msg);
  }
  window.siteTrack = track;

  function findAlbum(slug) {
    var albums = window.ALBUMS || [];
    for (var i = 0; i !== albums.length; i++) if (albums[i].slug === slug) return albums[i];
    return null;
  }
  function slugFromHash(href) {
    var m = /#\/([^/]+)/.exec(href || '');
    return m ? m[1] : null;
  }

  // Clicks: album links (select_content) and social profile links.
  var SOCIAL = { 'x.com': 'x', 'twitter.com': 'x', 'youtube.com': 'youtube', 'linkedin.com': 'linkedin' };
  document.addEventListener('click', function (e) {
    var a = e.target.closest && e.target.closest('a');
    if (!a || !a.href) return;
    var url = new URL(a.href, location.href);
    var host = url.hostname.replace(/^www\./, '');

    if (SOCIAL[host]) {
      track('select_content', { content_type: 'social_profile', content_id: SOCIAL[host],
                                social_platform: SOCIAL[host], link_location: 'say_hi' });
      return;
    }
    if (url.pathname.indexOf('/photography') !== 0) return;
    var slug = slugFromHash(url.hash);
    var where = a.classList.contains('photo-link') ? 'home_strip'
              : a.classList.contains('next') ? 'next_album'
              : a.classList.contains('cover') ? 'album_index' : 'other';
    track('select_content', { content_type: slug ? 'album' : 'photography_index',
                              content_id: slug || 'photography', link_location: where });
  }, true);

  // Album views and how far into an album people scroll (photography page only).
  if (location.pathname.indexOf('/photography') === 0) {
    var current = null, marks = {};
    function onRoute() {
      var album = findAlbum(slugFromHash(location.hash));
      current = album;
      marks = {};
      if (album) {
        track('album_view', { album_id: album.slug, album_title: album.title, album_date: album.date || String(album.year),
                              photo_count: album.photos.length });
      }
    }
    window.addEventListener('hashchange', onRoute);
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
