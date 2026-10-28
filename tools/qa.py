#!/usr/bin/env python3
"""QA gate for the Just One More Bite website: checks every built page in docs/.

    <venv>/bin/python tools/qa.py                          # full sweep: static + browser + axe + Lighthouse + production pass
    <venv>/bin/python tools/qa.py --pages home,menus --no-lighthouse
    python3 tools/qa.py --no-browser --no-lighthouse        # static checks only (standard library, no venv)

Checks
  1. SEO basics          title/description length + uniqueness, one H1, heading order, canonical, lang, img alt/size,
                         internal links resolve (sub-path safe), no {{ left, >= 3 internal links in <main>, sitemap.
  2. Structured data     JSON-LD parses, required properties, FAQPage == visible <details>, telephone == tel: links.
  3. Facts               phone, deadline, delivery day/window, menu day, prices, email vs src/site.json; banned claims
                         (medical, superlatives, AI filler), regulatory trust claims outside the compliance switch,
                         street addresses, legal hedging.
  4. Responsive          headless Chrome at 320-1440 px: horizontal overflow (+ widest offender), clipped text,
                         tap targets, console errors, failed requests, broken images, 404 page at a nested URL.
  5. Accessibility       axe-core (WCAG 2.2 AA + best practice) at 390 and 1440 px, plus the open mobile nav sheet.
  6. Performance         Lighthouse mobile + desktop on a local GitHub-Pages-like server (gzip, /justonemorebite/ prefix);
                         a second production pass builds a copy with "preview": false and re-checks SEO (no noindex).

Writes qa/REPORT.md and qa/report.json. Exit code 1 if anything FAILs.

Node tools (axe-core, lighthouse) come from $QA_NODE (an npm --prefix folder), default ~/.cache/jomb-qa-node.
Install once with:  python3 tools/qa.py --install   (runs npm install --prefix $QA_NODE axe-core lighthouse)
Everything runs headless; nothing is published.
"""
import argparse
import fcntl
import gzip
import html
import json
import mimetypes
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from collections import Counter, defaultdict
from datetime import datetime
from html.parser import HTMLParser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
SRC = ROOT / "src"
OUT_DIR = ROOT / "qa"
NODE_PREFIX = Path(os.environ.get("QA_NODE") or Path.home() / ".cache" / "jomb-qa-node")
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
PREFIX = "/justonemorebite/"  # GitHub Pages project sub-path

PLANNED = ["home", "menus", "zone-meal-delivery", "paleo-meal-delivery", "low-carb-dairy-free-meals",
           "family-meal-delivery", "protein-by-the-pound", "how-it-works", "delivery-area", "pricing", "faq",
           "chef-michael-saunders", "about-jomb", "private-chef-raleigh", "catering-weddings", "gift-cards",
           "contact", "reviews", "meal-plans", "404"]
WIDTHS = [320, 360, 390, 414, 768, 1024, 1280, 1440]
AXE_WIDTHS = (390, 1440)
MOBILE_MAX = 480

FAIL, WARN, INFO = "FAIL", "WARN", "INFO"
CATS = ["seo", "schema", "facts", "responsive", "a11y", "perf"]
CAT_LABEL = {"seo": "SEO", "schema": "Schema", "facts": "Facts", "responsive": "Responsive", "a11y": "A11y",
             "perf": "Lighthouse", "site": "Site", "prod": "Production build"}

# Classes rendered by build.py / site.css (shared chrome and components): issues there belong to the design system.
SYSTEM_RE = re.compile(r"(^|[\s.#>])(head|title|html|site-header|header-inner|header-actions|header-call|header-order|"
                       r"nav-desktop|nav-sheet|menu-toggle|brand|brand-name|site-footer|footer-[\w-]+|mobile-bar|"
                       r"preview-ribbon|skip-link|cta-band[\w-]*|plans|plan|plan-[\w-]+|steps|step|step-[\w-]+|"
                       r"menu-board[\w-]*|menu-group|menu-cols|menu-foot|menu-week|facts|fact|creds[\w-]*|marquee[\w-]*|"
                       r"quotes?|quote--[\w-]+|faq|breadcrumbs|table-wrap|chips|btn--sm|footer)\b|JSON-LD site graph|"
                       r"site\.css|site\.js|build\.py")


# ---------------------------------------------------------------- tiny DOM (stdlib) ---------------------------------

VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}
SKIP_TEXT = {"script", "style", "noscript", "template", "svg"}
BLOCK = {"p", "li", "tr", "h1", "h2", "h3", "h4", "h5", "h6", "summary", "figcaption", "blockquote", "dt", "dd",
         "caption", "section", "article", "div", "header", "footer", "nav", "main", "aside", "details", "table",
         "ul", "ol", "address", "figure", "form", "label", "button", "title", "body", "html", "thead", "tbody"}
HEADINGS = ("h1", "h2", "h3", "h4", "h5", "h6")
TIGHT_INLINE = {"em", "i", "u", "mark", "sup", "sub", "abbr", "s", "q", "wbr"}


class Node:
    __slots__ = ("tag", "attrs", "children", "parent", "line")

    def __init__(self, tag, attrs, parent, line=0):
        self.tag, self.attrs, self.children, self.parent, self.line = tag, attrs, [], parent, line

    def get(self, k, d=None):
        return self.attrs.get(k, d)

    def iter(self):
        for c in self.children:
            if isinstance(c, Node):
                yield c
                yield from c.iter()

    def find_all(self, *tags):
        return [n for n in self.iter() if n.tag in tags]

    def first(self, tag):
        return next((n for n in self.iter() if n.tag == tag), None)

    def classes(self):
        return (self.get("class") or "").split()

    def text(self, skip=SKIP_TEXT):
        out = []

        def walk(n):
            for c in n.children:
                if isinstance(c, str):
                    out.append(c)
                elif c.tag not in skip:
                    if c.tag == "br":
                        out.append(" ")
                    walk(c)
                    if c.tag in BLOCK:
                        out.append(" ")
        walk(self)
        return norm("".join(out))

    def raw_text(self):
        return "".join(c if isinstance(c, str) else c.raw_text() for c in self.children)

    def ancestors(self):
        n = self.parent
        while n is not None:
            yield n
            n = n.parent

    def inside(self, pred):
        return any(pred(a) for a in self.ancestors())


