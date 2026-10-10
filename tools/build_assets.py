"""Build the animated SVG cards used by the profile README.

Run from the repo root:  python tools/build_assets.py
Writes assets/hero.svg, about.svg, stack.svg and connect.svg.

Edit the CONTENT section below to change text; layout is measured from the
real font metrics, so chips and labels re-flow automatically.
Portrait: tools/photo.webp (cropped and inlined into the hero).
Fonts: Barlow Condensed and IBM Plex Mono (SIL OFL 1.1, see licenses/).
"""

from __future__ import annotations

import base64
import io
import re
from dataclasses import dataclass
from html import escape
from pathlib import Path

from fontTools import subset
from fontTools.ttLib import TTFont
from PIL import Image, ImageEnhance, ImageFilter

ROOT = Path(__file__).resolve().parent.parent
FONT_DIR = ROOT / "tools" / "fonts"
OUT_DIR = ROOT / "assets"

# ---------------------------------------------------------------- palette
# Pulled from the portrait: ember-lit maroon studio, orange key light, sand backdrop.
BG = "#0d0605"
CARD_2 = "#120605"
LINE = "#4a1d10"
TEXT = "#fff1e6"
MUTED = "#c9a28c"
DIM = "#8c5f4c"
ACCENT = "#ff6a1f"
ACCENT_LIGHT = "#ff9d5c"
ACCENT_PALE = "#ffd0ad"
HOT = "#e0301e"
SAND = "#d4926a"

WIDTH = 1200

# ---------------------------------------------------------------- content
NAME_FIRST = "DAKSHIN"
NAME_LAST = "RAJ"
ROLE = "Backend · Agentic AI · Flutter"
PITCH = "Turning LLMs, data and APIs into systems that run in the real world."
META = [
    ("pin", "Coimbatore, India"),
    ("cap", "B.Tech CSE · Amrita · Y3"),
    ("git", "github.com/Dakshin10"),
]

FOCUS = [
    ("server", "Backend Engineering", "FastAPI, Node and Postgres services built to scale."),
    ("graph", "Agentic AI", "Multi-agent graphs, tool calling, MCP servers and RAG."),
    ("phone", "Flutter Apps", "Cross-platform apps wired to real-time backends."),
]

WHOAMI = [
    'const dakshin: Developer = {',
    '  name   : "Dakshin Raj",',
    '  role   : "AI Engineer Intern @ MinoriLabs",',
    '  study  : "B.Tech CSE @ Amrita",',
    '  year   : "3rd Year",',
    '  base   : "Coimbatore, India",',
    '  focus  : ["Backend", "Agentic AI", "Flutter"],',
    '  edge   : "AI systems, not just CRUD apps",',
    '};',
]

STACK = [
    ("Languages", ["Python", "TypeScript", "JavaScript", "Java", "C", "Dart"]),
    ("Mobile", ["Flutter"]),
    ("Backend", ["FastAPI", "Node.js", "Express", "Django", "REST APIs"]),
    ("Databases", ["PostgreSQL", "MySQL", "MongoDB", "SQLite", "Cloudflare D1", "Redis", "Firebase"]),
    ("Agentic AI", ["LangGraph", "LangChain", "MCP", "FastMCP", "Tool calling", "Multi-agent orchestration"]),
    ("LLMs", ["Groq", "Llama", "GPT-OSS", "Ollama", "Qwen", "Gemini API"]),
    ("RAG & Doc AI", ["RAG pipelines", "PaddleOCR", "PyMuPDF", "PDF extraction"]),
    ("Integrations", ["Google Sheets", "OAuth 2.0", "WebSockets", "MQTT"]),
    ("Cloud & Tooling", ["GCP", "Cloudflare", "Vercel", "Render", "Git", "GitHub"]),
]

CONNECT = [
    ("LINKEDIN", "in/dakshin-raj"),
    ("EMAIL", "dakshinrajponraju@gmail.com"),
    ("GITHUB", "Dakshin10"),
]


# ---------------------------------------------------------------- fonts
@dataclass(frozen=True)
class Face:
    family: str
    file: str
    weight: int


DISPLAY = Face("Display", "display800.woff2", 800)
MONO = Face("Mono", "mono400.woff2", 400)
MONO_BOLD = Face("Mono", "mono600.woff2", 600)
FACES = (DISPLAY, MONO, MONO_BOLD)

_metrics: dict[str, tuple[dict[int, str], dict[str, tuple[int, int]], int]] = {}


def _load_metrics(face: Face):
    if face.file not in _metrics:
        font = TTFont(FONT_DIR / face.file)
        _metrics[face.file] = (
            font.getBestCmap(),
            font["hmtx"].metrics,
            font["head"].unitsPerEm,
        )
    return _metrics[face.file]


def text_width(text: str, face: Face, size: float, tracking: float = 0.0) -> float:
    cmap, hmtx, upem = _load_metrics(face)
    units = sum(hmtx[cmap.get(ord(ch), ".notdef")][0] for ch in text)
    return units * size / upem + tracking * len(text)


def font_face_css(face: Face, chars: str) -> str:
    """Subset a face to the characters actually used and inline it as base64."""
    font = TTFont(FONT_DIR / face.file)
    options = subset.Options()
    options.flavor = "woff2"
    options.layout_features = ["kern", "liga"]
    options.name_IDs = []  # drop names: the subset is a renamed, modified copy
    subsetter = subset.Subsetter(options)
    subsetter.populate(text=chars + " ")
    subsetter.subset(font)
    buffer = io.BytesIO()
    font.flavor = "woff2"
    font.save(buffer)
    data = base64.b64encode(buffer.getvalue()).decode("ascii")
    return (
        f"@font-face{{font-family:{face.family};font-weight:{face.weight};"
        f"src:url(data:font/woff2;base64,{data}) format('woff2')}}"
    )


