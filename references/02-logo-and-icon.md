# Logo and icon construction

Read `01-ratio-basics.md` first. This file is for marks, wordmarks, icons and app icons.

## What the ratio does for a mark

A logo is seen at 16 px and on a building. Proportions that repeat one ratio survive both,
because the eye reads the relationship rather than the measurements. The ratio sets the
relationships: how tall the letters are inside the box, how wide the clear space is, how the
curves relate to each other, how the stroke weights step. The idea of the mark is yours; the
ratio tidies it.

## Steps

1. **Measure the existing mark.** Export the SVG, run `proportion_check.py --svg`, and add the
   hand measurements the script cannot see (stroke weights, gaps, counter widths). Write the
   table down before changing anything, so the after can be compared with the before.
2. **Frame it in a golden rectangle.** Run `golden_grid.jsx` with the mark selected. The rectangle
   encloses the mark and the spiral's eye shows where the visual weight should sit. If the mark is
   square or circular, the rectangle still helps: it sets clear space and the lockup with the name.
3. **Build the circle kit.** Diameters from the sequence at one unit (for example 8 px units: 8,
   16, 24, 40, 64, 104), or the inscribed circles the script drew. Snap every curve to one of
   them. A curve that fits none of them is the first candidate to redraw.
4. **Set the line weights by phi.** Three weights are enough: hairline, regular, bold at 1,
   1.618, 2.618 of the thinnest. If the typeface has fixed weights, pick the three whose ratios
   come closest and write down the deviation.
5. **Set the inner proportions.** Letters or symbol at 0.618 of the container height, margins
   sharing the 0.382. Counters and gaps from the sequence. Any lean, angle or cut that belongs
   to the concept stays as it is; the ratio moves what is around it.
6. **Clear space and minimum size.** Clear space 0.382 of the mark's height on every side (or
   0.618 for a quiet brand). Minimum size: the smallest width at which the thinnest stroke is
   still one device pixel.
7. **Check and correct by eye.** Rerun the check. Then look at it at 16 px, in one colour,
   reversed, next to the peers. The eye wins; a departure gets a note in the file.
8. **Leave it as a template.** Grid on the locked "Golden grid" layer, the mark on its own layer,
   every part a named group, notes with the values. The next designer edits it.

## Icon grids

App and interface icons use a keyline grid: a 24-unit square (or 20, 16) with a circle, a
square, a landscape and a portrait rectangle inside it, all of the same visual weight. Platform
keylines are not golden (Material: circle 20, square 18, rectangles 20 by 16 in a 24 grid). This
skill's own variant sets the inner circle at 0.618 of the square and the rectangles at 1 : 1.618;
it reads lighter than the platform set, so pick one grid and keep every icon on it. Draw it once as a component; every icon is drawn inside it, then exported
without it.

## Wordmarks

The ratio has a say in type too: x-height to cap height sits near 0.62 in old-style serifs (EB
Garamond is 0.615) and near 0.72 in most grotesque sans, which tells you which family a wordmark
reads as; letter spacing from the sequence (a tracking value, a word space of 2 or 3 units);
a tagline at 0.382 of the wordmark height, or 0.236 for a long one. See
`03-typography.md` for the scale.

## The audit list

From construction-grid tools: the near-misses worth checking because they are the ones that
look wrong without saying why.

- stroke weights: do they come from one phi family?
- corner radii: one family, inner and outer radii differing by the stroke
- edge angles: repeated, with the concept's own angle kept
- concentric circles: curves that share a centre should share it exactly
- symmetry: mirrored parts match to the pixel, or the asymmetry is deliberate and noted
- optical centre: the mark's weight sits on the eye or a phi crossing, away from the geometric centre

## What not to do

Do not stretch a finished mark onto the grid. Measure, then move one thing at a time, and
compare with the before. Do not add a spiral to a presentation that was not built on one; it
shows. And a mark that is 2 percent off the ratio is finished; a mark that is 30 percent off and
beautiful is also finished. The ratio is a tool for balance. The mark does not have to pass it.
