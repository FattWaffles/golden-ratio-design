// golden_grid.jsx: draw a golden ratio construction on a locked "Golden grid" layer in Illustrator.
// Golden rectangle, shrinking squares, spiral (cubic arcs), inscribed circles, phi lines at 0.382 and
// 0.618, the eye point, and a notes text. Each part is a named group, so the file stays an editable
// template for the next designer.
//
// Run: File > Scripts > Other Script, or from the shell:
//   osascript -e 'tell application "Adobe Illustrator 2026" to do javascript (POSIX file "/path/golden_grid.jsx")'
// With a selection (or CONFIG.bounds) the rectangle encloses it (landscape or portrait by its shape) and
// is centred on it. With nothing selected it fills the active artboard width. Override any CONFIG key by
// defining GOLDEN_CONFIG before this file is included, e.g. var GOLDEN_CONFIG = {squares: 10, mirror: true}.
// Keys: width, bounds, boundsType, orient, squares, spiral, circles, phiLines, eye, notes, mirror, layer, stroke, lock.
#target illustrator

var CONFIG = {
  width: 0,            // 0 = artboard width when nothing is selected
  bounds: null,        // [left, top, right, bottom] in document points (y up): use these instead of the selection
  boundsType: "geometric", // geometric (the paths) or visible (with strokes and effects) when reading the selection
  orient: "auto",      // auto | landscape | portrait
  squares: 8,
  spiral: true,
  circles: true,
  phiLines: true,
  eye: true,
  notes: true,
  mirror: false,       // flip the spiral left to right
  layer: "Golden grid",
  stroke: 0.75,        // pt, squares get half, spiral one and a half
  rgb: { grid: [31, 43, 255], spiral: [232, 38, 43], note: [85, 85, 94] },
  cmyk: { grid: [100, 80, 0, 0], spiral: [0, 95, 85, 0], note: [0, 0, 0, 70] },
  lock: true
};
if (typeof GOLDEN_CONFIG !== "undefined" && GOLDEN_CONFIG) { for (var key in GOLDEN_CONFIG) { CONFIG[key] = GOLDEN_CONFIG[key]; } GOLDEN_CONFIG = null; }
// GOLDEN_CONFIG is consumed by the run: Illustrator keeps the script engine alive between runs, so a stale
// override would otherwise leak into the next one.

var PHI = (1 + Math.sqrt(5)) / 2;
var INV = 1 / PHI;
var KAPPA = 0.5522847498;

function goldenSquares(x, y, w, h, n) {
  var out = [], start = (w >= h) ? 0 : 1, i, d, s;
  for (i = 0; i < n; i++) {
    if (w < 1e-6 || h < 1e-6) { break; }
    d = (i + start) % 4;
    s = Math.min(w, h);
    if (d === 0) { out.push([x, y, s, d]); x += s; w -= s; }
    else if (d === 1) { out.push([x, y, s, d]); y += s; h -= s; }
    else if (d === 2) { out.push([x + w - s, y, s, d]); w -= s; }
    else { out.push([x, y + h - s, s, d]); h -= s; }
  }
  return { squares: out, rest: [x, y, w, h] };
}

function eyePoint(x, y, w, h) {
  var r = goldenSquares(x, y, w, h, 60).rest;
  return [r[0] + r[2] / 2, r[1] + r[3] / 2];
}

function arcInSquare(sq) {
  var x = sq[0], y = sq[1], s = sq[2], d = sq[3];
  if (d === 0) { return { p0: [x, y + s], p3: [x + s, y], c: [x + s, y + s] }; }
  if (d === 1) { return { p0: [x, y], p3: [x + s, y + s], c: [x, y + s] }; }
  if (d === 2) { return { p0: [x + s, y], p3: [x, y + s], c: [x, y] }; }
  return { p0: [x + s, y + s], p3: [x, y], c: [x + s, y] };
}

function arcBeziers(sq) {
  var a = arcInSquare(sq), r = sq[2], k = KAPPA * r;
  var u0 = [(a.p0[0] - a.c[0]) / r, (a.p0[1] - a.c[1]) / r];
  var u3 = [(a.p3[0] - a.c[0]) / r, (a.p3[1] - a.c[1]) / r];
  return { p0: a.p0, p1: [a.p0[0] + k * u3[0], a.p0[1] + k * u3[1]], p2: [a.p3[0] + k * u0[0], a.p3[1] + k * u0[1]], p3: a.p3 };
}

function restoreActive(doc, prev, grid) {
  // leave an unlocked layer active, so the next run and the designer can keep working
  var i;
  if (prev && prev !== grid && !prev.locked && prev.visible) { doc.activeLayer = prev; return; }
  for (i = 0; i < doc.layers.length; i++) {
    if (doc.layers[i] !== grid && !doc.layers[i].locked && doc.layers[i].visible) { doc.activeLayer = doc.layers[i]; return; }
  }
}

