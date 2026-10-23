#!/usr/bin/env python3
"""logo_measure.py: measure a logo drawn as filled shapes, then put every part on the phi ladder.

A logo exported as outlines has no stroke-width or font-size to read. This script draws the
shapes and measures them itself, in SVG user units:

  shapes    each connected ink shape: its box, area and line width (median, p10, p90, min, max,
            and a flag when the width is uneven)
  gaps      the space between ink edges in narrow channels, per part: median, p10, p90, min, max,
            and where the narrowest ones are. Open space is left out.
  counters  closed holes: box, area and the widest circle inside
  parts     shapes grouped by large gaps, so an icon and a wordmark are two parts, and the gap
            between the parts
  word      for a part with three or more letters in a row: baseline, x-height, round height
            (the o with its overshoot), ascender, descender, stem width at mid x-height and the
            letter gaps at mid x-height

How it measures. The SVG is parsed (paths with every command, absolute and relative; rect, circle,
ellipse, polygon, polyline; transforms on groups and elements; fill-rule; simple masks) and drawn on
a raster fine enough that the thinnest line is about 20 px wide. Exact Euclidean distance transforms
(Felzenszwalb and Huttenlocher), inside and outside the ink, give each pixel its nearest edge. A line
width is twice the inside distance on the medial ridge; a gap is twice the outside distance on a
channel ridge. Both are then read against the vector outline (the distance to each side, summed), so
they do not depend on the pixel grid. Defs, clip paths, masks, titles, text, unfilled elements and
this skill's construction groups (golden-grid, notes, squares, circles, phi-lines, eye, phi-points,
spacing-ruler) are not measured. A rect covering the whole canvas is the background; shapes painted
later in its colour cut the ink.

Then every value goes on the phi ladder of one unit, with the ladder code of proportion_check.py:
the wordmark stem when there is a word, else the median line width. Whole steps by default, half
steps with --half, within 3 percent is on, and the report ends with the chance rate.

  python3 -I logo_measure.py logo.svg
  python3 -I logo_measure.py logo.svg --unit "mark line" --half
  python3 -I logo_measure.py logo.svg --unit 4.2265
  python3 -I logo_measure.py logo.svg --json
  python3 -I logo_measure.py logo.svg --px-per-line 30 --max-pixels 4000000

Standard library only. Outline live type before export: text elements are not measured. Fills under
half opacity are overlays (a grid's column tint) and are left out too.

Limits: icon and word split into two parts only when the space between them is over 1.5 line widths
and 1.8 times the usual space between letters (a tighter lockup reads as one mark with no word). A
background tile that stops short of the canvas edge counts as ink. The gap median moves with
--gap-limit, so compare gaps measured with the same limit.
"""
import argparse
import bisect
import json
import math
import os
import re
import sys
import time
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.dont_write_bytecode = True   # importing a sibling script must not leave __pycache__ in the skill folder
import proportion_check as pc  # noqa: E402  (the ladder code is shared, the way golden_build imports golden_grid)

PHI = pc.PHI
CONSTRUCTION_IDS = ("golden-grid", "notes", "squares", "circles", "phi-lines", "eye", "phi-points", "spacing-ruler")
NOT_DRAWN = {"defs", "clipPath", "mask", "title", "desc", "metadata", "style", "script", "linearGradient",
             "radialGradient", "pattern", "marker", "filter", "foreignObject", "text", "image", "symbol",
             "font", "font-face", "cursor", "view", "animate", "set"}
GROUPS = {"g", "svg", "a", "switch"}
SHAPES = {"path", "rect", "circle", "ellipse", "polygon", "polyline", "line"}
INHERITED = ("fill", "fill-rule", "fill-opacity", "visibility", "stroke", "stroke-width", "stroke-linecap")
PRESENTATION = INHERITED + ("opacity", "display", "mask", "clip-path")
KAPPA = 0.5522847498307936
INF = float("inf")
BIG = 1 << 39               # a squared distance standing for "no feature in this column"
COS_RIDGE = -0.6            # the two nearest edges of a ridge pixel face each other (more than about 127 degrees apart)
RIDGE_SEP = 4               # px: and lie at least this far apart, so the steps of a slanted edge are not a ridge
COS_EXACT = -0.8            # on the vector outline the two sides face each other within about 37 degrees
GAP_LIMIT = 1.25            # channels up to this multiple of the part's line width count as gaps
GAP_REACH = 3.0             # channel ridges are read up to this multiple, to find the most common channel width
PX_PER_LINE = 20.0
MAX_PIXELS = 2_000_000
PIECE = 3.0                 # outline pieces of at most this many px, for the edge index
FLAT_TOL = 0.02             # px: curve flattening tolerance


class LogoError(Exception):
    pass


# ---------------------------------------------------------------- small helpers

def fmt(v, nd=3):
    if v is None:
        return "-"
    if abs(v) < 0.5 * 10 ** -nd:
        v = 0.0
    s = ("%." + str(nd) + "f") % v
    return s.rstrip("0").rstrip(".") if "." in s else s


def sig(v, n=4):
    return "-" if v is None else pc.sig(v, n)


def pct(sorted_vals, q):
    """Percentile with linear interpolation; sorted_vals is sorted and not empty."""
    if not sorted_vals:
        return None
    k = (len(sorted_vals) - 1) * q / 100.0
    lo = int(math.floor(k))
    hi = min(lo + 1, len(sorted_vals) - 1)
    return sorted_vals[lo] + (sorted_vals[hi] - sorted_vals[lo]) * (k - lo)


def stats(vals):
    v = sorted(vals)
    if not v:
        return None
    return {"n": len(v), "median": pct(v, 50), "p10": pct(v, 10), "p90": pct(v, 90), "min": v[0], "max": v[-1]}


def local(tag):
    return tag.rsplit("}", 1)[-1] if isinstance(tag, str) else ""


_NUM = re.compile(r"[+-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?")


def length(v, ref=None, default=0.0):
    """An attribute length in user units. Percentages need the reference length."""
    if v is None:
        return default
    v = v.strip()
    m = _NUM.match(v)
    if not m:
        return default
    x = float(m.group(0))
    if v.endswith("%"):
        return x / 100.0 * ref if ref else default
    return x


# ---------------------------------------------------------------- colours and style

NAMED = {"white": "#ffffff", "black": "#000000", "none": "none", "transparent": "none", "red": "#ff0000",
         "green": "#008000", "blue": "#0000ff", "gray": "#808080", "grey": "#808080", "silver": "#c0c0c0",
         "currentcolor": "#000000"}


def norm_colour(c):
    c = (c or "").replace("!important", "").strip().lower()
    if c.startswith("url("):
        return c
    if c in NAMED:
        return NAMED[c]
    m = re.fullmatch(r"#([0-9a-f])([0-9a-f])([0-9a-f])", c)
    if m:
        return "#" + "".join(ch * 2 for ch in m.groups())
    m = re.fullmatch(r"rgba?\(([^)]*)\)", c)
    if m:
        parts = [p.strip() for p in m.group(1).split(",")]
        try:
            vals = [int(round(float(p.rstrip("%")) * (2.55 if p.endswith("%") else 1))) for p in parts[:3]]
            if len(parts) > 3 and float(parts[3]) == 0:
                return "none"
            return "#%02x%02x%02x" % tuple(max(0, min(255, x)) for x in vals)
        except ValueError:
            return c
    return c


def luminance(c):
    c = norm_colour(c)
    if c == "none":
        return 0.0
    if re.fullmatch(r"#[0-9a-f]{6}", c):
        r, g, b = (int(c[k:k + 2], 16) for k in (1, 3, 5))
        return (0.2126 * r + 0.7152 * g + 0.0722 * b) / 255.0
    return 1.0


def parse_decls(s):
    out = {}
    for part in (s or "").split(";"):
        if ":" in part:
            k, v = part.split(":", 1)
            out[k.strip().lower()] = v.replace("!important", "").strip()
    return out


def parse_css(text):
    rules = []
    text = re.sub(r"/\*.*?\*/", "", text or "", flags=re.S)
    for sel, body in re.findall(r"([^{}]+)\{([^}]*)\}", text):
        decl = {k: v for k, v in parse_decls(body).items() if k in PRESENTATION}
        if not decl:
            continue
        for one in sel.split(","):
            one = one.strip()
            if one == "*" or re.fullmatch(r"[.#]?[A-Za-z_][\w-]*", one):
                rules.append((one, decl))
    return rules


def own_style(el, css):
    st = {}
    for k in PRESENTATION:
        v = el.get(k)
        if v is not None:
            st[k] = v.strip()
    if css:
        tag, eid = local(el.tag), el.get("id")
        classes = (el.get("class") or "").split()
        for level in (0, 1, 2):
            for sel, decl in css:
                if (level == 0 and sel in ("*", tag)) or (level == 1 and sel[:1] == "." and sel[1:] in classes) or \
                        (level == 2 and sel[:1] == "#" and sel[1:] == eid):
                    st.update(decl)
    if el.get("style"):
        st.update({k: v for k, v in parse_decls(el.get("style")).items() if k in PRESENTATION})
    return st


def number(v, default):
    try:
        return float(_NUM.match(v.strip()).group(0))
    except (AttributeError, ValueError):
        return default


# ---------------------------------------------------------------- transforms

IDENT = (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)


def mmul(m, n):
    a, b, c, d, e, f = m
    A, B, C, D, E, F = n
    return (a * A + c * B, b * A + d * B, a * C + c * D, b * C + d * D, a * E + c * F + e, b * E + d * F + f)


def apply(m, p):
    return (m[0] * p[0] + m[2] * p[1] + m[4], m[1] * p[0] + m[3] * p[1] + m[5])


_TF = re.compile(r"(matrix|translate|scale|rotate|skewX|skewY)\s*\(([^)]*)\)")


def parse_transform(s):
    m = IDENT
    for name, args in _TF.findall(s or ""):
        v = [float(t) for t in _NUM.findall(args)]
        if name == "matrix":
            if len(v) != 6:
                continue
            t = tuple(v)
        elif name == "translate":
            t = (1.0, 0.0, 0.0, 1.0, v[0] if v else 0.0, v[1] if len(v) > 1 else 0.0)
        elif name == "scale":
            sx = v[0] if v else 1.0
            t = (sx, 0.0, 0.0, v[1] if len(v) > 1 else sx, 0.0, 0.0)
        elif name == "rotate":
            a = math.radians(v[0] if v else 0.0)
            t = (math.cos(a), math.sin(a), -math.sin(a), math.cos(a), 0.0, 0.0)
            if len(v) >= 3:
                t = mmul(mmul((1.0, 0.0, 0.0, 1.0, v[1], v[2]), t), (1.0, 0.0, 0.0, 1.0, -v[1], -v[2]))
        elif name == "skewX":
            t = (1.0, 0.0, math.tan(math.radians(v[0] if v else 0.0)), 1.0, 0.0, 0.0)
        else:
            t = (1.0, math.tan(math.radians(v[0] if v else 0.0)), 0.0, 1.0, 0.0, 0.0)
        m = mmul(m, t)
    return m


# ---------------------------------------------------------------- path data

ARGS = {"M": 2, "L": 2, "H": 1, "V": 1, "C": 6, "S": 4, "Q": 4, "T": 2, "A": 7, "Z": 0}


