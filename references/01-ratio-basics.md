# Ratio basics

The numbers behind every other reference. Read this once; the others assume it.

## The ratio

phi = 1.6180339887. Its inverse is 0.6180339887, and phi minus one is the same number. That
self-similarity is the whole point: cut a golden rectangle into a square and a smaller rectangle,
and the smaller rectangle is golden too, for ever. A design built on it has one proportion at
every scale, which is why it reads as calm.

Useful forms of the same number:

| value | meaning | use |
|---:|:---|:---|
| 1.618 | phi | the bigger part is this many times the smaller |
| 0.618 | 1/phi | the bigger part's share of the whole |
| 0.382 | 1/phi^2 | the smaller part's share of the whole |
| 0.236 | 1/phi^3 | the second split of the smaller part |
| 0.146 | 1/phi^4 | the third split |
| 2.618 | phi^2 | two steps up a scale |
| 1.272 | square root of phi | a half step, for tighter scales |
| 137.5 degrees | the golden angle, 360/phi^2 | spacing around a circle |

Approximations that pass: 5:8, 8:13, 13:21, 62:38. 60:40 is 7 percent off and fails the check;
use it only when a grid forces it, and note it. Within 3 percent of the ratio counts as on, the
working tolerance of this skill (no published threshold exists), so stop chasing decimals once
the check says "on".

## The sequence

1 1 2 3 5 8 13 21 34 55 89 144 233. Each number is the sum of the two before it, and each pair's
ratio closes in on phi (8/5 = 1.6, 13/8 = 1.625, 21/13 = 1.615). The sequence is the ratio in
whole numbers, which is why it works for pixel sizes, point sizes and spacing where decimals are
noise. Pick a run of it as your spacing scale and your type scale falls out of the same numbers.

## Drawing the grid by hand (his method)

1. Draw a square. Call its side 1.
2. Beside it, draw a rectangle of width 0.618 and the same height. Together they make a golden
   rectangle of width 1.618.
3. In the new rectangle, draw a square of its width (0.618). What is left below it is a golden
   rectangle again, turned the other way.
4. Repeat inward: square, remainder, square, remainder. Eight squares are plenty; by the ninth
   the square is 1.3 percent of the width (13 px in a 1000 px grid), too small to place anything on.
5. In each square, draw a quarter circle from one corner to the opposite corner, centred on the
   corner that touches the next square. Joined up, the arcs make the spiral.

In Illustrator `scripts/golden_grid.jsx` draws all of this on a locked layer in one run, and
`scripts/golden_grid.py grid` writes the same as an SVG for Figma or the browser. Draw it by hand
once anyway: the construction is the lesson.

## The spiral and the eye

The true golden spiral is logarithmic: it grows by phi every quarter turn. The quarter circles
are a close stand-in and are what every grid, plugin and tutorial actually draws. The spiral
winds into one point, the eye, at 0.724 of the width and 0.724 of the height of a landscape
rectangle (0.276 of the width for the portrait version that turns the same way). Whatever sits
on the eye is what people look at first. Put the focal point there, or on one of the four
crossings of the 0.382 and 0.618 lines, which are the same idea with less drawing.

## Circles from the sequence

Circles with diameters 1, 2, 3, 5, 8, 13 (any unit) are the logo kit. Overlap them and the
curves you cut from them share one family of radii, so a mark drawn from them looks resolved
even when the viewer cannot say why. The inscribed circle of each square in the grid gives the
same set, scaled by phi instead of by the sequence; both are fine, use the one whose sizes land
on your drawing.

## Angle and triangle

The golden angle, 137.5 degrees, spaces items around a centre so that none line up: use it to
place petals, dots or an accent hue on the colour wheel. The golden triangle (36, 72, 72 degrees)
and its gnomon (108, 36, 36) build the pentagram and any five-fold mark.

## Checking what exists

Measure first, every time. Width and height of each part, gaps, stroke weights, type sizes,
then `scripts/proportion_check.py` says which ratios are on, near or off and what one side would
need to be. Most good work is already near the ratio by instinct; the check tells you which
near-misses are worth nudging and which to leave.
