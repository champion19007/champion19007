"""Post-process the rendered github-profile-trophy SVG.

Two passes:
  1. Remap gruvbox's palette onto the README's Hallownest palette. The
     Action exposes only named themes (no custom hex), and none of the
     bundled ones match, so this is done after rendering.
  2. Drop "Unknown / 0pt" cards and reflow the row. The composite Action
     has no `rank` input -- that is a query param of the hosted service,
     not the Action -- so empty trophies are removed here instead.

Layout is a single row of fixed-width cards, so reflow is just
reassigning x at a constant pitch and shrinking the root width.
"""
import pathlib
import re
import sys

# Keyed to github-profile-trophy's own gruvbox theme (src/theme.ts at the
# pinned SHA) rather than reverse-engineered from a sample render. Reading
# the source matters here: #98971a looks like a rank colour in a render but
# is actually TEXT, and the real B rank is #d65d0e. Guessing from counts got
# both wrong and left S looking dimmer than the A ranks below it.
#
# The four rank bases are a single descending ramp so higher rank always
# reads brighter, matching the snake's contribution ramp.
# Keys are lowercase, matching theme.ts verbatim; lookup lowercases too.
PALETTE = {
    # chrome
    "#282828": "#0A0A0A",  # BACKGROUND (also DEFAULT_RANK_TEXT)
    "#ebdbb2": "#F0EDE5",  # TITLE + ICON_CIRCLE -> bone
    "#98971a": "#E0752D",  # TEXT (rank label) -> infection orange
    "#689d6a": "#8FB8C9",  # LAUREL -> ghost blue
    "#fabd26": "#E8C87A",  # NEXT_RANK_BAR -> pale gold

    # rank ramp, brightest first
    "#fabd2f": "#E8C87A",  # S_RANK_BASE / SHADOW
    "#83a598": "#E0752D",  # A_RANK_BASE / SHADOW
    "#d65d0e": "#C26426",  # B_RANK_BASE / SHADOW
    "#928374": "#8A4A1C",  # DEFAULT_RANK (C) BASE / SHADOW

    # rank label backplates -> near-void
    "#322301": "#151515",  # S_RANK_TEXT
    "#151e1a": "#0A0A0A",  # A_RANK_TEXT
    "#301503": "#151515",  # B_RANK_TEXT

    # secret ranks (unused today, mapped so they cannot leak gruvbox)
    "#fb4934": "#E0752D",
    "#d3869b": "#8FB8C9",
    "#458588": "#8FB8C9",
    "#b16286": "#F0EDE5",
}

CARD_W, PITCH = 115, 125
CARD_RE = re.compile(r'<svg\s+x="(\d+)"\s+y="0"')


def split_cards(svg):
    """Return (prefix, [card_html, ...], suffix) for the top-level cards."""
    starts = [m.start() for m in CARD_RE.finditer(svg)]
    if not starts:
        return svg, [], ""
    spans = []
    for st in starts:
        depth, i = 0, st
        while i < len(svg):
            if svg.startswith("<svg", i):
                depth += 1
                i += 4
            elif svg.startswith("</svg>", i):
                depth -= 1
                i += 6
                if depth == 0:
                    spans.append((st, i))
                    break
            else:
                i += 1
    return svg[:spans[0][0]], [svg[a:b] for a, b in spans], svg[spans[-1][1]:]


def main(path):
    p = pathlib.Path(path)
    svg = p.read_text(encoding="utf-8")

    svg = re.sub(r"#[0-9a-fA-F]{6}",
                 lambda m: PALETTE.get(m.group(0).lower(), m.group(0)), svg)

    prefix, cards, suffix = split_cards(svg)
    if not cards:
        sys.exit("no trophy cards found -- upstream SVG layout changed")

    kept = [c for c in cards if "Unknown" not in c]
    dropped = len(cards) - len(kept)
    if not kept:
        sys.exit("every trophy was Unknown -- refusing to emit an empty row")

    kept = [CARD_RE.sub(f'<svg x="{i * PITCH}" y="0"', c, count=1)
            for i, c in enumerate(kept)]

    width = (len(kept) - 1) * PITCH + CARD_W
    prefix = re.sub(r'width="\d+"', f'width="{width}"', prefix, count=1)
    prefix = re.sub(r'viewBox="0 0 \d+ (\d+)"', rf'viewBox="0 0 {width} \1"',
                    prefix, count=1)

    out = prefix + "".join(kept) + suffix
    p.write_text(out, encoding="utf-8")

    colors = sorted(set(re.findall(r"#[0-9a-fA-F]{6}", out)))
    print(f"kept {len(kept)} trophies, dropped {dropped} Unknown")
    print(f"width {width}, colors {colors}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "assets/trophy.svg")