def tokenize_path(d):
    """[(command, [numbers])]. Arc flags are read as single digits, so "a1 1 0 011 1" works."""
    out, i, n, cmd = [], 0, len(d), None
    while True:
        while i < n and d[i] in " \t\r\n,":
            i += 1
        if i >= n:
            break
        ch = d[i]
        if ch.isalpha():
            if ch.upper() not in ARGS:
                raise LogoError("path data: unknown command %r" % ch)
            cmd = ch
            i += 1
            if cmd in "Zz":
                out.append((cmd, []))
                continue
        elif cmd is None or cmd in "Zz":
            raise LogoError("path data: a number where a command belongs, at %d" % i)
        up = cmd.upper()
        vals = []
        for k in range(ARGS[up]):
            while i < n and d[i] in " \t\r\n,":
                i += 1
            if up == "A" and k in (3, 4):
                if i < n and d[i] in "01":
                    vals.append(float(d[i]))
                    i += 1
                    continue
                raise LogoError("path data: bad arc flag at %d" % i)
            m = _NUM.match(d, i)
            if not m:
                raise LogoError("path data: expected a number at %d" % i)
            vals.append(float(m.group(0)))
            i = m.end()
        out.append((cmd, vals))
        if cmd == "M":
            cmd = "L"
        elif cmd == "m":
            cmd = "l"
    return out


def arc_cubics(p0, rx, ry, rot, large, sweep, p1):
    """SVG endpoint arc to cubic Beziers (implementation notes F.6.5)."""
    (x1, y1), (x2, y2) = p0, p1
    if (x1, y1) == (x2, y2):
        return []
    rx, ry = abs(rx), abs(ry)
    if rx == 0 or ry == 0:
        return [("L", p0, p1)]
    phi = math.radians(rot)
    cp, sp = math.cos(phi), math.sin(phi)
    dx, dy = (x1 - x2) / 2.0, (y1 - y2) / 2.0
    xp, yp = cp * dx + sp * dy, -sp * dx + cp * dy
    lam = xp * xp / (rx * rx) + yp * yp / (ry * ry)
    if lam > 1:
        rx, ry = rx * math.sqrt(lam), ry * math.sqrt(lam)
    num = rx * rx * ry * ry - rx * rx * yp * yp - ry * ry * xp * xp
    den = rx * rx * yp * yp + ry * ry * xp * xp
    coef = math.sqrt(max(0.0, num / den)) if den else 0.0
    if large == sweep:
        coef = -coef
    cxp, cyp = coef * rx * yp / ry, -coef * ry * xp / rx
    cx = cp * cxp - sp * cyp + (x1 + x2) / 2.0
    cy = sp * cxp + cp * cyp + (y1 + y2) / 2.0

    def ang(ux, uy, vx, vy):
        a = math.atan2(ux * vy - uy * vx, ux * vx + uy * vy)
        return a

    t1 = ang(1, 0, (xp - cxp) / rx, (yp - cyp) / ry)
    dt = ang((xp - cxp) / rx, (yp - cyp) / ry, (-xp - cxp) / rx, (-yp - cyp) / ry)
    if not sweep and dt > 0:
        dt -= 2 * math.pi
    elif sweep and dt < 0:
        dt += 2 * math.pi
    n = max(1, int(math.ceil(abs(dt) / (math.pi / 2) - 1e-9)))
    step = dt / n
    k = 4.0 / 3.0 * math.tan(step / 4)
    out, cur = [], p0

    def pt(a):
        ca, sa = math.cos(a), math.sin(a)
        return (cx + rx * ca * cp - ry * sa * sp, cy + rx * ca * sp + ry * sa * cp)

    def dpt(a):
        ca, sa = math.cos(a), math.sin(a)
        return (-rx * sa * cp - ry * ca * sp, -rx * sa * sp + ry * ca * cp)

    for s in range(n):
        a0, a1 = t1 + s * step, t1 + (s + 1) * step
        e = pt(a1) if s < n - 1 else p1
        d0, d1 = dpt(a0), dpt(a1)
        c1 = (cur[0] + k * d0[0], cur[1] + k * d0[1])
        c2 = (e[0] - k * d1[0], e[1] - k * d1[1])
        out.append(("C", cur, c1, c2, e))
        cur = e
    return out


def path_subpaths(d):
    """Subpaths of segments ('L', p0, p1) or ('C', p0, c1, c2, p3), before any transform."""
    subs, segs = [], None
    x = y = 0.0
    start = (0.0, 0.0)
    prev, last_c2, last_q = None, None, None
    for cmd, v in tokenize_path(d or ""):
        up = cmd.upper()
        rel = cmd != up
        if up == "M":
            x, y = (x + v[0], y + v[1]) if rel else (v[0], v[1])
            segs = []
            subs.append(segs)
            start = (x, y)
            prev = "M"
            continue
        if up == "Z":
            if segs is not None and (x, y) != start:
                segs.append(("L", (x, y), start))
            x, y = start
            segs = None          # a command after Z without M starts a new subpath at the same point
            prev = "Z"
            continue
        if segs is None:
            segs = []
            subs.append(segs)
            start = (x, y)
        p0 = (x, y)
        ox, oy = (x, y) if rel else (0.0, 0.0)
        if up == "L":
            p1 = (ox + v[0], oy + v[1])
            segs.append(("L", p0, p1))
        elif up == "H":
            p1 = ((x + v[0]) if rel else v[0], y)
            segs.append(("L", p0, p1))
        elif up == "V":
            p1 = (x, (y + v[0]) if rel else v[0])
            segs.append(("L", p0, p1))
        elif up == "C":
            c1, c2, p1 = (ox + v[0], oy + v[1]), (ox + v[2], oy + v[3]), (ox + v[4], oy + v[5])
            segs.append(("C", p0, c1, c2, p1))
            last_c2 = c2
        elif up == "S":
            c1 = (2 * x - last_c2[0], 2 * y - last_c2[1]) if prev in ("C", "S") else p0
            c2, p1 = (ox + v[0], oy + v[1]), (ox + v[2], oy + v[3])
            segs.append(("C", p0, c1, c2, p1))
            last_c2 = c2
        elif up in ("Q", "T"):
            if up == "Q":
                q, p1 = (ox + v[0], oy + v[1]), (ox + v[2], oy + v[3])
            else:
                q = (2 * x - last_q[0], 2 * y - last_q[1]) if prev in ("Q", "T") else p0
                p1 = (ox + v[0], oy + v[1])
            c1 = (p0[0] + 2.0 / 3 * (q[0] - p0[0]), p0[1] + 2.0 / 3 * (q[1] - p0[1]))
            c2 = (p1[0] + 2.0 / 3 * (q[0] - p1[0]), p1[1] + 2.0 / 3 * (q[1] - p1[1]))
            segs.append(("C", p0, c1, c2, p1))
            last_q = q
        elif up == "A":
            p1 = (ox + v[5], oy + v[6])
            segs.extend(arc_cubics(p0, v[0], v[1], v[2], v[3] != 0, v[4] != 0, p1))
        x, y = p1
        prev = up
    return [s for s in subs if s]


def ellipse_sub(cx, cy, rx, ry):
    kx, ky = KAPPA * rx, KAPPA * ry
    e, s, w, n = (cx + rx, cy), (cx, cy + ry), (cx - rx, cy), (cx, cy - ry)
    return [("C", e, (cx + rx, cy + ky), (cx + kx, cy + ry), s), ("C", s, (cx - kx, cy + ry), (cx - rx, cy + ky), w),
            ("C", w, (cx - rx, cy - ky), (cx - kx, cy - ry), n), ("C", n, (cx + kx, cy - ry), (cx + rx, cy - ky), e)]


def rect_sub(x, y, w, h, rx, ry):
    if rx is None and ry is None:
        rx = ry = 0.0
    elif rx is None:
        rx = ry
    elif ry is None:
        ry = rx
    rx, ry = min(abs(rx), w / 2.0), min(abs(ry), h / 2.0)
    if rx <= 0 or ry <= 0:
        a, b, c, d = (x, y), (x + w, y), (x + w, y + h), (x, y + h)
        return [("L", a, b), ("L", b, c), ("L", c, d), ("L", d, a)]
    kx, ky = KAPPA * rx, KAPPA * ry
    out = []
    p = (x + rx, y)

    def line(q):
        nonlocal p
        if q != p:
            out.append(("L", p, q))
        p = q

    def corner(c1, c2, q):
        nonlocal p
        out.append(("C", p, c1, c2, q))
        p = q
    line((x + w - rx, y))
    corner((x + w - rx + kx, y), (x + w, y + ry - ky), (x + w, y + ry))
    line((x + w, y + h - ry))
    corner((x + w, y + h - ry + ky), (x + w - rx + kx, y + h), (x + w - rx, y + h))
    line((x + rx, y + h))
    corner((x + rx - kx, y + h), (x, y + h - ry + ky), (x, y + h - ry))
    line((x, y + ry))
    corner((x, y + ry - ky), (x + rx - kx, y), (x + rx, y))
    return out


def capsule_sub(p0, p1, w, cap):
    """The outline of a stroked line (used inside masks only)."""
    dx, dy = p1[0] - p0[0], p1[1] - p0[1]
    L = math.hypot(dx, dy)
    if L == 0 or w <= 0:
        return []
    ux, uy = dx / L, dy / L
    nx, ny = -uy * w / 2, ux * w / 2
    if cap == "square":
        p0 = (p0[0] - ux * w / 2, p0[1] - uy * w / 2)
        p1 = (p1[0] + ux * w / 2, p1[1] + uy * w / 2)
    a, b = (p0[0] + nx, p0[1] + ny), (p1[0] + nx, p1[1] + ny)
    c, d = (p1[0] - nx, p1[1] - ny), (p0[0] - nx, p0[1] - ny)
    if cap != "round":
        return [("L", a, b), ("L", b, c), ("L", c, d), ("L", d, a)]
    r = w / 2
    end = arc_cubics(b, r, r, 0, False, False, c) or [("L", b, c)]
    beg = arc_cubics(d, r, r, 0, False, False, a) or [("L", d, a)]
    return [("L", a, b)] + end + [("L", c, d)] + beg


def points_sub(s):
    """polygon or polyline points; a filled polyline closes the same way a polygon does."""
    v = [float(t) for t in _NUM.findall(s or "")]
    pts = list(zip(v[0::2], v[1::2]))
    if len(pts) < 2:
        return []
    return [("L", pts[k], pts[k + 1]) for k in range(len(pts) - 1)] + [("L", pts[-1], pts[0])]


# ---------------------------------------------------------------- reading the SVG

def read_svg(path):
    try:
        src = open(path, encoding="utf-8", errors="replace").read()
    except OSError as e:
        raise LogoError("cannot read %s: %s" % (path, e))
    ents = {}
    for name, q1, q2 in re.findall(r"<!ENTITY\s+([A-Za-z_][\w.-]*)\s+(?:\"([^\"]*)\"|'([^']*)')\s*>", src):
        val = q1 or q2
        if "&" in val or "<" in val or len(val) > 4096:
            raise LogoError("the file declares an entity this reader does not expand; export it again without a DOCTYPE")
        ents[name] = val
    if re.search(r"<!ENTITY\s+%|<!ENTITY[^>]*\b(SYSTEM|PUBLIC)\b", src):
        raise LogoError("the file declares an external or parameter entity; export it again without a DOCTYPE")
    src = re.sub(r"<!DOCTYPE[^\[>]*(\[.*?\])?\s*>", "", src, count=1, flags=re.S)
    for name, val in ents.items():
        src = src.replace("&%s;" % name, val)
    try:
        root = ET.fromstring(src)
    except ET.ParseError as e:
        raise LogoError("not a readable SVG (%s)" % e)
    if local(root.tag) != "svg":
        raise LogoError("the file's root element is %r, an SVG starts with <svg>" % local(root.tag))
    return root


class Item(object):
    __slots__ = ("id", "named", "fill", "rule", "subs", "masks", "eraser", "value")

    def __init__(self, **kw):
        for k in self.__slots__:
            setattr(self, k, kw.get(k))


