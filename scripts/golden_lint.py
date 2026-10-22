#!/usr/bin/env python3
"""golden_lint.py: enforce the proportion contract.

Reads a CSS file (or the style blocks of an HTML file), a Figma variables export, an SVG, or
plain values, classifies each value by domain (type, line_height, space, stroke, column, radius,
other), and checks it against the allowed set in the contract (contract/golden.json by default).
A value is on (within tolerance), near (within twice), exempt, a logged departure, off, or
unchecked (em and fr need their context). Off values in a block-mode domain fail the run with
exit code 1; warn-mode domains report and carry on. Nothing is edited in place: the table tells
the designer or the agent what to snap to, or what to log.

  python3 -I golden_lint.py --css site/index.html
  python3 -I golden_lint.py --figma variables.json
  python3 -I golden_lint.py --svg mark.svg
  python3 -I golden_lint.py --body <body> --values "type:<sizes>" "space:8,12,21"
  python3 -I golden_lint.py --snap 23 --domain space
  python3 -I golden_lint.py --snap <size> --domain type    (every level as a ratio of body)
  python3 -I golden_lint.py --css styles.css --body <body> (check against a chosen body without editing the contract)
  python3 -I golden_lint.py --css styles.css --contract my-project.golden.json --report lint.md
  python3 -I golden_lint.py --css styles.css --fix nearest --out styles.golden.css
  python3 -I golden_lint.py --css styles.css --fix both --out styles.golden.css   (writes -down and -up files)

--fix (CSS only) pushes every blocked value to the allowed step (nearest, up, down, or both as
two versions) and writes a copy with "/* was ... */" beside each change. The original is never
touched: the copy is the template the designer edits. Figma and SVG inputs are reported only.
"""
import argparse
import json
import math
import os
import re
import sys

PHI = (1 + math.sqrt(5)) / 2
HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_CONTRACT = os.path.join(HERE, "..", "contract", "golden.json")
DOMAINS = ("type", "line_height", "space", "stroke", "column", "radius", "other")


def fmt(v, nd=2):
    s = ("%." + str(nd) + "f") % v
    return s.rstrip("0").rstrip(".") if "." in s else s


def blank(text):
    """Same length, newlines kept, so offsets and line numbers still point into the original."""
    return re.sub(r"[^\n]", " ", text)


# ---------------------------------------------------------------- allowed sets

def additive_run(base, count=14):
    """The run through base where each term is the sum of the two before: 1 2 3 5 8 13 ... for 8."""
    base = float(base)
    a, b = base, round(base * PHI)
    up = [a, b]
    while len(up) < count:
        a, b = b, a + b
        up.append(b)
    down = []
    a, b = base, up[1]
    while True:
        c = b - a
        if c < 1 or c >= a:
            break
        down.insert(0, c)
        b, a = a, c
    return [float(v) for v in down] + [float(v) for v in up]


LEVELS = {"small": -1, "body": 0, "subhead": 1, "heading 2": 2, "heading 1": 3}


def type_body(dom, ratio=PHI):
    """The body size of the chosen typeface; every type size is a ratio of it. None when the contract
    sets no size, which is the default. Older contracts load: version 2's hero (body = hero / phi^2)
    and version 1's base."""
    if dom.get("body"):
        return float(dom["body"])
    if dom.get("hero"):
        return float(dom["hero"]) / float(ratio) ** 2
    if dom.get("base"):
        return float(dom["base"])
    return None


def type_half(contract):
    dom = contract["domains"]["type"]
    return bool(dom.get("half_steps", contract.get("half_step", False)))


def type_levels(dom, ratio=PHI):
    """[(name, step)] from small to large: each level's ratio of body as a step of phi."""
    named = dom.get("levels")
    if isinstance(named, dict) and named:
        out = [(name, round(math.log(float(r)) / math.log(float(ratio)) * 2) / 2.0) for name, r in named.items()]
    else:
        out = list(LEVELS.items())
    return sorted(out, key=lambda x: x[1])


def type_set(dom, ratio, half):
    """The body times each level's ratio, and the half steps between them when the contract asks."""
    body = type_body(dom, ratio)
    if body is None:
        return []
    steps = [k for _, k in type_levels(dom, ratio)]
    if half:
        steps = [x / 2.0 for x in range(int(min(steps) * 2), int(max(steps) * 2) + 1)]
    return sorted(set(body * ratio ** k for k in steps))


