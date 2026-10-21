"""Shared palette, fonts and card chrome for the profile SVGs."""

import math
from xml.sax.saxutils import escape

BLUE = "#2F7BFF"
CYAN = "#00D4FF"
ICE = "#A8ECFF"
SKY = "#7DB9FF"
GOLD = "#F5C451"

CARD = "#070C18"
PANEL = "#0C1426"
INK = "#E6EDF3"
MUTED = "#8A97B0"
DIM = "#4D5B78"

MONO = "'JetBrains Mono','Fira Code','SF Mono','SFMono-Regular',Menlo,Consolas,'Liberation Mono',monospace"
SANS = "'Inter','Segoe UI',-apple-system,BlinkMacSystemFont,'Helvetica Neue',Arial,sans-serif"

# Electric blue -> cyan -> ice gradient used across every card.
GRAD_STOPS = (
    f'<stop offset="0" stop-color="{BLUE}"/>'
    f'<stop offset=".55" stop-color="{CYAN}"/>'
    f'<stop offset="1" stop-color="{ICE}"/>'
)

BASE_CSS = """
.au1{animation:au1 18s ease-in-out infinite alternate}
.au2{animation:au2 23s ease-in-out infinite alternate}
@keyframes au1{to{transform:translate(70px,26px)}}
@keyframes au2{to{transform:translate(-90px,-24px)}}
.pulse{animation:pulse 2s ease-in-out infinite}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:.25}}
"""


def esc(text):
    return escape(str(text), {'"': "&quot;"})


def pts(*points):
    return " ".join(f"{x:.1f},{y:.1f}" for x, y in points)


def svg(width, height, title, body, css=""):
    """Wrap body in a standalone SVG document with the shared base styles."""
    return f"""<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="{esc(title)}">
<title>{esc(title)}</title>
<style>
text{{font-family:{SANS};font-variant-ligatures:none;font-feature-settings:"liga" 0,"calt" 0;}}
.m{{font-family:{MONO};}}
{BASE_CSS}
{css}
@media (prefers-reduced-motion:reduce){{*{{animation:none!important;}}}}
</style>
{body}
</svg>
"""


def backdrop(width, height, rx=16):
    """Deep navy fill with two slowly drifting aurora glows and a faint dot grid."""
    return f"""<defs>
  <linearGradient id="grad" x1="0" y1="0" x2="1" y2="0">{GRAD_STOPS}</linearGradient>
  <radialGradient id="au1" cx=".2" cy="0" r=".6"><stop offset="0" stop-color="{BLUE}" stop-opacity=".26"/><stop offset="1" stop-color="{BLUE}" stop-opacity="0"/></radialGradient>
  <radialGradient id="au2" cx=".9" cy="1" r=".55"><stop offset="0" stop-color="{CYAN}" stop-opacity=".13"/><stop offset="1" stop-color="{CYAN}" stop-opacity="0"/></radialGradient>
  <linearGradient id="edge" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#fff" stop-opacity=".2"/><stop offset=".45" stop-color="#fff" stop-opacity=".05"/><stop offset="1" stop-color="{CYAN}" stop-opacity=".22"/></linearGradient>
  <linearGradient id="sep" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#fff" stop-opacity="0"/><stop offset=".2" stop-color="#fff" stop-opacity=".09"/><stop offset=".8" stop-color="#fff" stop-opacity=".09"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient>
  <pattern id="dots" width="22" height="22" patternUnits="userSpaceOnUse"><circle cx="1" cy="1" r=".9" fill="#fff" fill-opacity=".04"/></pattern>
  <clipPath id="frame"><rect width="{width}" height="{height}" rx="{rx}"/></clipPath>
</defs>
<g clip-path="url(#frame)">
  <rect width="{width}" height="{height}" fill="{CARD}"/>
  <rect class="au1" x="-120" y="-80" width="{width + 240}" height="{height + 160}" fill="url(#au1)"/>
  <rect class="au2" x="-120" y="-80" width="{width + 240}" height="{height + 160}" fill="url(#au2)"/>
  <rect width="{width}" height="{height}" fill="url(#dots)"/>
</g>
"""


def border(width, height, rx=16, dur=11):
    """Hairline gradient border plus two comets of light circling it."""
    x, w, h, r = 0.75, width - 1.5, height - 1.5, rx - 0.75
    perimeter = 2 * (w + h) - (8 - 2 * math.pi) * r
    out = [f'<rect x="{x}" y="{x}" width="{w}" height="{h}" rx="{r}" fill="none" stroke="url(#edge)" stroke-width="1.2"/>']
    for colour, delay in ((CYAN, 0), (BLUE, dur / 2)):
        tail = 240
        for length, sw, op in ((tail, 5, .08), (130, 2.4, .32), (46, 1.5, .95)):
            start = perimeter + length - tail
            out.append(f'<rect x="{x}" y="{x}" width="{w}" height="{h}" rx="{r}" fill="none" stroke="{colour}" stroke-width="{sw}" '
                       f'stroke-opacity="{op}" stroke-linecap="round" stroke-dasharray="{length} {perimeter - length:.1f}" stroke-dashoffset="{start:.1f}">'
                       f'<animate attributeName="stroke-dashoffset" from="{start:.1f}" to="{length - tail:.1f}" dur="{dur}s" begin="-{delay}s" repeatCount="indefinite"/></rect>')
    return "\n".join(out)


