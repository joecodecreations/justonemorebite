"""Turn Mike's original photos into fast, responsive WebP files for the site.

Run:  <venv>/bin/python tools/images.py
Reads originals from src/img/source (downloaded from justonemorebitenc.com) and
../photos (Facebook), writes docs/img/<slug>-<width>.webp plus og-*.jpg share cards,
and src/img/manifest.json (slug -> widths + aspect ratio) for build.py.
"""
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageOps

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src" / "img" / "source"
FB = ROOT.parent / "photos"
OUT = ROOT / "docs" / "img"
WIDTHS = [480, 800, 1200, 1600]

# slug: (source file, optional crop box as fractions (left, top, right, bottom), alt text)
PHOTOS = {
    "lamb": ("038.jpg", None, "Roasted rack of lamb with red wine demi-glace, mashed potatoes and vegetables"),
    "salmon-plated": ("041.jpg", None, "Glazed salmon fillets plated with grilled asparagus"),
    "meals-rows": ("059.jpg", None, "Rows of Just One More Bite meals packed for Tuesday delivery"),
    "meals-containers": ("033.jpg", None, "Weekly prepared meals in containers with chicken, rice and snap peas"),
    "meals-tray": ("071.jpg", None, "Lunch containers with chicken, brown rice and green beans ready for delivery"),
    "zone-plate": ("083.jpg", None, "Herb-crusted chicken with asparagus and a cranberry relish"),
    "paleo-plate": ("084.jpg", None, "Sliced roast pork tenderloin over a kale salad"),
    "lcdf-plate": ("095.jpg", None, "Sliced chicken with a green herb sauce over a crunchy cabbage slaw"),
    "family-plate": ("080.jpg", None, "Glazed braised short rib with roasted potatoes and green beans"),
    "steaks-grill": ("005.jpg", None, "Chef grilling USDA Choice steaks"),
    "shrimp": ("072.jpg", None, "Spiced grilled shrimp packed for a weekly order"),
    "tuna": ("085.jpg", None, "Seared tuna with a spicy aioli over carrot slaw"),
    "pineapple-chicken": ("076.jpg", None, "Grilled chicken with pineapple and teriyaki glaze"),
    "bbq-chicken-broccoli": ("101.jpg", None, "Barbecue chicken with broccoli and pasta in weekly meal containers"),
    "chef-plating": ("062.jpg", None, "Chef plating seared salmon and asparagus on a butcher-block cart"),
    "chef-plating-2": ("063.jpg", None, "Chef finishing plates of seared salmon"),
    "chef-label": ("069.jpg", None, "Chef checking a hand-written label on a bottle of house vinaigrette"),
    "chef-banner": ("061.jpg", None, "Chef Michael Saunders of Just One More Bite at an event"),
    "chef-table-outdoor": ("046.jpg", None, "Chef standing at a long outdoor table set for a private dinner"),
    "table-outdoor": ("042.jpg", None, "Farmhouse table set outdoors for a private chef dinner"),
    "table-fall": ("039.jpg", None, "Autumn table setting with sunflowers and leaf placemats"),
    "private-plates": ("036.jpg", None, "Plated first courses lined up for a private dinner party"),
    "scallop": ("034.jpg", None, "Seared scallop course on a shell-shaped plate"),
    "home-plating": ("035.jpg", None, "Chefs plating a multi-course private dinner"),
    "dinner-candles": ("FB:486008935_1299935305038307_1244899798049135174_n.jpg", None, "Candlelit long table with flowers and printed menus for a private birthday dinner"),
    "dinner-long": ("FB:485147882_1299935398371631_1912618257677948610_n.jpg", None, "Long dinner table set beside the open kitchen for a private event"),
    "produce": ("FB:481436321_1282947210070450_6199690547344729569_n.jpg", (0.0, 0.47, 1.0, 1.0), "Fresh squash, zucchini, eggplant and peppers on a prep table"),
    "catering-tuna": ("043.jpg", None, "Seared tuna crostini with grapefruit and wasabi cream on a catering table"),
    "catering-buffet": ("012.jpg", None, "Catered buffet spread with salads, crudités and dips"),
    "catering-platter": ("013.jpg", None, "Catering platter of grilled skewers and greens"),
    "catering-crostini": ("014.jpg", None, "Pulled pork crostini and stuffed bread bites for a party"),
    "soup": ("007.jpg", None, "Bowls of tomato bisque garnished with herbs"),
    "fruit": ("079.jpg", None, "Fresh-cut fruit cups with strawberries, mango and almonds"),
    "athletes": ("055.jpg", None, "Two athletes in JOMB Athlete shirts at a CrossFit competition"),
    "dessert": ("009.jpg", None, "Fruit crumble with vanilla ice cream and berry sauce"),
    "steak-plated": ("015.jpg", None, "Sliced steak with asparagus and a balsamic reduction"),
    "seared-tuna-slaw": ("026.jpg", None, "Sesame seared tuna over purple cabbage"),
    "osso-buco-style": ("091.jpg", None, "Braised pork with a savory pan sauce"),
    "turkey-plate": ("110.jpg", None, "Roast turkey with cranberry, sweet potato and creamy salad"),
}

