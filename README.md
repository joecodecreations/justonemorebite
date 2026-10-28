# Just One More Bite: website

A fast, mobile-first marketing website for Just One More Bite (Chef Michael Saunders, Raleigh NC), built to rank in Google and to be quoted by AI assistants.

- **Live preview:** https://joecodecreations.github.io/justonemorebite/ (GitHub Pages, served from `docs/`)
- **Status:** preview. Every page has `noindex` and a slim "Preview" ribbon so it can't compete with the real site in Google. Ordering buttons go to the existing live JOMB Store, so they work today.

## How it's built

- Plain static HTML, CSS and a small JavaScript file. No framework, no tracking, no build service, no GitHub Actions.
- `python3 build.py` (standard library only) turns `src/` into `docs/`.
- All business facts live in **one file**, `src/site.json`: phone, order deadline, delivery day and window, towns, prices. Change a fact there, rebuild, and every page, the structured data, `llms.txt` and the sitemap update together. That's the fix for the old site's three phone numbers and five order deadlines.
- The weekly menu lives in `src/menu.json`. Update it every Wednesday and rebuild.
- Pages are `src/pages/*.html` (a JSON meta header plus HTML with `{{placeholders}}`). See [COMPONENTS.md](COMPONENTS.md).

## SEO and AI-search features built in

- Unique title and description on every page, one keyword-led H1, clean URLs, and a breadcrumb trail (visible and in structured data).
- Structured data (JSON-LD) generated from `site.json` on every page:
  - `FoodEstablishment` (service-area business, Raleigh NC, `areaServed` towns)
  - `Person` (Chef Michael Saunders) and `WebSite`
  - `Service` + `Offer` with real prices on each menu page
  - `FAQPage` that always matches the visible FAQ text
  - `BreadcrumbList`
- Answer-first opening paragraphs with real numbers: the text Google and AI assistants quote.
- A "JOMB at a glance" fact page (`about-jomb/`), `llms.txt`, `sitemap.xml`, `robots.txt` (doesn't block AI crawlers), Open Graph share cards, and a web manifest with icons.
- Performance:
  - Responsive WebP images (`srcset`), lazy loading, and the hero image at high fetch priority
  - Two self-hosted font files and no third-party scripts
  - Content works without JavaScript

## Commands

```bash
python3 build.py                                   # build docs/ (prints WARN lines for broken links or missing images)
<venv>/bin/python tools/images.py                  # re-make WebP images + share cards from the original photos
<venv>/bin/python tools/shots.py --pages home      # full-page screenshots (desktop + mobile) via headless Chrome
<venv>/bin/python tools/make_pdf.py                # screenshots PDF -> ../JOMB_Website_Preview.pdf
```

The tools need Pillow and Playwright (`pip install pillow playwright`). Playwright drives the installed Google Chrome headlessly (`channel="chrome"`), so no extra browser download is needed.

## Going live on the real domain

1. Confirm the facts marked `CONFIRM` in `src/site.json` with Mike.
2. Set `"preview": false` and `"base_url": "https://www.justonemorebitenc.com"`, then rebuild. This removes `noindex` and the ribbon, and points canonical URLs, the sitemap, the structured data and `llms.txt` at the real domain.
3. Choose a host:
   - Point the domain at GitHub Pages (add a `CNAME` file to `docs/`).
   - Or keep Squarespace for the store and move this design's copy and structure into Squarespace pages.

   Either way, add 301 redirects from the old URLs (`/zone-menu` → `/zone-meal-delivery/`, `/diet-menu` → `/low-carb-dairy-free-meals/`, `/page-g` → `/private-chef-raleigh/`, `/weddings` → `/catering-weddings/`, `/about` → `/chef-michael-saunders/`, `/testimonials` → `/reviews/`).
4. Swap the temporary bite-mark logo for the logo Mike picks from `../logos/`.

## Photos

The photos are Mike's own, from justonemorebitenc.com and Facebook.
- Processed web versions are in `docs/img/`.
- Originals in `src/img/source/` are **not** committed. That folder includes client family photos and health screenshots that must never be published.
- See `../BRAND_GUIDE.md` §5 for what's off-limits.
