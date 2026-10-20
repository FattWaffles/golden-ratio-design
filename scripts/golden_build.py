#!/usr/bin/env python3
"""golden_build.py: build a mark from a plan written in the golden grammar, with no free numbers.

A plan is JSON. Every size is a term of the kit (1 2 3 5 8 13 21 ...), every position a named
point of the golden frame plus kit offsets, every stroke a phi step, every angle from the
contract's list. A value outside those sets is refused, unless the plan logs it as a departure
with a reason. The engine renders an SVG (grid underneath, named parts, cuts as masks, a notes
line) and an Illustrator script that draws the same construction on an unlocked "Construction"
layer under the locked "Golden grid" layer, so a designer finishes it by hand.

  python3 -I golden_build.py plan.json --out mark.svg --jsx mark.jsx
  python3 -I golden_build.py --grammar          (prints the vocabulary)
  python3 -I golden_build.py --example shell    (prints a plan to start from)
"""
import argparse
import json
import math
import os
import re
import sys
from xml.sax.saxutils import escape

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from golden_grid import PHI, INV, FIB, golden_squares, eye_point, spiral_path, arc_beziers, grid_groups, fmt  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_CONTRACT = os.path.join(HERE, "..", "contract", "golden.json")
QUARTERS = {"ne": (270, 360), "se": (0, 90), "sw": (90, 180), "nw": (180, 270)}  # screen angles, y down, 0 = east

GRAMMAR = """
PLAN
  name          a short name
  unit          px per kit unit (any number above 0; it sets scale only)
  kit           optional, default 1 2 3 5 8 13 21 34 55 89 144
  frame         "golden landscape w:21" | "golden portrait h:21" | "square s:13"
  stroke_unit   "phi:-3" (unit times phi to that power; default -3, about a quarter unit)
  ink, paper    colours for fills and cuts (default #0E0E14 and #FFFFFF)
  parts         list, drawn in order; a cut applies to the nearest solid part before it (or "cut": "<id>")

PART, one shape key plus options
  "circle": "d:8"                       diameter in kit units
  "rect": "golden landscape w:8"        golden rectangle by width
  "rect": "golden portrait h:8"         golden rectangle by height
  "rect": "square s:5"                  square
  "line": "len:8", "angle": ...         a stroke; angle from the contract list, "golden" = 137.5
  "arc": "d:8", "quarter": "ne"         quarter circle of that diameter, quadrant ne se sw nw
  "spiral": "squares:6"                 the frame's own spiral (or "w:13" for a smaller one)
  "id": "outer"                         a name, used by the SVG, the layer and cut targets
  "at": "eye"                           a frame point: centre eye crossing-tl crossing-tr
                                        crossing-bl crossing-br top bottom left right corner-tl
                                        corner-tr corner-bl corner-br square-N square-N-tl ... -br
  "at": "eye dx:2 dy:-3"                plus offsets in kit units (kit terms, signed)
  "fill": "ink" | "paper" | "none" | "#hex"
  "stroke": "step:2"                    stroke width = stroke_unit times phi^(step-1), steps 1 to 6; absent means no stroke on
                                        a circle or rect and step:1 on a line, arc or spiral
  "cut": true | "<id>"                  subtract this shape from the nearest solid part before it (or that id)
  "join": true                          unite with the previous solid part (a group in the SVG, Pathfinder Add in Illustrator)
  "rotate": angle                       from the contract list, anticlockwise like "angle"
  "radius": "d:1"                       corner radius for rects, a kit term

DEPARTURES
  a size, radius, frame or angle may be written as {"value": 20, "departure": "the box leans 20 degrees, the concept"}
  it is accepted and written into the notes; a bare number outside the sets is refused
  (offsets and stroke steps take kit terms and steps only)
"""

EXAMPLES = {
    "shell": {
        "name": "shell", "unit": 12, "frame": "golden landscape w:21",
        "parts": [
            {"id": "frame-line", "rect": "golden landscape w:21", "at": "centre", "fill": "none", "stroke": "step:1"},
            {"id": "spiral", "spiral": "squares:6", "stroke": "step:4"},
            {"id": "eye-dot", "circle": "d:2", "at": "eye", "fill": "ink"},
        ],
    },
    "letter-o": {
        "name": "letter o", "unit": 14, "frame": "golden portrait h:13",
        "parts": [
            {"id": "ring", "circle": "d:8", "at": "centre", "fill": "ink"},
            {"id": "counter", "circle": "d:5", "at": "centre", "cut": True},
            {"id": "notch", "rect": "square s:1", "at": "centre dx:3 dy:-3", "cut": "ring"},
        ],
    },
    "monogram": {
        "name": "ob monogram", "unit": 12, "frame": "golden landscape w:21",
        "parts": [
            {"id": "box", "rect": "square s:13", "at": "square-1", "fill": "ink"},
            {"id": "o", "circle": "d:8", "at": "square-2", "fill": "ink"},
            {"id": "o-counter", "circle": "d:5", "at": "square-2", "cut": "o"},
            {"id": "slash", "line": "len:13", "angle": 58.3, "at": "square-1", "stroke": "step:3", "cut": "box"},
            {"id": "mark-line", "rect": "golden landscape w:21", "at": "centre", "fill": "none", "stroke": "step:1"},
        ],
    },
}


