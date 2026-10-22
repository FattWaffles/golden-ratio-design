# Worked example: Oblique

The numbers from the Oblique brand and oblique.so, checked against the ratio with the scripts in
this skill. Verdicts use the 3 percent tolerance. The first tables measure logo v1. The last logo
section is the rebalance built from them, which Oblique adopted as logo v2 on 2026-10-20.

## Logo v1 (box lean upright)

| measure | a | b | ratio | nearest | verdict |
|:---|---:|---:|---:|:---|:---|
| export canvas (viewBox) | 2300 | 1400 | 0.609 | 0.618 | on (-1.5%) |
| whole mark (box with depth) | 1988 | 581 | 0.292 | 0.309, two golden rectangles end to end | near (-5.4%) |
| front face of the box | 1652 | 334 | 0.202 | 0.236 | off (-14.4%); three golden rectangles end to end (0.206) would be on |
| depth face height against front face height | 246 | 334 | 0.737 | 0.786, half step | off (-6.3%, just past near) |
| mark height against canvas height | 581 | 1400 | 0.415 | 0.382 | off (+8.7%) |

Measured 2026-10-20 on artboard "v1 box-lean-upright" of the working logo file with the Illustrator
script's bounds and a read-only probe; nothing was saved. The spiral's eye of the enclosing golden
rectangle (1988 by 1229) falls on the e, where the wordmark ends.

The box leans 20 degrees and the letters stand upright at 130 percent of a normal height. Both
are the concept and stay. The ratio moves what is around them: letter block at 0.618 of box
height, margins sharing the 0.382, stroke steps at 1 : 1.618 : 2.618.

## Inside the logo (measured 2026-10-20)

Every counter, ring, gap, slit, cut and line of the same mark, from the SVG export and the font data
(two measurers and an independent checker; they agree within 1 percent). Stem s = 82.8, x-height 245.6.

| part | value | over the stem | nearest step | verdict |
|:---|---:|---:|:---|:---|
| box line | 15.45 | 0.187 | 1/phi^3.5, half step | on, between whole steps |
| slits in b and q | 29.4 to 29.9 | 0.35 to 0.36 | 1/phi^2 | off to near |
| gaps between letters | 29.8 round, 33.1 straight | 0.36, 0.40 | 1/phi^2 | near |
| e crossbar | 43.1 | 0.52 | 1/phi^1.5, half step, +7 percent | off |
| counters o b q e | 50.0 to 52.3 | 0.60 to 0.63 | 1/phi | on, all four |
| stems | 82.8 | 1 | unit | |
| horizontals (after the 1.3 stretch) | 94.9 | 1.146 | phi^0.5, half step, -9.9 percent | off |

Also on:

- The o is 2.63 stems wide (phi^2).
- The o counter is 0.24 of the o's width (1/phi^3). It shares the o's centre point; the arcs are not concentric.
- The b counter is 0.382 of the bowl right of the stem.
- Both cuts between the top strips equal the stem.

Off:

- The two adjacent top strips, at 1.37 and 5.98.
- The end face, irregular after the line was thickened by hand.
- The ring of the o: 1.15 times as thick at top and bottom as at the sides.

The depth lines run at 36.25 degrees, 0.7 percent from the pentagon angle 36. This is a coincidence
of the 45 degree recession and the 20 degree lean. Angles are outside the checked set.

The font carries the ratio in its counters. The stretch, the gap rule and the box line sit off the
ladder. The unstretched font was off too: its horizontals are 0.88 of the stems. The eight weights do
not share one ladder:

```bash
python3 -I scripts/proportion_check.py --ladder "line=15.45" "slit=29.4" "gap-round=29.8" "gap-straight=33.1" "crossbar=43.1" "counter=52.3" "stem=82.8" "horizontal=94.9" --unit stem
```

That puts 2 of 8 on, and one of the two is the stem itself.

## Logo v2: every shape and weight from the stem

The rebalance, built from logo v1's own generator and font engine. It keeps the knockout box, the 20
degree lean and the 45 degree recession, and lowers the letters from 130 to 113 percent. Oblique adopted
it as logo v2 on 2026-10-20. The stem is the unit.

| part | rule | value |
|:---|:---|---:|
| stretch | horizontals equal stems: 220 / 194 font units | 113 percent |
| x-height | set by the stretch: 2.59 s, phi^2 -1.2 percent | 214.2 |
| stems, horizontals, top margin, cuts | s | 82.8 |
| counters | the font's, kept: 0.60 to 0.63 s, on s / phi | 50.0 to 52.3 |
| bottom margin | s / phi | 51.2 |
| gaps, e crossbar | s / phi^2 (round sides 0.9 of it, optical) | 31.6 |
| box line | s / phi^3 | 19.55 |
| face height | x-height + phi s (phi of the x-height, +0.5 percent) | 348.2 |
| depth rise | phi^2 s | 216.8 |
| depth lines | 36.00 degrees (recession 44.65) | |

```bash
python3 -I scripts/proportion_check.py --ladder "line=19.55" "gap=31.6" "counter=51.2" "stem=82.8" --unit stem
```

That puts 4 of 4 on, each phi over the one below. Adding "xheight=214.2" and "face=348.2" gives 6 of
6 on; the x-height sits phi^2 over the stem. An independent measurement of the built mark found every
designed relation within 3 percent. The round-side gaps (0.344 of the stem) are the logged optical
departure. Costs: letters shorter than the 130 percent concept, a heavier box line, a thinner e
crossbar. Stems and horizontals become one weight, and the o becomes an even ring.

## Type (oblique.so)

FK Grotesk since 2026-10-21. The contract holds the typeface and no size: Oblique's version 1 is
FK Grotesk at the body size Oblique chooses, and every level follows from that body by the rule
(small 0.618, body 1, subhead 1.618, heading 2 2.618, heading 1 4.236).

```bash
python3 -I scripts/golden_grid.py version --contract examples/oblique.golden.json --typeface "FK Grotesk" --body <chosen body>
python3 -I scripts/golden_grid.py scale --body <chosen body> --typeface "FK Grotesk"
```

The line heights logged on 2026-10-20 for the earlier typefaces (1.4, 1.1, 0.88) stay in the
contract as departures until they are rechecked with FK Grotesk.

## Colour (shares to aim for)

| part | share | colour |
|:---|---:|:---|
| dominant | 61.8 | white #FFFFFF with frost #F2F2EF surfaces |
| secondary | 23.6 | ink #0E0E14 and grey #55555E (text, lines) |
| accent | 14.6 | electric blue #1F2BFF takes 0.618 of this (9.0), red #E8262B and orange #FF8A1E share the rest, yellow #FFD60A rarely |

The ink is the heaviest colour and takes the smaller share, as the rule says.

## Page (oblique.so)

Wrap 1680, margin 20 at 1440 (1.25 rem). Golden columns inside 1400: content 855, side 524.
Hero at 1440 by 890 is a golden rectangle (0.618 within 1.1 percent at 1440 by 900), with the
headline on the upper band. Section gap `--section` clamps 96 to 304 px; the sequence values
nearest are 89 and 233, candidates if the site moves onto the sequence.

## Figma

Oblique's own plugin (`studio/figma/`) builds the style guide pages; the Golden grid plugin from
this skill is imported beside it and run on the Website page's desktop and phone frames.
