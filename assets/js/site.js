/* satsh · comportamiento del sitio.  Sin dependencias.
   (El idioma inicial lo fija un pequeño script en <head>, antes de pintar; aquí está el selector.) */
(function () {
  "use strict";

  var doc = document, root = doc.documentElement;
  var reduceMotion = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  var $ = function (s, c) { return (c || doc).querySelector(s); };
  var $$ = function (s, c) { return Array.prototype.slice.call((c || doc).querySelectorAll(s)); };

  /* ------------------------------------------------------------------ idioma */
  function applyLang(lang) {
    root.lang = lang;
    var t = $("title");
    if (t && t.getAttribute("data-" + lang)) { doc.title = t.getAttribute("data-" + lang); }
    var m = $('meta[name="description"]');
    if (m && m.getAttribute("data-" + lang)) { m.setAttribute("content", m.getAttribute("data-" + lang)); }
    $$("[data-aria-es]").forEach(function (el) { el.setAttribute("aria-label", el.getAttribute("data-aria-" + lang)); });
    $$("img[data-alt-es]").forEach(function (el) { el.setAttribute("alt", el.getAttribute("data-alt-" + lang)); });
  }
  applyLang(root.lang === "es" ? "es" : "en");
  $$(".lang button").forEach(function (b) {
    b.addEventListener("click", function () {
      var l = b.getAttribute("data-set");
      try { localStorage.setItem("satsh-lang", l); } catch (e) { /* modo privado */ }
      applyLang(l);
      requestAnimationFrame(function () { updateSpy(); });
    });
  });

  /* ------------------------------------------------------------------ cabecera */
  var header = $(".site-header");
  function onScrollHeader() { if (header) { header.classList.toggle("is-scrolled", window.scrollY > 24); } }
  onScrollHeader();
  var toggle = $(".nav-toggle");
  if (toggle) {
    toggle.addEventListener("click", function () {
      var open = header.classList.toggle("is-open");
      toggle.setAttribute("aria-expanded", open ? "true" : "false");
    });
    $$(".nav a").forEach(function (a) { a.addEventListener("click", function () { header.classList.remove("is-open"); }); });
  }

  /* ------------------------------------------------------------------ aparición al hacer scroll */
  var reveals = $$(".reveal");
  if ("IntersectionObserver" in window && !reduceMotion) {
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (e) { if (e.isIntersecting) { e.target.classList.add("is-in"); io.unobserve(e.target); } });
    }, { threshold: 0.12, rootMargin: "0px 0px -6% 0px" });
    reveals.forEach(function (el) { io.observe(el); });
  } else {
    reveals.forEach(function (el) { el.classList.add("is-in"); });
  }

  /* ------------------------------------------------------------------ paralaje */
  var plx = $$("[data-parallax]").map(function (el) {
    return { el: el, speed: parseFloat(el.getAttribute("data-parallax")) || 0, host: el.closest(".panel, .section") || el.parentElement,
             full: el.classList.contains("layer--full") };
  });
  var ticking = false;
  function parallax() {
    ticking = false;
    var vh = window.innerHeight;
    for (var i = 0; i < plx.length; i++) {
      var p = plx[i], r = p.host.getBoundingClientRect();
      if (r.bottom < -200 || r.top > vh + 200) { continue; }
      var delta = (r.top + r.height / 2) - vh / 2;
      var y = -delta * p.speed;
      if (p.full) { var lim = r.height * 0.16; y = Math.max(-lim, Math.min(lim, y)); }
      p.el.style.transform = "translate3d(0," + y.toFixed(1) + "px,0)";
    }
  }
  function onScroll() {
    onScrollHeader();
    if (!ticking) { ticking = true; requestAnimationFrame(parallax); }
  }
  if (!reduceMotion) {
    window.addEventListener("scroll", onScroll, { passive: true });
    window.addEventListener("resize", onScroll);
    parallax();
  } else {
    window.addEventListener("scroll", onScrollHeader, { passive: true });
  }

  /* ------------------------------------------------------------------ campo de estrellas */
  var sc = $("#stars");
  if (sc && sc.getContext) {
    var sx = sc.getContext("2d"), SW = 0, SH = 0, DPR = 1, stars = [], shoot = null, nextShoot = 4000;
    var LAYERS = [{ f: 0.04, n: 1.0, r: 0.6 }, { f: 0.10, n: 0.55, r: 0.9 }, { f: 0.22, n: 0.28, r: 1.3 }];
    var seed = 7; function rnd() { seed = (seed * 16807) % 2147483647; return (seed - 1) / 2147483646; }
    function initStars() {
      DPR = Math.min(window.devicePixelRatio || 1, 2);
      SW = window.innerWidth; SH = window.innerHeight;
      sc.width = SW * DPR; sc.height = SH * DPR; sx.setTransform(DPR, 0, 0, DPR, 0, 0);
      stars = []; seed = 7;
      var base = Math.round(SW * SH / 5200);
      LAYERS.forEach(function (L, li) {
        for (var i = 0, n = Math.round(base * L.n); i < n; i++) {
          stars.push({ l: li, x: rnd() * SW, y: rnd() * SH, r: L.r * (0.5 + rnd() * 0.8), a: 0.35 + rnd() * 0.65, t: 0.6 + rnd() * 2.2, p: rnd() * 6.28 });
        }
      });
    }
    function drawStars(ts) {
      sx.clearRect(0, 0, SW, SH);
      var sy = window.scrollY;
      for (var i = 0; i < stars.length; i++) {
        var s = stars[i], f = LAYERS[s.l].f;
        var y = ((s.y - sy * f) % SH + SH) % SH;
        var a = s.a * (reduceMotion ? 1 : 0.72 + 0.28 * Math.sin(ts / 1000 * s.t + s.p));
        sx.globalAlpha = a; sx.fillStyle = "#fff";
        sx.beginPath(); sx.arc(s.x, y, s.r, 0, 6.2832); sx.fill();
      }
      sx.globalAlpha = 1;
      if (!reduceMotion) {
        if (!shoot && ts > nextShoot) {
          shoot = { x: SW * (0.35 + Math.random() * 0.6), y: SH * Math.random() * 0.4, vx: -9, vy: 4.2, life: 0 };
          nextShoot = ts + 9000 + Math.random() * 9000;
        }
        if (shoot) {
          shoot.x += shoot.vx; shoot.y += shoot.vy; shoot.life++;
          var g = sx.createLinearGradient(shoot.x, shoot.y, shoot.x - shoot.vx * 9, shoot.y - shoot.vy * 9);
          g.addColorStop(0, "rgba(255,255,255,.9)"); g.addColorStop(1, "rgba(255,255,255,0)");
          sx.strokeStyle = g; sx.lineWidth = 1.2; sx.beginPath(); sx.moveTo(shoot.x, shoot.y);
          sx.lineTo(shoot.x - shoot.vx * 9, shoot.y - shoot.vy * 9); sx.stroke();
          if (shoot.life > 70) { shoot = null; }
        }
      }
    }
    initStars();
    window.addEventListener("resize", function () { initStars(); if (reduceMotion) { drawStars(0); } });
    if (reduceMotion) { drawStars(0); window.addEventListener("scroll", function () { drawStars(0); }, { passive: true }); }
    else { (function loop(ts) { drawStars(ts); requestAnimationFrame(loop); })(0); }
  }

  /* ------------------------------------------------------------------ células (guiño a la simulación de lunagen) */
  $$("canvas[data-cells]").forEach(function (cv) {
    var cx = cv.getContext("2d"), W = 0, H = 0, dpr = 1, cells = [], visible = true;
    var maxCells = parseInt(cv.getAttribute("data-cells"), 10) || 70;
    function color(res, a) {            // reserva 0..1: ámbar → verde → cian (como la ventana de lunagen)
      var h = 38 + res * 150;
      return "hsla(" + h.toFixed(0) + ",90%," + (58 + res * 8).toFixed(0) + "%," + a + ")";
    }
    function spawn(x, y, ang, len) {
      return { x: x, y: y, a: ang, len: len || 0.5, vx: (Math.random() - 0.5) * 0.35, vy: (Math.random() - 0.5) * 0.35,
               va: (Math.random() - 0.5) * 0.004, res: 0.2 + Math.random() * 0.8, grow: 0.0008 + Math.random() * 0.0012,
               ph: Math.random() * 6.28, life: 1 };
    }
    function resize() {
      dpr = Math.min(window.devicePixelRatio || 1, 2);
      var r = cv.getBoundingClientRect(); W = r.width; H = r.height;
      cv.width = W * dpr; cv.height = H * dpr; cx.setTransform(dpr, 0, 0, dpr, 0, 0);
      var n0 = Math.max(24, Math.min(maxCells, Math.round(W * H / 21000)));
      cells = [];
      for (var i = 0; i < n0; i++) { cells.push(spawn(Math.random() * W, Math.random() * H, Math.random() * 6.28, 0.5 + Math.random() * 0.5)); }
    }
    function step(ts) {
      cx.clearRect(0, 0, W, H);
      var born = [];
      for (var i = cells.length - 1; i >= 0; i--) {
        var c = cells[i];
        c.x += c.vx + Math.sin(ts / 2600 + c.ph) * 0.12; c.y += c.vy + Math.cos(ts / 3100 + c.ph) * 0.12; c.a += c.va;
        if (c.x < -30) { c.x = W + 30; } if (c.x > W + 30) { c.x = -30; } if (c.y < -30) { c.y = H + 30; } if (c.y > H + 30) { c.y = -30; }
        c.len += c.grow;
        if (c.len >= 1) {                                   // división
          c.len = 0.5; if (cells.length + born.length < maxCells) {
            var dx = Math.cos(c.a) * 7, dy = Math.sin(c.a) * 7;
            born.push(spawn(c.x + dx, c.y + dy, c.a + (Math.random() - 0.5) * 0.4, 0.5)); c.x -= dx; c.y -= dy;
          } else { cells.splice(i, 1); continue; }          // tope de población: muere
        }
        var L = 7 + c.len * 14, half = Math.max(0, L / 2 - 2.6), ca = Math.cos(c.a), sa = Math.sin(c.a);
        cx.lineCap = "round"; cx.lineWidth = 5.2; cx.strokeStyle = color(c.res, 0.5 + 0.2 * Math.sin(ts / 1500 + c.ph));
        cx.shadowColor = color(c.res, 0.8); cx.shadowBlur = 10;
        cx.beginPath(); cx.moveTo(c.x - ca * half, c.y - sa * half); cx.lineTo(c.x + ca * half, c.y + sa * half); cx.stroke();
      }
      cx.shadowBlur = 0;
      for (var j = 0; j < born.length; j++) { cells.push(born[j]); }
      if (cells.length < 20) { cells.push(spawn(Math.random() * W, Math.random() * H, Math.random() * 6.28, 0.5)); }
    }
    resize();
    window.addEventListener("resize", resize);
    if ("IntersectionObserver" in window) {
      new IntersectionObserver(function (es) { visible = es[0].isIntersecting; }, { threshold: 0 }).observe(cv);
    }
    if (reduceMotion) { step(0); }
    else { (function loop(ts) { if (visible) { step(ts); } requestAnimationFrame(loop); })(0); }
  });

  /* ------------------------------------------------------------------ botones de copiar */
  function flash(btn) {
    var old = btn.innerHTML; btn.classList.add("is-done"); btn.textContent = "✓";
    setTimeout(function () { btn.innerHTML = old; btn.classList.remove("is-done"); }, 1400);
  }
  function copyText(txt, btn) {
    function fallback() {
      var ta = doc.createElement("textarea"); ta.value = txt; ta.style.position = "fixed"; ta.style.opacity = "0";
      doc.body.appendChild(ta); ta.select(); try { doc.execCommand("copy"); } catch (e) { /* nada */ } doc.body.removeChild(ta); flash(btn);
    }
    if (navigator.clipboard && window.isSecureContext) { navigator.clipboard.writeText(txt).then(function () { flash(btn); }, fallback); }
    else { fallback(); }
  }
  doc.addEventListener("click", function (e) {
    var b = e.target.closest && e.target.closest(".copy");
    if (!b) { return; }
    var txt = b.getAttribute("data-copy");
    if (!txt) { var pre = b.parentElement.querySelector("pre, code"); txt = pre ? pre.innerText.replace(/\s+$/, "") : ""; }
    copyText(txt, b);
  });
  $$(".prose pre").forEach(function (pre) {
    var b = doc.createElement("button"); b.type = "button"; b.className = "copy";
    b.innerHTML = '<span data-lang="es">Copiar</span><span data-lang="en">Copy</span>';
    pre.appendChild(b);
  });

  /* ------------------------------------------------------------------ documentación: índice lateral */
  var toc = $(".toc"), spyLinks = [];
  function updateSpy() {
    if (!toc) { return; }
    var lang = root.lang, block = $('.prose [data-lang="' + lang + '"]');
    if (!block) { return; }
    var heads = $$("h2[id], h3[id]", block), cur = null;
    for (var i = 0; i < heads.length; i++) { if (heads[i].getBoundingClientRect().top < 170) { cur = heads[i]; } }
    $$(".toc a").forEach(function (a) { a.classList.toggle("active", !!cur && a.getAttribute("href") === "#" + cur.id); });
  }
  if (toc) {
    window.addEventListener("scroll", function () { requestAnimationFrame(updateSpy); }, { passive: true });
    updateSpy();
    var tt = $(".toc-toggle");
    if (tt) { tt.addEventListener("click", function () { toc.classList.toggle("is-open"); }); }
    $$(".toc a").forEach(function (a) { a.addEventListener("click", function () { toc.classList.remove("is-open"); }); });
  }

  /* ------------------------------------------------------------------ año del pie */
  $$("[data-year]").forEach(function (el) { el.textContent = new Date().getFullYear(); });
})();