def collect(root):
    """Walk the drawing: filled shapes in paint order, with their transforms, fill rules and masks."""
    css = []
    for el in root.iter():
        if local(el.tag) == "style":
            css += parse_css("".join(el.itertext()))
    ids = {el.get("id"): el for el in root.iter() if el.get("id")}
    vb = [float(t) for t in _NUM.findall(root.get("viewBox") or "")]
    if len(vb) == 4 and vb[2] > 0 and vb[3] > 0:
        canvas = tuple(vb)
    else:
        w, h = length(root.get("width")), length(root.get("height"))
        canvas = (0.0, 0.0, w, h) if w > 0 and h > 0 else None
    notes = {"text": 0, "image": 0, "stroke only": 0, "translucent": 0, "clip-path ignored": 0, "skipped construction": []}
    items = []

    def walk(el, ctm, inh, masks, depth, mask_mode, out):
        if depth > 64:
            return
        tag = local(el.tag)
        if tag in NOT_DRAWN:
            if tag in ("text", "image") and not mask_mode:
                notes[tag] += 1
            return
        eid = el.get("id") or ""
        if eid in CONSTRUCTION_IDS:
            notes["skipped construction"].append(eid)
            return
        st = own_style(el, css)
        if st.get("display", "").strip() == "none":
            return
        alpha = inh.get("_alpha", 1.0) * number(st.get("opacity", "1"), 1.0)
        if alpha <= 0:
            return
        style = dict(inh)
        style.update({k: st[k] for k in INHERITED if k in st})
        style["_alpha"] = alpha
        m = mmul(ctm, parse_transform(el.get("transform")))
        if not mask_mode:
            mk = st.get("mask", "none")
            mm = re.match(r"url\(\s*['\"]?#([^)'\"]+)['\"]?\s*\)", mk)
            if mm and mm.group(1) in ids and local(ids[mm.group(1)].tag) == "mask":
                masks = masks + [(ids[mm.group(1)], m)]
            if st.get("clip-path", "none") != "none":
                notes["clip-path ignored"] += 1
        if tag in GROUPS:
            if tag == "svg" and el is not root:
                m = mmul(m, (1.0, 0.0, 0.0, 1.0, length(el.get("x")), length(el.get("y"))))
            for ch in el:
                walk(ch, m, style, masks, depth + 1, mask_mode, out)
            return
        if tag == "use":
            href = el.get("href") or el.get("{http://www.w3.org/1999/xlink}href") or ""
            target = ids.get(href[1:]) if href.startswith("#") else None
            if target is None:
                return
            m2 = mmul(m, (1.0, 0.0, 0.0, 1.0, length(el.get("x")), length(el.get("y"))))
            if local(target.tag) == "symbol":
                for ch in target:
                    walk(ch, m2, style, masks, depth + 1, mask_mode, out)
            else:
                walk(target, m2, style, masks, depth + 1, mask_mode, out)
            return
        if tag not in SHAPES:
            return
        fill = norm_colour(style.get("fill", "black"))
        hidden = style.get("visibility", "visible").strip() in ("hidden", "collapse")
        fop = number(style.get("fill-opacity", "1"), 1.0)
        subs = None
        if tag == "line":
            if mask_mode and norm_colour(style.get("stroke", "none")) != "none":
                w = number(style.get("stroke-width", "1"), 1.0)
                p0 = (length(el.get("x1")), length(el.get("y1")))
                p1 = (length(el.get("x2")), length(el.get("y2")))
                seg = capsule_sub(p0, p1, w, style.get("stroke-linecap", "butt").strip())
                subs = [seg] if seg else []
                fill = norm_colour(style.get("stroke"))
            else:
                notes["stroke only"] += 1
                return
        if fill == "none" or fop <= 0 or hidden:
            if norm_colour(style.get("stroke", "none")) != "none" and not mask_mode:
                notes["stroke only"] += 1
            return
        if not mask_mode and fop * style.get("_alpha", 1.0) < 0.5:
            notes["translucent"] += 1      # an overlay (a grid's column tint), not ink
            return
        if subs is None:
            cw = canvas[2] if canvas else None
            ch_ = canvas[3] if canvas else None
            try:
                if tag == "path":
                    subs = path_subpaths(el.get("d"))
                elif tag == "rect":
                    x, y = length(el.get("x"), cw), length(el.get("y"), ch_)
                    w, h = length(el.get("width"), cw), length(el.get("height"), ch_)
                    if w <= 0 or h <= 0:
                        return
                    rx = el.get("rx")
                    ry = el.get("ry")
                    subs = [rect_sub(x, y, w, h, length(rx, cw) if rx else None, length(ry, ch_) if ry else None)]
                elif tag == "circle":
                    r = length(el.get("r"))
                    if r <= 0:
                        return
                    subs = [ellipse_sub(length(el.get("cx"), cw), length(el.get("cy"), ch_), r, r)]
                elif tag == "ellipse":
                    rx, ry = length(el.get("rx"), cw), length(el.get("ry"), ch_)
                    if rx <= 0 or ry <= 0:
                        return
                    subs = [ellipse_sub(length(el.get("cx"), cw), length(el.get("cy"), ch_), rx, ry)]
                else:
                    subs = [points_sub(el.get("points"))]
            except LogoError as e:
                raise LogoError("%s: %s" % ((tag + " " + eid) if eid else tag, e))
        subs = [[tuple([s[0]] + [apply(m, p) for p in s[1:]]) for s in sub] for sub in subs if sub]
        if not subs:
            return
        rule = style.get("fill-rule", "nonzero").strip()
        out.append(Item(id=eid or tag, named=bool(eid), fill=fill, rule="evenodd" if rule == "evenodd" else "nonzero",
                        subs=subs, masks=masks, eraser=False, value=luminance(fill)))

    walk(root, IDENT, {}, [], 0, False, items)
    # masks: their drawing, in the user space of the element that uses them
    mask_cache = {}
    for it in items:
        resolved = []
        for mel, m in it.masks or []:
            key = (id(mel), m)
            if key not in mask_cache:
                mi = []
                for ch in mel:
                    walk(ch, m, {}, [], 1, True, mi)
                mask_cache[key] = mi
            resolved.append(mask_cache[key])
        it.masks = resolved
    # the background: a first shape that covers the whole canvas
    paper = None
    if items and canvas:
        b = bounds_of([items[0]])
        cx, cy, cw, chh = canvas
        if b and b[0] <= cx + 0.01 * cw and b[1] <= cy + 0.01 * chh and b[2] >= cx + 0.99 * cw and b[3] >= cy + 0.99 * chh \
                and len(items) > 1:
            paper = items[0].fill
            items = items[1:]
    for it in items:
        it.eraser = paper is not None and it.fill == paper
    return items, canvas, paper, notes


# ---------------------------------------------------------------- geometry

def cubic_ts(a, b, c, d):
    """Parameters in (0, 1) where one coordinate of a cubic has a turning point."""
    A = -a + 3 * b - 3 * c + d
    B = 2 * (a - 2 * b + c)
    C = b - a
    out = []
    if abs(A) < 1e-12:
        if abs(B) > 1e-12:
            out.append(-C / B)
    else:
        disc = B * B - 4 * A * C
        if disc >= 0:
            r = math.sqrt(disc)
            out += [(-B + r) / (2 * A), (-B - r) / (2 * A)]
    return [t for t in out if 1e-9 < t < 1 - 1e-9]


def bez(p0, p1, p2, p3, t):
    u = 1 - t
    a, b, c, d = u * u * u, 3 * u * u * t, 3 * u * t * t, t * t * t
    return (a * p0[0] + b * p1[0] + c * p2[0] + d * p3[0], a * p0[1] + b * p1[1] + c * p2[1] + d * p3[1])


def bounds_of(items):
    xs, ys = [], []
    for it in items:
        for sub in it.subs:
            for s in sub:
                if s[0] == "L":
                    xs += [s[1][0], s[2][0]]
                    ys += [s[1][1], s[2][1]]
                else:
                    p0, p1, p2, p3 = s[1:]
                    ts = [0.0, 1.0] + cubic_ts(p0[0], p1[0], p2[0], p3[0]) + cubic_ts(p0[1], p1[1], p2[1], p3[1])
                    for t in ts:
                        x, y = bez(p0, p1, p2, p3, t)
                        xs.append(x)
                        ys.append(y)
    if not xs:
        return None
    return (min(xs), min(ys), max(xs), max(ys))


def straight_cubic(p0, p1, p2, p3):
    dx, dy = p3[0] - p0[0], p3[1] - p0[1]
    L = math.hypot(dx, dy)
    if L == 0:
        return False
    for p in (p1, p2):
        if abs((p[0] - p0[0]) * dy - (p[1] - p0[1]) * dx) / L > 1e-6 * max(1.0, L):
            return False
    return True


def flatten(sub, s, ox, oy, tol):
    """A subpath in pixel coordinates: points, and for each edge ending at a point, True when it is straight."""
    pts, straight = [], []

    def P(p):
        return ((p[0] - ox) * s, (p[1] - oy) * s)
    for seg in sub:
        if seg[0] == "L":
            a, b = P(seg[1]), P(seg[2])
            if not pts:
                pts.append(a)
                straight.append(True)
            pts.append(b)
            straight.append(True)
            continue
        p0, p1, p2, p3 = (P(p) for p in seg[1:])
        if not pts:
            pts.append(p0)
            straight.append(True)
        if straight_cubic(p0, p1, p2, p3):
            pts.append(p3)
            straight.append(True)
            continue
        L = max(math.hypot(p0[0] - 2 * p1[0] + p2[0], p0[1] - 2 * p1[1] + p2[1]),
                math.hypot(p1[0] - 2 * p2[0] + p3[0], p1[1] - 2 * p2[1] + p3[1]))
        n = max(1, min(2000, int(math.ceil(math.sqrt(0.75 * L / tol)))))
        ts = sorted(set([k / float(n) for k in range(1, n + 1)] + cubic_ts(p0[0], p1[0], p2[0], p3[0]) +
                        cubic_ts(p0[1], p1[1], p2[1], p3[1])))
        for t in ts:
            pts.append(bez(p0, p1, p2, p3, t))
            straight.append(False)
    return pts, straight


def spans_of(polys, rule, H):
    """{row: [(x_start, x_end)]} of pixel-centre crossings filled under the rule."""
    rows = {}
    for pts, _ in polys:
        n = len(pts)
        if n < 3:
            continue
        for k in range(n):
            x0, y0 = pts[k - 1]
            x1, y1 = pts[k]
            if y0 == y1:
                continue
            if y0 < y1:
                w, ya, yb, xa, xb = 1, y0, y1, x0, x1
            else:
                w, ya, yb, xa, xb = -1, y1, y0, x1, x0
            j0 = max(0, int(math.ceil(ya - 0.5)))
            j1 = min(H, int(math.ceil(yb - 0.5)))
            if j1 <= j0:
                continue
            sl = (xb - xa) / (yb - ya)
            for j in range(j0, j1):
                r = rows.get(j)
                if r is None:
                    r = rows[j] = []
                r.append((xa + (j + 0.5 - ya) * sl, w))
    out = {}
    odd = rule == "evenodd"
    for j, xs in rows.items():
        xs.sort()
        wind, spans, start = 0, [], 0.0
        for x, w in xs:
            was = (wind & 1) if odd else (wind != 0)
            wind += w
            now = (wind & 1) if odd else (wind != 0)
            if now and not was:
                start = x
            elif was and not now:
                spans.append((start, x))
        if spans:
            out[j] = spans
    return out


def paint(img, spans, W, val):
    one = b"\x01" * W if val else bytes(W)
    for j, sp in spans.items():
        row = img[j]
        for xa, xb in sp:
            i0 = max(0, int(math.ceil(xa - 0.5)))
            i1 = min(W, int(math.ceil(xb - 0.5)))
            if i1 > i0:
                row[i0:i1] = one[:i1 - i0]


