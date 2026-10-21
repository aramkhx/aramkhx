#!/usr/bin/env python3
"""Build the static profile SVGs in assets/ (hero, genesis block, buttons, footer).

Edit the data below, then run:  python3 scripts/build_assets.py
assets/chain-activity.svg is rendered separately by chain_activity.py (daily workflow).
"""

import hashlib
import math
import random
from pathlib import Path

from theme import (BLUE, CARD, CYAN, DIM, GOLD, ICE, INK, MUTED, PANEL, SANS, SKY,
                   backdrop, border, card, esc, glass, icon, pts, svg)

ASSETS = Path(__file__).resolve().parent.parent / "assets"

# Most monospace fonts lack U+2713, so draw the tick from the sans stack.
CHECK = f'<tspan font-family="{SANS}">✓</tspan>'

NAME = "ARAM KHACHATRYAN"
ROLE = "Software & Cybersecurity Engineer"
LOCATION = "Yerevan, Armenia"
ENS = "aramk.eth"
UID = "108998795"  # GitHub user id, doubles as the genesis block height

# (icon, label, value, colour, note); colour None = shimmering hash, value None = gas bar
OVERVIEW = [
    ("block", "Block Height", UID, INK, "github uid"),
    ("check", "Status", "Finalized", CYAN, ""),
    ("user", "Validator", "Aram Khachatryan", INK, ""),
    ("ens", "ENS Name", ENS, CYAN, ""),
    ("pin", "Location", f"{LOCATION} · 40.18°N 44.51°E", INK, ""),
    ("role", "Role", ROLE, INK, ""),
    ("flag", "Ideology", "Li₿ertarian", GOLD, ""),
    ("cup", "Gas Used", None, INK, ""),
    ("hash", "Block Hash", "0x" + ENS.encode().hex() + "…", None, ""),
]

TXS = [
    ("prove()", BLUE, "Groth16 circuits in Circom → Solidity verifiers"),
    ("transmit()", GOLD, "210-byte ZK alert packets over LoRa radio"),
    ("build()", CYAN, "On-chain programs in Rust & Anchor: escrow, vault"),
    ("secure()", ICE, "TLS · RSA · AES-GCM · SHA-256 on Nordic nRF"),
    ("translate()", SKY, "Web3 vocabulary → Armenian (Հայերեն)"),
    ("publish()", MUTED, "Writing at aramk.eth.limo, in EN & Հայերեն"),
]

BUTTONS = [
    ("btn-ens", ENS, BLUE, "eth"),
    ("btn-linkedin", "LinkedIn", CYAN, "in"),
    ("btn-mail", "Email", ICE, "mail"),
]


def short_hash(text):
    h = hashlib.sha256(text.encode()).hexdigest()
    return f"0x{h[:4]}…{h[-4:]}"


def mix(c1, c2, t):
    a = [int(c1[i:i + 2], 16) for i in (1, 3, 5)]
    b = [int(c2[i:i + 2], 16) for i in (1, 3, 5)]
    return "#" + "".join(f"{round(x + (y - x) * t):02X}" for x, y in zip(a, b))


def hexagon(cx, cy, r):
    return pts(*[(cx + r * math.cos(math.radians(a)), cy + r * math.sin(math.radians(a)))
                 for a in (-90, -30, 30, 90, 150, 210)])


def star4(x, y, s):
    k = s * 0.2
    return f"M{x},{y - s} L{x + k},{y - k} L{x + s},{y} L{x + k},{y + k} L{x},{y + s} L{x - k},{y + k} L{x - s},{y} L{x - k},{y - k}Z"


def reveal(attr, start, end, dur, lead=0.2):
    """SMIL that holds `start` for the lead fraction, then eases to `end` and stays there."""
    return (f'<animate attributeName="{attr}" values="{start};{start};{end}" keyTimes="0;{lead};1" dur="{dur}s" '
            f'fill="freeze" calcMode="spline" keySplines="0 0 1 1;.25 .1 .25 1"/>')


TILT, EYE = math.radians(-16), 900.0  # camera tilt and distance shared by every crystal


def apex_y(cy, R):
    """Screen y of a crystal's top vertex; it sits on the spin axis, so it never moves."""
    y, z = -1.3 * R * math.cos(TILT), -1.3 * R * math.sin(TILT)
    return cy + y * EYE / (EYE - z)


