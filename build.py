#!/usr/bin/env python3
"""Build the Just One More Bite website into docs/ (served by GitHub Pages).

    python3 build.py

No dependencies (standard library only). Content lives in src/:
  site.json          business facts (phone, cutoff, towns, prices...) - change once, updates everywhere
  menu.json          this week's menu
  data/*.json        testimonials, FAQ
  pages/*.html       one file per page: a <!--meta {json} --> header + HTML body with {{placeholders}}
See COMPONENTS.md for every placeholder and CSS component.
"""
import html
from urllib.parse import urlparse
import json
import re
import shutil
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
OUT = ROOT / "docs"

SITE = json.loads((SRC / "site.json").read_text())
MENU = json.loads((SRC / "menu.json").read_text())
TESTI = json.loads((SRC / "data" / "testimonials.json").read_text())
FAQ = json.loads((SRC / "data" / "faq.json").read_text())
for _f in sorted((SRC / "data" / "faq").glob("*.json")) if (SRC / "data" / "faq").exists() else []:
    FAQ.update({k: v for k, v in json.loads(_f.read_text()).items() if not k.startswith("_")})
IMG = json.loads((SRC / "img" / "manifest.json").read_text())
P = SITE["prices"]
BASE = SITE["base_url"].rstrip("/")
YEAR = date.today().year
WARN = []

NAV = [
    ("menus", "Menus", "menus/"),
    ("plans", "Meal Plans", "meal-plans/"),
    ("how", "How It Works", "how-it-works/"),
    ("pricing", "Pricing", "pricing/"),
    ("private", "Private Chef", "private-chef-raleigh/"),
    ("catering", "Catering", "catering-weddings/"),
    ("chef", "Chef Mike", "chef-michael-saunders/"),
]
FOOTER_COLS = [
    ("Menus", [("This week's menu", "menus/"), ("Meal plans & membership", "meal-plans/"), ("Zone meals", "zone-meal-delivery/"), ("Paleo meals", "paleo-meal-delivery/"),
               ("Low-Carb Dairy-Free", "low-carb-dairy-free-meals/"), ("Family dinners", "family-meal-delivery/"), ("Protein by the pound", "protein-by-the-pound/")]),
    ("Company", [("Meet Chef Mike", "chef-michael-saunders/"), ("Reviews", "reviews/"), ("How it works", "how-it-works/"),
                 ("Delivery area", "delivery-area/"), ("Pricing", "pricing/"), ("FAQ", "faq/"), ("JOMB at a glance", "about-jomb/")]),
    ("Beyond the box", [("Private chef dinners", "private-chef-raleigh/"), ("Catering & weddings", "catering-weddings/"),
                        ("Gift cards", "gift-cards/"), ("Contact", "contact/")]),
]

PLANS = {
    "zone": {"tag": "Most popular", "title": "Zone", "img": "zone-plate", "path": "zone-meal-delivery/",
             "blurb": "Breakfast, lunch and dinner for 6 days, built to 4-block macros for fat loss and lean muscle.",
             "from": P["zone_all"]["per"], "unit": "per meal · full plan"},
    "paleo": {"tag": "No grains · no dairy", "title": "Paleo", "img": "paleo-plate", "path": "paleo-meal-delivery/",
              "blurb": "Six days of lunches and dinners with no grains, no dairy and no added sugar.",
              "from": P["paleo_lunch"]["per"], "unit": "per lunch"},
    "lcdf": {"tag": "Lighter & cleaner", "title": "Low-Carb Dairy-Free", "img": "lcdf-plate", "path": "low-carb-dairy-free-meals/",
             "blurb": "Six days of lunches and dinners for cleaner, lighter eating that still tastes like a restaurant.",
             "from": P["lcdf_lunch"]["per"], "unit": "per lunch"},
    "family": {"tag": "Feeds 3", "title": "Family Dinners", "img": "family-plate", "path": "family-meal-delivery/",
               "blurb": "Real dinners the whole table will eat. Each one feeds three adults, or two adults and two kids.",
               "from": "75", "unit": "per dinner · feeds 3"},
}

