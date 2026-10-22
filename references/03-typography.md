# Typography and font deciding

Read `01-ratio-basics.md` first. This file covers the type scale, line height, measure, spacing
and how to choose and pair fonts with the ratio as the referee.

## Sizing type from the headline (Will Paterson's rule)

Source: Will Paterson, "How to Use the Golden Ratio in Graphic Design!", about 3:10 to 4:45
(`09-video-notes.md`). In the Pro tip at 9:12 he says sizing type is the main way he uses the
ratio at work. This is the default way to size headline, subtitle and body.

1. Set the headline first.
2. Divide it by 1.618 for the next size down. This can work, but it usually reads as a subtitle.
3. Divide by 1.618 again. That is body. In his words, the headline "divided it twice by 1.618".
4. In Figma or Illustrator, type the division straight into the font size field: `/1.618`, then
   Enter.

His example: headline 75, subtitle 46, body 29.

As ratios of body: body 1, subtitle 1.618, headline 2.618. If the body size is already chosen,
multiply instead: body 18 gives 29 and 47. Both directions land on the scale below.

The headline here is the heading that sits with the body text. Bigger display sizes, such as a
hero, keep stepping up from it by 1.618 (body 18: hero 76, three steps up). His rule uses whole
steps; the half step in the next section is this skill's own option for in-between sizes.

## The scale

One base size, multiplied and divided by phi. Run `golden_grid.py scale --base 16` for the table
or `--format css` for tokens.

| step | 16 px base | role |
|---:|---:|:---|
| -2 | 6.1 | micro (use 7 or 8 in practice) |
| -1 | 9.9 | small, captions, labels |
| 0 | 16 | body |
| 1 | 25.9 | lead paragraph, h4 |
| 2 | 41.9 | h3 |
| 3 | 67.8 | h2 |
| 4 | 109.7 | h1 |
| 5 | 177.4 | display |
| 6 | 287.1 | hero |

Phi is a big step. It gives a strong hierarchy with few sizes, which suits editorial and brand
work. When a product interface needs more sizes between body and heading, use the half step,
1.272 (the square root of phi), so two half steps still equal one phi step and the system stays
whole: `--ratio root-phi`. Phone screens usually want the half step for headings and the full
step only for display.

Round to whole pixels in interfaces and to the nearest half point in print. Rounding to the
nearest pixel breaks the ratio by less than 2 percent across this table; the 7 or 8 micro label is
a legibility floor, 15 to 31 percent off, and counts as a departure.

## Line height

Three stops, from the same number:

| text | line height | why |
|:---|---:|:---|
| body | 1.618 | long lines need air; the ratio's own leading |
| subheads, lead | 1.272 | shorter lines, one half step tighter |
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
unit as the body size. With body 16: 8 below a paragraph (or a full line, 26), 21 to 34 above a
heading, 13 below it. The rule that keeps pages readable: space above a heading is bigger than
space below it, by one step of the sequence.

## Choosing fonts with the ratio

The ratio cannot pick a font. It can tell you whether two fonts belong together and how to set
them.

1. **Roles first.** Display (headlines), editorial (body and long reading), utility (labels,
   numbers, interface). Two fonts cover most brands; three is the limit.
2. **Contrast by phi.** The display font should sit at least one full phi step above body
   wherever they meet (16 body, 26 or bigger where the two fonts meet; 42, two steps, is where a
   display font usually first appears), and
   the utility font at least one half step below body. If the pairing only works when the sizes
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

`golden_grid.py scale --base 16 --format css` writes `--step-n2` to `--step-6`, the three leading
values and `--space-1` to `--space-8` as CSS variables, ready for a stylesheet or a Figma
variables import. Keep the base size as the one editable number; everything else follows.
