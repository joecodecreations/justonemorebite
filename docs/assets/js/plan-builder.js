/* JOMB Membership plan builder (meal-plans page).
   Reads the model from <script type="application/json" id="membership-data"> (written by build.py from
   site.json -> membership). The math mirrors plan_quote() in build.py exactly, including Python's
   round-half-even, so the builder always agrees with the static featured cards and price charts.
   No prices live in this file. */
(function () {
  "use strict";
  var d = document;
  var dataEl = d.getElementById("membership-data");
  if (!dataEl) return;
  var M;
  try { M = JSON.parse(dataEl.textContent); } catch (e) { return; }

  var reduceMotion = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  var has = function (o, k) { return Object.prototype.hasOwnProperty.call(o, k); };
  var find = function (list, key) { for (var i = 0; i < list.length; i++) if (list[i].key === key) return list[i]; return null; };

  // ---------- math (mirror of build.py plan_quote) ----------
  // Python's round(x, n): correctly rounded from the exact binary value, ties to even.
  // toFixed is also exact but breaks ties upward, so detect exact ties and fix them.
  function pyRound(x, nd) {
    nd = nd || 0;
    var ax = Math.abs(x);
    var s = ax.toFixed(nd + 25);
    var dot = s.indexOf(".");
    var tail = s.slice(dot + 1 + nd);
    var r;
    if (/^50*$/.test(tail)) {
      var head = s.slice(0, nd ? dot + 1 + nd : dot);
      var last = +head.charAt(head.length - 1);
      r = last % 2 === 0 ? Number(head) : Number((Number(head) + Math.pow(10, -nd)).toFixed(nd));
    } else {
      r = Number(ax.toFixed(nd));
    }
    return x < 0 ? -r : r;
  }

  function quote(household, days, coverage, menu) {
    var hh = find(M.households, household);
    days = parseInt(days, 10);
    var disc = M.discount[String(days)];
    var meals, base, unit;
    if (has(hh, "family_dinners")) {
      meals = days * hh.family_dinners;
      base = meals * M.family_dinner;
      unit = "family dinner";
    } else {
      var cov = find(M.coverage, coverage);
      var perDay = 0;
      for (var i = 0; i < cov.meals.length; i++) perDay += M.menus[menu][cov.meals[i]];
      meals = days * cov.meals.length * hh.people;
      base = perDay * days * hh.people;
      unit = "meal";
    }
    var price = pyRound(base * (1 - disc), 2);
    return {
      base: pyRound(base, 2), price: price, save: pyRound(base - price, 2), per: pyRound(price / meals, 2),
      meals: meals, unit: unit, monthly: pyRound(price * M.weeks_per_month, 0), disc: disc,
      deliveries: M.deliveries[String(days)]
    };
  }
  // exposed for automated checks against build.py
  window.JOMBPlanQuote = quote;

  function money(v) { return "$" + v.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 }); }
  function wholeMoney(v) { return "$" + Math.round(v).toLocaleString("en-US"); }
  function pct(disc) { return Math.round(disc * 100) + "%"; }
  function plural(n, word) { return n + " " + word + (n === 1 ? "" : "s"); }

  var isFamily = function (hk) { var h = find(M.households, hk); return !!h && has(h, "family_dinners"); };
  function coverageOk(c, menuKey) {
    if (c.menus && c.menus.indexOf(menuKey) < 0) return false;
    var mv = M.menus[menuKey];
    for (var i = 0; i < c.meals.length; i++) if (!has(mv, c.meals[i])) return false;
    return true;
  }

  // ---------- page-wide enhancements (work even if the builder is absent) ----------
  function enhanceStatic() {
    // hero numbers: lowest weekly price and the top subscriber discount, straight from the model
    var maxDisc = 0;
    Object.keys(M.discount).forEach(function (k) { if (M.discount[k] > maxDisc) maxDisc = M.discount[k]; });
    var from = Infinity;
    M.households.forEach(function (h) {
      M.days.forEach(function (dy) {
        if (has(h, "family_dinners")) { from = Math.min(from, quote(h.key, dy).price); return; }
        Object.keys(M.menus).forEach(function (mk) {
          M.coverage.forEach(function (c) { if (coverageOk(c, mk)) from = Math.min(from, quote(h.key, dy, c.key, mk).price); });
        });
      });
    });
    d.querySelectorAll('[data-mbr="maxsave"]').forEach(function (el) { el.textContent = pct(maxDisc); });
    if (isFinite(from)) d.querySelectorAll('[data-mbr="from"]').forEach(function (el) { el.textContent = money(from); });

    // featured cards: highlight "Most popular" and add "Customize" (cards are rendered in model order)
    var cards = d.querySelectorAll(".mbr-plan");
    cards.forEach(function (card, i) {
      var f = (M.featured || [])[i];
      if (!f) return;
      if (/popular/i.test(f.tag || "")) card.classList.add("mbr-plan--popular");
      if (!builder) return;
      var b = d.createElement("button");
      b.type = "button";
      b.className = "mbr-customize";
      b.innerHTML = "Customize this plan<span class=\"sr-only\">: " + esc(f.name) + "</span>";
      b.addEventListener("click", function () {
        interacted = true;
        urlReady = true;
        setState({ household: f.household, days: f.days, coverage: f.coverage, menu: f.menu === "family" ? state.menu : f.menu });
        var target = d.getElementById("builder");
        if (target) target.scrollIntoView({ behavior: reduceMotion ? "auto" : "smooth", block: "start" });
        var checked = builder.querySelector("input:checked");
        if (checked) setTimeout(function () { checked.focus({ preventScroll: true }); }, reduceMotion ? 0 : 500);
      });
      card.appendChild(b);
    });
  }

  function esc(s) { return String(s).replace(/[&<>"']/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]; }); }

  // ---------- builder ----------
  var builder = d.querySelector("[data-builder]");
  var state = null;
  var outs = {};

  var MENU_NOTE = { zone: "4-block macros", paleo: "No grains, dairy or added sugar", lcdf: "Lighter, low-carb" };
  var COV_SHORT = { dinner: "Dinners", lunch_dinner: "Lunch & Dinner", all: "All-Day" };
  var MEAL_LABEL = { breakfast: "Breakfast", lunch: "Lunch", dinner: "Dinner" };

  function chip(name, value, title, sub, extraClass) {
    var id = "b-" + name + "-" + value;
    return '<label class="builder-chip' + (extraClass ? " " + extraClass : "") + '" for="' + id + '">' +
      '<input class="builder-radio" type="radio" name="b-' + name + '" id="' + id + '" value="' + esc(value) + '">' +
      '<span class="builder-face"><b>' + title + "</b>" + (sub ? "<small>" + sub + "</small>" : "") + "</span></label>";
  }

  function renderOptions() {
    var html = { household: "", days: "", menu: "", coverage: "" };
    M.households.forEach(function (h) {
      var sub = has(h, "family_dinners")
        ? plural(h.family_dinners, "family dinner") + " a night"
        : (h.people === 1 ? "1 person" : h.people + " people");
      html.household += chip("household", h.key, esc(h.label), esc(sub));
    });
    M.days.forEach(function (dy) {
      html.days += chip("days", String(dy), '<span class="builder-num">' + dy + "</span> days",
        '<span class="builder-save-word">save </span><span class="builder-save-minus" aria-hidden="true">−</span>' + pct(M.discount[String(dy)]), "builder-chip--day");
    });
    Object.keys(M.menus).forEach(function (mk) {
      html.menu += chip("menu", mk, esc(M.menus[mk].label), esc(MENU_NOTE[mk] || ""));
    });
    M.coverage.forEach(function (c) {
      var sub = c.menus ? c.menus.map(function (k) { return M.menus[k] ? M.menus[k].label : k; }).join(", ") + " menu only" : plural(c.meals.length, "meal") + " a day";
      html.coverage += chip("coverage", c.key, esc(c.label), esc(sub));
    });
    Object.keys(html).forEach(function (k) {
      var box = builder.querySelector('[data-options="' + k + '"]');
      if (box) box.innerHTML = html[k];
    });
  }

  function featuredMatch(s) {
    var fam = isFamily(s.household);
    var list = M.featured || [];
    for (var i = 0; i < list.length; i++) {
      var f = list[i];
      if (f.household !== s.household || +f.days !== +s.days) continue;
      if (fam || (f.coverage === s.coverage && f.menu === s.menu)) return f;
    }
    return null;
  }

  function describe(s, q) {
    var hh = find(M.households, s.household);
    var fam = has(hh, "family_dinners");
    var cov = find(M.coverage, fam ? "dinner" : s.coverage);
    var menuLabel = fam ? "Family menu" : M.menus[s.menu].label;
    var f = featuredMatch(s);
    var name;
    if (f) name = f.name;
    else if (fam) name = (hh.family_dinners > 1 ? "Big Family " : "Family ") + s.days;
    else name = (M.menus[s.menu].label + " " + (COV_SHORT[s.coverage] || cov.label)) + (hh.people === 2 ? " for Two" : hh.people > 2 ? " for " + hh.people : "") + " · " + s.days + " days";
    var detail = hh.label + " · " + s.days + " days a week · " + cov.label.toLowerCase() + " · " + menuLabel;
    return { name: name, tag: f ? f.tag : "", detail: detail, fam: fam, hh: hh, cov: cov };
  }

  function mailto(name, detail) {
    var body = "Hi Chef Mike,\n\nI'd like to start the " + name + " plan (" + detail + ").\n\nName:\nDelivery address (home, office or gym):\n" +
      "Phone:\nAny allergies:\nStart week:\n\nThanks!";
    return "mailto:" + M.email + "?subject=" + encodeURIComponent("JOMB Membership: " + name) + "&body=" + encodeURIComponent(body);
  }

  function setText(key, text) { (outs[key] || []).forEach(function (el) { el.textContent = text; }); }

  // smooth number roll for the weekly price
  var anim = {};
  function rollMoney(key, to) {
    (outs[key] || []).forEach(function (el, i) {
      var id = key + i;
      var from = parseFloat(el.getAttribute("data-value") || "NaN");
      el.setAttribute("data-value", String(to));
      if (anim[id]) cancelAnimationFrame(anim[id]);
      if (reduceMotion || isNaN(from) || from === to) { el.textContent = money(to); return; }
      var t0 = null, dur = 420;
      var step = function (t) {
        if (t0 === null) t0 = t;
        var k = Math.min(1, (t - t0) / dur);
        var e = 1 - Math.pow(1 - k, 3);
        el.textContent = money(k < 1 ? Math.round((from + (to - from) * e) * 100) / 100 : to);
        if (k < 1) anim[id] = requestAnimationFrame(step);
      };
      anim[id] = requestAnimationFrame(step);
    });
  }

  function weekGrid(s, info, q) {
    var firstDay = builder.getAttribute("data-first-day") || "Tuesday";
    var secondDay = builder.getAttribute("data-second-day") || "Friday";
    var split = q.deliveries > 1 ? Math.ceil(s.days / 2) : s.days;
    var rows = info.fam
      ? [{ label: "Family dinner", times: info.hh.family_dinners }]
      : info.cov.meals.map(function (m) { return { label: MEAL_LABEL[m] || m, times: info.hh.people }; });
    var html = '<div class="builder-week-head"><span>Your week at a glance</span><span class="builder-legend">' +
      '<span><i class="is-a"></i>' + esc(firstDay) + "</span>" + (q.deliveries > 1 ? '<span><i class="is-b"></i>' + esc(secondDay) + "</span>" : "") + "</span></div>";
    rows.forEach(function (r) {
      var dots = "";
      for (var i = 0; i < s.days; i++) dots += '<i class="' + (i < split ? "is-a" : "is-b") + '"></i>';
      html += '<div class="builder-week-row"><span class="builder-week-label">' + esc(r.label) + '</span><span class="builder-dots">' + dots +
        '</span><span class="builder-week-x">' + (r.times > 1 ? "×" + r.times : "") + "</span></div>";
    });
    return html;
  }

  var liveTimer = null, lastWeekKey = "", interacted = false;
  function update() {
    var s = state;
    var fam = isFamily(s.household);
    var q = fam ? quote(s.household, s.days) : quote(s.household, s.days, s.coverage, s.menu);
    var info = describe(s, q);

    builder.querySelectorAll('[data-for="individual"]').forEach(function (el) { el.hidden = fam; });
    builder.querySelectorAll('[data-for="family"]').forEach(function (el) { el.hidden = !fam; });
    if (fam) setText("familynote", info.hh.note || "");

    // coverage availability depends on the menu (breakfast is Zone-only)
    builder.querySelectorAll('input[name="b-coverage"]').forEach(function (inp) {
      var c = find(M.coverage, inp.value);
      inp.disabled = !coverageOk(c, s.menu);
      inp.closest(".builder-chip").classList.toggle("is-disabled", inp.disabled);
    });

    rollMoney("price", q.price);
    setText("base", money(q.base));
    setText("save", "Save " + money(q.save) + " a week (" + pct(q.disc) + ")");
    setText("perlabel", "Per " + q.unit);
    setText("per", money(q.per));
    setText("monthly", wholeMoney(q.monthly));
    setText("meals", plural(q.meals, q.unit));
    var firstDay = builder.getAttribute("data-first-day") || "Tuesday";
    var secondDay = builder.getAttribute("data-second-day") || "Friday";
    setText("deliveries", q.deliveries > 1 ? q.deliveries + " · " + firstDay.slice(0, 3) + " + " + secondDay.slice(0, 3) : "1 · " + firstDay);
    setText("name", info.name);
    setText("detail", info.detail);
    setText("barsub", money(q.per) + " per " + q.unit + " · save " + pct(q.disc));
    (outs.tag || []).forEach(function (el) { el.textContent = info.tag; el.hidden = !info.tag; });
    (outs.mailto || []).forEach(function (el) { el.href = mailto(info.name, info.detail + " · " + money(q.price) + " a week"); });

    var weekKey = [s.household, s.days, fam ? "" : s.coverage].join("|");
    if (weekKey !== lastWeekKey) {
      lastWeekKey = weekKey;
      (outs.week || []).forEach(function (el) { el.innerHTML = weekGrid(s, info, q); });
    }

    var bar = d.querySelector("[data-builder-bar]");
    if (bar && !reduceMotion) { bar.classList.remove("is-bump"); void bar.offsetWidth; bar.classList.add("is-bump"); }

    if (!interacted) return;
    clearTimeout(liveTimer);
    liveTimer = setTimeout(function () {
      setText("live", info.name + ": " + money(q.price) + " a week, " + money(q.per) + " per " + q.unit + ", " +
        plural(q.meals, q.unit) + " a week. You save " + money(q.save) + " a week, " + pct(q.disc) + " off one-off prices.");
    }, 350);
  }

  function syncInputs() {
    ["household", "days", "menu", "coverage"].forEach(function (k) {
      var inp = builder.querySelector('input[name="b-' + k + '"][value="' + state[k] + '"]');
      if (inp) inp.checked = true;
    });
  }

  function normalize(s) {
    if (!find(M.households, s.household)) s.household = M.households[0].key;
    if (M.days.indexOf(+s.days) < 0) s.days = M.days[0];
    s.days = +s.days;
    if (!M.menus[s.menu]) s.menu = Object.keys(M.menus)[0];
    var c = find(M.coverage, s.coverage);
    var hint = "";
    if (!c || !coverageOk(c, s.menu)) {
      // fall back to the richest coverage this menu offers
      var best = null;
      M.coverage.forEach(function (cc) { if (coverageOk(cc, s.menu) && (!best || cc.meals.length > best.meals.length)) best = cc; });
      if (c && best) hint = c.label + " is on the " + (c.menus || []).map(function (k) { return M.menus[k] ? M.menus[k].label : k; }).join(", ") + " menu only, so we switched you to " + best.label.toLowerCase() + ".";
      s.coverage = best ? best.key : M.coverage[0].key;
    }
    return hint;
  }

  function setState(patch) {
    var prevCoverage = state && state.coverage;
    var next = {};
    Object.keys(state || {}).forEach(function (k) { next[k] = state[k]; });
    Object.keys(patch).forEach(function (k) { if (patch[k] != null) next[k] = patch[k]; });
    var hint = normalize(next);
    state = next;
    syncInputs();
    var zoneOnly = M.coverage.filter(function (c) { return c.menus; }).map(function (c) {
      return c.label.split(",")[0] + " is on the " + c.menus.map(function (k) { return M.menus[k] ? M.menus[k].label : k; }).join(", ") + " menu.";
    }).join(" ");
    setText("coveragehint", hint && prevCoverage !== state.coverage ? hint : zoneOnly);
    update();
    writeUrl();
  }

  function readUrl() {
    var out = {};
    try {
      var p = new URLSearchParams(location.search);
      ["household", "days", "menu", "coverage"].forEach(function (k) { if (p.get(k)) out[k] = p.get(k); });
    } catch (e) { /* old browser: ignore */ }
    return out;
  }
  var urlReady = false;
  function writeUrl() {
    if (!urlReady || !window.history || !history.replaceState) return;
    try {
      var p = new URLSearchParams(location.search);
      ["household", "days", "menu", "coverage"].forEach(function (k) { p.set(k, state[k]); });
      if (isFamily(state.household)) { p.delete("menu"); p.delete("coverage"); }
      history.replaceState(null, "", location.pathname + "?" + p.toString() + location.hash);
    } catch (e) { /* file:// or sandboxed: ignore */ }
  }

  function initBuilder() {
    builder.hidden = false;
    renderOptions();
    builder.querySelectorAll("[data-out]").forEach(function (el) {
      var k = el.getAttribute("data-out");
      (outs[k] = outs[k] || []).push(el);
    });
    d.querySelectorAll("[data-builder-bar] [data-out]").forEach(function (el) {
      var k = el.getAttribute("data-out");
      (outs[k] = outs[k] || []).push(el);
    });

    var pop = null;
    (M.featured || []).forEach(function (f) { if (!pop && /popular/i.test(f.tag || "")) pop = f; });
    pop = pop || (M.featured || [])[0] || {};
    var fromUrl = readUrl();
    state = {};
    setState({
      household: fromUrl.household || pop.household,
      days: fromUrl.days || pop.days,
      menu: fromUrl.menu || (pop.menu && M.menus[pop.menu] ? pop.menu : "zone"),
      coverage: fromUrl.coverage || pop.coverage
    });
    urlReady = Object.keys(fromUrl).length > 0;

    var form = builder.querySelector("form");
    form.addEventListener("submit", function (e) { e.preventDefault(); });
    form.addEventListener("change", function (e) {
      var t = e.target;
      if (!t || t.type !== "radio") return;
      urlReady = true;
      interacted = true;
      var patch = {};
      patch[t.name.replace(/^b-/, "")] = t.value;
      setState(patch);
    });

    // mobile summary bar: visible while the options are on screen and the full summary isn't
    var bar = d.querySelector("[data-builder-bar]");
    var summary = builder.querySelector(".builder-summary");
    if (bar && summary && "IntersectionObserver" in window) {
      var formIn = false, sumIn = false;
      var refresh = function () {
        var on = formIn && !sumIn;
        bar.classList.toggle("is-visible", on);
        d.body.classList.toggle("builder-bar-on", on);
      };
      new IntersectionObserver(function (en) { en.forEach(function (x) { formIn = x.isIntersecting; }); refresh(); }, { rootMargin: "-20% 0px -10% 0px" }).observe(form);
      new IntersectionObserver(function (en) { en.forEach(function (x) { sumIn = x.isIntersecting; }); refresh(); }, { threshold: 0.25 }).observe(summary);
      bar.querySelector("a").addEventListener("click", function (e) {
        e.preventDefault();
        summary.scrollIntoView({ behavior: reduceMotion ? "auto" : "smooth", block: "start" });
      });
    }
  }

  if (builder) initBuilder();
  enhanceStatic();
})();
