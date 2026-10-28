# Website components and page rules

The site is static HTML built by `python3 build.py` (standard library only) from `src/` into `docs/`, which GitHub Pages serves. **Study `src/pages/home.html` and its output `docs/index.html` first.** It's the reference for tone, structure and quality.

## Files

| File | Owner | What |
|---|---|---|
| `build.py` | main agent only | Templating, layout, structured data, sitemap, llms.txt, link checker. Don't edit it; ask for changes in your report. |
| `src/site.json` | main agent | All business facts (phone, cutoff, towns, prices). Don't hard-code facts; use placeholders. |
| `src/menu.json` | main agent | This week's dishes |
| `src/data/testimonials.json` | read-only | Real testimonials: ids `jonathan rebecca anna tara nan sandi_mom sandi_pro steve` |
| `src/data/faq.json` | read-only | Core FAQ groups: `ordering food plans events` |
| `src/data/faq/<yours>.json` | **you** | Your own FAQ groups: `{"zone": [{"q": "...", "a": "..."}]}`. Merged at build time. Group keys must be unique across agents. |
| `src/pages/<slug>.html` | **you** (your assigned pages only) | One file per page |
| `src/assets/css/parts/<yours>.css` | **you** | Extra CSS for your pages, appended after `site.css` at build. Reuse existing components first. Prefix any new classes with your area (e.g. `.menu-`, `.svc-`, `.info-`). |
| `src/assets/css/site.css` | main agent | The design system. Read it; don't edit it. |

## Page file format

```html
<!--meta
{
  "title": "Zone Meal Delivery in Raleigh, NC | Just One More Bite",   // ≤ 60 chars, unique
  "description": "…",                                                   // 140–155 chars, unique, includes a fact + a place
  "path": "zone-meal-delivery/",                                        // output folder; "" = home
  "og": "og-zone",                                                      // share image: og-home og-zone og-paleo og-lcdf og-family og-chef og-private og-catering og-default
  "nav": "menus",                                                       // highlights the nav item: menus how pricing private catering chef faq
  "page_type": "WebPage",                                               // or AboutPage, FAQPage, ContactPage, CollectionPage, ProfilePage
  "breadcrumb": [["Menus", "menus/"], ["Zone", "zone-meal-delivery/"]], // excludes Home; last item = this page
  "service": {"name": "Zone diet meal delivery", "description": "…", "type": "Meal delivery", "offers": ["zone_all", "zone_double"]}   // optional; adds Service + Offer structured data (offers = keys in site.json prices)
}
-->
<section class="page-hero"> … </section>
…
```

`special: "404"` in the meta writes `docs/404.html` (the path value is then ignored).

## Placeholders (filled at build time)

**Facts**
- `{{phone}}` `{{tel}}` `{{phone_link}}` (a full `<a>` tag)
- `{{email}}` `{{email_link}}`
- `{{store}}`: the JOMB Store URL. Every "Order" button points here.
- `{{cutoff}}` → "Saturday at 8 PM" · `{{cutoff_short}}` → "Sat 8 PM"
- `{{delivery_day}}` · `{{delivery_window}}` · `{{delivery}}` · `{{menu_posted}}`
- `{{towns_sentence}}` → "Raleigh, Cary, … and Knightdale"
- `{{week_label}}` · `{{order_by}}`
- `{{chef}}` (Chef Michael Saunders) · `{{chef_nick}}` (Chef Mike) · `{{chef_years}}` (20+)
- `{{name}}` · `{{year}}` · `{{instagram}}` · `{{facebook}}` · `{{entity}}` (the standard one-paragraph business description)

**Prices**
- `{{price:zone_all}}` → $253 · `{{per:zone_all}}` → $14.05
- Keys: `zone_all zone_double zone_breakfast zone_lunch zone_dinner lcdf_lunch lcdf_dinner paleo_lunch paleo_dinner family_meal family_soup family_salad fruit protein_chicken protein_beef protein_pork protein_seafood gift_from` (`per` exists only for meal plans)

**Links and media**
- `{{link:zone-meal-delivery/}}`: a relative link to a site path. **Always** use this for internal links: the site lives under `/justonemorebite/` on GitHub Pages, so links starting with `/` break.
- `{{img:slug|sizes|class|eager|alt}}`: a responsive `<img>`.
  - Slugs and alt text are in `src/img/manifest.json`.
  - `sizes` defaults to `(min-width: 900px) 50vw, 100vw`.
  - Use `eager` only for the main hero image.
- `{{icon:name}}`: icons are `check calendar cart truck cooler phone mail pin chef leaf dumbbell flame clock gift users star plate sparkle heart briefcase arrow menu close instagram facebook list`