class PlanError(Exception):
    pass


# ---------------------------------------------------------------- parsing

def parse_num(token, kit, errors, where, allow_negative=False, allow_zero=False):
    """A kit term, or a departure object. Returns float or None."""
    if isinstance(token, dict) and "value" in token:
        if not token.get("departure"):
            errors.append("%s: a departure needs a reason, as {\"value\": N, \"departure\": \"why\"}" % where); return None, None
        try:
            return float(token["value"]), token["departure"]
        except (TypeError, ValueError):
            errors.append("%s: departure value %r is not a number" % (where, token["value"])); return None, None
    try:
        v = float(token)
    except (TypeError, ValueError):
        errors.append("%s: %r is not a number" % (where, token)); return None, None
    if v == 0 and allow_zero:
        return 0.0, None
    mag = abs(v)
    if mag in kit and (v > 0 or allow_negative):
        return v, None
    near = min(kit, key=lambda k: abs(k - mag))
    errors.append("%s: %s is not in the kit %s; nearest %s" % (where, fmt(v), " ".join(fmt(k) for k in kit), fmt(near if v > 0 else -near)))
    return None, None


def parse_spec(spec, key, kit, errors, where):
    """'d:8' -> 8, 'golden landscape w:8' -> ('landscape', 8) ..."""
    if isinstance(spec, dict):
        v, dep = parse_num(spec, kit, errors, where)
        return {"n": v, "dep": dep, "kind": None}
    m = re.search(r"(\w+):(\S+)", str(spec))
    if not m:
        errors.append("%s: cannot read %r" % (where, spec)); return None
    tag, val = m.group(1), m.group(2)
    if key == "spiral" and tag == "squares":
        try:
            n = int(val)
        except ValueError:
            errors.append("%s: squares should be a whole number" % where); return None
        if n < 1:
            errors.append("%s: squares must be at least 1" % where); return None
        return {"n": float(n), "dep": None, "kind": None, "tag": tag}
    v, dep = parse_num(val, kit, errors, where)
    kind = None
    low = str(spec).lower()
    if key == "rect":
        kind = "square" if "square" in low else ("portrait" if "portrait" in low else ("landscape" if "landscape" in low else {"s": "square", "h": "portrait", "w": "landscape"}.get(tag)))
        if kind is None or (kind == "square" and tag != "s") or (kind == "portrait" and tag != "h") or (kind == "landscape" and tag != "w"):
            errors.append("%s: landscape takes w:, portrait takes h:, square takes s: (got %r)" % (where, spec)); return None
    return {"n": v, "dep": dep, "kind": kind, "tag": tag}


def parse_angle(token, angles, errors, where):
    if token is None:
        return 0.0, None
    if isinstance(token, str) and token.lower() == "golden":
        return 137.5, None
    if isinstance(token, dict) and token.get("departure"):
        return float(token["value"]), token["departure"]
    try:
        v = float(token)
    except (TypeError, ValueError):
        errors.append("%s: angle %r unreadable; use golden or one of %s" % (where, token, " ".join(fmt(x) for x in angles))); return None, None
    for a in angles:
        if abs(v - a) < 0.05:
            return float(a), None
    near = min(angles, key=lambda a: abs(a - v))
    errors.append("%s: angle %s is not in the contract list; nearest %s (or log it as a departure)" % (where, fmt(v), fmt(near)))
    return None, None


def parse_at(token, kit, errors, where):
    if not token:
        return "centre", 0.0, 0.0, []
    parts = str(token).split()
    name, dx, dy, deps = parts[0], 0.0, 0.0, []
    seen = set()
    for p in parts[1:]:
        m = re.match(r"(dx|dy):(-?[\d.]+)$", p)
        if not m:
            errors.append("%s: offset %r should be dx:N or dy:N" % (where, p)); continue
        if m.group(1) in seen:
            errors.append("%s: %s given twice" % (where, m.group(1))); continue
        seen.add(m.group(1))
        v, dep = parse_num(m.group(2), kit, errors, where + " " + m.group(1), allow_negative=True, allow_zero=True)
        if v is None:
            continue
        if m.group(1) == "dx":
            dx = v
        else:
            dy = v
        if dep:
            deps.append(dep)
    return name, dx, dy, deps


# ---------------------------------------------------------------- frame

def frame_points(W, H):
    sq, _ = golden_squares(0, 0, W, H, 10)
    ex, ey = (W / 2, H / 2) if abs(W - H) < 1e-9 else eye_point(0, 0, W, H)
    pts = {
        "centre": (W / 2, H / 2), "eye": (ex, ey),
        "crossing-tl": (W * INV * INV, H * INV * INV), "crossing-tr": (W * INV, H * INV * INV),
        "crossing-bl": (W * INV * INV, H * INV), "crossing-br": (W * INV, H * INV),
        "top": (W / 2, 0), "bottom": (W / 2, H), "left": (0, H / 2), "right": (W, H / 2),
        "corner-tl": (0, 0), "corner-tr": (W, 0), "corner-bl": (0, H), "corner-br": (W, H),
    }
    for i, (x, y, s, d) in enumerate(sq, 1):
        pts["square-%d" % i] = (x + s / 2, y + s / 2)
        pts["square-%d-tl" % i] = (x, y); pts["square-%d-tr" % i] = (x + s, y)
        pts["square-%d-bl" % i] = (x, y + s); pts["square-%d-br" % i] = (x + s, y + s)
    return pts, sq