ICONS = {
    "check": '<path d="M5 12.5l4.5 4.5L19 7.5"/>',
    "calendar": '<rect x="3.5" y="5" width="17" height="15.5" rx="2.5"/><path d="M3.5 10h17M8 3v4M16 3v4"/>',
    "cart": '<path d="M3 4h2.2l2.1 11.2a1.5 1.5 0 0 0 1.5 1.2h8.6a1.5 1.5 0 0 0 1.5-1.1L21 8H6.3"/><circle cx="9.5" cy="20" r="1.3"/><circle cx="17.5" cy="20" r="1.3"/>',
    "truck": '<path d="M2.5 6.5h11v9h-11zM13.5 9.5h4l3 3.2v2.8h-7z"/><circle cx="6.5" cy="17.5" r="1.8"/><circle cx="17" cy="17.5" r="1.8"/>',
    "cooler": '<rect x="3.5" y="8" width="17" height="12" rx="2"/><path d="M3.5 12h17M9 8V5.5h6V8"/>',
    "phone": '<path d="M6.6 3.5h2.6l1.4 4.1-1.9 1.3a11.5 11.5 0 0 0 6.4 6.4l1.3-1.9 4.1 1.4v2.6a2 2 0 0 1-2.2 2A16.8 16.8 0 0 1 4.6 5.7a2 2 0 0 1 2-2.2z"/>',
    "mail": '<rect x="3" y="5.5" width="18" height="13" rx="2.5"/><path d="M3.5 7l8.5 6 8.5-6"/>',
    "pin": '<path d="M12 21s7-6.2 7-11.5A7 7 0 0 0 5 9.5C5 14.8 12 21 12 21z"/><circle cx="12" cy="9.5" r="2.5"/>',
    "chef": '<path d="M7 14.5V20h10v-5.5"/><path d="M7 14.5a4 4 0 0 1-1.2-7.8A4.5 4.5 0 0 1 12 4a4.5 4.5 0 0 1 6.2 2.7A4 4 0 0 1 17 14.5z"/><path d="M7 17h10"/>',
    "leaf": '<path d="M5 19c0-8 5.5-13.5 15-14-0.5 9.5-6 15-14 15"/><path d="M5 19c3-4 6-6.5 9.5-8.5"/>',
    "dumbbell": '<path d="M6.5 7v10M17.5 7v10M3.5 9.5v5M20.5 9.5v5M6.5 12h11"/>',
    "flame": '<path d="M12 21c4 0 6.5-2.6 6.5-6.2 0-4-3.2-6.3-4.2-10.3-2.3 1.7-3.4 4-3.3 6.3-1-1-1.6-2.1-1.8-3.3C7.4 9.4 5.5 11.6 5.5 14.8 5.5 18.4 8 21 12 21z"/>',
    "clock": '<circle cx="12" cy="12" r="8.5"/><path d="M12 7.5V12l3 2"/>',
    "gift": '<rect x="3.5" y="8.5" width="17" height="4" rx="1"/><path d="M5 12.5V20h14v-7.5M12 8.5V20M12 8.5C10.5 5 7 5 7 7s3 1.5 5 1.5zM12 8.5c1.5-3.5 5-3.5 5-1.5s-3 1.5-5 1.5z"/>',
    "users": '<circle cx="9" cy="8.5" r="3.2"/><path d="M3 19.5c.6-3.3 3-5.2 6-5.2s5.4 1.9 6 5.2"/><circle cx="17" cy="9.5" r="2.4"/><path d="M16.5 14.4c2.4.2 4 1.8 4.5 4.6"/>',
    "star": '<path d="M12 3.8l2.5 5.2 5.6.7-4.1 3.9 1 5.6-5-2.7-5 2.7 1-5.6-4.1-3.9 5.6-.7z"/>',
    "plate": '<circle cx="12" cy="12" r="8.5"/><circle cx="12" cy="12" r="4.5"/>',
    "sparkle": '<path d="M12 3.5l1.8 5.2 5.2 1.8-5.2 1.8L12 17.5l-1.8-5.2L5 10.5l5.2-1.8zM18.5 15.5l.8 2.2 2.2.8-2.2.8-.8 2.2-.8-2.2-2.2-.8 2.2-.8z"/>',
    "heart": '<path d="M12 20s-7.5-4.6-7.5-10A4.3 4.3 0 0 1 12 7.6 4.3 4.3 0 0 1 19.5 10c0 5.4-7.5 10-7.5 10z"/>',
    "briefcase": '<rect x="3.5" y="7.5" width="17" height="12" rx="2"/><path d="M9 7.5V5.5h6v2M3.5 12.5h17"/>',
    "arrow": '<path d="M5 12h14M13 6l6 6-6 6"/>',
    "menu": '<path d="M4 7h16M4 12h16M4 17h16"/>',
    "close": '<path d="M6 6l12 12M18 6L6 18"/>',
    "instagram": '<rect x="3.5" y="3.5" width="17" height="17" rx="5"/><circle cx="12" cy="12" r="4"/><circle cx="17.3" cy="6.7" r=".9" fill="currentColor"/>',
    "facebook": '<path d="M14 8.5h2.5V5H14a3.5 3.5 0 0 0-3.5 3.5V11H8v3.5h2.5V21H14v-6.5h2.5L17 11h-3V9a.5.5 0 0 1 .5-.5z"/>',
    "list": '<path d="M9 6.5h11M9 12h11M9 17.5h11"/><circle cx="4.5" cy="6.5" r="1"/><circle cx="4.5" cy="12" r="1"/><circle cx="4.5" cy="17.5" r="1"/>',
}


def icon(name, cls=""):
    body = ICONS.get(name)
    if body is None:
        WARN.append(f"unknown icon {name}")
        body = ICONS["sparkle"]
    c = f' class="{cls}"' if cls else ""
    return (f'<svg{c} viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" '
            f'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">{body}</svg>')


_mark_n = [0]


def brand_mark():
    _mark_n[0] += 1
    i = _mark_n[0]
    return (f'<svg class="brand-mark" viewBox="0 0 48 48" aria-hidden="true"><defs><mask id="bite{i}">'
            '<rect width="48" height="48" fill="#fff"/><circle cx="45.5" cy="15" r="5.6" fill="#000"/>'
            '<circle cx="47" cy="24" r="5.6" fill="#000"/><circle cx="45.5" cy="33" r="5.6" fill="#000"/></mask></defs>'
            f'<circle cx="24" cy="24" r="21.5" fill="#C8402A" mask="url(#bite{i})"/>'
            '<circle cx="22.5" cy="24" r="11.5" fill="none" stroke="#FAF6EF" stroke-width="2.2"/></svg>')


def logo_img(pg, dark=False):
    lg = SITE.get("logo")
    if not lg:
        return brand_mark() + '<span class="brand-name">Just One More Bite<small>Chef-made · Raleigh, NC</small></span>'
    src = lg["file_dark"] if dark else lg["file"]
    return (f'<img class="brand-logo" src="{pg.rel(src)}" width="{lg["width"]}" height="{lg["height"]}" '
            f'alt="{esc(lg["alt"])}" decoding="async">')


def money(v):
    v = float(v)
    return f"${v:,.0f}" if v == int(v) else f"${v:,.2f}"


def esc(s):
    return html.escape(str(s), quote=True)


class Page:
    def __init__(self, path):
        self.path = path  # "" for home, "zone-meal-delivery/" etc.
        self.depth = path.count("/")
        self.faq = []
        self.extra_ld = []

    def rel(self, target):
        prefix = "../" * self.depth
        if target in ("", "/"):
            return prefix or "./"
        return prefix + target.lstrip("/")


def img_tag(pg, spec):
    parts = spec.split("|")
    slug = parts[0].strip()
    sizes = parts[1].strip() if len(parts) > 1 and parts[1].strip() else "(min-width: 900px) 50vw, 100vw"
    cls = parts[2].strip() if len(parts) > 2 else ""
    eager = len(parts) > 3 and parts[3].strip() == "eager"
    alt = parts[4].strip() if len(parts) > 4 and parts[4].strip() else None
    m = IMG.get(slug)
    if not m:
        WARN.append(f"{pg.path or 'home'}: unknown image {slug}")
        return ""
    ws = m["widths"]
    src_w = 800 if 800 in ws else ws[min(1, len(ws) - 1)]
    srcset = ", ".join(f'{pg.rel("img/" + slug + "-" + str(w) + ".webp")} {w}w' for w in ws)
    h = round(m["h"] * src_w / m["w"])
    load = 'fetchpriority="high" decoding="async"' if eager else 'loading="lazy" decoding="async"'
    c = f' class="{cls}"' if cls else ""
    return (f'<img{c} src="{pg.rel("img/" + slug + "-" + str(src_w) + ".webp")}" srcset="{srcset}" sizes="{sizes}" '
            f'width="{src_w}" height="{h}" alt="{esc(alt or m["alt"])}" {load}>')


def towns_sentence():
    t = SITE["towns"]
    return ", ".join(t[:-1]) + " and " + t[-1]