class DomBuilder(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = Node("#root", {}, None)
        self.cur = self.root

    def handle_starttag(self, tag, attrs):
        n = Node(tag, {k: (v if v is not None else "") for k, v in attrs}, self.cur, self.getpos()[0])
        self.cur.children.append(n)
        if tag not in VOID:
            self.cur = n

    def handle_startendtag(self, tag, attrs):
        self.cur.children.append(Node(tag, {k: (v if v is not None else "") for k, v in attrs}, self.cur, self.getpos()[0]))

    def handle_endtag(self, tag):
        n = self.cur
        while n is not None and n.tag != tag:
            n = n.parent
        if n is not None and n.parent is not None:
            self.cur = n.parent

    def handle_data(self, d):
        self.cur.children.append(d)


def parse_html(text):
    b = DomBuilder()
    b.feed(text)
    b.close()
    return b.root


def norm(s):
    s = html.unescape(s) if "&" in s else s
    s = s.replace("\u00a0", " ").replace("\u2009", " ").replace("\u202f", " ").replace("\u200b", "")
    return re.sub(r"\s+", " ", s).strip()


def css_path(n, depth=4):
    parts = []
    while n is not None and n.tag not in ("#root", "html", "body") and len(parts) < depth:
        s = n.tag
        if n.get("id"):
            parts.append(f"{s}#{n.get('id')}")
            break
        cls = [c for c in n.classes() if c not in ("reveal", "is-in")][:2]
        if cls:
            s += "." + ".".join(cls)
        elif n.parent is not None:
            sib = [c for c in n.parent.children if isinstance(c, Node) and c.tag == n.tag]
            if len(sib) > 1:
                s += f":nth-of-type({sib.index(n) + 1})"
        parts.append(s)
        n = n.parent
    return " > ".join(reversed(parts))


def segments(root):
    """Visible text split into blocks: [(text, block_node)]. Table cells are joined with ' | '."""
    out, buf = [], []

    def flush(node):
        s = norm("".join(buf))
        if s:
            out.append((s, node))
        buf.clear()

    def walk(n, blk):
        for c in n.children:
            if isinstance(c, str):
                buf.append(c)
            elif c.tag in SKIP_TEXT or c.tag == "head":
                continue
            elif c.tag in BLOCK:
                flush(blk)
                walk(c, c)
                flush(c)
            elif c.tag in ("td", "th"):
                buf.append(" | ")
                walk(c, blk)
                buf.append(" ")
            elif c.tag == "br":
                buf.append(" ")
            elif c.tag in TIGHT_INLINE:
                walk(c, blk)
            else:  # span, a, b, small…: often display:block in CSS, so keep words apart
                buf.append(" ")
                walk(c, blk)
                buf.append(" ")
    body = root.first("body") or root
    walk(body, body)
    return out


# ---------------------------------------------------------------- report ---------------------------------------------

class Report:
    def __init__(self):
        self.issues = []
        self.pages = {}
        self.notes = []

    def add(self, page, cat, sev, check, msg, el="", fix="", owner=None, **extra):
        if owner is None:
            owner = "system" if SYSTEM_RE.search(el or "") else "page"
        self.issues.append(dict(page=page, cat=cat, sev=sev, check=check, msg=msg, el=el, fix=fix, owner=owner, **extra))

    def page(self, name):
        return self.pages.setdefault(name, {"facts_found": defaultdict(list), "lighthouse": {}, "stats": {}})


# ---------------------------------------------------------------- site facts -----------------------------------------

def money(v):
    v = float(v)
    return f"${v:,.0f}" if v == int(v) else f"${v:,.2f}"


def parse_time(s):
    s = s.strip().lower()
    if s == "noon":
        return (12, 0)
    if s == "midnight":
        return (0, 0)
    m = re.match(r"(\d{1,2})(?::(\d{2}))?\s*([ap])\.?\s?m\.?", s)
    if not m:
        return None
    h, mi, ap = int(m.group(1)), int(m.group(2) or 0), m.group(3)
    if ap == "p" and h != 12:
        h += 12
    if ap == "a" and h == 12:
        h = 0
    return (h, mi)


def fmt_time(t):
    h, m = t
    ap = "AM" if h < 12 else "PM"
    h12 = h % 12 or 12
    return f"{h12}{':%02d' % m if m else ''} {ap}"


def family_of(key):
    return {"fruit": "family", "gift_from": "gift"}.get(key, key.split("_")[0])


def derived_values(site, skip):
    """Simple arithmetic on site.json prices (same plan family): sums, savings, per-person/per-day splits, multiples."""
    out = {}
    fam = defaultdict(list)
    for k, v in site["prices"].items():
        fam[family_of(k)].append((k, float(v["price"])))

    def put(val, formula):
        val = round(val, 2)
        if val > 0 and val not in skip:
            out.setdefault(val, [])
            if formula not in out[val]:
                out[val].append(formula)
    for k, v in site["prices"].items():
        pr = float(v["price"])
        for m in (2, 3, 4, 5, 6, 7, 12):
            put(pr * m, f"{m} × {k} ({money(pr)})")
        for d in (2, 3, 4, 5, 6, 12, 18, 36):
            put(pr / d, f"{k} ({money(pr)}) ÷ {d}")
            if "per" in v:
                put(float(v["per"]) / d, f"{k}.per (${v['per']}) ÷ {d}")
                put(float(v["per"]) * d, f"{d} × {k}.per (${v['per']})")
    for f, items in fam.items():
        n = len(items)
        combos = [(items[i],) for i in range(n)]
        combos += [(items[i], items[j]) for i in range(n) for j in range(i + 1, n)]
        combos += [(items[i], items[j], items[l]) for i in range(n) for j in range(i + 1, n) for l in range(j + 1, n)]
        for c in combos[n:]:
            tot = sum(x[1] for x in c)
            name = " + ".join(x[0] for x in c)
            put(tot, name)
            for d in (2, 3, 4, 6, 12, 18):
                put(tot / d, f"({name}) ÷ {d}")
            for k2, v2 in items:
                if tot - v2 > 0 and all(k2 != x[0] for x in c):
                    put(tot - v2, f"({name}) − {k2}")
        for k1, v1 in items:
            for k2, v2 in items:
                for m in (2, 3):
                    if k1 != k2 and m * v1 - v2 > 0:
                        put(m * v1 - v2, f"{m} × {k1} − {k2}")
    return out


def pick_formula(formulas, context):
    """Prefer the formula whose plan family is named in the surrounding text."""
    ctx = context.lower()
    words = {"zone": "zone", "lcdf": "low-carb", "paleo": "paleo", "family": "famil", "protein": "protein", "gift": "gift"}
    for fm in formulas:
        fams = {family_of(k) for k in re.findall(r"[a-z]+_[a-z]+|fruit", fm)}
        if fams and all(words.get(fa, fa) in ctx for fa in fams):
            return fm
    return formulas[0]


def membership_values(site):
    """Every number build.py's JOMB Membership renderers can print, computed by build.py's own plan_quote()."""
    mb = site.get("membership")
    if not mb:
        return {}
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("jomb_build_for_qa", ROOT / "build.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        pq = mod.plan_quote
    except Exception:  # noqa: BLE001 - build.py changed shape; fall back to no membership numbers
        return {}
    out = {}
    menus = list(mb.get("menus", {})) + ["family"]
    for hh in mb.get("households", []):
        for days in mb.get("days", []):
            for cov in mb.get("coverage", []):
                for menu in menus:
                    try:
                        q = pq(hh["key"], days, cov["key"], menu)
                    except Exception:  # noqa: BLE001 - combination not offered
                        continue
                    label = f"membership {hh['key']}/{days}d/{cov['key']}/{menu}"
                    for k in ("base", "price", "save", "per", "monthly"):
                        if isinstance(q.get(k), (int, float)):
                            out.setdefault(round(float(q[k]), 2), f"{label} {k}")
    for menu, meals in mb.get("menus", {}).items():
        for meal, v in meals.items():
            if isinstance(v, (int, float)):
                out.setdefault(round(float(v), 2), f"membership.menus.{menu}.{meal}")
    return out


class Facts:
    def __init__(self, site):
        self.site = site
        self.phone_digits = re.sub(r"\D", "", site["phone_tel"])[-10:]
        self.tel = site["phone_tel"]
        self.email = site["email"].lower()
        self.cutoff_day = site["cutoff_day"]
        self.cutoff_time = parse_time(site["cutoff_time"])
        self.delivery_day = site["delivery_day"]
        w = re.split(r"\s*[–—-]\s*", site["delivery_window"])
        self.window = (parse_time(w[0]), parse_time(w[1]))
        self.menu_day = site["menu_posted"].split()[0]
        self.store = site["store_url"]
        self.years = re.sub(r"\D", "", site["chef"]["years"])
        self.prices = {}
        for k, v in site["prices"].items():
            self.prices[k] = {round(float(v["price"]), 2)} | ({round(float(v["per"]), 2)} if "per" in v else set())
        self.allowed_prices = set().union(*self.prices.values())
        self.base = site["base_url"].rstrip("/")
        comp = site.get("compliance") or {}
        self.compliance_on = bool(comp.get("enabled"))
        self.compliance_line = norm(comp.get("line", ""))
        # Known amounts from BRAND_GUIDE.md that are not (yet) keys in site.json.
        self.extra_prices = {100.0: "protein-by-the-pound $100 minimum (BRAND_GUIDE §2)"}
        self.member = membership_values(site)          # value -> how build.py derived it (JOMB Membership)
        self.derived = derived_values(site, self.allowed_prices | set(self.member) | set(self.extra_prices))
        self.derived_all = derived_values(site, set())
        mb = site.get("membership") or {}
        self.member_status = mb.get("status")
        self.extra_delivery_days = {DAY_LOOKUP[d] for d in re.findall(DAY_ALT, mb.get("delivery_note", "")) if d in DAY_LOOKUP} - {self.delivery_day}


# ---------------------------------------------------------------- regexes --------------------------------------------

_DAY_NAMES = {"Monday": ["Monday", "Mon"], "Tuesday": ["Tuesday", "Tues", "Tue"], "Wednesday": ["Wednesday", "Wed"],
              "Thursday": ["Thursday", "Thurs", "Thu"], "Friday": ["Friday", "Fri"], "Saturday": ["Saturday", "Sat"],
              "Sunday": ["Sunday", "Sun"]}
DAY_LOOKUP = {}
for _full, _alts in _DAY_NAMES.items():
    for _a in _alts:
        DAY_LOOKUP[_a] = _full
        DAY_LOOKUP[_a.upper()] = _full
        DAY_LOOKUP[_a + "s"] = _full
DAY_ALT = "|".join(sorted(DAY_LOOKUP, key=len, reverse=True))
DAY = rf"(?P<day>\b(?:{DAY_ALT})\b)\.?"
TIME = r"(?P<time>\b\d{1,2}(?::\d{2})?\s*[AaPp]\.?\s?[Mm]\b\.?|\bnoon\b|\bmidnight\b)"
PAIR_DT = re.compile(DAY + r"(?:\s*[,·@–—-]\s*|\s+)(?:(?:night|evening|morning|afternoon)\s+)?(?:(?:at|by|before|until|till|between|from)\s+)?" + TIME)
PAIR_TD = re.compile(TIME + r"\s+(?:on\s+|every\s+|each\s+|this\s+)?" + DAY)
RANGE = re.compile(r"(?P<h1>\b\d{1,2})(?::(?P<m1>\d{2}))?\s*(?P<ap1>[AaPp]\.?\s?[Mm]\.?)?\s*(?:–|—|-|to|until|and)\s*"
                   r"(?P<h2>\d{1,2})(?::(?P<m2>\d{2}))?\s*(?P<ap2>[AaPp]\.?\s?[Mm]\b\.?)")
DEADLINE_TIME = re.compile(r"\b(?:order|orders|ordering|deadline|cutoff|cut-off)\b(?P<gap>[^.;|]{0,25}?)\b(?:by|before|until|is|at)\s+" + TIME, re.I)
DELIVERY_DAY = [re.compile(r"\bdeliver(?:s|ed|y|ies|ing)?\s+(?:(?:on|every|each|this|next)\s+)?" + DAY, re.I),
                re.compile(DAY + r"\s+deliver(?:y|ies)\b", re.I),
                re.compile(r"\barriv(?:e|es|ing)\s+(?:(?:on|every|each|this|next)\s+)?" + DAY, re.I)]
CUTOFF_DAY = [re.compile(r"\b(?:order|orders|ordering)\s+(?:by|before)\s+(?:(?:this|next)\s+)?" + DAY, re.I),
              re.compile(r"\b(?:deadline|cutoff|cut-off)\s*(?:is|:|–|—|-)?\s*(?:(?:every|each|on)\s+)?" + DAY, re.I),
              re.compile(r"\bclos(?:e|es|ed|ing)\s+(?:(?:on|every|each)\s+)?" + DAY, re.I)]
MENU_DAY = re.compile(r"\bmenus?\b(?P<gap>[^.;|]{0,40}?)\b(?:posts?|posted|drops?|goes up|goes live|published|released|"
                      r"comes out|is out|every|each)\s+(?:(?:every|each|on)\s+)?" + DAY, re.I)
PHONE10 = re.compile(r"(?<![\d$.])(?:\+?1[\s.\-]?)?\(?(\d{3})\)?[\s.\-]?(\d{3})[\s.\-]?(\d{4})(?!\d)")
PHONE7 = re.compile(r"(?<![\d$.)\-])(\d{3})[-.](\d{4})(?!\d)")
OLD_PHONES = ("7565662", "8302568")
EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
PRICE = re.compile(r"\$\s?(\d{1,3}(?:,\d{3})+|\d+)(?:\.(\d{1,2}))?(?!\d)")
NEGATION = re.compile(r"\b(?:not|no|never|nor|without|isn't|aren't|don't|doesn't|won't|can't|cannot)\b|n['’]t\b", re.I)
MED_CTX = re.compile(r"\b(?:disease|condition|diabet\w*|illness|symptom\w*|medical|blood|obesity|cancer|heart|"
                     r"inflammation|disorder|insulin|cholesterol|pressure|health problems?)\b", re.I)
STREET = re.compile(r"\b\d{2,6}\s+(?:[NSEW]\.?\s+)?(?:[A-Z][\w'’]+\s+){1,3}(?:St|Street|Rd|Road|Ave|Avenue|Blvd|Boulevard|"
                    r"Dr|Drive|Ln|Lane|Way|Ct|Court|Pkwy|Parkway|Hwy|Highway|Pl|Place|Cir|Circle|Trl|Trail|Ter|"
                    r"Terrace|Sq|Square|Loop|Run|Pike)\b\.?(?:,?\s*(?:Suite|Ste\.?|Unit|#)\s*\w+)?")
RESULTS = re.compile(r"\b(?:lost|lose|losing|dropped|drop|shed)\s+(?:about\s+|over\s+|nearly\s+|almost\s+|≈\s*|~\s*)?\d+\s*"
                     r"(?:lb|lbs|pounds)\b|≈\s*\d+\s*(?:lb|lbs)\b", re.I)

# (pattern, label, severity, kind) kind: plain | neg (skip when the sentence is negated) | med (needs medical context)
BANNED = [
    (r"\bcur(?:e|es|ed|ing)\b", "medical claim 'cure'", FAIL, "neg"),
    (r"\brevers(?:e|es|ed|ing)\b(?![- ]?sear)", "medical claim 'reverse'", FAIL, "neg"),
    (r"\bdiabet(?:es|ic|ics)\b", "medical claim 'diabetes'", FAIL, "plain"),
    (r"\bheal(?:s|ed|ing)?\b", "medical claim 'heal'", FAIL, "neg"),
    (r"\btreat(?:s|ed|ing|ment|ments)?\b", "medical claim 'treat'", FAIL, "med"),
    (r"\bprevent(?:s|ed|ing|ion)?\b", "medical claim 'prevent'", FAIL, "med"),
    (r"\b(?:disease|illness|cancer|cholesterol|blood (?:sugar|pressure)|insulin|inflammation|obesity|hypertension)\b",
     "health condition named", WARN, "neg"),
    (r"\bGLP-?1\b|\bozempic\b|\bwegovy\b|\bmounjaro\b|\bzepbound\b|\bsemaglutide\b|\btirzepatide\b",
     "drug reference (only 'high-protein, portion-right meals' is allowed)", WARN, "plain"),
    (r"\bguarantee[sd]?\b", "guarantee (brand guide: never invent guarantees)", FAIL, "neg"),
    (r"\bbest\s+(?:[\w-]+\s+){0,3}in\s+(?:raleigh|the triangle|nc|north carolina|town|the area|the state|the country|america)\b",
     "superlative 'best in …'", FAIL, "plain"),
    (r"\b(?:raleigh|triangle|nc|north carolina)['’]s\s+(?:best|#\s?1|number one|top)\b", "superlative '…'s best'", FAIL, "plain"),
    (r"(?<![\w&])#\s?1\b|\bnumber one\b|\bno\.\s?1\b", "'#1' claim", FAIL, "plain"),
    (r"\baward[- ]winning\b|\bvoted best\b|\bbest[- ]rated\b|\btop[- ]rated\b", "unverifiable award/rating claim", FAIL, "plain"),
    (r"\belevat(?:e|es|ed|ing)\b", "AI filler 'elevate'", FAIL, "plain"),
    (r"\bunlock(?:s|ed|ing)?\b", "AI filler 'unlock'", FAIL, "plain"),
    (r"\bdelv(?:e|es|ed|ing)\b", "AI filler 'delve'", FAIL, "plain"),
    (r"\bculinary journey\b", "AI filler 'culinary journey'", FAIL, "plain"),
    (r"\btantaliz\w*", "AI filler 'tantalize'", FAIL, "plain"),
    (r"\bmouth[- ]?watering symphony\b", "AI filler 'mouthwatering symphony'", FAIL, "plain"),
    (r"\blook no further\b", "AI filler 'look no further'", FAIL, "plain"),
    (r"\bsymphony\b|\bembark\w*|\bnestled\b|\bgame[- ]chang\w+|\bseamless\w*|\bfast-paced world\b|\btapestry\b|"
     r"\btestament to\b|\brealm\b|\bunparalleled\b|\bsecond to none\b|\bworld[- ]class\b|\bmouth[- ]?watering\b|"
     r"\bfoodie heaven\b|\bculinary (?:experience|adventure|masterpiece)\b|\bexquisite\b|\bdelectable\b",
     "generic AI phrasing", WARN, "plain"),
    (r"\bhurry\b|\bact now\b|\blimited[- ]time (?:offer|only|deal)\b|\bfor a limited time\b|\bdon['’]t miss out\b|\bonly \d+ (?:spots|slots|left)\b|\bselling fast\b",
     "fake urgency", WARN, "plain"),
]
BANNED = [(re.compile(p, re.I), lab, sev, kind) for p, lab, sev, kind in BANNED]

# Regulatory trust claims may only come from site.json "compliance" (footer .footer-trust / {{trust}}).
TRUST = re.compile(r"\bServ[- ]?Safe\b(?:[- ](?:certified|manager|certification))?|\blicensed\b(?!\s+(?:dietitian|nutritionist|"
                   r"physician|doctor|professional|attorney|provider|therapist|trainer|health))|\b(?:health[- ])?inspected\b|"
                   r"\bpermitted (?:kitchen|facility|commissary)\b|\bpermit\s*(?:#|no\.?|number)\s*[:\-]?\s*[A-Z0-9][\w-]{2,}|"
                   r"\bhealth[- ]department\b|\bhealth[- ]inspect\w*|\bcertified (?:kitchen|commissary|facility|food (?:handler|manager|safety))\b|"
                   r"\bfood[- ]safety certif\w*|\binsured\b|\bbonded\b", re.I)
HEDGE = re.compile(r"\bpending (?:permit|approval|inspection|licens\w*|certification)\b|\bpermit pending\b|\blicense pending\b|"
                   r"\bnot (?:yet )?(?:licensed|permitted|inspected|certified)\b|\bunlicensed\b|\buninspected\b|"
                   r"\bawaiting (?:inspection|permit|approval|licens\w*|certification)\b|\bin the process of (?:getting|obtaining|securing)\b|"
                   r"\bapplied for (?:a |the |our )?(?:permit|license|licence)\b|\bonce (?:we are|we're|our kitchen is) (?:licensed|permitted|inspected)\b|"
                   r"\bcottage (?:food|kitchen)\b|\bhome kitchen\b", re.I)

FIXES = {
    "title-length": "Shorten \"title\" in the page's <!--meta--> header to ≤ 60 characters (Google truncates around 580 px).",
    "desc-length": "Rewrite \"description\" in the <!--meta--> header to 140–155 characters with one fact (price/day) and a place.",
    "h1-count": "Keep exactly one <h1> (the hero headline); turn the others into <h2>.",
    "heading-skip": "Use the next heading level down (h2 under h1, h3 under h2) or restyle with a class instead of skipping a level.",
    "img-alt": "Use {{img:slug|sizes||lazy|alt text}} or add alt text to src/img/manifest.json (decorative images: alt=\"\" + aria-hidden).",
    "img-size": "Add width and height attributes (the {{img}} placeholder adds them automatically) to prevent layout shift.",
    "root-link": "Use {{link:path/}} or a relative URL; links starting with '/' break under the /justonemorebite/ sub-path.",
    "broken-link": "Point the link at a page/asset that exists (check spelling and the trailing slash) or build the missing page.",
    "placeholder": "Fix the {{placeholder}} name (see COMPONENTS.md); build.py leaves unknown ones in the output.",
    "few-links": "Add descriptive {{link:…}} links in the body copy to at least 3 related pages (COMPONENTS rule 6).",
}


# ---------------------------------------------------------------- static checks -------------------------------------

class PageDoc:
    def __init__(self, name, file, rel, docs):
        self.name, self.file, self.rel, self.docs = name, file, rel, docs
        self.raw = file.read_text(errors="replace")
        self.dom = parse_html(self.raw)
        self.head = self.dom.first("head") or self.dom
        self.main = self.dom.first("main")
        self.segs = segments(self.dom)

    def meta(self, name=None, prop=None):
        for m in self.head.find_all("meta"):
            if (name and m.get("name") == name) or (prop and m.get("property") == prop):
                return m.get("content")
        return None

    def ld_blocks(self):
        return [s for s in self.dom.find_all("script") if (s.get("type") or "").lower() == "application/ld+json"]


def discover(docs):
    pages = {}
    for f in sorted(docs.rglob("index.html")):
        rel = f.parent.relative_to(docs).as_posix()
        if rel.startswith("assets"):
            continue
        pages["home" if rel == "." else rel] = (f, "" if rel == "." else rel + "/")
    if (docs / "404.html").exists():
        pages["404"] = (docs / "404.html", "404.html")
    return pages


def resolve(page, href):
    """Return (kind, target_path_or_None, fragment). kind: external|mail|tel|anchor|rootabs|protorel|local|other."""
    h = href.strip()
    low = h.lower()
    if low.startswith(("http://", "https://")):
        return "external", None, None
    if low.startswith("mailto:"):
        return "mail", None, None
    if low.startswith(("tel:", "sms:")):
        return "tel", None, None
    if low.startswith(("data:", "javascript:", "blob:")):
        return "other", None, None
    if h.startswith("//"):
        return "protorel", None, None
    if h.startswith("/"):
        return "rootabs", None, None
    u = urlsplit(h)
    if not u.path:
        return "anchor", page.file, u.fragment
    target = (page.file.parent / unquote(u.path)).resolve()
    if u.path.endswith("/") or target.is_dir():
        target = target / "index.html"
    return "local", target, u.fragment


def page_name_for(target, docs):
    try:
        rel = target.resolve().relative_to(docs.resolve()).as_posix()
    except ValueError:
        return None
    if rel == "index.html":
        return "home"
    if rel == "404.html":
        return "404"
    if rel.endswith("/index.html"):
        return rel[: -len("/index.html")]
    return None


def check_seo(p, ctx, rep):
    n, add = p.name, rep.add
    st = rep.page(n)["stats"]
    html_el = p.dom.first("html")
    if not html_el or not html_el.get("lang"):
        add(n, "seo", FAIL, "lang", "<html> has no lang attribute", "html", "Add lang=\"en-US\" in build.py head().", owner="system")
    if not p.head.first("meta") or not any(m.get("name") == "viewport" for m in p.head.find_all("meta")):
        add(n, "seo", FAIL, "viewport", "no <meta name=viewport>", "head", "Add the responsive viewport meta tag.", owner="system")
    # title
    t_el = p.head.first("title")
    title = t_el.text() if t_el else ""
    st["title"], st["title_len"] = title, len(title)
    if not title:
        add(n, "seo", FAIL, "title", "missing <title>", "head > title", FIXES["title-length"])
    elif len(title) > 60:
        add(n, "seo", FAIL, "title-length", f"title is {len(title)} chars (max 60): \"{title}\"", "head > title", FIXES["title-length"], owner="page")
    # description
    desc = norm(p.meta(name="description") or "")
    st["description_len"] = len(desc)
    if not desc:
        add(n, "seo", FAIL, "description", "missing meta description", "meta[name=description]", FIXES["desc-length"], owner="page")
    elif not 120 <= len(desc) <= 160:
        add(n, "seo", FAIL, "desc-length", f"meta description is {len(desc)} chars (need 120–160)", "meta[name=description]", FIXES["desc-length"], owner="page")
    elif not 140 <= len(desc) <= 155:
        add(n, "seo", INFO, "desc-length", f"meta description is {len(desc)} chars (house rule 140–155)", "meta[name=description]", FIXES["desc-length"], owner="page")
    # headings
    h1s = p.dom.find_all("h1")
    st["h1"] = [h.text() for h in h1s]
    if len(h1s) != 1:
        add(n, "seo", FAIL, "h1-count", f"{len(h1s)} <h1> elements (need exactly 1)", ", ".join(css_path(h) for h in h1s) or "main", FIXES["h1-count"], owner="page")
    prev = 0
    for h in p.dom.find_all(*HEADINGS):
        lvl = int(h.tag[1])
        if prev == 0 and lvl != 1 and h1s:
            add(n, "seo", WARN, "heading-skip", f"first heading is <{h.tag}> \"{h.text()[:50]}\" (before the <h1>)", css_path(h), FIXES["heading-skip"])
        elif prev and lvl > prev + 1:
            add(n, "seo", WARN, "heading-skip", f"h{prev} → h{lvl} skips a level: \"{h.text()[:60]}\"", css_path(h), FIXES["heading-skip"])
        prev = lvl
    # canonical / robots / og
    canon = next((l.get("href") for l in p.head.find_all("link") if "canonical" in (l.get("rel") or "").split()), None)
    expected = f"{ctx.facts.base}/{p.rel}" if p.name not in ("404",) else None
    if p.name == "home":
        expected = f"{ctx.facts.base}/"
    st["canonical"] = canon
    if p.name == "404":
        if canon:
            add(n, "seo", WARN, "canonical-404", f"404 page declares a canonical ({canon})", "link[rel=canonical]",
                "Skip the canonical (and og:url) when meta.special == '404' in build.py head(); a 404 should not canonicalize to a real URL.", owner="system")
    elif not canon:
        add(n, "seo", FAIL, "canonical", "missing <link rel=canonical>", "head", "build.py head() writes it; check the page meta \"path\".", owner="system")
    elif not canon.startswith("http"):
        add(n, "seo", FAIL, "canonical", f"canonical is not absolute: {canon}", "link[rel=canonical]", "Use an absolute URL.", owner="system")
    elif expected and canon != expected:
        add(n, "seo", FAIL, "canonical", f"canonical {canon} ≠ expected {expected}", "link[rel=canonical]", "Set the meta \"path\" to the folder name.", owner="page")
    robots = (p.meta(name="robots") or "").lower()
    st["robots"] = robots
    if ctx.site.get("preview") and "noindex" not in robots:
        add(n, "seo", FAIL, "robots", "preview build without noindex", "meta[name=robots]", "build.py head() must add noindex while preview is true.", owner="system")
    if not ctx.site.get("preview") and "noindex" in robots and p.name != "404":
        add(n, "seo", FAIL, "robots", "production build still has noindex", "meta[name=robots]", "Set \"preview\": false and rebuild.", owner="system")
    for prop in ("og:title", "og:description", "og:image", "og:url"):
        if not p.meta(prop=prop) and p.name != "404":
            add(n, "seo", WARN, "open-graph", f"missing {prop}", f"meta[property={prop}]", "build.py head() writes Open Graph tags.", owner="system")
    og = p.meta(prop="og:image") or ""
    if og.startswith(ctx.facts.base + "/"):
        local = p.docs / og[len(ctx.facts.base) + 1:]
        if not local.exists():
            add(n, "seo", FAIL, "og-image", f"og:image file missing: {og[len(ctx.facts.base) + 1:]}", "meta[property=og:image]",
                "Use an existing share card (og-home og-zone og-paleo og-lcdf og-family og-chef og-private og-catering og-default) or run tools/images.py.", owner="page")
    if p.meta(prop="og:url") and canon and p.meta(prop="og:url") != canon and p.name != "404":
        add(n, "seo", WARN, "open-graph", "og:url differs from canonical", "meta[property=og:url]", "Make og:url equal the canonical.", owner="system")
    # main landmark + skip link
    mains = p.dom.find_all("main")
    if len(mains) != 1:
        add(n, "seo", FAIL, "main", f"{len(mains)} <main> elements", "main", "Exactly one <main id=main> (build.py header()).", owner="system")
    # images
    eager = []
    for img in p.dom.find_all("img"):
        sel = css_path(img)
        src = img.get("src", "")
        decorative = img.get("aria-hidden") == "true" or img.get("role") in ("presentation", "none") or img.inside(lambda a: a.get("aria-hidden") == "true")
        if "alt" not in img.attrs:
            add(n, "seo", FAIL, "img-alt", f"<img> without alt: {src}", sel, FIXES["img-alt"])
        elif not img.get("alt").strip() and not decorative:
            add(n, "seo", WARN, "img-alt", f"<img> with empty alt (not marked decorative): {src}", sel, FIXES["img-alt"])
        if not img.get("width") or not img.get("height"):
            add(n, "seo", FAIL, "img-size", f"<img> without width/height: {src}", sel, FIXES["img-size"])
        if img.get("fetchpriority") == "high" or img.get("loading") == "eager" or (img.get("loading") is None and img.get("fetchpriority") is None):
            eager.append(sel)
    if len(eager) > 1:
        add(n, "seo", WARN, "img-eager", f"{len(eager)} images load eagerly (only the hero should): {', '.join(eager[:4])}", eager[1],
            "Drop 'eager' from all but the main hero {{img}}; others get loading=lazy.", owner="page")
    # links
    internal_targets = set()
    ids = {x.get("id") for x in p.dom.iter() if x.get("id")} | {x.get("name") for x in p.dom.find_all("a") if x.get("name")}
    for el in p.dom.iter():
        if el.tag in ("script", "style"):
            continue
        urls = []
        for attr in ("href", "src", "poster", "action"):
            if el.get(attr) is not None and not (el.tag == "link" and "canonical" in (el.get("rel") or "")):
                urls.append((attr, el.get(attr)))
        for attr in ("srcset", "imagesrcset"):
            if el.get(attr):
                urls += [(attr, part.strip().split(" ")[0]) for part in el.get(attr).split(",") if part.strip()]
        for attr, u in urls:
            if el.tag == "meta":
                continue
            kind, target, frag = resolve(p, u)
            sel = css_path(el)
            if kind == "rootabs" and el.tag == "base" and p.name == "404" and u == (urlsplit(ctx.facts.base).path.rstrip("/") + "/"):
                continue  # the 404 page's <base> is how it survives being served at nested URLs
            if kind == "rootabs":
                add(n, "seo", FAIL, "root-link", f"{attr}=\"{u}\" starts with '/' (breaks under {PREFIX})", sel, FIXES["root-link"])
            elif kind == "protorel":
                add(n, "seo", WARN, "protocol-relative", f"{attr}=\"{u}\" is protocol-relative", sel, "Use an explicit https:// URL.")
            elif kind == "anchor":
                if frag and frag not in ids:
                    add(n, "seo", FAIL, "anchor", f"#{frag} has no matching id on the page", sel, "Add the id or fix the fragment.")
            elif kind == "external" and u.lower().startswith("http://"):
                add(n, "seo", WARN, "insecure-link", f"insecure http:// link {u}", sel, "Use https://.")
            elif kind == "local":
                try:
                    target.relative_to(p.docs.resolve())
                except ValueError:
                    add(n, "seo", FAIL, "broken-link", f"{attr}=\"{u}\" points outside the site root", sel, FIXES["root-link"])
                    continue
                if not target.exists():
                    tname = page_name_for(target, p.docs)
                    if tname in PLANNED and ctx.allow_pending:
                        add(n, "seo", INFO, "pending-link", f"links to {tname}/ which is not built yet", sel, "Will resolve when that page is built.", owner="page")
                    else:
                        add(n, "seo", FAIL, "broken-link", f"{attr}=\"{u}\" → {target.relative_to(p.docs.resolve()) if target.is_relative_to(p.docs.resolve()) else target} not found", sel, FIXES["broken-link"])
                elif frag and target.suffix == ".html":
                    tname = page_name_for(target, p.docs)
                    other = ctx.pages.get(tname)
                    if other and frag not in {x.get("id") for x in other.dom.iter() if x.get("id")}:
                        add(n, "seo", WARN, "anchor", f"{u}: no id=\"{frag}\" on {tname}", sel, "Add the id on the target page or drop the fragment.")
                if attr == "href" and el.tag == "a" and el.inside(lambda a: a.tag == "main"):
                    tname = page_name_for(target, p.docs)
                    if tname and tname != p.name:
                        internal_targets.add(tname)
            if el.tag == "a" and el.get("target") == "_blank" and "noopener" not in (el.get("rel") or "") and kind == "external":
                add(n, "seo", WARN, "noopener", f"target=_blank without rel=noopener: {u}", sel, "Add rel=\"noopener\".")
    st["internal_links_in_main"] = sorted(internal_targets)
    if p.name != "404" and len(internal_targets) < 3:
        add(n, "seo", FAIL, "few-links", f"only {len(internal_targets)} internal page link(s) in <main> ({', '.join(sorted(internal_targets)) or 'none'}); need ≥ 3",
            "main", FIXES["few-links"], owner="page")
    # leftover placeholders
    for m in re.finditer(r"\{\{[^}]*\}?\}?", p.raw):
        line = p.raw.count("\n", 0, m.start()) + 1
        add(n, "seo", FAIL, "placeholder", f"unreplaced placeholder {m.group(0)[:40]} (line {line})", f"line {line}", FIXES["placeholder"])
    # sitemap / llms.txt
    if p.name != "404":
        if ctx.sitemap is not None and (canon or expected) not in ctx.sitemap:
            add(n, "seo", FAIL, "sitemap", "page missing from sitemap.xml", "sitemap.xml", "build.py write_extras() lists every non-404 page.", owner="system")
        if ctx.llms is not None and (canon or "") not in ctx.llms:
            add(n, "seo", WARN, "llms", "page missing from llms.txt", "llms.txt", "build.py llms_txt() lists every page.", owner="system")


def walk_ld(obj, out, parent=None, key=None, path="$"):
    if isinstance(obj, dict):
        out.append((obj, parent, key, path))
        for k, v in obj.items():
            walk_ld(v, out, obj, k, f"{path}.{k}")
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            walk_ld(v, out, parent, key, f"{path}[{i}]")


def types_of(o):
    t = o.get("@type", [])
    return t if isinstance(t, list) else [t]


def check_schema(p, ctx, rep):
    n, add, f = p.name, rep.add, ctx.facts
    blocks = p.ld_blocks()
    if not blocks and p.name == "404":
        return
    if not blocks:
        add(n, "schema", FAIL, "jsonld", "no application/ld+json block", "head", "build.py head() writes the @graph.", owner="system")
        return
    nodes = []
    for b in blocks:
        txt = b.raw_text()
        try:
            data = json.loads(txt)
        except json.JSONDecodeError as e:
            add(n, "schema", FAIL, "jsonld-parse", f"JSON-LD does not parse: {e}", css_path(b), "Fix the JSON (build.py uses json.dumps; a page-level block is hand-written).")
            continue
        walk_ld(data, nodes)
    typed = [(o, par, k, path) for o, par, k, path in nodes if "@type" in o]
    p.ld_nodes = nodes
    canon = next((l.get("href") for l in p.head.find_all("link") if "canonical" in (l.get("rel") or "").split()), None)
    defined = {o["@id"] for o, *_ in nodes if "@id" in o and len(o) > 1}
    for o, par, k, path in nodes:
        if set(o) == {"@id"} and o["@id"] not in defined:
            add(n, "schema", WARN, "id-ref", f"{path} references {o['@id']} which is not defined on this page", "JSON-LD", "Define the node in the same @graph or drop the reference.", owner="system")
    catalog_noprice = []
    tcount = Counter(t for o, *_ in typed for t in types_of(o))
    rep.page(n)["stats"]["schema_types"] = dict(tcount)
    for o, par, k, path in typed:
        ts = types_of(o)
        where = f"JSON-LD {'/'.join(ts)}"
        if set(ts) & {"FoodEstablishment", "LocalBusiness", "Restaurant"}:
            for prop in ("name", "telephone", "address", "areaServed"):
                if not o.get(prop):
                    add(n, "schema", FAIL, "required", f"{'/'.join(ts)} missing {prop}", "JSON-LD site graph", "Add it in build.py site_graph().", owner="system")
            a = o.get("address") or {}
            if isinstance(a, dict) and not (a.get("addressLocality") and a.get("addressRegion")):
                add(n, "schema", FAIL, "required", "address needs addressLocality + addressRegion", "JSON-LD site graph", "Add both in build.py.", owner="system")
            if isinstance(a, dict) and a.get("streetAddress"):
                add(n, "facts", FAIL, "street-address", f"JSON-LD streetAddress \"{a['streetAddress']}\" (service-area business: no street address)", "JSON-LD site graph",
                    "Remove streetAddress; keep locality/region only (BRAND_GUIDE §2).", owner="system")
        nested_offer = par is not None and "Offer" in types_of(par) and k == "itemOffered"
        if "Service" in ts and not nested_offer:
            for prop in ("name", "provider"):
                if not o.get(prop):
                    add(n, "schema", FAIL, "required", f"Service missing {prop}", where, "Add it to the page meta \"service\" (build.py page_graph()).")
            if canon and o.get("url") and o["url"] != canon:
                add(n, "schema", WARN, "url", f"Service url {o['url']} ≠ canonical", where, "Service url should be the page URL.", owner="system")
        if "Offer" in ts:
            in_catalog = par is not None and "OfferCatalog" in types_of(par)
            missing = [x for x in ("price", "priceCurrency") if o.get(x) in (None, "")]
            if missing and in_catalog:
                catalog_noprice.append((o.get("itemOffered") or {}).get("name", "?"))
            elif missing:
                add(n, "schema", FAIL, "offer-price", f"Offer \"{o.get('name', '?')}\" missing {', '.join(missing)}", where, "Use offers keys from site.json prices in the page meta \"service\".", owner="system")
            if o.get("price") not in (None, ""):
                try:
                    v = round(float(o["price"]), 2)
                except ValueError:
                    add(n, "schema", FAIL, "offer-price", f"Offer price \"{o['price']}\" is not numeric", where, "Use a plain number like 253.00.", owner="system")
                    v = None
                if v is not None:
                    key = next((k2 for k2, pv in ctx.site["prices"].items() if pv.get("label") == o.get("name")), None)
                    ok = (v in f.prices[key]) if key else (v in f.allowed_prices)
                    rep.page(n)["facts_found"]["prices"].append(f"JSON-LD {o.get('name', 'Offer')}: {money(v)}")
                    if not ok:
                        add(n, "facts", FAIL, "price", f"JSON-LD Offer \"{o.get('name')}\" price {o['price']} not in site.json", where, "Offers must come from site.json prices keys.", owner="system")
                if o.get("priceCurrency") and o["priceCurrency"] != "USD":
                    add(n, "schema", FAIL, "offer-price", f"priceCurrency {o['priceCurrency']}", where, "Use USD.", owner="system")
        if "BreadcrumbList" in ts:
            items = o.get("itemListElement") or []
            if not items:
                add(n, "schema", FAIL, "breadcrumb", "BreadcrumbList has no items", where, "Add a \"breadcrumb\" list to the page meta.", owner="page")
            for i, it in enumerate(items):
                if it.get("position") != i + 1 or not it.get("name") or not it.get("item"):
                    add(n, "schema", FAIL, "breadcrumb", f"breadcrumb item {i + 1} needs position/name/item: {json.dumps(it)[:120]}", where, "build.py page_graph() writes these from meta \"breadcrumb\".", owner="system")
                url = it.get("item") or ""
                if url.startswith(f.base + "/"):
                    rel = url[len(f.base) + 1:]
                    tgt = (p.docs / rel / "index.html") if (rel == "" or rel.endswith("/")) else p.docs / rel
                    if not tgt.exists():
                        tname = page_name_for(tgt, p.docs)
                        sev = INFO if (tname in PLANNED and ctx.allow_pending) else FAIL
                        add(n, "schema", sev, "breadcrumb", f"breadcrumb \"{it.get('name')}\" → {rel or '/'} does not exist yet" if sev == INFO else f"breadcrumb \"{it.get('name')}\" → {rel or '/'} does not exist",
                            where, "Breadcrumb paths in the meta must be real page folders.", owner="page")
            if items and canon and items[-1].get("item") != canon and p.name != "404":
                add(n, "schema", FAIL, "breadcrumb", f"last breadcrumb item {items[-1].get('item')} ≠ canonical {canon}", where,
                    "The last meta \"breadcrumb\" entry must be this page's path.", owner="page")
            vis = p.dom.first("nav")
            vis = next((x for x in p.dom.find_all("nav") if "breadcrumbs" in x.classes()), None)
            ld_names = [norm(str(it.get("name", ""))) for it in items]
            if vis is not None:
                vis_names = [li.text() for li in vis.find_all("li")]
                if vis_names != ld_names:
                    add(n, "schema", FAIL, "breadcrumb", f"visible breadcrumb {vis_names} ≠ JSON-LD {ld_names}", "nav.breadcrumbs", "Use {{breadcrumbs}} (it renders from the same meta).", owner="page")
            elif len(items) > 1:
                add(n, "schema", WARN, "breadcrumb", "JSON-LD breadcrumb but no visible {{breadcrumbs}}", "main", "Put {{breadcrumbs}} at the top of the page hero.", owner="page")
        if "FAQPage" in ts:
            if not o.get("mainEntity") and any("FAQPage" in types_of(o2) and o2.get("mainEntity") for o2, *_ in typed):
                add(n, "schema", FAIL, "faq-double", "page_type FAQPage makes the WebPage node an empty FAQPage, and {{faq}} adds a second FAQPage: "
                    "2 FAQPage nodes, one without questions (Rich Results Test: 'Missing field mainEntity' / duplicate FAQPage)", "JSON-LD WebPage (build.py page_graph)",
                    "In build.py page_graph(): when meta page_type == 'FAQPage', put mainEntity on the page node and skip the separate #faq node "
                    "(or emit the page node as WebPage).", owner="system")
                continue
            check_faq(p, o, rep)
        if set(ts) & {"WebPage", "AboutPage", "FAQPage", "ContactPage", "CollectionPage", "ProfilePage", "ItemPage"} and o.get("url"):
            if canon and o["url"] != canon and p.name != "404":
                add(n, "schema", FAIL, "url", f"{'/'.join(ts)} url {o['url']} ≠ canonical {canon}", where, "build.py uses the meta path for both.", owner="system")
    if catalog_noprice:
        add(n, "schema", INFO, "offer-price", f"{len(catalog_noprice)} OfferCatalog entries have no price (fine for a catalog listing)", "JSON-LD site graph",
            "Optional: add a \"from\" price via priceSpecification.", owner="system")
    if tcount.get("FAQPage", 0) > 1 and not any(i["check"] == "faq-double" and i["page"] == n for i in rep.issues):
        add(n, "schema", WARN, "faq", f"{tcount['FAQPage']} FAQPage nodes (Google expects one)", "JSON-LD", "Merge into one {{faq:a,b}} call.", owner="page")
    details = [d for d in p.dom.find_all("details") if d.first("summary")]
    if details and not tcount.get("FAQPage"):
        add(n, "schema", WARN, "faq", f"{len(details)} visible <details> FAQ items but no FAQPage schema", css_path(details[0]),
            "Render FAQs with {{faq:group}} so FAQPage JSON-LD matches the visible text.", owner="page")
    # telephone consistency
    ld_tels = {str(o["telephone"]) for o, *_ in nodes if "telephone" in o}
    tel_links = {}
    for a in p.dom.find_all("a"):
        h = (a.get("href") or "").strip()
        if h.lower().startswith(("tel:", "sms:")):
            tel_links.setdefault(h.split(":", 1)[1], css_path(a))
    for t in ld_tels:
        if re.sub(r"\D", "", t)[-10:] != f.phone_digits or t != f.tel:
            add(n, "schema", FAIL, "telephone", f"JSON-LD telephone {t} ≠ site.json {f.tel}", "JSON-LD site graph", "Use SITE['phone_tel'].", owner="system")
    for t, sel in tel_links.items():
        if t != f.tel:
            add(n, "facts", FAIL, "phone", f"tel: link dials {t}, site.json says {f.tel}", sel, "Use {{tel}} / {{phone_link}}.")
    if ld_tels and tel_links and not (ld_tels & set(tel_links)):
        add(n, "schema", FAIL, "telephone", f"JSON-LD telephone {sorted(ld_tels)} not among tel: links {sorted(tel_links)}", "JSON-LD", "Both must come from site.json.", owner="system")


def check_faq(p, o, rep):
    n, add = p.name, rep.add
    visible = {}
    for d in p.dom.find_all("details"):
        s = d.first("summary")
        if not s:
            continue
        q = s.text()
        a = norm(" ".join((c.text() if isinstance(c, Node) else norm(c)) for c in d.children if c is not s))
        visible.setdefault(q, []).append((a, css_path(d)))
    for q, lst in visible.items():
        if len(lst) > 1 and len({a for a, _ in lst}) > 1:
            add(n, "schema", WARN, "faq-duplicate", f"the question \"{q[:70]}\" appears {len(lst)}× on this page with different answers", lst[1][1],
                "Make each question specific (e.g. \"Is there a minimum for family dinners?\" vs \"…for protein by the pound?\") in the FAQ JSON group.", owner="page")
    ents = o.get("mainEntity") or []
    if isinstance(ents, dict):
        ents = [ents]
    if not ents:
        add(n, "schema", FAIL, "faq", "FAQPage has no mainEntity", "JSON-LD FAQPage", "Use {{faq:group}}.", owner="system")
    seen = set()
    for e in ents:
        q_raw = str(e.get("name", ""))
        a_raw = str((e.get("acceptedAnswer") or {}).get("text", ""))
        q, a = norm(q_raw), norm(a_raw)
        if not q or not a:
            add(n, "schema", FAIL, "faq", f"FAQ question missing name/acceptedAnswer.text: {q[:60]}", "JSON-LD FAQPage", "Use {{faq:group}}.", owner="system")
            continue
        seen.add(q)
        if q not in visible:
            add(n, "schema", FAIL, "faq-match", f"FAQPage question not visible on the page: \"{q[:80]}\"", "JSON-LD FAQPage",
                "Only mark up questions shown in a visible <details>; use {{faq:group}}.", owner="page")
            continue
        cands = visible[q]
        if any(va == a for va, _ in cands):
            continue
        va, sel = cands[0]
        ent = re.search(r"&(?:amp|lt|gt|quot|#\d+|#x[0-9a-f]+|[a-z]+);", a_raw)
        if ent and any(norm(html.unescape(a_raw)) == v for v, _ in cands):
            add(n, "schema", WARN, "faq-entity", f"FAQ answer JSON-LD contains a raw HTML entity (\"{ent.group(0)}\") for \"{q[:60]}\"",
                "JSON-LD FAQPage (build.py page_graph strip())", "In build.py page_graph(), return html.unescape(re.sub(r'<[^>]+>', '', h)) so the schema text is plain text.", owner="system")
            continue
        i = next((k for k in range(min(len(a), len(va))) if a[k] != va[k]), min(len(a), len(va)))
        add(n, "schema", FAIL, "faq-match", f"FAQ answer differs from visible text for \"{q[:60]}\": schema …{a[max(0, i - 20):i + 40]}… vs page …{va[max(0, i - 20):i + 40]}…",
            sel, "Render the FAQ with {{faq:group}} only; don't hand-edit the visible answer.", owner="page")
    for q, lst in visible.items():
        sel = lst[0][1]
        if q not in seen and ents:
            add(n, "schema", WARN, "faq-match", f"visible FAQ \"{q[:60]}\" is not in the FAQPage schema", sel, "Add it through {{faq:group}} so the schema includes it.", owner="page")


def sentences(text):
    return [s for s in re.split(r"(?<=[.!?])\s+(?=[A-Z0-9\"“(])", text) if s]


def fact_texts(p):
    """All customer-visible strings: (text, where, node)."""
    out = [(t, css_path(nd), nd) for t, nd in p.segs]
    t_el = p.head.first("title")
    if t_el:
        out.append((t_el.text(), "head > title", t_el))
    for key, sel in (("description", "meta[name=description]"),):
        v = p.meta(name=key)
        if v:
            out.append((norm(v), sel, None))
    for prop in ("og:title", "og:description"):
        v = p.meta(prop=prop)
        if v:
            out.append((norm(v), f"meta[property={prop}]", None))
    for el in p.dom.iter():
        for attr in ("alt", "aria-label", "title"):
            if el.get(attr) and el.tag not in ("link",):
                out.append((norm(el.get(attr)), f"{css_path(el)}[{attr}]", el))
    return out


def ld_texts(p):
    out = []
    for o, par, k, path in getattr(p, "ld_nodes", []):
        for kk, v in o.items():
            if isinstance(v, str) and kk not in ("@id", "@type", "@context", "url", "item", "image", "logo", "target", "sameAs",
                                                   "primaryImageOfPage", "telephone", "email", "price", "priceCurrency"):
                out.append((norm(v), f"JSON-LD {'/'.join(types_of(o)) if '@type' in o else path}.{kk}"))
    return out


def in_quote(node):
    return node is not None and (node.tag == "blockquote" or node.inside(lambda a: a.tag == "blockquote" or "quote" in a.classes()))


def check_facts(p, ctx, rep):
    n, add, f = p.name, rep.add, ctx.facts
    found = rep.page(n)["facts_found"]
    texts = fact_texts(p)
    ld = ld_texts(p)
    seen = set()

    def once(key):
        if key in seen:
            return False
        seen.add(key)
        return True

    all_text = " ".join(t for t, *_ in texts)
    for text, where, node in texts:
        is_ld = False
        # phones
        spans = []
        for m in PHONE10.finditer(text):
            digits = "".join(m.groups())
            spans.append(m.span())
            found["phones"].append(m.group(0).strip())
            if digits != f.phone_digits and once(("phone", digits, where)):
                add(n, "facts", FAIL, "phone", f"phone {m.group(0).strip()} ≠ site.json {f.site['phone_display']}", where, "Use {{phone}} / {{phone_link}}.")
        for m in PHONE7.finditer(text):
            if any(a <= m.start() < b for a, b in spans):
                continue
            digits = "".join(m.groups())
            if digits in OLD_PHONES:
                add(n, "facts", FAIL, "phone", f"old phone fragment {m.group(0)}", where, "Use {{phone}}.")
        # emails
        for m in EMAIL.finditer(text):
            found["emails"].append(m.group(0))
            if m.group(0).lower() != f.email and once(("email", m.group(0), where)):
                add(n, "facts", FAIL, "email", f"email {m.group(0)} ≠ site.json {f.email}", where, "Use {{email}} / {{email_link}}.")
        # day + time pairs
        pair_spans = []
        for rx in (PAIR_DT, PAIR_TD):
            for m in rx.finditer(text):
                day = DAY_LOOKUP.get(m.group("day").rstrip("."), None)
                t = parse_time(m.group("time"))
                if not day or not t:
                    continue
                pair_spans.append(m.span())
                phrase = m.group(0)
                if (day, t) == (f.cutoff_day, f.cutoff_time):
                    found["deadlines"].append(phrase)
                elif (day, t) == (f.delivery_day, f.window[0]):
                    found["delivery"].append(phrase)
                elif day == f.delivery_day and t == f.window[1]:
                    found["delivery"].append(phrase)
                    add(n, "facts", WARN, "delivery", f"\"{phrase}\": use the full window ({f.delivery_day}, {f.site['delivery_window']})", where, "Use {{delivery}}.")
                else:
                    found["other_day_times"].append(phrase)
                    add(n, "facts", FAIL, "deadline", f"\"{phrase}\" disagrees with site.json (order by {f.cutoff_day} {fmt_time(f.cutoff_time)}; delivered {f.delivery_day} {f.site['delivery_window']})",
                        where, "Use {{cutoff}} / {{cutoff_short}} / {{delivery}} instead of typing days and times.")
        for m in DEADLINE_TIME.finditer(text):
            if any(a <= m.start("time") < b for a, b in pair_spans) or re.search(DAY, m.group("gap")):
                continue
            t = parse_time(m.group("time"))
            found["deadlines"].append(m.group(0))
            if t and t != f.cutoff_time:
                add(n, "facts", FAIL, "deadline", f"\"{m.group(0)}\" ≠ site.json cutoff {f.cutoff_day} {fmt_time(f.cutoff_time)}", where, "Use {{cutoff}}.")
        # time windows
        for m in RANGE.finditer(text):
            ap2 = m.group("ap2")
            ap1 = m.group("ap1")
            h1, h2 = int(m.group("h1")), int(m.group("h2"))
            if not ap1:
                ap1 = "am" if (h1 > h2 and ap2.lower().startswith("p")) else ap2
            t1 = parse_time(f"{h1}:{m.group('m1') or '00'} {ap1}")
            t2 = parse_time(f"{h2}:{m.group('m2') or '00'} {ap2}")
            ctxt = text[max(0, m.start() - 90): m.end() + 30].lower()
            found["windows"].append(m.group(0))
            if (t1, t2) != f.window:
                sev = FAIL if re.search(r"deliver|tuesday|window|drop", ctxt) else WARN
                add(n, "facts", sev, "delivery-window", f"time window \"{m.group(0)}\" ≠ site.json delivery window {f.site['delivery_window']}", where, "Use {{delivery_window}}.")
        # day-only facts
        for rx in DELIVERY_DAY:
            for m in rx.finditer(text):
                day = DAY_LOOKUP.get(m.group("day").rstrip("."))
                found["delivery"].append(m.group(0))
                if day and day != f.delivery_day:
                    sent = next((x for x in sentences(text) if m.group(0) in x), text)
                    if day in f.extra_delivery_days and re.search(r"membership|member|subscri|second delivery|[57][- ]day|plan", sent, re.I):
                        found["delivery"].append(f"{m.group(0)} (membership second delivery)")
                        continue
                    add(n, "facts", FAIL, "delivery-day", f"\"{m.group(0)}\" ≠ delivery day {f.delivery_day}", where, "Use {{delivery_day}}.")
        for rx in CUTOFF_DAY:
            for m in rx.finditer(text):
                day = DAY_LOOKUP.get(m.group("day").rstrip("."))
                found["deadlines"].append(m.group(0))
                if day and day != f.cutoff_day:
                    add(n, "facts", FAIL, "deadline", f"\"{m.group(0)}\" ≠ order deadline {f.cutoff_day}", where, "Use {{cutoff}}.")
        for m in MENU_DAY.finditer(text):
            if re.search(r"deliver|order|arriv", m.group("gap"), re.I):
                continue
            day = DAY_LOOKUP.get(m.group("day").rstrip("."))
            found["menu_posted"].append(m.group(0))
            if day and day != f.menu_day:
                add(n, "facts", FAIL, "menu-day", f"\"{m.group(0)}\" ≠ new menu day {f.menu_day}", where, "Use {{menu_posted}}.")
        # prices
        for m in PRICE.finditer(text):
            v = round(float(m.group(1).replace(",", "") + "." + (m.group(2) or "0")), 2)
            found["prices"].append(m.group(0))
            if v in f.allowed_prices:
                ctx_price_check(n, text, m, v, where, f, rep)
            elif v in f.member:
                found["membership_prices"].append(m.group(0))
            elif v in f.extra_prices:
                if once(("xprice", v)):
                    add(n, "facts", WARN, "price", f"{m.group(0)} ({f.extra_prices[v]}) is not a key in site.json", where,
                        "Add it to site.json (e.g. prices.protein_min) and use {{price:key}} so it can't drift.", owner="system")
            elif v in f.derived:
                if once(("dprice", v, where)):
                    add(n, "facts", WARN, "derived-price", f"{m.group(0)} = {pick_formula(f.derived[v], text)} from site.json, typed by hand (…{text[max(0, m.start() - 40):m.end() + 20]}…)", where,
                        "Correct today, but it won't update when site.json changes. Drop it, or ask the main agent for a {{calc}} placeholder.")
            elif v in f.extra_prices:
                if once(("xprice", v)):
                    add(n, "facts", WARN, "price", f"{m.group(0)} ({f.extra_prices[v]}) is not a key in site.json", where,
                        "Add it to site.json (e.g. prices.protein_min) and use {{price:key}} so it can't drift.", owner="system")
            else:
                add(n, "facts", FAIL, "price", f"price {m.group(0)} is not in site.json (context: …{text[max(0, m.start() - 40):m.end() + 20]}…)", where,
                    "Use {{price:key}} / {{per:key}} from site.json; never type prices.")
        # chef years
        for s in sentences(text):
            for m in re.finditer(r"\b(\d{1,2})\+?\s*(?:years|yrs)\b(?!\s+(?:young|old|ago))(?=[^.]{0,40}\b(?:kitchen|experience|cooking|restaurant|culinary|career|professional|industry|as a chef))", s, re.I):
                if True:
                    found["years"].append(m.group(0))
                    if m.group(1) == "17":
                        add(n, "facts", FAIL, "chef-years", f"\"{m.group(0)}\" (old bio); site.json says {f.site['chef']['years']}", where, "Use {{chef_years}}.")
                    elif m.group(1) != f.years and not in_quote(node):
                        add(n, "facts", WARN, "chef-years", f"\"{m.group(0)}\" near chef/kitchen wording; site.json years = {f.site['chef']['years']}", where,
                            "If this is Chef Mike's experience, use {{chef_years}}.")
    # claims: visible text + JSON-LD
    claim_texts = [(t, w, nd) for t, w, nd in texts] + [(t, w, None) for t, w in ld]
    check_claims(n, claim_texts, rep, ctx)
    if RESULTS.search(all_text) and not re.search(r"individual results vary", all_text, re.I):
        add(n, "facts", FAIL, "results-disclaimer", f"weight-loss result \"{RESULTS.search(all_text).group(0)}\" without \"Individual results vary.\"", "main",
            "Add a visible note: \"*Individual results vary.\" next to the result (BRAND_GUIDE §4).", owner="page")
    # tel / mailto hrefs + order buttons
    for a in p.dom.find_all("a"):
        h = (a.get("href") or "").strip()
        digits = re.sub(r"\D", "", h)
        if any(op in digits for op in OLD_PHONES):
            add(n, "facts", FAIL, "phone", f"link to an old phone number: {h}", css_path(a), "Use {{tel}}.")
        if h.lower().startswith("mailto:") and h[7:].split("?")[0].lower() != f.email:
            add(n, "facts", FAIL, "email", f"mailto {h} ≠ site.json {f.email}", css_path(a), "Use {{email_link}}.")
        label = a.text()
        if (re.match(r"(?i)^order\b(?!\s+(?:question|status|help|issue|change|problem))", label) and h != f.store
                and not h.lower().startswith(("mailto:", "tel:", "sms:"))):
            add(n, "facts", FAIL, "order-link", f"\"{label}\" button goes to {h}, not the JOMB Store", css_path(a), "Order buttons use {{store}}.")
        if "justonemorebitenc.com" in h and h.rstrip("/") != f.store.rstrip("/"):
            add(n, "facts", WARN, "old-site-link", f"links to an old-site page: {h}", css_path(a), "Link to the new page with {{link:…}} (only the Store stays on the old site).")
    if not ctx.facts.compliance_on and p.dom.first("p") is not None:
        for el in p.dom.iter():
            if "footer-trust" in el.classes():
                add(n, "facts", FAIL, "trust-claim", "footer trust line rendered while compliance.enabled is false", css_path(el), "build.py should render it only when enabled.", owner="system")


PLAN_WORDS = [("zone", r"\bzone\b"), ("lcdf", r"low[- ]carb(?:[ ,]+dairy[- ]free)?|dairy[- ]free|\blcdf\b"), ("paleo", r"\bpaleo\b"),
              ("family", r"\bfamil(?:y|ies)\b"), ("protein", r"protein by the pound|\bper (?:lb|pound)\b|/lb\b|cooked protein"),
              ("gift", r"\bgift[- ]?cards?\b")]
ITEM_WORDS = [("protein_chicken", r"\bchicken\b"), ("protein_beef", r"\bbeef\b"), ("protein_pork", r"\bpork\b"),
              ("protein_seafood", r"\bseafood\b"), ("family_soup", r"\bsoups?\b"), ("family_salad", r"\bsalads?\b"),
              ("fruit", r"\bfruit\b")]
MEAL_WORDS = r"\b(breakfast|lunch|dinner)(?:es|s)?\b"


def _keys_for(plan, f):
    return [k for k in f.prices if family_of(k) == plan]


def ctx_price_check(n, text, m, v, where, f, rep):
    """WARN when a price sits next to a plan name whose site.json prices don't include it (same sentence only)."""
    sent_start = max(text.rfind(". ", 0, m.start()), text.rfind("? ", 0, m.start()), text.rfind("! ", 0, m.start()), text.rfind(" | ", 0, m.start()))
    sent_start = 0 if sent_start < 0 else sent_start + 2
    nxt = [i for i in (text.find(". ", m.end()), text.find(" | ", m.end())) if i >= 0]
    sent_end = min(nxt) if nxt else len(text)
    before, after = text[sent_start: m.start()], text[m.end(): sent_end]
    after_near = after[:22]
    hits = []  # (distance, keys, word)
    for rx_list, is_item in ((ITEM_WORDS, True), (PLAN_WORDS, False)):
        for key, rx in rx_list:
            keys = [key] if is_item else _keys_for(key, f)
            mm = re.match(r"\s*\)?\s*(?:on|for|with|of)\s+(?:the\s+|a\s+|an\s+)?(?:" + rx + ")", after_near, re.I)
            if mm:
                hits.append((-1, keys, mm.group(0).strip(), key))  # "…$81 on Zone": wins
            for mm in re.finditer(rx, before[-70:], re.I):
                hits.append((len(before[-70:]) - mm.end(), keys, mm.group(0), key))
    if not hits:
        return
    hits.sort(key=lambda h: h[0])
    best = hits[0]
    if best[0] >= 0 and len({h[3] for h in hits if h[0] >= 0}) > 1:
        return  # several plans named before the price: ambiguous ("Zone, Paleo and Family menus from $12.25")
    keys, word = best[1], best[2]
    meal_after = re.match(r"\s*\)?\s*(?:for\s+(?:the\s+|a\s+)?|per\s+|a\s+|each\s+)?" + MEAL_WORDS, after[:24], re.I)
    meals_before = {x.lower() for x in re.findall(MEAL_WORDS, before[-40:], re.I)}
    meal = meal_after.group(1).lower() if meal_after else (next(iter(meals_before)) if len(meals_before) == 1 else None)
    if meal:
        keys = [k for k in keys if meal in k] or keys
    vals = set().union(*(f.prices[k] for k in keys)) if keys else set()
    fam = {family_of(k) for k in keys}
    if v in f.derived_all and any(family_of(k2) in fam for fm in f.derived_all[v] for k2 in re.findall(r"[a-z]+_[a-z]+|fruit", fm)):
        return  # e.g. "$20 less than two singles" = 2 × zone_all − zone_double
    if vals and v not in vals and v not in f.member:
        rep.add(n, "facts", WARN, "price-context", f"{m.group(0)} sits next to \"{word}{' … ' + meal if meal else ''}\" but site.json has "
                f"{', '.join(money(x) for x in sorted(vals))} for that (…{text[max(0, m.start() - 50):m.end() + 20]}…)", where,
                "Check the price belongs to this plan; use {{price:key}} / {{per:key}}.")


def check_claims(n, texts, rep, ctx):
    f = ctx.facts
    for text, where, node in texts:
        for s in sentences(text):
            qspans = [mm.span() for mm in re.finditer(r'[“"]([^”"]{3,})[”"]', s)]
            hedged = False
            for m in HEDGE.finditer(s):
                hedged = True
                rep.add(n, "facts", FAIL, "legal-hedge", f"legal caveat / hedging on a customer page: \"{m.group(0)}\" (…{s[:120]}…)", where,
                        "Remove it. Permit/licence status lives only in site.json \"compliance\" (off in preview); customer copy never discusses it.")
            for m in TRUST.finditer(s):
                if hedged:
                    break
                term = m.group(0)
                quoted = in_quote(node) or any(a <= m.start() < b for a, b in qspans)
                if quoted and re.match(r"(?i)serv[- ]?safe", term):
                    rep.add(n, "facts", INFO, "trust-claim", f"testimonial mentions \"{term}\" (allowed: quoted testimonial)", where, "", owner="page")
                    continue
                if f.compliance_on and f.compliance_line and (f.compliance_line.lower() in s.lower() or f.compliance_line.lower() in text.lower()):
                    continue
                if node is not None and ("footer-trust" in node.classes() or node.inside(lambda a: "footer-trust" in a.classes())) and f.compliance_on:
                    continue
                sev = WARN if quoted else FAIL
                rep.add(n, "facts", sev, "trust-claim", f"regulatory trust claim \"{term}\" hard-coded{' in a testimonial' if quoted else ''} (compliance switch is {'on' if f.compliance_on else 'off'}): …{s[:110]}…",
                        where, "Remove it from the copy. Trust lines render only from site.json \"compliance\" via {{trust}} / the footer .footer-trust line.",
                        owner="system" if where.startswith("JSON-LD") else None)
            for m in STREET.finditer(s):
                rep.add(n, "facts", FAIL, "street-address", f"street address \"{m.group(0)}\" (service-area business: no kitchen address in public assets)", where,
                        "Remove it; say \"Raleigh, NC\" / the delivery towns instead (BRAND_GUIDE §2).")
            for rx, label, sev, kind in BANNED:
                for m in rx.finditer(s):
                    quoted = in_quote(node) or any(a <= m.start() < b for a, b in qspans)
                    if kind == "neg" and NEGATION.search(s):
                        continue
                    if kind == "med" and (not MED_CTX.search(s) or NEGATION.search(s)):
                        continue
                    if label.startswith("superlative") or label.startswith("'#1'"):
                        pass
                    rep.add(n, "facts", WARN if (quoted and sev == FAIL) else sev, "banned-claim",
                            f"{label}: \"{m.group(0)}\"{' (inside a testimonial quote)' if quoted else ''} — …{s[:110]}…", where,
                            "Rewrite with a specific, true fact (BRAND_GUIDE §4: numbers beat adjectives; no medical claims).")


def check_global(ctx, rep):
    titles, descs, h1s = defaultdict(list), defaultdict(list), defaultdict(list)
    for name, p in ctx.pages.items():
        st = rep.page(name)["stats"]
        if st.get("title"):
            titles[st["title"]].append(name)
        d = norm(p.meta(name="description") or "")
        if d:
            descs[d].append(name)
        for h in st.get("h1", []):
            h1s[h].append(name)
    for t, names in titles.items():
        if len(names) > 1:
            for nm in names:
                if nm in ctx.selected:
                    rep.add(nm, "seo", FAIL, "title-unique", f"title also used by {', '.join(x for x in names if x != nm)}: \"{t}\"", "head > title", FIXES["title-length"], owner="page")
    for d, names in descs.items():
        if len(names) > 1:
            for nm in names:
                if nm in ctx.selected:
                    rep.add(nm, "seo", FAIL, "desc-unique", f"meta description also used by {', '.join(x for x in names if x != nm)}", "meta[name=description]", FIXES["desc-length"], owner="page")
    for h, names in h1s.items():
        if len(names) > 1:
            for nm in names:
                if nm in ctx.selected:
                    rep.add(nm, "seo", WARN, "h1-unique", f"H1 also used by {', '.join(x for x in names if x != nm)}", "h1", "Give every page its own keyword-led H1.", owner="page")
    missing = [x for x in PLANNED if x not in ctx.pages]
    if missing:
        rep.add("(site)", "site", INFO if ctx.allow_pending else FAIL, "planned-pages", f"{len(missing)} planned page(s) not built yet: {', '.join(missing)}", "docs/",
                "Build the remaining pages.", owner="page")
    # CSS url() references
    for css in ctx.docs.rglob("*.css"):
        txt = css.read_text(errors="replace")
        for m in re.finditer(r"url\(\s*['\"]?([^'\")]+)", txt):
            u = m.group(1)
            if u.startswith(("data:", "http", "#")):
                continue
            if u.startswith("/"):
                rep.add("(site)", "seo", FAIL, "root-link", f"{css.relative_to(ctx.docs)}: url({u}) starts with '/'", "site.css", FIXES["root-link"], owner="system")
            elif not (css.parent / u.split("?")[0].split("#")[0]).exists():
                rep.add("(site)", "seo", FAIL, "broken-link", f"{css.relative_to(ctx.docs)}: url({u}) not found", "site.css", FIXES["broken-link"], owner="system")


def source_pages():
    """src/pages/*.html -> {page name: (path, body text after the meta header, line offset)}."""
    out = {}
    for f in sorted((SRC / "pages").glob("*.html")):
        raw = f.read_text(errors="replace")
        m = re.match(r"\s*<!--meta\s*(\{.*?\})\s*-->", raw, re.S)
        if not m:
            continue
        try:
            meta = json.loads(m.group(1))
        except json.JSONDecodeError:
            continue
        name = "404" if meta.get("special") == "404" else (meta.get("path", "").strip("/") or "home")
        out[name] = (f, raw[m.end():], raw.count("\n", 0, m.end()))
    return out


def _blank(m):
    return re.sub(r"[^\n]", " ", m.group(0))


def check_sources(ctx, rep):
    """Facts typed into src/pages instead of placeholders: correct today, wrong the day site.json changes."""
    f = ctx.facts
    for name, (path, body, off) in source_pages().items():
        if name not in ctx.selected:
            continue
        rel = f"src/pages/{path.name}"
        no_ph = re.sub(r"\{\{.*?\}\}", _blank, body, flags=re.S)
        text = re.sub(r"<!--.*?-->", _blank, no_ph, flags=re.S)
        text = re.sub(r"<[^>]+>", _blank, text)
        text_n = html.unescape(text)

        def line(i):
            return off + body.count("\n", 0, i) + 1
        hits = defaultdict(list)
        for m in PRICE.finditer(text_n):
            v = round(float(m.group(1).replace(",", "") + "." + (m.group(2) or "0")), 2)
            if v in f.allowed_prices:
                key = next((k for k, vals in f.prices.items() if v in vals), "?")
                hits["prices"].append(f"{m.group(0)} (l.{line(m.start())}, = {key})")
            elif v in f.member:
                hits["prices"].append(f"{m.group(0)} (l.{line(m.start())}, = {f.member[v]})")
            elif v in f.extra_prices:
                hits["prices"].append(f"{m.group(0)} (l.{line(m.start())}, {f.extra_prices[v]}, no site.json key)")
            elif v in f.derived:
                hits["prices"].append(f"{m.group(0)} (l.{line(m.start())}, = {pick_formula(f.derived[v], text_n[max(0, m.start() - 160):m.end() + 40])})")
            else:
                hits["prices"].append(f"{m.group(0)} (l.{line(m.start())}, not from site.json)")
        for m in PHONE10.finditer(text_n):
            hits["phone"].append(f"{m.group(0).strip()} (l.{line(m.start())})")
        for m in EMAIL.finditer(no_ph):
            hits["email"].append(f"{m.group(0)} (l.{line(m.start())})")
        for m in re.finditer(re.escape(f.store), no_ph):
            hits["store URL"].append(f"l.{line(m.start())}")
        for rx in (PAIR_DT, PAIR_TD, RANGE, *DELIVERY_DAY, *CUTOFF_DAY, MENU_DAY):
            for m in rx.finditer(text_n):
                hits["day/time"].append(f"\"{norm(m.group(0))}\" (l.{line(m.start())})")
        fixes = {"prices": "{{price:key}} / {{per:key}} (or a membership placeholder)", "phone": "{{phone}} / {{phone_link}}",
                 "email": "{{email}} / {{email_link}}", "store URL": "{{store}}",
                 "day/time": "{{cutoff}} / {{cutoff_short}} / {{delivery_day}} / {{delivery_window}} / {{menu_posted}}"}
        for kind, items in hits.items():
            items = list(dict.fromkeys(items))
            rep.add(name, "facts", WARN, "hard-coded", f"{len(items)} hard-coded {kind} value(s) in {rel}: {'; '.join(items[:8])}{' …' if len(items) > 8 else ''}",
                    rel, f"Replace with {fixes[kind]} so the value follows site.json.", owner="page")


def check_site_json(ctx, rep):
    site, f = ctx.site, ctx.facts
    for k, v in site["prices"].items():
        meals = v.get("meals") or 0
        if "per" in v and meals > 1:
            exact = float(v["price"]) / meals
            if abs(round(exact, 2) - float(v["per"])) > 0.001:
                rep.add("(site)", "facts", WARN, "site-json", f"prices.{k}: {money(v['price'])} ÷ {meals} meals = ${exact:.4f}, which rounds to ${exact:.2f}, but per = ${v['per']}",
                        "src/site.json", "Confirm the per-meal figure with the JOMB Store (the store may show the truncated value), then make per match.", owner="system")
    mb = site.get("membership") or {}
    for menu, meals in (mb.get("menus") or {}).items():
        for meal, val in meals.items():
            if not isinstance(val, (int, float)):
                continue
            key = f"{menu}_{meal}"
            per = site["prices"].get(key, {}).get("per")
            if per is None:
                continue
            if abs(float(per) - float(val)) > 0.001:
                rep.add("(site)", "facts", FAIL, "site-json", f"membership.menus.{menu}.{meal} = {val} but prices.{key}.per = {per}", "src/site.json",
                        "Derive membership per-meal prices from prices.* in build.py instead of a second copy.", owner="system")
            else:
                rep.add("(site)", "facts", INFO, "site-json", f"membership.menus.{menu}.{meal} duplicates prices.{key}.per ({per}); it matches today",
                        "src/site.json", "Derive it from prices.* in build.py so the two can't drift.", owner="system")
    fd = mb.get("family_dinner")
    if fd is not None and abs(float(fd) - float(site["prices"]["family_meal"]["price"])) > 0.001:
        rep.add("(site)", "facts", FAIL, "site-json", f"membership.family_dinner = {fd} but prices.family_meal = {site['prices']['family_meal']['price']}", "src/site.json",
                "Use prices.family_meal in build.py.", owner="system")
    if mb and str(mb.get("status", "")).lower() in ("proposed", "draft"):
        shown = [nm for nm, pg in ctx.pages.items() if re.search(r"JOMB Membership|subscri(?:be|ber|ption)s? (?:and )?save|save (?:up to )?\d+%", pg.dom.text(), re.I)]
        labelled = [nm for nm in shown if re.search(r"\bproposed\b|\bdraft\b|\bcoming soon\b", ctx.pages[nm].dom.text(), re.I)]
        if shown:
            rep.add("(site)", "facts", WARN, "proposed-offer", f"membership status is \"{mb.get('status')}\" but {len(shown)} page(s) present it as a live offer "
                    f"(\"save 5–12%\", prices, sign-up){'' if not labelled else f'; only {len(labelled)} say proposed/draft'}: {', '.join(shown)}",
                    "src/site.json membership", "BRAND_GUIDE §2: proposed offers are never shown as live. Gate the membership blocks on a membership.enabled switch "
                    "(off in preview, like compliance), or label them \"Proposed\" until Mike approves.", owner="system")
        if f.extra_delivery_days:
            rep.add("(site)", "facts", INFO, "proposed-offer", f"membership adds a {'/'.join(sorted(f.extra_delivery_days))} second delivery ({mb.get('delivery_note')}); "
                    "that's a new operational promise beyond site.json's Tuesday delivery", "src/site.json membership",
                    "Confirm with Mike before it goes live.", owner="system")


# ---------------------------------------------------------------- local server --------------------------------------

mimetypes.add_type("application/manifest+json", ".webmanifest")
mimetypes.add_type("font/woff2", ".woff2")
mimetypes.add_type("image/webp", ".webp")
mimetypes.add_type("image/svg+xml", ".svg")
COMPRESSIBLE = ("text/", "application/javascript", "application/json", "application/manifest+json", "image/svg+xml", "application/xml")


def make_handler(root, prefix):
    class H(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, *a):
            pass

        def do_HEAD(self):
            self.serve(True)

        def do_GET(self):
            self.serve(False)

        def serve(self, head):
            path = unquote(urlsplit(self.path).path)
            if prefix != "/" and path == prefix.rstrip("/"):
                return self.redirect(prefix)
            if not path.startswith(prefix):
                return self.not_found(head)
            rel = path[len(prefix):]
            if ".." in Path(rel).parts:
                return self.not_found(head)
            f = root / rel
            if f.is_dir():
                if rel and not rel.endswith("/"):
                    return self.redirect(path + "/")
                f = f / "index.html"
            if not f.is_file():
                return self.not_found(head)
            self.send_file(200, f, head)

        def redirect(self, loc):
            self.send_response(301)
            self.send_header("Location", loc)
            self.send_header("Content-Length", "0")
            self.end_headers()

        def not_found(self, head):
            nf = root / "404.html"
            if nf.is_file():
                return self.send_file(404, nf, head)
            body = b"Not found"
            self.send_response(404)
            self.send_header("Content-Type", "text/plain")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            if not head:
                self.wfile.write(body)

        def send_file(self, code, f, head):
            data = f.read_bytes()
            ctype = mimetypes.guess_type(f.name)[0] or "application/octet-stream"
            if ctype.startswith("text/") or ctype in ("application/javascript", "application/json", "image/svg+xml"):
                ctype += "; charset=utf-8"
            gz = "gzip" in (self.headers.get("Accept-Encoding") or "") and ctype.startswith(COMPRESSIBLE)
            if gz:
                data = gzip.compress(data, 6)
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "max-age=600")  # what GitHub Pages sends
            self.send_header("Vary", "Accept-Encoding")
            if gz:
                self.send_header("Content-Encoding", "gzip")
            self.end_headers()
            if not head:
                try:
                    self.wfile.write(data)
                except (BrokenPipeError, ConnectionResetError):
                    pass
    return H


class SiteServer:
    def __init__(self, root, prefix=PREFIX):
        self.prefix = prefix
        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(Path(root), prefix))
        self.httpd.daemon_threads = True
        self.port = self.httpd.server_address[1]
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()

    def url(self, rel=""):
        return f"http://127.0.0.1:{self.port}{self.prefix}{rel}"

    def close(self):
        self.httpd.shutdown()
        self.httpd.server_close()


