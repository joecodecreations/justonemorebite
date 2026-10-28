"""Full-page screenshots of the built site (desktop + mobile), headless Chrome via Playwright.

    <venv>/bin/python tools/shots.py [--pages home,menus] [--out DIR] [--base URL]

Default base is the local docs/ folder (file://). Pass --base https://joecodecreations.github.io/justonemorebite/
to shoot the live site. Writes <out>/<page>-desktop.png, -mobile.png and -mobile-fold.png.
"""
import argparse
import re
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"

PREP = """
document.querySelectorAll('.reveal').forEach(e => e.classList.add('is-in'));
document.querySelectorAll('.marquee-track').forEach(e => e.style.animation = 'none');
document.querySelectorAll('.dot').forEach(e => e.style.animation = 'none');
"""


def pages():
    out = []
    for f in sorted(DOCS.rglob("index.html")):
        rel = f.parent.relative_to(DOCS).as_posix()
        out.append(("home" if rel == "." else rel.strip("/"), "" if rel == "." else rel + "/"))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pages", default="")
    ap.add_argument("--out", default=str(ROOT / "shots"))
    ap.add_argument("--base", default="")
    ap.add_argument("--only", default="", help="desktop or mobile")
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    want = set(filter(None, a.pages.split(",")))
    todo = [p for p in pages() if not want or p[0] in want]
    with sync_playwright() as pw:
        browser = pw.chromium.launch(channel="chrome", headless=True)
        configs = {
            "desktop": dict(viewport={"width": 1440, "height": 900}, device_scale_factor=1),
            "mobile": dict(viewport={"width": 390, "height": 844}, device_scale_factor=2, is_mobile=True, has_touch=True),
        }
        for kind, cfg in configs.items():
            if a.only and a.only != kind:
                continue
            ctx = browser.new_context(**cfg)
            page = ctx.new_page()
            for name, path in todo:
                url = (a.base.rstrip("/") + "/" + path) if a.base else (DOCS / path / "index.html").as_uri()
                page.goto(url, wait_until="networkidle")
                page.evaluate(PREP)
                page.evaluate("document.fonts.ready")
                # lazy images: scroll through the page so everything loads
                h = page.evaluate("document.body.scrollHeight")
                for y in range(0, h, 700):
                    page.evaluate(f"window.scrollTo(0,{y})")
                    page.wait_for_timeout(60)
                page.evaluate("window.scrollTo(0,0)")
                page.wait_for_timeout(400)
                safe = re.sub(r"[^a-z0-9-]", "-", name)
                if kind == "mobile":
                    page.screenshot(path=str(out / f"{safe}-mobile-fold.png"))
                page.add_style_tag(content=".mobile-bar{display:none!important}.site-header{position:relative!important}")
                full_h = page.evaluate("document.documentElement.scrollHeight")
                dpr = cfg["device_scale_factor"]
                if full_h * dpr <= 16000:
                    page.screenshot(path=str(out / f"{safe}-{kind}.png"), full_page=True)
                else:  # Chrome tiles captures past 16384 px: shoot in slices and stitch
                    from PIL import Image
                    import io
                    width = cfg["viewport"]["width"]
                    step = int(15000 / dpr)
                    parts = []
                    for y in range(0, full_h, step):
                        h = min(step, full_h - y)
                        png = page.screenshot(full_page=True, clip={"x": 0, "y": y, "width": width, "height": h})
                        parts.append(Image.open(io.BytesIO(png)).convert("RGB"))
                    canvas = Image.new("RGB", (parts[0].width, sum(p.height for p in parts)), "white")
                    yy = 0
                    for p in parts:
                        canvas.paste(p, (0, yy))
                        yy += p.height
                    canvas.save(out / f"{safe}-{kind}.png")
                print("shot", kind, name)
            ctx.close()
        browser.close()


if __name__ == "__main__":
    main()