def type_note(v, body, ratio, dom, verdict):
    """A size as a ratio of body, named by its level or by the two levels it falls between."""
    k = math.log(v / body) / math.log(ratio)
    levels = type_levels(dom, ratio)
    if verdict != "off":
        name, step = min(levels, key=lambda x: abs(x[1] - k))
        label = name if abs(step - k) < 0.25 else "half step"
    else:
        lower = [n for n, s in levels if s <= k]
        upper = [n for n, s in levels if s >= k]
        if lower and upper:
            label = "between %s and %s" % (lower[-1], upper[0])
        else:
            label = ("below " + levels[0][0]) if not lower else ("above " + levels[-1][0])
    return "%s x body, %s" % (fmt(v / body, 2), label)


def allowed_sets(contract):
    d = contract["domains"]
    ratio = contract.get("ratio", PHI)
    run = additive_run(d["space"]["base"])
    return {
        "type": type_set(d["type"], ratio, type_half(contract)),
        "line_height": list(d["line_height"]["stops"]),
        "space": run,
        "column": list(d["column"]["shares"]),
        "radius": run,
        "other": run,
    }


def stroke_set(contract, seen):
    dom = contract["domains"]["stroke"]
    base = dom.get("base")
    if not base:
        base = min(seen) if seen else 1.0
    return [float(base) * PHI ** n for n in range(int(dom.get("steps", 6)))], float(base)


# ---------------------------------------------------------------- classification

SKIP_PROPS = ("src", "content", "font-family", "transition", "animation", "color", "background", "background-color",
              "background-image", "background-position", "background-size", "fill", "stroke", "opacity", "z-index",
              "font-weight", "letter-spacing", "transform", "filter", "box-shadow", "grid-area", "grid-template-areas",
              "font-display", "text-decoration", "mask-image", "-webkit-mask-image", "mask", "-webkit-mask",
              "mask-position", "mask-size", "object-position", "transform-origin", "aspect-ratio", "scroll-margin-top",
              "unicode-range", "rootmargin", "threshold", "text-size-adjust", "-webkit-text-size-adjust", "clip-path",
              "flex", "flex-grow", "flex-shrink", "order", "animation-delay", "transition-delay", "line-clamp", "-webkit-line-clamp")
SPACE_PROPS = ("margin", "padding", "gap", "row-gap", "column-gap", "inset", "top", "right", "bottom", "left", "outline-offset",
               "--space", "--gap", "--margin", "--section", "--pad")
STROKE_PROPS = ("border-width", "border-top-width", "border-right-width", "border-bottom-width", "border-left-width",
                "outline-width", "stroke-width", "--line-width", "--stroke")
RADIUS_PROPS = ("border-radius", "--radius")
COLUMN_PROPS = ("width", "max-width", "min-width", "flex-basis", "grid-template-columns", "--measure", "--col")


def classify(prop):
    p = prop.lower().strip()
    if p == "line-height" or p.startswith("--leading") or p.startswith("--lh"):
        return "line_height"
    if p in ("outline-offset", "row-gap", "column-gap"):
        return "space"
    if p in STROKE_PROPS or p.startswith("--stroke") or (p.startswith("border") and "radius" not in p) or p.startswith("outline"):
        return "stroke"
    if any(p.startswith(r) for r in RADIUS_PROPS):
        return "radius"
    if p == "font-size" or p.startswith("--t-") or p.startswith("--text") or p.startswith("--font-size") or p.startswith("--step"):
        return "type"
    if any(p.startswith(s) for s in SPACE_PROPS):
        return "space"
    if any(p == c or p.startswith(c) for c in COLUMN_PROPS):
        return "column"
    return "other"


NUM = r"(-?\d*\.?\d+)"
UNIT_RE = re.compile(NUM + r"(px|rem|em|%|fr|vw|vh|pt)?(?![\w-])")