# ---------------------------------------------------------------- browser checks ------------------------------------

JS_SEL = r"""
const SEL = (el) => {
  const parts = [];
  for (let n = el, i = 0; n && n.nodeType === 1 && n !== document.body && n !== document.documentElement && i < 5; n = n.parentElement, i++) {
    let s = n.tagName.toLowerCase();
    if (n.id) { parts.unshift(s + '#' + n.id); break; }
    const cls = [...n.classList].filter(c => !['reveal','is-in','is-visible','is-scrolled','is-open'].includes(c)).slice(0, 2);
    if (cls.length) s += '.' + cls.join('.');
    else if (n.parentElement) { const sib = [...n.parentElement.children].filter(c => c.tagName === n.tagName); if (sib.length > 1) s += ':nth-of-type(' + (sib.indexOf(n) + 1) + ')'; }
    parts.unshift(s);
  }
  return parts.join(' > ');
};
"""

JS_PREP = """() => {
  document.querySelectorAll('.reveal').forEach(e => e.classList.add('is-in'));
  const s = document.createElement('style');
  s.textContent = '*,*::before,*::after{transition:none!important;animation:none!important;scroll-behavior:auto!important}';
  document.head.appendChild(s);
}"""

JS_SCROLL = """async () => {
  const H = () => Math.max(document.body.scrollHeight, document.documentElement.scrollHeight);
  const step = Math.max(500, innerHeight * 0.9);
  for (let y = 0; y < H(); y += step) { window.scrollTo(0, y); await new Promise(r => setTimeout(r, 35)); }
  window.scrollTo(0, H()); await new Promise(r => setTimeout(r, 80));
  window.scrollTo(0, 0); await new Promise(r => setTimeout(r, 40));
  window.dispatchEvent(new Event('scroll'));
}"""

