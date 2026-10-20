# Handover and balance

The reason this skill exists: the ratio sets up a template, and a person edits it afterwards.
This file says how to leave the work so that happens, and how to judge balance when the numbers
and the eye disagree.

## Leave it as a template

- **Illustrator.** Grid on a locked layer named "Golden grid". The artwork on its own layer above.
  Every part a named group (Rectangle, Squares, Circles, Spiral, Eye, Phi lines, Notes, and for
  the mark: Box, Letters, Margins or whatever the parts are). A Notes text in the file with the
  values, the date and the departures.
- **Figma.** A locked "Golden grid" group per frame size, guides set, the Golden variables
  collection bound to type and spacing, a "Golden notes" text layer, components for keylines and
  card ratios.
- **Code.** The CSS variables from `golden_grid.py scale --format css`, with the base size as the
  only hand-edited number; a comment at the top naming the ratio and the date.
- **Everywhere.** The before-and-after measurement table from `proportion_check.py`, so the next
  person sees what moved and what was left alone.

A template that someone can edit without asking is the measure of done.

## Hierarchy by phi

One dominant, one secondary, everything else a step down. Apply it to the three channels at
once:

| channel | dominant | secondary | the rest |
|:---|:---|:---|:---|
| type | one display size on the page | one subhead size | body and labels |
| colour | 61.8 percent surface | 23.6 percent structure | 14.6 percent accent |
| space | the 0.618 column or hero | the 0.382 column or bar | gaps from the sequence |

When a page feels busy, one of the channels has two dominants. Find it, demote one by a phi
step, and the page settles. When a page feels flat, the dominant and the secondary are less than
a phi step apart.

## When the numbers and the eye disagree

The eye wins. The ratio is a setup, and optical correction is finishing: round letters overshoot,
horizontals look thinner than verticals of the same weight, centred things look low, a square
looks wide. Keep the correction, and write it down as a departure with its reason, so the next
designer does not "fix" it back to the number.

What a departure note looks like: `hero line height 0.88 (table says 1.0): display caps read as a
block and 1.0 left a visible gap`. One line, the value, the reason.

## Tolerance

3 percent either side of the ratio is on, the working tolerance of this skill (no published
threshold exists). Up to 6 percent is near, worth a look and usually
worth a nudge. Beyond that is a choice: either the concept needs it (keep it, note it) or it is
drift (fix it). The default tolerance lives in `proportion_check.py --tolerance`.

## When to leave the ratio out

- A mark whose idea is a specific angle, a specific squareness or a deliberate imbalance. The
  ratio tidies the surroundings and leaves the idea alone.
- A grid system already in place (a client's design system, a platform's spacing scale). Map the
  ratio onto it where it fits and stop there.
- A layout that is one block of text: measure and leading matter, columns do not.

Say in the notes that the ratio was considered and where it was set aside.
