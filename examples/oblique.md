# Worked example: Oblique

The numbers from the Oblique brand and oblique.so, checked against the ratio with the scripts in
this skill. Verdicts use the 3 percent tolerance. Nothing here is a change; it is the measurement
table that a rebalance starts from.

## Logo (V1, box lean upright)

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

## Type (oblique.so, body 18 px)

| token | px | against body | nearest | verdict |
|:---|---:|---:|:---|:---|
| label | 11 | 0.611 | 0.618 | on |
| small | 14 | 0.778 | 0.786 (half step) | on |
| body | 18 | 1 | 1 | base |
| big (clamp) | 26 to 38 | 1.44 to 2.11 | 1.618 and 2.618 would be 29 and 47 | between steps |
| hero | 142 at 1440 wide | 7.9 | 6.85 (phi^4) and 11.1 (phi^5) | between steps, set by headline width |

Line heights: body 1.4 (EB Garamond's small x-height, a noted departure from 1.618), big 1.1,
hero 0.88 (display reads as shape). Measure: the 18 px body paragraphs run 18 em or 46 percent,
about 48 characters; the practice paragraphs at small (14 px) run 34 em, about 90 characters in
EB Garamond (0.376 em per character), above the 75 ceiling. 28 em would land at 75 and 25 em at 66.

Roles: Gloock display, EB Garamond editorial, Martian Mono utility, Oblique Trace Heavy for the
word oblique at 0.8 em in running text.

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
