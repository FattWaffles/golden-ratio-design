#!/usr/bin/env python3
"""golden_grid.py: golden ratio grids, spirals, circles and tables, as SVG or text.

Every drawing is a template: named groups, hairline strokes, values written as notes,
so a designer can open the SVG in Illustrator or Figma and edit on top of it.

  python3 -I golden_grid.py grid   --width 1000 --out grid.svg
  python3 -I golden_grid.py page   --width 1440 --height 900 --margin 34 --out page.svg
  python3 -I golden_grid.py hero   --theme light --out hero-light.svg
  python3 -I golden_grid.py scale  --base 16 --format css
  python3 -I golden_grid.py shares --total 100 --parts 3
  python3 -I golden_grid.py sequence --unit 8 --count 8
"""
import argparse
import json
import math
import sys

PHI = (1 + math.sqrt(5)) / 2          # 1.6180339887...
INV = 1 / PHI                         # 0.6180339887...
KAPPA = 0.5522847498                  # cubic handle length for a quarter circle, as a fraction of r
FIB = [1, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144, 233, 377, 610, 987, 1597]
PHI_DIGITS = "1618033988749894848204586834365638117720309179805762862135"
GOLDEN_ANGLE = 360 / (PHI * PHI)      # 137.5077...

COLOURS = {"grid": "#1F2BFF", "spiral": "#E8262B", "ink": "#0E0E14", "note": "#55555E", "fill": "#1F2BFF"}


def fmt(v):
    """Compact number for SVG attributes."""
    return ("%.3f" % v).rstrip("0").rstrip(".") if abs(v) >= 1e-9 else "0"


# ---------------------------------------------------------------- geometry

def golden_squares(x, y, w, h, n):
    """Squares spiralling inward from a rectangle.

    Returns ([(x, y, side, direction)], remaining_rect). direction says where the square
    sits in the rectangle that was left: 0 left, 1 top, 2 right, 3 bottom. The cycle
    left, top, right, bottom keeps the spiral turning one way."""
    out = []
    start = 0 if w >= h else 1
    for i in range(n):
        d = (i + start) % 4
        s = min(w, h)
        if s < 0.5:
            break
        if (d in (0, 2)) != (w >= h):
            break  # the rectangle is not golden; stop before the tiling and the spiral go wrong
        if d == 0:
            out.append((x, y, s, d)); x += s; w -= s
        elif d == 1:
            out.append((x, y, s, d)); y += s; h -= s
        elif d == 2:
            out.append((x + w - s, y, s, d)); w -= s
        else:
            out.append((x, y + h - s, s, d)); h -= s
    return out, (x, y, w, h)


def eye_point(x, y, w, h):
    """The point the spiral winds into: the centre of what is left after many squares."""
    _, (rx, ry, rw, rh) = golden_squares(x, y, w, h, 60)
    return rx + rw / 2, ry + rh / 2


def arc_in_square(sq):
    """Quarter arc of the spiral inside one square: (outer end, inner end, centre)."""
    x, y, s, d = sq
    if d == 0:
        return (x, y + s), (x + s, y), (x + s, y + s)
    if d == 1:
        return (x, y), (x + s, y + s), (x, y + s)
    if d == 2:
        return (x + s, y), (x, y + s), (x, y)
    return (x + s, y + s), (x, y), (x + s, y)


def arc_beziers(sq):
    """Cubic bezier (p0, p1, p2, p3) for the quarter arc in a square."""
    p0, p3, c = arc_in_square(sq)
    r = sq[2]
    u0 = ((p0[0] - c[0]) / r, (p0[1] - c[1]) / r)
    u3 = ((p3[0] - c[0]) / r, (p3[1] - c[1]) / r)
    k = KAPPA * r
    p1 = (p0[0] + k * u3[0], p0[1] + k * u3[1])
    p2 = (p3[0] + k * u0[0], p3[1] + k * u0[1])
    return p0, p1, p2, p3


def spiral_path(squares):
    """SVG path data for the spiral through the squares, outer end first."""
    parts = []
    for i, sq in enumerate(squares):
        p0, p1, p2, p3 = arc_beziers(sq)
        if i == 0:
            parts.append("M %s %s" % (fmt(p0[0]), fmt(p0[1])))
        parts.append("C %s %s %s %s %s %s" % tuple(fmt(v) for p in (p1, p2, p3) for v in p))
    return " ".join(parts)


