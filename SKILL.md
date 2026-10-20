---
name: golden-ratio-design
description: Golden ratio (phi 1.618, the divine proportion) construction and checking for every design task, as the default proportion system. Grids, shrinking squares, the spiral and phi circles for logos, wordmarks and icons; the type scale, line height, measure and font pairing for font deciding; colour shares at 61.8 / 23.6 / 14.6; website and app layout with golden columns, the hero rectangle and the spacing sequence 8 13 21 34 55 89; Figma guides, variables and a plugin; Illustrator script on a locked layer. Use this before constructing and before exporting any logo, icon, type system, palette, page, app screen, deck or Figma frame, even when the user never says golden ratio, proportion or grid, and whenever they ask for balance, hierarchy, spacing, a type scale, a layout grid or "make it feel resolved". Every output is an editable template for a designer to finish.
---

# Golden ratio design

The ratio sets up the template; a person finishes it. Use phi to decide the proportions nobody
wants to argue about (column widths, type steps, spacing, colour shares, where the first thing
goes), build them as named, locked, annotated construction, and leave the idea of the design and
the final optical corrections to the designer. The eye wins; the departure gets written down.

## The numbers

phi 1.618, 1/phi 0.618, 1/phi^2 0.382, 1/phi^3 0.236, 1/phi^4 0.146, half step 1.272.
Sequence 1 1 2 3 5 8 13 21 34 55 89 144 233. Eye of the spiral at 0.724 of width and height
(0.276 of width when portrait). Golden angle 137.5 degrees. Within 3 percent is on.

## The loop, every time

1. **Measure what exists.** Sizes, gaps, strokes, type sizes, colour areas. Run
   `scripts/proportion_check.py` with the pairs, a JSON file or the SVG export. Keep the table.
2. **Construct.** Draw the grid on the work: `scripts/golden_grid.jsx` in Illustrator (locked
   "Golden grid" layer, named groups, a notes text), `scripts/golden_grid.py grid|page` for an
   SVG, the Figma plugin in `figma/` for frames. Type and spacing tokens from
   `golden_grid.py scale`, colour shares from `golden_grid.py shares`.
3. **Check.** Rerun the check. On, near, off, with the value each side would need.
4. **Correct by eye.** Optical corrections stay; the concept's own angles and shapes stay.
5. **Record.** Notes in the file: values, date, tolerance, each departure with its reason.
6. **Hand over as a template.** Locked grid, named parts, variables, the measurement table.

## Hard rules (the contract)

`contract/golden.json` is the proportion contract: the allowed sets for type, line height,
spacing, strokes, columns and angles, a tolerance, an exempt list and a departures log. Projects
copy it and set their base sizes (`examples/oblique.golden.json` is Oblique's, body 18).

- **No free numbers.** Before a size is written into CSS, Figma or Illustrator, it comes from the
  contract: `golden_lint.py --snap 23 --domain space` answers 21 or 34. A value that must stay
  outside the sets is added to the contract's departures with a reason, in the same change.
- **The lint runs before export.** `golden_lint.py --css|--figma|--svg` on the file. Type,
  line height, spacing, strokes and columns block on an off value (exit 1); radii and other sizes
  warn. For a CSS file, `--fix nearest|up|down` writes a copy with blocked values pushed to the
  step, and `--fix both` writes a step-down and a step-up version to choose between; Figma and
  SVG inputs are reported only. The original is never edited.
- **Marks are built from the grammar.** New logos, icons and letterforms start as a plan for
  `golden_build.py`, where every size is a kit term and every position a frame point. The engine
  refuses any other number unless the plan logs it as a departure with a reason. See
  `references/10-construction-grammar.md`.
- **Departures are the designer's.** The eye still wins; the agent records each departure and leaves it in place.

Show the person a sample before explaining it: the grid over their work, or the scale table,
is faster to judge than a paragraph.

## Which reference to open

| task | read |
|:---|:---|
| any task, first time | `references/01-ratio-basics.md` |
| logo, wordmark, icon, app icon, mark construction, clear space | `references/02-logo-and-icon.md` |
| choosing fonts, pairing, type scale, line height, measure, type tokens | `references/03-typography.md` |
| palette shares, balance of colour, a new hue, tint ramps | `references/04-colour.md` |
| website pages, hero, columns, sections, image crops | `references/05-website-layout.md` |
| phone and tablet screens, cards, touch targets, icon keylines | `references/06-app-layout.md` |
| anything in Figma: plugin, guides, variables, handover layer | `references/07-figma.md` |
| hierarchy, when numbers and eye disagree, tolerance, leaving it as a template | `references/08-handover-and-balance.md` |
| the source video's method by chapter | `references/09-video-notes.md` |
| building a new mark from the ratio with no free numbers | `references/10-construction-grammar.md` |
| a worked example with real numbers (Oblique) | `examples/oblique.md` |

## Scripts

Run Python with `python3 -I` and quoted paths. All write to stdout unless `--out` is given (for the
lint, `--out` names the fixed copy and `--report` saves the table).

- `scripts/golden_grid.py grid --width 1000 --out grid.svg`: golden rectangle, squares, spiral,
  circles, phi lines, eye, notes. `--orient portrait`, `--mirror`, `--squares N`, `--colours`.
- `scripts/golden_grid.py page --width 1440 --height 900 --margin 34 --gutter 21`: page grid
  with phi lines and crossings, golden columns, hero rectangle, spacing ruler. Phone: 390 by 844,
  margin 21, gutter 13.
- `scripts/golden_grid.py scale --base 16 [--ratio phi|root-phi|1.25] [--format table|json|css]`.
- `scripts/golden_grid.py shares --total 100 --parts 3` and `sequence --unit 8 --count 8`.
- `scripts/golden_grid.py hero --theme light|dark`: the README image, digits of phi on the grid.
- `scripts/proportion_check.py --pairs "box=2300/1400" ... [--svg file] [--json file] [--tolerance 3]`.
- `scripts/golden_lint.py --css|--figma|--svg|--values ... [--contract file] [--snap N --domain d] [--fix nearest|up|down|both --out path]`:
  the enforcer. Exit 1 when a block-mode domain has an off value.
- `scripts/golden_build.py plan.json --out mark.svg --jsx mark.jsx`, `--grammar`, `--example shell|letter-o|monogram`:
  the construction engine for new marks.
- `scripts/golden_grid.jsx`: Illustrator. With a selection, the rectangle encloses it; without,
  it fills the artboard. Configure by defining `GOLDEN_CONFIG` before the file (consumed by the run) or editing CONFIG.
- `figma/`: the plugin (grid on selection, phi guides and 21-column grid, Golden variables).

## How it sits with other skills

This skill is the proportion layer under the others. Logo work: the logo skill owns concept,
critique, testing and delivery; this skill draws the construction grid first and runs the check
before export. Site and interface work: the interface skill owns the page; this skill supplies
the columns, the hero rectangle, the type and spacing tokens and the colour shares, and checks
the result. Type decisions: roles and pairing come from the typography reference here; the brand
skill records the choice. Decks and boards: the page grid at the slide size.

## What it is not

A proportion system cannot generate the idea, pick the font or choose the colour. It balances
what the designer made. A mark that is beautiful and 30 percent off the ratio is finished. A
spiral laid over a finished design for the presentation proves nothing and shows; draw it only
where it was used.