def render_menu(pg, key):
    data = MENU.get(key)
    if not data:
        WARN.append(f"unknown menu {key}")
        return ""
    names = {"zone": "Zone Menu", "paleo": "Paleo Menu", "lcdf": "Low-Carb Dairy-Free Menu", "family": "Family Menu", "protein": "Protein by the Pound"}
    groups = []
    for gname, g in data.items():
        items = "".join(f"<li>{esc(i)}</li>" for i in g["items"])
        label = {"breakfasts": "Breakfasts", "lunches": "Lunches", "dinners": "Dinners", "extras": "Sides & extras", "this_week": "This week's proteins"}.get(gname, gname.title())
        groups.append(f'<div class="menu-group"><h4>{label} <span>{esc(g.get("note", ""))}</span></h4><ol>{items}</ol></div>')
    return (f'<div class="menu-board"><div class="menu-board-head"><h3>{names.get(key, key)}</h3>'
            f'<span class="menu-week">{esc(MENU["week_label"])}</span></div><div class="menu-cols">{"".join(groups)}</div>'
            f'<div class="menu-foot"><p>{esc(MENU["order_by"])}. A brand-new menu posts every {SITE["menu_posted"]}. No substitutions.</p>'
            f'<a class="btn btn--primary btn--sm" href="{SITE["store_url"]}">{icon("cart")}Order in the JOMB Store</a></div></div>')


def render_plans(pg, arg):
    keys = [k.strip() for k in arg.split(",")] if arg else list(PLANS)
    cards = []
    for k in keys:
        p = PLANS[k]
        cards.append(
            f'<article class="plan reveal"><div class="plan-photo">{img_tag(pg, p["img"] + "|(min-width: 1150px) 25vw, (min-width: 680px) 50vw, 100vw")}</div>'
            f'<span class="plan-tag">{esc(p["tag"])}</span><div class="plan-body"><h3>{esc(p["title"])}</h3><p>{esc(p["blurb"])}</p>'
            f'<div class="plan-price"><strong>${p["from"]}</strong><span>{esc(p["unit"])}</span></div>'
            f'<a class="text-link stretched" href="{pg.rel(p["path"])}">See the menu<span class="sr-only"> for {esc(p["title"])}</span></a></div></article>')
    return f'<div class="plans">{"".join(cards)}</div>'


def render_steps(pg, arg):
    steps = [
        ("calendar", "1", "Pick your menu", f"A brand-new menu drops every {SITE['menu_posted']}. Choose Zone, Paleo, Low-Carb Dairy-Free or Family dinners.", f"Every {SITE['menu_posted'].split()[0]}"),
        ("cart", "2", "Order by Saturday night", f"Check out online in the JOMB Store before {SITE['cutoff_day']} at {SITE['cutoff_time']}. Order one week, or subscribe and save.", f"{SITE['cutoff_day']} · {SITE['cutoff_time']}"),
        ("truck", "3", "We cook. You eat.", f"Chef Mike cooks it all from scratch, and it arrives {SITE['delivery_day']} at your home, office or gym. Heat, plate, enjoy.", f"{SITE['delivery_day']} · {SITE['delivery_window']}"),
    ]
    out = []
    for ic, n, h, p, when in steps:
        out.append(f'<div class="step reveal"><span class="step-num">0{n}</span><span class="step-icon">{icon(ic)}</span>'
                   f'<h3>{h}</h3><p>{p}</p><span class="step-when">{when}</span></div>')
    return f'<div class="steps">{"".join(out)}</div>'


def render_quote(pg, arg):
    parts = arg.split("|")
    t = TESTI.get(parts[0].strip())
    if not t:
        WARN.append(f"unknown testimonial {arg}")
        return ""
    feature = len(parts) > 1 and parts[1].strip() == "feature"
    short = len(parts) > 1 and parts[1].strip() == "short"
    text = t["short"] if short else t["quote"]
    cls = "quote quote--feature reveal" if feature else "quote reveal"
    return (f'<figure class="{cls}"><blockquote>{esc(text)}</blockquote><figcaption><span><b>{esc(t["name"])}</b>'
            f'{esc(t["detail"])}</span></figcaption></figure>')


def render_quotes(pg, arg):
    ids = [i.strip() for i in arg.split(",")]
    cls = "quotes quotes--3" if len(ids) % 3 == 0 else "quotes"
    return f'<div class="{cls}">' + "".join(render_quote(pg, i) for i in ids) + "</div>"


def render_faq(pg, arg):
    groups = [g.strip() for g in arg.split(",")]
    items = []
    for g in groups:
        if g not in FAQ:
            WARN.append(f"unknown faq group {g}")
            continue
        for qa in FAQ[g]:
            a = fill(pg, qa["a"])
            q = fill(pg, qa["q"])
            pg.faq.append((q, a))
            items.append(f'<details><summary>{q}</summary><div class="answer"><p>{a}</p></div></details>')
    return f'<div class="faq">{"".join(items)}</div>'


def render_price_table(pg, arg):
    groups = {
        "zone": ["zone_all", "zone_double", "zone_breakfast", "zone_lunch", "zone_dinner"],
        "lcdf": ["lcdf_lunch", "lcdf_dinner"],
        "paleo": ["paleo_lunch", "paleo_dinner"],
        "family": ["family_meal", "family_soup", "family_salad", "fruit"],
        "protein": ["protein_chicken", "protein_beef", "protein_pork", "protein_seafood"],
    }
    keys = []
    for g in ([a.strip() for a in arg.split(",")] if arg else list(groups)):
        keys += groups[g]
    rows = []
    for k in keys:
        v = P[k]
        per = f'${v["per"]}' if "per" in v else "—"
        desc = esc(v.get("desc", ""))
        rows.append(f'<tr><td><strong>{esc(v["label"])}</strong><br><span class="muted small">{desc}</span></td>'
                    f'<td class="num">{money(v["price"])}</td><td class="num">{per}</td></tr>')
    return ('<div class="table-wrap"><table class="table"><thead><tr><th>Plan</th><th class="num">Price</th>'
            f'<th class="num">Per meal</th></tr></thead><tbody>{"".join(rows)}</tbody></table></div>'
            '<p class="note mt-1">Prices before NC sales tax. Checkout in the JOMB Store.</p>')


def render_facts(pg, arg):
    facts = [
        (f"{SITE['cutoff_day'][:3]} {SITE['cutoff_time']}", "Order deadline for next week"),
        (SITE["delivery_day"], f"Delivered {SITE['delivery_window']}"),
        (SITE["menu_posted"].split()[0][:3] + ".", "New menu every week"),
        (f"${P['zone_breakfast']['per']}", "Meals from, before tax"),
    ]
    return '<div class="facts">' + "".join(f'<div class="fact"><b>{a}</b><span>{b}</span></div>' for a, b in facts) + "</div>"


