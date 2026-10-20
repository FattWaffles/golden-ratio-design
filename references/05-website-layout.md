# Website layout

Read `01-ratio-basics.md` first. This file is the page grid: columns, the hero, spacing, where
the first thing goes.

## The page grid

`golden_grid.py page --width 1440 --height 900 --out page.svg` draws it: phi lines at 0.382 and
0.618 of the width and height, the four crossings, the content and side columns, the hero
rectangle, and a spacing ruler. Drop the SVG on a Figma frame, or set the lines as guides with
the Figma plugin.

| element | rule | 1440 wide, 34 margin, 21 gutter |
|:---|:---|---:|
| content column | 0.618 of inner width, minus half the gutter | 837 |
| side column | the rest | 514 |
| hero | inner width / phi, capped at the inner height (900 minus 68 = 832); at 1440 by 900 the cap wins, so the hero is 832 tall and 832 times phi wide | 1346 by 832 |
| phi lines x | 0.382 and 0.618 of the page | 550, 890 |
| phi lines y | 0.382 and 0.618 of the viewport | 344, 556 |
| spiral eye | 0.724 of the hero's width and height | (1008, 636) |

The 21-column trick: a 21-column grid with no gutter puts the golden split on a column edge
(13 columns are 61.9 percent). Use it in Figma when you want snapping rather than guides.

## The hero

The first screen is a golden rectangle when the viewport allows it (1440 by 890 is one, 1920 by
1187, 390 by 631 on a phone). Put the headline or the one image on the spiral's eye or the
nearest phi crossing. Headline size from the type scale: step 5 or 6 at desktop, step 3 or 4 on
a phone. Keep 0.382 of the hero as air; a hero that is 80 percent type reads as a poster, which
is sometimes the point.

## Spacing

One sequence for the whole site: 8 13 21 34 55 89 144 233 (or 4 6 10 16 26 42 68 110 for a tight
product site). Gutters 21, card padding 21 or 34, section gaps 89 to 233, margins 34 at desktop
and 21 on a phone. Spacing that comes from one sequence is what makes a page feel designed
rather than assembled.

## Sections

Alternate section heights at phi: a 610 section, a 377 section, a 610, with the 0.382 share as
space. Within a section, the text block is 0.618 of the width on wide screens and full width
below 720 px. Stack order on a phone follows the reading order of the desktop grid, content
column first.

## Images

Image frames at 1 : 1.618 (landscape) or 1.618 : 1 (portrait); squares for products and
avatars. Crop so the subject sits on the spiral's eye of the frame, which is the same rule
photographers use. Image to text width at 0.618 : 0.382 in a two-column row.

## Checks before handover

- Content and side columns, hero height, section heights: on or near with
  `proportion_check.py`.
- Spacing values all from the one sequence (grep the stylesheet for px values; strays show up).
- The headline sits within 3 percent of the eye or a phi crossing.
- Mobile: the first screen is the portrait golden rectangle and the headline is on its eye
  (0.276 of the width, 0.724 of the height, spiral turning the same way).
- Every departure written in the page's design note.