def golden_rect(width=None, height=None, orient="auto"):
    """Width and height of a golden rectangle from whichever side is given."""
    if width and height:
        return float(width), float(height)
    if width:
        w = float(width)
        return (w, w * PHI) if orient == "portrait" else (w, w * INV)
    h = float(height)
    return (h * INV, h) if orient == "portrait" else (h * PHI, h)


# ---------------------------------------------------------------- svg pieces

def svg_open(w, h, bg=None, pad=0):
    s = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %s %s" width="%s" height="%s">'
         % (fmt(w + 2 * pad), fmt(h + 2 * pad), fmt(w + 2 * pad), fmt(h + 2 * pad))]
    if bg:
        s.append('<rect width="100%%" height="100%%" fill="%s"/>' % bg)
    return s


def text(x, y, chars, size, colour, anchor="start", family="ui-monospace, Menlo, Consolas, monospace", extra=""):
    return ('<text x="%s" y="%s" font-family="%s" font-size="%s" fill="%s" text-anchor="%s"%s>%s</text>'
            % (fmt(x), fmt(y), family, fmt(size), colour, anchor, (" " + extra) if extra else "", chars))


def grid_groups(x, y, w, h, n, c, stroke=1.0, spiral=True, circles=True, phi_lines=True, eye=True,
                notes=True, squares_on=True, note_size=None):
    """The construction as named SVG groups, so each part is its own layer when imported."""
    sq, _ = golden_squares(x, y, w, h, n)
    g = []
    g.append('<g id="golden-rectangle"><rect x="%s" y="%s" width="%s" height="%s" fill="none" stroke="%s" stroke-width="%s"/></g>'
             % (fmt(x), fmt(y), fmt(w), fmt(h), c["grid"], fmt(stroke)))
    if squares_on:
        g.append('<g id="squares" fill="none" stroke="%s" stroke-width="%s">' % (c["grid"], fmt(stroke * 0.5)))
        for i, (sx, sy, s, d) in enumerate(sq):
            g.append('<rect id="square-%d" x="%s" y="%s" width="%s" height="%s"/>' % (i + 1, fmt(sx), fmt(sy), fmt(s), fmt(s)))
        g.append('</g>')
    if circles:
        g.append('<g id="circles" fill="none" stroke="%s" stroke-width="%s" stroke-dasharray="%s %s">'
                 % (c["grid"], fmt(stroke * 0.5), fmt(stroke * 2), fmt(stroke * 2)))
        for i, (sx, sy, s, d) in enumerate(sq):
            g.append('<circle id="circle-%d" cx="%s" cy="%s" r="%s"/>' % (i + 1, fmt(sx + s / 2), fmt(sy + s / 2), fmt(s / 2)))
        g.append('</g>')
    if phi_lines:
        g.append('<g id="phi-lines" stroke="%s" stroke-width="%s" stroke-dasharray="%s %s">'
                 % (c["grid"], fmt(stroke * 0.5), fmt(stroke * 6), fmt(stroke * 4)))
        for f in (INV * INV, INV):
            g.append('<line x1="%s" y1="%s" x2="%s" y2="%s"/>' % (fmt(x + w * f), fmt(y), fmt(x + w * f), fmt(y + h)))
            g.append('<line x1="%s" y1="%s" x2="%s" y2="%s"/>' % (fmt(x), fmt(y + h * f), fmt(x + w), fmt(y + h * f)))
        g.append('</g>')
    if spiral:
        g.append('<g id="spiral"><path d="%s" fill="none" stroke="%s" stroke-width="%s" stroke-linecap="round"/></g>'
                 % (spiral_path(sq), c["spiral"], fmt(stroke * 1.5)))
    if eye:
        ex, ey = eye_point(x, y, w, h)
        r = max(w, h) * 0.012
        g.append('<g id="eye" stroke="%s" stroke-width="%s" fill="none">' % (c["spiral"], fmt(stroke)))
        g.append('<circle cx="%s" cy="%s" r="%s"/>' % (fmt(ex), fmt(ey), fmt(r)))
        g.append('<line x1="%s" y1="%s" x2="%s" y2="%s"/>' % (fmt(ex - r * 2), fmt(ey), fmt(ex + r * 2), fmt(ey)))
        g.append('<line x1="%s" y1="%s" x2="%s" y2="%s"/>' % (fmt(ex), fmt(ey - r * 2), fmt(ex), fmt(ey + r * 2)))
        g.append('</g>')
    if notes:
        ns = note_size or max(8.0, min(w, h) * 0.018)
        ex, ey = eye_point(x, y, w, h)
        line1 = "phi 1.618  |  W %s  H %s  |  W/H %s" % (fmt(round(w, 1)), fmt(round(h, 1)), fmt(round(w / h, 3)))
        line2 = "0.618 : 0.382 lines  |  eye at (%s, %s) of W, H  |  %d squares, inscribed circles" % (
            fmt(round((ex - x) / w, 3)), fmt(round((ey - y) / h, 3)), len(sq))
        g.append('<g id="notes">')
        g.append(text(x, y + h + ns * 1.6, line1, ns, c["note"]))
        g.append(text(x, y + h + ns * 3.0, line2, ns, c["note"]))
        g.append('</g>')
    return g, sq


