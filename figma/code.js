// Golden Ratio Grid, a Figma plugin with no UI. Import it with Plugins > Development > Import plugin
// from manifest. Three commands, all on the current selection:
//   grid       golden rectangle, squares, spiral, circles, phi lines, eye, as a locked group "Golden grid"
//   guides     ruler guides at 0.382 and 0.618 of width and height, plus a 21-column layout grid
//              (13 columns are 61.9 percent, 8 are 38.1, so the golden split sits on column edges)
//   variables  a "Golden" variable collection: spacing 8 13 21 34 55 89 144 233 and type from the hero:
//              sub hero = hero / phi, body = hero / phi^2, then small, micro and display by the same step.
//              The hero is the one selected text layer's size, otherwise HERO below. Run it again after
//              changing the hero: an existing Golden collection is updated in place, and every text
//              layer bound to its variables follows.
// Each result is a template: names on every node, nothing merged, the grid group locked.
const PHI = (1 + Math.sqrt(5)) / 2;
const INV = 1 / PHI;
const HERO = 42; // the project's hero size in px (body is HERO / phi^2); a selected text layer overrides it
const KAPPA = 0.5522847498;
const GRID = { r: 31 / 255, g: 43 / 255, b: 1 };
const SPIRAL = { r: 232 / 255, g: 38 / 255, b: 43 / 255 };

function goldenSquares(x, y, w, h, n) {
  const out = [];
  const start = w >= h ? 0 : 1;
  for (let i = 0; i < n; i++) {
    if (w < 1e-6 || h < 1e-6) break;
    const d = (i + start) % 4;
    const s = Math.min(w, h);
    if (d === 0) { out.push([x, y, s, d]); x += s; w -= s; }
    else if (d === 1) { out.push([x, y, s, d]); y += s; h -= s; }
    else if (d === 2) { out.push([x + w - s, y, s, d]); w -= s; }
    else { out.push([x, y + h - s, s, d]); h -= s; }
  }
  return { squares: out, rest: [x, y, w, h] };
}

function eyePoint(x, y, w, h) {
  const r = goldenSquares(x, y, w, h, 60).rest;
  return [r[0] + r[2] / 2, r[1] + r[3] / 2];
}

function arcBeziers([x, y, s, d]) {
  let p0, p3, c;
  if (d === 0) { p0 = [x, y + s]; p3 = [x + s, y]; c = [x + s, y + s]; }
  else if (d === 1) { p0 = [x, y]; p3 = [x + s, y + s]; c = [x, y + s]; }
  else if (d === 2) { p0 = [x + s, y]; p3 = [x, y + s]; c = [x, y]; }
  else { p0 = [x + s, y + s]; p3 = [x, y]; c = [x + s, y]; }
  const u0 = [(p0[0] - c[0]) / s, (p0[1] - c[1]) / s];
  const u3 = [(p3[0] - c[0]) / s, (p3[1] - c[1]) / s];
  const k = KAPPA * s;
  return { p0, p1: [p0[0] + k * u3[0], p0[1] + k * u3[1]], p2: [p3[0] + k * u0[0], p3[1] + k * u0[1]], p3 };
}

function spiralData(squares) {
  const f = (v) => Math.round(v * 1000) / 1000;
  let d = "";
  squares.forEach((sq, i) => {
    const b = arcBeziers(sq);
    if (i === 0) d += `M ${f(b.p0[0])} ${f(b.p0[1])} `;
    d += `C ${f(b.p1[0])} ${f(b.p1[1])} ${f(b.p2[0])} ${f(b.p2[1])} ${f(b.p3[0])} ${f(b.p3[1])} `;
  });
  return d.trim();
}

function stroke(node, colour, weight, dashed) {
  node.fills = [];
  node.strokes = [{ type: "SOLID", color: colour }];
  node.strokeWeight = weight;
  if (dashed) node.dashPattern = [weight * 4, weight * 3];
}

function selectionBounds(nodes) {
  // page space, so the grid lands on the selection even when it sits inside frames or groups
  let L = Infinity, T = Infinity, R = -Infinity, B = -Infinity;
  for (const n of nodes) {
    const bb = n.absoluteBoundingBox || { x: n.x, y: n.y, width: n.width, height: n.height };
    L = Math.min(L, bb.x); T = Math.min(T, bb.y); R = Math.max(R, bb.x + bb.width); B = Math.max(B, bb.y + bb.height);
  }
  return { L, T, R, B };
}