def crystal(cx, cy, R, frames=48, dur=18, direction=1, top=("#0B2C73", "#D4F7FF"),
            bottom=("#071A47", "#5FB4FF"), glass_opacity=.8, edge=.6):
    """A glass crystal (hexagonal bipyramid) spinning in 3D, baked into SMIL keyframes.

    Every facet is drawn twice: in a back layer seen through the glass and in a front layer.
    Opacity hands each facet between the layers as it turns, and its fill follows the light.
    """
    ring = [(R * math.cos(k * math.pi / 3), 0.0, R * math.sin(k * math.pi / 3)) for k in range(6)]
    verts = [(0.0, -1.3 * R, 0.0), (0.0, 1.8 * R, 0.0)] + ring
    faces = ([(0, 2 + k, 2 + (k + 1) % 6) for k in range(6)]
             + [(1, 2 + (k + 1) % 6, 2 + k) for k in range(6)])
    tilt, D = TILT, EYE
    lx, ly, lz = -0.45, -0.75, 0.55
    ln = math.sqrt(lx * lx + ly * ly + lz * lz)
    light = (lx / ln, ly / ln, lz / ln)

    def spin(v, theta):
        x, y, z = v
        x, z = x * math.cos(theta) + z * math.sin(theta), -x * math.sin(theta) + z * math.cos(theta)
        return x, y * math.cos(tilt) - z * math.sin(tilt), y * math.sin(tilt) + z * math.cos(tilt)

    points = [[] for _ in faces]
    shown = [[] for _ in faces]
    fills = [[] for _ in faces]
    for f in range(frames + 1):  # the extra frame equals the first, so the loop is seamless
        tv = [spin(v, direction * 2 * math.pi * f / frames) for v in verts]
        proj = [(cx + x * D / (D - z), cy + y * D / (D - z)) for x, y, z in tv]
        for i, face in enumerate(faces):
            a, b, c = (tv[j] for j in face)
            u = [b[k] - a[k] for k in range(3)]
            w = [c[k] - a[k] for k in range(3)]
            n = [u[1] * w[2] - u[2] * w[1], u[2] * w[0] - u[0] * w[2], u[0] * w[1] - u[1] * w[0]]
            centre = [(a[k] + b[k] + c[k]) / 3 for k in range(3)]
            if sum(n[k] * centre[k] for k in range(3)) < 0:
                n = [-x for x in n]
            nn = math.sqrt(sum(x * x for x in n))
            n = [x / nn for x in n]
            to_eye = (-centre[0], -centre[1], D - centre[2])
            points[i].append(pts(*(proj[j] for j in face)))
            shown[i].append(1 if sum(n[k] * to_eye[k] for k in range(3)) > 0 else 0)
            lit = 0.15 + 0.85 * max(0.0, sum(n[k] * light[k] for k in range(3)))
            fills[i].append(mix(*(top if i < 6 else bottom), lit))

    def anim(attr, values):
        return f'<animate attributeName="{attr}" dur="{dur}s" repeatCount="indefinite" values="{";".join(map(str, values))}"/>'

    back = [f'<polygon points="{points[i][0]}" opacity="{1 - shown[i][0]}" fill="#0A1C40" fill-opacity=".35" '
            f'stroke="{ICE}" stroke-opacity=".25" stroke-linejoin="round">'
            f'{anim("points", points[i])}{anim("opacity", [1 - s for s in shown[i]])}</polygon>'
            for i in range(len(faces))]
    front = [f'<polygon points="{points[i][0]}" opacity="{shown[i][0]}" fill="{fills[i][0]}" fill-opacity="{glass_opacity}" '
             f'stroke="#DDF8FF" stroke-opacity="{edge}" stroke-width="1.1" stroke-linejoin="round">'
             f'{anim("points", points[i])}{anim("opacity", shown[i])}{anim("fill", fills[i])}</polygon>'
             for i in range(len(faces))]
    core = (f'<ellipse class="core" cx="{cx}" cy="{cy + 8}" rx="{R * .75:.0f}" ry="{R * 1.1:.0f}" '
            f'fill="url(#coreG)"/>')
    return "\n".join(back), core, "\n".join(front)


def orbit(cx, cy, rx, ry, angle, colour, dur, delay=0):
    """Tilted orbit split into a far half (drawn behind the crystal) and a near half."""
    far = f"M{cx + rx},{cy} A{rx},{ry} 0 0 0 {cx - rx},{cy}"
    near = f"M{cx - rx},{cy} A{rx},{ry} 0 0 0 {cx + rx},{cy}"
    rot = f'transform="rotate({angle} {cx} {cy})"'

    def rider(path, show_first):
        kp, vis = ("0;1;1", "1;0") if show_first else ("0;0;1", "0;1")
        return (f'<circle r="3.6" fill="{colour}" filter="url(#glow)">'
                f'<animateMotion dur="{dur}s" begin="-{delay}s" repeatCount="indefinite" path="{path}" keyPoints="{kp}" keyTimes="0;.5;1" calcMode="linear"/>'
                f'<animate attributeName="opacity" dur="{dur}s" begin="-{delay}s" repeatCount="indefinite" calcMode="discrete" keyTimes="0;.5" values="{vis}"/></circle>')

    behind = (f'<g {rot}><path d="{far}" fill="none" stroke="url(#grad)" stroke-opacity=".3" stroke-width="1.2" stroke-dasharray="2 6"/>'
              f'{rider(far, False)}</g>')
    ahead = (f'<g {rot}><path d="{near}" fill="none" stroke="url(#grad)" stroke-opacity=".75" stroke-width="1.4" stroke-dasharray="2 6"/>'
             f'{rider(near, True)}</g>')
    return behind, ahead


