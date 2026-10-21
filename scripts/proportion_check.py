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
  python3 -I proportion_check.py --set full --pairs "line/stem=15.45/82.8"
  python3 -I proportion_check.py --ladder "line=15.45" "gap=29.8" "counter=52.3" "stem=82.8" --unit stem

--set core (the default) scores against the main shares: 0.618, 0.382, 0.236, 0.146, the 0.786 half step,
0.309, 0.5 and 1. --set full replaces them with every power of phi down to 1/phi^6, every half step between
them, 1/(2 phi) and 1/(3 phi); it leaves out 0.5. Every report ends with the chance rate: how often an
arbitrary value would land on with that set and tolerance. One hit proves little; weigh full steps and
relations between independent parts.

--ladder takes line weights, gaps, counters and margins as name=value and puts each on the phi ladder of
the unit (the main stroke, usually the stem): unit, unit/1.618, unit/2.618, unit/4.236 and so on. It shows
each value's step, how far it sits from it, the step between neighbours and the value that would land.
It runs on its own: --pairs, --json and --svg cannot be given with it.
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


def full_targets():
    """Every power of phi from 1/phi^6 to 1, the half steps between them, 1/(2 phi) and 1/(3 phi)."""
    out = [("1 (equal)", 1.0)]
    for k in range(1, 7):
        out.append(("%s (1/phi^%d)" % (fmt(INV ** k), k), INV ** k))
    for k in range(0, 6):
        h = k + 0.5
        out.append(("%s (1/phi^%s, half step)" % (fmt(INV ** h), fmt(h, 1)), INV ** h))
    out.append(("0.309 (1/2phi, two golden rectangles end to end)", INV / 2))
    out.append(("0.206 (1/3phi, three golden rectangles end to end)", INV / 3))
    return out


def chance_rate(targets, tol, lo=None, n=20000):
    """Share of ratios spread evenly in log space between lo and 1 that land within tol of a target."""
    lo = lo or min(v for _, v in targets) / (1 + 2 * tol / 100)
    a, hits = math.log(lo), 0
    for i in range(n):
        r = math.exp(a + (0 - a) * (i + 0.5) / n)
        if any(abs(r - v) / v * 100 <= tol for _, v in targets):
            hits += 1
    return hits / n, lo


def fmt(v, nd=3):
    if abs(v) < 0.5 * 10 ** -nd:
        v = 0.0                      # no "-0"
    s = ("%." + str(nd) + "f") % v
    return s.rstrip("0").rstrip(".") if "." in s else s


def verdict_of(dev, tol):
    """on within tol, near within twice it; judged on the deviation as printed (2 decimals)."""
    d = abs(round(dev, 2))
    return "on" if d <= tol else ("near" if d <= 2 * tol else "off")


def sig(v, n=4):
    """A value to n significant figures (at least 2 decimals), so small units do not print as 0."""
    if not v:
        return "0"
    return fmt(v, max(2, n - 1 - int(math.floor(math.log10(abs(v))))))


def assess(name, a, b, tol, targets=None):
    targets = targets or TARGETS
    a, b = float(a), float(b)
    if a <= 0 or b <= 0:
        return {"name": name, "a": fmt(a, 2), "b": fmt(b, 2), "error": "sides must be positive"}
    small, large = min(a, b), max(a, b)
    r = small / large
    best = min(targets, key=lambda t: abs(r - t[1]) / t[1])
    dev = (r - best[1]) / best[1] * 100
    verdict = verdict_of(dev, tol)
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


def ladder_rows(items, unit_name, tol, half):
    """items: [(name, value)]. Each value over the unit, its nearest step phi^k (whole steps, or half steps
    too when half), and the step to its smaller neighbour."""
    vals = [(n, v) for n, v in items if v is not None and v > 0]
    if not vals:
        return None, []
    unit = None
    if unit_name:
        unit = next((v for n, v in vals if n == unit_name), None)
        if unit is None:
            return "unit %r is not one of the names" % unit_name, []
    else:
        unit_name, unit = max(vals, key=lambda t: t[1])
    step = 0.5 if half else 1.0
    LP = math.log(PHI)

    def nearest_step(ratio_log):
        """The step (a multiple of step) nearest in percent, choosing between the two around the value."""
        lo_k = math.floor(ratio_log / LP / step) * step
        return min((lo_k, lo_k + step), key=lambda c: abs(math.exp(ratio_log - c * LP) - 1))

    rows, prev = [], None
    for n, v in sorted(vals, key=lambda t: t[1]):
        k = nearest_step(math.log(v) - math.log(unit))
        land = unit * PHI ** k
        dev = (v - land) / land * 100
        row = {"name": n, "value": v, "over_unit": float("%.4g" % (v / unit)), "step": k, "lands_at": float("%.4g" % land),
               "deviation_pct": round(dev, 2), "verdict": verdict_of(dev, tol)}
        if prev:
            g = v / prev[1]
            gk = nearest_step(math.log(v) - math.log(prev[1]))
            row["from_previous"] = {"from": prev[0], "ratio": round(g, 4), "nearest_step": gk,
                                    "deviation_pct": round((g - PHI ** gk) / PHI ** gk * 100, 2)}
        rows.append(row)
        prev = (n, v)
    return (unit_name, unit), rows


def ladder_chance(tol, half):
    """Share of values placed at random (evenly in log space) that land within tol of a step."""
    band = math.log(1 + tol / 100) - math.log(max(1e-12, 1 - tol / 100))
    return min(1.0, band / ((0.5 if half else 1.0) * math.log(PHI)))