# ---------------------------------------------------------------- commands

def cmd_grid(a):
    if not a.width and not a.height:
        sys.exit("grid: give --width or --height (one side makes an exact golden rectangle)")
    c = colours_from(a.colours)
    w, h = golden_rect(a.width, a.height, a.orient)
    ratio = w / h if w >= h else h / w
    off = abs(ratio - PHI) / PHI * 100
    if a.width and a.height and off > 0.5:
        print("note: %s x %s is %.1f%% off phi, so the squares stop where the tiling stops being exact; "
              "give one side only for an exact golden rectangle" % (fmt(w), fmt(h), off))
    pad = max(w, h) * 0.06 if a.pad is None else a.pad
    s = svg_open(w, h, a.background, pad)
    if a.mirror:
        inner = ['<g id="golden-grid" transform="translate(%s %s) scale(-1 1)">' % (fmt(pad + w), fmt(pad))]
    else:
        inner = ['<g id="golden-grid" transform="translate(%s %s)">' % (fmt(pad), fmt(pad))]
    groups, sq = grid_groups(0, 0, w, h, a.squares, c, a.stroke, not a.no_spiral, not a.no_circles,
                             not a.no_phi_lines, not a.no_eye, False)
    s += inner + groups + ['</g>']
    ex, ey = eye_point(0, 0, w, h)
    if a.mirror:
        ex = w - ex
    if not a.no_notes:
        ns = max(8.0, min(w, h) * 0.018)
        s.append('<g id="notes" transform="translate(%s %s)">' % (fmt(pad), fmt(pad)))
        s.append(text(0, h + ns * 1.6, "phi 1.618  |  W %s  H %s  |  W/H %s%s" % (
            fmt(round(w, 1)), fmt(round(h, 1)), fmt(round(w / h, 3)), "  |  mirrored" if a.mirror else ""), ns, c["note"]))
        s.append(text(0, h + ns * 3.0, "0.618 : 0.382 lines  |  eye at (%s, %s) of W, H  |  %d squares, inscribed circles" % (
            fmt(round(ex / w, 3)), fmt(round(ey / h, 3)), len(sq)), ns, c["note"]))
        s.append('</g>')
    s.append('</svg>')
    write(a.out, "\n".join(s))
    print("golden rectangle %s x %s (long/short %.4f, phi %.4f, off by %.2f%%), %d squares, eye at (%s, %s)"
          % (fmt(round(w, 2)), fmt(round(h, 2)), ratio, PHI, off, len(sq), fmt(round(ex, 1)), fmt(round(ey, 1))))


