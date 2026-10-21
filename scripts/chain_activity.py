#!/usr/bin/env python3
"""Render assets/chain-activity.svg: the last year of GitHub contributions as an isometric
chain of mined blocks, plus live profile stats.

Runs daily from .github/workflows/chain-activity.yml. Standard library only.
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

from theme import BLUE, CYAN, DIM, GOLD, ICE, INK, MUTED, PANEL, SKY, border, card, esc, glass, icon, pts, svg

USER = os.environ.get("GH_USER", "aramkhx")
TOKEN = os.environ.get("GITHUB_TOKEN")
OUT = Path(__file__).resolve().parent.parent / "assets" / "chain-activity.svg"

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


def count_up(total, x, y, attrs, start=0.4, span=1.7, steps=16):
    """Stacked numbers that flash in sequence, so the total appears to count up from zero.

    Only the final number is visible without SMIL, so static renderers still show the total.
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
        out.append(f'<text x="{x}" y="{y}" {attrs} opacity="0">{value:,}'
                   f'<animate attributeName="opacity" dur="{dur:.2f}s" fill="freeze" calcMode="discrete" '
                   f'keyTimes="0;{times[i] / dur:.3f};{times[i + 1] / dur:.3f}" values="0;1;0"/></text>')
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

    tiles, overlays, months, glows = [], [], [], []
    d = (1 - gap) / 2
    angle = math.degrees(math.atan2(u[1], u[0]))
    for day, count, level in sorted(days, key=lambda t: (-cell(t[0])[0], cell(t[0])[1])):
        c, r = cell(day)
        h = height(count)
        a, b, cc, dd = (c + d, r + d), (c + 1 - d, r + d), (c + 1 - d, r + 1 - d), (c + d, r + 1 - d)
        top = pts(*(P(*q, h) for q in (a, b, cc, dd)))
        left = pts(P(*a), P(*dd), P(*dd, h), P(*a, h))
        front = pts(P(*dd), P(*cc), P(*cc, h), P(*dd, h))
        wave = 3.2 + c * 0.05
        if count:
            lvl = min(level, 4) or 1
            colour = LEVELS[lvl]
            drop = 0.3 + c * 0.028
            tiles.append(
                f'<g class="t" style="animation-delay:{drop:.2f}s">'
                f'<polygon points="{left}" fill="url(#L{lvl})"/>'
                f'<polygon points="{front}" fill="url(#F{lvl})"/>'
                f'<polygon points="{top}" fill="{colour}" stroke="#fff" stroke-opacity=".45" stroke-width=".7"/>'
                f'<polygon class="fl" points="{top}" fill="#fff" opacity="0" style="animation-delay:{wave:.2f}s"/>'
                f'<polygon class="land" points="{top}" fill="#fff" opacity="0" style="animation-delay:{drop + .55:.2f}s"/></g>')
            glows.append(f'<polygon points="{top}" fill="{colour}"/>')
        else:
            tiles.append(
                f'<g class="e" style="animation-delay:{c * 0.012:.2f}s">'
                f'<polygon points="{left}" fill="#0A0F1C"/><polygon points="{front}" fill="#0E1526"/>'
                f'<polygon class="wv" points="{top}" fill="{LEVELS[0]}" style="animation-delay:{wave:.2f}s"/></g>')
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
    nodes = "".join(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="1.8" fill="#fff"/>' for x, y in links)
    chain = comet = ""
    if links:
        chain = (f'<g class="chain"><path d="{chain_d}" fill="none" stroke="{CYAN}" stroke-opacity=".16" stroke-width="5" stroke-linejoin="round"/>'
                 f'<path class="flow" d="{chain_d}" fill="none" stroke="{ICE}" stroke-opacity=".6" stroke-width="1"/>{nodes}</g>')
    if len(links) > 1:  # a bright head and two fading tail beads, each starting a beat later
        for i, (r, fill, op, extra) in enumerate([(3.6, "#fff", 1, ' filter="url(#glowF)"'), (2.6, ICE, .6, ""), (1.8, CYAN, .35, "")]):
            begin = f"{3.4 + i * .1:.1f}s"
            comet += (f'<circle r="{r}" fill="{fill}" opacity="0"{extra}><set attributeName="opacity" to="{op}" begin="{begin}"/>'
                      f'<animateMotion dur="{comet_dur:.1f}s" begin="{begin}" repeatCount="indefinite" path="{chain_d}"/></circle>')

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

    number = 'font-size="64" font-weight="800"'
    ticks, final_anim = count_up(total, 26, 162, f'{number} fill="url(#grad)"')

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
.land{animation:land .9s ease-out both}
@keyframes land{0%{opacity:0}20%{opacity:.85}100%{opacity:0}}
.fl{animation:fl 7s ease-out infinite}
@keyframes fl{0%{opacity:0}3%{opacity:.55}14%,100%{opacity:0}}
.wv{animation:wv 7s ease-out infinite}
@keyframes wv{0%,14%,100%{fill:#141C30}3%{fill:#2D6FDB}}
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
  <filter id="bloom" x="-30%" y="-60%" width="160%" height="220%"><feGaussianBlur stdDeviation="12"/></filter>
  <filter id="glowF" x="-100%" y="-100%" width="300%" height="300%"><feGaussianBlur stdDeviation="3" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
  <radialGradient id="pool"><stop offset="0" stop-color="{CYAN}" stop-opacity=".18"/><stop offset=".6" stop-color="{BLUE}" stop-opacity=".06"/><stop offset="1" stop-color="{BLUE}" stop-opacity="0"/></radialGradient>
  {side_grads}
</defs>
<g clip-path="url(#frame)">{stars}</g>
<circle class="pulse" cx="{live_x - 44:.0f}" cy="36" r="3.5" fill="{CYAN}"/>
<text x="{live_x:.0f}" y="40" class="m" font-size="11" font-weight="700" letter-spacing="1.5" text-anchor="end" fill="{CYAN}">LIVE</text>
<text x="28" y="96" class="m" font-size="12" letter-spacing="3" fill="{MUTED}">BLOCKS MINED</text>
<text x="26" y="162" {number} fill="{BLUE}" opacity=".6" filter="url(#bloom)">{total:,}{final_anim}</text>
{ticks}
<text x="26" y="162" {number} fill="url(#grad)">{total:,}{final_anim}</text>
<text x="28" y="190" font-size="13" fill="{MUTED}">contributions in the last year</text>
{stat_tiles}
<ellipse cx="{fx:.1f}" cy="{fy:.1f}" rx="370" ry="100" transform="rotate({angle:.1f} {fx:.1f} {fy:.1f})" fill="url(#pool)"/>
<g>{"".join(tiles)}</g>
<g class="tops" opacity=".7" filter="url(#blur)">{"".join(glows)}</g>
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