def print_ladder(head, rows, tol, half, fmt_json):
    rate = ladder_chance(tol, half)
    if fmt_json:
        print(json.dumps({"unit": {"name": head[0], "value": head[1]}, "tolerance_pct": tol, "half_steps": half,
                          "chance_on": round(rate, 3), "rows": rows}, indent=2))
        return
    print("Ladder on the unit %s = %s (steps of phi%s; step 0 is the unit, -1 is unit/1.618, -2 is unit/2.618)\n" % (head[0], sig(head[1]), ", half steps allowed" if half else ""))
    print("| part | value | over unit | step | lands at | off by | verdict | step from the part below |")
    print("|:---|---:|---:|---:|---:|---:|:---|:---|")
    for r in rows:
        fp = r.get("from_previous")
        gap = ""
        if fp:
            gap = "%s over %s: %s (phi^%s, %s%s%%)" % (r["name"], fp["from"], fmt(fp["ratio"]), fmt(fp["nearest_step"], 1),
                                                     "+" if fp["deviation_pct"] > 0 else "", fmt(fp["deviation_pct"], 2))
        print("| %s | %s | %s | %s | %s | %s%s%% | %s | %s |" % (r["name"], sig(r["value"]), fmt(r["over_unit"]), fmt(r["step"], 1),
              sig(r["lands_at"]), "+" if r["deviation_pct"] > 0 else "", fmt(r["deviation_pct"], 2), r["verdict"], gap))
    on = sum(1 for r in rows if r["verdict"] == "on")
    print("\n%d of %d on a step within %s%%. A balanced mark puts every weight, gap and counter on one ladder; three or four steps are enough." % (on, len(rows), fmt(tol, 1)))
    print("Chance rate: a value placed at random lands on a %s step %d%% of the time. Repeats inside one drawing (four counters drawn to one width) count as one relation." % ("half" if half else "whole", round(rate * 100)))


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--pairs", nargs="*", default=[], help='name=a/b, for example "box=2300/1400"')
    p.add_argument("--json", help='file of {"name": [a, b]}')
    p.add_argument("--svg", help="SVG file: rect, circle, ellipse, image elements and the viewBox")
    p.add_argument("--tolerance", type=float, default=3.0, help="percent counted as on the ratio (default 3)")
    p.add_argument("--format", choices=["table", "json"], default="table")
    p.add_argument("--set", choices=["core", "full"], default="core", help="targets: core shares (default) or full (every power and half step of phi)")
    p.add_argument("--ladder", nargs="*", default=None, help='weights, gaps, counters as name=value, for example "stem=82.8" "gap=29.8"')
    p.add_argument("--unit", help="with --ladder: the name of the unit (default: the largest value)")
    p.add_argument("--half", action="store_true", help="with --ladder: allow half steps (1.272) as well as whole steps")
    a = p.parse_args()
    if not math.isfinite(a.tolerance) or a.tolerance < 0:
        p.error("--tolerance must be a finite number, 0 or more")
    if a.ladder is None and (a.unit or a.half):
        p.error("--unit and --half go with --ladder")
    if a.ladder is not None:
        if a.pairs or a.json or a.svg:
            p.error("--ladder runs on its own; drop --pairs, --json and --svg")
        if not a.ladder:
            p.error('--ladder needs at least one name=value, for example "stem=82.8" "gap=29.8"')
        items = []
        for it in a.ladder:
            m = re.match(r"^\s*(.*?)\s*=\s*" + NUM + r"\s*$", it)
            items.append((m.group(1), float(m.group(2))) if m else (it, None))
        bad = [it for (n, v), it in zip(items, a.ladder) if not n or v is None or not math.isfinite(v) or v <= 0]
        if bad:
            p.error("could not read %s: use name=value with a name and a positive value" % ", ".join(bad))
        names = [n for n, _ in items]
        dup = sorted({n for n in names if names.count(n) > 1})
        if dup:
            p.error("give each name once: %s repeats" % ", ".join(dup))
        head, rows = ladder_rows(items, a.unit, a.tolerance, a.half)
        if isinstance(head, str):
            p.error(head)
        print_ladder(head, rows, a.tolerance, a.half, a.format == "json")
        return
    targets = TARGETS if a.set == "core" else full_targets()
    pairs = pairs_from_args(a.pairs)
    if a.json:
        pairs += pairs_from_json(a.json)
    if a.svg:
        pairs += pairs_from_svg(a.svg)
    if not pairs:
        p.error("give --pairs, --json or --svg")
    rows = [assess(n, x, y, a.tolerance, targets) if x is not None else {"name": n, "a": "", "b": "", "error": "could not read, use name=a/b"}
            for n, x, y in pairs]
    if a.format == "json":
        rate, lo = chance_rate(targets, a.tolerance)
        print(json.dumps({"tolerance_pct": a.tolerance, "set": a.set, "chance_on": round(rate, 3),
                          "chance_range": [round(lo, 4), 1], "rows": rows}, indent=2))
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
    rate, lo = chance_rate(targets, a.tolerance)
    print("Chance rate: with the %s set at %s%%, an arbitrary ratio between %s and 1 lands on %d%% of the time. Weigh full steps and relations between independent parts." % (a.set, fmt(a.tolerance, 1), fmt(lo, 3), round(rate * 100)))


if __name__ == "__main__":
    main()