JS_MEASURE = "(W) => {" + JS_SEL + r"""
  const de = document.documentElement, cw = de.clientWidth;
  const sw = Math.max(de.scrollWidth, document.body ? document.body.scrollWidth : 0);
  const out = {W, innerWidth, clientWidth: cw, scrollWidth: sw, offenders: [], clipped: [], broken: [], thirdParty: []};
  const clipAnc = (el, axisOnlyHidden) => {
    for (let a = el.parentElement; a && a !== document.body && a !== de; a = a.parentElement) {
      const cs = getComputedStyle(a);
      const ox = cs.overflowX, oy = cs.overflowY;
      if (axisOnlyHidden ? (ox === 'hidden' || ox === 'clip' || oy === 'hidden' || oy === 'clip') : (ox !== 'visible' || (cs.contain || '').includes('paint'))) return a;
    }
    return null;
  };
  const isOver = (r) => r.right > cw + 1;
  for (const el of document.body.querySelectorAll('*')) {
    if (el.closest('#nav-sheet, script, style, noscript, template, .sr-only, .skip-link')) continue;
    const r = el.getBoundingClientRect();
    if (r.width < 1 || r.height < 1) continue;
    const cs = getComputedStyle(el);
    if (cs.visibility === 'hidden' || cs.opacity === '0') continue;
    if (isOver(r)) {
      const clip = clipAnc(el, false);
      if (!(clip && clip.getBoundingClientRect().right <= cw + 1)) {
        const p = el.parentElement, pr = p.getBoundingClientRect();
        out.offenders.push({sel: SEL(el), right: Math.round(r.right), width: Math.round(r.width), over: Math.round(r.right - cw),
          breakout: p === document.body || pr.right <= cw + 1, text: ((el.innerText || el.getAttribute('alt') || '') + '').trim().replace(/\s+/g, ' ').slice(0, 60)});
      }
    }
    // own-text elements clipped by an overflow:hidden ancestor
    const ownText = [...el.childNodes].some(c => c.nodeType === 3 && c.textContent.trim().length > 1);
    if (ownText && !el.closest('[aria-hidden="true"], .marquee') && cs.textOverflow !== 'ellipsis') {
      const clip = clipAnc(el, true);
      if (clip) {
        const cr = clip.getBoundingClientRect();
        const dx = Math.max(0, r.right - cr.right, cr.left - r.left), dy = Math.max(0, r.bottom - cr.bottom, cr.top - r.top);
        if (dx > 2 || dy > 2) out.clipped.push({sel: SEL(el), by: SEL(clip), dx: Math.round(dx), dy: Math.round(dy), text: el.textContent.trim().replace(/\s+/g, ' ').slice(0, 60)});
      }
    }
  }
  out.broken = [...document.images].filter(i => i.complete && i.naturalWidth === 0 && (i.currentSrc || i.src)).map(i => ({sel: SEL(i), src: i.currentSrc || i.src}));
  out.thirdParty = [...new Set(performance.getEntriesByType('resource').map(e => e.name).filter(u => !u.startsWith(location.origin) && !u.startsWith('data:')).map(u => new URL(u).host))];
  return out;
}"""