def hero():
    W, H = 1000, 360
    rnd = random.Random(11)
    cx, cy, R, floor = 792, 162, 60, 282
    tip = apex_y(cy, R)
    name_w, name_y = 570, 198

    # Type the role after a short pause. The clip starts full width so the text still
    # shows in any renderer without SMIL; with SMIL it collapses at t=0 and types in.
    cw, x0, ty = 12.0, 82, 274
    n, lead, step = len(ROLE), 1.6, 0.055
    dur = lead + n * step
    key_times = "0;" + ";".join(f"{(lead + i * step) / dur:.4f}" for i in range(n + 1))
    typing = f'dur="{dur:.2f}s" fill="freeze" calcMode="discrete" keyTimes="{key_times}"'
    widths = "0;" + ";".join(f"{i * cw:g}" for i in range(n + 1))
    xs = f"{x0};" + ";".join(f"{x0 + i * cw:g}" for i in range(n + 1))

    stars = []
    for _ in range(60):
        sx, sy = rnd.uniform(12, 988), rnd.uniform(12, 348)
        stars.append(f'<circle class="star" cx="{sx:.0f}" cy="{sy:.0f}" r="{rnd.uniform(.5, 1.3):.1f}" fill="{rnd.choice([ICE, "#fff", SKY])}" '
                     f'style="animation-delay:-{rnd.uniform(0, 6):.1f}s;animation-duration:{rnd.uniform(3, 7):.1f}s"/>')

    meteors = "".join(
        f'<g transform="rotate(17 {mx} {my})"><rect class="meteor" x="{mx}" y="{my}" width="130" height="1.6" rx=".8" '
        f'fill="url(#meteorG)" style="animation-delay:{delay}s"/></g>'
        for mx, my, delay in [(120, 30, 1.8), (420, 14, 5.6), (250, 64, 9.3)])

    rays = []
    for k in range(12):
        a = math.radians(k * 30 + rnd.uniform(-8, 8))
        half = math.radians(rnd.uniform(1.2, 2.8))
        length = rnd.uniform(220, 300)
        rays.append(f'<polygon points="{pts((cx, cy), (cx + length * math.cos(a - half), cy + length * math.sin(a - half)), (cx + length * math.cos(a + half), cy + length * math.sin(a + half)))}"/>')

    motes = []
    for k in range(18):
        mx, my = cx + rnd.uniform(-125, 125), floor - rnd.uniform(0, 10)
        style = f'style="animation-delay:-{rnd.uniform(0, 7):.1f}s;animation-duration:{rnd.uniform(4.5, 7.5):.1f}s"'
        if k % 3 == 0:  # every third mote is a tiny hexagon
            motes.append(f'<polygon class="mote" points="{hexagon(mx, my, rnd.uniform(2.6, 3.8))}" fill="none" stroke="{ICE}" stroke-width=".9" {style}/>')
        else:
            motes.append(f'<circle class="mote" cx="{mx:.0f}" cy="{my:.0f}" r="{rnd.uniform(1.6, 3.4):.1f}" fill="url(#moteG)" {style}/>')

    ripples = "".join(f'<ellipse class="ripple" cx="{cx}" cy="{floor}" rx="40" ry="6" fill="none" stroke="{ICE}" stroke-width="1" '
                      f'vector-effect="non-scaling-stroke" style="animation-delay:-{k * 2.25}s"/>' for k in range(2))

    # Holographic pedestal: rings drawn flat, then squashed onto the floor so their spin reads as 3D.
    ring = 'fill="none" vector-effect="non-scaling-stroke"'
    pedestal = f"""<g transform="translate({cx} {floor}) scale(1 .17)">
    <circle r="160" fill="url(#padG)"/>
    <circle class="spin" r="152" {ring} stroke="{ICE}" stroke-opacity=".4" stroke-width="1" stroke-dasharray="2 9"/>
    <circle class="spinr" r="124" {ring} stroke="{CYAN}" stroke-opacity=".65" stroke-width="1.5" stroke-dasharray="46 16 8 16"/>
    <polygon class="spin" style="animation-duration:28s" points="{hexagon(0, 0, 102)}" {ring} stroke="{SKY}" stroke-opacity=".4" stroke-width="1"/>
    <circle r="76" {ring} stroke="{ICE}" stroke-opacity=".55" stroke-width="1.2"/>
  </g>"""

    back, core, front = crystal(cx, cy, R, glass_opacity=.62)
    inner_back, _, inner_front = crystal(cx, cy + 10, 22, dur=9, direction=-1, top=("#3A8DFF", "#FFFFFF"),
                                         bottom=("#1E5FD8", "#BFF3FF"), glass_opacity=.9, edge=.9)
    orbit_a = orbit(cx, cy + 18, 168, 36, -9, CYAN, 9)
    orbit_b = orbit(cx, cy + 18, 130, 26, 14, ICE, 7, delay=2)
    sparkles = "".join(f'<path class="twinkle" style="animation-delay:{d}s" d="{star4(x, y, s)}" fill="{ICE}"/>' for x, y, s, d in
                       [(688, 78, 7, 0), (908, 100, 5, 1.1), (938, 232, 6, 2.3), (648, 212, 4.5, 3.1), (852, 52, 4, 1.7)])
    bars = "".join(f'<rect class="bar" x="{164 + i * 5}" y="{99 - h}" width="3" height="{h}" rx="1" fill="{CYAN}" style="animation-delay:{i * .2:.1f}s"/>'
                   for i, h in enumerate((5, 8, 11)))
    name = (f'x="56" y="{name_y}" font-size="58" font-weight="800" letter-spacing="1" textLength="{name_w}" '
            f'lengthAdjust="spacingAndGlyphs"')

    css = f"""
.float{{animation:float 6s ease-in-out infinite}}
@keyframes float{{0%,100%{{transform:translateY(0)}}50%{{transform:translateY(-8px)}}}}
.core{{animation:core 3.2s ease-in-out infinite}}
@keyframes core{{0%,100%{{opacity:.55}}50%{{opacity:1}}}}
.rays{{transform-origin:{cx}px {cy}px;animation:spin 90s linear infinite}}
.spin,.spinr{{transform-box:fill-box;transform-origin:center;animation:spin 40s linear infinite}}
.spinr{{animation-name:spinr;animation-duration:24s}}
@keyframes spin{{to{{transform:rotate(360deg)}}}}
@keyframes spinr{{to{{transform:rotate(-360deg)}}}}
.column{{animation:column 4s ease-in-out infinite}}
@keyframes column{{0%,100%{{opacity:.55}}50%{{opacity:1}}}}
.curtain{{animation:curtain 16s ease-in-out infinite alternate}}
@keyframes curtain{{from{{transform:translateX(-50px) skewX(-5deg)}}to{{transform:translateX(50px) skewX(5deg)}}}}
.star{{animation:star 5s ease-in-out infinite}}
@keyframes star{{0%,100%{{opacity:.15}}50%{{opacity:.9}}}}
.meteor{{opacity:0;animation:meteor 11s ease-in infinite}}
@keyframes meteor{{0%{{opacity:0;transform:translateX(0)}}1%{{opacity:1}}9%{{opacity:0;transform:translateX(380px)}}100%{{opacity:0;transform:translateX(380px)}}}}
.twinkle{{transform-box:fill-box;transform-origin:center;animation:twinkle 3.6s ease-in-out infinite}}
@keyframes twinkle{{0%,100%{{opacity:0;transform:scale(.3) rotate(0deg)}}50%{{opacity:.95;transform:scale(1) rotate(45deg)}}}}
.glint{{transform-box:fill-box;transform-origin:center;animation:glint 5s ease-in-out infinite}}
@keyframes glint{{0%,68%,100%{{opacity:0;transform:scale(.2) rotate(0deg)}}78%{{opacity:1;transform:scale(1) rotate(45deg)}}90%{{opacity:0;transform:scale(.4) rotate(90deg)}}}}
.flare{{transform-box:fill-box;transform-origin:center;animation:flare 5s ease-in-out infinite}}
@keyframes flare{{0%,68%,100%{{opacity:0;transform:scaleX(.1)}}78%{{opacity:.9;transform:scaleX(1)}}92%{{opacity:0;transform:scaleX(.3)}}}}
.ripple{{transform-box:fill-box;transform-origin:center;animation:ripple 4.5s ease-out infinite}}
@keyframes ripple{{0%{{transform:scale(1);opacity:.5}}100%{{transform:scale(5.4);opacity:0}}}}
.mote{{opacity:0;animation:mote 6s ease-in infinite}}
@keyframes mote{{0%{{transform:translateY(0);opacity:0}}20%{{opacity:.95}}100%{{transform:translateY(-160px);opacity:0}}}}
.bar{{animation:bar 1.4s ease-in-out infinite}}
@keyframes bar{{0%,100%{{opacity:.3}}50%{{opacity:1}}}}
.grow{{transform-box:fill-box;transform-origin:left center;animation:grow 1.4s 1.2s ease-out both}}
@keyframes grow{{from{{transform:scaleX(0)}}to{{transform:none}}}}
.up{{animation:up 1s ease-out both}}
@keyframes up{{from{{opacity:0;transform:translateY(10px)}}to{{opacity:1;transform:none}}}}
.gloss{{animation:gloss 12s ease-in-out 3s infinite}}
@keyframes gloss{{0%,72%{{transform:translateX(0) skewX(-24deg)}}100%{{transform:translateX(1750px) skewX(-24deg)}}}}
"""

    body = f"""{backdrop(W, H, rx=18)}
<defs>
  <linearGradient id="shineG" gradientUnits="userSpaceOnUse" x1="0" y1="0" x2="220" y2="0" gradientTransform="translate(-300)">
    <stop offset="0" stop-color="#fff" stop-opacity="0"/><stop offset=".5" stop-color="#fff" stop-opacity=".85"/><stop offset="1" stop-color="#fff" stop-opacity="0"/>
    <animateTransform attributeName="gradientTransform" type="translate" values="-300;-300;760" keyTimes="0;.6;1" dur="6.5s" begin="2s" repeatCount="indefinite"/>
  </linearGradient>
  <radialGradient id="halo" cx="{cx}" cy="{cy}" r="230" gradientUnits="userSpaceOnUse"><stop offset="0" stop-color="{BLUE}" stop-opacity=".45"/><stop offset=".45" stop-color="{CYAN}" stop-opacity=".1"/><stop offset="1" stop-color="{CYAN}" stop-opacity="0"/></radialGradient>
  <radialGradient id="rayG" cx="{cx}" cy="{cy}" r="300" gradientUnits="userSpaceOnUse"><stop offset="0" stop-color="{ICE}" stop-opacity=".2"/><stop offset=".5" stop-color="{CYAN}" stop-opacity=".05"/><stop offset="1" stop-color="{CYAN}" stop-opacity="0"/></radialGradient>
  <radialGradient id="coreG"><stop offset="0" stop-color="#FFFFFF" stop-opacity=".95"/><stop offset=".35" stop-color="{ICE}" stop-opacity=".7"/><stop offset="1" stop-color="{BLUE}" stop-opacity="0"/></radialGradient>
  <radialGradient id="moteG"><stop offset="0" stop-color="#fff"/><stop offset=".4" stop-color="{ICE}" stop-opacity=".8"/><stop offset="1" stop-color="{CYAN}" stop-opacity="0"/></radialGradient>
  <radialGradient id="padG"><stop offset="0" stop-color="{CYAN}" stop-opacity=".35"/><stop offset=".6" stop-color="{BLUE}" stop-opacity=".12"/><stop offset="1" stop-color="{BLUE}" stop-opacity="0"/></radialGradient>
  <linearGradient id="columnG" gradientUnits="userSpaceOnUse" x1="0" y1="{floor}" x2="0" y2="30"><stop offset="0" stop-color="{ICE}" stop-opacity=".26"/><stop offset=".5" stop-color="{CYAN}" stop-opacity=".07"/><stop offset="1" stop-color="{CYAN}" stop-opacity="0"/></linearGradient>
  <linearGradient id="meteorG" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#fff" stop-opacity="0"/><stop offset="1" stop-color="#fff" stop-opacity=".95"/></linearGradient>
  <linearGradient id="glossG" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#fff" stop-opacity="0"/><stop offset=".5" stop-color="#fff" stop-opacity=".05"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient>
  <linearGradient id="horizon" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="{CYAN}" stop-opacity="0"/><stop offset=".5" stop-color="{ICE}" stop-opacity=".6"/><stop offset="1" stop-color="{CYAN}" stop-opacity="0"/></linearGradient>
  <linearGradient id="fadeDown" gradientUnits="userSpaceOnUse" x1="0" y1="{floor}" x2="0" y2="{floor + 80}"><stop offset="0" stop-color="#fff" stop-opacity=".4"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient>
  <mask id="reflect" maskUnits="userSpaceOnUse" x="560" y="{floor}" width="440" height="{H - floor}"><rect x="560" y="{floor}" width="440" height="{H - floor}" fill="url(#fadeDown)"/></mask>
  <filter id="glow" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="3" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
  <filter id="bloom" x="-20%" y="-60%" width="140%" height="220%"><feGaussianBlur stdDeviation="14"/></filter>
  <filter id="veil" x="-10%" y="-60%" width="120%" height="220%"><feGaussianBlur stdDeviation="20"/></filter>
  <clipPath id="nameClip"><rect x="40" y="{name_y - 76}" height="100" width="{name_w + 40}">{reveal("width", 0, name_w + 40, 1.8)}</rect></clipPath>
  <clipPath id="type"><rect x="{x0 - 2}" y="{ty - 22}" height="30" width="{n * cw:g}"><animate attributeName="width" {typing} values="{widths}"/></rect></clipPath>
</defs>
<g clip-path="url(#frame)">
  <g class="curtain" filter="url(#veil)" opacity=".6">
    <path d="M-80,70 C140,10 300,120 520,60 S860,20 1080,80 L1080,128 C860,80 700,170 520,118 S140,80 -80,140 Z" fill="{BLUE}" fill-opacity=".4"/>
    <path d="M-80,124 C200,64 380,172 600,112 S900,92 1080,142 L1080,176 C880,142 640,212 460,162 S160,132 -80,182 Z" fill="{CYAN}" fill-opacity=".2"/>
  </g>
  {"".join(stars)}
  {meteors}
  <g class="rays" fill="url(#rayG)">{"".join(rays)}</g>
  <rect width="{W}" height="{H}" fill="url(#halo)"/>
  <polygon class="column" points="{pts((cx - 34, floor), (cx + 34, floor), (cx + 9, 30), (cx - 9, 30))}" fill="url(#columnG)"/>
  {pedestal}
  <rect x="600" y="{floor}" width="390" height="1" fill="url(#horizon)"/>
  {ripples}
  {"".join(motes)}

  <g id="gem" class="float">
    {orbit_a[0]}
    {orbit_b[0]}
    {back}
    {core}
    {inner_back}
    {inner_front}
    {front}
    {orbit_a[1]}
    {orbit_b[1]}
    <ellipse class="flare" cx="{cx}" cy="{tip:.1f}" rx="36" ry="1.3" fill="{ICE}"/>
    <path class="glint" d="{star4(cx, round(tip, 1), 15)}" fill="#fff" filter="url(#glow)"/>
  </g>
  <g mask="url(#reflect)"><use href="#gem" xlink:href="#gem" transform="translate(0 {2 * floor}) scale(1 -1)"/></g>
  {sparkles}

  <g class="up">
    <rect x="56" y="78" width="132" height="30" rx="15" fill="{CYAN}" fill-opacity=".07" stroke="{CYAN}" stroke-opacity=".35"/>
    <circle class="pulse" cx="74" cy="93" r="4" fill="{CYAN}"/>
    <text x="86" y="98" class="m" font-size="13" font-weight="600" letter-spacing="2" fill="{CYAN}">MAINNET</text>
    {bars}
  </g>

  <g clip-path="url(#nameClip)">
    <text {name} fill="{BLUE}" opacity=".55" filter="url(#bloom)">{NAME}</text>
    <text {name} fill="url(#grad)">{NAME}</text>
    <text {name} fill="url(#shineG)">{NAME}</text>
  </g>
  <rect x="40" y="{name_y - 62}" width="3" height="76" rx="1.5" fill="#fff" opacity="0" filter="url(#glow)">
    {reveal("x", 40, name_w + 80, 1.8)}
    <animate attributeName="opacity" values="0;0;1;1;0" keyTimes="0;.2;.26;.9;1" dur="1.8s" fill="freeze"/>
  </rect>

  <rect class="grow" x="58" y="{name_y + 27}" width="242" height="2" rx="1" fill="url(#grad)"/>
  <circle r="2.6" fill="#fff" filter="url(#glow)"><animateMotion dur="3.2s" repeatCount="indefinite" path="M58,{name_y + 28} H300"/>
    <animate attributeName="opacity" values="0;1;1;0" keyTimes="0;.1;.9;1" dur="3.2s" repeatCount="indefinite"/></circle>

  <text x="56" y="{ty}" class="m" font-size="20" font-weight="700" fill="{CYAN}">$</text>
  <text clip-path="url(#type)" x="{x0}" y="{ty}" class="m" font-size="20" fill="{INK}" textLength="{n * cw:g}">{esc(ROLE)}</text>
  <rect x="{x0 + n * cw:g}" y="{ty - 18}" width="11" height="22" fill="{CYAN}" opacity=".85">
    <animate attributeName="x" {typing} values="{xs}"/>
    <animate attributeName="opacity" values=".85;0" dur="1s" repeatCount="indefinite" calcMode="discrete"/>
  </rect>

  <rect class="gloss" x="-420" y="-60" width="280" height="{H + 120}" fill="url(#glossG)" transform="skewX(-24)"/>
</g>
{border(W, H, rx=18, dur=12)}
"""
    return svg(W, H, f"Aram Khachatryan — {ROLE}", body, css)