def render_creds(pg, arg):
    items = "".join(f'<li>{esc(r["place"])}<span>{esc(r["role"])} · {esc(r["city"])}</span></li>' for r in SITE["chef"]["resume"])
    return (f'<section class="creds" aria-label="Chef Michael Saunders\' résumé"><div class="container creds-inner">'
            f'<span class="creds-label">Chef Mike\'s kitchens</span><ul class="creds-list">{items}</ul></div></section>')


def render_marquee(pg, arg):
    words = "".join(f"<span>{esc(w)}</span>" for w in MENU["marquee"])
    return f'<div class="marquee" aria-hidden="true"><div class="marquee-track">{words}{words}</div></div>'


def render_cta(pg, arg):
    slug = arg or "meals-rows"
    return (f'<section class="section section--tight"><div class="container"><div class="cta-band reveal">{img_tag(pg, slug + "|100vw")}'
            f'<div class="cta-band-inner"><span class="eyebrow">Next week, handled</span><h2>Dinner is already <em>decided.</em></h2>'
            f'<p>New menu every {SITE["menu_posted"]}. Order by {SITE["cutoff_day"]} at {SITE["cutoff_time"]}, and Chef Mike delivers {SITE["delivery_day"]}.</p>'
            f'<div class="btn-row"><a class="btn btn--primary btn--lg" href="{SITE["store_url"]}">{icon("cart")}Order this week</a>'
            f'<a class="btn btn--outline-light btn--lg" href="{pg.rel("menus/")}">See the menu</a></div>'
            f'<p class="small">Questions? Call <a href="tel:{SITE["phone_tel"]}">{SITE["phone_display"]}</a> or email '
            f'<a href="mailto:{SITE["email"]}">{SITE["email"]}</a>.</p></div></div></div></section>')


def render_resume(pg, arg):
    items = "".join(f'<li><b>{esc(r["role"])}</b>, {esc(r["place"])} <span class="muted">· {esc(r["city"])}</span></li>' for r in SITE["chef"]["resume"])
    return f'<ul class="checks">{items}</ul>'


def render_towns(pg, arg):
    return '<ul class="chips">' + "".join(f'<li>{icon("pin")}{esc(t)}</li>' for t in SITE["towns"]) + "</ul>"


def breadcrumbs(pg, meta):
    crumbs = [("Home", "")] + [tuple(c) for c in meta.get("breadcrumb", [])]
    out = []
    for i, (name, path) in enumerate(crumbs):
        if i == len(crumbs) - 1:
            out.append(f'<li aria-current="page">{esc(name)}</li>')
        else:
            out.append(f'<li><a href="{pg.rel(path)}">{esc(name)}</a></li>')
    return f'<nav class="breadcrumbs" aria-label="Breadcrumb"><ol>{"".join(out)}</ol></nav>'


SIMPLE = None


def simple_values():
    return {
        "phone": SITE["phone_display"], "tel": SITE["phone_tel"], "email": SITE["email"], "store": SITE["store_url"],
        "phone_link": f'<a href="tel:{SITE["phone_tel"]}">{SITE["phone_display"]}</a>',
        "email_link": f'<a href="mailto:{SITE["email"]}">{SITE["email"]}</a>',
        "cutoff": f'{SITE["cutoff_day"]} at {SITE["cutoff_time"]}', "cutoff_short": f'{SITE["cutoff_day"][:3]} {SITE["cutoff_time"]}',
        "delivery_day": SITE["delivery_day"], "delivery_window": SITE["delivery_window"],
        "delivery": f'{SITE["delivery_day"]}, {SITE["delivery_window"]}', "menu_posted": SITE["menu_posted"],
        "week_label": MENU["week_label"], "order_by": MENU["order_by"], "towns_sentence": towns_sentence(),
        "chef": SITE["chef"]["display"], "chef_nick": SITE["chef"]["nick"], "chef_years": SITE["chef"]["years"],
        "name": SITE["name"], "year": str(YEAR), "instagram": SITE["instagram"], "facebook": SITE["facebook"],
        "entity": SITE["entity"],
        "updated": date.today().strftime("%B %Y"),
        "trust": SITE.get("compliance", {}).get("line", "") if SITE.get("compliance", {}).get("enabled") else "",
    }


PH = re.compile(r"\{\{\s*([a-z_]+)(?::([^}]*))?\s*\}\}")


def fill(pg, text, meta=None):
    global SIMPLE
    SIMPLE = SIMPLE or simple_values()

    def rep(m):
        key, arg = m.group(1), (m.group(2) or "").strip()
        if key in SIMPLE and not arg:
            return SIMPLE[key]
        if key == "price":
            return money(P[arg]["price"])
        if key == "per":
            return "$" + P[arg]["per"]
        if key == "link":
            return pg.rel(arg)
        if key == "asset":
            return pg.rel(arg)
        if key == "img":
            return img_tag(pg, arg)
        if key == "icon":
            return icon(arg)
        if key == "menu":
            return render_menu(pg, arg)
        if key == "plans":
            return render_plans(pg, arg)
        if key == "steps":
            return render_steps(pg, arg)
        if key == "quote":
            return render_quote(pg, arg)
        if key == "quotes":
            return render_quotes(pg, arg)
        if key == "faq":
            return render_faq(pg, arg)
        if key == "price_table":
            return render_price_table(pg, arg)
        if key == "facts":
            return render_facts(pg, arg)
        if key == "creds":
            return render_creds(pg, arg)
        if key == "marquee":
            return render_marquee(pg, arg)
        if key == "cta_band":
            return render_cta(pg, arg)
        if key == "resume":
            return render_resume(pg, arg)
        if key == "towns_chips":
            return render_towns(pg, arg)
        if key == "breadcrumbs":
            return breadcrumbs(pg, meta or {})
        if key == "membership_featured":
            return render_mbr_featured(pg, arg)
        if key == "membership_table":
            return render_mbr_table(pg, arg)
        if key == "membership_from":
            return mbr_from()
        if key == "membership_save_max":
            return mbr_save_max()
        if key == "membership_mini":
            return render_mbr_mini(pg, arg)
        if key == "membership_perks":
            return render_mbr_perks(pg, arg)
        if key == "membership_json":
            return render_mbr_json(pg, arg)
        if key == "proposal":
            return render_proposal(pg, arg)
        WARN.append(f"{pg.path or 'home'}: unknown placeholder {m.group(0)}")
        return m.group(0)

    prev = None
    while prev != text:  # allow placeholders that produce placeholders
        prev = text
        text = PH.sub(rep, text)
    return text


# ---------- membership (proposed subscription plans) ----------
from urllib.parse import quote as _q