JS_TAPS = "(groups) => {" + JS_SEL + r"""
  const vis = (el) => { const r = el.getBoundingClientRect(), cs = getComputedStyle(el); return r.width > 0 && r.height > 0 && cs.visibility !== 'hidden' && cs.display !== 'none' && r.right > 0 && r.left < innerWidth; };
  const all = [...document.querySelectorAll('a[href], button, [role=button], input, select, textarea, summary')].filter(vis);
  const rects = all.map(e => [e, e.getBoundingClientRect()]);
  const out = [];
  const seen = new Set();
  for (const [group, sel, min, spacing] of groups) {
    for (const el of document.querySelectorAll(sel)) {
      if (seen.has(el) || !vis(el)) continue;
      seen.add(el);
      const r = el.getBoundingClientRect();
      if (r.width >= min && r.height >= min) continue;
      const label = (el.innerText || el.textContent || el.getAttribute('aria-label') || '').trim().replace(/\s+/g, ' ').slice(0, 40);
      if (el.closest('details:not([open])') && el.tagName !== 'SUMMARY') continue;
      if (spacing) {
        // WCAG 2.5.8 exceptions: inline link inside a sentence, or a 24px circle that doesn't hit another target
        const p = el.parentElement, pt = (p && p.textContent || '').trim().replace(/\s+/g, ' ');
        if (getComputedStyle(el).display === 'inline' && pt.length > label.length + 15) continue;
        const cx = r.left + r.width / 2, cy = r.top + r.height / 2, h = min / 2;
        const hit = rects.some(([o, orr]) => o !== el && !o.contains(el) && !el.contains(o) && orr.left < cx + h && orr.right > cx - h && orr.top < cy + h && orr.bottom > cy - h);
        if (!hit) continue;
      }
      out.push({group, sel: SEL(el), w: Math.round(r.width), h: Math.round(r.height), min, label});
    }
  }
  return out;
}"""

