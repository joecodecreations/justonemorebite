"""Make the website screenshots PDF (desktop + mobile) for Mike.

    <venv>/bin/python tools/make_pdf.py [--base URL] [--shots DIR] [--out FILE] [--skip-shots]

1. Takes full-page screenshots of every page (tools/shots.py), unless --skip-shots.
2. Renders a branded cover, a contents page and one "at a glance" page per site page
   (desktop + phone, first screen) as HTML in the brand fonts, screenshotted by headless Chrome.
3. Appends the full-length desktop and mobile captures as tall pages.
4. Writes one PDF (default: ../JOMB_Website_Preview.pdf).
"""
import argparse
import html
import json
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

from PIL import Image
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
SITE = json.loads((ROOT / "src" / "site.json").read_text())
FONT = (ROOT / "src" / "assets" / "fonts" / "fraunces-latin.woff2").as_uri()
FONT_I = (ROOT / "src" / "assets" / "fonts" / "fraunces-italic-latin.woff2").as_uri()
DPI = 200
ORDER = ["home", "menus", "meal-plans", "zone-meal-delivery", "paleo-meal-delivery", "low-carb-dairy-free-meals", "family-meal-delivery",
         "protein-by-the-pound", "how-it-works", "pricing", "delivery-area", "private-chef-raleigh", "catering-weddings",
         "chef-michael-saunders", "reviews", "faq", "gift-cards", "contact", "about-jomb"]

CSS = f"""
@font-face {{ font-family: F; src: url({FONT}); font-weight: 400 700; }}
@font-face {{ font-family: F; src: url({FONT_I}); font-style: italic; font-weight: 400 700; }}
* {{ box-sizing: border-box; margin: 0; }}
body {{ width: 1100px; height: 850px; overflow: hidden; background: #FAF6EF; color: #1B1714; font-family: -apple-system, "SF Pro Text", Helvetica, sans-serif; }}
.f {{ font-family: F, Georgia, serif; }}
em {{ font-style: italic; color: #C8402A; font-weight: 480; }}
.eyebrow {{ font: 650 11px/1.2 -apple-system, sans-serif; letter-spacing: .18em; text-transform: uppercase; color: #A3321F; }}
"""


def page_meta():
    out = {}
    for f in DOCS.rglob("index.html"):
        rel = f.parent.relative_to(DOCS).as_posix()
        name = "home" if rel == "." else rel
        doc = f.read_text()
        t = re.search(r"<title>(.*?)</title>", doc, re.S)
        d = re.search(r'<meta name="description" content="(.*?)"', doc, re.S)
        title = html.unescape(t.group(1)) if t else name
        if name == "home":
            title = "Home | " + title.split(" | ")[-1]
        out[name] = {"title": title, "desc": html.unescape(d.group(1)) if d else "",
                     "url": SITE["base_url"].rstrip("/") + "/" + ("" if name == "home" else name + "/")}
    return out


def render(page, body_html, out):
    tmp = Path(out).parent / "_render.html"  # load from file:// so local images and fonts are allowed
    tmp.write_text(f"<html><head><meta charset='utf-8'><style>{CSS}</style></head><body>{body_html}</body></html>")
    page.goto(tmp.as_uri(), wait_until="networkidle")
    page.evaluate("document.fonts.ready")
    page.wait_for_timeout(150)
    page.screenshot(path=str(out))


