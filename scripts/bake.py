"""Pre-render SVG blur filters into small embedded PNGs (used by build_assets.py).

An animated SVG shown as an <img> is repainted every frame, and a feGaussianBlur filter
is recomputed on each repaint. Blurred light is soft by nature, so a baked bitmap of the
same blur looks identical while costing the browser almost nothing to draw.

Needs:  pip install pillow numpy   (text_outline also needs: pip install fonttools uharfbuzz)
"""

import base64
import io
import re

import numpy as np
from PIL import Image, ImageDraw

SUPERSAMPLE = 4  # draw shapes this much finer than the bitmap, then average down


def _rgb(colour):
    return np.array([int(colour[i:i + 2], 16) for i in (1, 3, 5)], dtype=np.float64) / 255


def _gauss(a, sd, axis):
    """Separable Gaussian along one axis; outside the canvas counts as transparent, like a filter region."""
    if sd <= 0:
        return a
    r = int(np.ceil(3 * sd))
    k = np.exp(-np.arange(-r, r + 1) ** 2 / (2 * sd * sd))
    k /= k.sum()
    pad = [(0, 0)] * a.ndim
    pad[axis] = (r, r)
    p = np.pad(a, pad)
    out = np.zeros_like(a)
    n = a.shape[axis]
    for i, w in enumerate(k):
        out += w * np.take(p, range(i, i + n), axis=axis)
    return out


class Canvas:
    """A premultiplied RGBA float canvas covering a region of SVG user space."""

    def __init__(self, x, y, w, h, scale):
        self.x, self.y, self.w, self.h, self.scale = x, y, w, h, scale
        self.px = max(1, round(w * scale)), max(1, round(h * scale))
        self.rgba = np.zeros((self.px[1], self.px[0], 4))

    def _mask(self, draw_fn):
        s = self.scale * SUPERSAMPLE
        img = Image.new("L", (self.px[0] * SUPERSAMPLE, self.px[1] * SUPERSAMPLE), 0)
        draw_fn(ImageDraw.Draw(img), lambda X, Y: ((X - self.x) * s, (Y - self.y) * s), s)
        img = img.resize(self.px, Image.BOX)
        return np.asarray(img, dtype=np.float64) / 255

    def paint(self, draw_fn, colour, opacity=1.0):
        """Composite one shape (drawn in white by draw_fn) with source-over."""
        a = self._mask(draw_fn)[..., None] * opacity
        src = np.concatenate([_rgb(colour) * a, a], axis=2)
        self.rgba = src + self.rgba * (1 - a)

    def polygon(self, points, colour, opacity=1.0):
        self.paint(lambda d, tf, s: d.polygon([tf(*p) for p in points], fill=255), colour, opacity)

    def blur(self, sd):
        sd *= self.scale
        self.rgba = _gauss(_gauss(self.rgba, sd, 0), sd, 1)
        return self

    def image(self, opacity=None, attrs=""):
        """<image> element carrying the canvas as an embedded PNG, placed back in user space."""
        a = self.rgba[..., 3:]
        rgb = np.where(a > 1e-6, self.rgba[..., :3] / np.maximum(a, 1e-6), 0)
        px = np.clip(np.round(np.concatenate([rgb, a], axis=2) * 255), 0, 255).astype(np.uint8)
        clear = px[..., 3] == 0
        seen = px[~clear][:, :3]
        if len(seen) and (seen == seen[0]).all():  # one colour: give empty pixels it too, so PNG packs tighter
            px[clear, :3] = seen[0]
        else:
            px[clear, :3] = 0
        img = Image.fromarray(px, "RGBA")
        if (px[..., 0] == px[..., 1]).all() and (px[..., 1] == px[..., 2]).all():
            img = img.convert("LA")
        buf = io.BytesIO()
        img.save(buf, "PNG", optimize=True)
        data = base64.b64encode(buf.getvalue()).decode()
        op = f' opacity="{opacity}"' if opacity is not None else ""
        return (f'<image x="{self.x:.1f}" y="{self.y:.1f}" width="{self.w:.1f}" height="{self.h:.1f}" '
                f'preserveAspectRatio="none"{op}{attrs} href="data:image/png;base64,{data}"/>')


def region(bbox, x=-.1, y=-.1, w=1.2, h=1.2):
    """A filter region from fractions of the bounding box, the way filter x/y/width/height work."""
    bx, by, bw, bh = bbox
    return bx + x * bw, by + y * bh, w * bw, h * bh