TAP_GROUPS_MOBILE = [
    ["header", ".site-header a, .site-header button", 44, False],
    ["CTA button", "main a.btn, main button, .cta-band a.btn", 44, False],
    ["FAQ toggle", "main details > summary", 44, False],
    ["link", "main a, footer a, .breadcrumbs a", 24, True],
]

AXE_RUN = """async (ctx) => {
  const r = await axe.run(ctx || document, {resultTypes: ['violations'], runOnly: {type: 'tag', values: ['wcag2a','wcag2aa','wcag21a','wcag21aa','wcag22aa','best-practice']}});
  return r.violations.map(v => ({id: v.id, impact: v.impact, help: v.help, helpUrl: v.helpUrl,
    nodes: v.nodes.map(n => ({target: n.target.map(t => Array.isArray(t) ? t.join(' ') : t).join(' '), html: n.html.slice(0, 160), summary: (n.failureSummary || '').replace(/\\s+/g, ' ').slice(0, 300)}))}));
}"""


def browser_checks(ctx, rep, server, axe_path, widths):
    from playwright.sync_api import sync_playwright
    resp_issues = defaultdict(lambda: {"widths": set(), "detail": None})
    axe_seen = {}

    def note(page, cat, sev, check, key, msg, el, fix, w, owner=None):
        k = (page, cat, sev, check, key)
        d = resp_issues[k]
        d["widths"].add(w)
        if d["detail"] is None:
            d["detail"] = (msg, el, fix, owner)

    with sync_playwright() as pw:
        browser = pw.chromium.launch(channel="chrome", headless=True)
        for w in widths:
            mobile = w <= MOBILE_MAX
            bctx = browser.new_context(viewport={"width": w, "height": 844 if mobile else 900}, device_scale_factor=1,
                                       is_mobile=mobile, has_touch=mobile)
            targets = [(nm, ctx.pages[nm].rel) for nm in ctx.selected]
            if "404" in ctx.pages and "404" in ctx.selected:
                targets.append(("404@nested", "no-such-page/really/"))
            for name, rel in targets:
                pname = "404" if name == "404@nested" else name
                page = bctx.new_page()
                errs, failed = [], []
                page.on("console", lambda m, errs=errs: errs.append(m.text) if m.type == "error" else None)
                page.on("pageerror", lambda e, errs=errs: errs.append(str(e)))
                page.on("requestfailed", lambda r, failed=failed: failed.append((r.url, r.failure or "failed")))

                def on_resp(r, failed=failed, main_url=server.url(rel)):
                    if r.status >= 400 and r.url != main_url:
                        failed.append((r.url, r.status))
                page.on("response", on_resp)
                try:
                    resp = page.goto(server.url(rel), wait_until="load", timeout=30000)
                except Exception as e:  # noqa: BLE001
                    note(pname, "responsive", FAIL, "load", "load", f"page failed to load: {e}", "page", "Check the build output.", w)
                    page.close()
                    continue
                if name != "404@nested" and resp and resp.status != 200:
                    note(pname, "responsive", FAIL, "status", str(resp.status), f"HTTP {resp.status}", "page", "Page should return 200.", w)
                page.evaluate(JS_PREP)
                page.evaluate(JS_SCROLL)
                try:
                    page.wait_for_load_state("networkidle", timeout=6000)
                except Exception:  # noqa: BLE001
                    pass
                page.evaluate(JS_PREP)
                m = page.evaluate(JS_MEASURE, w)
                tag = " (404 served at a nested URL)" if name == "404@nested" else ""
                for e in errs:
                    if name == "404@nested" and "status of 404" in e and not failed:
                        continue  # the 404 document itself
                    note(pname, "responsive", FAIL, "console", e[:120], f"console error{tag}: {e[:200]}", "console", "Fix the script error (site.js or inline script).", w)
                for u, why in failed:
                    short = u.replace(server.url(""), "")
                    if name == "404@nested":
                        note(pname, "responsive", FAIL, "404-nested", "nested", f"404 page loses its assets when GitHub Pages serves it at a nested URL (e.g. /justonemorebite/no-such-page/really/): {short} → {why}",
                             "404.html <head>", "GitHub Pages serves 404.html at any missing path, so relative links break. In build.py, give the 404 page "
                             f"<base href=\"{PREFIX}\"> (preview) / the production root, or write its asset and nav URLs absolute.", w, owner="system")
                        break
                    note(pname, "responsive", FAIL, "failed-request", short, f"request failed: {short} → {why}", short, "Fix the path (sub-path safe, file exists).", w)
                if name == "404@nested":
                    page.close()
                    continue
                over = max(m["scrollWidth"], m["innerWidth"]) - m["clientWidth"]
                if m["scrollWidth"] > m["clientWidth"] + 1:
                    offs = [o for o in m["offenders"] if o["breakout"]] or sorted(m["offenders"], key=lambda o: -o["over"])[:3]
                    offs = sorted(offs, key=lambda o: -o["over"])
                    top = offs[0] if offs else {"sel": "?", "over": over, "width": 0, "text": ""}
                    others = "; ".join(f"{o['sel']} (+{o['over']}px)" for o in offs[1:4])
                    note(pname, "responsive", FAIL, "overflow", top["sel"],
                         f"horizontal overflow: page is {m['scrollWidth']}px wide in a {m['clientWidth']}px viewport; widest offender {top['sel']} "
                         f"({top['width']}px wide, +{top['over']}px{', “' + top['text'] + '”' if top['text'] else ''}){'; also ' + others if others else ''}",
                         top["sel"], "Constrain it: max-width:100%, min-width:0 on grid/flex children, overflow-wrap:anywhere for long strings, "
                         "or white-space:normal on nowrap buttons at small widths.", w)
                else:
                    offs = [o for o in m["offenders"] if o["breakout"]]
                    for o in offs[:3]:
                        note(pname, "responsive", WARN, "hidden-overflow", o["sel"], f"{o['sel']} sticks out {o['over']}px past the viewport (masked by body overflow-x:hidden; content is cut off)",
                             o["sel"], "Make it fit the viewport instead of relying on body overflow-x:hidden.", w)
                for c in m["clipped"][:6]:
                    note(pname, "responsive", WARN, "clipped-text", c["sel"], f"text clipped by {c['by']} (dx {c['dx']}px, dy {c['dy']}px): “{c['text']}”",
                         c["sel"], "Let the box grow (min-height instead of height, no fixed widths) or reflow at this width.", w)
                for b in m["broken"]:
                    note(pname, "responsive", FAIL, "broken-image", b["src"], f"image failed to load: {b['src']}", b["sel"], "Check the img slug/width exists in docs/img.", w)
                for host in m["thirdParty"]:
                    note(pname, "responsive", WARN, "third-party", host, f"third-party request to {host}", "page", "README promises no third-party requests; self-host or drop it.", w)
                # tap targets
                if w <= 768:
                    sev = FAIL if mobile else WARN
                    taps = page.evaluate(JS_TAPS, TAP_GROUPS_MOBILE)
                    page.evaluate("() => { window.scrollTo(0, Math.min(900, document.body.scrollHeight)); window.dispatchEvent(new Event('scroll')); }")
                    page.wait_for_timeout(120)
                    taps += page.evaluate(JS_TAPS, [["mobile bar", ".mobile-bar a, .mobile-bar button", 44, False]])
                    for t in taps:
                        s2 = sev if t["min"] >= 44 else WARN
                        note(pname, "responsive", s2, "tap-target", t["sel"], f"{t['group']} tap target “{t['label']}” is {t['w']}×{t['h']}px (min {t['min']}×{t['min']})",
                             t["sel"], "Give it min-height/min-width 44px (padding), e.g. .btn--sm { min-height: 44px }" if t["min"] >= 44 else
                             "Make the link ≥ 24px tall (padding-block) or space links ≥ 24px apart (WCAG 2.5.8).", w)
                    page.evaluate("() => window.scrollTo(0, 0)")
                    # mobile nav sheet
                    opener = page.query_selector("[data-nav-open]")
                    if opener and opener.is_visible():
                        opener.click()
                        page.wait_for_timeout(80)
                        taps = page.evaluate(JS_TAPS, [["nav sheet", "#nav-sheet a, #nav-sheet button", 44, False]])
                        for t in taps:
                            note(pname, "responsive", sev, "tap-target", t["sel"], f"nav sheet tap target “{t['label']}” is {t['w']}×{t['h']}px (min 44×44)", t["sel"], "Pad it to ≥ 44px.", w, owner="system")
                        if w in AXE_WIDTHS and axe_path:
                            page.add_script_tag(path=str(axe_path))
                            for v in page.evaluate(AXE_RUN, "#nav-sheet"):
                                axe_note(rep, axe_seen, pname, v, w, "open mobile nav sheet")
                        page.keyboard.press("Escape")
                        page.wait_for_timeout(60)
                        ok = page.evaluate("() => document.activeElement && document.activeElement.hasAttribute('data-nav-open')")
                        if not ok:
                            note(pname, "a11y", WARN, "focus-return", "nav", "closing the mobile menu (Escape) doesn't return focus to the menu button",
                                 "button[data-nav-open]", "In site.js setNav(false), call document.querySelector('[data-nav-open]').focus() when the sheet was open.", w, owner="system")
                # axe
                if w in AXE_WIDTHS and axe_path:
                    page.add_script_tag(path=str(axe_path))
                    for v in page.evaluate(AXE_RUN, None):
                        axe_note(rep, axe_seen, pname, v, w, "")
                page.close()
            bctx.close()
        browser.close()
    for (page, cat, sev, check, key), d in resp_issues.items():
        msg, el, fix, owner = d["detail"]
        ws = sorted(d["widths"])
        rep.add(page, cat, sev, check, msg + f" [at {fmt_widths(ws)}]", el, fix, owner=owner, widths=ws)
    for (page, rid, where), d in axe_seen.items():
        v = d["v"]
        sev = FAIL if v["impact"] in ("critical", "serious") else WARN
        tg = list(d["targets"])
        first = d["targets"][tg[0]] if tg else {"summary": "", "html": ""}
        summ = re.sub(r"^Fix (?:any|all) of the following:\s*", "", first["summary"])
        rep.add(page, "a11y", sev, f"axe:{rid}", f"{v['help']} ({v['impact']}, {len(tg)} element{'s' if len(tg) != 1 else ''}){' in the ' + where if where else ''}: "
                f"{', '.join(tg[:6])}{' …' if len(tg) > 6 else ''} [at {fmt_widths(sorted(d['widths']))}]",
                tg[0] if tg else "", f"{summ} First element: {first['html'][:120]} — {v['helpUrl']}", widths=sorted(d["widths"]),
                targets=[{"target": t, "html": n["html"], "summary": n["summary"]} for t, n in d["targets"].items()])