def render(items, s, ox, oy, W, H, tol, missed=None):
    """The ink raster (rows of 0 and 1) and the flattened outline of every item and mask shape.
    missed, a list, collects the ids of ink shapes too thin to cover a pixel centre."""
    img = [bytearray(W) for _ in range(H)]
    outlines = []
    all1 = int.from_bytes(b"\x01" * W, "big")
    for it in items:
        polys = [flatten(sub, s, ox, oy, tol) for sub in it.subs]
        outlines.append((it, polys))
        spans = spans_of(polys, it.rule, H)
        val = 0 if it.eraser else 1
        if missed is not None and val and not any(int(math.ceil(xb - 0.5)) > int(math.ceil(xa - 0.5))
                                                  for sp in spans.values() for xa, xb in sp):
            missed.append(it.id)
        if not it.masks:
            paint(img, spans, W, val)
            continue
        mimg = None
        for mitems in it.masks:
            mm = [bytearray(W) for _ in range(H)]
            for mi in mitems:
                mp = [flatten(sub, s, ox, oy, tol) for sub in mi.subs]
                outlines.append((mi, mp))
                paint(mm, spans_of(mp, mi.rule, H), W, 1 if mi.value >= 0.5 else 0)
            mimg = mm if mimg is None else [bytearray((int.from_bytes(a, "big") & int.from_bytes(b, "big")).to_bytes(W, "big"))
                                             for a, b in zip(mimg, mm)]
        tmp = [bytearray(W) for _ in range(H)]
        paint(tmp, spans, W, 1)
        for j in spans:
            t = int.from_bytes(tmp[j], "big") & int.from_bytes(mimg[j], "big")
            cur = int.from_bytes(img[j], "big")
            cur = (cur | t) if val else (cur & (all1 ^ t))
            img[j] = bytearray(cur.to_bytes(W, "big"))
    return img, outlines


# ---------------------------------------------------------------- connected shapes

_RUN = {1: re.compile(rb"\x01+"), 0: re.compile(rb"\x00+")}


class Labels(object):
    """4-connected components of one value, kept as runs per row."""

    def __init__(self, img, W, H, val):
        pat = _RUN[val]
        runs = [[(m.start(), m.end()) for m in pat.finditer(row)] for row in img]
        parent = []

        def find(a):
            while parent[a] != a:
                parent[a] = parent[parent[a]]
                a = parent[a]
            return a
        ids = []
        for j in range(H):
            prev = runs[j - 1] if j else []
            pid = ids[j - 1] if j else []
            row_ids = []
            k = 0
            for a, b in runs[j]:
                rid = len(parent)
                parent.append(rid)
                row_ids.append(rid)
                while k < len(prev) and prev[k][1] <= a:
                    k += 1
                kk = k
                while kk < len(prev) and prev[kk][0] < b:
                    ra, rb = find(rid), find(pid[kk])
                    if ra != rb:
                        parent[max(ra, rb)] = min(ra, rb)
                    kk += 1
            ids.append(row_ids)
        compact = {}
        self.starts, self.ends, self.labs = [], [], []
        info = []
        for j in range(H):
            st, en, lb = [], [], []
            for (a, b), rid in zip(runs[j], ids[j]):
                r = find(rid)
                if r not in compact:
                    compact[r] = len(compact)
                    info.append({"px": 0, "i0": a, "i1": b, "j0": j, "j1": j + 1, "border": False})
                c = compact[r]
                d = info[c]
                d["px"] += b - a
                d["i0"], d["i1"] = min(d["i0"], a), max(d["i1"], b)
                d["j1"] = j + 1
                if j == 0 or j == H - 1 or a == 0 or b == W:
                    d["border"] = True
                st.append(a)
                en.append(b)
                lb.append(c)
            self.starts.append(st)
            self.ends.append(en)
            self.labs.append(lb)
        self.runs = runs
        self.info = info
        self.H = H

    def at(self, i, j):
        if j < 0 or j >= self.H:
            return -1
        st = self.starts[j]
        k = bisect.bisect_right(st, i) - 1
        if k >= 0 and i < self.ends[j][k]:
            return self.labs[j][k]
        return -1


# ---------------------------------------------------------------- distance transforms

def edt(img, W, H, feature, targets):
    """Exact squared Euclidean distance (Felzenszwalb and Huttenlocher) from each target pixel to the
    nearest pixel of value feature, with that pixel's column and row. targets: runs per row."""
    NEG, POS = -(1 << 20), 1 << 20
    ups = []
    up = [NEG] * W
    for j in range(H):
        up = [j if c == feature else u for c, u in zip(img[j], up)]
        ups.append(up)
    dn = [POS] * W
    D2 = [None] * H
    FX = [None] * H
    FY = [None] * H
    for j in range(H - 1, -1, -1):
        row = img[j]
        dn = [j if c == feature else d for c, d in zip(row, dn)]
        if not targets[j]:
            ups[j] = None
            continue
        fr = [u if j - u <= d - j else d for u, d in zip(ups[j], dn)]
        ups[j] = None
        f = [(j - r) * (j - r) for r in fr]
        qs = [q for q in range(W) if f[q] < BIG]
        d2row = [0] * W
        fxr = [-POS] * W
        fyr = [-POS] * W
        if qs:
            h = [fq + q * q for q, fq in enumerate(f)]
            n = len(qs)
            v = [0] * n
            z = [0.0] * (n + 1)
            k = 0
            v[0] = qs[0]
            z[0], z[1] = -INF, INF
            for q in qs[1:]:
                hq = h[q]
                while True:
                    p = v[k]
                    s = (hq - h[p]) / (2.0 * (q - p))
                    if s > z[k]:
                        break
                    k -= 1
                k += 1
                v[k] = q
                z[k] = s
                z[k + 1] = INF
            k = 0
            for a, b in targets[j]:
                for x in range(a, b):
                    while z[k + 1] < x:
                        k += 1
                    p = v[k]
                    dx = x - p
                    d2row[x] = dx * dx + f[p]
                    fxr[x] = p
                    fyr[x] = fr[p]
        D2[j], FX[j], FY[j] = d2row, fxr, fyr
    return D2, FX, FY


def ridge(img, W, H, target, D2, FX, FY, d2cap=None):
    """Pixels of the target value whose nearest feature and a 4-neighbour's nearest feature lie on
    opposite sides: the medial ridge. {(i, j): (ax, ay, bx, by)} with the two features."""
    out = {}
    best = {}

    def test(pi, pj, qi, qj):
        ax, ay = FX[pj][pi], FY[pj][pi]
        bx, by = FX[qj][qi], FY[qj][qi]
        if (ax - bx) * (ax - bx) + (ay - by) * (ay - by) < RIDGE_SEP * RIDGE_SEP:
            return
        for (i, j, a0, a1, b0, b1) in ((pi, pj, ax, ay, bx, by), (qi, qj, bx, by, ax, ay)):
            ux, uy, vx, vy = a0 - i, a1 - j, b0 - i, b1 - j
            na, nb = ux * ux + uy * uy, vx * vx + vy * vy
            if not na or not nb:
                continue
            c = (ux * vx + uy * vy) / math.sqrt(na * nb)
            if c < COS_RIDGE and c < best.get((i, j), 1.0):
                best[(i, j)] = c
                out[(i, j)] = (a0, a1, b0, b1)
    cap = d2cap if d2cap is not None else BIG
    for j in range(H):
        fx, fy = FX[j], FY[j]
        if fx is None:
            continue
        row, d2 = img[j], D2[j]
        cand = [i for i, (r0, r1, a0, a1, b0, b1, d0) in enumerate(zip(row, row[1:], fx, fx[1:], fy, fy[1:], d2))
                if r0 == target and r1 == target and d0 <= cap and abs(a0 - a1) + abs(b0 - b1) > 2]
        for i in cand:
            test(i, j, i + 1, j)
        if j + 1 < H and FX[j + 1] is not None:
            row2, fx2, fy2 = img[j + 1], FX[j + 1], FY[j + 1]
            cand = [i for i, (r0, r1, a0, a1, b0, b1, d0) in enumerate(zip(row, row2, fx, fx2, fy, fy2, d2))
                    if r0 == target and r1 == target and d0 <= cap and abs(a0 - a1) + abs(b0 - b1) > 2]
            for i in cand:
                test(i, j, i, j + 1)
    return out


# ---------------------------------------------------------------- the vector outline, indexed