def cmd_page(a):
    c = colours_from(a.colours)
    W, H, m, g = float(a.width), float(a.height), float(a.margin), float(a.gutter)
    if W <= 0 or H <= 0 or 2 * m + g >= W or 2 * m >= H:
        sys.exit("page: margins and gutter must leave room inside %s x %s" % (fmt(W), fmt(H)))
    ns = max(8.0, min(W, H) * 0.014)
    band = ns * 3.6  # notes sit under the page, outside it, so the hero keeps the full inner height
    s = svg_open(W, H + band, a.background)
    s.append('<g id="page"><rect x="0" y="0" width="%s" height="%s" fill="none" stroke="%s" stroke-width="%s"/></g>'
             % (fmt(W), fmt(H), c["ink"], fmt(a.stroke)))
    s.append('<g id="margins"><rect x="%s" y="%s" width="%s" height="%s" fill="none" stroke="%s" stroke-width="%s" stroke-dasharray="2 3"/></g>'
             % (fmt(m), fmt(m), fmt(W - 2 * m), fmt(H - 2 * m), c["note"], fmt(a.stroke * 0.5)))
    # phi lines across the whole page: the four crossings are the strongest places for a focal point
    s.append('<g id="phi-lines" stroke="%s" stroke-width="%s" stroke-dasharray="8 6">' % (c["grid"], fmt(a.stroke * 0.5)))
    for f in (INV * INV, INV):
        s.append('<line x1="%s" y1="0" x2="%s" y2="%s"/>' % (fmt(W * f), fmt(W * f), fmt(H)))
        s.append('<line x1="0" y1="%s" x2="%s" y2="%s"/>' % (fmt(H * f), fmt(W), fmt(H * f)))
    s.append('</g>')
    s.append('<g id="phi-points" fill="%s">' % c["spiral"])
    for fx in (INV * INV, INV):
        for fy in (INV * INV, INV):
            s.append('<circle cx="%s" cy="%s" r="%s"/>' % (fmt(W * fx), fmt(H * fy), fmt(max(W, H) * 0.004)))
    s.append('</g>')
    # golden columns inside the margins: content 0.618, side 0.382, gutter taken from the middle
    iw = W - 2 * m
    content = iw * INV - g / 2
    side = iw - content - g
    s.append('<g id="columns" fill="%s" fill-opacity="0.08" stroke="%s" stroke-width="%s">' % (c["fill"], c["grid"], fmt(a.stroke * 0.5)))
    s.append('<rect id="content-column" x="%s" y="%s" width="%s" height="%s"/>' % (fmt(m), fmt(m), fmt(content), fmt(H - 2 * m)))
    s.append('<rect id="side-column" x="%s" y="%s" width="%s" height="%s"/>' % (fmt(m + content + g), fmt(m), fmt(side), fmt(H - 2 * m)))
    s.append('</g>')
    # the golden rectangle at the top of the content area: the hero or first screen
    orient = "portrait" if H > W else "landscape"
    gw, gh = golden_rect(iw, None, orient)
    if gh > H - 2 * m:
        gw, gh = golden_rect(None, H - 2 * m, orient)
    s.append('<g id="golden-rectangle-hero" transform="translate(%s %s)">' % (fmt(m), fmt(m)))
    groups, sq = grid_groups(0, 0, gw, gh, a.squares, c, a.stroke, True, False, False, True, False)
    s += groups
    s.append('</g>')
    # sequence spacing ruler along the bottom
    s.append('<g id="spacing-ruler" stroke="%s" stroke-width="%s">' % (c["note"], fmt(a.stroke * 0.5)))
    x = m
    ls = max(7.0, m * 0.25)
    for v in [8, 13, 21, 34, 55, 89]:
        s.append('<line x1="%s" y1="%s" x2="%s" y2="%s"/>' % (fmt(x), fmt(H - m * 0.55), fmt(x), fmt(H - m * 0.25)))
        if v >= 2 * ls:
            s.append(text(x + v / 2, H - m * 0.3, str(v), ls, c["note"], "middle"))
        x += v
    s.append('<line x1="%s" y1="%s" x2="%s" y2="%s"/>' % (fmt(x), fmt(H - m * 0.55), fmt(x), fmt(H - m * 0.25)))
    s.append('</g>')
    ex, ey = eye_point(0, 0, gw, gh)
    s.append('<g id="notes">')
    s.append(text(m, H + ns * 1.4, "page %s x %s  |  margin %s  gutter %s  |  content %s  side %s (0.618 : 0.382)"
                  % (fmt(W), fmt(H), fmt(m), fmt(g), fmt(round(content, 1)), fmt(round(side, 1))), ns, c["note"]))
    s.append(text(m, H + ns * 2.8, "hero rectangle %s x %s  |  eye at (%s, %s)  |  phi lines at 0.382 and 0.618 of page"
                  % (fmt(round(gw, 1)), fmt(round(gh, 1)), fmt(round(m + ex, 1)), fmt(round(m + ey, 1))), ns, c["note"]))
    s.append('</g>')
    s.append('</svg>')
    write(a.out, "\n".join(s))
    print("page %s x %s: content %s, side %s, hero %s x %s, phi lines at x %s %s and y %s %s"
          % (fmt(W), fmt(H), fmt(round(content, 1)), fmt(round(side, 1)), fmt(round(gw, 1)), fmt(round(gh, 1)),
             fmt(round(W * INV * INV, 1)), fmt(round(W * INV, 1)), fmt(round(H * INV * INV, 1)), fmt(round(H * INV, 1))))