# ---------------------------------------------------------------- build

def build(plan, contract):
    errors, deps = [], []
    try:
        kit = [float(k) for k in plan.get("kit", FIB[1:12])]
        unit = float(plan.get("unit", 10))
    except (TypeError, ValueError):
        raise PlanError("unit and kit must be numbers")
    if unit <= 0:
        raise PlanError("unit must be above 0, got %s" % fmt(unit))
    if not kit or any(k <= 0 for k in kit):
        raise PlanError("kit terms must be above 0")
    if "parts" not in plan or not isinstance(plan["parts"], list) or not plan["parts"]:
        raise PlanError("the plan needs a parts list with at least one part")
    angles = contract.get("angles", [0, 90, 180, 270, 36, 72, 108, 137.5, 31.7, 58.3])
    frame_spec = plan.get("frame", "golden landscape w:21")
    fr = parse_spec(frame_spec, "rect", kit, errors, "frame" if "frame" in plan else "frame (default golden landscape w:21)")
    if fr is None or fr["n"] is None:
        raise PlanError("\n".join(errors))
    if fr["dep"]:
        deps.append("frame %s: %s" % (fmt(fr["n"]), fr["dep"]))
    if fr["kind"] == "square":
        W = H = fr["n"] * unit
    elif fr["kind"] == "portrait":
        H = fr["n"] * unit; W = H * INV
    else:
        W = fr["n"] * unit; H = W * INV
    su = re.match(r"phi:(-?\d+)$", str(plan.get("stroke_unit", "phi:-3")))
    if not su:
        raise PlanError("stroke_unit should be phi:N (unit times phi to the power N), got %r" % plan.get("stroke_unit"))
    stroke_unit = unit * PHI ** int(su.group(1))
    max_step = int(contract.get("domains", {}).get("stroke", {}).get("steps", 6))
    pts, sq = frame_points(W, H)
    ink, paper = plan.get("ink", "#0E0E14"), plan.get("paper", "#FFFFFF")
    for label, col in (("ink", ink), ("paper", paper)):
        if not re.match(r"^#[0-9A-Fa-f]{6}$", str(col)):
            raise PlanError("%s should be #rrggbb, got %r" % (label, col))
    parts = []
    for i, p in enumerate(plan.get("parts", [])):
        where = "part %d (%s)" % (i + 1, p.get("id", "no id"))
        pid = str(p.get("id") or "part-%d" % (i + 1))
        if pid in [q["id"] for q in parts]:
            errors.append("%s: id %r is already used" % (where, pid)); continue
        kind = next((k for k in ("circle", "rect", "line", "arc", "spiral") if k in p), None)
        if not kind:
            errors.append("%s: needs circle, rect, line, arc or spiral" % where); continue
        spec = parse_spec(p[kind], kind, kit, errors, where)
        if spec is None or spec["n"] is None:
            continue
        if spec["dep"]:
            deps.append("%s size %s: %s" % (pid, fmt(spec["n"]), spec["dep"]))
        name, dx, dy, d2 = parse_at(p.get("at"), kit, errors, where)
        deps += ["%s offset: %s" % (pid, d) for d in d2]
        if name not in pts:
            errors.append("%s: unknown point %r (use centre, eye, crossing-tl/tr/bl/br, square-1 to square-%d with -tl/-tr/-bl/-br, corner-tl/tr/bl/br, top, bottom, left, right)" % (where, name, len(sq))); continue
        cx, cy = pts[name][0] + dx * unit, pts[name][1] + dy * unit
        stroke_w = None
        if p.get("stroke"):
            m = re.match(r"step:([1-9]\d*)$", str(p["stroke"]))
            if not m or int(m.group(1)) > max_step:
                errors.append("%s: stroke %r should be step:N with N from 1 (hairline) to %d" % (where, p["stroke"], max_step)); continue
            stroke_w = stroke_unit * PHI ** (int(m.group(1)) - 1)
        angle, adep = parse_angle(p.get("angle"), angles, errors, where) if "angle" in p else (0.0, None)
        if adep:
            deps.append("%s angle %s: %s" % (pid, fmt(angle), adep))
        rot, rdep = parse_angle(p.get("rotate"), angles, errors, where) if "rotate" in p else (0.0, None)
        if rdep:
            deps.append("%s rotation %s: %s" % (pid, fmt(rot), rdep))
        radius = None
        if p.get("radius"):
            rs = parse_spec(p["radius"], "radius", kit, errors, where)
            radius = rs["n"] * unit if rs and rs["n"] else None
            if rs and rs["dep"]:
                deps.append("%s radius %s: %s" % (pid, fmt(rs["n"]), rs["dep"]))
        quarter = p.get("quarter", "ne")
        if kind == "arc" and quarter not in QUARTERS:
            errors.append("%s: quarter %r is not one of ne, se, sw, nw" % (where, quarter)); continue
        fill = p.get("fill", "none" if kind in ("line", "arc", "spiral") else "ink")
        fill = {"ink": ink, "paper": paper}.get(fill, fill)
        if fill != "none" and not re.match(r"^#[0-9A-Fa-f]{6}$", str(fill)):
            errors.append("%s: fill should be ink, paper, none or #rrggbb, got %r" % (where, p.get("fill"))); continue
        cut = p.get("cut")
        if cut is True and not any(not q["cut"] for q in parts):
            errors.append("%s: a cut needs a solid part before it" % where); continue
        if isinstance(cut, str) and cut not in [q["id"] for q in parts]:
            errors.append("%s: cut target %r is not an earlier part id (so far: %s)" % (where, cut, ", ".join(q["id"] for q in parts) or "none")); continue
        if p.get("join") and not any(not q["cut"] for q in parts):
            errors.append("%s: join needs a solid part before it" % where); continue
        parts.append(dict(id=pid, kind=kind, n=spec["n"] * unit, shape=spec.get("kind"), cx=cx, cy=cy, at=name,
                          stroke=stroke_w, fill=fill, cut=cut, join=bool(p.get("join")), angle=angle or 0.0,
                          rotate=rot or 0.0, quarter=quarter, radius=radius, squares=int(spec["n"]) if kind == "spiral" and spec.get("tag") == "squares" else None))
    if errors:
        raise PlanError("\n".join(errors))
    return dict(W=W, H=H, unit=unit, stroke_unit=stroke_unit, parts=parts, deps=deps, ink=ink, paper=paper, kit=kit, sq=sq, pts=pts)