def axe_note(rep, seen, page, v, w, where):
    k = (page, v["id"], where)
    if k not in seen:
        seen[k] = {"v": v, "widths": set(), "targets": {}, "where": where}
    d = seen[k]
    d["widths"].add(w)
    for nd in v["nodes"]:
        d["targets"].setdefault(nd["target"], nd)


def fmt_widths(ws):
    if not ws:
        return ""
    if len(ws) == len(WIDTHS):
        return "all widths"
    return ", ".join(f"{x}" for x in ws) + " px"


# ---------------------------------------------------------------- Lighthouse ----------------------------------------

def lighthouse(url, form, out_json, categories, lh_bin):
    cmd = [str(lh_bin), url, "--output=json", f"--output-path={out_json}", "--quiet", "--max-wait-for-load=45000",
           "--chrome-flags=--headless=new --no-first-run --no-default-browser-check --disable-extensions",
           f"--only-categories={','.join(categories)}"]
    if form == "desktop":
        cmd.append("--preset=desktop")
    env = dict(os.environ)
    if Path(CHROME).exists():
        env.setdefault("CHROME_PATH", CHROME)
    try:
        r = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=240)
    except subprocess.TimeoutExpired:
        return None, "timed out after 240 s"
    if not Path(out_json).exists():
        return None, (r.stderr or r.stdout)[-600:]
    try:
        return json.loads(Path(out_json).read_text()), None
    except json.JSONDecodeError as e:
        return None, str(e)


def lh_summary(js):
    a = js["audits"]
    cats = {k: (round(v["score"] * 100) if v.get("score") is not None else None) for k, v in js["categories"].items()}

    def num(k):
        return (a.get(k) or {}).get("numericValue")
    out = {"scores": cats, "lcp_ms": num("largest-contentful-paint"), "cls": num("cumulative-layout-shift"),
           "tbt_ms": num("total-blocking-time"), "fcp_ms": num("first-contentful-paint"), "si_ms": num("speed-index"),
           "bytes": num("total-byte-weight"), "failing": []}
    for cid, cat in js["categories"].items():
        for ref in cat.get("auditRefs", []):
            au = a.get(ref["id"]) or {}
            mode = au.get("scoreDisplayMode")
            if mode in ("notApplicable", "manual", "informative") or au.get("score") is None:
                if mode == "error":
                    out["failing"].append({"cat": cid, "id": ref["id"], "title": au.get("title"), "score": None, "display": au.get("errorMessage", "error")})
                continue
            thr = 0.9 if cid == "performance" else 1
            if au["score"] < thr and (ref.get("weight", 0) > 0 or cid == "performance"):
                items = ((au.get("details") or {}).get("items") or [])[:3]
                ex = []
                for it in items:
                    node = it.get("node") if isinstance(it, dict) else None
                    s = (node or {}).get("selector") or it.get("url") if isinstance(it, dict) else None
                    if s:
                        ex.append(re.sub(r"^https?://127\.0\.0\.1:\d+/(?:justonemorebite/)?", "", str(s))[:90])
                out["failing"].append({"cat": cid, "id": ref["id"], "title": au.get("title"), "score": au["score"],
                                       "display": au.get("displayValue", ""), "weight": ref.get("weight", 0), "examples": ex})
    seo = js["categories"].get("seo")
    if seo:
        tot = sc = 0
        for ref in seo["auditRefs"]:
            au = a.get(ref["id"]) or {}
            if ref["id"] == "is-crawlable" or au.get("score") is None or not ref.get("weight"):
                continue
            tot += ref["weight"]
            sc += ref["weight"] * au["score"]
        out["seo_excl_crawlable"] = round(100 * sc / tot) if tot else None
    return out


TARGETS = {"performance": 90, "accessibility": 95, "best-practices": 95, "seo": 100}


def run_lighthouse(ctx, rep, server, lh_bin, pages, tmp):
    for name in pages:
        rel = ctx.pages[name].rel
        for form in ("mobile", "desktop"):
            out = tmp / f"lh-{name.replace('/', '_')}-{form}.json"
            t0 = time.time()
            js, err = lighthouse(server.url(rel), form, out, ["performance", "accessibility", "best-practices", "seo"], lh_bin)
            print(f"  lighthouse {form:7s} {name:28s} {time.time() - t0:5.1f}s", flush=True)
            if not js:
                rep.add(name, "perf", FAIL, "lighthouse-run", f"Lighthouse {form} failed: {err}", "lighthouse", "Re-run; check Chrome and the local server.", owner="system")
                continue
            s = lh_summary(js)
            rep.page(name)["lighthouse"][form] = s
            for cat, target in TARGETS.items():
                score = s["scores"].get(cat)
                if score is None:
                    continue
                if cat == "seo":
                    excl = s.get("seo_excl_crawlable")
                    if ctx.site.get("preview"):
                        if excl is not None and excl < 100:
                            rep.add(name, "perf", FAIL, f"lh-seo-{form}", f"Lighthouse SEO {score} ({excl} ignoring the deliberate preview noindex) on {form}", "lighthouse",
                                    lh_fix(s, "seo"), owner=None)
                        continue
                if score < target:
                    rep.add(name, "perf", FAIL, f"lh-{cat}-{form}", f"Lighthouse {cat} {score} on {form} (target ≥ {target})", "lighthouse", lh_fix(s, cat))


def lh_fix(s, cat):
    items = [f for f in s["failing"] if f["cat"] == cat]
    items.sort(key=lambda f: (f.get("score") if f.get("score") is not None else 0, -f.get("weight", 0)))
    parts = []
    for f in items[:5]:
        ex = f" e.g. {', '.join(f['examples'][:2])}" if f.get("examples") else ""
        parts.append(f"{f['title']}{' (' + f['display'] + ')' if f.get('display') else ''}{ex}")
    return "Failing audits: " + " · ".join(parts) if parts else "See the Lighthouse JSON."


# ---------------------------------------------------------------- production pass -----------------------------------

def build_prod_copy(tmp):
    dst = tmp / "prod"
    dst.mkdir(parents=True, exist_ok=True)
    shutil.copy(ROOT / "build.py", dst / "build.py")
    shutil.copytree(SRC, dst / "src", ignore=shutil.ignore_patterns("source", "sheet_*.jpg", ".DS_Store"))
    (dst / "docs").mkdir()
    shutil.copytree(DOCS / "img", dst / "docs" / "img")
    for f in ("favicon.png", "apple-touch-icon.png", "icon-192.png", "icon-512.png"):
        if (DOCS / f).exists():
            shutil.copy(DOCS / f, dst / "docs" / f)
    sj = dst / "src" / "site.json"
    site = json.loads(sj.read_text())
    site["preview"] = False
    site["base_url"] = site.get("production_url") or site["base_url"]
    sj.write_text(json.dumps(site, indent=2, ensure_ascii=False))
    r = subprocess.run([sys.executable, "build.py"], cwd=dst, capture_output=True, text=True, timeout=300)
    warns = [ln[6:] for ln in r.stdout.splitlines() if ln.startswith("WARN:")]
    return dst / "docs", site, warns, r


def prod_checks(ctx, rep, prod_docs, prod_site, lh_bin, tmp, run_lh):
    base = prod_site["base_url"].rstrip("/")
    pages = discover(prod_docs)
    res = {"base_url": base, "pages": {}}
    for name, (f, rel) in pages.items():
        if name not in ctx.selected and name != "404":
            continue
        p = PageDoc(name, f, rel, prod_docs)
        robots = (p.meta(name="robots") or "").lower()
        canon = next((l.get("href") for l in p.head.find_all("link") if "canonical" in (l.get("rel") or "").split()), "")
        if name == "404":
            if "noindex" not in robots:
                rep.add("404", "prod", WARN, "404-noindex", "production 404 page is indexable (robots: index, follow)", "meta[name=robots]",
                        "In build.py head(), use noindex for meta.special == '404' even when preview is false.", owner="system")
            continue
        if "noindex" in robots or "index" not in robots:
            rep.add(name, "prod", FAIL, "robots", f"production robots meta is \"{robots}\"", "meta[name=robots]", "build.py head() should emit index, follow when preview is false.", owner="system")
        if p.dom.first("body") and any("preview-ribbon" in x.classes() for x in p.dom.iter()):
            rep.add(name, "prod", FAIL, "ribbon", "preview ribbon still rendered with preview=false", ".preview-ribbon", "Gate it on SITE['preview'] in build.py.", owner="system")
        if not canon.startswith(base):
            rep.add(name, "prod", FAIL, "canonical", f"canonical {canon} does not use the production base {base}", "link[rel=canonical]", "Set base_url to the production URL at launch.", owner="system")
        res["pages"][name] = {"robots": robots, "canonical": canon}
    sm = (prod_docs / "sitemap.xml").read_text() if (prod_docs / "sitemap.xml").exists() else ""
    if base not in sm:
        rep.add("(site)", "prod", FAIL, "sitemap", "production sitemap.xml doesn't use the production base URL", "sitemap.xml", "build.py write_extras().", owner="system")
    if "404" in sm:
        rep.add("(site)", "prod", FAIL, "sitemap", "sitemap lists the 404 page", "sitemap.xml", "Skip special pages in write_extras().", owner="system")
    if run_lh:
        server = SiteServer(prod_docs, "/")
        try:
            for name in [x for x in ctx.lh_pages if x in pages and x != "404"]:
                out = tmp / f"lh-prod-{name.replace('/', '_')}.json"
                t0 = time.time()
                js, err = lighthouse(server.url(pages[name][1]), "mobile", out, ["seo"], lh_bin)
                print(f"  lighthouse prod-seo {name:28s} {time.time() - t0:5.1f}s", flush=True)
                if not js:
                    rep.add(name, "prod", FAIL, "lighthouse-run", f"Lighthouse production SEO run failed: {err}", "lighthouse", "Re-run.", owner="system")
                    continue
                s = lh_summary(js)
                res["pages"].setdefault(name, {})["lighthouse_seo"] = s["scores"].get("seo")
                rep.page(name)["lighthouse"]["prod_seo"] = s["scores"].get("seo")
                if (s["scores"].get("seo") or 0) < 100:
                    rep.add(name, "prod", FAIL, "lh-seo-prod", f"Lighthouse SEO {s['scores'].get('seo')} on the production build (target 100)", "lighthouse", lh_fix(s, "seo"))
        finally:
            server.close()
    return res


# ---------------------------------------------------------------- report writing ------------------------------------

def status_of(issues):
    if any(i["sev"] == FAIL for i in issues):
        return "FAIL"
    if any(i["sev"] == WARN for i in issues):
        return "WARN"
    return "PASS"


ICON = {"FAIL": "❌", "WARN": "⚠️", "PASS": "✅", "INFO": "ℹ️", "—": "—"}


def cell(issues, ran=True):
    if not ran:
        return "—"
    st = status_of(issues)
    nf = sum(1 for i in issues if i["sev"] == FAIL)
    nw = sum(1 for i in issues if i["sev"] == WARN)
    if st == "PASS":
        return "✅"
    return f"{ICON[st]} {nf}F/{nw}W" if nf else f"{ICON[st]} {nw}W"


