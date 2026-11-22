# Printing proxies for a sliding-blade paper trimmer

`mtg-proxies print --slider` makes a sheet for a manual paper trimmer with a
sliding blade carriage, such as a Fiskars SureCut or a similar trimmer. It
keeps the cards in a straight grid, prints mirrored bleed around every card,
and adds a straight cut line along every card edge. Each line runs from one
paper edge to the other, so the lines cross clearly at every card corner. They
run through the bleed and gutters and never cross the card art.

The mode is separate from `--handcut`, which also prints full-page lines but
uses an edge-to-edge layout without bleed, and is aimed at a guillotine or a
ruler and craft knife.

## Quick start

```bash
mtg-proxies print decklist.txt proxies.pdf --paper 8.5x11 --slider
```

Then:

1. Print on Letter paper at **100 % / Actual size**, portrait. Do not use
   **Fit to page**, **Scale to fit**, **Shrink oversized pages**, or borderless
   scaling.
2. Cut the six vertical lines first. Each line runs from the top paper edge to
   the bottom edge, so you can line up the blade at both ends. The two lines
   around each gutter are 4 mm apart with the default 2 mm bleed: cut along both
   and remove the narrow waste strip.
3. Rotate each strip and cut the six horizontal lines. These lines also span
   the whole sheet, so they remain on the strips after the vertical cuts. Stack
   the strips if your trimmer can hold them, or align each line against the
   fence.
4. Check the finished card against a real card. With the default border crop it
   is about 61.1 × 86.5 mm, so it slips into a sleeve in front of a real common.

## What the layout does

The layout maximizes the number of cards that fit while leaving room for the
bleed. On Letter with the default settings it fits **nine cards in a 3 × 3
grid**:

| Setting | Default |
|---|---|
| Paper | Letter, 215.9 × 279.4 mm |
| Grid | 3 × 3 (9 cards) |
| Finished card | 61.1 × 86.5 mm |
| Bleed | 2 mm mirrored, all four sides |
| Gutter between cards | 4 mm (twice the bleed) |
| Trim-grid margin | 12.3 mm left/right, 5.9 mm top/bottom |
| Corners | square |
| Cut guides | full-page lines on card edges |

The gutter is deliberately twice the bleed. Each card's bleed then occupies
one half of the gutter and never prints over a neighbouring card's face. The
two cut lines on either side of the gutter are the finished card edges.

If the paper, card size, bleed, or gap cannot fit nine cards, the tool uses the
largest grid that does fit; it does not shrink the cards. It prints the chosen
grid and margins when it starts.

The cut guides are straight lines on the card edges. Every vertical cut starts
at the top paper edge and ends at the bottom edge. Every horizontal cut spans
the full paper width. The lines cross at every card corner, which makes each
corner an obvious intersection rather than a tiny tick.

The lines sit exactly on the finished card edge. Where cards face a gutter, the
line runs through the mirrored bleed and the bare gutter, not across the card
art. The blade removes the line itself, so a cut along a line leaves a clean
card edge. Because the lines span the whole sheet, the perpendicular guides are
still present on each strip after the first set of cuts.

## Bleed and cut accuracy

Bleed is the extra printed image outside the finished card edge. If the blade
is a fraction of a millimetre off, you cut through printed artwork instead of
exposing white paper. The bleed is mirrored: the edge pixels of the card scan
are reflected outwards, so the extension looks like a natural continuation of
the card border.

The default 2 mm bleed is enough for normal trimmer accuracy. Increase it with
`--bleed 3` if you want more tolerance, but the wider gutters may reduce the
number of cards per sheet. Use `--bleed 0` to disable bleed; the mode then
behaves like handcut with a wider gutter when `--gap` is set.

```bash
# 3 mm bleed
mtg-proxies print decklist.txt proxies.pdf --paper 8.5x11 --slider --bleed 3

# full 63.5 x 88.9 mm card, 2 mm bleed
mtg-proxies print decklist.txt proxies.pdf --paper 8.5x11 --slider \
  --bleed 2 --border_crop 0

# full-size rounded card (e.g. for a 3 mm corner rounder)
mtg-proxies print decklist.txt proxies.pdf --paper 8.5x11 --slider \
  --bleed 2 --corner-radius 3
```

Rounded cards print at full size automatically, because a corner rounder does
not change the card's width or height; the border crop is only used for
square-cornered cards.

With `--border_crop 0` and 2 mm bleed, nine cards still fit on Letter, but the
top and bottom margins shrink to about 2.4 mm. Print a test page and check that
your printer does not clip the card edges. If it does, use a smaller bleed
(`--bleed 1`) or accept fewer cards.

`--gap` sets a minimum paper gap between finished card edges. The tool uses
the larger of `--gap` and twice the bleed. The CLI limit for `--gap` is 3 mm,
so on a bleed sheet the gutter is usually controlled by the bleed.

## Cutting order

For the default 3 × 3 sheet:

1. Put the sheet on the trimmer with the edge you want to keep against the
   fence. Align the blade with a vertical cut line at both the top and bottom
   paper edges.
2. Cut the leftmost line (the left edge of the first column), then the two
   lines around the first gutter, and so on. A 3-column sheet has six vertical
   cut lines: two outer edges and four edges around the two gutters.
3. Remove the narrow gutter strips. You now have three card strips.
4. Rotate a strip 90° and cut the six horizontal lines the same way. The
   left/right page margins are gone on the middle strip, but the horizontal
   lines still cross the full strip and provide a guide at both ends.
5. Repeat for the remaining strips.

The important measurement is the distance between the two lines of a gutter:
with 2 mm bleed it is 4 mm. The finished card is the distance between the outer
edges of two adjacent gutters, not the centre of the gutter.

If you prefer fewer, easier cuts, use `--bleed 0 --gap 0`. Cards are then edge
to edge with a single guide line between them, and one cut separates each pair.
You lose the bleed protection at the cut edge.

## Paper and printer settings

- Use **matte** paper. Glossy paper is slippery in a trimmer and can show roller
  marks.
- **200–250 gsm cardstock** gives the best feel in a sleeve. **110 lb / 200 gsm**
  is easier to cut and is fine inside a sleeve.
- Printable sticker paper also works: trim the sheet, peel, and stick each
  proxy onto a bulk common.
- Set the printer to **Actual size / 100 %**, Letter, portrait. Check the scale
  with a ruler before cutting a full deck.
- If the printer clips the outer bleed, that is harmless: bleed is waste. If it
  clips the trim line itself, reduce the bleed or use six cards per page.

## Previewing the guides

Render page 1 without printing a full deck:

```bash
pdftoppm -f 1 -l 1 -r 150 -png proxies.pdf preview
```

The preview should show card art running into the gutters, with a straight cut
line along every card edge. The lines should cross at each card corner and run
all the way to the paper edges.

## Differences from the other modes

| | `--slider` | `--handcut` | `--makercraft` |
|---|---|---|---|
| Cut guide | Full-page lines on card edges, with bleed | Full-page lines on card edges | Camera marks |
| Bleed | 2 mm by default | 0 by default | 0 by default |
| Cards per Letter page | 9 | 9 | 6 |
| Corners | Square by default | Square by default | Rounded by default |
| Extra file | None by default | None by default | `makercraft.plt` |
| Cut with | Sliding-blade trimmer | Guillotine, rotary trimmer, knife | Skycut C10 |

`--slider` cannot be combined with `--handcut` or `--makercraft`.