MBR = SITE.get("membership", {})


def plan_quote(household, days, coverage="dinner", menu="family"):
    hh = next(h for h in MBR["households"] if h["key"] == household)
    days = int(days)
    disc = MBR["discount"][str(days)]
    if "family_dinners" in hh:
        meals = days * hh["family_dinners"]
        base = meals * MBR["family_dinner"]
        unit = "family dinner"
    else:
        cov = next(c for c in MBR["coverage"] if c["key"] == coverage)
        per_day = sum(MBR["menus"][menu][meal] for meal in cov["meals"])
        meals = days * len(cov["meals"]) * hh["people"]
        base = per_day * days * hh["people"]
        unit = "meal"
    price = round(base * (1 - disc), 2)
    return {"base": round(base, 2), "price": price, "save": round(base - price, 2), "per": round(price / meals, 2),
            "meals": meals, "unit": unit, "monthly": round(price * MBR["weeks_per_month"]), "disc": disc,
            "deliveries": MBR["deliveries"][str(days)]}


def m2(v):
    return f"${v:,.2f}"


def plan_mailto(name, detail):
    body = (f"Hi Chef Mike,\n\nI'd like to start the {name} plan ({detail}).\n\nName:\nDelivery address (home, office or gym):\n"
            f"Phone:\nAny allergies:\nStart week:\n\nThanks!")
    return f"mailto:{SITE['email']}?subject={_q('JOMB Membership: ' + name)}&body={_q(body)}"


def mbr_from():
    best = None
    for h in MBR["households"]:
        for d in MBR["days"]:
            if "family_dinners" in h:
                combos = [("dinner", "family")]
            else:
                combos = [(c["key"], m) for m, mv in MBR["menus"].items() for c in MBR["coverage"]
                          if ("menus" not in c or m in c["menus"]) and all(meal in mv for meal in c["meals"])]
            for cov, menu in combos:
                p = plan_quote(h["key"], d, cov, menu)["price"]
                best = p if best is None or p < best else best
    return m2(best)


def mbr_save_max():
    return f'{round(max(MBR["discount"].values()) * 100)}%'


def render_mbr_featured(pg, arg):
    cards = []
    for f in MBR.get("featured", []):
        q = plan_quote(f["household"], f["days"], f["coverage"], f["menu"])
        hh = next(h for h in MBR["households"] if h["key"] == f["household"])
        cov = next(c for c in MBR["coverage"] if c["key"] == f["coverage"])
        menu_label = "Family menu" if f["menu"] == "family" else MBR["menus"][f["menu"]]["label"]
        detail = f'{hh["label"]} · {f["days"]} days a week · {cov["label"].lower()} · {menu_label}'
        deliv = "1 delivery a week" if q["deliveries"] == 1 else f'{q["deliveries"]} deliveries a week'
        cards.append(
            f'<article class="mbr-plan{" mbr-plan--popular" if f["tag"] == "Most popular" else ""} reveal"><span class="mbr-tag">{esc(f["tag"])}</span><h3>{esc(f["name"])}</h3>'
            f'<p class="mbr-blurb">{esc(f["blurb"])}</p><ul class="mbr-specs"><li>{esc(hh["label"])}</li><li>{f["days"]} days a week</li>'
            f'<li>{esc(cov["label"])} · {esc(menu_label)}</li><li>{deliv}</li></ul>'
            f'<div class="mbr-price"><strong>{m2(q["price"])}</strong><span>/ week</span></div>'
            f'<p class="mbr-math"><s>{m2(q["base"])}</s> · save {m2(q["save"])} a week ({round(q["disc"] * 100)}%) · {m2(q["per"])} per {q["unit"]}</p>'
            f'<p class="mbr-month">About {m2(q["monthly"]).split(".")[0]} a month · {q["meals"]} {q["unit"]}s a week</p>'
            f'<a class="btn btn--primary" href="{plan_mailto(f["name"], detail)}">Start {esc(f["name"])}</a></article>')
    return f'<div class="mbr-plans">{"".join(cards)}</div>'


def render_mbr_table(pg, arg):
    days = MBR["days"]
    head = "".join(f'<th class="num">{d} days</th>' for d in days)
    if arg == "family":
        rows = []
        for hk in ("family", "bigfamily"):
            hh = next(h for h in MBR["households"] if h["key"] == hk)
            cells = "".join(f'<td class="num"><strong>{m2(plan_quote(hk, d)["price"])}</strong><br><span class="muted small">{m2(plan_quote(hk, d)["per"])}/dinner</span></td>' for d in days)
            rows.append(f'<tr><td><strong>{esc(hh["label"])}</strong><br><span class="muted small">{esc(hh["note"])}</span></td>{cells}</tr>')
        title = "Family dinner plans · weekly price"
    else:
        rows = []
        for mk, mv in MBR["menus"].items():
            for c in MBR["coverage"]:
                if "menus" in c and mk not in c["menus"]:
                    continue
                if any(meal not in mv for meal in c["meals"]):
                    continue
                cells = "".join(f'<td class="num"><strong>{m2(plan_quote("one", d, c["key"], mk)["price"])}</strong><br><span class="muted small">{m2(plan_quote("one", d, c["key"], mk)["per"])}/meal</span></td>' for d in days)
                rows.append(f'<tr><td><strong>{esc(mv["label"])}</strong><br><span class="muted small">{esc(c["label"])}</span></td>{cells}</tr>')
        title = "Individual plans · weekly price for one person (two people: double it)"
    disc_row = "".join(f'<td class="num"><span class="mbr-save">save {round(MBR["discount"][str(d)] * 100)}%</span></td>' for d in days)
    return (f'<div class="table-wrap"><table class="table mbr-table"><caption class="sr-only">{esc(title)}</caption><thead><tr><th>Plan</th>{head}</tr></thead>'
            f'<tbody>{"".join(rows)}<tr class="mbr-disc-row"><td><span class="muted small">Subscriber savings vs. one-off orders</span></td>{disc_row}</tr></tbody></table></div>')


def render_mbr_mini(pg, arg):
    items = []
    for f in MBR.get("featured", []):
        q = plan_quote(f["household"], f["days"], f["coverage"], f["menu"])
        items.append(f'<li><span class="mbr-mini-name">{esc(f["name"])}</span><strong>{m2(q["price"])}<small>/wk</small></strong>'
                     f'<span class="mbr-mini-note">{m2(q["per"])} per {q["unit"]} · save {round(q["disc"] * 100)}%</span></li>')
    return f'<ul class="mbr-mini">{"".join(items)}</ul>'


