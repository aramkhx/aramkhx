#!/usr/bin/env python3
"""Render assets/chain-activity.svg: the last year of GitHub contributions as an isometric
chain of mined blocks, plus live profile stats.

Runs daily from .github/workflows/chain-activity.yml. Standard library, plus (when installed)
Pillow + numpy to pre-render the tower glow and fonttools + uharfbuzz to outline the big total.
Without them it falls back to a live SVG blur and live text.
  GH_USER       GitHub login (default: aramkhx)
  GITHUB_TOKEN  optional, raises the REST API rate limit
"""

import datetime as dt
import json
import math
import os
import random
import re
import sys
import time
import urllib.request
from pathlib import Path

try:
    import bake  # Pillow + numpy
except ImportError:
    bake = None
from theme import BLUE, CYAN, DIM, GOLD, GRAD_STOPS, ICE, INK, MUTED, PANEL, SKY, border, card, esc, glass, halo_gradient, icon, pts, svg

USER = os.environ.get("GH_USER", "aramkhx")
TOKEN = os.environ.get("GITHUB_TOKEN")
OUT = Path(__file__).resolve().parent.parent / "assets" / "chain-activity.svg"
NUMBER_FONT = Path(__file__).resolve().parent / "fonts" / "InterDisplay-ExtraBold-latin.ttf"

# Top-face colour per GitHub contribution level (0 = empty day).
LEVELS = ["#141C30", "#1E4FBF", BLUE, "#00B4F0", "#7FE9FF"]


def get(url, api=False, attempts=3):
    headers = {"User-Agent": f"{USER}-profile-readme"}
    if api:
        headers["Accept"] = "application/vnd.github+json"
        if TOKEN:
            headers["Authorization"] = f"Bearer {TOKEN}"
    for attempt in range(attempts):  # ride out a brief GitHub hiccup instead of failing the daily run
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=30) as resp:
                return resp.read().decode()
        except OSError:
            if attempt == attempts - 1:
                raise
            time.sleep(5 * (attempt + 1))


def calendar(user):
    """[(date, count, level)] for the public contribution calendar, oldest first."""
    page = get(f"https://github.com/users/{user}/contributions")
    tips = {m[0]: m[1] for m in re.findall(r'<tool-tip[^>]*\bfor="([^"]+)"[^>]*>([^<]*)</tool-tip>', page)}
    days = []
    for tag in re.findall(r"<td\b[^>]*ContributionCalendar-day[^>]*>", page):
        attrs = dict(re.findall(r'([\w-]+)="([^"]*)"', tag))
        if "data-date" not in attrs:
            continue
        level = int(attrs.get("data-level", 0))
        m = re.match(r"\s*([\d,]+) contribution", tips.get(attrs.get("id", ""), ""))
        count = int(m.group(1).replace(",", "")) if m else (0 if attrs.get("id") in tips else level)
        days.append((dt.date.fromisoformat(attrs["data-date"]), count, level))
    if len(days) < 300:
        raise SystemExit(f"contribution calendar looks wrong ({len(days)} days parsed)")
    return sorted(days)


def profile(user):
    info = json.loads(get(f"https://api.github.com/users/{user}", api=True))
    stars, page = 0, 1
    while True:
        repos = json.loads(get(f"https://api.github.com/users/{user}/repos?per_page=100&type=owner&page={page}", api=True))
        stars += sum(r["stargazers_count"] for r in repos if not r["fork"])
        if len(repos) < 100:
            break
        page += 1
    return {"repos": info["public_repos"], "stars": stars}


def streaks(days):
    longest = run = 0
    for _, count, _ in days:
        run = run + 1 if count else 0
        longest = max(longest, run)
    current = 0
    tail = days[:-1] if days[-1][1] == 0 else days  # today may simply not have activity yet
    for _, count, _ in reversed(tail):
        if not count:
            break
        current += 1
    return current, longest


def shade(hex_colour, k):
    r, g, b = (int(hex_colour[i:i + 2], 16) for i in (1, 3, 5))
    return f"#{int(r * k):02X}{int(g * k):02X}{int(b * k):02X}"