def cover_html(n):
    return f"""
<div style="display:grid;grid-template-columns:1fr 1fr;height:850px">
  <div style="padding:70px 60px;display:flex;flex-direction:column;justify-content:space-between">
    <div class="eyebrow">Website preview · {date.today():%B %Y}</div>
    <div>
      <div class="f" style="font-size:76px;line-height:1;letter-spacing:-.02em;font-weight:560">Just One<br>More Bite</div>
      <div class="f" style="font-size:34px;line-height:1.15;margin-top:22px">The new website, <em>on every screen.</em></div>
      <p style="margin-top:26px;font-size:16px;line-height:1.6;color:#3a332d;max-width:420px">A mobile-first, search- and AI-optimized marketing site for Chef Michael Saunders' chef-made meal delivery in Raleigh, NC. {n} pages, each shown on a laptop and a phone.</p>
    </div>
    <div style="font-size:13px;color:#6b625a;line-height:1.6">Live preview: <b style="color:#1B1714">{html.escape(SITE['base_url'])}/</b><br>Prepared for Chef Michael Saunders</div>
  </div>
  <div style="background:#1B1714;position:relative;overflow:hidden">
    <img src="{(DOCS / 'img' / 'lamb-1200.webp').as_uri()}" style="position:absolute;inset:0;width:100%;height:100%;object-fit:cover;opacity:.92">
    <div style="position:absolute;right:36px;bottom:36px;width:150px;height:150px;border-radius:50%;background:#C8402A;color:#fff;display:grid;place-items:center;text-align:center;transform:rotate(8deg)">
      <div><div style="font:650 10px/1.3 sans-serif;letter-spacing:.14em">CHEF-MADE</div><div class="f" style="font-size:30px;line-height:1.05">Every<br>Tuesday</div></div></div>
  </div>
</div>"""


def contents_html(items):
    rows = "".join(
        f'<div style="display:flex;justify-content:space-between;gap:20px;padding:9px 0;border-bottom:1px dashed #d9cdbc">'
        f'<span class="f" style="font-size:19px">{i + 1:02d} · {html.escape(m["title"].split(" | ")[0])}</span>'
        f'<span style="font-size:12px;color:#6b625a;white-space:nowrap">{html.escape(m["url"].split("/justonemorebite")[-1] or "/")}</span></div>'
        for i, (k, m) in enumerate(items))
    return f"""<div style="padding:60px 70px">
<div class="eyebrow">Contents</div><div class="f" style="font-size:44px;margin:12px 0 24px">Every page, <em>at a glance</em></div>
<div style="columns:2;column-gap:56px">{rows}</div>
<p style="margin-top:28px;font-size:13px;color:#6b625a;line-height:1.6">Each page appears first as a side-by-side "first screen" view (laptop at 1440 px wide, phone at 390 px), then as full-length scrolling captures at the end of this document.</p></div>"""


def glance_html(i, m, desk, mob):
    return f"""<div style="padding:44px 52px;height:850px;display:flex;flex-direction:column">
<div style="display:flex;justify-content:space-between;align-items:flex-end;margin-bottom:20px">
  <div><div class="eyebrow">Page {i:02d}</div><div class="f" style="font-size:32px;margin-top:6px;letter-spacing:-.01em">{html.escape(m['title'].split(' | ')[0])}</div>
  <div style="font-size:13px;color:#6b625a;margin-top:6px;max-width:640px;line-height:1.5">{html.escape(m['desc'])}</div></div>
  <div style="font-size:12px;color:#6b625a;text-align:right;line-height:1.6">{html.escape(m['url'])}</div></div>
<div style="display:flex;gap:28px;align-items:flex-start;flex:1">
  <div style="flex:1"><div style="font:650 10px sans-serif;letter-spacing:.16em;color:#6b625a;margin-bottom:8px">LAPTOP · 1440 PX</div>
    <div style="border-radius:14px;overflow:hidden;box-shadow:0 20px 50px rgba(27,23,20,.18);border:1px solid #e8dfd2;background:#fff">
    <div style="height:22px;background:#e8dfd2;display:flex;gap:6px;align-items:center;padding-left:10px"><i style="width:9px;height:9px;border-radius:50%;background:#C8402A"></i><i style="width:9px;height:9px;border-radius:50%;background:#d9a441"></i><i style="width:9px;height:9px;border-radius:50%;background:#4f6b3a"></i></div>
    <img src="{desk.as_uri()}" style="display:block;width:100%"></div></div>
  <div style="width:255px"><div style="font:650 10px sans-serif;letter-spacing:.16em;color:#6b625a;margin-bottom:8px">PHONE · 390 PX</div>
    <div style="border-radius:34px;padding:9px;background:#1B1714;box-shadow:0 20px 50px rgba(27,23,20,.25)">
    <img src="{mob.as_uri()}" style="display:block;width:100%;border-radius:26px"></div></div>
</div></div>"""


