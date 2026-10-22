# Figma

How the construction lands in Figma so that the file is a template a designer edits later.

## Three ways in

1. **The plugin** (`figma/` in this skill). Plugins > Development > Import plugin from manifest,
   pick `figma/manifest.json`. Three commands:
   - Golden grid on selection: rectangle, squares, circles, phi lines, spiral and eye as a locked
     group named "Golden grid W x H" around whatever is selected.
   - Phi guides and 21-column grid on selected frames: ruler guides at 0.382 and 0.618 of width
     and height, plus a 21-column layout grid with no gutter so the golden split (13 + 8) sits on
     column edges.
   - Golden variables: a "Golden" collection with space/1 to space/8 (8 13 21 34 55 89 144 233),
     type/small, type/body, type/subhead, type/heading-2 and type/heading-1 (0.618, 1, 1.618,
     2.618 and 4.236 times the body), and ratio/phi. The body is the size of the one text layer
     selected when the command runs, otherwise the collection's type/body. No size is assumed:
     with neither, the command stops and asks for one. Running it again updates the collection in
     place, so the trigger after choosing a new body is: change type/body (or select a text layer
     at the new body size), run the command. Every text layer bound to the type variables follows.
   The plugin is written against the Plugin API without a UI and was not yet run inside Figma by
   the author; if a command fails, the error shows as a toast and nothing is changed. If the import
   complains about the manifest id, create a new plugin once (Plugins > Development > New plugin),
   copy the numeric id Figma generates into `figma/manifest.json`, and keep it.
2. **SVG import.** `golden_grid.py grid` and `page` write SVGs with named groups. Drag one onto a
   frame; it arrives as a group with the same names (golden-rectangle, squares, spiral, circles,
   phi-lines, eye, notes). Lock it.
3. **The free Golden Spiral community plugin** draws the spiral alone, for a quick overlay.

## Working with it

- Keep the grid group locked and at the top of the layer list, named with its size. One grid per
  frame size; duplicate it with the frame.
- Build on variables: type sizes and spacing bound to the Golden collection, so changing the
  body size later moves the whole system. The body is the one number to edit.
- Components for the keyline icon grid and for the card ratios (1 : 1.618 lying and standing,
  1 : 1). Icons and images are placed inside them.
- Layout grids are for snapping; guides are for seeing. Use both, hide both before presenting.

## Checking a Figma file

Export the frame as SVG and run `proportion_check.py --svg` for the frame, sections and cards,
then add the type sizes by hand with `--pairs`. The report goes into a "Golden notes" text layer
in the frame, with any departure and its reason, so the next person finds the thinking in the
file.

## Handover note template

Put this in a text layer named "Golden notes" on each page:

```
Golden grid: 1440 x 890 (desktop), 390 x 631 (phone)
Type: <typeface>, version <n>, body <size>; levels 0.618 1 1.618 2.618 4.236 x body
Spacing: 8 13 21 34 55 89
Colour shares: white 61.8, ink 23.6, accents 14.6
Departures: hero line height 0.88 (display reads as shape); card gap 24 (component library)
Checked: 2026-10-20 with proportion_check.py, tolerance 3 percent
```
