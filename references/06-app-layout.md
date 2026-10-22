# App layout

Read `01-ratio-basics.md` and `05-website-layout.md` first. Phones and tablets are the same
rules at a different size, with touch as the extra constraint.

## The phone frame

`golden_grid.py page --width 390 --height 844 --margin 21 --gutter 13` draws it. A 390-wide
screen holds a portrait golden rectangle of 390 by 631: that is the first screen before the user
scrolls, and the 213 px below it (a quarter of the screen) is where tab bars and primary buttons live.

| element | rule | 390 by 844, margin 21, gutter 13 |
|:---|:---|---:|
| first screen | portrait golden rectangle, full width | 390 by 631 (348 by 563 inside margins) |
| spiral eye | 0.276 of width, 0.724 of height | (108, 457) on the full-width 390 by 631; (117, 428) on the 348 by 563 inside the margins, which is what the page script draws |
| phi lines x | 0.382, 0.618 of width | 149, 241 |
| phi lines y | 0.382, 0.618 of height | 322, 522 |
| content and side | 0.618 : 0.382 of inner width | 209, 126 |

The eye on a phone sits low left, which is where thumbs rest and where the primary action
usually belongs. The title and the first card go on the upper phi line (0.382 of height).

## Spacing and touch

One sequence: 8 13 21 34 55 89. Touch targets at 55 (above the platform minimums of 44 and 48),
list rows at 55 or 89, card padding 21, gaps 13, screen margins 21 (13 on small phones, 34 on
tablets). Buttons: height 55, horizontal padding 21 or 34, corner radius 8 or 13.

## Cards and tiles

Card ratio 1 : 1.618 lying down for media cards, standing for posters and products, square for
avatars and app icons. Inside a card: image takes 0.618 of the height, text the 0.382, or the
other way round for text-led cards. A two-up tile grid at 0.618 : 0.382 widths gives one lead
tile and one support tile per row, which reads better than two equal tiles.

## Type on a phone

Body 16 or 17, whole steps: sub hero 26 or 28, hero 42 or 45, and the display size (68 or 72)
only for the one number or title on a screen. Line height 1.5 for body (7 percent under the
ratio, fine at short measures; note it as a departure), 1.272 for the sub hero, 1.0 for the
display size. Measure on a phone is set by the margins; check it stays above 45 characters at
body size.

## Icon grid

App icons and interface icons share a keyline grid: 24-unit square, inner circle at 0.618 of the
square, golden rectangles for wide and tall shapes. Draw the grid as a locked component in Figma
and keep every icon inside it; `02-logo-and-icon.md` has the construction.

## Figma values to type in

- Frame 390 by 844. Guides at x 149 and 241, y 322 and 522 (the plugin's guides command sets them).
- Auto layout padding 21, gap 13 (lists) or 21 (cards), 34 between sections.
- Layout grid: 21 columns, no gutter, so the 13 and 8 column edges give the golden split.
- Variables from the plugin's "Golden" collection: space/1 to space/8, type/label to type/display.

## Checks

- First screen is the golden rectangle and the primary action sits on or near the eye.
- Every spacing value is in the sequence.
- Touch targets at 44 or above, 55 preferred.
- Card ratios on the ratio within 3 percent, or square.