# ---------------------------------------------------------------- svg

def svg_shape(p, b, as_mask=False):
    """One part as an SVG element string. In a mask, shapes are black (hidden)."""
    fill = "#000000" if as_mask else p["fill"]
    stroke = ""
    if p["stroke"] and not (as_mask and p["kind"] in ("circle", "rect") and p["fill"] != "none"):
        stroke = ' stroke="%s" stroke-width="%s" stroke-linecap="round"' % ("#000000" if as_mask else (p["fill"] if p["fill"] != "none" else b["ink"]), fmt(p["stroke"]))
    tr = ' transform="rotate(%s %s %s)"' % (fmt(-p["rotate"]), fmt(p["cx"]), fmt(p["cy"])) if p["rotate"] else ""
    k = p["kind"]
    p = dict(p, id=escape(str(p["id"]), {'"': "&quot;"}))
    if k == "circle":
        return '<circle id="%s" cx="%s" cy="%s" r="%s" fill="%s"%s%s/>' % (p["id"], fmt(p["cx"]), fmt(p["cy"]), fmt(p["n"] / 2), fill, stroke, tr)
    if k == "rect":
        if p["shape"] == "square":
            w = h = p["n"]
        elif p["shape"] == "portrait":
            h = p["n"]; w = h * INV
        else:
            w = p["n"]; h = w * INV
        rx = ' rx="%s"' % fmt(p["radius"]) if p["radius"] else ""
        return '<rect id="%s" x="%s" y="%s" width="%s" height="%s"%s fill="%s"%s%s/>' % (p["id"], fmt(p["cx"] - w / 2), fmt(p["cy"] - h / 2), fmt(w), fmt(h), rx, fill, stroke, tr)
    if k == "line":
        a = math.radians(p["angle"]); L = p["n"] / 2
        x1, y1 = p["cx"] - L * math.cos(a), p["cy"] + L * math.sin(a)
        x2, y2 = p["cx"] + L * math.cos(a), p["cy"] - L * math.sin(a)
        sw = p["stroke"] or b["stroke_unit"]
        return '<line id="%s" x1="%s" y1="%s" x2="%s" y2="%s" stroke="%s" stroke-width="%s" stroke-linecap="round"%s/>' % (
            p["id"], fmt(x1), fmt(y1), fmt(x2), fmt(y2), "#000000" if as_mask else (p["fill"] if p["fill"] != "none" else b["ink"]), fmt(sw), tr)
    if k == "arc":
        r = p["n"] / 2
        a0, a1 = QUARTERS.get(p["quarter"], QUARTERS["ne"])
        x1, y1 = p["cx"] + r * math.cos(math.radians(a0)), p["cy"] + r * math.sin(math.radians(a0))
        x2, y2 = p["cx"] + r * math.cos(math.radians(a1)), p["cy"] + r * math.sin(math.radians(a1))
        sw = p["stroke"] or b["stroke_unit"]
        return '<path id="%s" d="M %s %s A %s %s 0 0 1 %s %s" fill="none" stroke="%s" stroke-width="%s" stroke-linecap="round"%s/>' % (
            p["id"], fmt(x1), fmt(y1), fmt(r), fmt(r), fmt(x2), fmt(y2), "#000000" if as_mask else (p["fill"] if p["fill"] != "none" else b["ink"]), fmt(sw), tr)
    if k == "spiral":
        n = p["squares"] or 6
        if p["squares"]:
            sqs, _ = golden_squares(0, 0, b["W"], b["H"], n)
        else:
            w = p["n"]; h = w * INV
            sqs, _ = golden_squares(p["cx"] - w / 2, p["cy"] - h / 2, w, h, 8)
        sw = p["stroke"] or b["stroke_unit"]
        return '<path id="%s" d="%s" fill="none" stroke="%s" stroke-width="%s" stroke-linecap="round"%s/>' % (
            p["id"], spiral_path(sqs), "#000000" if as_mask else (p["fill"] if p["fill"] != "none" else b["ink"]), fmt(sw), tr)
    return ""