function drawGrid() {
  const sel = figma.currentPage.selection;
  if (!sel.length) { figma.notify("Select something first: the grid encloses the selection."); return; }
  const parent = sel[0].parent;
  const { L, T, R, B } = selectionBounds(sel);
  const selW = R - L, selH = B - T;
  let W, H;
  if (selW >= selH) { W = Math.max(selW, selH * PHI); H = W * INV; } else { H = Math.max(selH, selW * PHI); W = H * INV; }
  const x0 = L + selW / 2 - W / 2, y0 = T + selH / 2 - H / 2;
  const nodes = [];

  const rect = figma.createRectangle(); rect.name = "Rectangle"; rect.x = x0; rect.y = y0; rect.resize(W, H); stroke(rect, GRID, 1, false); nodes.push(rect);
  const sq = goldenSquares(0, 0, W, H, 8).squares;
  sq.forEach((s, i) => {
    const r = figma.createRectangle(); r.name = `Square ${i + 1} (${Math.round(s[2])})`; r.x = x0 + s[0]; r.y = y0 + s[1]; r.resize(s[2], s[2]); stroke(r, GRID, 0.5, false); nodes.push(r);
    const c = figma.createEllipse(); c.name = `Circle ${i + 1} (d ${Math.round(s[2])})`; c.x = x0 + s[0]; c.y = y0 + s[1]; c.resize(s[2], s[2]); stroke(c, GRID, 0.5, true); nodes.push(c);
  });
  for (const f of [INV * INV, INV]) {
    const v = figma.createLine(); v.name = `Phi line x ${f.toFixed(3)}`; v.x = x0 + W * f; v.y = y0; v.resize(H, 0); v.rotation = -90; stroke(v, GRID, 0.5, true); nodes.push(v);
    const h = figma.createLine(); h.name = `Phi line y ${f.toFixed(3)}`; h.x = x0; h.y = y0 + H * f; h.resize(W, 0); stroke(h, GRID, 0.5, true); nodes.push(h);
  }
  const spiral = figma.createVector(); spiral.name = "Golden spiral";
  spiral.vectorPaths = [{ windingRule: "NONE", data: spiralData(sq) }];
  spiral.x = x0; spiral.y = y0; stroke(spiral, SPIRAL, 1.5, false); spiral.strokeCap = "ROUND"; nodes.push(spiral);
  const eye = eyePoint(0, 0, W, H); const rr = Math.max(W, H) * 0.012;
  const e = figma.createEllipse(); e.name = `Eye (${(eye[0] / W).toFixed(3)}, ${(eye[1] / H).toFixed(3)})`; e.x = x0 + eye[0] - rr; e.y = y0 + eye[1] - rr; e.resize(rr * 2, rr * 2); stroke(e, SPIRAL, 1, false); nodes.push(e);

  const group = figma.group(nodes, parent);
  group.name = `Golden grid ${Math.round(W)} x ${Math.round(H)}`;
  group.locked = true;
  figma.notify(`Golden grid ${Math.round(W)} x ${Math.round(H)}: eye at ${(eye[0] / W).toFixed(3)}, ${(eye[1] / H).toFixed(3)} of W, H`);
}

function setGuides() {
  const frames = figma.currentPage.selection.filter((n) => "guides" in n && (n.type === "FRAME" || n.type === "COMPONENT"));
  if (!frames.length) { figma.notify("Select a frame or component."); return; }
  for (const f of frames) {
    const w = f.width, h = f.height;
    f.guides = [
      { axis: "X", offset: w * INV * INV }, { axis: "X", offset: w * INV },
      { axis: "Y", offset: h * INV * INV }, { axis: "Y", offset: h * INV },
    ];
    if ("layoutGrids" in f) {
      f.layoutGrids = [{ pattern: "COLUMNS", alignment: "STRETCH", gutterSize: 0, count: 21, offset: 0, visible: true, color: { r: GRID.r, g: GRID.g, b: GRID.b, a: 0.08 } }];
    }
  }
  figma.notify(`Phi guides on ${frames.length} frame(s): 0.382 and 0.618 of width and height, 21 columns (13 + 8).`);
}

async function makeVariables() {
  // The hero drives everything: the selected text layer's size, else HERO at the top.
  let hero = HERO, from = "HERO in code.js";
  const texts = figma.currentPage.selection.filter((n) => n.type === "TEXT");
  if (texts.length === 1 && typeof texts[0].fontSize === "number") {
    hero = texts[0].fontSize;
    from = `the selected text layer "${texts[0].name}"`;
  }
  const body = hero / (PHI * PHI);
  let collection = (await figma.variables.getLocalVariableCollectionsAsync()).find((c) => c.name === "Golden");
  const fresh = !collection;
  if (fresh) collection = figma.variables.createVariableCollection("Golden");
  const mode = collection.modes[0].modeId;
  const existing = {};
  if (!fresh) {
    for (const id of collection.variableIds) {
      const v = await figma.variables.getVariableByIdAsync(id);
      if (v) existing[v.name] = v;
    }
  }
  const set = (name, value) => {
    const v = existing[name] || figma.variables.createVariable(name, collection, "FLOAT");
    v.setValueForMode(mode, value);
  };
  [8, 13, 21, 34, 55, 89, 144, 233].forEach((v, i) => set(`space/${i + 1}`, v));
  const roles = { "-2": "micro", "-1": "small", "0": "body", "1": "sub-hero", "2": "hero", "3": "display" };
  for (let n = -2; n <= 3; n++) set(`type/${roles[String(n)]}`, Math.round(body * Math.pow(PHI, n)));
  set("ratio/phi", 1.618);
  set("ratio/inverse", 0.618);
  figma.notify(`Golden collection ${fresh ? "created" : "updated"} from hero ${hero} (${from}): sub hero ${Math.round(body * PHI)}, body ${Math.round(body)}, small ${Math.round(body / PHI)}. Text bound to type/* follows.`);
}

(async () => {
  try {
    if (figma.command === "grid") drawGrid();
    else if (figma.command === "guides") setGuides();
    else if (figma.command === "variables") await makeVariables();
  } catch (err) {
    figma.notify("Golden Ratio Grid: " + err.message);
  }
  figma.closePlugin();
})();
