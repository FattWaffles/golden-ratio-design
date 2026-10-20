<picture>
  <source media="(prefers-color-scheme: dark)" srcset="assets/hero-dark.svg">
  <img alt="The digits of phi, 1.618033988749..., set one per square on the golden grid with the golden spiral through them" src="assets/hero-light.svg" width="100%">
</picture>

# golden-ratio-design

Golden ratio (divine proportion) maths for design, as scripts and rules for Illustrator and Figma. One ratio, phi 1.618, drawn as grids, squares, spirals and circles for logos and icons, turned into type scales, spacing sequences and colour shares, and laid over pages and app screens. Every output is an editable template: locked construction layer, named parts, values written in the file, so a designer finishes it by hand.

It is also a skill for Claude Code: drop the folder into `.claude/skills/` and it becomes the default proportion system for design work in that project.

## The rules

1. **Measure before you draw.** Sizes, gaps, strokes, type sizes, colour areas, into a table. The check tells you what is already on the ratio.
2. **One golden rectangle frames the work.** Sides 1 : 1.618. A logo, a hero, a card, a first screen.
3. **Squares make the spiral, and the spiral places the first thing.** The eye of the spiral sits at 0.724 of the width and height. Put the focal point there or on a crossing of the 0.382 and 0.618 lines.
4. **Sizes step by phi.** 1, 1.618, 2.618, 4.236. The half step, 1.272, when you need more sizes. Spacing follows the sequence 8 13 21 34 55 89 144.
5. **Split space 61.8 / 38.2.** Three parts: 61.8 / 23.6 / 14.6. Content and sidebar, image and caption, logo and clear space.
6. **Line weights step by phi.** Hairline, regular, bold at 1, 1.618, 2.618 of the thinnest.
7. **Type: body times phi is the next heading.** Line height 1.618 for body, 1.272 for subheads, 1.0 for display. Measure 45 to 75 characters. Display font at least one full step above body where they meet.
8. **Colour: dominant 61.8, secondary 23.6, accent 14.6, measured by area.** The heaviest colour takes the smaller share. A new hue sits 137.5 degrees round the wheel.
9. **Within 3 percent is on.** The eye has the final say, and every departure is written down with its reason.
10. **Leave it as a template.** Locked "Golden grid" layer, named groups, notes with the values, variables bound to one base size.
11. **No free numbers.** Every size comes from the contract's sets or is logged as a departure with a reason. The lint blocks type, line height, spacing, strokes and columns that step outside; new marks are built from a grammar that cannot.

## What is inside

| path | what |
|:---|:---|
| `scripts/golden_grid.py` | SVG grids (rectangle, squares, spiral, circles, phi lines, eye), page and phone grids, type scale and spacing tables, colour shares, this README's hero image |
| `scripts/proportion_check.py` | ratio report for pairs, JSON or an SVG: on, near, off, and what each side would need to be |
| `contract/golden.json` | the proportion contract: allowed sets per domain, block or warn, tolerance, exempt values, departures log |
| `scripts/golden_lint.py` | the enforcer: lints CSS, Figma variables, SVG or plain values against the contract; snaps; `--fix` writes a pushed copy of a CSS file (or two, step down and step up) |
| `scripts/golden_build.py` | the construction engine: a plan in the golden grammar (kit sizes, frame points, phi strokes, listed angles) becomes an SVG and an Illustrator script; anything outside the sets is refused |
| `examples/plans/` | three plans with their renders: a shell, a letter o, a two-letter monogram |
| `scripts/golden_grid.jsx` | Illustrator: the construction on a locked layer around the selection, every part named |
| `figma/` | Figma plugin: golden grid on selection, phi guides and a 21-column grid, a Golden variables collection |
| `references/` | the method by area: basics, logo and icon, typography, colour, website, app, Figma, handover, the source video |
| `examples/oblique.md` | a worked example with real numbers |
| `assets/grids/` | ready SVG grids: 1000 landscape, 390 portrait, 1440 by 900 page, 390 by 844 phone |
| `SKILL.md` | the Claude Code skill file |