def card(width, height, index, label, note=""):
    """Backdrop plus the shared header: index pill, spaced label, note and a fading rule."""
    return backdrop(width, height) + f"""<rect x="28" y="24" width="36" height="22" rx="11" fill="{CYAN}" fill-opacity=".1" stroke="{CYAN}" stroke-opacity=".4"/>
<text x="46" y="39" class="m" font-size="11" font-weight="700" text-anchor="middle" fill="{CYAN}">{esc(index)}</text>
<text x="76" y="40" class="m" font-size="13" letter-spacing="3" fill="{INK}">{esc(label)}</text>
<text x="{width - 28}" y="40" class="m" font-size="12" text-anchor="end" fill="{DIM}">{esc(note)}</text>
<rect x="28" y="60" width="{width - 56}" height="1" fill="url(#sep)"/>
"""


def glass(x, y, w, h, rx=12):
    """Translucent panel with a gradient hairline edge."""
    return (f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{PANEL}" fill-opacity=".72"/>'
            f'<rect x="{x + .5}" y="{y + .5}" width="{w - 1}" height="{h - 1}" rx="{rx - .5}" fill="none" stroke="url(#edge)"/>')


# 14px line icons, drawn as strokes in a 14x14 box.
ICONS = {
    "block": '<path d="M7 1 L13 4 L13 10 L7 13 L1 10 L1 4 Z M1 4 L7 7 L13 4 M7 7 V13"/>',
    "check": '<circle cx="7" cy="7" r="6"/><path d="M4.2 7.2 L6.2 9.2 L9.8 5.2"/>',
    "user": '<circle cx="7" cy="4.6" r="2.8"/><path d="M1.8 13 C2.6 9.4 11.4 9.4 12.2 13"/>',
    "ens": '<path d="M7 1 L12 7 L7 13 L2 7 Z M2 7 H12"/>',
    "pin": '<path d="M7 13 C7 13 2.5 8.6 2.5 5.4 A4.5 4.5 0 0 1 11.5 5.4 C11.5 8.6 7 13 7 13 Z"/><circle cx="7" cy="5.4" r="1.6"/>',
    "role": '<rect x="1.5" y="4" width="11" height="8.5" rx="1.8"/><path d="M5 4 V2.3 H9 V4 M1.5 7.8 H12.5"/>',
    "flag": '<path d="M2.5 13 V1.5 M2.5 2 H11 L9 5 L11 8 H2.5"/>',
    "cup": '<path d="M2 5.5 H10 V9 A3.5 3.5 0 0 1 6.5 12.5 H5.5 A3.5 3.5 0 0 1 2 9 Z M10 6.5 H11 A1.6 1.6 0 0 1 11 9.7 H10 M4.5 1.5 V3.5 M7.5 1.5 V3.5"/>',
    "hash": '<path d="M5 1.5 L4 12.5 M10 1.5 L9 12.5 M1.5 5 H12.5 M1.5 9 H12.5"/>',
    "calendar": '<rect x="1.5" y="2.5" width="11" height="10" rx="2"/><path d="M1.5 6 H12.5 M4.5 1 V4 M9.5 1 V4"/>',
    "star": '<path d="M7 1.2 L8.8 4.9 L12.8 5.4 L9.9 8.2 L10.6 12.2 L7 10.3 L3.4 12.2 L4.1 8.2 L1.2 5.4 L5.2 4.9 Z"/>',
    "flame": '<path d="M7 13 C3.8 13 2.5 10.8 2.5 8.8 C2.5 6 5.5 4.6 5.5 1.5 C8.5 3 11.5 5.6 11.5 8.8 C11.5 10.8 10.2 13 7 13 Z M7 13 C5.8 13 5 12 5 10.8 C5 9.4 7 8.4 7 7 C8.4 8 9 9.4 9 10.8 C9 12 8.2 13 7 13 Z"/>',
    "bolt": '<path d="M8 1 L2.5 8 H7 L6 13 L11.5 6 H7 Z"/>',
    "repo": '<path d="M3 1.5 H11.5 V12.5 H3 A1.5 1.5 0 0 1 1.5 11 V3 A1.5 1.5 0 0 1 3 1.5 Z M1.5 11 A1.5 1.5 0 0 1 3 9.5 H11.5"/>',
}


def icon(kind, x, y, colour):
    """14px line icon with its top-left corner at (x, y)."""
    return (f'<g transform="translate({x} {y})" fill="none" stroke="{colour}" stroke-width="1.4" '
            f'stroke-linecap="round" stroke-linejoin="round">{ICONS[kind]}</g>')
