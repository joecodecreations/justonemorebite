(function () {
  var d = document, root = d.documentElement;
  root.classList.add("js");

  // mobile nav sheet
  var sheet = d.getElementById("nav-sheet");
  var openers = d.querySelectorAll("[data-nav-open]");
  var closers = d.querySelectorAll("[data-nav-close]");
  function setNav(open) {
    if (!sheet) return;
    sheet.classList.toggle("is-open", open);
    sheet.setAttribute("aria-hidden", open ? "false" : "true");
    d.body.classList.toggle("nav-open", open);
    openers.forEach(function (b) { b.setAttribute("aria-expanded", open ? "true" : "false"); });
    if (open) { var f = sheet.querySelector("a, button"); if (f) f.focus(); }
  }
  openers.forEach(function (b) { b.addEventListener("click", function () { setNav(true); }); });
  closers.forEach(function (b) { b.addEventListener("click", function () { setNav(false); }); });
  d.addEventListener("keydown", function (e) { if (e.key === "Escape") setNav(false); });
  if (sheet) sheet.querySelectorAll("nav a").forEach(function (a) { a.addEventListener("click", function () { setNav(false); }); });

  // header shadow + mobile action bar
  var header = d.querySelector(".site-header");
  var bar = d.querySelector(".mobile-bar");
  var ticking = false;
  function onScroll() {
    var y = window.scrollY || 0;
    if (header) header.classList.toggle("is-scrolled", y > 8);
    if (bar) bar.classList.toggle("is-visible", y > 420);
    ticking = false;
  }
  window.addEventListener("scroll", function () { if (!ticking) { ticking = true; requestAnimationFrame(onScroll); } }, { passive: true });
  onScroll();

  // reveal on scroll
  var els = d.querySelectorAll(".reveal");
  if ("IntersectionObserver" in window && els.length) {
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (en) { if (en.isIntersecting) { en.target.classList.add("is-in"); io.unobserve(en.target); } });
    }, { rootMargin: "0px 0px -8% 0px", threshold: 0.08 });
    els.forEach(function (el) { io.observe(el); });
  } else { els.forEach(function (el) { el.classList.add("is-in"); }); }
})();