def cmd_hero(a):
    """README hero: the digits of phi, one per square, with the spiral through them."""
    dark = a.theme == "dark"
    ink = "#F2F2EF" if dark else "#0E0E14"
    grid = "#7C84FF" if dark else "#1F2BFF"
    spiral = "#FF6B6B" if dark else "#E8262B"
    note = "#A0A0A8" if dark else "#55555E"
    W = float(a.width)
    H = W * INV
    pad = W * 0.045
    s = svg_open(W, H, a.background, pad)
    s.append('<g transform="translate(%s %s)">' % (fmt(pad), fmt(pad)))
    sq, _ = golden_squares(0, 0, W, H, min(a.squares, len(PHI_DIGITS)))
    s.append('<g id="squares" fill="none" stroke="%s" stroke-width="1.25" stroke-opacity="0.9">' % grid)
    s.append('<rect x="0" y="0" width="%s" height="%s" stroke-width="2"/>' % (fmt(W), fmt(H)))
    for i, (sx, sy, side, d) in enumerate(sq):
        s.append('<rect x="%s" y="%s" width="%s" height="%s"/>' % (fmt(sx), fmt(sy), fmt(side), fmt(side)))
    s.append('</g>')
    s.append('<g id="digits" fill="%s" font-family="Georgia, \'Times New Roman\', Times, serif">' % ink)
    for i, (sx, sy, side, d) in enumerate(sq):
        if i >= len(PHI_DIGITS):
            break
        fs = side * 0.74
        if fs < 4:
            break
        cx, cy = sx + side / 2, sy + side / 2
        s.append('<text x="%s" y="%s" font-size="%s" text-anchor="middle">%s</text>'
                 % (fmt(cx), fmt(cy + fs * 0.34), fmt(fs), PHI_DIGITS[i]))
        if i == 0:
            s.append('<text x="%s" y="%s" font-size="%s" text-anchor="middle">.</text>'
                     % (fmt(cx + fs * 0.36), fmt(cy + fs * 0.34), fmt(fs)))
    s.append('</g>')
    s.append('<g id="spiral"><path d="%s" fill="none" stroke="%s" stroke-width="%s" stroke-linecap="round"/></g>'
             % (spiral_path(sq), spiral, fmt(W * 0.0035)))
    ex, ey = eye_point(0, 0, W, H)
    s.append('<circle cx="%s" cy="%s" r="%s" fill="%s"/>' % (fmt(ex), fmt(ey), fmt(W * 0.004), spiral))
    ls = W * 0.013
    s.append('<g id="labels" fill="%s">' % note)
    s.append(text(W / 2, -ls * 0.9, "phi", ls, note, "middle", family="Georgia, 'Times New Roman', serif", extra='font-style="italic"'))
    s.append(text(-ls * 0.9, H / 2, "1", ls, note, "middle", family="Georgia, 'Times New Roman', serif",
                  extra='transform="rotate(-90 %s %s)"' % (fmt(-ls * 0.9), fmt(H / 2))))
    s.append(text(0, H + ls * 2.0, a.title, ls, note))
    s.append(text(W, H + ls * 2.0, "phi = 1.618 033 988 749 894 848 204 586 834 365 638...", ls, note, "end"))
    s.append('</g>')
    s.append('</g>')
    s.append('</svg>')
    write(a.out, "\n".join(s))
    print("hero %s: %s x %s plus %s padding, %d digits" % (a.theme, fmt(round(W)), fmt(round(H)), fmt(round(pad)), len(sq)))


