# Just One More Bite: QA report

Generated 2026-10-28 17:05 by `tools/qa.py` in 240 s · 20 page(s) · widths 320, 360, 390, 414, 768, 1024, 1280, 1440 · Lighthouse skipped · production pass on

**Result: FAIL** · 1 fail(s), 15 warning(s) · site QA score **98/100** (per page: 100 − 8 per FAIL − 2 per WARN)

## Summary

| Page | Score | SEO | Schema | Facts | Responsive | A11y | LH mobile P/A/BP/SEO | LH desktop P/A/BP/SEO | Mobile LCP · CLS · TBT · KB |
|---|---|---|---|---|---|---|---|---|---|
| [about-jomb](#about-jomb) | 98 | ✅ | ✅ | ⚠️ 1W | ✅ | ✅ | — | — | — |
| [catering-weddings](#catering-weddings) | 100 | ✅ | ✅ | ✅ | ✅ | ✅ | — | — | — |
| [chef-michael-saunders](#chef-michael-saunders) | 100 | ✅ | ✅ | ✅ | ✅ | ✅ | — | — | — |
| [contact](#contact) | 100 | ✅ | ✅ | ✅ | ✅ | ✅ | — | — | — |
| [delivery-area](#delivery-area) | 100 | ✅ | ✅ | ✅ | ✅ | ✅ | — | — | — |
| [family-meal-delivery](#family-meal-delivery) | 100 | ✅ | ✅ | ✅ | ✅ | ✅ | — | — | — |
| [faq](#faq) | 96 | ✅ | ✅ | ⚠️ 2W | ✅ | ✅ | — | — | — |
| [gift-cards](#gift-cards) | 100 | ✅ | ✅ | ✅ | ✅ | ✅ | — | — | — |
| [how-it-works](#how-it-works) | 98 | ✅ | ✅ | ⚠️ 1W | ✅ | ✅ | — | — | — |
| [home](#home) | 92 | ✅ | ✅ | ✅ | ✅ | ❌ 1F/0W | — | — | — |
| [low-carb-dairy-free-meals](#low-carb-dairy-free-meals) | 100 | ✅ | ✅ | ✅ | ✅ | ✅ | — | — | — |
| [meal-plans](#meal-plans) | 98 | ✅ | ✅ | ⚠️ 1W | ✅ | ✅ | — | — | — |
| [menus](#menus) | 100 | ✅ | ✅ | ✅ | ✅ | ✅ | — | — | — |
| [paleo-meal-delivery](#paleo-meal-delivery) | 100 | ✅ | ✅ | ✅ | ✅ | ✅ | — | — | — |
| [pricing](#pricing) | 84 | ✅ | ✅ | ⚠️ 8W | ✅ | ✅ | — | — | — |
| [private-chef-raleigh](#private-chef-raleigh) | 100 | ✅ | ✅ | ✅ | ✅ | ✅ | — | — | — |
| [protein-by-the-pound](#protein-by-the-pound) | 100 | ✅ | ✅ | ✅ | ✅ | ✅ | — | — | — |
| [reviews](#reviews) | 100 | ✅ | ✅ | ✅ | ✅ | ✅ | — | — | — |
| [zone-meal-delivery](#zone-meal-delivery) | 100 | ✅ | ✅ | ✅ | ✅ | ✅ | — | — | — |
| [404](#404) | 100 | ✅ | ✅ | ✅ | ✅ | ✅ | — | — | — |

## System-level issues (site.css · site.js · build.py)

- ❌ **FAIL** [A11y · axe:color-contrast] `li:nth-child(1) > .mbr-mini-name`: Elements must meet minimum color contrast ratio thresholds (serious, 12 elements): li:nth-child(1) > .mbr-mini-name, li:nth-child(1) > strong > small, li:nth-child(1) > .mbr-mini-note, li:nth-child(2) > .mbr-mini-name, li:nth-child(2) > strong > small, li:nth-child(2) > .mbr-mini-note … [at 390, 1440 px] · pages: home
  - Fix: Element has insufficient color contrast of 4.25 (foreground color: #ffffff, background color: #ce533f, font size: 9.1pt (12.16px), font weight: normal). Expected contrast ratio of 4.5:1 First element: <span class="mbr-mini-name">Family 3</span> — https://dequeuniversity.com/rules/axe/4.14/color-contrast?application=axeAPI
- ⚠️ **WARN** [Facts · derived-price] `div.faq > details > div.answer > p`: $9.50 = (zone_breakfast + zone_lunch + zone_dinner) − zone_all from site.json, typed by hand (….50. The full plan is $253, which saves $9.50 a week. The double …) · pages: faq, pricing
  - Fix: Correct today, but it won't update when site.json changes. Drop it, or ask the main agent for a {{calc}} placeholder.
- ⚠️ **WARN** [Facts · derived-price] `div.faq > details > div.answer > p`: $18.75 = family_meal ($75) ÷ 4 from site.json, typed by hand (…two adults and two small children, it's $18.75 a person. There's a…) · pages: faq, pricing
  - Fix: Correct today, but it won't update when site.json changes. Drop it, or ask the main agent for a {{calc}} placeholder.
- ⚠️ **WARN** [Facts · proposed-offer] `src/site.json membership`: membership status is "proposed" but 13 page(s) present it as a live offer ("save 5–12%", prices, sign-up); only 3 say proposed/draft: about-jomb, delivery-area, family-meal-delivery, faq, how-it-works, home, low-carb-dairy-free-meals, meal-plans, menus, paleo-meal-delivery, pricing, protein-by-the-pound, zone-meal-delivery · pages: (site)
  - Fix: BRAND_GUIDE §2: proposed offers are never shown as live. Gate the membership blocks on a membership.enabled switch (off in preview, like compliance), or label them "Proposed" until Mike approves.
- ⚠️ **WARN** [Facts · site-json] `src/site.json`: prices.zone_all: $253 ÷ 18 meals = $14.0556, which rounds to $14.06, but per = $14.05 · pages: (site)
  - Fix: Confirm the per-meal figure with the JOMB Store (the store may show the truncated value), then make per match.

## Page issues

### about-jomb

Title (57): JOMB at a Glance: Just One More Bite Fact Sheet | Raleigh · description 154 chars · internal links in main: 18

| Sev | Area | Check | Element | Issue | Fix |
|---|---|---|---|---|---|
| ⚠️ WARN | Facts | hard-coded | `src/pages/about-jomb.html` | 1 hard-coded day/time value(s) in src/pages/about-jomb.html: "delivery on Friday." (l.58) | Replace with {{cutoff}} / {{cutoff_short}} / {{delivery_day}} / {{delivery_window}} / {{menu_posted}} so the value follows site.json. |

<details><summary>Info (1)</summary>

- [Schema · offer-price] 7 OfferCatalog entries have no price (fine for a catalog listing)

</details>

<details><summary>Facts seen on this page</summary>

- **phones**: (919) 443-5408
- **emails**: jomborders@gmail.com
- **deadlines**: Saturday at 8 PM, Order by Saturday, Saturday at 8 PM., close Saturday, Saturday 8 PM
- **delivery**: Delivered Tuesday, delivered every Tuesday, Tuesday, 10 AM, delivery on Friday., delivery on Friday. (membership second delivery), delivers on Tuesday, delivers Tuesday., Tuesday delivery
- **windows**: 10 AM – 5 PM, 10 AM – 5 PM.
- **menu_posted**: menu every Wednesday, menu All four menus, new every Wednesday
- **prices**: $12.25, $253, $14.05, $486, $13.50, $73.50, $81, $108, $75, $87, $117, $20, $35, $10.99, $13.99, $14.99, $18.99, $100, $50
- **years**: 20+ years

</details>

### catering-weddings

Title (60): Wedding & Event Catering in Raleigh, NC | Just One More Bite · description 155 chars · internal links in main: 8

No page-level FAIL/WARN.

<details><summary>Info (2)</summary>

- [Schema · offer-price] 7 OfferCatalog entries have no price (fine for a catalog listing)
- [Facts · trust-claim] testimonial mentions "ServSafe" (allowed: quoted testimonial)

</details>

<details><summary>Facts seen on this page</summary>

- **phones**: (919) 443-5408
- **emails**: jomborders@gmail.com
- **deadlines**: Saturday at 8 PM, Order by Saturday, Saturday 8 PM
- **delivery**: Delivered Tuesday, delivered every Tuesday, delivered Tuesday
- **menu_posted**: menu every Wednesday
- **prices**: $50

</details>

### chef-michael-saunders

Title (54): Chef Michael Saunders | Just One More Bite, Raleigh NC · description 153 chars · internal links in main: 7

No page-level FAIL/WARN.

<details><summary>Info (3)</summary>

- [Schema · offer-price] 7 OfferCatalog entries have no price (fine for a catalog listing)
- [Facts · trust-claim] testimonial mentions "ServSafe" (allowed: quoted testimonial)
- [Facts · trust-claim] testimonial mentions "ServSafe" (allowed: quoted testimonial)

</details>

<details><summary>Facts seen on this page</summary>

- **phones**: (919) 443-5408
- **emails**: jomborders@gmail.com
- **deadlines**: Saturday at 8 PM, Order by Saturday, Saturday 8 PM
- **delivery**: Delivered Tuesday, delivered every Tuesday., Tuesday delivery, delivered Tuesday., delivers Tuesday.
- **menu_posted**: menu every Wednesday
- **prices**: $12.25
- **years**: 20+ years, 20+ yrs

</details>

### contact

Title (50): Contact Just One More Bite | Raleigh Meal Delivery · description 148 chars · internal links in main: 8

No page-level FAIL/WARN.

<details><summary>Info (1)</summary>

- [Schema · offer-price] 7 OfferCatalog entries have no price (fine for a catalog listing)

</details>

<details><summary>Facts seen on this page</summary>

- **phones**: (919) 443-5408
- **emails**: jomborders@gmail.com
- **deadlines**: Saturday at 8 PM, Order by Saturday, close Saturday, order by Saturday, Saturday 8 PM
- **delivery**: Delivered Tuesday, Tuesday, 10 AM, arrive Tuesday, Tuesday delivery, Tuesday · 10 AM, delivery on Tuesday, delivers Tuesday.
- **windows**: 10 AM – 5 PM., 10 AM – 5 PM
- **menu_posted**: menu posts every Wednesday, menu every Wednesday

</details>

### delivery-area

Title (54): Meal Delivery: Raleigh, Cary, Morrisville & RTP | JOMB · description 143 chars · internal links in main: 8

No page-level FAIL/WARN.

<details><summary>Info (1)</summary>

- [Schema · offer-price] 7 OfferCatalog entries have no price (fine for a catalog listing)

</details>

<details><summary>Facts seen on this page</summary>

- **phones**: (919) 443-5408
- **emails**: jomborders@gmail.com
- **deadlines**: Saturday at 8 PM, Order by Saturday, Saturday at 8 PM., Sat 8 PM, close Saturday, Saturday 8 PM
- **delivery**: Delivered Tuesday, Tuesday between 10 AM, Tuesday delivery, Tuesday · 10 AM, arrive on Tuesday, Tuesday, 10 AM, deliveries every Tuesday, delivery on Friday., delivery on Friday. (membership second delivery), delivers Tuesday., delivered every Tuesday, delivers every Tuesday
- **windows**: 10 AM – 5 PM, 10 AM – 5 PM., 10 AM–5 PM
- **menu_posted**: menu posts every Wednesday, menu every Wednesday
- **prices**: $12.25, $75, $14.05, $81, $87

</details>

### family-meal-delivery

Title (56): Family Meal Delivery in Raleigh, NC | $75 Dinners Feed 3 · description 154 chars · internal links in main: 13

No page-level FAIL/WARN.

<details><summary>Info (1)</summary>

- [Schema · offer-price] 7 OfferCatalog entries have no price (fine for a catalog listing)

</details>

<details><summary>Facts seen on this page</summary>

- **phones**: (919) 443-5408
- **emails**: jomborders@gmail.com
- **deadlines**: Saturday at 8 PM, Order by Saturday, Saturday at 8 PM., close Saturday, Saturday 8 PM
- **delivery**: Delivered Tuesday, Tuesday, 10 AM, delivered Tuesday, arrive Tuesday, delivers Tuesday., delivered Tuesdays, Tuesday delivery
- **windows**: 10 AM – 5 PM, 10 AM – 5 PM.
- **menu_posted**: menu every Wednesday, menu posts every Wednesday
- **prices**: JSON-LD Family dinner: $75, JSON-LD Soup of the week: $20, JSON-LD Entrée salad: $35, JSON-LD Fresh-cut fruit, 1-gallon bag: $35, $75, $20, $35, $25.00, $50, $14.05, $14.50, $12.50

</details>

### faq

Title (57): FAQ: Raleigh Meal Delivery Questions | Just One More Bite · description 155 chars · internal links in main: 15

No page-level FAIL/WARN. (2 system-level issue(s) listed above.)

<details><summary>Info (1)</summary>

- [Schema · offer-price] 7 OfferCatalog entries have no price (fine for a catalog listing)

</details>

<details><summary>Facts seen on this page</summary>

- **phones**: (919) 443-5408
- **emails**: jomborders@gmail.com
- **deadlines**: Saturday at 8 PM, Order by Saturday, close Saturday, Saturday at 8 PM., order by Saturday, Saturday 8 PM
- **delivery**: Delivered Tuesday, Tuesday, 10 AM, arrive Tuesday, Tuesday between 10 AM, delivered on Tuesday, arrive on Tuesday, deliveries every Tuesday, delivery on Friday., delivery on Friday. (membership second delivery), Tuesday delivery, delivery on Friday, delivery on Friday (membership second delivery), delivered Tuesday, delivered every Tuesday, delivery on Tuesday, delivers Tuesday.
- **windows**: 10 AM – 5 PM, 10 AM – 5 PM.
- **menu_posted**: menu posts every Wednesday, menu? Every Wednesday, menu every Wednesday, menu goes up every Wednesday, menu is brand-new every Wednesday, menus every Wednesday
- **prices**: $12.25, $19.50, $75, $50, $253, $14.05, $108, $87, $117, $13.50, $12.50, $18.00, $14.50, $486, $262.50, $9.50, $20, $25, $18.75, $100, $35, $73.50, $81, $25.00, $10.99, $13.99, $14.99, $18.99
- **years**: 20+ years

</details>

### gift-cards

Title (51): Meal Gift Cards in Raleigh, NC | Just One More Bite · description 153 chars · internal links in main: 10

No page-level FAIL/WARN.

<details><summary>Info (1)</summary>

- [Schema · offer-price] 7 OfferCatalog entries have no price (fine for a catalog listing)

</details>

<details><summary>Facts seen on this page</summary>

- **phones**: (919) 443-5408
- **emails**: jomborders@gmail.com
- **deadlines**: Saturday at 8 PM, Order by Saturday, Sat 8 PM, Saturday 8 PM
- **delivery**: Delivered Tuesday, Tuesday, 10 AM, arrive Tuesday., Tuesday · 10 AM, arrive Tuesday
- **windows**: 10 AM – 5 PM, 10 AM – 5 PM.
- **menu_posted**: menu is written new each Wednesday, menu, posted every Wednesday, menu every Wednesday
- **prices**: JSON-LD Gift cards from: $50, $50, $75, $81, $117, $20, $35

</details>

### how-it-works

Title (56): How Our Raleigh Meal Delivery Works | Just One More Bite · description 155 chars · internal links in main: 13

| Sev | Area | Check | Element | Issue | Fix |
|---|---|---|---|---|---|
| ⚠️ WARN | Facts | hard-coded | `src/pages/how-it-works.html` | 1 hard-coded day/time value(s) in src/pages/how-it-works.html: "Order by Saturday." (l.18) | Replace with {{cutoff}} / {{cutoff_short}} / {{delivery_day}} / {{delivery_window}} / {{menu_posted}} so the value follows site.json. |

<details><summary>Info (1)</summary>

- [Schema · offer-price] 7 OfferCatalog entries have no price (fine for a catalog listing)

</details>

<details><summary>Facts seen on this page</summary>

- **phones**: (919) 443-5408
- **emails**: jomborders@gmail.com
- **deadlines**: Saturday at 8 PM, Order by Saturday, Order by Saturday., Sat 8 PM, Order by Sat, Saturday at 8 PM., close Saturday, Saturday 8 PM, order by Saturday
- **delivery**: Delivered Tuesday, Tuesday between 10 AM, arrive Tuesday, Tuesday 10 AM, Tuesday · 10 AM, deliver every Tuesday, arrive on Tuesday., delivered on Tuesday, delivers Tuesday., delivered Tuesday, Tuesday delivery
- **windows**: 10 AM – 5 PM
- **menu_posted**: menu every Wednesday, menu goes up Wednesday, menu goes up every Wednesday
- **prices**: $12.25, $253, $14.05, $14.50, $19.50, $87, $117, $12.50, $18.00, $75, $108, $20, $35, $10.99, $50

</details>

### home

Title (59): Just One More Bite | Chef-Made Meal Delivery in Raleigh, NC · description 153 chars · internal links in main: 15

No page-level FAIL/WARN. (1 system-level issue(s) listed above.)

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

### low-carb-dairy-free-meals

Title (52): Low-Carb, Dairy-Free Meal Delivery in Raleigh | JOMB · description 145 chars · internal links in main: 13

No page-level FAIL/WARN.

<details><summary>Info (1)</summary>

- [Schema · offer-price] 7 OfferCatalog entries have no price (fine for a catalog listing)

</details>

<details><summary>Facts seen on this page</summary>

- **phones**: (919) 443-5408
- **emails**: jomborders@gmail.com
- **deadlines**: Saturday at 8 PM, Order by Saturday, Saturday at 8 PM., Sat 8 PM, Ordering by Sat, close Saturday, Saturday 8 PM
- **delivery**: Delivered Tuesday, delivered every Tuesday, arrive Tuesday., delivered Tuesday, delivers Tuesday., delivered Tuesdays
- **menu_posted**: menu posts every Wednesday, menu every Wednesday
- **prices**: JSON-LD Low-Carb Dairy-Free · lunches: $75, JSON-LD Low-Carb Dairy-Free · dinners: $108, $75, $12.50, $108, $18.00, $14.05, $14.50

</details>

### meal-plans

Title (59): Meal Plan Subscriptions in Raleigh, NC | Just One More Bite · description 151 chars · internal links in main: 11

| Sev | Area | Check | Element | Issue | Fix |
|---|---|---|---|---|---|
| ⚠️ WARN | Facts | hard-coded | `src/pages/meal-plans.html` | 3 hard-coded day/time value(s) in src/pages/meal-plans.html: "delivery Friday" (l.36); "delivery on Friday." (l.71); "Friday delivery" (l.211) | Replace with {{cutoff}} / {{cutoff_short}} / {{delivery_day}} / {{delivery_window}} / {{menu_posted}} so the value follows site.json. |

<details><summary>Info (2)</summary>

- [Schema · offer-price] 7 OfferCatalog entries have no price (fine for a catalog listing)
- [Facts · builder-math] plan builder: checked 80 option combinations against build.py plan_quote(): all prices match [at 1440 px]

</details>

<details><summary>Facts seen on this page</summary>

- **phones**: (919) 443-5408
- **emails**: jomborders@gmail.com
- **deadlines**: Saturday at 8 PM, Order by Saturday, Saturday at 8 PM., Sat 8 PM, Saturday 8 PM
- **delivery**: Delivered Tuesday, Delivered every Tuesday, delivery Friday, delivery Friday (membership second delivery), arrive Tuesday., arrive Tuesday, Tuesday, 10 AM, delivered Tuesday, Friday delivery, Friday delivery (membership second delivery), Tuesday delivery, delivery on Friday, delivery on Friday (membership second delivery), delivers Tuesday.
- **windows**: 10 AM – 5 PM., 10 AM – 5 PM
- **menu_posted**: menu every Wednesday, menu is brand-new every Wednesday
- **prices**: $34.20, $213.75, $225.00, $11.25, $71.25, $926, $337.50, $375.00, $37.50, $67.50, $1,461, $162.00, $180.00, $18.00, $16.20, $701, $269.50, $306.25, $36.75, $12.83, $1,167, $142.50, $276.00, $69.00, $462.00, $66.00, $285.00, $427.50, $552.00, $675.00 …

</details>

### menus

Title (55): This Week's Menus · Meal Delivery in Raleigh, NC | JOMB · description 153 chars · internal links in main: 13

No page-level FAIL/WARN.

<details><summary>Info (1)</summary>

- [Schema · offer-price] 7 OfferCatalog entries have no price (fine for a catalog listing)

</details>

<details><summary>Facts seen on this page</summary>

- **phones**: (919) 443-5408
- **emails**: jomborders@gmail.com
- **deadlines**: Saturday at 8 PM, Order by Saturday, Saturday at 8 PM., Sat 8 PM, close Saturday, Saturday · 8 PM, Saturday 8 PM, Order by Sat
- **delivery**: Delivered Tuesday, Tuesday, 10 AM, delivered Tuesday, Tuesday 10 AM, arrives Tuesday, Tuesday · 10 AM, Tuesday between 10 AM, delivers Tuesday., Tuesday delivery
- **windows**: 10 AM – 5 PM, 10 AM – 5 PM.
- **menu_posted**: menu posts every Wednesday, menu drops every Wednesday, menus every Wednesday, menu every Wednesday
- **prices**: $12.25, $75, $14.05, $14.50, $12.50, $10.99, $253, $13.50, $87, $19.50, $117, $18.00, $108, $25.00, $20, $35, $100, $13.99, $486, $73.50, $81, $14.99, $18.99, $50

</details>

### paleo-meal-delivery

Title (55): Paleo Meal Delivery in Raleigh, NC | Just One More Bite · description 149 chars · internal links in main: 14

No page-level FAIL/WARN.

<details><summary>Info (1)</summary>

- [Schema · offer-price] 7 OfferCatalog entries have no price (fine for a catalog listing)

</details>

<details><summary>Facts seen on this page</summary>

- **phones**: (919) 443-5408
- **emails**: jomborders@gmail.com
- **deadlines**: Saturday at 8 PM, Order by Saturday, order by Saturday, Saturday at 8 PM., close Saturday, Saturday 8 PM
- **delivery**: Delivered Tuesday, delivered Tuesday, Tuesday, 10 AM, delivers Tuesday., delivered Tuesdays
- **windows**: 10 AM – 5 PM.
- **menu_posted**: menu every Wednesday, menu posts every Wednesday
- **prices**: JSON-LD Paleo · lunches: $87, JSON-LD Paleo · dinners: $117, $14.50, $19.50, $87, $117, $12.50, $13.50, $18.00, $14.05, $75

</details>

### pricing

Title (52): Meal Prep Prices in Raleigh, NC | Just One More Bite · description 153 chars · internal links in main: 11

| Sev | Area | Check | Element | Issue | Fix |
|---|---|---|---|---|---|
| ⚠️ WARN | Facts | derived-price | `div.container > div.info-math > div.is-best > p:nth-of-type(2)` | $42.17 = zone_all ($253) ÷ 6 from site.json, typed by hand (…eakfast, lunch and dinner for six days: $42.17 a day for three che…) | Correct today, but it won't update when site.json changes. Drop it, or ask the main agent for a {{calc}} placeholder. |
| ⚠️ WARN | Facts | derived-price | `div.container > div.info-math > div:nth-of-type(2) > p:nth-of-type(2)` | $40.50 = 3 × zone_double.per ($13.50) from site.json, typed by hand (…ry meal for two people is $81 a day, or $40.50 each.…) | Correct today, but it won't update when site.json changes. Drop it, or ask the main agent for a {{calc}} placeholder. |
| ⚠️ WARN | Facts | derived-price | `div.container > div.info-math > div:nth-of-type(3) > p:nth-of-type(2)` | $18.75 = lcdf_lunch ($75) ÷ 4 from site.json, typed by hand (…Or $18.75 a person for two ad…) | Correct today, but it won't update when site.json changes. Drop it, or ask the main agent for a {{calc}} placeholder. |
| ⚠️ WARN | Facts | derived-price | `div.container > div.info-cards.info-cards--3 > article.info-card > p` | $9.50 = (zone_breakfast + zone_lunch + zone_dinner) − zone_all from site.json, typed by hand (…ly cost $262.50; the full plan is $253, $9.50 less every week.…) | Correct today, but it won't update when site.json changes. Drop it, or ask the main agent for a {{calc}} placeholder. |
| ⚠️ WARN | Facts | derived-price | `div.container > div.info-cards.info-cards--3 > article.info-card > p` | $18.75 = family_meal ($75) ÷ 4 from site.json, typed by hand (…each) or two adults and two small kids ($18.75 each). The two-dinn…) | Correct today, but it won't update when site.json changes. Drop it, or ask the main agent for a {{calc}} placeholder. |
| ⚠️ WARN | Facts | hard-coded | `src/pages/pricing.html` | 15 hard-coded prices value(s) in src/pages/pricing.html: $42.17 (l.62, = zone_all ($253) ÷ 6); $81 (l.67, = zone_lunch); $40.50 (l.67, = 3 × zone_double.per ($13.50)); $18.75 (l.72, = lcdf_lunch ($75) ÷ 4); $183 (l.76, = membership two/3d/lunch_dinner/lcdf base); $15.25 (l.76, = membership one/5d/lunch_dinner/lcdf save); $189 (l.81, = membership two/3d/lunch_dinner/zone base); $15.75 (l.81, = membership one/5d/lunch_dinner/zone save) … | Replace with {{price:key}} / {{per:key}} (or a membership placeholder) so the value follows site.json. |

Plus 2 system-level issue(s) listed above.

<details><summary>Info (1)</summary>

- [Schema · offer-price] 7 OfferCatalog entries have no price (fine for a catalog listing)

</details>

<details><summary>Facts seen on this page</summary>

- **phones**: (919) 443-5408
- **emails**: jomborders@gmail.com
- **deadlines**: Saturday at 8 PM, Order by Saturday, Saturday 8 PM
- **delivery**: Delivered Tuesday, delivered Tuesday., delivers Tuesday.
- **menu_posted**: menu every Wednesday
- **prices**: JSON-LD Zone · all meals: $253, JSON-LD Zone · all meals, double: $486, JSON-LD Zone · breakfasts: $73.50, JSON-LD Zone · lunches: $81, JSON-LD Zone · dinners: $108, JSON-LD Low-Carb Dairy-Free · lunches: $75, JSON-LD Low-Carb Dairy-Free · dinners: $108, JSON-LD Paleo · lunches: $87, JSON-LD Paleo · dinners: $117, JSON-LD Family dinner: $75, $12.25, $19.50, $253, $14.05, $13.50, $75, $25.00, $486, $73.50, $81, $108, $18.00, $12.50, $87, $14.50, $117, $20, $35, $10.99, $13.99 …

</details>

### private-chef-raleigh

Title (56): Private Chef Dinners in Raleigh, NC | Just One More Bite · description 149 chars · internal links in main: 7

No page-level FAIL/WARN.

<details><summary>Info (1)</summary>

- [Schema · offer-price] 7 OfferCatalog entries have no price (fine for a catalog listing)

</details>

<details><summary>Facts seen on this page</summary>

- **phones**: (919) 443-5408
- **emails**: jomborders@gmail.com
- **deadlines**: Saturday at 8 PM, Order by Saturday, Saturday 8 PM
- **delivery**: Delivered Tuesday, delivered every Tuesday
- **menu_posted**: menu every Wednesday
- **prices**: $50
- **years**: 20+ years

</details>

### protein-by-the-pound

Title (59): Cooked Protein by the Pound in Raleigh | Just One More Bite · description 152 chars · internal links in main: 11

No page-level FAIL/WARN.

<details><summary>Info (1)</summary>

- [Schema · offer-price] 7 OfferCatalog entries have no price (fine for a catalog listing)

</details>

<details><summary>Facts seen on this page</summary>

- **phones**: (919) 443-5408
- **emails**: jomborders@gmail.com
- **deadlines**: Saturday at 8 PM, Order by Saturday, Sat 8 PM, Order by Sat, Saturday at 8 PM., close Saturday, Saturday 8 PM
- **delivery**: Delivered Tuesday, Tuesday delivery, Tuesday, 10 AM, delivered Tuesday, delivers Tuesday., delivered Tuesdays
- **windows**: 10 AM – 5 PM
- **menu_posted**: menu posts every Wednesday, menu every Wednesday
- **prices**: JSON-LD Chicken, per lb (cooked): $10.99, JSON-LD CAB beef, per lb (cooked): $13.99, JSON-LD Pork, per lb (cooked): $14.99, JSON-LD Seafood, per lb (cooked): $18.99, $10.99, $13.99, $14.99, $18.99, $100, $14.05, $14.50, $12.50, $75

</details>

### reviews

Title (53): Reviews of Just One More Bite | Raleigh Meal Delivery · description 150 chars · internal links in main: 9

No page-level FAIL/WARN.

<details><summary>Info (2)</summary>

- [Schema · offer-price] 7 OfferCatalog entries have no price (fine for a catalog listing)
- [Facts · trust-claim] testimonial mentions "ServSafe" (allowed: quoted testimonial)

</details>

<details><summary>Facts seen on this page</summary>

- **phones**: (919) 443-5408
- **emails**: jomborders@gmail.com
- **deadlines**: Saturday at 8 PM, Order by Saturday, Saturday 8 PM
- **delivery**: Delivered Tuesday, delivered every Tuesday, delivers Tuesday., Tuesday delivery
- **menu_posted**: menu every Wednesday
- **prices**: $75

</details>

### zone-meal-delivery

Title (57): Zone Diet Meal Delivery in Raleigh | 4-Block Meals | JOMB · description 155 chars · internal links in main: 13

No page-level FAIL/WARN.

<details><summary>Info (1)</summary>

- [Schema · offer-price] 7 OfferCatalog entries have no price (fine for a catalog listing)

</details>

<details><summary>Facts seen on this page</summary>

- **phones**: (919) 443-5408
- **emails**: jomborders@gmail.com
- **deadlines**: Saturday at 8 PM, Order by Saturday, Saturday at 8 PM., close Saturday, Saturday 8 PM
- **delivery**: Delivered Tuesday, delivered every Tuesday, delivered Tuesday, Tuesday delivery, Tuesday, 10 AM, delivers Tuesday., delivered Tuesdays
- **windows**: 10 AM – 5 PM.
- **menu_posted**: menu every Wednesday, menu posts every Wednesday
- **prices**: JSON-LD Zone · all meals: $253, JSON-LD Zone · all meals, double: $486, JSON-LD Zone · breakfasts: $73.50, JSON-LD Zone · lunches: $81, JSON-LD Zone · dinners: $108, $253, $14.05, $13.50, $486, $73.50, $12.25, $81, $108, $18.00, $14.50, $12.50, $75

</details>

### 404

Title (35): Page Not Found | Just One More Bite · description 148 chars · internal links in main: 10

No page-level FAIL/WARN.

<details><summary>Facts seen on this page</summary>

- **phones**: (919) 443-5408
- **emails**: jomborders@gmail.com
- **deadlines**: Saturday at 8 PM, Order by Saturday, Saturday 8 PM
- **delivery**: Delivered Tuesday, delivers Tuesday., Tuesday delivery
- **menu_posted**: menu every Wednesday

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