function main() {
  if (app.documents.length === 0) { app.documents.add(DocumentColorSpace.RGB, 1000, 1000); }
  var doc = app.activeDocument;
  app.coordinateSystem = CoordinateSystem.DOCUMENTCOORDINATESYSTEM;
  var isRGB = (doc.documentColorSpace === DocumentColorSpace.RGB);

  function colour(name) {
    var c;
    if (isRGB) { c = new RGBColor(); c.red = CONFIG.rgb[name][0]; c.green = CONFIG.rgb[name][1]; c.blue = CONFIG.rgb[name][2]; }
    else { c = new CMYKColor(); c.cyan = CONFIG.cmyk[name][0]; c.magenta = CONFIG.cmyk[name][1]; c.yellow = CONFIG.cmyk[name][2]; c.black = CONFIG.cmyk[name][3]; }
    return c;
  }

  // frame: [left, top] in a y-down frame, converted to Illustrator's y-up on draw
  var left, top, W, H, selW = 0, selH = 0, i, b;
  var hasBounds = (CONFIG.bounds && CONFIG.bounds.length === 4);
  var sel = doc.selection;
  var hasSel = sel && sel.length > 0 && sel.typename !== "TextRange" && sel[0].geometricBounds;
  if (hasBounds || hasSel) {
    var L = 1e9, T = -1e9, R = -1e9, B = 1e9;
    if (hasBounds) { L = CONFIG.bounds[0]; T = CONFIG.bounds[1]; R = CONFIG.bounds[2]; B = CONFIG.bounds[3]; }
    else {
      for (i = 0; i < sel.length; i++) {
        b = (CONFIG.boundsType === "visible") ? sel[i].visibleBounds : sel[i].geometricBounds; // [left, top, right, bottom], y up
        if (b[0] < L) { L = b[0]; } if (b[1] > T) { T = b[1]; } if (b[2] > R) { R = b[2]; } if (b[3] < B) { B = b[3]; }
      }
    }
    selW = R - L; selH = T - B;
    var landscape = (CONFIG.orient === "landscape") || (CONFIG.orient === "auto" && selW >= selH);
    if (landscape) { W = Math.max(selW, selH * PHI); H = W * INV; }
    else { H = Math.max(selH, selW * PHI); W = H * INV; }
    left = L + selW / 2 - W / 2; top = T - selH / 2 + H / 2;
  } else {
    var ab = doc.artboards[doc.artboards.getActiveArtboardIndex()].artboardRect; // [left, top, right, bottom]
    var abW = ab[2] - ab[0], abH = ab[1] - ab[3];
    var wantLandscape = (CONFIG.orient === "landscape") || (CONFIG.orient === "auto" && abW >= abH);
    W = CONFIG.width > 0 ? CONFIG.width : abW * 0.9;
    if (wantLandscape) { H = W * INV; } else { H = W * PHI; }
    if (H > abH * 0.9) { H = abH * 0.9; W = wantLandscape ? H * PHI : H * INV; }
    left = ab[0] + abW / 2 - W / 2; top = ab[1] - abH / 2 + H / 2;
  }

  function X(x) { return CONFIG.mirror ? left + W - x : left + x; }
  function Y(y) { return top - y; }

  // layer
  var layer = null;
  for (i = 0; i < doc.layers.length; i++) { if (doc.layers[i].name === CONFIG.layer) { layer = doc.layers[i]; } }
  if (!layer) { layer = doc.layers.add(); layer.name = CONFIG.layer; }
  layer.locked = false; layer.visible = true;
  var prevActive = doc.activeLayer;
  doc.activeLayer = layer; // Illustrator adds items through the active layer; a locked active layer throws
  var root = layer.groupItems.add(); root.name = "Golden grid " + Math.round(W) + " x " + Math.round(H);
  var sq = goldenSquares(0, 0, W, H, CONFIG.squares).squares;
  if (sq.length === 0) { root.remove(); if (CONFIG.lock) { layer.locked = true; } restoreActive(doc, prevActive, layer); return "Golden grid: nothing to draw (squares " + CONFIG.squares + ", size " + Math.round(W) + " x " + Math.round(H) + ")"; }
  var eye = eyePoint(0, 0, W, H);
  try {

  function strokeIt(item, name, width, dashed) {
    item.filled = false; item.stroked = true; item.strokeColor = colour(name); item.strokeWidth = width;
    if (dashed) { item.strokeDashes = [width * 4, width * 3]; }
  }

  var gRect = root.groupItems.add(); gRect.name = "Rectangle";
  var rect = gRect.pathItems.rectangle(Y(0), X(CONFIG.mirror ? W : 0), W, H);
  strokeIt(rect, "grid", CONFIG.stroke, false);

  var gSq = root.groupItems.add(); gSq.name = "Squares";
  for (i = 0; i < sq.length; i++) {
    var s = sq[i];
    var r = gSq.pathItems.rectangle(Y(s[1]), X(CONFIG.mirror ? s[0] + s[2] : s[0]), s[2], s[2]);
    r.name = "Square " + (i + 1) + " (" + Math.round(s[2]) + ")";
    strokeIt(r, "grid", CONFIG.stroke * 0.5, false);
  }

  if (CONFIG.circles) {
    var gC = root.groupItems.add(); gC.name = "Circles";
    for (i = 0; i < sq.length; i++) {
      var q = sq[i];
      var e = gC.pathItems.ellipse(Y(q[1]), X(CONFIG.mirror ? q[0] + q[2] : q[0]), q[2], q[2]);
      e.name = "Circle " + (i + 1) + " (d " + Math.round(q[2]) + ")";
      strokeIt(e, "grid", CONFIG.stroke * 0.5, true);
    }
  }

  if (CONFIG.phiLines) {
    var gP = root.groupItems.add(); gP.name = "Phi lines 0.382 and 0.618";
    var fr = [INV * INV, INV], j;
    for (j = 0; j < 2; j++) {
      var v = gP.pathItems.add(); v.setEntirePath([[X(W * fr[j]), Y(0)], [X(W * fr[j]), Y(H)]]); strokeIt(v, "grid", CONFIG.stroke * 0.5, true);
      var hz = gP.pathItems.add(); hz.setEntirePath([[X(0), Y(H * fr[j])], [X(W), Y(H * fr[j])]]); strokeIt(hz, "grid", CONFIG.stroke * 0.5, true);
    }
  }

  if (CONFIG.spiral) {
    var gS = root.groupItems.add(); gS.name = "Spiral";
    var path = gS.pathItems.add();
    var anchors = [], bz = [];
    for (i = 0; i < sq.length; i++) { bz.push(arcBeziers(sq[i])); }
    anchors.push([X(bz[0].p0[0]), Y(bz[0].p0[1])]);
    for (i = 0; i < bz.length; i++) { anchors.push([X(bz[i].p3[0]), Y(bz[i].p3[1])]); }
    path.setEntirePath(anchors);
    for (i = 0; i < path.pathPoints.length; i++) {
      var pp = path.pathPoints[i];
      pp.leftDirection = (i > 0) ? [X(bz[i - 1].p2[0]), Y(bz[i - 1].p2[1])] : pp.anchor;
      pp.rightDirection = (i < bz.length) ? [X(bz[i].p1[0]), Y(bz[i].p1[1])] : pp.anchor;
      pp.pointType = (i === 0 || i === bz.length) ? PointType.CORNER : PointType.SMOOTH;
    }
    strokeIt(path, "spiral", CONFIG.stroke * 1.5, false);
    path.name = "Golden spiral";
  }

  if (CONFIG.eye) {
    var gE = root.groupItems.add(); gE.name = "Eye (" + (eye[0] / W).toFixed(3) + ", " + (eye[1] / H).toFixed(3) + ")";
    var rr = Math.max(W, H) * 0.012;
    var ec = gE.pathItems.ellipse(Y(eye[1] - rr), X(CONFIG.mirror ? eye[0] + rr : eye[0] - rr), rr * 2, rr * 2);
    strokeIt(ec, "spiral", CONFIG.stroke, false);
    var l1 = gE.pathItems.add(); l1.setEntirePath([[X(eye[0] - rr * 2), Y(eye[1])], [X(eye[0] + rr * 2), Y(eye[1])]]); strokeIt(l1, "spiral", CONFIG.stroke, false);
    var l2 = gE.pathItems.add(); l2.setEntirePath([[X(eye[0]), Y(eye[1] - rr * 2)], [X(eye[0]), Y(eye[1] + rr * 2)]]); strokeIt(l2, "spiral", CONFIG.stroke, false);
  }

  if (CONFIG.notes) {
    var gN = root.groupItems.add(); gN.name = "Notes";
    var ns = Math.max(6, Math.min(W, H) * 0.018);
    var t = gN.textFrames.add();
    t.contents = "phi 1.618  |  W " + Math.round(W * 10) / 10 + "  H " + Math.round(H * 10) / 10 + "  |  0.618 : 0.382 lines  |  eye at (" +
      (eye[0] / W).toFixed(3) + ", " + (eye[1] / H).toFixed(3) + ") of W, H  |  " + sq.length + " squares, inscribed circles" +
      (selW ? ("  |  selection " + Math.round(selW) + " x " + Math.round(selH)) : "");
    t.textRange.characterAttributes.size = ns;
    t.textRange.characterAttributes.fillColor = colour("note");
    t.position = [left, top - H - ns * 0.8];
  }

  } finally {
    if (CONFIG.lock) { layer.locked = true; }
    restoreActive(doc, prevActive, layer);
  }
  doc.selection = null;
  return "Golden grid: " + Math.round(W) + " x " + Math.round(H) + " on layer '" + CONFIG.layer + "', " + sq.length +
    " squares, eye at " + Math.round(eye[0]) + ", " + Math.round(eye[1]) + (selW ? " around a " + Math.round(selW) + " x " + Math.round(selH) + " selection" : "");
}

main();
