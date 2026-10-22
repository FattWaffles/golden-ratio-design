# Typography and font deciding

Read `01-ratio-basics.md` first. This file covers the type scale, line height, measure, spacing
and how to choose and pair fonts with the ratio as the referee.

## Sizing type from the hero

This is the default way to size the type hierarchy, and the hero is the one number a project
sets. Nothing else is fixed: change the hero and every other size is generated again from it.

1. Set the hero first.
2. Divide it by 1.618 for the sub hero. It can pass for body, but it reads as the second level.
3. Divide by 1.618 again. That is body: the hero divided twice by 1.618.
4. Keep dividing for small and micro, and multiply once for display.
5. In Figma or Illustrator, type the division straight into the font size field: `/1.618`, then
   Enter. Or let the tools do it: the contract holds `hero`, `golden_grid.py scale --hero N`
   prints the ladder, the CSS tokens derive from `--type-hero`, and the Figma plugin rebuilds
   the Golden variables from the selected hero layer.

Example: hero 75, sub hero 46, body 29. Hero 68: sub hero 42, body 26. Hero 62: sub hero 38,
body 24.

The sizes are written as ratios of body (body 1, sub hero 1.618, hero 2.618) because body is
what text is measured against; the hero still sets them. A contract that holds only a body
still loads and works from the bottom up. Whole steps only; the half step in the next section is
an option for in-between sizes.

## The scale

Every size is a ratio of the body size of the chosen typeface. One body per typeface: a second
face used only for display takes its sizes from the main body; a face with running text of its
own gets its own contract copy and body. Run `golden_grid.py scale --hero 76` (or `--body 29`)
for the table, `--format css` for tokens.

| level | x body | body 16 | body 29 |
|:---|---:|---:|---:|
| micro | 0.382 | 6 | 11 |
| small | 0.618 | 10 | 18 |
| body | 1 | 16 | 29 |
| sub hero | 1.618 | 26 | 47 |
| hero | 2.618 | 42 | 76 |
| display | 4.236 | 68 | 123 |

Phi is a big step. It gives a strong hierarchy with few sizes, which suits editorial and brand
work. Whole steps only: the rule divides by 1.618 and nothing else, so no size sits between body
and sub hero. The half step, 1.272, stays in the skill as a line-height stop. A contract can turn
it on for type with `half_steps: true` (off since version 2) when a product interface needs
in-between sizes; write that choice down.

Round to whole pixels in interfaces and to the nearest half point in print. Rounding to the
nearest pixel breaks the ratio by less than 2 percent from body 16 up. A 6 px micro is below
legibility, so micro labels at body 16 use 7 or 8 and count as a departure.

## Line height

Three stops, from the same number:

| text | line height | why |
|:---|---:|:---|
| body | 1.618 | long lines need air; the ratio's own leading |
| sub hero, lead | 1.272 | shorter lines; the square root of phi, between body and display |
| display | 1.0 (down to 0.88) | big type reads as shape; leading becomes a gap |

These stops are this skill's own system. The usual ranges are 1.4 to 1.6 for body, 1.1 to 1.3 for
headings and about 1.0 for display, and the stops sit inside them.

Fonts with a large x-height (most sans) can take body at 1.5, which is 7 percent under the ratio:
outside the tolerance, so write it down as a departure. Fonts with a small x-height (Garamond and its relatives) often look
right at 1.4 with a bigger size: measure the x-height, set the size so the x-height matches what
a sans would give at 16, then take the leading from the table.

## Measure (line length)

45 to 75 characters per line, 66 as the target (Bringhurst's range). On a page with a sidebar
the text column is 0.618 of the content width and the measure usually lands inside the range by
itself. Check it with the font's own average character width: 34 em is about 65 characters for a font
averaging 0.52 em per character (most sans) and about 90 for a narrow old-style serif such as EB
Garamond (0.38 em). Count a real line rather than converting.

## Spacing around type

Paragraph space, heading space above and below, margins: take them from the sequence in the same
unit as the body size. The run is the same whatever the body: 8 below a paragraph (or a full
line), 21 to 34 above a heading, 13 below it. The rule that keeps pages readable: space above a heading is bigger than
space below it, by one step of the sequence.

## Choosing fonts with the ratio

The ratio cannot pick a font. It can tell you whether two fonts belong together and how to set
them.

1. **Roles first.** Display (headlines), editorial (body and long reading), utility (labels,
   numbers, interface). Two fonts cover most brands; three is the limit.
2. **Contrast by phi.** The display font should sit at least one full phi step above body
   wherever they meet (16 body, 26 or bigger where the two fonts meet; 42, two steps, is where a
   display font usually first appears), and
   the utility font one whole step below body, at 0.618. If the pairing only works when the sizes
   are close, the fonts are too alike or too different; change one.
3. **Match x-heights at body size.** Set both candidate fonts at the same cap height and compare
   x-heights. Match them by eye: if they differ visibly, give the smaller x-height font a bigger
   size (the ratio of their x-heights tells you how much). Ten percent is this skill's working
   tolerance, with no published source.
4. **Weight steps.** The weights used across the brand should come from one family of ratios:
   stem widths at 1, 1.618, 2.618 of the lightest. Variable fonts let you set this exactly; fixed
   weights usually give Light, Regular, Bold as the nearest three.
5. **Test at the eye.** Put the headline on the spiral's eye of the page grid at the display
   size, body in the 0.618 column, labels in the 0.382 column. If the hierarchy reads in one
   glance, the pairing works.

## Tokens

`golden_grid.py scale --hero 76 --format css` writes `--type-hero: 76px` and derives every other
token from it with `calc()` and `--type-ratio`, so editing that one line in the stylesheet moves
`--type-sub-hero`, `--type-body`, `--type-small`, `--type-micro` and `--type-display` with it.
Each token carries its ratio of body and its px in a comment; `--static` writes fixed rem values
instead. The three leading values and `--space-1` to `--space-8` follow. The lint reads every
font size back as a ratio of the contract's body: 47 px reports as 1.62 x body, sub hero, and
23 px as off, between small and body. `golden_lint.py --hero 68` checks a file against a changed
hero without editing the contract.
