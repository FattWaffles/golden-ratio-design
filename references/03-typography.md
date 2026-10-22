# Typography and font deciding

Read `01-ratio-basics.md` first. This file covers the type rule, line height, measure, spacing
and how to choose and pair fonts with the ratio as the referee.

## The type rule

The body size of the chosen typeface is 1. Every other level is a ratio of it:

| level | x body |
|:---|---:|
| small text | 0.618 |
| body | 1 |
| subheads | 1.618 |
| heading 2 | 2.618 |
| heading 1 | 4.236 |

- **Whole steps of 1.618 only.** Each level is the one below it times 1.618, so a heading divided
  by 1.618 is a subhead, and a subhead divided by 1.618 is body.
- **No size is set.** Whatever body size the designer chooses, every level follows from it. Pixel
  sizes appear only as a calculated column: `golden_grid.py scale --body N`.
- **Versions.** One typeface plus its body size is a version. Changing the typeface or the body
  size makes a new version: `golden_grid.py version --contract FILE --typeface NAME --body N`
  records it in the contract's history and prints the tag for the repo.
- **By hand.** In Figma or Illustrator, type the step straight into the font size field:
  `/1.618` or `*1.618`, then Enter.

One body per typeface: a second face used only for headings takes its levels from the main
body; a face with running text of its own gets its own contract copy and its own versions.

Phi is a big step. It gives a strong hierarchy with few levels, which suits editorial and brand
work. The half step, 1.272, stays in the skill as a line-height stop. A contract can turn it on
for type with `half_steps: true` (off since version 2) when a product interface needs in-between
levels; write that choice down.

Round to whole pixels in interfaces and to the nearest half point in print.

## Line height

Three stops, from the same number:

| text | line height | why |
|:---|---:|:---|
| body | 1.618 | long lines need air; the ratio's own leading |
| subheads, lead | 1.272 | shorter lines; the square root of phi |
| headings | 1.0 (down to 0.88) | big type reads as shape; leading becomes a gap |

These stops are this skill's own system. The usual ranges are 1.4 to 1.6 for body, 1.1 to 1.3 for
headings and about 1.0 for display, and the stops sit inside them.

Fonts with a large x-height (most sans) can take body at 1.5, which is 7 percent under the ratio:
outside the tolerance, so write it down as a departure. Fonts with a small x-height (Garamond and
its relatives) often look right at 1.4 with a bigger body: compare the x-height with a large
x-height sans at the same size, raise the chosen body by the ratio of the two, then take the
leading from the table.

## Measure (line length)

45 to 75 characters per line, 66 as the target (Bringhurst's range). On a page with a sidebar
the text column is 0.618 of the content width and the measure usually lands inside the range by
itself. Check it with the font's own average character width: 34 em is about 65 characters for a font
averaging 0.52 em per character (most sans) and about 90 for a narrow old-style serif such as EB
Garamond (0.38 em). Count a real line rather than converting.

## Spacing around type

Paragraph space, heading space above and below, margins: take them from the sequence. The run is
the same whatever the body: 8 below a paragraph (or a full line), 21 to 34 above a heading, 13
below it. The rule that keeps pages readable: space above a heading is bigger than space below it,
by one step of the sequence.

## Choosing fonts with the ratio

The ratio cannot pick a font. It can tell you whether two fonts belong together and how to set
them.

1. **Roles first.** Display (headlines), editorial (body and long reading), utility (labels,
   numbers, interface). Two fonts cover most brands; three is the limit.
2. **Contrast by phi.** The display font should sit at least one full step above body wherever
   they meet (a subhead, 1.618, or bigger; heading 2, 2.618, is where a display font usually
   first appears), and the utility font one whole step below body, at 0.618. If the pairing only
   works when the sizes are close, the fonts are too alike or too different; change one.
3. **Match x-heights at body size.** Set both candidate fonts at the same cap height and compare
   x-heights. Match them by eye: if they differ visibly, give the smaller x-height font a bigger
   size (the ratio of their x-heights tells you how much). Ten percent is this skill's working
   tolerance, with no published source.
4. **Weight steps.** The weights used across the brand should come from one family of ratios:
   stem widths at 1, 1.618, 2.618 of the lightest. Variable fonts let you set this exactly; fixed
   weights usually give Light, Regular, Bold as the nearest three.
5. **Test at the eye.** Put the headline on the spiral's eye of the page grid at a heading level,
   body in the 0.618 column, labels in the 0.382 column. If the hierarchy reads in one glance, the
   pairing works.

## Tokens

`golden_grid.py scale --body N --format css` writes `--type-body` as the one number to edit and
derives `--type-small`, `--type-subhead`, `--type-heading-2` and `--type-heading-1` from it with
`calc()` and `--type-ratio`, so changing that one line moves every level. Each token carries its
ratio of body in a comment; `--static` writes fixed rem values instead. The three leading values
and `--space-1` to `--space-8` follow.

The lint reads every font size as a ratio of the contract's body and names its level, or the two
levels it falls between. With no body in the contract it reports type as unchecked;
`golden_lint.py --body N` checks a file against a chosen body without editing the contract.
