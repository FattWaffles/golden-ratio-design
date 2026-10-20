# Construction grammar: building a mark with no free numbers

The contract (`contract/golden.json`) says which values exist. The lint (`scripts/golden_lint.py`)
catches values that stepped outside it. This file is the third piece: how an agent builds a mark
from the ratio in the first place, so there is nothing to catch. The agent writes a plan in a
small vocabulary where every number is a kit term, a frame point, a phi step or a listed angle,
and `scripts/golden_build.py` refuses any other number unless the plan logs it as a departure
with a reason. The output is a template: the construction
on its own layer under the grid, every part named, the departures written in the notes.

## The vocabulary

Run `python3 -I scripts/golden_build.py --grammar` for the full list. In short:

| term | means | allowed values |
|:---|:---|:---|
| `unit` | px per kit unit; sets scale only | any number |
| `kit` | the sizes that exist | 1 2 3 5 8 13 21 34 55 89 144 (or your own run) |
| `frame` | the golden rectangle the mark lives in | `golden landscape w:21`, `golden portrait h:21`, `square s:13` |
| `circle d:8` | diameter | a kit term |
| `rect golden landscape w:8` | a golden rectangle by width (or `portrait h:`, `square s:`) | a kit term |
| `line len:8`, `angle` | a stroke of that length at that angle | kit term; angle from the contract list, `golden` = 137.5 |
| `arc d:8`, `quarter: ne` | a quarter circle | kit term; ne se sw nw |
| `spiral squares:6` | the frame's own spiral | a count |
| `at` | where the centre sits | `centre`, `eye`, `crossing-tl` to `-br`, `square-N`, `square-N-tl` to `-br`, `top`, `bottom`, `left`, `right`, `corner-tl` to `-br` |
| `at: "eye dx:2 dy:-3"` | an offset from that point | kit terms, signed |
| `stroke step:2` | stroke width | stroke unit times phi to the step minus one (`step:1` is the stroke unit itself); a line, arc or spiral with no stroke draws at step 1 |
| `fill` | ink, paper, none, a hex | |
| `cut` | subtract from the nearest solid part before it (or `cut: "<id>"` for a named one) | |
| `join` | unite with the previous solid part: a group in the SVG (same ink reads as one shape), Pathfinder Add in Illustrator; a later cut goes through the whole union | |
| `{"value": 20, "departure": "why"}` | a number outside the sets, logged | any size, radius, frame or angle, with a reason (offsets and stroke steps take kit terms and steps only) |

Why the kit: two circles of diameters 5 and 8 relate by 1.6, three
lines of lengths 3, 5 and 8 the same, and a stroke of step 1 against step 3 by 2.618. Every
relationship in the mark is then a relationship the eye already knows, which is what "resolved"
looks like. The agent can still make a bad mark; it cannot make an unbalanced one by accident.

## The workflow for an agent

1. **Brief and idea first.** The grammar only builds. Write the idea in one line
   (a box with a letter cut from it; a shell; two initials sharing a stroke) before any plan.
2. **Pick the frame and the unit.** Landscape for wordmarks and lockups, portrait or square for
   icons. The unit is only scale: unit 12 gives a mark 252 px wide at `w:21`; 10 gives 210 and 14 gives 294.
3. **Place the big shapes on frame points.** The eye for the focal element, `square-1` and
   `square-2` for a two-part mark, crossings for a three-part one. Sizes from the kit, biggest
   first.
4. **Cut and join.** Counters, notches and negative space as `cut` parts; shared stems as `join`.
   Keep each cut as its own part in the plan so the designer can move it.
5. **Strokes by step.** Hairline `step:1`, regular `step:2`, bold `step:3`. Three steps at most.
6. **Build.** `golden_build.py plan.json --out mark.svg --jsx mark.jsx`. A refused plan prints
   each bad value with its nearest allowed one; fix the plan and rebuild, the output is regenerated from it.
7. **Check.** `proportion_check.py --svg mark.svg` for the parts' ratios; the logo skill's
   `svg_audit.py` for the paths; the 16 px row and the one-colour test.
8. **Hand over.** Run the .jsx in Illustrator: the mark lands on an unlocked "Construction"
   layer with every part named, the locked grid on the layer under it, and a summary of the plan in a
   text named Notes. The designer
   finishes by hand. Anything they change that leaves the kit goes into the notes as a departure.

## Three plans to learn from

`examples/plans/shell.json`: a golden frame, its spiral at `step:4` and a kit-2 dot on the eye.
The spiral is the mark; the dot is the focal point.

`examples/plans/letter-o.json`: a ring of diameter 8 with a diameter-5 counter cut from it, and a
kit-1 square notch cut at `centre dx:3 dy:-3`. A letterform from two circles and a square, with the
counter and the notch both cut from the ring.

`examples/plans/monogram.json`: a kit-13 square on `square-1`, a diameter-8 o on `square-2` with
its counter cut, a diagonal at 58.3 degrees (a golden rectangle's diagonal measured from its short
side; the landscape frame's own diagonal runs at 31.7 from the long side) cut through the
square at `step:3`, and the frame as a hairline. Two initials from the grid's own squares.

Print any of them with `--example shell`, `--example letter-o`, `--example monogram`.

## What the builder does with cuts

In the SVG a cut is a mask on its target, so the file stays one shape per part. In Illustrator the
generated script tries Pathfinder Subtract on the two parts (it outlines a stroked cutter first, then
groups the pair so the live effect subtracts the front shape from the back);
when that fails it falls back to a paper-filled shape named "(cut, paper)" so nothing is lost and
the designer can run the boolean by hand. Set `USE_PATHFINDER = false` at the top of the .jsx to
keep every cut as a paper shape on purpose.

## Limits

No text: wordmarks come from the type skill and the font; the grammar builds marks, letterforms
and frames for type to sit in. No freeform curves: a curve is an arc or a spiral segment, or it is
drawn by hand afterwards and noted. No colour theory: fill is ink, paper or a hex you chose by the
colour reference.
