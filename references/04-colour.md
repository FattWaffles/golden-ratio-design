# Colour balance

Read `01-ratio-basics.md` first. The ratio does two jobs in colour: it sets how much of each
colour appears, and it can choose a hue when the palette needs a new one.

## Shares

The classic rule is 60 / 30 / 10. This skill's golden version is 61.8 / 23.6 / 14.6: the whole split at
the golden section, then the smaller part split again. Run `golden_grid.py shares --parts 3`.

| part | share | what it is |
|:---|---:|:---|
| dominant | 61.8% | background and large surfaces, usually the lightest or quietest colour |
| secondary | 23.6% | text, structure, the colour that carries the reading |
| accent | 14.6% | the brand's loud colour, links, buttons, the one thing on the page that is red |

Two colours: 61.8 / 38.2. Four: 61.8 / 23.6 / 9.0 / 5.6 (keep splitting the last part).

Measure shares by area on a finished page or board. Counting swatches misleads: a tiny red button
on a white page is a 1 percent share, which is fine for an accent and wrong for a secondary.

## Weight

Dark and saturated colours weigh more. The heavier colour takes the smaller share: a palette
with a near-black and an electric blue puts the black in the 23.6 and the blue in the 14.6, and
the page stays mostly light. Flip it for a dark brand: near-black dominant, light secondary, the
accent unchanged. A working rule of this skill: the accent is the one colour under 15 percent of
the area, and it carries most of the places where someone has to act.

## Choosing a hue by the angle

When the palette needs one more colour and nothing in the brief decides it, step 137.5 degrees
(the golden angle) around the hue wheel from the dominant hue. A handful of hues picked this way
(up to five or six) spread evenly and stay distinct. This is a programmer's trick for generating
distinct hues; it has no standing in colour theory, and the brief wins when it has a view. Use
HSL or OKLCH hue; keep lightness and chroma from the existing palette so the new colour matches
the family.

## Tints and shades

A ramp of tints or shades steps by phi in lightness distance from the base. For a base at
lightness 50: 50, 69, 81, 88 up and 50, 31, 19, 12 down (each step closes 0.382 of the remaining
distance to white or black, so the steps themselves shrink by phi: 19, 12, 7). The ramp looks
evenly spaced to the eye; a linear ramp looks bunched at one end.

## Checks

- Shares: dominant, secondary and accent measured by area, within the 3 percent tolerance of
  61.8 / 23.6 / 14.6 or 61.8 / 38.2.
- Weight: the heaviest colour is not the dominant one, unless the brand is deliberately dark.
- Contrast is a separate rule and wins every time: text colours must pass contrast before the
  ratio has a say. Contrast findings stay in the working notes.
