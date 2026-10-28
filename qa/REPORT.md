# Just One More Bite: QA report

Generated 2026-10-28 16:07 by `tools/qa.py` in 33 s · 1 page(s) · widths (browser checks skipped) · Lighthouse on · production pass on

**Result: PASS** · 0 fail(s), 2 warning(s) · site QA score **100/100** (per page: 100 − 8 per FAIL − 2 per WARN)

## Summary

| Page | Score | SEO | Schema | Facts | Responsive | A11y | LH mobile P/A/BP/SEO | LH desktop P/A/BP/SEO | Mobile LCP · CLS · TBT · KB |
|---|---|---|---|---|---|---|---|---|---|
| [home](#home) | 100 | ✅ | ✅ | ✅ | — | — | 100/100/100/66 (100†) / prod 100 | 100/100/100/66 (100†) | 1.1s · 0.000 · 28ms · 508 |

† Preview builds carry `noindex` on purpose, so Lighthouse SEO fails *Page is blocked from indexing*. The number in brackets is the SEO score without that audit; `prod` is the score from a temporary copy built with `"preview": false` (the real site.json is never edited).

## System-level issues (site.css · site.js · build.py)

- ⚠️ **WARN** [Facts · proposed-offer] `src/site.json membership`: membership status is "proposed" but 13 page(s) present it as a live offer ("save 5–12%", prices, sign-up); only 3 say proposed/draft: about-jomb, delivery-area, family-meal-delivery, faq, how-it-works, home, low-carb-dairy-free-meals, meal-plans, menus, paleo-meal-delivery, pricing, protein-by-the-pound, zone-meal-delivery · pages: (site)
  - Fix: BRAND_GUIDE §2: proposed offers are never shown as live. Gate the membership blocks on a membership.enabled switch (off in preview, like compliance), or label them "Proposed" until Mike approves.
- ⚠️ **WARN** [Facts · site-json] `src/site.json`: prices.zone_all: $253 ÷ 18 meals = $14.0556, which rounds to $14.06, but per = $14.05 · pages: (site)
  - Fix: Confirm the per-meal figure with the JOMB Store (the store may show the truncated value), then make per match.

## Page issues

### home

Title (59): Just One More Bite | Chef-Made Meal Delivery in Raleigh, NC · description 153 chars · internal links in main: 15

No page-level FAIL/WARN.

<details><summary>Info (1)</summary>

- [Schema · offer-price] 7 OfferCatalog entries have no price (fine for a catalog listing)

</details>

<details><summary>Facts seen on this page</summary>

- **phones**: (919) 443-5408
- **emails**: jomborders@gmail.com
- **deadlines**: Saturday at 8 PM, Order by Saturday, Saturday at 8 PM., Saturday · 8 PM, close Saturday, Saturday 8 PM
- **delivery**: Delivered Tuesday, arrives Tuesday, Tuesday · 10 AM, delivered Tuesday, Tuesday between 10 AM, delivered on Tuesday, delivers Tuesday., delivered Tuesdays, Tuesday delivery
- **windows**: 10 AM – 5 PM
- **menu_posted**: menu every Wednesday, menu drops every Wednesday, menu posts every Wednesday, menu goes up every Wednesday
- **prices**: $12.25, $14.05, $14.50, $12.50, $75, $213.75, $71.25, $337.50, $67.50, $162.00, $16.20, $269.50, $12.83, $20, $35, $50
- **years**: 20+ years

</details>

<details><summary>Lighthouse audits below target</summary>

- mobile · performance · Use efficient cache lifetimes — Est savings of 441 KiB (http://127.0.0.1:59351/justonemorebite/img/zone-plate-800.webp, http://127.0.0.1:59351/justonemorebite/img/paleo-plate-800.webp)
- mobile · performance · Forced reflow
- mobile · performance · Network dependency tree
- mobile · performance · Render-blocking requests — Est savings of 150 ms (http://127.0.0.1:59351/justonemorebite/assets/css/site.css)
- mobile · performance · Minify CSS — Est savings of 3 KiB (http://127.0.0.1:59351/justonemorebite/assets/css/site.css)
- mobile · performance · Reduce unused CSS — Est savings of 14 KiB (http://127.0.0.1:59351/justonemorebite/assets/css/site.css)
- desktop · performance · Use efficient cache lifetimes — Est savings of 400 KiB (http://127.0.0.1:59351/justonemorebite/img/meals-tray-800.webp, http://127.0.0.1:59351/justonemorebite/assets/fonts/fraunces-latin.woff2)
- desktop · performance · Forced reflow
- desktop · performance · Improve image delivery — Est savings of 173 KiB (div.plans > article.plan > div.plan-photo > img, div.plans > article.plan > div.plan-photo > img)
- desktop · performance · Network dependency tree
- desktop · performance · Render-blocking requests — Est savings of 40 ms (http://127.0.0.1:59351/justonemorebite/assets/css/site.css)
- desktop · performance · Minify CSS — Est savings of 3 KiB (http://127.0.0.1:59351/justonemorebite/assets/css/site.css)
- desktop · performance · Reduce unused CSS — Est savings of 14 KiB (http://127.0.0.1:59351/justonemorebite/assets/css/site.css)

</details>

### (site)

No page-level FAIL/WARN. (2 system-level issue(s) listed above.)

<details><summary>Info (8)</summary>

- [Facts · site-json] membership.menus.zone.breakfast duplicates prices.zone_breakfast.per (12.25); it matches today
- [Facts · site-json] membership.menus.zone.lunch duplicates prices.zone_lunch.per (13.50); it matches today
- [Facts · site-json] membership.menus.zone.dinner duplicates prices.zone_dinner.per (18.00); it matches today
- [Facts · site-json] membership.menus.paleo.lunch duplicates prices.paleo_lunch.per (14.50); it matches today
- [Facts · site-json] membership.menus.paleo.dinner duplicates prices.paleo_dinner.per (19.50); it matches today
- [Facts · site-json] membership.menus.lcdf.lunch duplicates prices.lcdf_lunch.per (12.50); it matches today
- [Facts · site-json] membership.menus.lcdf.dinner duplicates prices.lcdf_dinner.per (18.00); it matches today
- [Facts · proposed-offer] membership adds a Friday second delivery (Delivered Tuesday; 5- and 7-day plans get a second delivery Friday so every meal is fresh); that's a new operational promise beyond site.json's Tuesday delivery

</details>

## How to run

```bash
<venv>/bin/python tools/qa.py                       # everything (~1 min per page with Lighthouse)
<venv>/bin/python tools/qa.py --pages home,menus --no-lighthouse
python3 tools/qa.py --no-browser --no-lighthouse    # static checks only, standard library
```

Checks: SEO basics, JSON-LD (FAQ text = visible text, phone = tel: links), fact consistency against `src/site.json` (phone, deadline, delivery day/window, menu day, prices, email), banned claims (medical, superlatives, AI filler), regulatory trust claims outside the `compliance` switch, street addresses and legal hedging, responsive layout at 320–1440 px (overflow, clipped text, tap targets, console errors, failed requests, the 404 page at a nested URL), axe-core WCAG 2.2 AA, and Lighthouse mobile + desktop. Exit code 1 on any FAIL.