# ---------------------------------------------------------------- svg helpers
class Svg:
    """Collects markup plus the characters each face renders, for subsetting."""

    def __init__(self, height: int, title: str, desc: str):
        self.height = height
        self.title = title
        self.desc = desc
        self.parts: list[str] = []
        self.defs: list[str] = []
        self.chars: dict[str, set[str]] = {face.file: set() for face in FACES}

    def add(self, markup: str) -> None:
        self.parts.append(markup)

    def text(self, x, y, value, face: Face, size, fill=TEXT, anchor="start",
             tracking=0.0, cls="", extra="") -> None:
        self.chars[face.file].update(value)
        family = "Display,sans-serif" if face is DISPLAY else "Mono,monospace"
        attrs = [
            f'x="{x:g}"', f'y="{y:g}"', f'font-family="{family}"',
            f'font-weight="{face.weight}"', f'font-size="{size:g}"', f'fill="{fill}"',
        ]
        if anchor != "start":
            attrs.append(f'text-anchor="{anchor}"')
        if tracking:
            attrs.append(f'letter-spacing="{tracking:g}"')
        if cls:
            attrs.append(f'class="{cls}"')
        if extra:
            attrs.append(extra)
        self.add(f'<text {" ".join(attrs)}>{escape(value)}</text>')

    def spans(self, x, y, runs: list[tuple[str, str]], face: Face, size, cls="") -> None:
        """One line of text made of differently coloured runs."""
        self.chars[face.file].update("".join(value for value, _ in runs))
        family = "Display,sans-serif" if face is DISPLAY else "Mono,monospace"
        body = "".join(
            f'<tspan fill="{fill}">{escape(value)}</tspan>' for value, fill in runs
        )
        cls_attr = f' class="{cls}"' if cls else ""
        self.add(
            f'<text x="{x:g}" y="{y:g}" font-family="{family}" font-weight="{face.weight}" '
            f'font-size="{size:g}" xml:space="preserve"{cls_attr}>{body}</text>'
        )

    def render(self) -> str:
        fonts = "".join(
            font_face_css(face, "".join(sorted(self.chars[face.file])))
            for face in FACES
            if self.chars[face.file]
        )
        slug = re.sub(r"[^a-z]+", "-", self.title.lower()).strip("-")
        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{self.height}" '
            f'viewBox="0 0 {WIDTH} {self.height}" role="img" '
            f'aria-labelledby="{slug}-t {slug}-d">'
            f'<title id="{slug}-t">{escape(self.title)}</title>'
            f'<desc id="{slug}-d">{escape(self.desc)}</desc>'
            f"<style>{fonts}{BASE_CSS}</style>"
            f"<defs>{COMMON_DEFS}{''.join(self.defs)}</defs>"
            f"{''.join(self.parts)}</svg>"
        )


BASE_CSS = """
.rise{animation:rise .9s cubic-bezier(.2,.7,.2,1) both}
.d1{animation-delay:.08s}.d2{animation-delay:.16s}.d3{animation-delay:.24s}
.d4{animation-delay:.32s}.d5{animation-delay:.4s}.d6{animation-delay:.48s}
.d7{animation-delay:.56s}.d8{animation-delay:.64s}.d9{animation-delay:.72s}
.blink{animation:blink 1.1s steps(1) infinite}
.pulse{transform-box:fill-box;transform-origin:center;animation:pulse 2.6s ease-out infinite}
.flow{stroke-dasharray:3 7;animation:flow 1.4s linear infinite}
.spin{animation:spin 60s linear infinite}
.spin-rev{animation:spin 90s linear infinite reverse}
.float{animation:float 6s ease-in-out infinite}
.scan{animation:scan 4.5s ease-in-out infinite}
.glow{animation:glow 5s ease-in-out infinite}
@keyframes rise{from{opacity:0;transform:translateY(14px)}to{opacity:1;transform:none}}
@keyframes blink{50%{opacity:0}}
@keyframes pulse{0%{transform:scale(.6);opacity:.9}100%{transform:scale(1.9);opacity:0}}
@keyframes flow{to{stroke-dashoffset:-20}}
@keyframes spin{to{transform:rotate(360deg)}}
@keyframes float{50%{transform:translateY(-8px)}}
@keyframes scan{0%,100%{transform:translateY(0);opacity:0}15%,85%{opacity:.55}50%{transform:translateY(120px)}}
@keyframes glow{50%{opacity:.55}}
.drop{animation:drop 1.4s cubic-bezier(.3,1.35,.5,1) both}
.swing{animation:swing 6s ease-in-out infinite}
.sheen{animation:sheen 7s ease-in-out infinite}
@keyframes drop{from{transform:translateY(-140px);opacity:0}to{transform:none;opacity:1}}
@keyframes swing{0%,100%{transform:rotate(-1.6deg)}50%{transform:rotate(1.6deg)}}
@keyframes sheen{0%{transform:translateX(0)}45%,100%{transform:translateX(640px)}}
@media (prefers-reduced-motion:reduce){*{animation:none!important}}
"""

COMMON_DEFS = f"""
<linearGradient id="accentText" x1="0" y1="0" x2="0" y2="1">
<stop offset="0" stop-color="{ACCENT_PALE}"/><stop offset=".45" stop-color="{ACCENT}"/>
<stop offset="1" stop-color="#b8300c"/></linearGradient>
<linearGradient id="cardFill" x1="0" y1="0" x2="1" y2="1">
<stop offset="0" stop-color="#220c06"/><stop offset="1" stop-color="{CARD_2}"/></linearGradient>
<radialGradient id="glowAccent"><stop offset="0" stop-color="{ACCENT}" stop-opacity=".45"/>
<stop offset="1" stop-color="{ACCENT}" stop-opacity="0"/></radialGradient>
<radialGradient id="glowHot"><stop offset="0" stop-color="{HOT}" stop-opacity=".28"/>
<stop offset="1" stop-color="{HOT}" stop-opacity="0"/></radialGradient>
<pattern id="grid" width="32" height="32" patternUnits="userSpaceOnUse">
<path d="M32 0H0V32" fill="none" stroke="#ffffff" stroke-opacity=".035"/></pattern>
"""