def blockie(seed, x, y, size=48, cells=8):
    """Mirrored identicon, the way block explorers draw an address avatar."""
    digest = hashlib.sha256(seed.encode()).digest()
    palette = [PANEL] * 4 + [BLUE] * 3 + [CYAN] * 2 + [ICE]
    cell = size / cells
    out = [f'<clipPath id="blk"><rect x="{x}" y="{y}" width="{size}" height="{size}" rx="11"/></clipPath>',
           f'<rect x="{x - 4}" y="{y - 4}" width="{size + 8}" height="{size + 8}" rx="14" fill="{CYAN}" opacity=".35" filter="url(#soft)"/>',
           f'<g clip-path="url(#blk)">']
    for row in range(cells):
        for col in range(cells // 2):
            colour = palette[digest[row * (cells // 2) + col] % len(palette)]
            for c in (col, cells - 1 - col):
                out.append(f'<rect x="{x + c * cell:.1f}" y="{y + row * cell:.1f}" width="{cell + .3:.1f}" height="{cell + .3:.1f}" fill="{colour}"/>')
    out.append(f'<rect class="holo" x="{x - 30}" y="{y - 10}" width="22" height="{size + 20}" fill="url(#holoG)" transform="skewX(-20)"/>')
    out.append("</g>")
    out.append(f'<rect x="{x + .5}" y="{y + .5}" width="{size - 1}" height="{size - 1}" rx="10.5" fill="none" stroke="{ICE}" stroke-opacity=".5"/>')
    out.append(f'<circle cx="{x + size - 2}" cy="{y + size - 2}" r="8" fill="{CARD}"/><circle cx="{x + size - 2}" cy="{y + size - 2}" r="6.2" fill="{CYAN}"/>'
               f'<path d="M{x + size - 5},{y + size - 2} L{x + size - 3},{y + size} L{x + size + 1},{y + size - 4.5}" fill="none" stroke="{CARD}" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/>')
    return "\n".join(out)


def genesis():
    W, H = 1000, 540
    css = """
.tx{animation:tx .6s ease-out both}
@keyframes tx{from{opacity:0;transform:translateX(-8px)}to{opacity:1;transform:none}}
.blink{animation:blink 1s steps(1) infinite}
@keyframes blink{50%{opacity:0}}
.np{transform-box:fill-box;transform-origin:center;animation:np 3.6s ease-out infinite}
@keyframes np{0%{transform:scale(1);opacity:.9}35%,100%{transform:scale(2.6);opacity:0}}
.sweep{animation:sweep 9s ease-in-out 1s infinite}
@keyframes sweep{0%,55%{transform:translateX(0) skewX(-22deg)}100%{transform:translateX(1400px) skewX(-22deg)}}
.holo{animation:holo 5s ease-in-out infinite}
@keyframes holo{0%,60%{transform:translateX(0) skewX(-20deg)}100%{transform:translateX(120px) skewX(-20deg)}}
"""
    out = [card(W, H, "01", "GENESIS BLOCK", "aramscan · personal block explorer")]
    out.append(f"""<defs>
  <linearGradient id="shine" gradientUnits="userSpaceOnUse" x1="0" y1="0" x2="160" y2="0">
    <stop offset="0" stop-color="{MUTED}"/><stop offset=".5" stop-color="#fff"/><stop offset="1" stop-color="{MUTED}"/>
    <animateTransform attributeName="gradientTransform" type="translate" values="100;540;540" keyTimes="0;.6;1" dur="4s" repeatCount="indefinite"/>
  </linearGradient>
  <linearGradient id="spine" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{CYAN}" stop-opacity=".7"/><stop offset="1" stop-color="{BLUE}" stop-opacity=".1"/></linearGradient>
  <linearGradient id="holoG" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#fff" stop-opacity="0"/><stop offset=".5" stop-color="#fff" stop-opacity=".55"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient>
  <linearGradient id="sweepG" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="{ICE}" stop-opacity="0"/><stop offset=".5" stop-color="{ICE}" stop-opacity=".07"/><stop offset="1" stop-color="{ICE}" stop-opacity="0"/></linearGradient>
  <clipPath id="panels"><rect x="28" y="154" width="462" height="360" rx="12"/><rect x="510" y="154" width="462" height="360" rx="12"/></clipPath>
  <filter id="glow" x="-100%" y="-100%" width="300%" height="300%"><feGaussianBlur stdDeviation="2.5" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
  <filter id="soft" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="8"/></filter>
</defs>
{blockie(ENS, 28, 80)}
<text x="92" y="101" font-size="15" fill="{MUTED}">Block</text>
<text x="138" y="102" class="m" font-size="26" font-weight="700" fill="{INK}">#{UID}</text>
<rect x="308" y="81" width="104" height="26" rx="13" fill="{CYAN}" fill-opacity=".1" stroke="{CYAN}" stroke-opacity=".4"/>
<circle class="pulse" cx="324" cy="94" r="3.5" fill="{CYAN}"/>
<text x="334" y="99" class="m" font-size="12" fill="{CYAN}">Finalized</text>
<text x="92" y="126" font-size="13.5" fill="{MUTED}">Genesis mined <tspan fill="{INK}">Jul 09, 2022</tspan> · validator <tspan fill="{CYAN}">{ENS}</tspan></text>
{glass(640, 80, 332, 36, rx=10)}
<circle cx="660" cy="97" r="6" fill="none" stroke="{MUTED}" stroke-width="1.6"/><path d="M664.5,101.5 L669,106" stroke="{MUTED}" stroke-width="1.6" stroke-linecap="round"/>
<text x="680" y="103" class="m" font-size="13" fill="{INK}">{ENS}</text>
<rect class="blink" x="752" y="90" width="2" height="16" fill="{CYAN}"/>
<rect x="902" y="88" width="62" height="20" rx="6" fill="#fff" fill-opacity=".05"/>
<text x="933" y="102" class="m" font-size="11" text-anchor="middle" fill="{DIM}">ENTER ↵</text>
""")

    # Overview panel
    out.append(glass(28, 154, 462, 360))
    out.append(f'<text x="48" y="184" font-size="15" font-weight="700" fill="{INK}">Overview</text>')
    y = 216
    for i, (kind, label, value, colour, note) in enumerate(OVERVIEW):
        if i:
            out.append(f'<rect x="48" y="{y - 20}" width="422" height="1" fill="url(#sep)"/>')
        out.append(icon(kind, 48, y - 11, SKY))
        out.append(f'<text x="72" y="{y}" class="m" font-size="12.5" fill="{MUTED}">{esc(label)}</text>')
        if value is None:
            out.append(f'<rect x="196" y="{y - 9}" width="140" height="8" rx="4" fill="#fff" fill-opacity=".07"/>')
            out.append(f'<rect x="196" y="{y - 9}" width="140" height="8" rx="4" fill="url(#grad)">{reveal("width", 0, 140, 2.6, lead=.15)}</rect>')
            out.append(f'<text x="346" y="{y}" class="m" font-size="13" fill="{INK}">∞ coffee <tspan fill="{DIM}">(100%)</tspan></text>')
        elif colour is None:
            out.append(f'<text x="196" y="{y}" class="m" font-size="13" fill="url(#shine)">{esc(value)}</text>')
        else:
            out.append(f'<text x="196" y="{y}" font-size="14.5" fill="{colour}">{esc(value)}'
                       + (f'<tspan class="m" font-size="11" fill="{DIM}" dx="10">{esc(note)}</tspan>' if note else "")
                       + "</text>")
        y += 34

    # Transactions panel: each tx hangs off a glowing vertical chain.
    out.append(glass(510, 154, 462, 360))
    out.append(f'<text x="530" y="184" font-size="15" font-weight="700" fill="{INK}">Transactions</text>')
    out.append(f'<rect x="632" y="170" width="58" height="20" rx="10" fill="#fff" fill-opacity=".06"/>'
               f'<text x="661" y="184" class="m" font-size="11" text-anchor="middle" fill="{MUTED}">{len(TXS)} txns</text>')
    out.append(f'<text x="952" y="184" class="m" font-size="11" text-anchor="end" fill="{DIM}">method · hash · status</text>')
    y0, step, sx, period = 200, 50, 541, 3.6
    top, bottom = y0 + 14, y0 + (len(TXS) - 1) * step + 14
    out.append(f'<rect x="{sx - 1}" y="{top}" width="2" height="{bottom - top}" rx="1" fill="url(#spine)"/>')
    out.append(f'<circle r="3" fill="{ICE}" filter="url(#glow)"><animateMotion dur="{period}s" repeatCount="indefinite" path="M{sx},{top} V{bottom}"/></circle>')
    for i, (method, colour, desc) in enumerate(TXS):
        y = y0 + i * step
        chip = len(method) * 7.2 + 16
        arrive = period * i / (len(TXS) - 1)
        out.append(f'<g class="tx" style="animation-delay:{0.4 + i * 0.18:.2f}s">')
        out.append(f'<circle class="np" style="animation-delay:{arrive - period:.2f}s" cx="{sx}" cy="{y + 14}" r="6.5" fill="none" stroke="{colour}" stroke-width="1.2"/>')
        out.append(f'<circle cx="{sx}" cy="{y + 14}" r="6.5" fill="{CARD}" stroke="{colour}" stroke-width="1.6"/>'
                   f'<circle cx="{sx}" cy="{y + 14}" r="2.4" fill="{colour}"/>')
        out.append(f'<rect x="560" y="{y + 4}" width="{chip:.0f}" height="20" rx="5" fill="{colour}" fill-opacity=".13" stroke="{colour}" stroke-opacity=".45"/>')
        out.append(f'<text x="{560 + chip / 2:.0f}" y="{y + 18}" class="m" font-size="12" text-anchor="middle" fill="{colour}">{esc(method)}</text>')
        out.append(f'<text x="{570 + chip:.0f}" y="{y + 18}" class="m" font-size="12" fill="{DIM}">{short_hash(desc)}</text>')
        out.append(f'<text x="952" y="{y + 18}" class="m" font-size="11" text-anchor="end" fill="{CYAN}">{CHECK} success</text>')
        out.append(f'<text x="560" y="{y + 42}" font-size="14" fill="{INK}">{esc(desc)}</text>')
        out.append("</g>")
    out.append(f'<g clip-path="url(#panels)"><rect class="sweep" x="-260" y="140" width="150" height="400" fill="url(#sweepG)" transform="skewX(-22)"/></g>')
    out.append(border(W, H))
    return svg(W, H, "Genesis block: about Aram Khachatryan", "\n".join(out), css)


def button(label, colour, icon_kind, delay):
    w = round(58 + len(label) * 8.4 + 18)
    h = 48
    icons = {
        "eth": f'<polygon points="24,12 31,24.5 24,28.5 17,24.5" fill="{colour}"/><polygon points="24,30.5 31,26.5 24,36 17,26.5" fill="{colour}" fill-opacity=".7"/>',
        "in": f'<text x="24" y="29.5" font-size="15" font-weight="800" text-anchor="middle" fill="{colour}">in</text>',
        "mail": f'<rect x="15.5" y="17" width="17" height="13" rx="2.5" fill="none" stroke="{colour}" stroke-width="1.8"/>'
                f'<polyline points="16.5,18.5 24,24.5 31.5,18.5" fill="none" stroke="{colour}" stroke-width="1.8" stroke-linejoin="round"/>',
    }
    css = f"""
.sheen{{animation:sheen 6s ease-in-out {delay}s infinite}}
@keyframes sheen{{0%,65%{{transform:translateX(0) skewX(-20deg)}}100%{{transform:translateX({w + 140}px) skewX(-20deg)}}}}
"""
    body = f"""<defs>
  <linearGradient id="edge" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{colour}" stop-opacity=".9"/><stop offset="1" stop-color="{colour}" stop-opacity=".15"/></linearGradient>
  <radialGradient id="glow" cx="0" cy=".5" r=".9"><stop offset="0" stop-color="{colour}" stop-opacity=".22"/><stop offset="1" stop-color="{colour}" stop-opacity="0"/></radialGradient>
  <linearGradient id="tile" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{colour}" stop-opacity=".28"/><stop offset="1" stop-color="{colour}" stop-opacity=".06"/></linearGradient>
  <linearGradient id="sh" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#fff" stop-opacity="0"/><stop offset=".5" stop-color="#fff" stop-opacity=".16"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient>
  <clipPath id="c"><rect x=".75" y=".75" width="{w - 1.5}" height="{h - 1.5}" rx="13"/></clipPath>
</defs>
<rect x=".75" y=".75" width="{w - 1.5}" height="{h - 1.5}" rx="13" fill="{CARD}"/>
<rect x=".75" y=".75" width="{w - 1.5}" height="{h - 1.5}" rx="13" fill="url(#glow)"/>
<g clip-path="url(#c)"><rect class="sheen" x="-90" y="-10" width="46" height="{h + 20}" fill="url(#sh)" transform="skewX(-20)"/></g>
<rect x=".75" y=".75" width="{w - 1.5}" height="{h - 1.5}" rx="13" fill="none" stroke="url(#edge)" stroke-width="1.5"/>
<rect x="8" y="8" width="32" height="32" rx="9" fill="url(#tile)" stroke="{colour}" stroke-opacity=".3"/>
{icons[icon_kind]}
<text x="52" y="29" class="m" font-size="14" font-weight="600" fill="{INK}">{esc(label)}</text>
"""
    return svg(w, h, label, body, css)


def wave(base, amp, wavelength, width):
    d = [f"M0,{base:.1f}"]
    d += [f"L{x},{base + amp * math.sin(2 * math.pi * x / wavelength):.1f}" for x in range(8, width + 1, 8)]
    return " ".join(d)


def footer():
    W, H = 1000, 170
    ly, x_start, x_end, period = 62, 70, 930, 4.0
    waves = [(14, 250, CYAN, .35, 9), (22, 500, BLUE, .4, 15), (9, 200, ICE, .25, 7)]
    css = f"""
.nd{{animation:nd {period / 2}s linear infinite}}
@keyframes nd{{0%{{opacity:1}}25%,100%{{opacity:.35}}}}
.halo{{transform-box:fill-box;transform-origin:center;animation:halo 3s ease-out infinite}}
@keyframes halo{{0%{{transform:scale(.6);opacity:.7}}100%{{transform:scale(1.8);opacity:0}}}}
""" + "".join(f".w{i}{{animation:w{i} {dur}s linear infinite}}@keyframes w{i}{{to{{transform:translateX(-{lam}px)}}}}\n"
              for i, (_, lam, _, _, dur) in enumerate(waves))
    out = [backdrop(W, H), f"""<defs>
  <linearGradient id="line" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="{BLUE}" stop-opacity="0"/><stop offset=".2" stop-color="{BLUE}" stop-opacity=".7"/><stop offset=".5" stop-color="{ICE}"/><stop offset=".8" stop-color="{CYAN}" stop-opacity=".7"/><stop offset="1" stop-color="{CYAN}" stop-opacity="0"/></linearGradient>
  <linearGradient id="hub" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{ICE}"/><stop offset="1" stop-color="{BLUE}"/></linearGradient>
  <linearGradient id="hairL" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="{BLUE}" stop-opacity="0"/><stop offset="1" stop-color="{BLUE}" stop-opacity=".8"/></linearGradient>
  <linearGradient id="hairR" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="{ICE}" stop-opacity=".8"/><stop offset="1" stop-color="{ICE}" stop-opacity="0"/></linearGradient>
  <linearGradient id="edgesFade" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#000"/><stop offset=".25" stop-color="#fff"/><stop offset=".75" stop-color="#fff"/><stop offset="1" stop-color="#000"/></linearGradient>
  <mask id="fade" maskUnits="userSpaceOnUse" x="0" y="0" width="{W}" height="{H}"><rect width="{W}" height="{H}" fill="url(#edgesFade)"/></mask>
  <filter id="glow" x="-100%" y="-100%" width="300%" height="300%"><feGaussianBlur stdDeviation="3" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
</defs>
<g mask="url(#fade)">""" + "".join(
        f'<path class="w{i}" d="{wave(ly, amp, lam, W + lam)}" fill="none" stroke="{colour}" stroke-opacity="{op}" stroke-width="1.2"/>'
        for i, (amp, lam, colour, op, _) in enumerate(waves)) + f"""</g>
<rect x="{x_start}" y="{ly - 3}" width="{x_end - x_start}" height="6" fill="url(#line)" opacity=".12"/>
<rect x="{x_start}" y="{ly - .7}" width="{x_end - x_start}" height="1.4" fill="url(#line)"/>"""]
    for i in range(2):
        out.append(f'<circle r="3.2" fill="#fff" filter="url(#glow)"><animateMotion dur="{period}s" begin="-{i * period / 2}s" repeatCount="indefinite" path="M{x_start},{ly} H{x_end}"/></circle>')
    nodes = [130 + k * 92.5 for k in range(9)]
    for k, x in enumerate(nodes):
        if k == 4:
            continue
        colour = BLUE if k < 4 else CYAN
        delay = ((x - x_start) / (x_end - x_start) * period) % (period / 2)
        out.append(f'<g class="nd" style="animation-delay:{delay - period / 2:.2f}s">'
                   f'<polygon points="{hexagon(x, ly, 9)}" fill="{CARD}" stroke="{colour}" stroke-width="1.4"/>'
                   f'<circle cx="{x}" cy="{ly}" r="2.6" fill="{colour}"/></g>')
    out.append(f'<polygon class="halo" points="{hexagon(500, ly, 24)}" fill="none" stroke="{ICE}" stroke-width="1.2"/>'
               f'<polygon points="{hexagon(500, ly, 22)}" fill="{PANEL}" stroke="url(#hub)" stroke-width="2"/>'
               f'<path d="M490,{ly + 1} L497,{ly + 8} L511,{ly - 7}" fill="none" stroke="{ICE}" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round" filter="url(#glow)"/>')
    out.append(f'<text x="{W / 2}" y="122" class="m" font-size="15" text-anchor="middle" fill="{INK}">visit confirmed · thanks for validating this block</text>')
    # Signature tagline in the shared gradient, framed by two hairlines that fade outwards.
    out.append(f'<text x="{W / 2 + 2}" y="148" class="m" font-size="12.5" font-weight="600" letter-spacing="4" text-anchor="middle" fill="url(#grad)">DON\'T TRUST. VERIFY.</text>')
    out.append(f'<rect x="{W / 2 - 240}" y="143.5" width="100" height="1" fill="url(#hairL)"/>'
               f'<rect x="{W / 2 + 140}" y="143.5" width="100" height="1" fill="url(#hairR)"/>')
    out.append(border(W, H, dur=10))
    return svg(W, H, "Visit confirmed — thanks for stopping by", "\n".join(out), css)


def main():
    ASSETS.mkdir(exist_ok=True)
    files = {
        "hero.svg": hero(),
        "genesis.svg": genesis(),
        "footer.svg": footer(),
    }
    for i, (name, label, colour, icon_kind) in enumerate(BUTTONS):
        files[f"{name}.svg"] = button(label, colour, icon_kind, delay=i * 0.8)
    for name, text in files.items():
        (ASSETS / name).write_text(text, encoding="utf-8")
        print(f"wrote assets/{name} ({len(text) / 1024:.1f} KB)")


if __name__ == "__main__":
    main()