def count_up(total, number, start=0.4, span=1.7, steps=16):
    """Stacked numbers that flash in sequence, so the total appears to count up from zero.

    number(value, attrs, inner) draws one number. Only the final number is visible without
    SMIL, so static renderers still show the total.
    """
    seq = []
    for k in range(1, steps + 1):
        value = round(total * (1 - (1 - k / steps) ** 3))
        if not seq or value != seq[-1]:
            seq.append(value)
    end = start + span
    dur = end + 0.5
    times = [start + span * i / len(seq) for i in range(len(seq))]
    out = []
    for i, value in enumerate(seq[:-1]):
        out.append(number(value, 'opacity="0"', f'<animate attributeName="opacity" dur="{dur:.2f}s" fill="freeze" calcMode="discrete" '
                                                 f'keyTimes="0;{times[i] / dur:.3f};{times[i + 1] / dur:.3f}" values="0;1;0"/>'))
    final = (f'<animate attributeName="opacity" dur="{dur:.2f}s" fill="freeze" calcMode="discrete" '
             f'keyTimes="0;{times[-1] / dur:.3f}" values="0;1"/>')
    return "".join(out), final


def render(days, stats):
    W, H = 1000, 450
    today = days[-1][0]
    total = sum(c for _, c, _ in days)
    active = sum(1 for _, c, _ in days if c)
    best_day = max(days, key=lambda d: d[1])
    current, longest = streaks(days)
    peak = max(best_day[1], 1)
    rnd = random.Random(7)  # fixed seed: the starfield should not churn between daily runs

    # Isometric-ish projection: weeks run up-right along u, weekdays down-right along v.
    u, v, gap, max_h = (12.0, -2.2), (8.5, 6.5), 0.8, 112.0
    first = days[0][0] - dt.timedelta(days=(days[0][0].weekday() + 1) % 7)

    def cell(day):
        return (day - first).days // 7, (day.weekday() + 1) % 7

    def ground(c, r):
        return c * u[0] + r * v[0], c * u[1] + r * v[1]

    # Fit the whole ribbon (towers included) into the space right of the stats panel.
    weeks = cell(today)[0] + 1
    corners = [ground(c, r) for c in (0, weeks) for r in (0, 7)]
    gx0, gx1 = min(x for x, _ in corners), max(x for x, _ in corners)
    gy0, gy1 = min(y for _, y in corners) - max_h, max(y for _, y in corners)
    box = (330, 92, 972, 404)
    scale = min((box[2] - box[0]) / (gx1 - gx0), (box[3] - box[1]) / (gy1 - gy0))
    ox = box[0] + ((box[2] - box[0]) - (gx1 - gx0) * scale) / 2 - gx0 * scale
    oy = box[1] + ((box[3] - box[1]) - (gy1 - gy0) * scale) / 2 - gy0 * scale

    def P(c, r, h=0.0):
        x, y = ground(c, r)
        return ox + x * scale, oy + (y - h) * scale

    def height(count):
        return 12 + (max_h - 12) * math.sqrt(count / peak) if count else 2.5

    tiles, overlays, months, glows = [], [], [], {}
    d = (1 - gap) / 2
    angle = math.degrees(math.atan2(u[1], u[0]))
    column = None
    # Back-to-front, so each week column is drawn as one run. The column's group drives the light
    # wave for all of its tiles (one animation per week instead of one per day): empty tops take
    # their fill from the inherited `color`, flash overlays their fill-opacity.
    for day, count, level in sorted(days, key=lambda t: (-cell(t[0])[0], cell(t[0])[1])):
        c, r = cell(day)
        h = height(count)
        if c != column:
            if column is not None:
                tiles.append("</g>")
            column = c
            tiles.append(f'<g class="k" style="animation-delay:{3.2 + c * 0.05:.2f}s">')
        a, b, cc, dd = (c + d, r + d), (c + 1 - d, r + d), (c + 1 - d, r + 1 - d), (c + d, r + 1 - d)
        top = pts(*(P(*q, h) for q in (a, b, cc, dd)))
        left = pts(P(*a), P(*dd), P(*dd, h), P(*a, h))
        front = pts(P(*dd), P(*cc), P(*cc, h), P(*dd, h))
        if count:
            lvl = min(level, 4) or 1
            colour = LEVELS[lvl]
            drop = 0.3 + c * 0.028
            tiles.append(
                f'<g class="t" style="animation-delay:{drop:.2f}s">'
                f'<polygon points="{left}" fill="url(#L{lvl})"/>'
                f'<polygon points="{front}" fill="url(#F{lvl})"/>'
                f'<polygon points="{top}" fill="{colour}" stroke="#fff" stroke-opacity=".45" stroke-width=".7"/>'
                f'<polygon class="fl" points="{top}" fill="#fff" style="animation-delay:{drop + .55:.2f}s"/></g>')
            glows.setdefault(colour, []).append([P(*q, h) for q in (a, b, cc, dd)])
        else:
            tiles.append(
                f'<g class="e" style="animation-delay:{c * 0.012:.2f}s">'
                f'<polygon points="{left}" fill="#0A0F1C"/><polygon points="{front}" fill="#0E1526"/>'
                f'<polygon points="{top}" fill="currentColor"/></g>')
        if day == best_day[0] and count:
            tx, ty = P(c + .5, r + .5, h)
            gx, gy = P(c + .5, r + .5)
            label = f'▲ {count} tx · {day.strftime("%b %d")}'
            lw = len(label) * 6.6 + 18
            overlays.append(
                "".join(f'<ellipse class="ripple" cx="{gx:.1f}" cy="{gy:.1f}" rx="9" ry="3.4" fill="none" stroke="{ICE}" stroke-width="1" '
                        f'vector-effect="non-scaling-stroke" style="animation-delay:{3 + k * 1.2:.1f}s"/>' for k in range(2))
                + f'<polygon class="glow" points="{top}" fill="{colour}" filter="url(#blur)"/>'
                f'<line x1="{tx:.1f}" y1="{ty - 4:.1f}" x2="{tx:.1f}" y2="{ty - 30:.1f}" stroke="{colour}" stroke-width="1" stroke-dasharray="2 3"/>'
                f'<g class="pop"><rect x="{tx - lw / 2:.1f}" y="{ty - 52:.1f}" width="{lw:.1f}" height="22" rx="11" fill="{PANEL}" fill-opacity=".92" stroke="{colour}" stroke-opacity=".6"/>'
                f'<text x="{tx:.1f}" y="{ty - 37:.1f}" class="m" font-size="11" text-anchor="middle" fill="{INK}">{esc(label)}</text></g>')
        if day == today:
            overlays.append(f'<polygon class="live" points="{top}" fill="none" stroke="{CYAN}" stroke-width="1.6"/>')
        if r == 0 and day.day <= 7:
            mx, my = P(c + .5, 7.9)
            months.append(f'<text transform="translate({mx:.1f} {my:.1f}) rotate({angle:.1f})" class="m" font-size="10" '
                          f'fill="{DIM}">{day.strftime("%b").upper()}</text>')
    tiles.append("</g>")

    # The chain links each week's tallest tower, oldest to newest, with a comet riding it.
    # One node per week keeps the line flowing even when most days are active.
    peaks = {}
    for day, count, _ in days:
        if count and count >= peaks.get(cell(day)[0], (None, 0))[1]:
            peaks[cell(day)[0]] = (day, count)
    links = [P(cell(day)[0] + .5, cell(day)[1] + .5, height(count)) for _, (day, count) in sorted(peaks.items())]
    chain_d = "M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in links)
    chain_len = sum(math.dist(links[i], links[i + 1]) for i in range(len(links) - 1))
    comet_dur = max(5.0, chain_len / 120)
    nodes = '<path fill="#fff" d="' + "".join(f"M{x - 1.8:.1f},{y:.1f}a1.8,1.8 0 1,0 3.6,0a1.8,1.8 0 1,0 -3.6,0" for x, y in links) + '"/>'
    chain = comet = ""
    if links:
        chain = (f'<g class="chain"><path d="{chain_d}" fill="none" stroke="{CYAN}" stroke-opacity=".16" stroke-width="5" stroke-linejoin="round"/>'
                 f'<path class="flow" d="{chain_d}" fill="none" stroke="{ICE}" stroke-opacity=".6" stroke-width="1"/>{nodes}</g>')
    if len(links) > 1:  # a bright head and two fading tail beads, each starting a beat later
        for i, (r, fill, op, halo) in enumerate([(3.6, "#fff", 1, True), (2.6, ICE, .6, False), (1.8, CYAN, .35, False)]):
            begin = f"{3.4 + i * .1:.1f}s"
            glow = '<circle r="10.8" fill="url(#haloComet)"/>' if halo else ""
            comet += (f'<g opacity="0"><set attributeName="opacity" to="{op}" begin="{begin}"/>'
                      f'<animateMotion dur="{comet_dur:.1f}s" begin="{begin}" repeatCount="indefinite" path="{chain_d}"/>'
                      f'{glow}<circle r="{r}" fill="{fill}"/></g>')

    sparks = []
    for k, (day, count, _) in enumerate(sorted((t for t in days if t[1]), key=lambda t: -t[1])[:5]):
        sx, sy = P(cell(day)[0] + .5, cell(day)[1] + .5, height(count))
        sparks += [f'<circle class="spark" cx="{sx:.1f}" cy="{sy:.1f}" r="1.8" fill="{ICE}" opacity="0" '
                   f'style="animation-delay:{3 + k * .45 + j * 1.3:.2f}s"/>' for j in range(2)]

    stars = "".join(f'<circle class="star" cx="{rnd.uniform(16, 984):.0f}" cy="{rnd.uniform(70, 436):.0f}" r="{rnd.uniform(.4, 1.1):.1f}" '
                    f'fill="{rnd.choice([ICE, "#fff", SKY])}" style="animation-delay:-{rnd.uniform(0, 6):.1f}s;animation-duration:{rnd.uniform(3, 7):.1f}s"/>'
                    for _ in range(40))

    tiles_xy = [(28, 212), (164, 212), (28, 280), (164, 280), (28, 348), (164, 348)]
    tile_data = [
        ("ACTIVE DAYS", f"{active}", BLUE, "calendar"),
        ("BEST DAY", f"{best_day[1]}", CYAN, "star"),
        ("LONGEST STREAK", f"{longest}d", ICE, "flame"),
        ("CURRENT STREAK", f"{current}d", SKY, "bolt"),
        ("PUBLIC REPOS", f"{stats['repos']}", BLUE, "repo"),
        ("STARS EARNED", f"{stats['stars']}", GOLD, "star"),
    ]
    stat_tiles = "".join(
        f'<g class="tile" style="animation-delay:{.2 + i * .08:.2f}s">'
        + glass(x, y, 126, 58, rx=10)
        + f'<rect x="{x + 14}" y="{y}" width="26" height="2" rx="1" fill="{colour}"/>'
        + icon(kind, x + 100, y + 33, colour)
        + f'<text x="{x + 14}" y="{y + 22}" class="m" font-size="9.5" letter-spacing="1" fill="{MUTED}">{label}</text>'
        f'<text x="{x + 14}" y="{y + 46}" font-size="20" font-weight="700" fill="{INK}">{value}</text></g>'
        for i, ((x, y), (label, value, colour, kind)) in enumerate(zip(tiles_xy, tile_data)))

    # The big total is drawn as glyph outlines in the shared gradient. WebKit (Safari, GitHub's
    # mobile app) paints gradient-filled text at low resolution, so live text would look soft.
    nx, ny, size = 26, 162, 64
    grads = []

    def outlined(value):
        d, _, advance = bake.text_outline(f"{value:,}", str(NUMBER_FONT), size, nx, ny)
        return f'<path d="{d}"/>', advance

    def number(value, attrs, inner, fill=None):
        if outlines:
            uses, advance = outlined(value)
            if fill is None:  # the gradient spans the number, as it did across the text box
                fill = f"url(#n{len(grads)})"
                grads.append(f'<linearGradient id="n{len(grads)}" gradientUnits="userSpaceOnUse" x1="{nx}" y1="0" '
                             f'x2="{nx + advance:.1f}" y2="0">{GRAD_STOPS}</linearGradient>')
            return f'<g fill="{fill}" {attrs}>{inner}{uses}</g>'
        return f'<text x="{nx}" y="{ny}" font-size="{size}" font-weight="800" fill="{fill or "url(#grad)"}" {attrs}>{value:,}{inner}</text>'

    try:
        outlines = bake is not None and bool(bake.text_outline("0", str(NUMBER_FONT), size, 0, 0)[0])
    except ImportError:  # fonttools / uharfbuzz missing: fall back to live text
        outlines = False
    ticks, final_anim = count_up(total, number)
    # Built before the SVG body, which lists every gradient these calls register.
    total_bloom = number(total, 'opacity=".6" filter="url(#bloom)"', final_anim, fill=BLUE)
    total_text = number(total, "", final_anim)
    total_box_w = outlined(total)[1] if outlines else len(f"{total:,}") * size * .6
    ascent, descent = .97 * size, .24 * size  # the text box the bloom's region was designed on
    bloom_region = (f'filterUnits="userSpaceOnUse" x="{nx - .3 * total_box_w:.1f}" y="{ny - ascent - .6 * (ascent + descent):.1f}" '
                    f'width="{1.6 * total_box_w:.1f}" height="{2.2 * (ascent + descent):.1f}"')

    # Blurred light over the tower tops. Baked into a bitmap when possible: a live blur filter is
    # recomputed on every animation frame. Otherwise one path per colour keeps the filter cheap.
    if bake and glows:
        sd, margin = 5, 15
        x0, y0, gw, gh = bake.bbox([p for quads in glows.values() for quad in quads for p in quad])
        canvas = bake.Canvas(x0 - margin, y0 - margin, gw + 2 * margin, gh + 2 * margin, .5)
        for colour, quads in glows.items():
            canvas.paint(lambda d, tf, s, quads=quads: [d.polygon([tf(*p) for p in q], fill=255) for q in quads], colour)
        tops = f'<g class="tops" opacity=".7">{canvas.blur(sd).image()}</g>'
    else:
        tops = ('<g class="tops" opacity=".7" filter="url(#blur)">'
                + "".join(f'<path fill="{colour}" d="{"".join("M" + pts(*q).replace(" ", " L") + "Z" for q in quads)}"/>'
                          for colour, quads in glows.items()) + "</g>")

    # Soft light pooled under the ribbon, aligned with the week axis.
    fx, fy = P(weeks / 2, 3.5)

    note = f"last 365 days · synced {today:%Y-%m-%d}"
    live_x = W - 28 - len(note) * 7.2 - 16

    side_grads = "".join(
        f'<linearGradient id="{kind}{lvl}" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{shade(LEVELS[lvl], k1)}"/>'
        f'<stop offset="1" stop-color="{shade(LEVELS[lvl], k2)}"/></linearGradient>'
        for lvl in range(1, 5) for kind, k1, k2 in (("L", .55, .16), ("F", .85, .3)))

    legend = "".join(f'<rect x="{900 + i * 13}" y="{H - 38}" width="10" height="10" rx="2" fill="{c}"/>'
                     for i, c in enumerate(LEVELS))

    css = """
.t{animation:drop .9s cubic-bezier(.2,.9,.3,1.15) both}
@keyframes drop{from{opacity:0;transform:translateY(-46px)}to{opacity:1;transform:none}}
.e{animation:fade .5s ease-out both}
@keyframes fade{from{opacity:0}to{opacity:1}}
.k{color:#141C30;fill-opacity:0;animation:wave 7s ease-out infinite backwards}
@keyframes wave{0%,14%,100%{color:#141C30;fill-opacity:0}3%{color:#2D6FDB;fill-opacity:.55}}
.k polygon{fill-opacity:1}
.k .fl{fill-opacity:inherit;animation:land .9s ease-out backwards}
@keyframes land{0%{fill-opacity:0}20%{fill-opacity:.85}100%{fill-opacity:0}}
.glow{animation:glow 2.4s ease-in-out infinite}
@keyframes glow{0%,100%{opacity:.25}50%{opacity:.9}}
.live{animation:live 1.2s ease-in-out infinite}
@keyframes live{0%,100%{opacity:1}50%{opacity:.15}}
.tops{animation:tops 1.4s 2.4s ease-out both}
@keyframes tops{from{opacity:0}to{opacity:.7}}
.chain{animation:chain 1.2s 2.8s ease-out both}
@keyframes chain{from{opacity:0}to{opacity:1}}
.flow{stroke-dasharray:3 6;animation:flow 1s linear infinite}
@keyframes flow{to{stroke-dashoffset:-9}}
.spark{animation:spark 2.6s ease-out infinite}
@keyframes spark{0%{transform:translateY(0);opacity:0}15%{opacity:1}100%{transform:translateY(-36px);opacity:0}}
.ripple{transform-box:fill-box;transform-origin:center;animation:ripple 2.4s ease-out infinite;opacity:0}
@keyframes ripple{0%{transform:scale(1);opacity:.8}100%{transform:scale(6);opacity:0}}
.pop{animation:pop .6s 2.9s cubic-bezier(.2,.9,.3,1.3) both}
@keyframes pop{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:none}}
.tile{animation:tile .6s ease-out both}
@keyframes tile{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:none}}
.star{animation:star 5s ease-in-out infinite}
@keyframes star{0%,100%{opacity:.1}50%{opacity:.7}}
"""
    body = f"""{card(W, H, "02", "CHAIN ACTIVITY", note)}
<defs>
  <filter id="blur" x="-100%" y="-100%" width="300%" height="300%"><feGaussianBlur stdDeviation="5"/></filter>
  <filter id="bloom" {bloom_region}><feGaussianBlur stdDeviation="12"/></filter>
  {"".join(grads)}
  {halo_gradient("haloComet", "#FFFFFF", 3.6, 3, 10.8)}
  <radialGradient id="pool"><stop offset="0" stop-color="{CYAN}" stop-opacity=".18"/><stop offset=".6" stop-color="{BLUE}" stop-opacity=".06"/><stop offset="1" stop-color="{BLUE}" stop-opacity="0"/></radialGradient>
  {side_grads}
</defs>
<g clip-path="url(#frame)">{stars}</g>
<circle class="pulse" cx="{live_x - 44:.0f}" cy="36" r="3.5" fill="{CYAN}"/>
<text x="{live_x:.0f}" y="40" class="m" font-size="11" font-weight="700" letter-spacing="1.5" text-anchor="end" fill="{CYAN}">LIVE</text>
<text x="28" y="96" class="m" font-size="12" letter-spacing="3" fill="{MUTED}">BLOCKS MINED</text>
{total_bloom}
{ticks}
{total_text}
<text x="28" y="190" font-size="13" fill="{MUTED}">contributions in the last year</text>
{stat_tiles}
<ellipse cx="{fx:.1f}" cy="{fy:.1f}" rx="370" ry="100" transform="rotate({angle:.1f} {fx:.1f} {fy:.1f})" fill="url(#pool)"/>
<g>{"".join(tiles)}</g>
{tops}
{chain}
{comet}
{"".join(sparks)}
{"".join(overlays)}
{"".join(months)}
<text x="892" y="{H - 29}" class="m" font-size="10" text-anchor="end" fill="{DIM}">less</text>
{legend}
<text x="{900 + len(LEVELS) * 13 + 2}" y="{H - 29}" class="m" font-size="10" fill="{DIM}">more</text>
{border(W, H)}
"""
    title = f"{USER} chain activity: {total} contributions in the last year"
    return svg(W, H, title, body, css)


def main():
    days = calendar(USER)
    stats = profile(USER)
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(render(days, stats), encoding="utf-8")
    print(f"wrote {OUT.relative_to(OUT.parent.parent)}: {sum(c for _, c, _ in days)} contributions, {stats}")


if __name__ == "__main__":
    sys.exit(main())
