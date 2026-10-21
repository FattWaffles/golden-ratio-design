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
   come closest and write down the deviation. Gaps, counters and margins join the same ladder;
   see "Inside the mark" below.
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

## Inside the mark: every shape, gap and weight

The outline can sit on the ratio while the inside does not. The eye reads the counters, the gaps
between letters, the slits and cuts and every line as much as the outer box, so measure them all
and put them on one ladder.

**Measure.** For each part, at the size the mark is used:

- counters: width, height, and each over the outer shape; whether they share its centre
- rings and bowls: thinnest and thickest stroke, taken through the counter's centre
- strokes: every vertical stem and every horizontal, measured separately
- gaps between letters at mid x-height, and the narrowest point
- slits, notches and cuts: their width against the stroke
- line bands, perpendicular to each edge (a hand-thickened line often differs edge to edge)
- margins, and panels or strips between cuts, against their neighbours
- angles of each family of edges

**Build the ladder.** Take the main stroke (the stem) as the unit s. The steps are s, s/1.618,
s/2.618, s/4.236, and upward s x 1.618, s x 2.618. Give each kind of part one whole step of s, up or
down; margins take a step too. Which step depends on the weight. In a heavy face like Oblique Trace
Heavy: counters s/phi, gaps and slits s/phi^2, lines s/phi^3, x-height phi^2 s. In a regular weight,
counters and the x-height sit several steps above s. Check it in one run:

```bash
python3 -I scripts/proportion_check.py --ladder "line=15.45" "gap=29.8" "counter=52.3" "stem=82.8" --unit stem
```

Each value gets its step, its distance from it, the value that would land, and the step between
it and the part below. Four steps from one unit is a balanced mark; eight weights on no common
step is the thing the eye calls "busy" without saying why.

**Watch the stretch.** Scaling letters in one direction changes their weights. Stretched taller by
k, every horizontal stroke grows by k while the stems stay, so the contrast becomes k x horizontal
over stem. Find the k where horizontals equal stems (k = stem / horizontal, in font units), and
check the x-height there. With Oblique Trace Heavy (stem 220, horizontal 194) k is 1.134. Stems and
horizontals are then one weight, and the o becomes an even ring. The x-height is 2.59 stems, 1.2
percent from phi^2. Thinner parts drawn to their own value, such as a crossbar or a slit, do not
follow; set them on the ladder separately. The 1.3 stretch the logo had made horizontals 1.146 of the
stems.

**Keep what the font already gives.** A well drawn face often carries the ratio in its counters
(every Oblique Trace Heavy counter is 0.60 to 0.63 of the stem wide, within 3 percent of 0.618).
Measure before redrawing, keep those relations, and change what a stretch, a tracking value or a
hand edit moved off the ladder.

**Optical departures stay and get written down:** round sides spaced a little tighter than
straight ones (0.9 of the gap), overshoots, tapering terminals.

**Count honestly.** At 3 percent, a single whole step lands by chance about 1 time in 8. With half
steps it is 1 in 4. The full set (`--set full`) gives 28 percent and the default core set 23
percent; the checker prints the rate for the set or ladder it used. One hit proves little. Evidence
is several independent parts on one ladder, such as the line, the gap and the counter each phi
apart. Repeats inside one font, like four counters drawn to one width, count as one relation.

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
- inside: counters, gaps, slits, cuts and margins each on a step of the main stroke
- stretch: horizontal strokes over vertical ones after any one-way scaling
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