def flatten(d, steps=24):
    """Points of an absolute SVG path using M, L, C, S and Z (enough for the shapes here)."""
    tokens = re.findall(r"[MLCSZ]|-?\d*\.?\d+", d)
    pts, cur, last_ctrl, cmd, i = [], (0.0, 0.0), None, None, 0

    def num():
        nonlocal i
        i += 1
        return float(tokens[i - 1])

    while i < len(tokens):
        if tokens[i] in "MLCSZ":
            cmd = tokens[i]
            i += 1
            if cmd == "Z":
                continue
        if cmd in "ML":
            cur = (num(), num())
            pts.append(cur)
            last_ctrl = None
        else:
            if cmd == "C":
                c1 = (num(), num())
            else:  # S reflects the previous control point
                c1 = (2 * cur[0] - last_ctrl[0], 2 * cur[1] - last_ctrl[1]) if last_ctrl else cur
            c2, end = (num(), num()), (num(), num())
            for k in range(1, steps + 1):
                t = k / steps
                m = 1 - t
                pts.append((m ** 3 * cur[0] + 3 * m * m * t * c1[0] + 3 * m * t * t * c2[0] + t ** 3 * end[0],
                            m ** 3 * cur[1] + 3 * m * m * t * c1[1] + 3 * m * t * t * c2[1] + t ** 3 * end[1]))
            cur, last_ctrl = end, c2
    return pts


def bbox(points):
    xs, ys = [p[0] for p in points], [p[1] for p in points]
    return min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys)


def text_outline(text, font_path, size, x, baseline, width=None, letter_spacing=0.0):
    """Shape `text` with HarfBuzz and return it as vector outlines: (svg path data, contours, advance).

    Same layout rules the profile's CSS asks for (kerning on, ligatures off, letter-spacing),
    then stretched to `width` like textLength + lengthAdjust="spacingAndGlyphs". Outlines draw
    identically everywhere: no font fallback, and no WebKit textLength bug cutting the text.
    """
    import uharfbuzz as hb
    from fontTools.pens.svgPathPen import SVGPathPen
    from fontTools.pens.transformPen import TransformPen
    from fontTools.pens.basePen import BasePen
    from fontTools.ttLib import TTFont

    class _Flatten(BasePen):
        """Collects a glyph outline as flattened point lists (one per contour)."""

        def __init__(self, glyphset, contours, steps=8):
            super().__init__(glyphset)
            self.contours, self.steps = contours, steps

        def _moveTo(self, p):
            self.contours.append([p])

        def _lineTo(self, p):
            self.contours[-1].append(p)

        def _curveToOne(self, c1, c2, p):
            (x0, y0), n = self._getCurrentPoint(), self.steps
            for k in range(1, n + 1):
                t = k / n
                m = 1 - t
                self.contours[-1].append((m ** 3 * x0 + 3 * m * m * t * c1[0] + 3 * m * t * t * c2[0] + t ** 3 * p[0],
                                          m ** 3 * y0 + 3 * m * m * t * c1[1] + 3 * m * t * t * c2[1] + t ** 3 * p[1]))

        def _qCurveToOne(self, c, p):
            (x0, y0), n = self._getCurrentPoint(), self.steps
            for k in range(1, n + 1):
                t = k / n
                m = 1 - t
                self.contours[-1].append((m * m * x0 + 2 * m * t * c[0] + t * t * p[0], m * m * y0 + 2 * m * t * c[1] + t * t * p[1]))


    face = hb.Face(hb.Blob.from_file_path(font_path))
    buf = hb.Buffer()
    buf.add_str(text)
    buf.guess_segment_properties()
    hb.shape(hb.Font(face), buf, {"liga": False, "calt": False, "kern": True})
    k = size / face.upem
    run = sum(p.x_advance * k + letter_spacing for p in buf.glyph_positions)
    stretch = width / run if width else 1.0

    font = TTFont(font_path)
    glyphs = font.getGlyphSet()
    svg_pen = SVGPathPen(glyphs, ntos=lambda v: f"{v:.2f}".rstrip("0").rstrip("."))
    contours = []
    pen_x = 0.0
    for info, pos in zip(buf.glyph_infos, buf.glyph_positions):
        name = font.getGlyphName(info.codepoint)
        ox = x + (pen_x + pos.x_offset * k) * stretch
        oy = baseline - pos.y_offset * k
        matrix = (k * stretch, 0, 0, -k, ox, oy)  # font units are y-up
        glyphs[name].draw(TransformPen(svg_pen, matrix))
        glyphs[name].draw(TransformPen(_Flatten(glyphs, contours), matrix))
        pen_x += pos.x_advance * k + letter_spacing
    return svg_pen.getCommands(), contours, run * stretch


def shapes_glow(contours, box, colour, sd, scale, region_frac):
    """Blur of filled outlines (even-odd, so letter counters stay open) inside a filter region."""
    cv = Canvas(*region(box, *region_frac), scale)

    def draw(d, tf, s):
        img = d._image
        acc = np.zeros((img.size[1], img.size[0]), dtype=bool)
        for contour in contours:
            layer = Image.new("L", img.size, 0)
            ImageDraw.Draw(layer).polygon([tf(*p) for p in contour], fill=255)
            acc ^= np.asarray(layer) > 127
        img.paste(Image.fromarray((acc * 255).astype(np.uint8)))

    cv.paint(draw, colour)
    return cv.blur(sd)