def css_values(src, rem_px):
    """Rows of (line, prop, raw, value, unit, domain, context, offset). Offsets index the original text."""
    out = []
    if re.search(r"<style[^>]*>", src, flags=re.I):
        keep, last = [], 0
        for m in re.finditer(r"<style[^>]*>(.*?)</style>", src, flags=re.S | re.I):
            keep.append(blank(src[last:m.start(1)])); keep.append(m.group(1)); last = m.end(1)
        keep.append(blank(src[last:]))
        src = "".join(keep)
    src_nc = re.sub(r"/\*.*?\*/", lambda m: blank(m.group(0)), src, flags=re.S)
    for m in re.finditer(r"(--[\w-]+|[a-zA-Z-]+)\s*:\s*([^;{}]+)[;}]", src_nc):
        prop, val = m.group(1), m.group(2)
        if prop.lower() in SKIP_PROPS or "gradient(" in val or "url(" in val:
            continue
        line = src_nc.count("\n", 0, m.start()) + 1
        dom = classify(prop)
        ctx = "clamp" if "clamp(" in val else ("calc" if "calc(" in val else ("min/max" if re.search(r"\b(min|max)\(", val) else ""))
        if re.search(r"\d(vw|vh)\b", val):
            ctx = "viewport formula"  # inputs to a formula: reported, never snapped
        scan = re.sub(r"var\([^)]*\)", lambda mm: " " * len(mm.group(0)), val)
        for u in UNIT_RE.finditer(scan):
            num, unit = float(u.group(1)), u.group(2) or ""
            off = m.start(2) + u.start()
            if unit in ("vw", "vh") or num == 0:
                continue
            size_dom = "other" if dom == "column" else dom
            if unit in ("px", "pt"):
                out.append((line, prop, u.group(0), num, "px", size_dom, ctx, off))
            elif unit == "rem":
                out.append((line, prop, u.group(0), num * rem_px, "px", size_dom, ctx, off))
            elif unit == "%":
                if dom in ("column", "other") and 0 < num <= 100:
                    out.append((line, prop, u.group(0), num / 100.0, "share", "column", ctx, off))
            elif unit == "fr":
                out.append((line, prop, u.group(0), num, "fr", "column", ctx, off))
            elif unit == "em":
                out.append((line, prop, u.group(0), num, "em", size_dom, ctx, off))
            elif unit == "" and dom == "line_height":
                out.append((line, prop, u.group(0), num, "ratio", "line_height", ctx, off))
    return out


def figma_values(path):
    """A flat {name: value} export or a nested {collections: [{variables: [{name, value}]}]} one."""
    data = json.load(open(path))
    flat = {}

    def walk(obj):
        if isinstance(obj, dict):
            if "name" in obj and "value" in obj and isinstance(obj["value"], (int, float)) and not isinstance(obj["value"], bool):
                flat[str(obj["name"]).strip("/")] = float(obj["value"]); return
            for k, v in obj.items():
                if isinstance(v, (int, float)) and not isinstance(v, bool):
                    flat[str(k).strip("/")] = float(v)
                else:
                    walk(v)
        elif isinstance(obj, list):
            for it in obj:
                walk(it)
    walk(data)
    out = []
    for name, v in flat.items():
        n = name.lower()
        if any(w in n for w in ("weight", "opacity", "z-index", "zindex", "order", "count")):
            continue
        if n.startswith("type") or "font" in n or "text-size" in n:
            dom = "type"
        elif n.startswith("space") or "gap" in n or "pad" in n or "margin" in n:
            dom = "space"
        elif "stroke" in n or "border" in n:
            dom = "stroke"
        elif "radius" in n:
            dom = "radius"
        elif "leading" in n or "line-height" in n or "lineheight" in n:
            dom = "line_height"
        else:
            dom = "other"
        out.append((0, name, fmt(v, 3), v, "ratio" if dom == "line_height" else "px", dom, "", None))
    return out


def strip_group(src, gid):
    """Remove <g id="gid"> ... </g> including nested groups."""
    start = re.search(r'<g\b[^>]*\bid="%s"[^>]*>' % re.escape(gid), src)
    if not start:
        return src
    depth, pos = 0, start.start()
    for m in re.finditer(r"<g\b|</g>", src[start.start():]):
        depth += 1 if m.group(0) == "<g" else -1
        if depth == 0:
            return src[:start.start()] + src[start.start() + m.end():]
    return src