## Quick start

Illustrator: select the artwork, then File > Scripts > Other Script and pick `scripts/golden_grid.jsx`. A locked layer "Golden grid" appears with the rectangle, squares, circles, phi lines, spiral, eye and a notes line. Or from a shell:

```bash
osascript -e 'tell application "Adobe Illustrator 2026" to do javascript (POSIX file "/path/to/scripts/golden_grid.jsx")'
```

Figma: Plugins > Development > Import plugin from manifest, choose `figma/manifest.json`. Select a frame, run "Phi guides and 21-column grid". Select artwork, run "Golden grid on selection". Run "Golden variables" once per file.

Anywhere:

```bash
python3 -I scripts/golden_grid.py page --width 1440 --height 900 --out page.svg
python3 -I scripts/golden_grid.py scale --base 16 --format css
python3 -I scripts/golden_grid.py shares --parts 3
python3 -I scripts/proportion_check.py --pairs "hero=1440/890" "label/body=11/18" --tolerance 3
python3 -I scripts/golden_lint.py --css styles.css --contract contract/golden.json
python3 -I scripts/golden_lint.py --snap 23 --domain space
python3 -I scripts/golden_build.py examples/plans/monogram.json --out monogram.svg --jsx monogram.jsx
```

## Enforcing it

The contract names the values that exist. The lint reads a stylesheet, a Figma variables export or an SVG and reports every proportion-bearing value as on, near, exempt, logged, off or unchecked (em and fr need their context), with the step below and above it. Off values in type, line height, spacing, strokes and columns fail the run. For a CSS file, `--fix` writes a copy with them pushed to the step, or two copies (down and up) to choose between; Figma and SVG inputs are reported only. The original file is never edited.

## Building a mark from it

An agent writes a plan: sizes from the kit (1 2 3 5 8 13 21), positions on the frame's points (the eye, the phi crossings, the squares), strokes by phi step, angles from the list. The engine refuses any other number unless it carries a reason, then renders the SVG and an Illustrator script that puts the construction on its own layer under the locked grid.

| | | |
|:---:|:---:|:---:|
| ![shell](examples/plans/shell.svg) | ![letter o](examples/plans/letter-o.svg) | ![monogram](examples/plans/monogram.svg) |
| `shell.json` | `letter-o.json` | `monogram.json` |

## The numbers

| value | meaning |
|---:|:---|
| 1.618 | phi, the bigger part over the smaller |
| 0.618 | the bigger part's share of the whole |
| 0.382 | the smaller part's share |
| 0.236 and 0.146 | the smaller part split again, for a third and fourth share |
| 1.272 | the half step (square root of phi) |
| 0.724 | the spiral's eye, as a fraction of width and height (0.276 of width when portrait) |
| 137.5 degrees | the golden angle |
| 1 1 2 3 5 8 13 21 34 55 89 144 | the sequence: the ratio in whole numbers |

## Grids

| | |
|:---:|:---:|
| ![golden rectangle 1000 wide](assets/grids/golden-landscape-1000.svg) | ![page grid 1440 by 900](assets/grids/page-1440x900.svg) |
| golden rectangle with squares, spiral, circles, phi lines | page grid with phi lines, golden columns, hero rectangle, spacing ruler |

## Sources

- Will Paterson, "How to Use the Golden Ratio in Graphic Design!" (2022), the method this skill follows: https://www.youtube.com/watch?v=MxiqsEm159U
- Robert Bringhurst, *The Elements of Typographic Style*, for the 45 to 75 character measure.
- The near-miss audit list (stroke weights, radii, angles, concentric circles, symmetry) follows the construction-grid tools Logo Grid Lines by Studio Gibbous and LogoGrid.

## Licence

MIT. Fonts, logos and brands named in the examples belong to their owners.