def page_score(issues):
    nf = sum(1 for i in issues if i["sev"] == FAIL)
    nw = sum(1 for i in issues if i["sev"] == WARN)
    return max(0, 100 - 8 * nf - 2 * nw)


def write_reports(ctx, rep, args, prod, build_warns, t_start):
    OUT_DIR.mkdir(exist_ok=True)
    pages = list(ctx.selected)
    by_page = defaultdict(list)
    for i in rep.issues:
        by_page[i["page"]].append(i)
    counted = [i for i in rep.issues if i["sev"] in (FAIL, WARN)]
    nf = sum(1 for i in counted if i["sev"] == FAIL)
    nw = sum(1 for i in counted if i["sev"] == WARN)
    scores = {p: page_score(by_page[p]) for p in pages}
    site_score = round(sum(scores.values()) / len(scores)) if scores else 0
    result = "FAIL" if nf else "PASS"
    ran = {"seo": True, "schema": True, "facts": True, "responsive": ctx.ran_browser, "a11y": ctx.ran_browser, "perf": ctx.ran_lh}

    L = []
    L.append("# Just One More Bite: QA report")
    L.append("")
    L.append(f"Generated {datetime.now().strftime('%Y-%m-%d %H:%M')} by `tools/qa.py` in {time.time() - t_start:.0f} s · "
             f"{len(pages)} page(s) · widths {', '.join(map(str, ctx.widths)) if ctx.ran_browser else '(browser checks skipped)'} · "
             f"Lighthouse {'on' if ctx.ran_lh else 'skipped'} · production pass {'on' if prod else 'skipped'}")
    L.append("")
    L.append(f"**Result: {result}** · {nf} fail(s), {nw} warning(s) · site QA score **{site_score}/100** "
             "(per page: 100 − 8 per FAIL − 2 per WARN)")
    L.append("")
    L.append("## Summary")
    L.append("")
    L.append("| Page | Score | SEO | Schema | Facts | Responsive | A11y | LH mobile P/A/BP/SEO | LH desktop P/A/BP/SEO | Mobile LCP · CLS · TBT · KB |")
    L.append("|---|---|---|---|---|---|---|---|---|---|")
    for p in pages:
        iss = by_page[p]
        cells = [cell([i for i in iss if i["cat"] == c], ran[c]) for c in ("seo", "schema", "facts", "responsive", "a11y")]
        lh = rep.page(p)["lighthouse"]

        def lhs(form):
            s = lh.get(form)
            if not s:
                return "—"
            sc = s["scores"]
            seo = sc.get("seo")
            seo_s = f"{seo}" + (f" ({s.get('seo_excl_crawlable')}†)" if ctx.site.get("preview") and s.get("seo_excl_crawlable") is not None else "")
            if lh.get("prod_seo") is not None and form == "mobile":
                seo_s += f" / prod {lh['prod_seo']}"
            return f"{sc.get('performance')}/{sc.get('accessibility')}/{sc.get('best-practices')}/{seo_s}"
        m = lh.get("mobile")
        vit = (f"{m['lcp_ms'] / 1000:.1f}s · {m['cls']:.3f} · {m['tbt_ms']:.0f}ms · {m['bytes'] / 1024:.0f}" if m and m.get("lcp_ms") is not None else "—")
        L.append(f"| [{p}](#{anchor(p)}) | {scores[p]} | " + " | ".join(cells) + f" | {lhs('mobile')} | {lhs('desktop')} | {vit} |")
    L.append("")
    if ctx.ran_lh and ctx.site.get("preview"):
        L.append("† Preview builds carry `noindex` on purpose, so Lighthouse SEO fails *Page is blocked from indexing*. The number in brackets is the SEO "
                 "score without that audit; `prod` is the score from a temporary copy built with `\"preview\": false` (the real site.json is never edited).")
        L.append("")
    site_issues = by_page.get("(site)", [])
    # system-level issues, grouped across pages
    sys_groups = defaultdict(list)
    for i in counted:
        if i["owner"] == "system" or i["page"] == "(site)":
            key = (i["sev"], i["cat"], i["check"], re.sub(r"(?:\.\./)+", "", re.sub(r"\[at [^\]]*\]", "", i["msg"])), re.sub(r":nth-of-type\(\d+\)", "", i["el"]))
            sys_groups[key].append(i)
    L.append("## System-level issues (site.css · site.js · build.py)")
    L.append("")
    if not sys_groups:
        L.append("None.")
    for sev in (FAIL, WARN):
        rows = [(k, v) for k, v in sys_groups.items() if k[0] == sev]
        rows.sort(key=lambda kv: (-len(kv[1]), kv[0][1], kv[0][2]))
        for (s, cat, check, msg, el), items in rows:
            pgs = sorted({i["page"] for i in items})
            ws = sorted({w for i in items for w in i.get("widths", [])})
            L.append(f"- {ICON[s]} **{s}** [{CAT_LABEL.get(cat, cat)} · {check}] `{el}`: {msg.strip()}"
                     f"{' [at ' + fmt_widths(ws) + ']' if ws else ''} · pages: {', '.join(pgs)}")
            if items[0]["fix"]:
                L.append(f"  - Fix: {items[0]['fix']}")
    L.append("")
    if build_warns:
        L.append("## Build warnings (from a fresh build of src/)")
        L.append("")
        for w in build_warns:
            L.append(f"- `{w}`")
        L.append("")
    L.append("## Page issues")
    L.append("")
    for p in pages + (["(site)"] if site_issues else []):
        iss = [i for i in by_page[p] if not (i["owner"] == "system" and i["sev"] in (FAIL, WARN))]
        nsys = sum(1 for i in by_page[p] if i["owner"] == "system" and i["sev"] in (FAIL, WARN))
        L.append(f"### {p}")
        L.append("")
        st = rep.page(p)["stats"]
        if st.get("title"):
            L.append(f"Title ({st.get('title_len')}): {st['title']} · description {st.get('description_len')} chars · internal links in main: {len(st.get('internal_links_in_main', []))}")
            L.append("")
        shown = [i for i in iss if i["sev"] in (FAIL, WARN)]
        info = [i for i in iss if i["sev"] == INFO]
        if not shown:
            L.append("No page-level FAIL/WARN." + (f" ({nsys} system-level issue(s) listed above.)" if nsys else ""))
        else:
            L.append("| Sev | Area | Check | Element | Issue | Fix |")
            L.append("|---|---|---|---|---|---|")
            shown.sort(key=lambda i: (i["sev"] != FAIL, CATS.index(i["cat"]) if i["cat"] in CATS else 9))
            for i in shown:
                L.append(f"| {ICON[i['sev']]} {i['sev']} | {CAT_LABEL.get(i['cat'], i['cat'])} | {i['check']} | `{md(i['el'])}` | {md(i['msg'])} | {md(i['fix'])} |")
            if nsys:
                L.append("")
                L.append(f"Plus {nsys} system-level issue(s) listed above.")
        if info:
            L.append("")
            L.append("<details><summary>Info (" + str(len(info)) + ")</summary>")
            L.append("")
            for i in info:
                L.append(f"- [{CAT_LABEL.get(i['cat'], i['cat'])} · {i['check']}] {md(i['msg'])}")
            L.append("")
            L.append("</details>")
        ff = rep.page(p)["facts_found"]
        if ff:
            L.append("")
            L.append("<details><summary>Facts seen on this page</summary>")
            L.append("")
            for k in ("phones", "emails", "deadlines", "delivery", "windows", "menu_posted", "prices", "years", "other_day_times"):
                if ff.get(k):
                    vals = list(dict.fromkeys(ff[k]))
                    L.append(f"- **{k}**: {md(', '.join(vals[:30]))}{' …' if len(vals) > 30 else ''}")
            L.append("")
            L.append("</details>")
        lh = rep.page(p)["lighthouse"]
        if lh.get("mobile") or lh.get("desktop"):
            L.append("")
            L.append("<details><summary>Lighthouse audits below target</summary>")
            L.append("")
            for form in ("mobile", "desktop"):
                s = lh.get(form)
                if not s:
                    continue
                for f in s["failing"]:
                    if ctx.site.get("preview") and f["id"] == "is-crawlable":
                        continue
                    ex = f" ({', '.join(f.get('examples', [])[:2])})" if f.get("examples") else ""
                    L.append(f"- {form} · {f['cat']} · {f['title']}{' — ' + f['display'] if f.get('display') else ''}{md(ex)}")
            L.append("")
            L.append("</details>")
        L.append("")
    L.append("## How to run")
    L.append("")
    L.append("```bash")
    L.append("<venv>/bin/python tools/qa.py                       # everything (~1 min per page with Lighthouse)")
    L.append("<venv>/bin/python tools/qa.py --pages home,menus --no-lighthouse")
    L.append("python3 tools/qa.py --no-browser --no-lighthouse    # static checks only, standard library")
    L.append("```")
    L.append("")
    L.append("Checks: SEO basics, JSON-LD (FAQ text = visible text, phone = tel: links), fact consistency against `src/site.json` "
             "(phone, deadline, delivery day/window, menu day, prices, email), banned claims (medical, superlatives, AI filler), "
             "regulatory trust claims outside the `compliance` switch, street addresses and legal hedging, responsive layout at "
             "320–1440 px (overflow, clipped text, tap targets, console errors, failed requests, the 404 page at a nested URL), "
             "axe-core WCAG 2.2 AA, and Lighthouse mobile + desktop. Exit code 1 on any FAIL.")
    (OUT_DIR / "REPORT.md").write_text("\n".join(L) + "\n")
    data = {
        "generated": datetime.now().isoformat(timespec="seconds"), "result": result, "fails": nf, "warnings": nw,
        "site_score": site_score, "pages": {p: {"score": scores[p], "status": {c: (status_of([i for i in by_page[p] if i["cat"] == c]) if ran[c] else None) for c in CATS},
                                                "stats": rep.page(p)["stats"], "facts_found": rep.page(p)["facts_found"], "lighthouse": rep.page(p)["lighthouse"]} for p in pages},
        "issues": rep.issues, "production_pass": prod, "build_warnings": build_warns,
        "config": {"widths": ctx.widths, "browser": ctx.ran_browser, "lighthouse": ctx.ran_lh, "allow_pending": ctx.allow_pending},
    }
    (OUT_DIR / "report.json").write_text(json.dumps(data, indent=1, default=lambda o: sorted(o) if isinstance(o, set) else str(o), ensure_ascii=False))
    return result, nf, nw, site_score, scores


def md(s):
    return str(s).replace("|", "\\|").replace("\n", " ")


def anchor(p):
    return re.sub(r"[^a-z0-9 -]", "", p.lower()).replace(" ", "-")


# ---------------------------------------------------------------- main ----------------------------------------------

class Ctx:
    pass


def snapshot_docs(tmp):
    """Copy docs/ under the build lock so a parallel build can't change files mid-run."""
    dst = tmp / "docs"
    with open(ROOT / ".build.lock", "a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        shutil.copytree(DOCS, dst)
    return dst


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--pages", default="", help="comma list of page names (home, menus, zone-meal-delivery, 404 …)")
    ap.add_argument("--lh-pages", default="", help="limit Lighthouse to these pages (default: --pages)")
    ap.add_argument("--widths", default=",".join(map(str, WIDTHS)))
    ap.add_argument("--no-browser", action="store_true", help="skip Playwright (responsive + axe)")
    ap.add_argument("--no-lighthouse", action="store_true")
    ap.add_argument("--no-prod", action="store_true", help="skip the preview:false production-build pass")
    ap.add_argument("--allow-pending", action="store_true", help="links/breadcrumbs to planned pages that aren't built yet are INFO, not FAIL")
    ap.add_argument("--build", action="store_true", help="run build.py before checking")
    ap.add_argument("--install", action="store_true", help=f"npm install axe-core + lighthouse into {NODE_PREFIX}")
    a = ap.parse_args()
    t_start = time.time()
    if a.install:
        NODE_PREFIX.mkdir(parents=True, exist_ok=True)
        subprocess.run(["npm", "install", "--no-audit", "--no-fund", "--prefix", str(NODE_PREFIX), "axe-core", "lighthouse"], check=True)
    if a.build:
        subprocess.run([sys.executable, "build.py"], cwd=ROOT)
    site = json.loads((SRC / "site.json").read_text())
    tmp = Path(tempfile.mkdtemp(prefix="jomb-qa-"))
    try:
        docs = snapshot_docs(tmp)
        ctx = Ctx()
        ctx.site, ctx.facts, ctx.docs, ctx.allow_pending = site, Facts(site), docs, a.allow_pending
        found = discover(docs)
        ctx.pages = {nm: PageDoc(nm, f, rel, docs) for nm, (f, rel) in found.items()}
        want = [x.strip().strip("/") for x in a.pages.split(",") if x.strip()]
        unknown = [w for w in want if w not in ctx.pages]
        if unknown:
            print("not built (skipped):", ", ".join(unknown))
        ctx.selected = [nm for nm in ctx.pages if not want or nm in want]
        ctx.lh_pages = [x.strip() for x in a.lh_pages.split(",") if x.strip()] or ctx.selected
        ctx.widths = [int(x) for x in a.widths.split(",") if x.strip()]
        ctx.sitemap = (docs / "sitemap.xml").read_text() if (docs / "sitemap.xml").exists() else None
        ctx.llms = (docs / "llms.txt").read_text() if (docs / "llms.txt").exists() else None
        rep = Report()
        print(f"QA: {len(ctx.selected)} page(s): {', '.join(ctx.selected)}", flush=True)
        for nm in ctx.selected:
            p = ctx.pages[nm]
            check_seo(p, ctx, rep)
            check_schema(p, ctx, rep)
            check_facts(p, ctx, rep)
        check_global(ctx, rep)
        check_site_json(ctx, rep)
        check_sources(ctx, rep)
        print(f"  static checks done ({time.time() - t_start:.0f}s)", flush=True)
        ctx.ran_browser = ctx.ran_lh = False
        axe_path = NODE_PREFIX / "node_modules" / "axe-core" / "axe.min.js"
        lh_bin = NODE_PREFIX / "node_modules" / ".bin" / "lighthouse"
        server = SiteServer(docs, PREFIX)
        try:
            if not a.no_browser:
                if not axe_path.exists():
                    rep.add("(site)", "a11y", WARN, "axe-missing", f"axe-core not found at {axe_path}; accessibility scan skipped", "", f"python3 tools/qa.py --install (or set QA_NODE)", owner="system")
                    axe_path = None
                browser_checks(ctx, rep, server, axe_path, ctx.widths)
                ctx.ran_browser = True
                print(f"  browser checks done ({time.time() - t_start:.0f}s)", flush=True)
            if not a.no_lighthouse:
                if not lh_bin.exists():
                    rep.add("(site)", "perf", WARN, "lighthouse-missing", f"lighthouse not found at {lh_bin}; skipped", "", "python3 tools/qa.py --install (or set QA_NODE)", owner="system")
                else:
                    run_lighthouse(ctx, rep, server, lh_bin, [x for x in ctx.lh_pages if x in ctx.pages], tmp)
                    ctx.ran_lh = True
        finally:
            server.close()
        prod, build_warns = None, []
        if not a.no_prod:
            prod_docs, prod_site, build_warns, r = build_prod_copy(tmp)
            if not (prod_docs / "index.html").exists():
                rep.add("(site)", "prod", FAIL, "build", f"production build failed: {(r.stderr or r.stdout)[-400:]}", "build.py", "Fix the build error.", owner="system")
            else:
                prod = prod_checks(ctx, rep, prod_docs, prod_site, lh_bin, tmp, ctx.ran_lh)
            print(f"  production pass done ({time.time() - t_start:.0f}s)", flush=True)
        result, nf, nw, score, scores = write_reports(ctx, rep, a, prod, build_warns, t_start)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print()
    for p, s in scores.items():
        iss = [i for i in rep.issues if i["page"] == p]
        print(f"  {p:30s} {s:3d}  " + "  ".join(f"{CAT_LABEL[c]}:{status_of([i for i in iss if i['cat'] == c])}" for c in CATS))
    print(f"\n{result}: {nf} fail(s), {nw} warning(s), site score {score}/100 → {OUT_DIR / 'REPORT.md'}")
    return 1 if nf else 0


if __name__ == "__main__":
    sys.exit(main())