def svg_values(path):
    src = open(path, encoding="utf-8", errors="replace").read()
    src = re.sub(r"<defs\b.*?</defs>", "", src, flags=re.S)
    src = re.sub(r"<mask\b.*?</mask>", "", src, flags=re.S)
    for gid in ("golden-grid", "notes", "squares", "circles", "phi-lines", "eye", "phi-points", "spacing-ruler"):
        src = strip_group(src, gid)
    out = []
    for m in re.finditer(r"<(\w+)\b([^>]*)>", src):
        tag, attrs = m.group(1), m.group(2)
        if tag in ("svg", "g", "defs", "mask", "style", "title", "desc"):
            continue
        line = src.count("\n", 0, m.start()) + 1
        idm = re.search(r'id="([^"]+)"', attrs)
        name = idm.group(1) if idm else tag
        for attr, dom in (("stroke-width", "stroke"), ("font-size", "type"), ("r", "other"), ("width", "other"), ("height", "other"), ("rx", "radius")):
            mm = re.search(r'(?<![\w-])%s="(-?[0-9.]+)"' % attr, attrs)
            if not mm:
                continue
            v = float(mm.group(1))
            label = name + " " + attr
            if attr == "r":
                v *= 2; label = name + " r x2 (diameter)"
            if v > 0:
                out.append((line, label, fmt(v, 3), v, "px", dom, "", None))
    return out


def plain_values(items):
    out = []
    for it in items:
        if ":" not in it:
            sys.exit("values look like domain:1,2,3 (domain is one of %s)" % ", ".join(DOMAINS))
        dom, nums = it.split(":", 1)
        dom = dom.strip()
        if dom not in DOMAINS:
            sys.exit("unknown domain %r; use one of %s" % (dom, ", ".join(DOMAINS)))
        for n in nums.split(","):
            n = n.strip()
            if not n:
                continue
            try:
                v = float(n.rstrip("%"))
            except ValueError:
                sys.exit("values: %r is not a number (write 16 or 61.8%%, no units)" % n)
            if n.endswith("%"):
                v /= 100.0
            unit = "ratio" if dom == "line_height" else ("share" if dom == "column" else "px")
            out.append((0, dom, n, v, unit, dom, "", None))
    return out


# ---------------------------------------------------------------- judging

def nearest(value, allowed):
    below = max([a for a in allowed if a <= value], default=None)
    above = min([a for a in allowed if a >= value], default=None)
    cands = [a for a in (below, above) if a is not None]
    best = min(cands, key=lambda a: abs(value - a) / a)
    return best, below, above


def judge(rows, contract, sets):
    tol = float(contract.get("tolerance_pct", 3))
    exempt = {(e["domain"], round(float(e["value"]), 4)): e["reason"] for e in contract.get("exempt", [])}
    departures = {(d["domain"], round(float(d["value"]), 4)): d.get("reason", "") for d in contract.get("departures", [])}
    strokes_seen = [abs(r[3]) for r in rows if r[5] == "stroke" and r[4] == "px" and r[3] > 0]
    stroke_allowed, stroke_base = stroke_set(contract, strokes_seen)
    tdom = contract["domains"].get("type", {})
    ratio, half = float(contract.get("ratio", PHI)), type_half(contract)
    body_px = type_body(tdom, ratio)
    out = []
    for row in rows:
        line, prop, raw, v, unit, dom, ctx = row[:7]
        off = row[7] if len(row) > 7 else None
        mode = contract["domains"].get(dom, {}).get("mode", "warn")
        if ctx in ("calc", "min/max", "viewport formula"):
            mode = "warn"
        base = dict(line=line, prop=prop, raw=raw, domain=dom, unit=unit, mode=mode, offset=off, signed=v, below="", above="", below_v=None, above_v=None)
        if unit in ("em", "fr"):
            out.append(dict(base, verdict="unchecked", note="%s needs its context" % unit)); continue
        v = abs(v)
        key = (dom, round(v, 4))
        if key in exempt:
            out.append(dict(base, verdict="exempt", note=exempt[key])); continue
        if key in departures:
            out.append(dict(base, verdict="logged", note=departures[key])); continue
        if v == 0:
            out.append(dict(base, verdict="unchecked", note="zero")); continue
        if dom == "type" and body_px is None:
            out.append(dict(base, verdict="unchecked", note="no body size: set the chosen typeface's body in the contract, or pass --body N")); continue
        allowed = stroke_allowed if dom == "stroke" else sets.get(dom, sets["other"])
        if unit == "share":
            allowed = sets["column"]
        best, below, above = nearest(v, allowed)
        dev = round((v - best) / best * 100, 6)
        verdict = "on" if abs(dev) <= tol else ("near" if abs(dev) <= 2 * tol else "off")
        nd = 3 if unit in ("share", "ratio") else 2
        note = "nearest %s (%s%%)" % (fmt(best, nd), ("+" if dev > 0 else "") + fmt(dev, 1))
        if dom == "type":
            note = "%s; %s" % (type_note(v, body_px, ratio, tdom, verdict), note)
        if ctx:
            note += ", inside %s" % ctx
        if dom == "stroke":
            note += ", thinnest %s" % fmt(stroke_base)
        out.append(dict(base, verdict=verdict, note=note, below=fmt(below, nd) if below is not None else "",
                        above=fmt(above, nd) if above is not None else "", below_v=below, above_v=above))
    return out