ROLES = {-3: "nano", -2: "micro", -1: "small", 0: "body", 1: "lead", 2: "heading 3", 3: "heading 2",
         4: "heading 1", 5: "display", 6: "hero", 7: "hero wide"}


def scale_rows(base, ratio, up, down):
    rows = []
    for n in range(-down, up + 1):
        size = base * ratio ** n
        rows.append({
            "step": n,
            "px": round(size, 2),
            "rem": round(size / 16, 3),
            "line_phi": round(size * PHI, 1),
            "line_root_phi": round(size * math.sqrt(PHI), 1),
            "line_one": round(size, 1),
            "role": ROLES.get(n, ""),
        })
    return rows


def cmd_scale(a):
    ratio = ratio_from(a.ratio)
    if a.base <= 0:
        sys.exit("--base must be above 0")
    rows = scale_rows(float(a.base), ratio, a.up, a.down)
    spacing = sequence_from(float(a.base) / 2, 8)
    if a.format == "json":
        print(json.dumps({"base": a.base, "ratio": ratio, "steps": rows, "spacing": spacing}, indent=2))
        return
    if a.format == "css":
        print(":root {")
        print("  /* type scale, base %spx, ratio %s */" % (a.base, round(ratio, 3)))
        for r in rows:
            print("  --step-%s: %srem; /* %spx, %s */" % (str(r["step"]).replace("-", "n"), r["rem"], r["px"], r["role"]))
        print("  --leading-body: %s; --leading-sub: %s; --leading-display: 1;" % (round(PHI, 3), round(math.sqrt(PHI), 3)))
        print("  /* spacing from the sequence */")
        for i, v in enumerate(spacing):
            print("  --space-%d: %spx;" % (i + 1, fmt(v)))
        print("}")
        return
    print("| step | px | rem | line x1.618 | line x1.272 | line x1 | role |")
    print("|---:|---:|---:|---:|---:|---:|:---|")
    for r in rows:
        print("| %d | %s | %s | %s | %s | %s | %s |" % (r["step"], r["px"], r["rem"], r["line_phi"], r["line_root_phi"], r["line_one"], r["role"]))
    print("\nspacing: " + "  ".join(fmt(v) for v in spacing))


def sequence_from(unit, count):
    """A spacing sequence from a unit: the Fibonacci run that starts at the unit when it is in the
    sequence, otherwise an additive run (each term the sum of the two before) from the unit and
    the unit times phi rounded, so the ratios close in on phi and the terms add up."""
    unit = float(unit)
    if unit <= 0 or count < 1:
        sys.exit("sequence: unit must be above 0 and count at least 1")
    if unit in FIB:
        i = FIB.index(unit)
        run = FIB[i:i + count]
        if len(run) == count:
            return run
    a = int(unit) if unit == int(unit) else unit
    b = round(unit * PHI)
    out = [a, b]
    while len(out) < count:
        a, b = b, a + b
        out.append(b)
    return out[:count]


def cmd_sequence(a):
    print("  ".join(fmt(v) for v in sequence_from(a.unit, a.count)))


def shares(total, parts):
    """Split a total at the golden section, then split the remainder again for each extra part."""
    out, rest = [], float(total)
    for i in range(parts - 1):
        take = rest * INV
        out.append(take)
        rest -= take
    out.append(rest)
    return out


def cmd_shares(a):
    if a.total <= 0 or a.parts < 1:
        sys.exit("shares: total must be above 0 and parts at least 1")
    vals = shares(a.total, a.parts)
    names = ["dominant", "secondary", "accent", "fourth", "fifth", "sixth"]
    for i, v in enumerate(vals):
        print("%-10s %s  (%s%%)" % (names[i] if i < len(names) else "part %d" % (i + 1), fmt(round(v, 2)), fmt(round(v / float(a.total) * 100, 1))))