**Components**
- `{{breadcrumbs}}`: visible breadcrumb from the meta. Put it at the top of your page hero.
- `{{menu:zone}}` / `paleo` / `lcdf` / `family` / `protein`: this week's menu board with an Order button
- `{{plans}}` or `{{plans:paleo,lcdf}}`: plan cards (keys `zone paleo lcdf family`)
- `{{steps}}`: the 3-step how-it-works cards
- `{{price_table}}` or `{{price_table:zone,family}}`: groups `zone lcdf paleo family protein`
- `{{facts}}`: 4-up key facts bar (deadline, delivery, new menu, price from)
- `{{quote:id}}` · `{{quote:id|feature}}` (dark, large) · `{{quote:id|short}}` · `{{quotes:id1,id2,id3}}` (grid; `id|feature` works inside it)
- `{{faq:group1,group2}}`: an accordion **plus** FAQPage structured data that matches the visible text. Use it on every page that answers questions.
- `{{towns_chips}}` · `{{resume}}` (chef résumé checklist) · `{{creds}}` (full-width résumé strip) · `{{marquee}}`
- `{{cta_band}}` or `{{cta_band:photo-slug}}`: the closing call to action. End every page with it.

## CSS components (from site.css)

- **Layout**
  - `.section` (+ `--tight` `--paper` `--sand` `--dark` `--tomato`)
  - `.container` (+ `--narrow`)
  - `.section-head` (+ `--center`)
  - `.grid .grid--2/3/4`
  - `.split` (+ `--reverse` `--wide-media`)
  - `.stack`
- **Type**
  - `.eyebrow` · `.lead` · `.muted` · `.small` · `.note`
  - `h1–h3 em`: italic tomato accent words. Use one per headline for that signature look.
- **Buttons**
  - `.btn` + `--primary` `--ghost` `--light` `--outline-light` `--sm` `--lg`
  - `.btn-row` · `.text-link` (adds an arrow)
- **Page hero**
  - `.page-hero > .container > {{breadcrumbs}} + .page-hero-grid` (text + `.media-frame`)
  - `.price-chips > .price-chip` (`<b>$14.05</b><span>per meal</span>`)
- **Media**
  - `.media-frame` (+ `--tall` `--square` `--wide`) · `.media-caption`
  - `.collage` (2–3 `.media-frame`s) · `.gallery` (8 figures)
- **Lists and boxes**
  - `.checks` (green-check list) · `.chips`
  - `.facts > .fact` · `.stat-row > .stat`
  - `.callout` · `.answer-box` (green box for the answer-first summary)
- **Tables**
  - `.table-wrap > .table` (+ `.table--compare`)
  - `.num` (right-aligned numbers)
- **Cards**
  - `.step` (used by `{{steps}}`) · `.plan` (used by `{{plans}}`) · `.service-cards > a.service-card` (photo card with overlay text)
  - `.quote` (used by `{{quote}}`)
- **Motion:** `.reveal` fades content in on scroll. Add it to blocks, not to tiny inline elements.

## Rules every page must follow

1. **Mobile-first.** Check your page at 390 px and 1440 px with the screenshot tool: `<venv>/bin/python tools/shots.py --pages <folder-name> --out <dir>`. The venv is `/private/tmp/claude-501/-Users-joey-projects-golden-eye/d4a0922b-13bf-44ce-9c0e-729d65a57ae6/scratchpad/venv/bin/python`. Page name = folder name, e.g. `zone-meal-delivery`. Look at the PNGs: no horizontal scroll, no overlaps, no awkward wraps.
2. **One H1 per page**, containing the main keyword + Raleigh (or the Triangle) where natural. A keyword eyebrow inside the H1 works well: `<h1><span class="eyebrow">Zone meal delivery · Raleigh, NC</span>Macro-perfect meals, <em>cooked by a chef.</em></h1>`.
3. **Answer first.** The first paragraph after the H1 states plainly who, what, where, price and how to order. That's the text Google and AI assistants quote. Use real numbers.
4. **Marketing quality.** This is a premium sales piece. Use benefit-led headlines, specific numbers, real testimonials and real photos, and a clear Order call to action in the hero *and* at the end (`{{cta_band}}`). No filler, no lorem ipsum, no generic AI phrasing ("elevate", "unlock", "delve", "culinary journey").
5. **Facts only from site.json, menu.json, testimonials.json, faq.json and the brand guide** (`../BRAND_GUIDE.md`). Never invent prices, dishes, awards, years in business, guarantees, delivery fees or nutrition numbers.
   - The Zone targets are real: ~28–32 g protein, 34–40 g carbs, 12–16 g fat per meal = 4 blocks; 1 block = 7 g protein, 9 g carbs, 1.5 g fat.
   - No medical claims. Results stories carry "Individual results vary."
6. **Internal links.** Link generously and descriptively between related pages with `{{link:…}}`. Every page links to at least 3 others.
7. **Images.** Real photos only, from the manifest. Every `{{img}}` gets a sensible `sizes` value. Use one `eager` image at most.
8. **Accessibility.** Proper heading order, descriptive link text, `aria-label` on icon-only links, contrast-safe colors (use the existing tokens).
9. **Build** with `python3 build.py` from `website/`. Your page must produce **no WARN lines of its own**. Links to pages other agents haven't finished will warn until they exist; that's fine.