def part_summary(p):
    s = "%s %s at %s" % (p["id"], p["kind"], p["at"])
    if p["cut"]:
        s += " (cut)"
    if p["join"]:
        s += " (joined)"
    if p["rotate"]:
        s += " rotated %s" % fmt(round(p["rotate"], 1))
    return s


def render_svg(plan, b, with_grid=True):
    W, H = b["W"], b["H"]
    pad = max(W, H) * 0.12
    s = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %s %s" width="%s" height="%s">' % (fmt(W + 2 * pad), fmt(H + 2 * pad), fmt(W + 2 * pad), fmt(H + 2 * pad))]
    s.append('<rect width="100%%" height="100%%" fill="%s"/>' % b["paper"])
    s.append('<g transform="translate(%s %s)">' % (fmt(pad), fmt(pad)))
    if with_grid:
        gx, gw = (0, W) if abs(W - H) > 1e-9 else (-(W * PHI - W) / 2, W * PHI)  # a square frame sits in a golden rectangle
        groups, _ = grid_groups(gx, 0, gw, H, 8, {"grid": "#1F2BFF", "spiral": "#E8262B", "ink": b["ink"], "note": "#55555E", "fill": "#1F2BFF"},
                                max(0.5, W * 0.0015), True, True, True, True, False)
        s.append('<g id="golden-grid" opacity="0.55">'); s += groups; s.append('</g>')
    # cuts: group cut parts by their target
    cuts = {}
    solids = [p for p in b["parts"] if not p["cut"]]
    for i, p in enumerate(b["parts"]):
        if p["cut"]:
            target = p["cut"] if isinstance(p["cut"], str) else next((q["id"] for q in reversed(b["parts"][:i]) if not q["cut"]), None)
            if target:
                cuts.setdefault(target, []).append(p)
    # joined parts form one cluster; a cut on any member masks the whole cluster
    clusters = []
    for p in solids:
        if p["join"] and clusters:
            clusters[-1].append(p)
        else:
            clusters.append([p])
    s.append('<defs>')
    for ci, cl in enumerate(clusters):
        cps = [cp for m in cl for cp in cuts.get(m["id"], [])]
        if not cps:
            continue
        s.append('<mask id="cut-%d" maskUnits="userSpaceOnUse" x="%s" y="%s" width="%s" height="%s">' % (ci, fmt(-pad), fmt(-pad), fmt(W + 2 * pad), fmt(H + 2 * pad)))
        s.append('<rect x="%s" y="%s" width="%s" height="%s" fill="#FFFFFF"/>' % (fmt(-pad), fmt(-pad), fmt(W + 2 * pad), fmt(H + 2 * pad)))
        for cp in cps:
            s.append(svg_shape(cp, b, as_mask=True))
        s.append('</mask>')
    s.append('</defs>')
    s.append('<g id="mark">')
    for ci, cl in enumerate(clusters):
        masked = any(m["id"] in cuts for m in cl)
        mask = ' mask="url(#cut-%d)"' % ci if masked else ""
        if len(cl) > 1:
            s.append('<g id="%s"%s>' % (escape("+".join(m["id"] for m in cl), {'"': "&quot;"}), mask))
            for m in cl:
                s.append(svg_shape(m, b))
            s.append('</g>')
        else:
            el = svg_shape(cl[0], b)
            if masked:
                tag = cl[0]["kind"].replace("spiral", "path").replace("arc", "path")
                el = el.replace("<%s " % tag, "<%s%s " % (tag, mask), 1)
            s.append(el)
    s.append('</g>')
    ns = max(7.0, min(W, H) * 0.028)
    s.append('<g id="notes" font-family="ui-monospace, Menlo, Consolas, monospace" font-size="%s" fill="#55555E">' % fmt(ns))
    s.append('<text x="0" y="%s">%s</text>' % (fmt(H + ns * 2.2), escape("%s  |  frame %s x %s  |  unit %s  |  stroke unit %s  |  kit %s" % (
        plan.get("name", "mark"), fmt(round(W, 1)), fmt(round(H, 1)), fmt(b["unit"]), fmt(round(b["stroke_unit"], 2)), " ".join(fmt(k) for k in b["kit"])))))
    s.append('<text x="0" y="%s">%s</text>' % (fmt(H + ns * 3.6), escape("parts: " + ", ".join(part_summary(p) for p in b["parts"]))))
    if b["deps"]:
        s.append('<text x="0" y="%s">%s</text>' % (fmt(H + ns * 5.0), escape("departures: " + "; ".join(b["deps"]))))
    s.append('</g>')
    s.append('</g></svg>')
    return "\n".join(s)