def divider_html(title, sub):
    return f"""<div style="height:850px;background:#1B1714;color:#fff7ee;display:flex;flex-direction:column;justify-content:center;padding:80px">
<div class="eyebrow" style="color:#f08a6f">Just One More Bite · website preview</div>
<div class="f" style="font-size:60px;margin-top:16px;line-height:1.05">{title}</div><p style="margin-top:18px;font-size:17px;color:#c9bfb2;max-width:640px;line-height:1.6">{sub}</p></div>"""


def tall_pages(png, label, max_h):
    im = Image.open(png).convert("RGB")
    w, h = im.size
    parts = []
    n = (h + max_h - 1) // max_h
    for k in range(n):
        parts.append(im.crop((0, k * max_h, w, min(h, (k + 1) * max_h))))
    return parts


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="")
    ap.add_argument("--shots", default=str(ROOT / "shots"))
    ap.add_argument("--out", default=str(ROOT.parent / "JOMB_Website_Preview.pdf"))
    ap.add_argument("--skip-shots", action="store_true")
    a = ap.parse_args()
    shots = Path(a.shots)
    if not a.skip_shots:
        cmd = [sys.executable, str(ROOT / "tools" / "shots.py"), "--out", str(shots)] + (["--base", a.base] if a.base else [])
        subprocess.run(cmd, check=True)
    meta = page_meta()
    names = [n for n in ORDER if n in meta and (shots / f"{n}-desktop.png").exists()]
    names += sorted(n for n in meta if n not in names and (shots / f"{n}-desktop.png").exists())
    folds = shots / "_folds"
    folds.mkdir(exist_ok=True)
    rendered = []
    with sync_playwright() as pw:
        b = pw.chromium.launch(channel="chrome", headless=True)
        page = b.new_page(viewport={"width": 1100, "height": 850}, device_scale_factor=2)
        render(page, cover_html(len(names)), folds / "00-cover.png")
        rendered.append(folds / "00-cover.png")
        render(page, contents_html([(n, meta[n]) for n in names]), folds / "01-contents.png")
        rendered.append(folds / "01-contents.png")
        for i, n in enumerate(names, 1):
            d = Image.open(shots / f"{n}-desktop.png").convert("RGB")
            dfold = folds / f"{n}-dfold.png"
            d.crop((0, 0, d.width, min(d.height, 900))).save(dfold)
            mfold = shots / f"{n}-mobile-fold.png"
            out = folds / f"g-{i:02d}-{n}.png"
            render(page, glance_html(i, meta[n], dfold, mfold), out)
            rendered.append(out)
        render(page, divider_html("Full-length <em>captures</em>", "Every page from top to bottom: laptop first, then phone. Zoom in to read any section."), folds / "zz-divider.png")
        rendered.append(folds / "zz-divider.png")
        b.close()
    pdf_pages = [Image.open(p).convert("RGB") for p in rendered]
    max_h = int(DPI * 190)  # keep every PDF page under the 200-inch limit
    for n in names:
        pdf_pages += tall_pages(shots / f"{n}-desktop.png", f"{n} desktop", max_h)
        mob = Image.open(shots / f"{n}-mobile.png").convert("RGB")
        mob_scaled = mob.resize((mob.width // 2 * 2 // 2, mob.height // 2), Image.LANCZOS) if mob.width > 900 else mob
        tmp = folds / f"{n}-mobile-pdf.png"
        mob_scaled.save(tmp)
        pdf_pages += tall_pages(tmp, f"{n} mobile", max_h)
    out = Path(a.out)
    pdf_pages[0].save(out, "PDF", save_all=True, append_images=pdf_pages[1:], resolution=DPI, quality=82)
    print(f"wrote {out} ({out.stat().st_size / 1e6:.1f} MB, {len(pdf_pages)} PDF pages, {len(names)} site pages)")


if __name__ == "__main__":
    main()