def render_table(results, source, warn_only=False):
    lines = ["| line | property | value | domain | verdict | snap down | snap up | note |", "|---:|:---|:---|:---|:---|---:|---:|:---|"]
    for r in results:
        flag = r["verdict"]
        if flag == "off" and r["mode"] == "block":
            flag = "off, would block" if warn_only else "OFF, blocks"
        lines.append("| %s | %s | %s | %s | %s | %s | %s | %s |" % (r["line"] or "", r["prop"], r["raw"], r["domain"], flag, r["below"], r["above"], r["note"]))
    on = sum(1 for r in results if r["verdict"] in ("on", "exempt", "logged"))
    off_block = [r for r in results if r["verdict"] == "off" and r["mode"] == "block"]
    near = sum(1 for r in results if r["verdict"] == "near")
    off_warn = sum(1 for r in results if r["verdict"] == "off" and r["mode"] != "block")
    unchecked = sum(1 for r in results if r["verdict"] == "unchecked")
    lines.append("")
    lines.append("%s: %d pass, %d near, %d off in warn domains, %d off in block domains, %d unchecked." % (source, on, near, off_warn, len(off_block), unchecked))
    if off_block:
        lines.append(("Would block (warn-only run). " if warn_only else "Blocked. ") + "Snap each blocked value to the column beside it, or add it to the contract's departures with a reason.")
    return "\n".join(lines), len(off_block)


# ---------------------------------------------------------------- fixing

def new_token(res, target, rem_px):
    raw, unit, signed = res["raw"], res["unit"], res["signed"]
    sign = "-" if signed < 0 else ""
    if unit == "px" and raw.endswith("rem"):
        return sign + fmt(target / rem_px, 3) + "rem"
    if unit == "px":
        return sign + fmt(target, 2) + ("pt" if raw.endswith("pt") else "px")
    if unit == "share":
        return fmt(target * 100, 1) + "%"
    if unit == "ratio":
        return fmt(target, 3)
    return None


