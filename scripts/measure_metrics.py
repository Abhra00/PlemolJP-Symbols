#!/usr/bin/env python3
"""Measure PlemolJP metrics and (optionally) compare them with a built font.

usage:
  measure_metrics.py PlemolJP-Regular.ttf [PlemolJPSymbols-Regular.ttf]

With one argument it prints the values used in private-build-plans.toml.
With two it prints a side-by-side table so you can see how far the Iosevka
build is from PlemolJP and adjust `metricOverride` accordingly. CI runs the
two-argument form and prints it in the log; it never fails the build.
"""
import sys

from fontTools.pens.boundsPen import BoundsPen
from fontTools.ttLib import TTFont


def measure(path):
    font = TTFont(path)
    glyphs, cmap = font.getGlyphSet(), font.getBestCmap()

    def bounds(ch):
        pen = BoundsPen(glyphs)
        glyphs[cmap[ord(ch)]].draw(pen)
        return pen.bounds

    hhea = font["hhea"]
    paren, hyphen, pipe = bounds("("), bounds("-"), bounds("|")
    return {
        "upm": font["head"].unitsPerEm,
        "advance (A)": font["hmtx"][cmap[ord("A")]][0],
        "cap (H top)": bounds("H")[3],
        "xHeight (x top)": bounds("x")[3],
        "ascender (b top)": bounds("b")[3],
        "symbolMid (- centre)": (hyphen[1] + hyphen[3]) / 2,
        "paren height ( )": paren[3] - paren[1],
        "leading (hhea)": hhea.ascent - hhea.descent + hhea.lineGap,
        "italicAngle": font["post"].italicAngle,
        "hyphen thickness": hyphen[3] - hyphen[1],
        "pipe stem width": pipe[2] - pipe[0],
    }


def main():
    if len(sys.argv) not in (2, 3):
        sys.exit(__doc__)
    ref = measure(sys.argv[1])
    built = measure(sys.argv[2]) if len(sys.argv) == 3 else None

    width = max(len(k) for k in ref)
    if built:
        print(f"{'':{width}}  {'PlemolJP':>10}  {'built':>10}  {'diff':>8}")
        for key, value in ref.items():
            other = built[key]
            print(f"{key:{width}}  {value:>10.1f}  {other:>10.1f}  {other - value:>+8.1f}")
    else:
        for key, value in ref.items():
            print(f"{key:{width}}  {value:>10.1f}")
        print("\nSuggested [metricOverride] (Iosevka draws '(' about 36 taller than parenSize):")
        print(f"cap = {ref['cap (H top)']:.0f}")
        print(f"ascender = {ref['ascender (b top)']:.0f}")
        print(f"xHeight = {ref['xHeight (x top)']:.0f}")
        print(f"symbolMid = {ref['symbolMid (- centre)']:.0f}")
        print(f"parenSize = {ref['paren height ( )'] - 36:.0f}")
        print(f"leading = {ref['leading (hhea)']:.0f}")


if __name__ == "__main__":
    main()