# share cards (1200x630): slug, source photo slug, vertical focus (0 = top, 1 = bottom)
OG = {
    "og-home": ("lamb", 0.5),
    "og-zone": ("zone-plate", 0.5),
    "og-paleo": ("paleo-plate", 0.5),
    "og-lcdf": ("lcdf-plate", 0.5),
    "og-family": ("family-plate", 0.5),
    "og-chef": ("chef-plating", 0.35),
    "og-private": ("dinner-candles", 0.55),
    "og-catering": ("catering-tuna", 0.5),
    "og-default": ("meals-rows", 0.5),
}


def load(name):
    path = FB / name[3:] if name.startswith("FB:") else SRC / name
    im = Image.open(path)
    im = ImageOps.exif_transpose(im).convert("RGB")
    return im


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    manifest = {}
    full = {}
    for slug, (src, crop, alt) in PHOTOS.items():
        im = load(src)
        if crop:
            w, h = im.size
            im = im.crop((int(crop[0] * w), int(crop[1] * h), int(crop[2] * w), int(crop[3] * h)))
        full[slug] = im
        w, h = im.size
        widths = [x for x in WIDTHS if x < w] + [min(w, WIDTHS[-1])]
        widths = sorted(set(widths))
        for tw in widths:
            th = round(h * tw / w)
            im.resize((tw, th), Image.LANCZOS).save(OUT / f"{slug}-{tw}.webp", "WEBP", quality=78, method=6)
        manifest[slug] = {"widths": widths, "w": w, "h": h, "alt": alt}
    for slug, (src_slug, focus) in OG.items():
        im = full[src_slug]
        w, h = im.size
        target = 1200 / 630
        if w / h > target:
            nw = int(h * target)
            left = (w - nw) // 2
            box = (left, 0, left + nw, h)
        else:
            nh = int(w / target)
            top = int((h - nh) * focus)
            box = (0, top, w, top + nh)
        im.crop(box).resize((1200, 630), Image.LANCZOS).save(OUT / f"{slug}.jpg", "JPEG", quality=82, optimize=True, progressive=True)
    make_icons()
    (ROOT / "src" / "img" / "manifest.json").write_text(json.dumps(manifest, indent=1))
    total = sum(p.stat().st_size for p in OUT.iterdir())
    print(f"{len(manifest)} photos, {len(list(OUT.iterdir()))} files, {total/1e6:.1f} MB")


def bite_mark(size, bg=None):
    """The JOMB mark: a tomato-red plate with a bite taken out, drawn 4x and downsampled."""
    s = size * 4
    im = Image.new("RGBA", (s, s), bg or (0, 0, 0, 0))
    mask = Image.new("L", (s, s), 0)
    d = ImageDraw.Draw(mask)
    pad = int(s * 0.08)
    d.ellipse([pad, pad, s - pad, s - pad], fill=255)
    r = int(s * 0.13)
    cx = s - pad - int(s * 0.04)
    for cy in (int(s * 0.30), int(s * 0.47), int(s * 0.64)):
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=0)
    inner = Image.new("L", (s, s), 0)
    di = ImageDraw.Draw(inner)
    ip = int(s * 0.25)
    di.ellipse([ip, ip, s - ip, s - ip], outline=255, width=max(2, int(s * 0.035)))
    red = Image.new("RGBA", (s, s), (200, 64, 42, 255))
    im.paste(red, (0, 0), mask)
    cream = Image.new("RGBA", (s, s), (250, 246, 239, 255))
    from PIL import ImageChops
    im.paste(cream, (0, 0), ImageChops.multiply(inner, mask))
    return im.resize((size, size), Image.LANCZOS)


def make_icons():
    for size, name in [(180, "apple-touch-icon.png"), (192, "icon-192.png"), (512, "icon-512.png")]:
        bg = (250, 246, 239, 255) if name == "apple-touch-icon.png" else None
        bite_mark(size, bg).save(OUT.parent / name)
    bite_mark(48).save(OUT.parent / "favicon.png")


if __name__ == "__main__":
    main()