def render_mbr_perks(pg, arg):
    return '<ul class="checks">' + "".join(f"<li>{esc(p)}</li>" for p in MBR.get("perks", [])) + "</ul>"


def render_mbr_json(pg, arg):
    data = {k: v for k, v in MBR.items() if not k.startswith("_")}
    data["email"] = SITE["email"]
    data["store"] = SITE["store_url"]
    return f'<script type="application/json" id="membership-data">{json.dumps(data, ensure_ascii=False)}</script>'


def render_proposal(pg, arg):
    if not SITE.get("preview"):
        return ""
    return f'<span class="proposal-pill">{esc(arg) if arg else "Proposed plan · for Chef Mike’s review"}</span>'


# ---------- structured data ----------

def abs_url(path):
    return f"{BASE}/{path}" if path else f"{BASE}/"


def site_graph():
    biz_id = abs_url("") + "#business"
    chef_id = abs_url("chef-michael-saunders/") + "#chef"
    services = [
        ("Zone meal delivery", "zone-meal-delivery/"), ("Paleo meal delivery", "paleo-meal-delivery/"),
        ("Low-carb, dairy-free meal delivery", "low-carb-dairy-free-meals/"), ("Family meal delivery", "family-meal-delivery/"),
        ("Cooked protein by the pound", "protein-by-the-pound/"), ("Private chef dinners", "private-chef-raleigh/"),
        ("Catering and weddings", "catering-weddings/"),
    ]
    return [
        {
            "@type": "FoodEstablishment", "@id": biz_id, "name": SITE["name"], "alternateName": [SITE["short_name"], "Just One More Bite NC"],
            "legalName": SITE["legal_name"], "description": SITE["entity"], "url": abs_url(""),
            "logo": abs_url(SITE["logo"]["file_png"]) if SITE.get("logo") else abs_url("icon-512.png"), "image": [abs_url("img/og-home.jpg"), abs_url("img/og-default.jpg")],
            "telephone": SITE["phone_tel"], "email": SITE["email"],
            "priceRange": f"${P['zone_breakfast']['per']}–${P['paleo_dinner']['per']} per meal",
            "servesCuisine": ["American", "Zone diet", "Paleo", "Low carb", "Dairy-free"],
            "address": {"@type": "PostalAddress", "addressLocality": "Raleigh", "addressRegion": "NC", "addressCountry": "US"},
            "areaServed": [{"@type": "Place", "name": f"{t}, NC" if "RTP" not in t else "Research Triangle Park, NC"} for t in SITE["towns"]],
            "founder": {"@id": chef_id}, "sameAs": [SITE["instagram"], SITE["facebook"]],
            "potentialAction": {"@type": "OrderAction", "target": SITE["store_url"]},
            "hasOfferCatalog": {"@type": "OfferCatalog", "name": "Just One More Bite menus and services", "itemListElement": [
                {"@type": "Offer", "itemOffered": {"@type": "Service", "name": n, "url": abs_url(u)}} for n, u in services]},
        },
        {
            "@type": "Person", "@id": chef_id, "name": SITE["chef"]["name"], "alternateName": [SITE["chef"]["display"], SITE["chef"]["nick"]],
            "jobTitle": "Executive Chef", "worksFor": {"@id": biz_id}, "url": abs_url("chef-michael-saunders/"),
            "image": abs_url("img/chef-plating-800.webp"),
            "description": "Executive Chef and owner of Just One More Bite in Raleigh, NC. Formerly " + "; ".join(
                f'{r["role"]} at {r["place"]} ({r["city"]})' for r in SITE["chef"]["resume"]) + ".",
            "knowsAbout": ["Zone diet meal prep", "Paleo cooking", "Low-carb, dairy-free cooking", "Steakhouse cuisine", "Private dining", "Catering"],
        },
        {"@type": "WebSite", "@id": abs_url("") + "#website", "url": abs_url(""), "name": SITE["name"], "publisher": {"@id": biz_id}},
    ]


def page_graph(pg, meta):
    url = abs_url(pg.path)
    crumbs = [("Home", "")] + [tuple(c) for c in meta.get("breadcrumb", [])]
    g = [{
        "@type": meta.get("page_type", "WebPage"), "@id": url + "#webpage", "url": url, "name": meta["title"],
        "description": meta["description"], "isPartOf": {"@id": abs_url("") + "#website"},
        "about": {"@id": abs_url("") + "#business"}, "primaryImageOfPage": abs_url(f"img/{meta.get('og', 'og-default')}.jpg"),
        "breadcrumb": {"@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": i + 1, "name": n, "item": abs_url(p)} for i, (n, p) in enumerate(crumbs)]},
    }]
    if meta.get("service"):
        s = meta["service"]
        offers = []
        for k in s.get("offers", []):
            v = P[k]
            offers.append({"@type": "Offer", "name": v["label"], "price": f'{float(v["price"]):.2f}', "priceCurrency": "USD",
                           "url": SITE["store_url"], "description": v.get("desc", v["label"])})
        svc = {"@type": "Service", "@id": url + "#service", "name": s["name"], "description": s["description"], "url": url,
               "provider": {"@id": abs_url("") + "#business"}, "serviceType": s.get("type", s["name"]),
               "areaServed": [{"@type": "Place", "name": t} for t in SITE["towns"]]}
        if offers:
            svc["offers"] = offers
        g.append(svc)
    ptype = meta.get("page_type", "WebPage")
    if ptype == "ProfilePage":
        g[0]["mainEntity"] = {"@id": abs_url("chef-michael-saunders/") + "#chef"}
    elif ptype == "AboutPage":
        g[0]["mainEntity"] = {"@id": abs_url("") + "#business"}
    if pg.faq:
        def strip(h):
            return re.sub(r"<[^>]+>", "", h)
        qs = [{"@type": "Question", "name": strip(q), "acceptedAnswer": {"@type": "Answer", "text": strip(a)}} for q, a in pg.faq]
        if ptype == "FAQPage":
            g[0]["mainEntity"] = qs  # the page itself is the FAQPage: one node, not two
        else:
            g.append({"@type": "FAQPage", "@id": url + "#faq", "mainEntity": qs})
    return g


# ---------- layout ----------

