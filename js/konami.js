// Konami code easter egg (up up down down left right left right B A), moved here from GTM.
(function () {
  var CODE = '38,38,40,40,37,39,37,39,66,65', keys = [];
  var GIF = 'https://media.giphy.com/media/Vuw9m5wXviFIQ/giphy.gif';
  var LINES = ['Never Gonna Give You Up', 'Never Gonna Let You Down'];
  var COLORS = ['#FF0000', '#00FF00', '#0000FF'];

  document.addEventListener('keyup', function (e) {
    keys.push(e.keyCode);
    if (keys.slice(-10).join() === CODE) rickroll();
  });

  function rickroll() {
    if (typeof window.gtag === 'function') window.gtag('event', 'konami_code');
    new Audio('https://www.dropbox.com/s/80ozalto7b3fju2/donotdelete-rickroll.mp3?dl=1').play();

    // Lyrics jump around the screen in random colours, once a second.
    var el = document.createElement('div'), i = 0;
    el.style.position = 'fixed';
    el.style.fontSize = '40px';
    el.style.fontFamily = '"Comic Sans MS"';
    el.style.zIndex = 10000001;
    document.body.appendChild(el);
    setInterval(function () {
      el.textContent = LINES[i++ % LINES.length];
      el.style.left = Math.floor(Math.random() * (innerWidth - 200)) + 'px';
      el.style.top = Math.floor(Math.random() * (innerHeight - 26)) + 'px';
      el.style.color = COLORS[Math.floor(Math.random() * COLORS.length)];
    }, 1000);

    var imgs = document.getElementsByTagName('img');
    for (var j = 0; j < imgs.length; j++) {
      imgs[j].src = GIF;
      if (imgs[j].hasAttribute('srcset')) imgs[j].srcset = GIF;
    }
  }
})();