class Edges(object):
    """Outline pieces on the ink boundary, in pixel coordinates, with the shapes on either side."""

    def __init__(self, outlines, img, W, H, ink, paper, cell=6.0):
        self.cell = cell
        self.x0, self.y0, self.x1, self.y1 = [], [], [], []
        self.lab, self.hole, self.straight, self.item, self.inkside = [], [], [], [], []
        grid = {}
        for it, polys in outlines:
            for pts, straight in polys:
                n = len(pts)
                for k in range(n):
                    a, b = pts[k - 1], pts[k]
                    st = straight[k] if k else True
                    L = math.hypot(b[0] - a[0], b[1] - a[1])
                    if L == 0:
                        continue
                    m = max(1, int(math.ceil(L / PIECE)))
                    for t in range(m):
                        pa = (a[0] + (b[0] - a[0]) * t / m, a[1] + (b[1] - a[1]) * t / m)
                        pb = (a[0] + (b[0] - a[0]) * (t + 1) / m, a[1] + (b[1] - a[1]) * (t + 1) / m)
                        mx, my = (pa[0] + pb[0]) / 2, (pa[1] + pb[1]) / 2
                        ci, cj = int(math.floor(mx)), int(math.floor(my))
                        best_ink = best_paper = None
                        for jj in (cj - 1, cj, cj + 1):
                            if jj < 0 or jj >= H:
                                continue
                            row = img[jj]
                            for ii in (ci - 1, ci, ci + 1):
                                if ii < 0 or ii >= W:
                                    continue
                                dd = (ii + 0.5 - mx) ** 2 + (jj + 0.5 - my) ** 2
                                if row[ii]:
                                    if best_ink is None or dd < best_ink[0]:
                                        best_ink = (dd, ii, jj)
                                elif best_paper is None or dd < best_paper[0]:
                                    best_paper = (dd, ii, jj)
                        if best_ink is None or best_paper is None:
                            continue
                        # which side of the piece the ink is on: +1 to the left of a to b, -1 to the right
                        nx, ny = -(pb[1] - pa[1]), pb[0] - pa[0]
                        nl = math.hypot(nx, ny)
                        nx, ny = nx / nl, ny / nl
                        side = 0
                        for sgn in (1, -1):
                            si, sj = int(math.floor(mx + sgn * 0.75 * nx)), int(math.floor(my + sgn * 0.75 * ny))
                            if 0 <= si < W and 0 <= sj < H and img[sj][si] and not side:
                                side = sgn
                            elif 0 <= si < W and 0 <= sj < H and img[sj][si] and side:
                                side = 0          # ink on both sides: a thin part, decide below
                                break
                        if not side:
                            side = 1 if (best_ink[1] + 0.5 - mx) * nx + (best_ink[2] + 0.5 - my) * ny > 0 else -1
                        idx = len(self.x0)
                        self.x0.append(pa[0])
                        self.y0.append(pa[1])
                        self.x1.append(pb[0])
                        self.y1.append(pb[1])
                        self.lab.append(ink.at(best_ink[1], best_ink[2]))
                        self.hole.append(paper.at(best_paper[1], best_paper[2]))
                        self.straight.append(st)
                        self.item.append(it)
                        self.inkside.append(side)
                        for gx in range(int(min(pa[0], pb[0]) // cell), int(max(pa[0], pb[0]) // cell) + 1):
                            for gy in range(int(min(pa[1], pb[1]) // cell), int(max(pa[1], pb[1]) // cell) + 1):
                                g = grid.get((gx, gy))
                                if g is None:
                                    g = grid[(gx, gy)] = []
                                g.append(idx)
        self.grid = grid

    def near(self, x, y, r):
        c = self.cell
        out = []
        for gx in range(int((x - r) // c), int((x + r) // c) + 1):
            for gy in range(int((y - r) // c), int((y + r) // c) + 1):
                g = self.grid.get((gx, gy))
                if g:
                    out.extend(g)
        return set(out)

    def dist(self, k, px, py):
        x0, y0 = self.x0[k], self.y0[k]
        dx, dy = self.x1[k] - x0, self.y1[k] - y0
        L2 = dx * dx + dy * dy
        t = ((px - x0) * dx + (py - y0) * dy) / L2 if L2 else 0.0
        t = 0.0 if t < 0 else (1.0 if t > 1 else t)
        qx, qy = x0 + t * dx, y0 + t * dy
        return math.hypot(px - qx, py - qy), qx, qy

    def two_sided(self, px, py, ax, ay, bx, by):
        """Distance from (px, py) to the outline on side a and on side b, and the shape on each side."""
        ra, rb = math.hypot(ax - px, ay - py), math.hypot(bx - px, by - py)
        if ra == 0 or rb == 0:
            return None
        R = max(ra, rb) + 1.5
        uax, uay, ubx, uby = (ax - px) / ra, (ay - py) / ra, (bx - px) / rb, (by - py) / rb
        da = db = INF
        ka = kb = -1
        qa = qb = None
        for k in self.near(px, py, R):
            d, qx, qy = self.dist(k, px, py)
            if d > R:
                continue
            vx, vy = qx - px, qy - py
            if vx * uax + vy * uay >= vx * ubx + vy * uby:
                if d < da:
                    da, ka, qa = d, k, (vx, vy)
            elif d < db:
                db, kb, qb = d, k, (vx, vy)
        if ka < 0 or kb < 0 or da == 0 or db == 0:
            return None
        if (qa[0] * qb[0] + qa[1] * qb[1]) / (da * db) > COS_EXACT:
            return None       # the nearest edges meet at a corner: no width to read here
        if abs(da - db) > max(2.0, 0.35 * (da + db)):
            return None       # a ridge pixel sits near the middle; one side far nearer means an edge or a corner
        return da, db, ka, kb

    def nearest(self, px, py, r):
        best, kb = INF, -1
        for k in self.near(px, py, r):
            d = self.dist(k, px, py)[0]
            if d < best:
                best, kb = d, k
        return best, kb


# ---------------------------------------------------------------- one pass at one scale

def raster_pass(items, box, s, pad, exact=True, gap_cap_px=None):
    bx0, by0, bx1, by1 = box
    ox, oy = bx0 - pad / s, by0 - pad / s
    W = int(math.ceil((bx1 - bx0) * s)) + 2 * pad
    H = int(math.ceil((by1 - by0) * s)) + 2 * pad
    missed = []
    img, outlines = render(items, s, ox, oy, W, H, FLAT_TOL if exact else 0.25, missed)
    ink = Labels(img, W, H, 1)
    if not ink.info:
        raise LogoError("the shapes draw no ink at this scale")
    D2i, FXi, FYi = edt(img, W, H, 0, ink.runs)
    rin = ridge(img, W, H, 1, D2i, FXi, FYi)
    res = {"s": s, "ox": ox, "oy": oy, "W": W, "H": H, "img": img, "ink": ink, "missed": missed}
    if not exact:
        widths = {}
        for (i, j), (ax, ay, bx, by) in rin.items():
            w = math.hypot(ax - i, ay - j) + math.hypot(bx - i, by - j) - 1.0
            widths.setdefault(ink.at(i, j), []).append(w / s)
        res["coarse_widths"] = widths
        return res
    paper = Labels(img, W, H, 0)
    res["paper"] = paper
    edges = Edges(outlines, img, W, H, ink, paper)
    res["edges"] = edges
    # line widths: both sides of every inside ridge pixel, read on the outline
    wsamp = {}
    for (i, j), (ax, ay, bx, by) in rin.items():
        r = edges.two_sided(i + 0.5, j + 0.5, ax + 0.5, ay + 0.5, bx + 0.5, by + 0.5)
        if r is None:
            continue
        wsamp.setdefault(ink.at(i, j), []).append((r[0] + r[1]) / s)
    res["widths"] = wsamp
    # outside: gaps on channel ridges, and the widest circle in each counter
    D2o, FXo, FYo = edt(img, W, H, 1, paper.runs)
    cap2 = None if gap_cap_px is None else (gap_cap_px / 2.0 + 2) ** 2
    rout = ridge(img, W, H, 0, D2o, FXo, FYo, cap2)
    gaps = []
    for (i, j), (ax, ay, bx, by) in rout.items():
        if gap_cap_px is not None and math.hypot(ax - i, ay - j) + math.hypot(bx - i, by - j) > gap_cap_px + 3:
            continue
        r = edges.two_sided(i + 0.5, j + 0.5, ax + 0.5, ay + 0.5, bx + 0.5, by + 0.5)
        if r is None:
            continue
        da, db, ka, kb = r
        gaps.append(((da + db) / s, (i + 0.5) / s + ox, (j + 0.5) / s + oy, edges.lab[ka], edges.lab[kb]))
    res["gaps"] = gaps
    widest = {}
    for c, d in enumerate(paper.info):
        if d["border"]:
            continue
        best = (-1, 0, 0)
        for j in range(d["j0"], d["j1"]):
            st, en, lb = paper.starts[j], paper.ends[j], paper.labs[j]
            d2 = D2o[j]
            for a, b, l in zip(st, en, lb):
                if l != c:
                    continue
                for x in range(a, b):
                    if d2[x] > best[0]:
                        best = (d2[x], x, j)
        if best[0] > 0:
            # climb the exact distance to the outline from the best pixel, in shrinking steps
            r0 = math.sqrt(best[0]) + 3
            x, y = best[1] + 0.5, best[2] + 0.5
            dd = edges.nearest(x, y, r0)[0]
            h = 0.5
            while h > 0.01 and dd < INF:
                moved = False
                for mx, my in ((h, 0), (-h, 0), (0, h), (0, -h)):
                    d2 = edges.nearest(x + mx, y + my, r0)[0]
                    if d2 > dd:
                        x, y, dd, moved = x + mx, y + my, d2, True
                        break
                if not moved:
                    h /= 2
            widest[c] = 2 * dd / s if 0 < dd < INF else 2 * math.sqrt(best[0]) / s
    res["widest"] = widest
    return res


# ---------------------------------------------------------------- grouping

def cluster_1d(spans, thr):
    """spans: [(lo, hi, key)] sorted by lo. Merge overlaps, then split where the gap exceeds thr."""
    groups = []
    for lo, hi, key in sorted(spans):
        if groups and lo - groups[-1]["hi"] <= thr:
            g = groups[-1]
            g["hi"] = max(g["hi"], hi)
            g["keys"].append(key)
        else:
            groups.append({"lo": lo, "hi": hi, "keys": [key]})
    return groups


def merged_gaps(spans):
    g = cluster_1d(spans, 0.0)
    return [b["lo"] - a["hi"] for a, b in zip(g, g[1:])]


def split_parts(shapes, line_med):
    """Shapes into parts: break at horizontal gaps clearly larger than the letter gaps (or, for a
    stacked lockup, at a vertical one)."""
    for axis in ("x", "y"):
        lo, hi = ("x0", "x1") if axis == "x" else ("y0", "y1")
        spans = [(sh[lo], sh[hi], k) for k, sh in enumerate(shapes)]
        gaps = merged_gaps(spans)
        if not gaps:
            continue
        # a break is wider than 1.5 line widths and clearly wider than the other gaps
        brk = []
        for i, g in enumerate(gaps):
            others = sorted(gaps[:i] + gaps[i + 1:])
            if g > 1.5 * line_med and (not others or g > 1.8 * max(pct(others, 50), 0.0)):
                brk.append(g)
        if brk:
            groups = cluster_1d(spans, min(brk) - 1e-9)
            if len(groups) > 1:
                return axis, groups
    return None, [{"lo": None, "hi": None, "keys": list(range(len(shapes)))}]


def glyphs_of(shapes, keys):
    """Shapes of one part as letters: a dot or accent above a stem joins it."""
    order = sorted(keys, key=lambda k: (shapes[k]["x0"], shapes[k]["y0"]))
    glyphs = []
    for k in order:
        sh = shapes[k]
        joined = False
        for g in glyphs:
            ov = min(sh["x1"], g["x1"]) - max(sh["x0"], g["x0"])
            narrow = min(sh["x1"] - sh["x0"], g["x1"] - g["x0"])
            vert = min(sh["y1"], g["y1"]) - max(sh["y0"], g["y0"])
            if narrow > 0 and ov > 0.5 * narrow and vert <= 0:
                g["keys"].append(k)
                g["x0"], g["x1"] = min(g["x0"], sh["x0"]), max(g["x1"], sh["x1"])
                g["y0"], g["y1"] = min(g["y0"], sh["y0"]), max(g["y1"], sh["y1"])
                joined = True
                break
        if not joined:
            glyphs.append({"keys": [k], "x0": sh["x0"], "x1": sh["x1"], "y0": sh["y0"], "y1": sh["y1"]})
    glyphs.sort(key=lambda g: g["x0"])
    return glyphs


def in_a_row(glyphs):
    """Three or more letters side by side: neighbours overlap by under a third of the narrower one."""
    if len(glyphs) < 3:
        return False
    for a, b in zip(glyphs, glyphs[1:]):
        narrow = min(a["x1"] - a["x0"], b["x1"] - b["x0"])
        if narrow <= 0 or min(a["x1"], b["x1"]) - max(a["x0"], b["x0"]) > narrow / 3.0:
            return False
    return True


def value_groups(vals, tol):
    """vals: [(y, glyph)]. Groups of nearly equal y; each with its y and the number of glyphs."""
    out = []
    for y, g in sorted(vals):
        if out and y - out[-1]["ys"][-1] <= tol:
            out[-1]["ys"].append(y)
            out[-1]["glyphs"].add(g)
        else:
            out.append({"ys": [y], "glyphs": {g}})
    for o in out:
        o["y"] = pct(sorted(o["ys"]), 50)
        o["count"] = len(o["glyphs"])
    return out


# ---------------------------------------------------------------- the measurement

def measure_file(path, px_per_line=PX_PER_LINE, max_pixels=MAX_PIXELS, scale=None, gap_limit=GAP_LIMIT):
    t0 = time.time()
    root = read_svg(path)
    items, canvas, paper_colour, notes = collect(root)
    ink_items = [it for it in items if not it.eraser]
    if not ink_items:
        raise LogoError("no filled shapes to measure (text, strokes and construction groups are not measured)")
    box = bounds_of(ink_items)
    bw, bh = max(box[2] - box[0], 1e-9), max(box[3] - box[1], 1e-9)
    big = max(bw, bh)
    pad = 4
    # a quick coarse pass estimates the thinnest and the thickest line, which set the detail
    s0 = min(800.0 / big, math.sqrt(250000.0 / (bw * bh)))
    coarse = raster_pass(items, box, s0, pad, exact=False)
    meds = [pct(sorted(v), 50) for v in coarse["coarse_widths"].values() if len(v) >= 4]
    thinnest = min(meds) if meds else None
    thickest = max(meds) if meds else min(bw, bh) / 4.0
    s_cap = math.sqrt(max_pixels / (bw * bh))
    while s_cap > 1e-9 and (bw * s_cap + 2 * pad + 1) * (bh * s_cap + 2 * pad + 1) > max_pixels:
        s_cap *= 0.97
    capped = False
    if scale:
        s = float(scale)
        if s > s_cap:
            s, capped = s_cap, True
    else:
        s = px_per_line / thinnest if thinnest else s_cap
        capped = s > s_cap
        s = max(min(s, s_cap), s0)
    # the gap search reaches a little beyond the widest channel that can count in any part
    gap_cap = max(gap_limit, GAP_REACH) * thickest * s * 1.1 + 4
    res = raster_pass(items, box, s, pad, exact=True, gap_cap_px=gap_cap)
    s, ox, oy = res["s"], res["ox"], res["oy"]
    ink, paper, edges = res["ink"], res["paper"], res["edges"]
    notes["too thin to draw"] = res["missed"]

    # ---- shapes: exact boxes from the outline pieces on their edge
    nshape = len(ink.info)
    ex = [[INF, INF, -INF, -INF] for _ in range(nshape)]
    names = [{} for _ in range(nshape)]
    hole_box = {}
    green = [0.0] * nshape          # exact areas from the outline, by Green's theorem
    hole_green = {}
    for k in range(len(edges.x0)):
        l = edges.lab[k]
        if l < 0:
            continue
        cr = 0.5 * (edges.x0[k] * edges.y1[k] - edges.x1[k] * edges.y0[k]) * edges.inkside[k]
        green[l] += cr
        if edges.hole[k] >= 0:
            hole_green[edges.hole[k]] = hole_green.get(edges.hole[k], 0.0) - cr
        xa, xb = sorted((edges.x0[k], edges.x1[k]))
        ya, yb = sorted((edges.y0[k], edges.y1[k]))
        b = ex[l]
        b[0], b[1], b[2], b[3] = min(b[0], xa), min(b[1], ya), max(b[2], xb), max(b[3], yb)
        it = edges.item[k]
        if it is not None and it.named and not it.eraser:
            names[l][it.id] = names[l].get(it.id, 0) + 1
        hl = edges.hole[k]
        if hl >= 0 and not paper.info[hl]["border"]:
            hb = hole_box.setdefault(hl, [INF, INF, -INF, -INF, {}])
            hb[0], hb[1], hb[2], hb[3] = min(hb[0], xa), min(hb[1], ya), max(hb[2], xb), max(hb[3], yb)
            hb[4][l] = hb[4].get(l, 0) + 1
    shapes = []
    for l, d in enumerate(ink.info):
        b = ex[l]
        if b[0] == INF:
            b = [d["i0"], d["j0"], d["i1"], d["j1"]]
        x0, y0, x1, y1 = b[0] / s + ox, b[1] / s + oy, b[2] / s + ox, b[3] / s + oy
        w = res["widths"].get(l, [])
        st = stats(w)
        el = max(names[l].items(), key=lambda t: t[1])[0] if names[l] else ""
        area = d["px"] / (s * s)
        if green[l] > 0 and abs(green[l] - d["px"]) <= 0.15 * d["px"] + 4 * (b[2] - b[0] + b[3] - b[1]):
            area = green[l] / (s * s)
        shapes.append({"label": l, "x0": x0, "y0": y0, "x1": x1, "y1": y1, "width": x1 - x0, "height": y1 - y0,
                       "area": area, "line": st, "element": el,
                       "uneven": bool(st and st["median"] and (st["p90"] - st["p10"]) / st["median"] > 0.08)})
    # tiny specks (under a thousandth of the ink) are left out of parts and words
    total_area = sum(sh["area"] for sh in shapes)
    real = [k for k, sh in enumerate(shapes) if sh["area"] >= 1e-3 * total_area]
    meds = sorted(shapes[k]["line"]["median"] for k in real if shapes[k]["line"])
    line_med = pct(meds, 50) if meds else min(bw, bh) / 4.0
    sub = [shapes[k] for k in real]
    axis, groups = split_parts(sub, line_med)
    parts = []
    for g in groups:
        keys = [real[k] for k in g["keys"]]
        glyphs = glyphs_of(shapes, keys)
        parts.append({"keys": keys, "glyphs": glyphs})
    # ---- word detection and names
    for p in parts:
        p["word"] = word_metrics(p, shapes, edges, res, s, ox, oy) if in_a_row(p["glyphs"]) else None
    nwords = sum(1 for p in parts if p["word"])
    nmarks = len(parts) - nwords
    wi = mi = 0
    for p in parts:
        if p["word"]:
            wi += 1
            p["name"] = "word" if nwords == 1 else "word %d" % wi
        else:
            mi += 1
            p["name"] = "mark" if nmarks == 1 else "mark %d" % mi
        xs = [shapes[k] for k in p["keys"]]
        p["x0"], p["y0"] = min(sh["x0"] for sh in xs), min(sh["y0"] for sh in xs)
        p["x1"], p["y1"] = max(sh["x1"] for sh in xs), max(sh["y1"] for sh in xs)
        p["width"], p["height"] = p["x1"] - p["x0"], p["y1"] - p["y0"]
        pw = sorted(w for k in p["keys"] for w in res["widths"].get(shapes[k]["label"], []))
        p["line"] = stats(pw)
    # shape names: part and order, left to right
    for p in parts:
        order = sorted(p["keys"], key=lambda k: (round(shapes[k]["x0"], 6), shapes[k]["y0"]))
        for n, k in enumerate(order, 1):
            shapes[k]["name"] = "%s %d" % (p["name"], n)
            shapes[k]["part"] = p["name"]
    for k, sh in enumerate(shapes):
        sh.setdefault("name", "speck %d" % (k + 1))
        sh.setdefault("part", None)
    label_part = {shapes[k]["label"]: shapes[k]["part"] for k in range(len(shapes))}
    label_name = {shapes[k]["label"]: shapes[k]["name"] for k in range(len(shapes))}
    # ---- gaps per part, limited to narrow channels
    for p in parts:
        lw = p["line"]["median"] if p["line"] else line_med
        limit = gap_limit * lw
        cand = [g for g in res["gaps"] if label_part.get(g[3]) == p["name"] and label_part.get(g[4]) == p["name"]]
        # an airy mark: when most channel space is wider than the limit, the limit follows the most common width.
        p["gap_limit_from"] = "line"
        reach = [g[0] for g in cand if g[0] <= max(gap_limit, GAP_REACH) * lw]
        if reach and not p["word"]:          # in a word, the open insides of n and m are counters
            bw_ = 0.05 * lw
            hist = {}
            for v in reach:
                hist[int(v // bw_)] = hist.get(int(v // bw_), 0) + 1
            mode = (max(hist.items(), key=lambda t: (t[1], -t[0]))[0] + 0.5) * bw_
            near = sum(1 for v in reach if abs(v - mode) <= 0.1 * mode)
            run = near / (1.5 * s)               # about 1.5 ridge samples per px of channel length
            # a real channel: a sharp peak that runs along the mark, not open space widening steadily
            if mode > limit and near >= 0.3 * len(reach) and run >= 4 * lw:
                limit, p["gap_limit_from"] = 1.25 * mode, "most common channel %s" % fmt(mode, 3)
        samples = [g for g in cand if g[0] <= limit]
        p["gap_limit"] = limit
        p["gaps"] = stats([g[0] for g in samples])
        narrow = []
        for g in sorted(samples):
            if all(math.hypot(g[1] - q[1], g[2] - q[2]) > 2 * lw for q in narrow):
                narrow.append(g)
            if len(narrow) == 5:
                break
        p["narrowest"] = [{"gap": g[0], "x": g[1], "y": g[2], "between": sorted({label_name.get(g[3], "?"), label_name.get(g[4], "?")})}
                          for g in narrow]
        if p["word"]:
            letter_narrowest(p, shapes, res["gaps"])
    # ---- counters
    counters = []
    for hl, hb in hole_box.items():
        enclosing = max(hb[4].items(), key=lambda t: t[1])[0]
        x0, y0, x1, y1 = hb[0] / s + ox, hb[1] / s + oy, hb[2] / s + ox, hb[3] / s + oy
        area = paper.info[hl]["px"] / (s * s)
        hg = hole_green.get(hl, 0.0)
        if hg > 0 and abs(hg - paper.info[hl]["px"]) <= 0.15 * paper.info[hl]["px"] + 4 * (hb[2] - hb[0] + hb[3] - hb[1]):
            area = hg / (s * s)
        counters.append({"in": label_name.get(enclosing, "?"), "part": label_part.get(enclosing), "x0": x0, "y0": y0,
                         "x1": x1, "y1": y1, "width": x1 - x0, "height": y1 - y0,
                         "area": area, "widest_circle": res["widest"].get(hl)})
    counters.sort(key=lambda c: (c["x0"], c["y0"]))
    for p in parts:
        cw = sorted(c["width"] for c in counters if c["part"] == p["name"])
        p["counters"] = stats(cw)
    # ---- gaps between parts
    part_gaps = []
    for a, b in zip(parts, parts[1:]):
        g = (b["x0"] - a["x1"]) if axis == "x" else (b["y0"] - a["y1"])
        part_gaps.append({"from": a["name"], "to": b["name"], "gap": g, "axis": "horizontal" if axis == "x" else "vertical"})
    return {
        "file": path, "units": "SVG user units", "canvas": canvas, "paper": paper_colour, "notes": notes,
        "raster": {"px_per_unit": s, "width": res["W"], "height": res["H"], "thinnest_line_estimate": thinnest, "capped": capped,
                   "seconds": round(time.time() - t0, 2)},
        "box": {"x0": box[0], "y0": box[1], "x1": box[2], "y1": box[3]},
        "gap_limit": gap_limit,
        "shapes": shapes, "parts": parts, "part_gaps": part_gaps, "counters": counters,
    }


def word_metrics(p, shapes, edges, res, s, ox, oy):
    """Baseline, x-height, ascender, descender, stems and letter gaps of a part that reads as a word."""
    glyphs = p["glyphs"]
    if len(glyphs) < 3:
        return None
    gl_of = {}
    for gi, g in enumerate(glyphs):
        for k in g["keys"]:
            gl_of[shapes[k]["label"]] = gi
    ph = max(g["y1"] for g in glyphs) - min(g["y0"] for g in glyphs)
    lw = sorted(shapes[k]["line"]["median"] for k in p["keys"] if shapes[k]["line"])
    lw_med = pct(lw, 50) if lw else ph / 10.0
    img = res["img"]
    H, W = res["H"], res["W"]
    tops, bots = [], []
    flat_len = {}
    for k in range(len(edges.x0)):
        l = edges.lab[k]
        if l not in gl_of or not edges.straight[k]:
            continue
        ya, yb = edges.y0[k], edges.y1[k]
        if abs(ya - yb) > 1e-6 * max(1.0, abs(ya)):
            continue
        mx = (edges.x0[k] + edges.x1[k]) / 2
        i = int(math.floor(mx))
        jb, ja = int(math.floor(ya + 0.75)), int(math.floor(ya - 0.75))
        if not (0 <= i < W and 0 <= ja < H and 0 <= jb < H):
            continue
        below, above = img[jb][i], img[ja][i]
        key = (l, round(ya, 4), "top" if below and not above else ("bottom" if above and not below else ""))
        if key[2]:
            flat_len[key] = flat_len.get(key, 0.0) + abs(edges.x1[k] - edges.x0[k])
    for (l, y, kind), L in flat_len.items():
        if L / s >= 0.5 * lw_med:
            (tops if kind == "top" else bots).append((y / s + oy, gl_of[l]))
    tol = 0.004 * ph
    bottoms = [(g["y1"], gi) for gi, g in enumerate(glyphs)]
    bg = value_groups(bots, tol)
    method = {}
    if bg:
        b = max(bg, key=lambda o: (o["count"], -o["y"]))
        baseline, method["baseline"] = b["y"], "%d flat bottoms" % b["count"]
    else:
        b = max(value_groups(bottoms, tol * 3), key=lambda o: (o["count"], -o["y"]))
        baseline, method["baseline"] = b["y"], "%d letter bottoms, no flat ones" % b["count"]
    top_all = min(g["y0"] for g in glyphs)
    floor_top = top_all + 0.1 * (baseline - top_all)
    shape_tops = [shapes[k]["y0"] for k in p["keys"]]

    def ends_here(y):
        """Some shape (an i stem, an n) has its top on this line, up to an overshoot: a crossbar never does."""
        h = baseline - y
        return any(y - 0.12 * h <= t <= y + 0.01 * h for t in shape_tops)
    tg = [o for o in value_groups(tops, tol) if floor_top < o["y"] < baseline and ends_here(o["y"])]
    xh_kind = "x-height"
    if tg:
        t = max(tg, key=lambda o: (o["count"], o["y"]))
        xline, method["x-height"] = t["y"], "%d flat tops" % t["count"]
    else:
        lt = [(g["y0"], gi) for gi, g in enumerate(glyphs) if g["y0"] > floor_top]
        if lt:
            t = max(value_groups(lt, tol * 3), key=lambda o: (o["count"], o["y"]))
            xline, method["x-height"] = t["y"], "%d letter tops, no flat ones" % t["count"]
        else:
            t = max(value_groups([(g["y0"], gi) for gi, g in enumerate(glyphs)], tol * 3), key=lambda o: o["count"])
            xline, method["x-height"] = t["y"], "every letter reaches the top: capitals"
            xh_kind = "cap height"
    xh = baseline - xline
    if xh <= 0:
        return None
    # round letters: over both lines by a little
    ov = (0.005 * xh, 0.12 * xh)      # an overshoot is more than export rounding and less than an ascender
    rounds = [g for g in glyphs if ov[0] < xline - g["y0"] < ov[1] and ov[0] < g["y1"] - baseline < ov[1]]
    asc_top = top_all
    desc_bot = max(g["y1"] for g in glyphs)
    # stems and letter gaps along the line at mid x-height
    ym = ((baseline - xh / 2) - oy) * s
    cross = []
    for k in range(len(edges.x0)):
        l = edges.lab[k]
        if l not in gl_of:
            continue
        y0, y1 = edges.y0[k], edges.y1[k]
        if y0 == y1 or not (min(y0, y1) <= ym < max(y0, y1)):
            continue
        x0, x1 = edges.x0[k], edges.x1[k]
        x = x0 + (ym - y0) * (x1 - x0) / (y1 - y0)
        vertical = abs(x1 - x0) <= 0.02 * abs(y1 - y0)
        cross.append((x, edges.straight[k] and vertical, vertical, gl_of[l]))
    cross.sort()
    dedup = []
    for c in cross:
        if dedup and abs(c[0] - dedup[-1][0]) < 1e-6:
            continue
        dedup.append(c)
    runs = []
    jm = int(math.floor(ym))
    for a, b in zip(dedup, dedup[1:]):
        xm = int(math.floor((a[0] + b[0]) / 2))
        if 0 <= jm < H and 0 <= xm < W and img[jm][xm]:
            # a stroke is about twice as wide as the distance from its middle to the nearest edge;
            # a run through a crossbar (the middle of an H or an E) is far wider than that
            wpx = b[0] - a[0]
            d = edges.nearest((a[0] + b[0]) / 2.0, ym, wpx)[0]
            stroke = d < INF and wpx <= 1.3 * 2 * d
            runs.append({"x0": a[0] / s + ox, "x1": b[0] / s + ox, "w": wpx / s, "stroke": stroke,
                         "straight": a[1] and b[1], "vertical": a[2] and b[2], "glyph": a[3]})
    strokes = [r for r in runs if r["stroke"]] or runs
    stems = [r["w"] for r in strokes if r["straight"]]
    if stems:
        stem_method = "%d straight vertical stems" % len(stems)
    else:
        stems = [r["w"] for r in strokes if r["vertical"]]
        stem_method = "%d upright strokes, no straight stems" % len(stems)
        if not stems and strokes:
            ws = sorted(r["w"] for r in strokes)
            stems = ws[:max(1, len(ws) // 2)]
            stem_method = "the narrower half of the strokes, no upright ones"
    stem = pct(sorted(stems), 50) if stems else None
    gaps = []
    for a, b in zip(runs, runs[1:]):
        if b["glyph"] != a["glyph"]:
            gaps.append({"between": [a["glyph"] + 1, b["glyph"] + 1], "gap": b["x0"] - a["x1"]})
    return {
        "glyphs": len(glyphs), "baseline": baseline, "x_line": xline, "x_height": xh, "x_height_kind": xh_kind,
        "round_height": pct(sorted(g["y1"] - g["y0"] for g in rounds), 50) if rounds else None,
        "round_count": len(rounds),
        "ascender_top": asc_top, "ascender": baseline - asc_top,
        "descender_bottom": desc_bot, "descender": desc_bot - baseline,
        "stem": stem, "stem_method": stem_method, "stem_values": stats(stems),
        "mid_line": baseline - xh / 2,
        "letter_gaps": gaps, "letter_gap": stats([g["gap"] for g in gaps]), "method": method,
        "glyph_boxes": [{"x0": g["x0"], "x1": g["x1"], "y0": g["y0"], "y1": g["y1"]} for g in glyphs],
    }


def letter_narrowest(p, shapes, gaps):
    """The narrowest point between neighbouring letters, from the channel ridges."""
    w = p["word"]
    gl_of = {}
    for gi, g in enumerate(p["glyphs"]):
        for k in g["keys"]:
            gl_of[shapes[k]["label"]] = gi
    best = {}
    for g in gaps:
        a, b = gl_of.get(g[3]), gl_of.get(g[4])
        if a is None or b is None or abs(a - b) != 1:
            continue
        key = (min(a, b), max(a, b))
        if key not in best or g[0] < best[key]:
            best[key] = g[0]
    for lg in w["letter_gaps"]:
        key = (lg["between"][0] - 1, lg["between"][1] - 1)
        lg["narrowest"] = best.get(key)


# ---------------------------------------------------------------- the ladder

def ladder_items(m):
    """Every measured value as (name, value), ready for proportion_check's ladder."""
    items = []
    parts = m["parts"]
    words = [p for p in parts if p["word"]]
    marks = [p for p in parts if not p["word"]]
    for p in marks:
        pre = "" if (len(parts) == 1) else (p["name"] + " ")
        if p["line"]:
            items.append((pre + "line", p["line"]["median"]))
        if p["gaps"]:
            items.append((pre + "gap", p["gaps"]["median"]))
        if p["counters"]:
            items.append((pre + "counter", p["counters"]["median"]))
        items.append((pre + "height", p["height"]))
        items.append((pre + "width", p["width"]))
    for p in words:
        w = p["word"]
        pre = "" if len(words) == 1 else (p["name"] + " ")
        if w["stem"]:
            items.append((pre + "stem", w["stem"]))
        items.append((pre + ("x-height" if w["x_height_kind"] == "x-height" else "cap height"), w["x_height"]))
        if w["ascender"] > w["x_height"] * 1.05:
            items.append((pre + "ascender", w["ascender"]))
        if w["descender"] > 0.05 * w["x_height"]:
            items.append((pre + "descender", w["descender"]))
        if w["letter_gap"]:
            items.append((pre + "letter gap", w["letter_gap"]["median"]))
        if p["counters"]:
            items.append((pre + "counter", p["counters"]["median"]))
    for g in m["part_gaps"]:
        items.append(("part gap" if len(m["part_gaps"]) == 1 else "part gap %s to %s" % (g["from"], g["to"]), g["gap"]))
    return [(n, v) for n, v in items if v is not None and v > 0]


def default_unit(m):
    names = [n for n, _ in ladder_items(m)]
    for n in ("stem", "word stem", "line", "mark line"):
        if n in names:
            return n
    stems = [n for n in names if n.endswith("stem")]
    lines = [n for n in names if n.endswith("line")]
    return (stems or lines or [None])[0]


def ladder_step(ratio, half=False, tol=3.0):
    """A ratio on the phi ladder: the nearest step, where it lands, how far off, and the steps around it."""
    st = 0.5 if half else 1.0
    lp = math.log(PHI)
    lg = math.log(ratio) / lp / st
    lo, hi = math.floor(lg) * st, (math.floor(lg) + 1) * st
    k = min((lo, hi), key=lambda c: abs(ratio / PHI ** c - 1))
    land = PHI ** k
    dev = (ratio - land) / land * 100
    return {"step": k, "lands_at": land, "deviation_pct": round(dev, 2), "verdict": pc.verdict_of(dev, tol),
            "below": PHI ** lo, "above": PHI ** hi}


RELATIONS = {
    "line/unit": "mark line width over the wordmark stem",
    "gap/line": "mark gap over the mark line width",
    "x-height/stem": "x-height over the stem",
    "icon height/x-height": "mark height over the x-height",
    "part gap/stem": "gap between the parts over the stem",
    "letter gap/stem": "letter gap at mid x-height over the stem (opt in)",
    "icon height/line": "mark height over its line width (opt in)",
}
DEFAULT_RELATIONS = ["line/unit", "gap/line", "x-height/stem", "icon height/x-height", "part gap/stem"]


def relations(m, names=None):
    """The logo's relations as (name, label, a, b) for the ones this logo has."""
    names = names or DEFAULT_RELATIONS
    words = [p for p in m["parts"] if p["word"]]
    marks = [p for p in m["parts"] if not p["word"]]
    w = words[0]["word"] if words else None
    mk = max(marks, key=lambda p: p["width"] * p["height"]) if marks else None
    gap = None
    if words and marks and m["part_gaps"]:
        for g in m["part_gaps"]:
            if {g["from"], g["to"]} == {mk["name"], words[0]["name"]}:
                gap = g["gap"]
    out = []
    for n in names:
        if n == "line/unit" and w and w["stem"] and mk and mk["line"]:
            out.append((n, "mark line %s / stem %s" % (sig(mk["line"]["median"]), sig(w["stem"])), mk["line"]["median"], w["stem"]))
        elif n == "gap/line" and mk and mk["gaps"] and mk["line"]:
            out.append((n, "mark gap %s / mark line %s" % (sig(mk["gaps"]["median"]), sig(mk["line"]["median"])), mk["gaps"]["median"], mk["line"]["median"]))
        elif n == "x-height/stem" and w and w["stem"]:
            out.append((n, "%s %s / stem %s" % (w["x_height_kind"], sig(w["x_height"]), sig(w["stem"])), w["x_height"], w["stem"]))
        elif n == "icon height/x-height" and w and mk:
            out.append((n, "mark height %s / %s %s" % (sig(mk["height"]), w["x_height_kind"], sig(w["x_height"])), mk["height"], w["x_height"]))
        elif n == "part gap/stem" and w and w["stem"] and gap and gap > 0:
            out.append((n, "part gap %s / stem %s" % (sig(gap), sig(w["stem"])), gap, w["stem"]))
        elif n == "letter gap/stem" and w and w["stem"] and w["letter_gap"]:
            out.append((n, "letter gap %s / stem %s" % (sig(w["letter_gap"]["median"]), sig(w["stem"])), w["letter_gap"]["median"], w["stem"]))
        elif n == "icon height/line" and mk and mk["line"]:
            out.append((n, "mark height %s / mark line %s" % (sig(mk["height"]), sig(mk["line"]["median"])), mk["height"], mk["line"]["median"]))
    return out


def resolve_unit(items, unit):
    """--unit is a name from the items or a number; a number joins the items as 'unit'."""
    if unit is None:
        return items, None
    try:
        v = float(unit)
    except ValueError:
        names = [n for n, _ in items]
        if unit not in names:
            # a mark on its own names its rows "line", "gap"; a lockup names them "mark line", "mark gap"
            if unit.startswith("mark ") and unit[5:] in names:
                return items, unit[5:]
            if "mark " + unit in names:
                return items, "mark " + unit
        return items, unit
    if not math.isfinite(v) or v <= 0:
        raise LogoError("--unit must be a name from the table or a positive number")
    return items + [("unit", v)], "unit"


# ---------------------------------------------------------------- printing

def decimals(m):
    """One decimal count per logo: 3 for a logo about 200 units wide, 2 for about 2000."""
    b = m["box"]
    size = max(b["x1"] - b["x0"], b["y1"] - b["y0"], 1e-9)
    return max(1, min(6, 5 - int(math.floor(math.log10(size)))))


def print_report(m, unit=None, half=False, tol=3.0, ladder=True):
    nd = decimals(m)

    def sig(v, n=4):          # noqa: F811  (lengths in this report print with the logo's decimals)
        return "-" if v is None else fmt(v, nd)
    r = m["raster"]
    cv = m["canvas"]
    print("Logo measure: %s" % os.path.basename(m["file"]))
    print("Values in SVG user units%s. Drawn at %s px per unit (%d x %d px%s) in %s s.%s" % (
        " (viewBox %s)" % " ".join(fmt(v) for v in cv) if cv else "", pc.sig(r["px_per_unit"]), r["width"], r["height"],
        ", capped by --max-pixels" if r.get("capped") else "",
        fmt(r["seconds"], 2), " Background %s; shapes in that colour cut the ink." % m["paper"] if m["paper"] else ""))
    nt = m["notes"]
    extra = []
    if nt["text"]:
        extra.append("%d text element(s) not measured: outline the type" % nt["text"])
    if nt["image"]:
        extra.append("%d image(s) not measured" % nt["image"])
    if nt["stroke only"]:
        extra.append("%d stroke-only element(s) not measured (golden_lint reads their stroke-width)" % nt["stroke only"])
    if nt["translucent"]:
        extra.append("%d translucent fill(s) under half opacity left out as overlays" % nt["translucent"])
    if nt.get("too thin to draw"):
        extra.append("%d shape(s) too thin to draw at this detail (%s): raise --scale to measure them" % (
            len(nt["too thin to draw"]), ", ".join(nt["too thin to draw"][:5])))
    if nt["clip-path ignored"]:
        extra.append("%d clip path(s) ignored" % nt["clip-path ignored"])
    if nt["skipped construction"]:
        extra.append("construction skipped: %s" % ", ".join(nt["skipped construction"]))
    if extra:
        print("Note: " + "; ".join(extra) + ".")
    print("\nParts")
    print("| part | shapes | x | y | width | height | line median | gap median |")
    print("|:---|---:|:---|:---|---:|---:|---:|---:|")
    for p in m["parts"]:
        print("| %s | %d | %s to %s | %s to %s | %s | %s | %s | %s |" % (
            p["name"], len(p["keys"]), sig(p["x0"]), sig(p["x1"]), sig(p["y0"]), sig(p["y1"]), sig(p["width"]), sig(p["height"]),
            sig(p["line"]["median"]) if p["line"] else "-", sig(p["gaps"]["median"]) if p["gaps"] else "-"))
    for g in m["part_gaps"]:
        print("\nGap %s to %s: %s (%s, edge to edge)." % (g["from"], g["to"], sig(g["gap"]), g["axis"]))
    print("\nShapes (line width = the distance across the ink at the middle of the line, read on the outline)")
    print("| shape | element | x | y | width | height | area | line median | p10 | p90 | min | max | |")
    print("|:---|:---|:---|:---|---:|---:|---:|---:|---:|---:|---:|---:|:---|")
    for sh in sorted(m["shapes"], key=lambda t: (t["part"] or "~", t["x0"], t["y0"])):
        ln = sh["line"]
        cells = [sig(ln[k]) for k in ("median", "p10", "p90", "min", "max")] if ln else ["-"] * 5
        print("| %s | %s | %s to %s | %s to %s | %s | %s | %s | %s | %s |" % (
            sh["name"], sh["element"][:24], sig(sh["x0"]), sig(sh["x1"]), sig(sh["y0"]), sig(sh["y1"]), sig(sh["width"]),
            sig(sh["height"]), fmt(sh["area"], max(0, nd - 2)), " | ".join(cells), "uneven" if sh["uneven"] else "even" if ln else ""))
    print("\nGaps between ink edges (channels up to %s x the part's line width; wider space is open space)" % fmt(m["gap_limit"], 2))
    for p in m["parts"]:
        if p.get("gap_limit_from", "line") != "line":
            print("%s: most channel space is wider, so the limit is 1.25 x its %s." % (p["name"], p["gap_limit_from"]))
    print("| part | samples | median | p10 | p90 | min | max | narrowest at (x, y) |")
    print("|:---|---:|---:|---:|---:|---:|---:|:---|")
    for p in m["parts"]:
        g = p["gaps"]
        if not g:
            print("| %s | 0 | - | - | - | - | - | none narrower than %s |" % (p["name"], sig(p["gap_limit"])))
            continue
        where = "; ".join("%s at (%s, %s) %s" % (sig(n["gap"]), sig(n["x"]), sig(n["y"]), " / ".join(n["between"])) for n in p["narrowest"][:3])
        print("| %s | %d | %s | %s | %s | %s | %s | %s |" % (p["name"], g["n"], sig(g["median"]), sig(g["p10"]), sig(g["p90"]),
                                                          sig(g["min"]), sig(g["max"]), where))
    if m["counters"]:
        print("\nCounters (closed)")
        print("| in shape | x | y | width | height | area | widest circle |")
        print("|:---|:---|:---|---:|---:|---:|---:|")
        for c in m["counters"]:
            print("| %s | %s to %s | %s to %s | %s | %s | %s | %s |" % (c["in"], sig(c["x0"]), sig(c["x1"]), sig(c["y0"]), sig(c["y1"]),
                                                                    sig(c["width"]), sig(c["height"]), fmt(c["area"], max(0, nd - 2)),
                                                                    sig(c["widest_circle"])))
    for p in m["parts"]:
        w = p["word"]
        if not w:
            continue
        print("\nWord (%s, %d letters)" % (p["name"], w["glyphs"]))
        print("| measure | value | where |")
        print("|:---|---:|:---|")
        print("| baseline | | y %s (%s) |" % (sig(w["baseline"]), w["method"]["baseline"]))
        print("| %s | %s | top y %s (%s) |" % (w["x_height_kind"], sig(w["x_height"]), sig(w["x_line"]), w["method"]["x-height"]))
        if w["round_height"]:
            print("| round height, with overshoot | %s | %d round letter(s) |" % (sig(w["round_height"]), w["round_count"]))
        print("| ascender | %s | top y %s |" % (sig(w["ascender"]), sig(w["ascender_top"])))
        print("| descender | %s | bottom y %s |" % (sig(w["descender"]), sig(w["descender_bottom"])))
        sv = w["stem_values"]
        print("| stem | %s | %s at y %s%s |" % (sig(w["stem"]), w["stem_method"], sig(w["mid_line"]),
                                                ", %s to %s" % (sig(sv["min"]), sig(sv["max"])) if sv and sv["n"] > 1 else ""))
        if w["letter_gap"]:
            lg = w["letter_gap"]
            print("| letter gap at mid x-height | %s | median of %d; %s to %s |" % (sig(lg["median"]), lg["n"], sig(lg["min"]), sig(lg["max"])))
            print("\nLetter gaps (letters numbered from the left): " + ", ".join(
                "%d-%d %s%s" % (g["between"][0], g["between"][1], sig(g["gap"]),
                                " (narrowest %s)" % sig(g["narrowest"]) if g.get("narrowest") else "") for g in w["letter_gaps"]))
    if not ladder:
        return
    print()
    print_ladder_for(m, unit, half, tol)


def print_ladder_for(m, unit=None, half=False, tol=3.0, as_json=False):
    items = ladder_items(m)
    items, uname = resolve_unit(items, unit)
    uname = uname or default_unit(m)
    head, rows = pc.ladder_rows(items, uname, tol, half)
    if isinstance(head, str):
        raise LogoError(head + "; the names are: " + ", ".join(n for n, _ in items))
    if head is None:
        raise LogoError("nothing measured to put on the ladder")
    pc.print_ladder(head, rows, tol, half, as_json)


def to_json(m, unit=None, half=False, tol=3.0):
    out = dict(m)
    out["parts"] = [{k: v for k, v in p.items() if k not in ("keys", "glyphs")} for p in m["parts"]]
    for p, src in zip(out["parts"], m["parts"]):
        p["shapes"] = sorted(m["shapes"][k]["name"] for k in src["keys"])
    out["shapes"] = [{k: v for k, v in sh.items() if k != "label"} for sh in m["shapes"]]
    items, uname = resolve_unit(ladder_items(m), unit)
    uname = uname or default_unit(m)
    head, rows = pc.ladder_rows(items, uname, tol, half)
    if head and not isinstance(head, str):
        out["ladder"] = {"unit": {"name": head[0], "value": head[1]}, "tolerance_pct": tol, "half_steps": half,
                         "chance_on": round(pc.ladder_chance(tol, half), 3), "rows": rows}
    out["relations"] = []
    for n, label, a, b in relations(m, list(RELATIONS)):
        st = ladder_step(a / b, half, tol)
        out["relations"].append(dict(st, name=n, label=label, ratio=a / b))
    return out


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("svg", help="the logo as an SVG of filled shapes")
    p.add_argument("--unit", help="ladder unit: a name from the ladder (stem, line, mark line, x-height ...) or a number")
    p.add_argument("--half", action="store_true", help="allow half steps (1.272) on the ladder as well as whole steps")
    p.add_argument("--tolerance", type=float, default=3.0, help="percent counted as on a step (default 3)")
    p.add_argument("--px-per-line", type=float, default=PX_PER_LINE, help="raster detail: px across the thinnest line (default 20)")
    p.add_argument("--max-pixels", type=float, default=MAX_PIXELS, help="raster size cap, for speed (default 2000000)")
    p.add_argument("--scale", type=float, help="px per SVG unit, in place of --px-per-line")
    p.add_argument("--gap-limit", type=float, default=GAP_LIMIT, help="widest channel counted as a gap, as a multiple of the line width (default 1.25)")
    p.add_argument("--no-ladder", action="store_true", help="the measurement only")
    p.add_argument("--json", action="store_true")
    a = p.parse_args()
    for name in ("tolerance", "px_per_line", "max_pixels", "gap_limit"):
        v = getattr(a, name)
        if not math.isfinite(v) or v <= 0:
            p.error("--%s must be a positive number" % name.replace("_", "-"))
    if a.scale is not None and (not math.isfinite(a.scale) or a.scale <= 0):
        p.error("--scale must be a positive number")
    try:
        m = measure_file(a.svg, a.px_per_line, a.max_pixels, a.scale, a.gap_limit)
        if a.json:
            print(json.dumps(to_json(m, a.unit, a.half, a.tolerance), indent=2, default=lambda o: sorted(o) if isinstance(o, set) else str(o)))
        else:
            print_report(m, a.unit, a.half, a.tolerance, not a.no_ladder)
    except LogoError as e:
        sys.exit("logo_measure: %s" % e)


if __name__ == "__main__":
    main()
