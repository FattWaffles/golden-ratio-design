#!/usr/bin/env python3
"""proportion_check.py: measure how close a design sits to the golden ratio.

Give it pairs of measurements, a JSON file, or an SVG. It reports each ratio, the nearest
golden value, the distance from it, and what one side would need to be to land on it.
Within the tolerance counts as on the ratio (default 3 percent). The report is advice for
the designer: the eye still decides, and a departure gets written down, never "fixed" blind.

  python3 -I proportion_check.py --pairs "box=2300/1400" "letters/box=910/1400" --tolerance 3
  python3 -I proportion_check.py --json measures.json
  python3 -I proportion_check.py --svg logo.svg
  python3 -I proportion_check.py --pairs "hero=1440/890" --format json
"""
import argparse
import json
import math
import re
import sys

PHI = (1 + math.sqrt(5)) / 2
INV = 1 / PHI
TARGETS = [
    ("0.618 (1/phi)", INV),
    ("0.382 (1/phi^2)", INV ** 2),
    ("0.236 (1/phi^3)", INV ** 3),
    ("0.146 (1/phi^4)", INV ** 4),
    ("0.786 (1/root phi, half step)", 1 / math.sqrt(PHI)),
    ("0.309 (1/2phi, two golden rectangles end to end)", INV / 2),
    ("0.5 (half)", 0.5),
    ("1 (equal)", 1.0),
]


def fmt(v, nd=3):
    s = ("%." + str(nd) + "f") % v
    return s.rstrip("0").rstrip(".") if "." in s else s


def assess(name, a, b, tol):
    a, b = float(a), float(b)
    if a <= 0 or b <= 0:
        return {"name": name, "a": fmt(a, 2), "b": fmt(b, 2), "error": "sides must be positive"}
    small, large = min(a, b), max(a, b)
    r = small / large
    best = min(TARGETS, key=lambda t: abs(r - t[1]) / t[1])
    dev = (r - best[1]) / best[1] * 100
    verdict = "on" if abs(dev) <= tol else ("near" if abs(dev) <= 2 * tol else "off")
    return {
        "name": name, "a": a, "b": b,
        "ratio": round(r, 4), "long_over_short": round(large / small, 4),
        "nearest": best[0], "deviation_pct": round(dev, 2), "verdict": verdict,
        "to_hit_nearest": {"target": round(best[1], 4), "keep_large_set_small": round(large * best[1], 2),
                           "keep_small_set_large": round(small / best[1], 2)},
        "to_hit_0618": {"keep_large_set_small": round(large * INV, 2), "keep_small_set_large": round(small * PHI, 2)},
    }


NUM = r"(-?\d+(?:\.\d+)?)"


def pairs_from_args(items):
    """name=a/b. A pair that does not parse becomes an error row, so the rest of the report still runs."""
    out = []
    for it in items:
        m = re.match(r"^\s*(.*?)\s*=\s*" + NUM + r"\s*/\s*" + NUM + r"\s*$", it)
        if not m:
            out.append((it, None, None))
            continue
        out.append((m.group(1) or "pair", float(m.group(2)), float(m.group(3))))
    return out


def pairs_from_json(path):
    try:
        data = json.load(open(path))
    except (OSError, ValueError) as e:
        sys.exit("json: %s" % e)
    out = []
    for k, v in data.items():
        try:
            if not isinstance(v, (list, tuple)) or len(v) != 2:
                raise ValueError
            out.append((k, float(v[0]), float(v[1])))
        except (TypeError, ValueError):
            out.append((k, None, None))
    return out


SKIP_GROUPS = ("squares", "circles", "eye", "phi-points", "phi-lines", "spacing-ruler")