# ---------------------------------------------------------------- jsx

def render_jsx(plan, b, grid_jsx_path):
    """ExtendScript that draws the construction on a 'Construction' layer, with the locked grid on the layer under it."""
    W, H = b["W"], b["H"]
    lines = []
    L = lines.append
    L("// Generated by golden_build.py from plan '%s'. Draws on layer 'Construction'; the grid goes on 'Golden grid'." % plan.get("name", "mark"))
    L("#target illustrator")
    L("var GRID_JSX = %s; // set to the path of golden_grid.jsx, or '' to skip the grid" % json.dumps(grid_jsx_path))
    L("var USE_PATHFINDER = true; // cuts through Pathfinder when it works, paper-filled shapes otherwise")
    L("var PHI = %r, INV = %r, KAPPA = 0.5522847498;" % (PHI, INV))
    L("app.userInteractionLevel = UserInteractionLevel.DONTDISPLAYALERTS;")
    L("var doc = app.documents.length ? app.activeDocument : app.documents.add(DocumentColorSpace.RGB, %s, %s);" % (fmt(W * 1.6), fmt(H * 1.6)))
    L("app.coordinateSystem = CoordinateSystem.DOCUMENTCOORDINATESYSTEM;")
    L("var ab = doc.artboards[doc.artboards.getActiveArtboardIndex()].artboardRect;")
    L("var W = %s, H = %s; var left = ab[0] + (ab[2] - ab[0]) / 2 - W / 2, top = ab[1] - (ab[1] - ab[3]) / 2 + H / 2;" % (fmt(W), fmt(H)))
    L("function X(x) { return left + x; } function Y(y) { return top - y; }")
    L("function rgb(hex) { var c = new RGBColor(); c.red = parseInt(hex.substr(1, 2), 16); c.green = parseInt(hex.substr(3, 2), 16); c.blue = parseInt(hex.substr(5, 2), 16); return c; }")
    L("var INK = rgb(%s), PAPER = rgb(%s);" % (json.dumps(b["ink"]), json.dumps(b["paper"])))
    L("function paint(item, fill, strokeW) { if (fill) { item.filled = true; item.fillColor = fill; } else { item.filled = false; }")
    L("  if (strokeW) { item.stroked = true; item.strokeWidth = strokeW; item.strokeColor = fill || INK; item.strokeCap = StrokeCap.ROUNDENDCAP; } else { item.stroked = false; } }")
    L("var layer = null; for (var i = 0; i < doc.layers.length; i++) { if (doc.layers[i].name === 'Construction') { layer = doc.layers[i]; } }")
    L("if (!layer) { layer = doc.layers.add(); layer.name = 'Construction'; }")
    L("layer.locked = false; doc.activeLayer = layer;")
    L("var rootName = %s;" % json.dumps(plan.get("name", "mark")))
    L("var root = layer.groupItems.add(); root.name = rootName;")
    L("// Pathfinder and expand can replace the group object; fetch it again by name before adding to it")
    L("function refreshRoot() { for (var ri = 0; ri < layer.groupItems.length; ri++) { if (layer.groupItems[ri].name === rootName) { root = layer.groupItems[ri]; return; } } }")
    L("var items = {};")
    for p in b["parts"]:
        pid = json.dumps(p["id"])
        fill = "null" if p["fill"] == "none" else ("INK" if p["fill"] == b["ink"] else ("PAPER" if p["fill"] == b["paper"] else "rgb(%s)" % json.dumps(p["fill"])))
        sw = fmt(p["stroke"]) if p["stroke"] else "0"
        k = p["kind"]
        if k == "circle":
            r = p["n"] / 2
            L("items[%s] = root.pathItems.ellipse(Y(%s), X(%s), %s, %s); paint(items[%s], %s, %s);" % (pid, fmt(p["cy"] - r), fmt(p["cx"] - r), fmt(p["n"]), fmt(p["n"]), pid, fill, sw))
        elif k == "rect":
            if p["shape"] == "square":
                w = h = p["n"]
            elif p["shape"] == "portrait":
                h = p["n"]; w = h * INV
            else:
                w = p["n"]; h = w * INV
            if p["radius"]:
                L("items[%s] = root.pathItems.roundedRectangle(Y(%s), X(%s), %s, %s, %s, %s); paint(items[%s], %s, %s);" % (pid, fmt(p["cy"] - h / 2), fmt(p["cx"] - w / 2), fmt(w), fmt(h), fmt(p["radius"]), fmt(p["radius"]), pid, fill, sw))
            else:
                L("items[%s] = root.pathItems.rectangle(Y(%s), X(%s), %s, %s); paint(items[%s], %s, %s);" % (pid, fmt(p["cy"] - h / 2), fmt(p["cx"] - w / 2), fmt(w), fmt(h), pid, fill, sw))
        elif k == "line":
            a = math.radians(p["angle"]); Ln = p["n"] / 2
            x1, y1 = p["cx"] - Ln * math.cos(a), p["cy"] + Ln * math.sin(a)
            x2, y2 = p["cx"] + Ln * math.cos(a), p["cy"] - Ln * math.sin(a)
            L("items[%s] = root.pathItems.add(); items[%s].setEntirePath([[X(%s), Y(%s)], [X(%s), Y(%s)]]); paint(items[%s], null, %s); items[%s].strokeColor = %s;" % (
                pid, pid, fmt(x1), fmt(y1), fmt(x2), fmt(y2), pid, fmt(p["stroke"] or b["stroke_unit"]), pid, fill if fill != "null" else "INK"))
        elif k in ("arc", "spiral"):
            if k == "arc":
                r = p["n"] / 2
                a0, a1 = QUARTERS.get(p["quarter"], QUARTERS["ne"])
                p0 = (p["cx"] + r * math.cos(math.radians(a0)), p["cy"] + r * math.sin(math.radians(a0)))
                p3 = (p["cx"] + r * math.cos(math.radians(a1)), p["cy"] + r * math.sin(math.radians(a1)))
                u0 = ((p0[0] - p["cx"]) / r, (p0[1] - p["cy"]) / r); u3 = ((p3[0] - p["cx"]) / r, (p3[1] - p["cy"]) / r)
                kk = 0.5522847498 * r
                bz = [dict(p0=p0, p1=(p0[0] + kk * u3[0], p0[1] + kk * u3[1]), p2=(p3[0] + kk * u0[0], p3[1] + kk * u0[1]), p3=p3)]
            else:
                n = p["squares"] or 6
                if p["squares"]:
                    sqs, _ = golden_squares(0, 0, W, H, n)
                else:
                    w = p["n"]; h = w * INV
                    sqs, _ = golden_squares(p["cx"] - w / 2, p["cy"] - h / 2, w, h, 8)
                bz = []
                for sq in sqs:
                    q0, q1, q2, q3 = arc_beziers(sq)
                    bz.append(dict(p0=q0, p1=q1, p2=q2, p3=q3))
            anchors = [bz[0]["p0"]] + [z["p3"] for z in bz]
            L("items[%s] = root.pathItems.add(); items[%s].setEntirePath([%s]);" % (pid, pid, ", ".join("[X(%s), Y(%s)]" % (fmt(x), fmt(y)) for x, y in anchors)))
            for j in range(len(anchors)):
                ld = bz[j - 1]["p2"] if j > 0 else anchors[j]
                rd = bz[j]["p1"] if j < len(bz) else anchors[j]
                L("items[%s].pathPoints[%d].leftDirection = [X(%s), Y(%s)]; items[%s].pathPoints[%d].rightDirection = [X(%s), Y(%s)]; items[%s].pathPoints[%d].pointType = %s;" % (
                    pid, j, fmt(ld[0]), fmt(ld[1]), pid, j, fmt(rd[0]), fmt(rd[1]), pid, j, "PointType.CORNER" if j in (0, len(anchors) - 1) else "PointType.SMOOTH"))
            L("paint(items[%s], null, %s); items[%s].strokeColor = %s;" % (pid, fmt(p["stroke"] or b["stroke_unit"]), pid, fill if fill != "null" else "INK"))
        L("items[%s].name = %s;" % (pid, pid))
        if p["rotate"]:
            L("items[%s].rotate(%s);" % (pid, fmt(p["rotate"])))
    # joins: unite the pair with Pathfinder Add so a later cut goes through both; a group if that fails
    for i, p in enumerate(b["parts"]):
        if p["join"]:
            prev = next((q["id"] for q in reversed(b["parts"][:i]) if not q["cut"]), None)
            if prev:
                a, c = json.dumps(prev), json.dumps(p["id"])
                L("try { doc.selection = null; items[%s].selected = true; items[%s].selected = true; app.executeMenuCommand('group');" % (a, c))
                L("  if (USE_PATHFINDER) { app.executeMenuCommand('Live Pathfinder Add'); app.executeMenuCommand('expandStyle'); }")
                L("  items[%s] = doc.selection[0]; items[%s] = items[%s]; items[%s].name = %s; } catch (e) { } refreshRoot();" % (a, c, a, a, json.dumps(prev + " + " + p["id"])))
    # cuts
    for i, p in enumerate(b["parts"]):
        if p["cut"]:
            target = p["cut"] if isinstance(p["cut"], str) else next((q["id"] for q in reversed(b["parts"][:i]) if not q["cut"]), None)
            if not target:
                continue
            L("try { if (USE_PATHFINDER) {")
            L("  var cutter = items[%s]; if (cutter.stroked && !cutter.filled) { doc.selection = null; cutter.selected = true; app.executeMenuCommand('OffsetPath v22'); cutter = doc.selection[0]; items[%s] = cutter; }" % (json.dumps(p["id"]), json.dumps(p["id"])))
            L("  doc.selection = null; items[%s].selected = true; cutter.selected = true; cutter.zOrder(ZOrderMethod.BRINGTOFRONT);" % json.dumps(target))
            L("  // a live Pathfinder effect applies to each selected object on its own; grouping the pair first makes it subtract the front from the back")
            L("  app.executeMenuCommand('group'); app.executeMenuCommand('Live Pathfinder Subtract'); app.executeMenuCommand('expandStyle');")
            L("  items[%s] = doc.selection[0]; items[%s].name = %s + ' minus ' + %s; }" % (json.dumps(target), json.dumps(target), json.dumps(target), json.dumps(p["id"])))
            L("  else { paint(items[%s], PAPER, 0); items[%s].name = %s + ' (cut, paper)'; } } catch (e) { paint(items[%s], PAPER, 0); items[%s].name = %s + ' (cut, paper; Pathfinder failed: ' + e.message + ')'; } refreshRoot();" % (
                json.dumps(p["id"]), json.dumps(p["id"]), json.dumps(p["id"]), json.dumps(p["id"]), json.dumps(p["id"]), json.dumps(p["id"])))
    L("refreshRoot(); var t = root.textFrames.add(); t.name = 'Notes'; t.contents = %s; t.textRange.characterAttributes.size = %s; t.position = [left, top - H - %s * 3.4];" % (
        json.dumps("%s | frame %s x %s | unit %s | stroke unit %s | parts: %s%s" % (plan.get("name", "mark"), fmt(round(W, 1)), fmt(round(H, 1)), fmt(b["unit"]), fmt(round(b["stroke_unit"], 2)),
                   ", ".join(part_summary(p) for p in b["parts"]),
                   (" | departures: " + "; ".join(b["deps"])) if b["deps"] else "")), fmt(max(6, min(W, H) * 0.028)), fmt(max(6, min(W, H) * 0.028) * 0.8)))
    L("doc.selection = null;")
    L("var gridNote = '';")
    L("if (GRID_JSX) {")
    L("  var gf = new File(GRID_JSX);")
    L("  if (!gf.exists) { gf = new File(File($.fileName).parent + '/golden_grid.jsx'); }")
    L("  if (!gf.exists) { gf = new File(File($.fileName).parent + '/../../scripts/golden_grid.jsx'); }")
    L("  if (!gf.exists) { gridNote = ' (grid skipped: golden_grid.jsx not found at ' + GRID_JSX + ')'; }")
    L("  else { try { var GOLDEN_CONFIG = { bounds: [left, top, left + W, top - H], squares: 8, lock: true }; $.evalFile(gf);")
    L("    for (var gi = 0; gi < doc.layers.length; gi++) { if (doc.layers[gi].name === 'Golden grid') { var gl = doc.layers[gi]; var wasLocked = gl.locked; gl.locked = false; gl.zOrder(ZOrderMethod.SENDTOBACK); gl.locked = wasLocked; } }")
    L("    doc.activeLayer = layer; } catch (e) { gridNote = ' (grid failed: ' + e.message + ')'; } }")
    L("}")
    L("'Construction: %s, %d parts, %s x %s' + gridNote;" % (plan.get("name", "mark"), len(b["parts"]), fmt(round(W)), fmt(round(H))))
    return "\n".join(lines)


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("plan", nargs="?", help="plan JSON file")
    p.add_argument("--contract", default=DEFAULT_CONTRACT)
    p.add_argument("--out", help="SVG path")
    p.add_argument("--jsx", help="Illustrator script path")
    p.add_argument("--no-grid", action="store_true")
    p.add_argument("--grammar", action="store_true", help="print the vocabulary")
    p.add_argument("--example", choices=sorted(EXAMPLES), help="print an example plan")
    a = p.parse_args()
    if a.grammar:
        print(GRAMMAR.strip()); return
    if a.example:
        print(json.dumps(EXAMPLES[a.example], indent=2)); return
    if not a.plan:
        p.error("give a plan file, --grammar or --example")
    try:
        plan = json.load(open(a.plan))
        contract = json.load(open(a.contract))
    except (OSError, ValueError) as e:
        sys.exit("cannot read: %s" % e)
    try:
        b = build(plan, contract)
    except PlanError as e:
        print("plan refused:\n" + str(e))
        sys.exit(1)
    svg = render_svg(plan, b, not a.no_grid)
    if a.out:
        open(a.out, "w", encoding="utf-8").write(svg); print("wrote " + a.out)
    else:
        sys.stdout.write(svg + "\n")
    if a.jsx:
        open(a.jsx, "w", encoding="utf-8").write(render_jsx(plan, b, os.path.join(HERE, "golden_grid.jsx"))); print("wrote " + a.jsx)
    print("%s: frame %s x %s, unit %s, %d parts, eye at (%s, %s)%s" % (plan.get("name", "mark"), fmt(round(b["W"], 1)), fmt(round(b["H"], 1)), fmt(b["unit"]), len(b["parts"]),
          fmt(round(b["pts"]["eye"][0], 1)), fmt(round(b["pts"]["eye"][1], 1)), ("; departures: " + "; ".join(b["deps"])) if b["deps"] else ""))


if __name__ == "__main__":
    main()
