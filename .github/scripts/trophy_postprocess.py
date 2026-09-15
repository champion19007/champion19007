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

PALETTE = {
    "#282828": "#0A0A0A", "#151E1A": "#0A0A0A", "#301503": "#151515",
    "#EBDBB2": "#F0EDE5", "#E1E4E8": "#F0EDE5",
    "#98971A": "#E0752D", "#D65D0E": "#E0752D", "#FB4934": "#E0752D",
    "#FABD26": "#E8C87A", "#FABD2F": "#E8C87A",
    "#83A598": "#8FB8C9", "#689D6A": "#8FB8C9", "#458588": "#8FB8C9",
    "#D3869B": "#8FB8C9", "#B16286": "#8FB8C9",
    "#928374": "#6B7280",
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
                 lambda m: PALETTE.get(m.group(0).upper(), m.group(0)), svg)

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