def pairs_from_svg(path):
    """Each rect, circle, ellipse and image: its own aspect, and its height against the canvas.
    Construction groups written by golden_grid.py (squares, circles, eye) are skipped, and a
    golden-rectangle element, when present, stands in for the canvas."""
    src = open(path, encoding="utf-8", errors="replace").read()
    src = re.sub(r"<defs\b.*?</defs>", "", src, flags=re.S)  # masks and gradients are not parts
    src = re.sub(r'<rect width="100%"[^>]*/>', "", src)       # a paper background
    for gid in SKIP_GROUPS:
        src = re.sub(r'<g id="%s"[^>]*>.*?</g>' % gid, "", src, flags=re.S)
    out = []
    cw = ch = None
    gr = re.search(r'<g id="golden-rectangle">\s*<rect[^>]*width="([0-9.]+)"[^>]*height="([0-9.]+)"', src)
    vb = re.search(r'viewBox="([^"]+)"', src)
    if gr:
        cw, ch = float(gr.group(1)), float(gr.group(2))
        out.append(("golden rectangle (canvas)", cw, ch))
        src = src.replace(gr.group(0), "", 1)
    elif vb:
        parts = [float(v) for v in re.split(r"[ ,]+", vb.group(1).strip())]
        if len(parts) == 4:
            cw, ch = parts[2], parts[3]
            out.append(("canvas", cw, ch))
    for m in re.finditer(r"<(rect|ellipse|circle|image)\b([^>]*)>", src):
        tag, attrs = m.group(1), m.group(2)
        idm = re.search(r'id="([^"]+)"', attrs)
        name = idm.group(1) if idm else tag
        def num(k):
            mm = re.search(r'(?<![\w-])%s="(-?[0-9.]+)"' % k, attrs)
            return float(mm.group(1)) if mm else None
        if tag == "circle":
            r = num("r")
            if r and ch:
                out.append((name + " (d/canvas h)", 2 * r, ch))
            continue
        w = num("width") if tag != "ellipse" else (num("rx") or 0) * 2
        h = num("height") if tag != "ellipse" else (num("ry") or 0) * 2
        if w and h:
            out.append((name, w, h))
            if ch and name != "canvas":
                out.append((name + " (h/canvas h)", h, ch))
    return out


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--pairs", nargs="*", default=[], help='name=a/b, for example "box=2300/1400"')
    p.add_argument("--json", help='file of {"name": [a, b]}')
    p.add_argument("--svg", help="SVG file: rect, circle, ellipse, image elements and the viewBox")
    p.add_argument("--tolerance", type=float, default=3.0, help="percent counted as on the ratio (default 3)")
    p.add_argument("--format", choices=["table", "json"], default="table")
    a = p.parse_args()
    if a.tolerance < 0:
        p.error("--tolerance must be 0 or more")
    pairs = pairs_from_args(a.pairs)
    if a.json:
        pairs += pairs_from_json(a.json)
    if a.svg:
        pairs += pairs_from_svg(a.svg)
    if not pairs:
        p.error("give --pairs, --json or --svg")
    rows = [assess(n, x, y, a.tolerance) if x is not None else {"name": n, "a": "", "b": "", "error": "could not read, use name=a/b"}
            for n, x, y in pairs]
    if a.format == "json":
        print(json.dumps({"tolerance_pct": a.tolerance, "rows": rows}, indent=2))
        return
    print("| measure | a | b | small/large | nearest | off by | verdict | to land on it |")
    print("|:---|---:|---:|---:|:---|---:|:---|:---|")
    for r in rows:
        if "error" in r:
            print("| %s | %s | %s | | | | %s | |" % (r["name"], r["a"], r["b"], r["error"]))
            continue
        t = r["to_hit_nearest"]
        fix = "small %s or large %s" % (fmt(t["keep_large_set_small"], 2), fmt(t["keep_small_set_large"], 2))
        if abs(t["target"] - INV) > 1e-3:
            fix += " (for 0.618: small %s or large %s)" % (fmt(r["to_hit_0618"]["keep_large_set_small"], 2), fmt(r["to_hit_0618"]["keep_small_set_large"], 2))
        print("| %s | %s | %s | %s | %s | %s%% | %s | %s |" % (
            r["name"], fmt(r["a"], 2), fmt(r["b"], 2), fmt(r["ratio"]), r["nearest"],
            ("+" if r["deviation_pct"] > 0 else "") + fmt(r["deviation_pct"], 2), r["verdict"], fix))
    on = sum(1 for r in rows if r.get("verdict") == "on")
    print("\n%d of %d on the ratio within %s%%. 'near' is within twice that. The eye decides; write down any departure you keep." % (on, len(rows), fmt(a.tolerance, 1)))


if __name__ == "__main__":
    main()
