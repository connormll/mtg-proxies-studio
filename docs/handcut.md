# Printing proxies for hand cutting

`mtg-proxies print --handcut` makes a PDF that you cut with a guillotine, a
rotary paper trimmer, or a ruler and craft knife. It does not need a cutting
machine or registration marks.

For a manual trimmer with a sliding blade, prefer
[`--slider`](slider.md): it adds mirrored bleed and runs the full-page cut
lines along the card edges with a wider gutter, instead of an edge-to-edge
layout.

## Quick start

```bash
mtg-proxies print decklist.txt proxies.pdf --paper 8.5x11 --handcut
```

Then:

1. Print the PDF at **100 % / Actual size** on Letter paper. Do not use
   **Fit to page**, **Scale to fit**, **Shrink oversized pages**, or borderless
   scaling.
2. Cut along the thin black lines. Each line runs from one paper edge to the
   other, so it stays visible after the sheet has been divided into strips.
3. Cut the four vertical lines first, then rotate the strips and cut the four
   horizontal lines. A guillotine or rotary trimmer gives the most consistent
   edges.
4. If you use `--corner-radius 2.5`, round the four corners with a 2.5 mm corner
   punch after trimming.

The lines run along the card boundaries, so they are removed by the cut itself.
They do not print across the card artwork.

## What the handcut layout does

Without `--handcut`, the PDF uses the normal print layout: rounded card
corners, the standard grid, and a companion SVG cut file. MakerCraft mode adds
registration marks and uses six cards on Letter so the camera has clear space
around them.

With `--handcut` the tool:

- Uses the **largest grid that fits** the paper. On Letter this is nine cards
  in a 3 × 3 grid; on A4 it is also nine cards.
- Sets `--gap 0` by default, so cards are **edge to edge**. One straight cut
  separates two neighbouring cards, and the whole sheet comes apart with four
  vertical and four horizontal cuts.
- Sets `--corner-radius 0` by default. Square corners are what a straight
  trimmer produces. An explicit `--corner-radius` still works, but the printed
  card art will then have rounded corners while the cut card is square; use a
  corner punch to remove the white corner triangles.
- Adds **thin black cut lines** along every card edge. Each line runs from one
  paper edge to the other, so it remains visible on the strips after the first
  cuts.
- Skips the SVG cut file unless you explicitly pass `--cut-file`.

The finished card size is controlled by `--border_crop`, exactly as in a normal
print. The default of 14 source pixels trims the outer border of the scan and
gives a finished size of about **61.1 × 86.5 mm**. That proxy fits in a sleeve
in front of a real common card. For a full **63.5 × 88.9 mm** card, use
`--border_crop 0`.

## Cutting order

For a 3 × 3 sheet with no gap:

1. Cut along each of the four vertical lines. You can stack the resulting
   strips if your trimmer has a tall fence, but cut one at a time if the paper
   shifts.
2. Rotate each strip 90° and cut along the four horizontal lines. The lines
   run across the whole strip, so each piece still has a guide.
3. Check one card against a real card. A trimmed proxy should be a little
   smaller than a real card with the default border crop.

On the last page, only the lines around the cards that actually exist are
printed; empty slots are not cut.

## Paper and printer settings

- Use **matte** paper. Glossy paper is slippery in a trimmer and shows roller
  marks.
- **200–250 gsm cardstock** gives the best feel in a sleeve but may need a
  trimmer with a strong blade. **110 lb / 200 gsm** is easier to cut and is fine
  inside a sleeve.
- Printable sticker paper also works: trim the sheet, peel, and stick each
  proxy onto a bulk common. Cut with a fresh blade and a light pass to avoid
  cutting through the backing.
- Set the printer to **Actual size / 100 %**, Letter, portrait. Check the
  printer's scale with a ruler before cutting a full deck: print page 1, measure
  a card, and confirm it is about 61.1 × 86.5 mm with the default crop (or
  63.5 × 88.9 mm with `--border_crop 0`).
- If your printer cannot print close to the edge, the outer ends of the lines
  may be clipped. The lines still extend inward and remain aligned with the
  cut, so trim with a straight edge if a line is short. If an entire line is
  missing, use a printer with smaller margins.

## A small gap instead of zero

If your trimmer is hard to align, or you want a little more tolerance, use a
gap:

```bash
mtg-proxies print decklist.txt proxies.pdf --paper 8.5x11 --handcut --gap 1.5
```

The cards are then 1.5 mm apart. The tool prints **two lines** around each
gutter, one on each card's finished edge. Cut along both lines and remove the
1.5 mm strip. That keeps every card at the exact finished size. If you cut once
down the middle of the gutter instead, each card will be about 0.75 mm wider.

A gap of 1–2 mm is usually easiest to handle with a rotary trimmer. `--gap 0`
gives the fewest cuts and the most cards per sheet.

## Differences from MakerCraft mode

| | `--handcut` | `--slider` | `--makercraft` |
|---|---|---|---|
| Cut guide | Printed cut lines | Printed cut lines with bleed | Four camera registration marks |
| Bleed | 0 by default | 2 mm by default | 0 by default |
| Cards per Letter page | 9 (3 × 3) | 9 (3 × 3) | 6 (3 × 2) |
| Corners | Square by default | Square by default | Rounded by default |
| Extra file | None by default | None by default | `makercraft.plt` |
| Cut with | Trimmer, guillotine, knife | Sliding-blade trimmer | Skycut C10 / MakerCraft |

`--handcut`, `--slider`, and `--makercraft` cannot be combined.

## Generating a preview

To check the lines without printing a full deck, render page 1:

```bash
pdftoppm -f 1 -l 1 -r 150 -png proxies.pdf preview
```

The black lines should follow the card edges and run all the way to the page
edges.

## Troubleshooting

- **No lines visible:** make sure `--handcut` was passed and the output is a
  PDF. The lines are thin; some PDF viewers hide hairlines at low zoom.
- **A line is offset from the card edge:** the PDF is being printed scaled or
  borderless. Reprint at 100 % / Actual size.
- **Cards are not the size you expected:** check `--border_crop`. The default
  crop of 14 gives 61.1 × 86.5 mm; `--border_crop 0` gives 63.5 × 88.9 mm.
- **The last page has one card and only two lines each way:** that is
  intentional. The lines only cover the cards that exist on the page.
- **Edges are ragged:** use a sharper blade or a guillotine. A rotary trimmer
  with a fresh blade and a slow, steady pass works well on 200 gsm cardstock.