def colours_from(arg):
    c = dict(COLOURS)
    if arg:
        try:
            c.update(json.loads(arg))
        except ValueError:
            sys.exit('--colours must be JSON such as {"grid":"#00AEEF","spiral":"#FF0066"}')
    return c


def ratio_from(arg):
    named = {"phi": PHI, "root-phi": math.sqrt(PHI)}
    if arg in named:
        return named[arg]
    try:
        r = float(arg)
    except ValueError:
        sys.exit("--ratio must be phi, root-phi or a number above 1")
    if r <= 1:
        sys.exit("--ratio must be above 1")
    return r


def write(path, data):
    if path:
        with open(path, "w", encoding="utf-8") as f:
            f.write(data)
        print("wrote " + path)
    else:
        sys.stdout.write(data + "\n")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    g = sub.add_parser("grid", help="golden rectangle with squares, spiral, circles and phi lines")
    g.add_argument("--width", type=float); g.add_argument("--height", type=float)
    g.add_argument("--orient", choices=["auto", "landscape", "portrait"], default="auto",
                   help="with one side given, auto means landscape; with both sides, the shape decides")
    g.add_argument("--squares", type=int, default=8, help="at least 1")
    g.add_argument("--stroke", type=float, default=1.0)
    g.add_argument("--pad", type=float, default=None)
    g.add_argument("--mirror", action="store_true", help="flip the spiral left to right")
    g.add_argument("--no-spiral", action="store_true"); g.add_argument("--no-circles", action="store_true")
    g.add_argument("--no-phi-lines", action="store_true"); g.add_argument("--no-eye", action="store_true")
    g.add_argument("--no-notes", action="store_true")
    g.add_argument("--colours", help='JSON, e.g. {"grid":"#00AEEF","spiral":"#FF0066"}')
    g.add_argument("--background", default=None)
    g.add_argument("--out")
    g.set_defaults(fn=cmd_grid)

    q = sub.add_parser("page", help="page or screen grid: phi lines, golden columns, hero rectangle, spacing ruler")
    q.add_argument("--width", type=float, required=True); q.add_argument("--height", type=float, required=True)
    q.add_argument("--margin", type=float, default=34); q.add_argument("--gutter", type=float, default=21)
    q.add_argument("--squares", type=int, default=6, help="at least 1")
    q.add_argument("--stroke", type=float, default=1.0)
    q.add_argument("--colours"); q.add_argument("--background", default=None)
    q.add_argument("--out")
    q.set_defaults(fn=cmd_page)

    h = sub.add_parser("hero", help="README hero image: the digits of phi set on the grid")
    h.add_argument("--theme", choices=["light", "dark"], default="light")
    h.add_argument("--width", type=float, default=1600)
    h.add_argument("--squares", type=int, default=12, help="at least 1, at most the digits available")
    h.add_argument("--title", default="golden-ratio-design")
    h.add_argument("--background", default=None)
    h.add_argument("--out")
    h.set_defaults(fn=cmd_hero)

    t = sub.add_parser("scale", help="type scale and spacing from a base size")
    t.add_argument("--base", type=float, default=16.0)
    t.add_argument("--ratio", default="phi", help="phi, root-phi, or a number such as 1.25")
    t.add_argument("--up", type=int, default=6); t.add_argument("--down", type=int, default=2)
    t.add_argument("--format", choices=["table", "json", "css"], default="table")
    t.set_defaults(fn=cmd_scale)

    r = sub.add_parser("shares", help="split a total at the golden section: 61.8 / 23.6 / 14.6")
    r.add_argument("--total", type=float, default=100); r.add_argument("--parts", type=int, default=3)
    r.set_defaults(fn=cmd_shares)

    z = sub.add_parser("sequence", help="spacing sequence from a unit")
    z.add_argument("--unit", type=float, default=8); z.add_argument("--count", type=int, default=8)
    z.set_defaults(fn=cmd_sequence)

    a = p.parse_args()
    if getattr(a, "squares", 1) < 1:
        p.error("--squares must be at least 1")
    a.fn(a)


if __name__ == "__main__":
    main()
