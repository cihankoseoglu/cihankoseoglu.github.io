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