def head(pg, meta, ld):
    if meta.get("special") == "404":
        base_path = urlparse(BASE).path.rstrip("/") + "/"
        return f"""<!doctype html>
<html lang="en-US">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<base href="{base_path}">
<title>{esc(meta["title"])}</title>
<meta name="description" content="{esc(meta["description"])}">
<meta name="robots" content="noindex, follow">
<meta name="theme-color" content="#FAF6EF">
<link rel="stylesheet" href="assets/css/site.css">
<link rel="icon" href="favicon.svg" type="image/svg+xml">
<link rel="apple-touch-icon" href="apple-touch-icon.png">
</head>"""
    title = meta["title"]
    desc = meta["description"]
    og = abs_url(f"img/{meta.get('og', 'og-default')}.jpg")
    robots = '<meta name="robots" content="noindex, nofollow">' if SITE["preview"] else '<meta name="robots" content="index, follow, max-image-preview:large">'
    return f"""<!doctype html>
<html lang="en-US">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{esc(title)}</title>
<meta name="description" content="{esc(desc)}">
{robots}
<link rel="canonical" href="{abs_url(pg.path)}">
<meta name="theme-color" content="#FAF6EF">
<meta property="og:type" content="website">
<meta property="og:site_name" content="{esc(SITE['name'])}">
<meta property="og:title" content="{esc(meta.get('og_title', title))}">
<meta property="og:description" content="{esc(desc)}">
<meta property="og:url" content="{abs_url(pg.path)}">
<meta property="og:image" content="{og}">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:locale" content="en_US">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{esc(meta.get('og_title', title))}">
<meta name="twitter:description" content="{esc(desc)}">
<meta name="twitter:image" content="{og}">
<meta name="geo.region" content="US-NC">
<meta name="geo.placename" content="Raleigh">
<link rel="preload" href="{pg.rel('assets/fonts/fraunces-latin.woff2')}" as="font" type="font/woff2" crossorigin>
<link rel="stylesheet" href="{pg.rel('assets/css/site.css')}">
<link rel="icon" href="{pg.rel('favicon.svg')}" type="image/svg+xml">
<link rel="icon" href="{pg.rel('favicon.png')}" type="image/png" sizes="48x48">
<link rel="apple-touch-icon" href="{pg.rel('apple-touch-icon.png')}">
<link rel="manifest" href="{pg.rel('site.webmanifest')}">
<script type="application/ld+json">{json.dumps({"@context": "https://schema.org", "@graph": ld}, ensure_ascii=False, separators=(",", ":"))}</script>
</head>"""


def header(pg, meta):
    nav_key = meta.get("nav", "")
    cur = ' aria-current="page"'
    links = "".join(
        f'<a href="{pg.rel(p)}"{cur if k == nav_key else ""}>{esc(n)}</a>' for k, n, p in NAV)
    sheet_links = "".join(f'<a href="{pg.rel(p)}">{esc(n)}</a>' for k, n, p in NAV) + \
        f'<a href="{pg.rel("reviews/")}">Reviews</a><a href="{pg.rel("faq/")}">FAQ</a><a href="{pg.rel("contact/")}">Contact</a>'
    ribbon = (f'<div class="preview-ribbon"><strong>Preview</strong> · {esc(SITE["preview_note"])}</div>' if SITE["preview"] else "")
    return f"""<body>
<a class="skip-link" href="#main">Skip to content</a>
{ribbon}
<header class="site-header">
  <div class="container header-inner">
    <a class="brand" href="{pg.rel('')}" aria-label="{esc(SITE['name'])} home">{logo_img(pg)}</a>
    <nav class="nav-desktop" aria-label="Main">{links}</nav>
    <div class="header-actions">
      <a class="btn btn--ghost btn--sm header-call" href="tel:{SITE['phone_tel']}">{icon('phone')}{SITE['phone_display']}</a>
      <a class="btn btn--primary btn--sm header-order" href="{SITE['store_url']}">Order now</a>
      <button class="menu-toggle" type="button" aria-label="Open menu" aria-controls="nav-sheet" aria-expanded="false" data-nav-open>{icon('menu')}</button>
    </div>
  </div>
</header>
<div class="nav-sheet" id="nav-sheet" aria-hidden="true">
  <div class="nav-sheet-top"><a class="brand" href="{pg.rel('')}" aria-label="{esc(SITE['name'])} home">{logo_img(pg)}</a>
    <button class="menu-toggle" type="button" aria-label="Close menu" data-nav-close>{icon('close')}</button></div>
  <nav aria-label="Mobile">{sheet_links}</nav>
  <div class="btn-row"><a class="btn btn--primary btn--lg" href="{SITE['store_url']}">{icon('cart')}Order now</a>
    <a class="btn btn--ghost btn--lg" href="tel:{SITE['phone_tel']}">{icon('phone')}Call</a></div>
  <p class="nav-sheet-meta">Order by {SITE['cutoff_day']} at {SITE['cutoff_time']} · Delivered {SITE['delivery_day']} · {esc(towns_sentence())}</p>
</div>
<main id="main">"""


def footer(pg):
    comp = SITE.get("compliance", {})
    trust_html = f'<p class="footer-trust">{esc(comp["line"])}</p>' if comp.get("enabled") else ""
    cols = "".join(
        f'<div><h3>{esc(t)}</h3><ul>' + "".join(f'<li><a href="{pg.rel(p)}">{esc(n)}</a></li>' for n, p in items) + "</ul></div>"
        for t, items in FOOTER_COLS)
    return f"""</main>
<footer class="site-footer">
  <div class="container">
    <div class="footer-grid">
      <div class="footer-brand">
        <a class="brand" href="{pg.rel('')}" aria-label="{esc(SITE['name'])} home">{logo_img(pg, dark=True)}</a>
        <p class="footer-tagline">Chef-made meals · Raleigh, NC</p>
        <p>{esc(SITE['entity'])}</p>
        <address class="footer-nap"><span><b>{esc(SITE['legal_name'])}</b></span><span>Raleigh, North Carolina · delivering to {esc(towns_sentence())}</span>
          <a href="tel:{SITE['phone_tel']}">{SITE['phone_display']}</a><a href="mailto:{SITE['email']}">{SITE['email']}</a></address>
        <div class="footer-social"><a href="{SITE['instagram']}" aria-label="Instagram">{icon('instagram')}</a><a href="{SITE['facebook']}" aria-label="Facebook">{icon('facebook')}</a></div>
      </div>
      {cols}
    </div>
    {trust_html}
    <div class="footer-bottom"><span>© {YEAR} {esc(SITE['legal_name'])}. All rights reserved.</span>
      <span>New menu every {SITE['menu_posted']} · Order by {SITE['cutoff_day']} {SITE['cutoff_time']} · Delivered {SITE['delivery_day']}</span></div>
  </div>
</footer>
<div class="mobile-bar" role="region" aria-label="Quick actions">
  <a class="btn btn--ghost" href="tel:{SITE['phone_tel']}">{icon('phone')}Call</a>
  <a class="btn btn--primary" href="{SITE['store_url']}">{icon('cart')}Order this week</a>
</div>
<script src="{pg.rel('assets/js/site.js')}" defer></script>
</body>
</html>
"""