def panel(svg: Svg, x, y, w, h, glow: str | None = None) -> None:
    clip = f"clip{len(svg.defs)}"
    svg.defs.append(f'<clipPath id="{clip}"><rect x="{x}" y="{y}" width="{w}" height="{h}" rx="22"/></clipPath>')
    svg.add(f'<g clip-path="url(#{clip})">')
    svg.add(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="url(#cardFill)"/>')
    svg.add(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="url(#grid)"/>')
    if glow == "accent":
        svg.add(f'<circle class="glow" cx="{x + w - 60}" cy="{y + 40}" r="320" fill="url(#glowAccent)"/>')
    elif glow == "hot":
        svg.add(f'<circle class="glow" cx="{x + 40}" cy="{y + h}" r="300" fill="url(#glowHot)"/>')
    svg.add("</g>")
    svg.add(
        f'<rect x="{x + .5}" y="{y + .5}" width="{w - 1}" height="{h - 1}" rx="22" '
        f'fill="none" stroke="{LINE}"/>'
    )
    svg.add(f'<path d="M{x + 28} {y + .5}h120" stroke="{ACCENT}" stroke-width="2"/>')


def section_head(svg: Svg, x, y, index: str, label: str, title: str, cls="rise") -> None:
    svg.text(x, y, f"{index} / {label.upper()}", MONO, 12, DIM, tracking=1.5, cls=cls)
    svg.text(x, y + 50, title.upper(), DISPLAY, 46, TEXT, tracking=.5, cls=f"{cls} d1")
    bar_y = y + 70
    svg.add(
        f'<g class="{cls} d2"><rect x="{x}" y="{bar_y}" width="96" height="3" rx="1.5" fill="{ACCENT}"/>'
        f'<rect x="{x + 104}" y="{bar_y}" width="40" height="3" rx="1.5" fill="{HOT}"/>'
        f'<rect x="{x + 152}" y="{bar_y}" width="120" height="3" rx="1.5" fill="{LINE}"/></g>'
    )


def slashes(svg: Svg, x, y, size=14, cls="") -> None:
    """The three slanted red bars used as a brand mark."""
    cls_attr = f' class="{cls}"' if cls else ""
    bars = "".join(
        f'<path d="M{x + i * size * .62:.1f} {y + size}l{size * .32:.1f} -{size}h{size * .3:.1f}'
        f'l-{size * .32:.1f} {size}z" fill="{HOT}"/>'
        for i in range(3)
    )
    svg.add(f"<g{cls_attr}>{bars}</g>")


ICONS = {
    "pin": '<path d="M8 1.5a5 5 0 0 0-5 5c0 3.6 5 8 5 8s5-4.4 5-8a5 5 0 0 0-5-5z"/><circle cx="8" cy="6.5" r="1.8"/>',
    "cap": '<path d="M1 6l7-3.5L15 6 8 9.5z"/><path d="M4 7.6v3.6c1 1 2.4 1.6 4 1.6s3-.6 4-1.6V7.6"/>',
    "cal": '<rect x="2" y="3" width="12" height="11" rx="2"/><path d="M2 7h12M5.5 1.5v3M10.5 1.5v3"/>',
    "git": '<circle cx="4" cy="3.5" r="1.8"/><circle cx="4" cy="12.5" r="1.8"/><circle cx="12" cy="6" r="1.8"/><path d="M4 5.3v5.4M12 7.8c0 2.5-3 2.7-6.6 3.7"/>',
    "server": '<rect x="2" y="2" width="16" height="6" rx="1.5"/><rect x="2" y="12" width="16" height="6" rx="1.5"/><path d="M5 5h.01M5 15h.01M9 5h6M9 15h6"/>',
    "graph": '<circle cx="10" cy="4" r="2.4"/><circle cx="4" cy="15" r="2.4"/><circle cx="16" cy="15" r="2.4"/><path d="M8.8 6.1L5.2 12.9M11.2 6.1l3.6 6.8M6.4 15h7.2"/>',
    "phone": '<rect x="5" y="1.5" width="10" height="17" rx="2.2"/><path d="M8.5 15.5h3"/>',
}


def icon(svg: Svg, name: str, x, y, scale=1.0, color=ACCENT_LIGHT) -> None:
    svg.add(
        f'<g transform="translate({x:g} {y:g}) scale({scale})" fill="none" stroke="{color}" '
        f'stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">{ICONS[name]}</g>'
    )


def frame(svg: Svg) -> None:
    svg.add(f'<rect width="{WIDTH}" height="{svg.height}" rx="26" fill="{BG}"/>')


# ---------------------------------------------------------------- hero
def build_hero() -> Svg:
    height = 600
    svg = Svg(height, "Dakshin Raj — hero",
              f"Hi, I'm Dakshin Raj. {ROLE}. {PITCH}")
    frame(svg)
    panel(svg, 0, 0, WIDTH, height, glow="accent")

    left = 64
    svg.text(left, 108, "Hi there, I'm", MONO, 18, ACCENT_PALE, cls="rise d1")
    svg.text(left - 4, 242, NAME_FIRST, DISPLAY, 156, TEXT, tracking=1, cls="rise d2")
    svg.text(left - 4, 378, NAME_LAST, DISPLAY, 156, "url(#accentText)", tracking=1, cls="rise d3")

    tag_x = left + text_width(NAME_LAST, DISPLAY, 156, 1) + 18
    slashes(svg, tag_x, 280, 16, cls="rise d4")
    svg.text(tag_x, 336, "BUILD.", DISPLAY, 32, TEXT, tracking=1, cls="rise d4")
    svg.text(tag_x, 370, "SHIP. REPEAT.", DISPLAY, 32, TEXT, tracking=1, cls="rise d4")

    svg.text(left, 436, ROLE, DISPLAY, 30, ACCENT_LIGHT, tracking=.6, cls="rise d5")
    svg.text(left, 470, PITCH, MONO, 15, MUTED, cls="rise d5")

    svg.add(f'<path class="rise d6" d="M{left} 512H652" stroke="{LINE}"/>')
    x = left
    for name, label in META:
        icon(svg, name, x, 535, 1.0, ACCENT_LIGHT)
        svg.text(x + 24, 548, label, MONO, 13, MUTED, cls="rise d6")
        x += 24 + text_width(label, MONO, 13) + 30

    draw_id_card(svg)
    return svg


PHOTO = ROOT / "tools" / "photo.webp"
PHOTO_FOCUS = (0.49, 0.40)  # centre of the face in the source image, as fractions
PHOTO_ZOOM = 1.18


def portrait_data_uri(w: int, h: int, scale: float = 2.0) -> str:
    """Crop the portrait around the face to the window's aspect, polish it, inline as JPEG."""
    im = Image.open(PHOTO).convert("RGB")
    src_w, src_h = im.size
    crop_w = min(src_w, src_h * w / h) / PHOTO_ZOOM
    crop_h = crop_w * h / w
    left = min(max(0, src_w * PHOTO_FOCUS[0] - crop_w / 2), src_w - crop_w)
    top = min(max(0, src_h * PHOTO_FOCUS[1] - crop_h / 2), src_h - crop_h)
    im = im.crop((round(left), round(top), round(left + crop_w), round(top + crop_h))).resize(
        (round(w * scale), round(h * scale)), Image.Resampling.LANCZOS)
    im = ImageEnhance.Contrast(im).enhance(1.06)
    im = ImageEnhance.Color(im).enhance(1.05)
    im = im.filter(ImageFilter.UnsharpMask(radius=1.4, percent=60, threshold=2))
    buffer = io.BytesIO()
    im.save(buffer, "JPEG", quality=80, optimize=True, progressive=True)
    return "data:image/jpeg;base64," + base64.b64encode(buffer.getvalue()).decode("ascii")


def float_chip(svg: Svg, label: str, cx, cy, accent: str, delay: float) -> None:
    w = text_width(label, MONO_BOLD, 12, 1.2) + 30
    x, y = cx - w / 2, cy - 16
    svg.add(f'<g class="float" style="animation-delay:-{delay:.1f}s">'
            f'<rect x="{x:.1f}" y="{y}" width="{w:.1f}" height="32" rx="9" fill="#1c0a05" '
            f'fill-opacity=".9" stroke="{accent}" stroke-opacity=".85"/>'
            f'<circle cx="{x + 11:.1f}" cy="{cy}" r="2.5" fill="{accent}"/>')
    svg.text(x + 20, cy + 4.5, label, MONO_BOLD, 12, TEXT, tracking=1.2)
    svg.add("</g>")


CARD_BOX = (776, 72, 344, 486)  # x, y, w, h of the badge at rest
SWING_PIVOT_Y = -40  # lanyard hangs from above the card's top edge
COMPANY = "MinoriLabs"
STRAP_LABEL = "DR·10"  # short enough to clear the metal clip


def emv_chip(svg: Svg, x, y) -> None:
    svg.add(f'<rect x="{x}" y="{y}" width="54" height="42" rx="8" fill="url(#chipGold)" '
            f'stroke="#8a5a1c" stroke-opacity=".7"/>'
            f'<path d="M{x} {y + 14}h16v14h-16M{x + 54} {y + 14}h-16v14h16M{x + 16} {y + 21}h22'
            f'M{x + 27} {y}v14M{x + 27} {y + 28}v14" fill="none" stroke="#7a4d14" stroke-opacity=".75"/>')


def draw_id_card(svg: Svg) -> None:
    """Swinging builder badge on a lanyard, with the portrait in its window."""
    x, y, w, h = CARD_BOX
    cx = x + w / 2
    win_x, win_y, win_w, win_h = x + 20, y + 70, w - 40, 252
    svg.defs.append(
        f'<clipPath id="cardClip"><rect x="{x}" y="{y}" width="{w}" height="{h}" rx="22"/></clipPath>'
        f'<clipPath id="winClip"><rect x="{win_x}" y="{win_y}" width="{win_w}" height="{win_h}" rx="14"/></clipPath>'
        f'<linearGradient id="badgeFill" x1="0" y1="0" x2="0" y2="1">'
        f'<stop offset="0" stop-color="#2b1009"/><stop offset="1" stop-color="#140604"/></linearGradient>'
        f'<linearGradient id="strap" x1="0" y1="0" x2="1" y2="0">'
        f'<stop offset="0" stop-color="#b8300c"/><stop offset=".5" stop-color="{ACCENT}"/>'
        f'<stop offset="1" stop-color="#b8300c"/></linearGradient>'
        f'<linearGradient id="metal" x1="0" y1="0" x2="1" y2="1">'
        f'<stop offset="0" stop-color="#f4ece6"/><stop offset=".5" stop-color="#a99d95"/>'
        f'<stop offset="1" stop-color="#6d625c"/></linearGradient>'
        f'<linearGradient id="chipGold" x1="0" y1="0" x2="1" y2="1">'
        f'<stop offset="0" stop-color="#f3d38c"/><stop offset="1" stop-color="#b8863a"/></linearGradient>'
        f'<linearGradient id="sheen" x1="0" y1="0" x2="1" y2="0">'
        f'<stop offset="0" stop-color="#fff" stop-opacity="0"/><stop offset=".5" stop-color="#fff" '
        f'stop-opacity=".09"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient>'
        f'<linearGradient id="winFade" x1="0" y1="0" x2="0" y2="1">'
        f'<stop offset=".7" stop-color="#140604" stop-opacity="0"/>'
        f'<stop offset="1" stop-color="#140604" stop-opacity=".7"/></linearGradient>'
        f'<pattern id="badgeStripes" width="9" height="9" patternUnits="userSpaceOnUse" '
        f'patternTransform="rotate(45)"><path d="M0 0V9" stroke="#fff" stroke-opacity=".03" stroke-width="3"/></pattern>'
        f'<filter id="badgeShadow" x="-30%" y="-20%" width="160%" height="150%">'
        f'<feDropShadow dx="0" dy="22" stdDeviation="20" flood-color="#000" flood-opacity=".6"/></filter>'
    )

    # backdrop: glow and orbit rings centred on the badge
    ring_cy = y + h / 2
    svg.add(f'<circle class="glow" cx="{x - 20}" cy="{ring_cy - 60}" r="260" fill="url(#glowAccent)"/>')
    for r, cls, dash in ((300, "spin", "2 10"), (262, "spin-rev", "1 6")):
        svg.add(f'<g style="transform-origin:{cx}px {ring_cy}px" class="{cls} rise d2">'
                f'<circle cx="{cx}" cy="{ring_cy}" r="{r}" fill="none" stroke="{ACCENT}" '
                f'stroke-opacity=".35" stroke-dasharray="{dash}"/>'
                f'<circle cx="{cx - r}" cy="{ring_cy}" r="3.5" fill="{ACCENT_LIGHT}"/></g>')

    svg.add('<g class="drop">')
    svg.add(f'<g class="swing" style="transform-origin:{cx}px {SWING_PIVOT_Y}px">')

    # lanyard strap + metal clip
    strap_w = 36
    svg.add(f'<rect x="{cx - strap_w / 2}" y="-10" width="{strap_w}" height="{y + 2 + 10}" '
            f'fill="url(#strap)"/>'
            f'<path d="M{cx - strap_w / 2 + 4} -10V{y}M{cx + strap_w / 2 - 4} -10V{y}" '
            f'stroke="#fff" stroke-opacity=".18" stroke-dasharray="2 3"/>')
    svg.text(cx + 4, 6, STRAP_LABEL, MONO_BOLD, 9.5, "#2a0a03", tracking=1.6,
             extra=f'transform="rotate(90 {cx + 4} 6)"')
    svg.add(f'<rect x="{cx - 21}" y="{y - 30}" width="42" height="30" rx="7" fill="url(#metal)" '
            f'stroke="#5c524c" stroke-width=".8"/>'
            f'<rect x="{cx - 10}" y="{y - 22}" width="20" height="12" rx="3" fill="{BG}"/>'
            f'<rect x="{cx - 7}" y="{y - 4}" width="14" height="22" rx="4" fill="url(#metal)" '
            f'stroke="#5c524c" stroke-width=".8"/>')

    # badge body
    svg.add(f'<g filter="url(#badgeShadow)"><rect x="{x}" y="{y}" width="{w}" height="{h}" rx="22" '
            f'fill="url(#badgeFill)"/></g>')
    svg.add(f'<g clip-path="url(#cardClip)">'
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="url(#badgeStripes)"/>'
            f'<rect x="{x}" y="{y}" width="{w}" height="5" fill="{HOT}"/>'
            f'<g transform="rotate(14 {cx} {y + h / 2})"><rect class="sheen" x="{x - 220}" y="{y - 40}" '
            f'width="140" height="{h + 80}" fill="url(#sheen)"/></g></g>'
            f'<rect x="{x + .5}" y="{y + .5}" width="{w - 1}" height="{h - 1}" rx="22" fill="none" '
            f'stroke="{SAND}" stroke-opacity=".45"/>'
            f'<rect x="{cx - 28}" y="{y + 16}" width="56" height="9" rx="4.5" fill="{BG}" '
            f'stroke="{LINE}"/>')

    svg.text(x + 24, y + 54, "DR / BUILDER PASS", DISPLAY, 21, TEXT, tracking=.8)
    svg.text(x + w - 24, y + 54, "#0010", MONO, 15, ACCENT_LIGHT, anchor="end")

    # portrait window with role tag
    svg.add(f'<g clip-path="url(#winClip)"><rect x="{win_x}" y="{win_y}" width="{win_w}" height="{win_h}" '
            f'fill="#1c0905"/>'
            f'<image href="{portrait_data_uri(win_w, win_h)}" x="{win_x}" y="{win_y}" width="{win_w}" '
            f'height="{win_h}" preserveAspectRatio="xMidYMid slice"/>'
            f'<rect x="{win_x}" y="{win_y}" width="{win_w}" height="{win_h}" fill="url(#winFade)"/>'
            f'<rect class="scan" x="{win_x}" y="{win_y + 20}" width="{win_w}" height="2" '
            f'fill="{ACCENT_PALE}" opacity="0"/></g>'
            f'<rect x="{win_x + .5}" y="{win_y + .5}" width="{win_w - 1}" height="{win_h - 1}" rx="14" '
            f'fill="none" stroke="{SAND}" stroke-opacity=".35"/>')
    role = "AI ENGINEER INTERN"
    role_w = text_width(role, MONO_BOLD, 11, 1.5) + 28
    svg.add(f'<rect x="{win_x + 12}" y="{win_y + win_h - 42}" width="{role_w:.1f}" height="28" rx="7" '
            f'fill="{ACCENT}"/>')
    svg.text(win_x + 26, win_y + win_h - 23.5, role, MONO_BOLD, 11, "#1a0905", tracking=1.5)

    # identity block
    svg.text(x + 24, y + 372, "DAKSHIN RAJ", DISPLAY, 40, TEXT, tracking=1)
    svg.text(x + 24, y + 396, "COIMBATORE / INDIA", MONO, 10.5, MUTED, tracking=1.4)
    emv_chip(svg, x + w - 24 - 54, y + 340)
    svg.add(f'<path d="M{x + 24} {y + 414}H{x + w - 24}" stroke="{LINE}" stroke-dasharray="2 4"/>')
    svg.text(x + 24, y + 440, "CURRENTLY AT", MONO, 9.5, DIM, tracking=1.6)
    svg.text(x + 24, y + 468, COMPANY.upper(), DISPLAY, 26, "url(#accentText)", tracking=1)
    status = "ACTIVE"
    pill_w = text_width(status, MONO_BOLD, 9.5, 1.4) + 30
    px = x + w - 24 - pill_w
    svg.add(f'<rect x="{px:.1f}" y="{y + 446}" width="{pill_w:.1f}" height="24" rx="12" fill="#2a0f07" '
            f'stroke="{ACCENT}" stroke-opacity=".6"/>'
            f'<circle cx="{px + 12:.1f}" cy="{y + 458}" r="3" fill="#3ddc97"/>'
            f'<circle class="pulse" cx="{px + 12:.1f}" cy="{y + 458}" r="3" fill="#3ddc97"/>')
    svg.text(px + 21, y + 461.5, status, MONO_BOLD, 9.5, ACCENT_PALE, tracking=1.4)

    svg.add("</g></g>")

    # agent chips floating beside the badge
    svg.add('<g class="rise d5">')
    for i, (chip_label, chip_y, accent) in enumerate((("LLM", 170, HOT), ("RAG", 300, ACCENT), ("MCP", 430, ACCENT))):
        float_chip(svg, chip_label, x - 52, chip_y, accent, i * 1.3)
    svg.add("</g>")


# ---------------------------------------------------------------- about
def build_about() -> Svg:
    height = 610
    svg = Svg(height, "Dakshin Raj — about",
              "What I build: backend engineering, agentic AI and Flutter apps. "
              "whoami: B.Tech CSE at Amrita, 3rd year, Coimbatore. "
              "Motto: code with intention, build with impact.")
    frame(svg)
    half = 588
    panel(svg, 0, 0, half, height, glow="accent")
    panel(svg, WIDTH - half, 0, half, height, glow="hot")
    build_about_left(svg, 0, half)
    build_about_right(svg, WIDTH - half, half)
    return svg


def build_about_left(svg: Svg, x0, w) -> None:
    x = x0 + 36
    section_head(svg, x, 52, "01", "from prompt to production", "Systems, not just CRUD.")

    tx, ty, tw, th = x, 150, w - 72, 172
    dots = "".join(f'<circle cx="{tx + 18 + i * 14}" cy="{ty + 16}" r="4" fill="{c}"/>'
                   for i, c in enumerate((HOT, ACCENT_LIGHT, LINE)))
    svg.add(f'<g class="rise d3"><rect x="{tx}" y="{ty}" width="{tw}" height="{th}" rx="14" '
            f'fill="#140604" stroke="{LINE}"/><path d="M{tx} {ty + 32}h{tw}" stroke="{LINE}"/>{dots}')
    svg.text(tx + 70, ty + 20, "github.com / dakshin10 / build", MONO, 11, DIM)
    svg.spans(tx + 18, ty + 62, [("> ", HOT), ("turn_ideas_into_agents()", TEXT)], MONO, 14)
    cursor_x = tx + 18 + text_width("> turn_ideas_into_agents()", MONO, 14) + 6
    svg.add(f'<rect class="blink" x="{cursor_x:.1f}" y="{ty + 50}" width="8" height="15" fill="{ACCENT}"/>')

    steps = [("01", "DESIGN", ACCENT), ("02", "ORCHESTRATE", ACCENT), ("03", "SHIP", HOT)]
    gap = 26
    box_w = (tw - 36 - gap * 2) / 3
    for i, (num, label, color) in enumerate(steps):
        bx = tx + 18 + i * (box_w + gap)
        by = ty + 86
        svg.add(f'<rect x="{bx:.1f}" y="{by}" width="{box_w:.1f}" height="68" rx="8" '
                f'fill="{color}" fill-opacity=".08" stroke="{color}" stroke-opacity=".8"/>')
        svg.text(bx + 12, by + 32, num, DISPLAY, 26, ACCENT_LIGHT if color == ACCENT else HOT)
        svg.text(bx + 12, by + 54, label, MONO_BOLD, 10.5, TEXT, tracking=1.4)
        if i < 2:
            ax = bx + box_w + 6
            svg.add(f'<path d="M{ax:.1f} {by + 34}h{gap - 12}m-4 -4l4 4l-4 4" fill="none" '
                    f'stroke="{DIM}" stroke-width="1.4"/>')
    svg.add(f'<rect class="scan" x="{tx + 1}" y="{ty + 34}" width="{tw - 2}" height="2" fill="{ACCENT}" opacity="0"/>')
    svg.add("</g>")

    y = 366
    for i, (name, title, sub) in enumerate(FOCUS):
        svg.add(f'<g class="rise d{4 + i}">')
        svg.add(f'<rect x="{x}" y="{y}" width="44" height="44" rx="11" fill="#2a0f07" stroke="{LINE}"/>')
        icon(svg, name, x + 12, y + 12, 1.0, ACCENT_LIGHT)
        svg.text(x + 62, y + 20, title, DISPLAY, 24, TEXT, tracking=.5)
        svg.text(x + 62, y + 40, sub, MONO, 12, MUTED)
        if i < len(FOCUS) - 1:
            svg.add(f'<path d="M{x} {y + 64}H{x0 + w - 36}" stroke="{LINE}" stroke-dasharray="2 4"/>')
        svg.add("</g>")
        y += 76


TOKEN = re.compile(r'("[^"]*")|(\bconst\b)|(\bDeveloper\b)|(\b\w+\b)(?=\s*:)|(\w+)|(\s+)|(.)')


def highlight(line: str) -> list[tuple[str, str]]:
    """Tiny TypeScript-ish syntax colouring for the whoami block."""
    runs = []
    for m in TOKEN.finditer(line):
        string, keyword, type_, key, word, space, punct = m.groups()
        if string:
            runs.append((string, ACCENT_PALE))
        elif keyword:
            runs.append((keyword, HOT))
        elif type_:
            runs.append((type_, ACCENT))
        elif key:
            runs.append((key, MUTED if line.startswith("  ") else TEXT))
        elif word or space:
            runs.append((word or space, TEXT))
        else:
            runs.append((punct, DIM))
    return runs


def build_about_right(svg: Svg, x0, w) -> None:
    x = x0 + 36
    svg.text(x, 52, "02 / CAT WHOAMI.TS", MONO, 12, DIM, tracking=1.5, cls="rise")
    svg.add(f'<g class="rise d1"><rect x="{x}" y="70" width="96" height="3" rx="1.5" fill="{ACCENT}"/>'
            f'<rect x="{x + 104}" y="70" width="40" height="3" rx="1.5" fill="{HOT}"/>'
            f'<rect x="{x + 152}" y="70" width="120" height="3" rx="1.5" fill="{LINE}"/></g>')

    cx, cy, cw = x, 100, w - 72
    line_h = 27
    ch = 52 + line_h * len(WHOAMI)
    svg.add(f'<g class="rise d3"><rect x="{cx}" y="{cy}" width="{cw}" height="{ch}" rx="14" '
            f'fill="#140604" stroke="{LINE}"/><path d="M{cx} {cy + 32}h{cw}" stroke="{LINE}"/>')
    svg.text(cx + 18, cy + 21, "whoami.ts", MONO_BOLD, 11, ACCENT_PALE, tracking=.6)
    svg.text(cx + cw - 18, cy + 21, "TS", MONO_BOLD, 11, DIM, anchor="end")
    for i, line in enumerate(WHOAMI):
        ly = cy + 60 + i * line_h
        svg.text(cx + 18, ly, f"{i + 1}", MONO, 12, LINE)
        svg.spans(cx + 46, ly, highlight(line), MONO, 14)
    svg.add("</g>")

    my = cy + ch + 66
    svg.text(x, my, "MAKE THE NEXT MOVE.", MONO, 12, DIM, tracking=1.5, cls="rise d5")
    svg.text(x, my + 50, "Code with intention.", DISPLAY, 44, TEXT, tracking=.5, cls="rise d6")
    svg.text(x, my + 96, "Build with impact.", DISPLAY, 44, "url(#accentText)", tracking=.5, cls="rise d7")
    slashes(svg, x0 + w - 84, my + 74, 16, cls="rise d8")


# ---------------------------------------------------------------- stack
# The stack is drawn as the system it builds: client -> API -> agent core -> data,
# running on the language runtime, inside the cloud/tooling boundary.
ICONS.update({
    "db": '<ellipse cx="10" cy="4.5" rx="7" ry="2.5"/><path d="M3 4.5v11c0 1.4 3.1 2.5 7 2.5s7-1.1 7-2.5v-11M3 10c0 1.4 3.1 2.5 7 2.5s7-1.1 7-2.5"/>',
    "plug": '<path d="M7 2v4M13 2v4M5 6h10v3a5 5 0 0 1-10 0zM10 14v4"/>',
    "code": '<path d="M7 5l-5 5 5 5M13 5l5 5-5 5"/>',
})

CHIP_SIZE = 12.5
CHIP_H = 30
CHIP_PAD = 12
CHIP_GAP = 8
MOD_HEAD = 62
MOD_PAD = 14
ROW_H = 28
ROW_GAP = 6


def chip_width(label: str, size: float = CHIP_SIZE) -> float:
    return text_width(label, MONO, size) + CHIP_PAD * 2 + 12


def layout_chips(labels: list[str], max_w: float) -> list[list[tuple[str, float]]]:
    rows: list[list[tuple[str, float]]] = [[]]
    used = 0.0
    for label in labels:
        cw = chip_width(label)
        if rows[-1] and used + cw > max_w:
            rows.append([])
            used = 0.0
        rows[-1].append((label, cw))
        used += cw + CHIP_GAP
    return rows


def chip(svg: Svg, x, y, label: str, lead: bool, size: float = CHIP_SIZE, h: int = CHIP_H,
         fill: str = "#180805") -> float:
    w = chip_width(label, size)
    svg.add(f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h}" rx="8" '
            f'fill="{"#2a0f07" if lead else fill}" stroke="{ACCENT if lead else LINE}"/>'
            f'<circle cx="{x + CHIP_PAD:.1f}" cy="{y + h / 2:.1f}" r="2.8" '
            f'fill="{ACCENT if lead else DIM}"/>')
    svg.text(x + CHIP_PAD + 10, y + h / 2 + size * .36, label, MONO, size, TEXT if lead else ACCENT_PALE)
    return w


def body_height(items: list[str], w: float, mode: str) -> float:
    if mode == "list":
        return len(items) * ROW_H + (len(items) - 1) * ROW_GAP
    rows = layout_chips(items, w - MOD_PAD * 2)
    return len(rows) * CHIP_H + (len(rows) - 1) * CHIP_GAP


def module_height(items: list[str], w: float, mode: str = "list") -> float:
    return MOD_HEAD + body_height(items, w, mode) + MOD_PAD


def module_frame(svg: Svg, x, y, w, h, title: str, tag: str, index: str,
                 icon_name: str | None, core: bool = False) -> None:
    svg.add(f'<rect x="{x}" y="{y:.1f}" width="{w}" height="{h:.1f}" rx="14" '
            f'fill="{"#200a05" if core else "#150705"}" fill-opacity=".94" '
            f'stroke="{ACCENT if core else LINE}" stroke-opacity="{.75 if core else 1}"/>')
    tx = x + MOD_PAD
    if icon_name:
        svg.add(f'<rect x="{tx}" y="{y + 13:.1f}" width="32" height="32" rx="9" fill="#2a0f07" stroke="{LINE}"/>')
        icon(svg, icon_name, tx + 6, y + 19, .95, ACCENT_LIGHT)
        tx += 44
    svg.text(tx, y + 30, title.upper(), DISPLAY, 20, TEXT, tracking=.7)
    svg.text(tx, y + 45, tag.upper(), MONO, 9.5, DIM, tracking=1.2)
    if core:
        pill_w = text_width("LIVE", MONO_BOLD, 9.5, 1.2) + 26
        px = x + w - MOD_PAD - pill_w
        svg.add(f'<rect x="{px:.1f}" y="{y + 15:.1f}" width="{pill_w:.1f}" height="20" rx="10" '
                f'fill="#2a0f07" stroke="{ACCENT}" stroke-opacity=".6"/>'
                f'<circle cx="{px + 10:.1f}" cy="{y + 25:.1f}" r="3" fill="{ACCENT}"/>'
                f'<circle class="pulse" cx="{px + 10:.1f}" cy="{y + 25:.1f}" r="3" fill="{ACCENT}"/>')
        svg.text(px + 18, y + 28.5, "LIVE", MONO_BOLD, 9.5, ACCENT_PALE, tracking=1.2)
    else:
        title_end = tx + text_width(title.upper(), DISPLAY, 20, .7)
        if title_end < x + w - MOD_PAD - 24:  # only when the title leaves room
            svg.text(x + w - MOD_PAD, y + 28, index, MONO_BOLD, 11, DIM, anchor="end")
    svg.add(f'<path d="M{x + MOD_PAD} {y + 54:.1f}H{x + w - MOD_PAD}" stroke="{LINE}" stroke-dasharray="2 4"/>')


def module_body(svg: Svg, x, y, w, items: list[str], mode: str) -> None:
    top = y + MOD_HEAD
    if mode == "list":
        for i, item in enumerate(items):
            ry = top + i * (ROW_H + ROW_GAP)
            lead = i == 0
            svg.add(f'<rect x="{x + MOD_PAD}" y="{ry:.1f}" width="{w - MOD_PAD * 2}" height="{ROW_H}" rx="7" '
                    f'fill="{"#2a0f07" if lead else "#1b0905"}" stroke="{ACCENT if lead else LINE}" '
                    f'stroke-opacity="{.8 if lead else .7}"/>'
                    f'<rect x="{x + MOD_PAD + 10}" y="{ry + ROW_H / 2 - 2.5:.1f}" width="5" height="5" rx="1" '
                    f'fill="{ACCENT if lead else DIM}"/>')
            svg.text(x + MOD_PAD + 24, ry + 18.5, item, MONO, CHIP_SIZE, TEXT if lead else ACCENT_PALE)
        return
    for r, row in enumerate(layout_chips(items, w - MOD_PAD * 2)):
        cx = x + MOD_PAD
        for c, (label, cw) in enumerate(row):
            chip(svg, cx, top + r * (CHIP_H + CHIP_GAP), label, lead=r == 0 and c == 0)
            cx += cw + CHIP_GAP


def module(svg: Svg, x, y, w, title, tag, index, items, icon_name, mode="list") -> float:
    h = module_height(items, w, mode)
    module_frame(svg, x, y, w, h, title, tag, index, icon_name)
    module_body(svg, x, y, w, items, mode)
    return h


def wire(svg: Svg, x1, y1, x2, y2, label: str, color: str, delay: float) -> None:
    """Curved connector with a flowing dash, a travelling packet and port dots."""
    mx = (x1 + x2) / 2
    d = f"M{x1:.1f} {y1:.1f}C{mx:.1f} {y1:.1f} {mx:.1f} {y2:.1f} {x2:.1f} {y2:.1f}"
    svg.add(f'<path d="{d}" fill="none" stroke="{LINE}" stroke-width="3"/>'
            f'<path class="flow" d="{d}" fill="none" stroke="{color}" stroke-opacity=".75" stroke-width="1.4"/>'
            f'<circle r="3.6" fill="{color}"><animateMotion dur="2.4s" begin="-{delay:.1f}s" '
            f'repeatCount="indefinite" path="{d}"/></circle>')
    for px, py in ((x1, y1), (x2, y2)):
        svg.add(f'<circle cx="{px:.1f}" cy="{py:.1f}" r="4" fill="{BG}" stroke="{color}" stroke-width="1.5"/>')
    svg.text(mx, min(y1, y2) - 8, label, MONO, 9.5, MUTED, anchor="middle", tracking=.6)


def build_stack() -> Svg:
    stack = dict(STACK)
    left, right = 44, WIDTH - 44
    lanes = [192, 184, 384, 200]
    lane_gap = (right - left - sum(lanes)) / (len(lanes) - 1)
    xs = [left]
    for w in lanes[:-1]:
        xs.append(xs[-1] + w + lane_gap)
    (x1, x2, x3, x4), (w1, w2, w3, w4) = xs, lanes

    # agent core is the tallest lane; everything else centres on it
    sub_w = (w3 - MOD_PAD * 2 - 12) / 2
    agentic_h = body_height(stack["Agentic AI"], w3, "wrap")
    subs_h = max(module_height(stack["LLMs"], sub_w), module_height(stack["RAG & Doc AI"], sub_w))
    core_h = MOD_HEAD + agentic_h + 14 + subs_h + MOD_PAD
    y0 = 214
    runtime_y = y0 + core_h + 44
    runtime_h = 58
    boundary_top, boundary_bottom = 166, runtime_y + runtime_h + 22
    height = int(boundary_bottom + 30)

    every = "; ".join(f"{cat}: {', '.join(items)}" for cat, items in STACK)
    svg = Svg(height, "Dakshin Raj — tech stack",
              f"My stack drawn as a system map: client, API, agent core and data layers on a "
              f"language runtime inside cloud infrastructure. {every}.")
    frame(svg)
    panel(svg, 0, 0, WIDTH, height, glow="accent")
    svg.add(f'<circle class="glow" cx="{x3 + w3 / 2}" cy="{y0 + core_h / 2}" r="320" fill="url(#glowAccent)"/>')
    section_head(svg, left, 52, "03", "system map · ls ./tech-stack", "The stack, wired up.")
    total = sum(len(items) for _, items in STACK)
    svg.text(right, 52, f"{total} tools · {len(STACK)} domains · 1 system", MONO, 12, DIM, anchor="end", cls="rise")
    svg.add(f'<g class="rise d2"><circle cx="{right - 150}" cy="97" r="4" fill="{ACCENT}"/>'
            f'<circle cx="{right - 62}" cy="97" r="4" fill="{HOT}"/></g>')
    svg.text(right - 140, 101, "request", MONO, 11, MUTED, cls="rise d2")
    svg.text(right - 52, 101, "response", MONO, 11, MUTED, cls="rise d2")

    # infra boundary with cloud & tooling riding its top edge
    svg.add(f'<rect class="rise d1" x="26" y="{boundary_top}" width="{WIDTH - 52}" '
            f'height="{boundary_bottom - boundary_top:.1f}" rx="20" fill="none" stroke="{SAND}" '
            f'stroke-opacity=".35" stroke-dasharray="6 6"/>')
    svg.add('<g class="rise d2">')
    label = "INFRA / CLOUD & TOOLING"
    label_w = text_width(label, MONO_BOLD, 11, 1.4) + 24
    svg.add(f'<rect x="{left}" y="{boundary_top - 13}" width="{label_w:.1f}" height="26" rx="13" fill="{BG}" '
            f'stroke="{SAND}" stroke-opacity=".5"/>')
    svg.text(left + 12, boundary_top + 4, label, MONO_BOLD, 11, SAND, tracking=1.4)
    cx = left + label_w + 10
    for i, item in enumerate(stack["Cloud & Tooling"]):
        cx += chip(svg, cx, boundary_top - 13, item, lead=i == 0, size=11.5, h=26, fill=BG) + 8
    svg.add("</g>")

    for i, (lx, caption) in enumerate(zip(xs, ("Client", "API", "Agent core", "Data"))):
        svg.text(lx, y0 - 14, f"L{i + 1} · {caption.upper()}", MONO_BOLD, 10, DIM, tracking=1.6, cls="rise d2")

    # L1 client: mobile + integrations
    mob_h = module_height(stack["Mobile"], w1)
    int_h = module_height(stack["Integrations"], w1)
    client_y = y0 + (core_h - mob_h - 18 - int_h) / 2
    int_y = client_y + mob_h + 18
    svg.add('<g class="rise d3">')
    module(svg, x1, client_y, w1, "Mobile", "layer · client", "02", stack["Mobile"], "phone")
    module(svg, x1, int_y, w1, "Integrations", "io · events", "08", stack["Integrations"], "plug")
    svg.add("</g>")

    # L2 api
    be_h = module_height(stack["Backend"], w2)
    be_y = y0 + (core_h - be_h) / 2
    svg.add('<g class="rise d4">')
    module(svg, x2, be_y, w2, "Backend", "layer · api", "03", stack["Backend"], "server")
    svg.add("</g>")

    # L3 agent core: agentic chips + LLM and RAG sub-modules
    svg.add('<g class="rise d5">')
    module_frame(svg, x3, y0, w3, core_h, "Agentic AI", "layer · agent core", "05", "graph", core=True)
    module_body(svg, x3, y0, w3, stack["Agentic AI"], "wrap")
    sub_y = y0 + MOD_HEAD + agentic_h + 14
    for i, (name, tag, idx) in enumerate((("LLMs", "models", "06"), ("RAG & Doc AI", "retrieval", "07"))):
        module(svg, x3 + MOD_PAD + i * (sub_w + 12), sub_y, sub_w, name, tag, idx, stack[name], None)
    svg.add("</g>")

    # L4 data
    db_h = module_height(stack["Databases"], w4)
    db_y = y0 + (core_h - db_h) / 2
    svg.add('<g class="rise d6">')
    module(svg, x4, db_y, w4, "Databases", "layer · data", "04", stack["Databases"], "db")
    svg.add("</g>")

    be_mid, core_mid, db_mid = be_y + be_h / 2, y0 + core_h / 2, db_y + db_h / 2
    svg.add('<g class="rise d7">')
    wire(svg, x1 + w1, client_y + mob_h / 2, x2, be_mid - 46, "HTTPS", ACCENT, 0)
    wire(svg, x1 + w1, int_y + int_h / 2, x2, be_mid + 46, "WS/MQTT", ACCENT, .8)
    wire(svg, x2 + w2, be_mid - 30, x3, core_mid - 60, "invoke", ACCENT, .4)
    wire(svg, x3, core_mid + 20, x2 + w2, be_mid + 30, "stream", HOT, 1.2)
    wire(svg, x3 + w3, core_mid - 50, x4, db_mid - 40, "query", ACCENT, .2)
    wire(svg, x4, db_mid + 40, x3 + w3, core_mid + 30, "rows", HOT, 1.0)
    svg.add("</g>")

    # runtime strip: every lane runs on the languages
    svg.add('<g class="rise d8">')
    for lx, lane_w in zip(xs, lanes):
        mid = lx + lane_w / 2
        svg.add(f'<path d="M{mid} {y0 + core_h + 8:.1f}V{runtime_y - 6:.1f}" stroke="{DIM}" stroke-dasharray="2 4"/>'
                f'<path d="M{mid - 4} {runtime_y - 10:.1f}l4 4l4 -4" fill="none" stroke="{DIM}"/>')
    svg.add(f'<rect x="{left}" y="{runtime_y:.1f}" width="{right - left}" height="{runtime_h}" rx="14" '
            f'fill="#150705" stroke="{LINE}"/>'
            f'<rect x="{left + 14}" y="{runtime_y + 13:.1f}" width="32" height="32" rx="9" fill="#2a0f07" stroke="{LINE}"/>')
    icon(svg, "code", left + 20, runtime_y + 19, .95, ACCENT_LIGHT)
    svg.text(left + 58, runtime_y + 28, "LANGUAGES", DISPLAY, 20, TEXT, tracking=.7)
    svg.text(left + 58, runtime_y + 43, "RUNTIME · 01", MONO, 9.5, DIM, tracking=1.2)
    cx = left + 200
    for i, item in enumerate(stack["Languages"]):
        cx += chip(svg, cx, runtime_y + 14, item, lead=i == 0) + CHIP_GAP
    svg.add("</g>")
    return svg


# ---------------------------------------------------------------- connect
def build_connect() -> Svg:
    height = 372
    links = ", ".join(f"{kind.title()}: {value}" for kind, value in CONNECT)
    svg = Svg(height, "Dakshin Raj — connect",
              f"Let's build what's next. {links}. Clickable links are listed below this card.")
    frame(svg)
    panel(svg, 0, 0, WIDTH, height, glow="hot")
    svg.add(f'<circle class="glow" cx="{WIDTH - 80}" cy="0" r="300" fill="url(#glowAccent)"/>')
    x = 44
    section_head(svg, x, 52, "04", "ping dakshin --connect", "Let's build what's next.")
    svg.text(x, 178, "Working on something ambitious — agents, backends, real-time apps?",
             MONO, 15, MUTED, cls="rise d3")
    svg.text(x, 202, "I'm always up for a good problem.", MONO, 15, MUTED, cls="rise d3")
    slashes(svg, WIDTH - 104, 48, 16, cls="rise d2")

    gap = 20
    card_w = (WIDTH - x * 2 - gap * 2) / 3
    for i, (kind, value) in enumerate(CONNECT):
        cx, cy = x + i * (card_w + gap), 240
        accent = HOT if i == 1 else ACCENT
        svg.add(f'<g class="rise d{4 + i}"><rect x="{cx:.1f}" y="{cy}" width="{card_w:.1f}" height="92" '
                f'rx="14" fill="#180805" stroke="{LINE}"/>'
                f'<rect x="{cx:.1f}" y="{cy + 22}" width="3" height="48" rx="1.5" fill="{accent}"/>')
        svg.text(cx + 24, cy + 38, kind, DISPLAY, 24, TEXT, tracking=1.2)
        size = 13.0
        while text_width(value, MONO, size) > card_w - 70 and size > 10:
            size -= .5
        svg.text(cx + 24, cy + 64, value, MONO, size, ACCENT_PALE)
        ax, ay = cx + card_w - 30, cy + 30
        svg.add(f'<path d="M{ax - 8:.1f} {ay + 8}l8 -8m-6 0h6v6" fill="none" stroke="{accent}" '
                f'stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></g>')
    return svg


def main() -> None:
    OUT_DIR.mkdir(exist_ok=True)
    builders = {"hero": build_hero, "about": build_about, "stack": build_stack, "connect": build_connect}
    for name, build in builders.items():
        markup = build().render()
        path = OUT_DIR / f"{name}.svg"
        path.write_text(markup, encoding="utf-8")
        print(f"{path.relative_to(ROOT)}  {len(markup) / 1024:.0f} KB")


if __name__ == "__main__":
    main()