def apply_fix(src, results, direction, rem_px, out_path):
    """Write a copy with each blocked value replaced by its allowed step, spliced by offset from
    the end of the file backwards so earlier offsets stay valid. Returns the number of changes."""
    edits = []
    for r in results:
        if r["verdict"] != "off" or r["mode"] != "block" or r["offset"] is None:
            continue
        v = abs(r["signed"])
        if direction == "nearest":
            cands = [c for c in (r["below_v"], r["above_v"]) if c is not None]
            target = min(cands, key=lambda c: abs(v - c) / c) if cands else None
        else:
            target = r["above_v"] if direction == "up" else r["below_v"]
        if target is None:
            continue
        new = new_token(r, target, rem_px)
        if not new or new == r["raw"]:
            continue
        edits.append((r["offset"], r["raw"], new))
    out = src
    for off, raw, new in sorted(edits, reverse=True):
        if out[off:off + len(raw)] != raw:
            continue
        out = out[:off] + new + " /* was " + raw + " */" + out[off + len(raw):]
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(out)
    return len(edits)


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--contract", default=DEFAULT_CONTRACT)
    p.add_argument("--css"); p.add_argument("--figma"); p.add_argument("--svg")
    p.add_argument("--values", nargs="*", default=[], help='domain:values, e.g. "type:18,29,47" "column:61.8%%,38.2%%"')
    p.add_argument("--snap", type=float, help="print the allowed values around this number")
    p.add_argument("--domain", default="space", help="domain for --snap")
    p.add_argument("--body", type=float, help="check type against this body size instead of the contract's; every level is a ratio of it")
    p.add_argument("--warn-only", action="store_true", help="never block, report only")
    p.add_argument("--report", help="write the table to this file as well")
    p.add_argument("--fix", choices=["nearest", "up", "down", "both"], help="write a copy of the CSS with blocked values pushed to the step")
    p.add_argument("--out", help="path for the fixed copy; 'both' adds -down and -up before the extension")
    p.add_argument("--json", action="store_true")
    a = p.parse_args()
    try:
        contract = json.load(open(a.contract))
    except (OSError, ValueError) as e:
        sys.exit("contract: %s" % e)
    if a.body is not None:
        if a.body <= 0:
            sys.exit("--body must be above 0")
        tdom = contract.setdefault("domains", {}).setdefault("type", {})
        tdom["body"] = a.body
        tdom.pop("hero", None)
    sets = allowed_sets(contract)
    if a.snap is not None:
        if a.domain not in DOMAINS:
            sys.exit("no such domain; use one of %s" % ", ".join(DOMAINS))
        if a.domain == "stroke":
            allowed, base = stroke_set(contract, [])
            if not contract["domains"]["stroke"].get("base"):
                print("stroke has no base in this contract: the set is relative to the thinnest stroke in a file. Steps from 1: %s" % " ".join(fmt(x) for x in allowed))
                return
        else:
            allowed = sets[a.domain]
        v = abs(a.snap)
        if v == 0:
            sys.exit("snap a value above 0")
        if a.domain == "type" and not allowed:
            print("no body size in this contract. Levels as ratios of body: %s. Pass --body N for sizes." % ", ".join(
                "%s %s" % (n, fmt(PHI ** k, 3)) for n, k in type_levels(contract["domains"]["type"])))
            return
        best, below, above = nearest(v, allowed)
        nd = 3 if a.domain in ("column", "line_height") else 2
        print("%s in %s: nearest %s, below %s, above %s" % (fmt(v, nd), a.domain, fmt(best, nd), fmt(below, nd) if below is not None else "none", fmt(above, nd) if above is not None else "none"))
        if a.domain == "type":
            tdom = contract["domains"]["type"]
            ratio = float(contract.get("ratio", PHI))
            body_px = type_body(tdom, ratio)
            print("%s. Levels: %s" % (type_note(v, body_px, ratio, tdom, "on"), ", ".join(
                "%s %s (%s x body)" % (n, fmt(body_px * ratio ** k), fmt(ratio ** k, 3)) for n, k in type_levels(tdom, ratio))))
        return
    rows, source, css_src = [], "", None
    try:
        if a.css:
            css_src = open(a.css, encoding="utf-8", errors="replace").read()
            rows += css_values(css_src, contract.get("rem_px", 16)); source = a.css
        if a.figma:
            rows += figma_values(a.figma); source = a.figma
        if a.svg:
            rows += svg_values(a.svg); source = a.svg
    except (OSError, ValueError) as e:
        sys.exit("cannot read: %s" % e)
    if a.values:
        rows += plain_values(a.values); source = source or "values"
    if not rows:
        p.error("give --css, --figma, --svg, --values or --snap")
    results = judge(rows, contract, sets)
    table, blocked = render_table(results, source, a.warn_only)
    if a.json:
        print(json.dumps({"source": source, "results": results}, indent=2))
    else:
        print(table)
    if a.report:
        with open(a.report, "w", encoding="utf-8") as f:
            f.write(table + "\n")
    if a.fix:
        if css_src is None:
            sys.exit("--fix works on --css files; Figma and SVG inputs are reported only")
        css_rows = css_values(css_src, contract.get("rem_px", 16))
        css_results = judge(css_rows, contract, sets)
        base, ext = os.path.splitext(a.out or (os.path.splitext(a.css)[0] + ".golden" + os.path.splitext(a.css)[1]))
        if a.fix == "both":
            for d in ("down", "up"):
                n = apply_fix(css_src, css_results, d, contract.get("rem_px", 16), base + "-" + d + ext)
                print("wrote %s (%d values pushed %s)" % (base + "-" + d + ext, n, d))
        else:
            n = apply_fix(css_src, css_results, a.fix, contract.get("rem_px", 16), base + ext)
            print("wrote %s (%d values pushed to the %s step)" % (base + ext, n, a.fix))
    if blocked and not a.warn_only:
        sys.exit(1)


if __name__ == "__main__":
    main()