def parse_page(path):
    raw = path.read_text()
    m = re.match(r"\s*<!--meta\s*(\{.*?\})\s*-->\s*", raw, re.S)
    if not m:
        raise SystemExit(f"{path}: missing <!--meta {{...}} --> header")
    meta = json.loads(m.group(1))
    return meta, raw[m.end():]


def build():
    if OUT.exists():
        for p in OUT.iterdir():
            if p.name == "img" or p.name in ICON_FILES:
                continue
            shutil.rmtree(p) if p.is_dir() else p.unlink()
    OUT.mkdir(exist_ok=True)
    shutil.copytree(SRC / "assets", OUT / "assets", dirs_exist_ok=True, ignore=shutil.ignore_patterns("parts"))
    css = (SRC / "assets" / "css" / "site.css").read_text()
    parts_dir = SRC / "assets" / "css" / "parts"
    for part in sorted(parts_dir.glob("*.css")) if parts_dir.exists() else []:
        css += f"\n/* ---- {part.name} ---- */\n" + part.read_text()
    (OUT / "assets" / "css" / "site.css").write_text(css)
    for f in ("favicon.svg",):
        if (SRC / f).exists():
            shutil.copy(SRC / f, OUT / f)
    # icons made by tools/images.py live in docs/ already (kept)
    pages = []
    for f in sorted((SRC / "pages").glob("*.html")):
        meta, body = parse_page(f)
        pg = Page(meta["path"])
        for k in ("title", "og_title", "description"):
            if k in meta:
                meta[k] = fill(pg, meta[k])
        _mark_n[0] = 0
        content = fill(pg, body, meta)
        ld = site_graph() + page_graph(pg, meta)
        doc = head(pg, meta, ld) + "\n" + header(pg, meta) + "\n" + content + "\n" + footer(pg)
        if "{{" in doc:
            WARN.append(f"{meta['path'] or 'home'}: unreplaced placeholder left in output")
        if meta.get("special") == "404":
            (OUT / "404.html").write_text(doc)
        else:
            d = OUT / meta["path"]
            d.mkdir(parents=True, exist_ok=True)
            (d / "index.html").write_text(doc)
            pages.append(meta)
    write_extras(pages)
    restore_icons()
    check_links()
    print(f"built {len(pages)} pages + 404 into {OUT}")
    for w in dict.fromkeys(WARN):
        print("WARN:", w)
    return 1 if WARN else 0


ICON_FILES = ("favicon.png", "apple-touch-icon.png", "icon-192.png", "icon-512.png")


def restore_icons():
    for f in ICON_FILES:
        if not (OUT / f).exists():
            WARN.append(f"missing {f}: run tools/images.py")


def write_extras(pages):
    (OUT / ".nojekyll").write_text("")
    today = date.today().isoformat()
    urls = "".join(f"<url><loc>{abs_url(m['path'])}</loc><lastmod>{today}</lastmod></url>" for m in pages)
    (OUT / "sitemap.xml").write_text(f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{urls}</urlset>\n')
    (OUT / "robots.txt").write_text(f"User-agent: *\nAllow: /\n\nSitemap: {abs_url('sitemap.xml')}\n")
    (OUT / "site.webmanifest").write_text(json.dumps({
        "name": SITE["name"], "short_name": SITE["short_name"], "start_url": "./", "display": "standalone",
        "background_color": "#FAF6EF", "theme_color": "#C8402A",
        "icons": [{"src": "icon-192.png", "sizes": "192x192", "type": "image/png"}, {"src": "icon-512.png", "sizes": "512x512", "type": "image/png"}]}, indent=1))
    (OUT / "llms.txt").write_text(llms_txt(pages))


def llms_txt(pages):
    lines = [f"# {SITE['name']} ({SITE['short_name']})", "", f"> {SITE['entity']}", "",
             "## Key facts",
             f"- Chef: {SITE['chef']['display']}, Executive Chef and owner. Formerly " + "; ".join(f"{r['role']}, {r['place']} ({r['city']})" for r in SITE['chef']['resume']) + ".",
             f"- New menu posted every {SITE['menu_posted']}. Order by {SITE['cutoff_day']} at {SITE['cutoff_time']}. Delivered {SITE['delivery_day']}, {SITE['delivery_window']}.",
             f"- Delivery area: {towns_sentence()} (North Carolina). Delivered to homes, offices and CrossFit gyms.",
             f"- Phone: {SITE['phone_display']} · Email: {SITE['email']} · Order online: {SITE['store_url']}",
             f"- Prices (before tax): Zone {money(P['zone_all']['price'])} for 18 meals (${P['zone_all']['per']}/meal); Low-Carb Dairy-Free lunches ${P['lcdf_lunch']['per']}, dinners ${P['lcdf_dinner']['per']}; Paleo lunches ${P['paleo_lunch']['per']}, dinners ${P['paleo_dinner']['per']}; Family dinner {money(P['family_meal']['price'])} (feeds 3).",
             "", "## Pages"]
    for m in pages:
        lines.append(f"- [{m['title']}]({abs_url(m['path'])}): {m['description']}")
    lines += ["", f"## Latest menu ({MENU['week_label']})"]
    for key, label in (("zone", "Zone"), ("paleo", "Paleo"), ("lcdf", "Low-Carb Dairy-Free"), ("family", "Family")):
        for g, d in MENU[key].items():
            lines.append(f"- {label} {g}: " + "; ".join(d["items"]))
    return "\n".join(lines) + "\n"


def check_links():
    for f in OUT.rglob("*.html"):
        doc = f.read_text()
        base_path = urlparse(BASE).path.rstrip("/") + "/"
        for href in re.findall(r'(?:href|src)="([^"#?]+)', doc):
            if href.startswith(("http", "mailto:", "tel:", "data:")):
                continue
            if f.name == "404.html" and href.startswith(base_path):
                href = href[len(base_path):] or "./"
            target = (f.parent / href).resolve()
            if href.endswith("/") or target.is_dir():
                target = target / "index.html"
            if not target.exists():
                WARN.append(f"broken link in {f.relative_to(OUT)}: {href}")
        for s in re.findall(r'srcset="([^"]+)"', doc):
            for part in s.split(","):
                u = part.strip().split(" ")[0]
                if not (f.parent / u).resolve().exists():
                    WARN.append(f"missing image in {f.relative_to(OUT)}: {u}")


if __name__ == "__main__":
    import fcntl
    with open(ROOT / ".build.lock", "w") as _lock:
        fcntl.flock(_lock, fcntl.LOCK_EX)  # parallel agents: one build at a time
        sys.exit(build())
