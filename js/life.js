// Conway's Game of Life, drawn on a canvas band at the top of the page.
// Click or drag to draw cells. The board wraps at the edges and quietly
// reseeds itself when it settles down.
(function () {
  var canvas = document.getElementById('life');
  if (!canvas || !canvas.getContext) return;
  var ctx = canvas.getContext('2d');

  var CELL = 14;          // cell size in CSS pixels
  var GAP = 2;            // space between cells
  var STEP_MS = 140;      // time between generations
  var FADE = 0.12;        // how fast cells fade in and out per frame
  var reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  var cols, rows, grid, next, alpha, ages;
  var color = getComputedStyle(document.documentElement).getPropertyValue('--accent').trim() || '#8a2be2';
  var lastStep = 0, stillGens = 0, visible = true, raf = null;

  function resize() {
    var dpr = window.devicePixelRatio || 1;
    var w = canvas.clientWidth, h = canvas.clientHeight;
    canvas.width = Math.round(w * dpr);
    canvas.height = Math.round(h * dpr);
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

    var newCols = Math.ceil(w / CELL), newRows = Math.ceil(h / CELL);
    var old = grid, oldCols = cols, oldRows = rows;
    cols = newCols; rows = newRows;
    grid = new Uint8Array(cols * rows);
    next = new Uint8Array(cols * rows);
    alpha = new Float32Array(cols * rows);
    ages = new Uint16Array(cols * rows);
    if (old) {
      for (var y = 0; y < Math.min(rows, oldRows); y++)
        for (var x = 0; x < Math.min(cols, oldCols); x++)
          if (old[y * oldCols + x]) { grid[y * cols + x] = 1; alpha[y * cols + x] = 1; }
    } else {
      seed(0.22);
    }
    draw();
  }

  function seed(density) {
    for (var i = 0; i < grid.length; i++) grid[i] = Math.random() < density ? 1 : 0;
  }

  // Drop a few gliders in to keep things moving.
  function sprinkle() {
    var glider = [[1, 0], [2, 1], [0, 2], [1, 2], [2, 2]];
    for (var n = 0; n < 4; n++) {
      var ox = Math.floor(Math.random() * cols), oy = Math.floor(Math.random() * rows);
      var fx = Math.random() < 0.5 ? 1 : -1, fy = Math.random() < 0.5 ? 1 : -1;
      glider.forEach(function (p) {
        var x = (ox + p[0] * fx + cols) % cols, y = (oy + p[1] * fy + rows) % rows;
        grid[y * cols + x] = 1;
      });
    }
  }

  function step() {
    var changed = 0, pop = 0;
    for (var y = 0; y < rows; y++) {
      var up = ((y - 1 + rows) % rows) * cols, mid = y * cols, down = ((y + 1) % rows) * cols;
      for (var x = 0; x < cols; x++) {
        var l = (x - 1 + cols) % cols, r = (x + 1) % cols;
        var n = grid[up + l] + grid[up + x] + grid[up + r] +
                grid[mid + l] + grid[mid + r] +
                grid[down + l] + grid[down + x] + grid[down + r];
        var i = mid + x, alive = grid[i];
        var v = (n === 3 || (alive && n === 2)) ? 1 : 0;
        next[i] = v;
        if (v !== alive) changed++;
        ages[i] = v ? Math.min(ages[i] + 1, 60) : 0;
        pop += v;
      }
    }
    var t = grid; grid = next; next = t;

    // Mostly still (or almost empty): wake it back up.
    stillGens = changed < cols * rows * 0.004 ? stillGens + 1 : 0;
    if (stillGens > 12 || pop < cols * rows * 0.02) { sprinkle(); stillGens = 0; }
  }

  function draw() {
    var w = canvas.clientWidth, h = canvas.clientHeight;
    ctx.clearRect(0, 0, w, h);
    ctx.fillStyle = color;
    for (var y = 0; y < rows; y++) {
      for (var x = 0; x < cols; x++) {
        var i = y * cols + x;
        var target = grid[i] ? 1 : 0;
        alpha[i] += (target - alpha[i]) * (reduceMotion ? 1 : FADE * 2);
        if (alpha[i] < 0.02) continue;
        // Older cells settle to a softer tone; newborns are brightest.
        var tone = grid[i] ? 0.85 - Math.min(ages[i], 30) / 30 * 0.45 : 0.4;
        ctx.globalAlpha = alpha[i] * tone;
        roundRect(x * CELL + GAP / 2, y * CELL + GAP / 2, CELL - GAP, CELL - GAP, 3);
      }
    }
    ctx.globalAlpha = 1;
  }

  function roundRect(x, y, w, h, r) {
    ctx.beginPath();
    ctx.moveTo(x + r, y);
    ctx.arcTo(x + w, y, x + w, y + h, r);
    ctx.arcTo(x + w, y + h, x, y + h, r);
    ctx.arcTo(x, y + h, x, y, r);
    ctx.arcTo(x, y, x + w, y, r);
    ctx.fill();
  }

  function frame(t) {
    raf = null;
    if (!visible || document.hidden) return;
    if (t - lastStep > STEP_MS) { step(); lastStep = t; }
    draw();
    raf = requestAnimationFrame(frame);
  }

  function start() {
    if (reduceMotion || raf) return;
    raf = requestAnimationFrame(frame);
  }

  // Drawing with the mouse or a finger.
  var drawing = false;
  function paint(e) {
    var rect = canvas.getBoundingClientRect();
    var x = Math.floor((e.clientX - rect.left) / CELL), y = Math.floor((e.clientY - rect.top) / CELL);
    if (x < 0 || y < 0 || x >= cols || y >= rows) return;
    // Draw a small plus so a single click makes something that lives a while.
    [[0, 0], [1, 0], [-1, 0], [0, 1], [0, -1]].forEach(function (d) {
      var i = ((y + d[1] + rows) % rows) * cols + (x + d[0] + cols) % cols;
      grid[i] = 1; ages[i] = 0;
    });
    stillGens = 0;
    if (reduceMotion) draw();
  }
  canvas.addEventListener('pointerdown', function (e) {
    drawing = true;
    // Capture mouse and pen so a drag can leave the band; a finger is left alone so the page still scrolls.
    if (e.pointerType !== 'touch') canvas.setPointerCapture(e.pointerId);
    paint(e);
  });
  canvas.addEventListener('pointermove', function (e) { if (drawing) paint(e); });
  canvas.addEventListener('pointerup', function () { drawing = false; });
  canvas.addEventListener('pointercancel', function () { drawing = false; });

  // Only run while the band is on screen and the tab is in front.
  if ('IntersectionObserver' in window) {
    new IntersectionObserver(function (entries) {
      visible = entries[0].isIntersecting;
      if (visible) start();
    }).observe(canvas);
  }
  document.addEventListener('visibilitychange', function () { if (!document.hidden) start(); });

  var resizeTimer;
  window.addEventListener('resize', function () {
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(resize, 150);
  });

  resize();
  start();
})();
