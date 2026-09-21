#!/usr/bin/env python3
"""Subset a built Iosevka plan into a symbol-only fallback for PlemolJP Console."""
import argparse
import sys
from pathlib import Path

from fontTools import unicodedata as ud
from fontTools.subset import Options, Subsetter
from fontTools.ttLib import TTFont

STYLES = {
    "Regular": ("Regular", 400, False, False),
    "Bold": ("Bold", 700, True, False),
    "Italic": ("Italic", 400, False, True),
    "BoldItalic": ("Bold Italic", 700, True, True),
}

MATH_LETTER_RANGES = [(0x2100, 0x214F), (0x1D400, 0x1D7FF), (0x1EE00, 0x1EEFF)]


def is_private_use(cp):
    return 0xE000 <= cp <= 0xF8FF or cp >= 0xF0000


def is_symbol(cp, math_letters):
    category = ud.category(chr(cp))
    if category[0] in "SPN":
        return True
    if math_letters and category[0] == "L":
        return any(a <= cp <= b for a, b in MATH_LETTER_RANGES)
    return False


def find_built(built_dir, suffix):
    hits = sorted(built_dir.rglob(f"*-{suffix}.ttf"))
    if len(hits) != 1:
        sys.exit(
            f"error: expected exactly one '*-{suffix}.ttf' under {built_dir}, "
            f"found {len(hits)}: {[str(h) for h in hits]}"
        )
    return hits[0]


def select(reference, donor, math_letters):
    ref_cmap = reference.getBestCmap()
    donor_cmap = donor.getBestCmap()
    donor_hmtx = donor["hmtx"]
    half = reference["hmtx"][ref_cmap[ord("A")]][0]
    keep = {
        c
        for c in donor_cmap
        if c > 0x7F
        and c not in ref_cmap
        and not is_private_use(c)
        and is_symbol(c, math_letters)
        and ud.east_asian_width(chr(c)) not in ("W", "F")
        and donor_hmtx[donor_cmap[c]][0] > 0
    }
    return half, keep


def apply_vertical_metrics(font, reference):
    ref_hhea, ref_os2 = reference["hhea"], reference["OS/2"]
    hhea, os2 = font["hhea"], font["OS/2"]
    hhea.ascent, hhea.descent, hhea.lineGap = (
        ref_hhea.ascent,
        ref_hhea.descent,
        ref_hhea.lineGap,
    )
    os2.sTypoAscender = ref_os2.sTypoAscender
    os2.sTypoDescender = ref_os2.sTypoDescender
    os2.sTypoLineGap = ref_os2.sTypoLineGap
    os2.usWinAscent = ref_os2.usWinAscent
    os2.usWinDescent = ref_os2.usWinDescent


def apply_names_and_style(font, family, suffix):
    style, weight, bold, italic = STYLES[suffix]
    ps = f"{family.replace(' ', '')}-{suffix}"
    names = font["name"]
    for name_id, value in (
        (1, family),
        (2, style),
        (3, f"{ps};subset"),
        (4, f"{family} {style}"),
        (6, ps),
    ):
        names.setName(value, name_id, 3, 1, 0x409)
    names.removeNames(nameID=16)
    names.removeNames(nameID=17)

    os2 = font["OS/2"]
    os2.usWeightClass = weight
    sel = os2.fsSelection & ~(0x01 | 0x20 | 0x40)
    if italic:
        sel |= 0x01
    if bold:
        sel |= 0x20
    if not (bold or italic):
        sel |= 0x40
    os2.fsSelection = sel
    font["head"].macStyle = (1 if bold else 0) | (2 if italic else 0)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--reference", required=True, type=Path)
    ap.add_argument("--built", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--family", default="PlemolJP Symbols")
    ap.add_argument("--no-math-letters", action="store_true")
    ap.add_argument("--allow-width-mismatch", action="store_true")
    args = ap.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    reference = TTFont(args.reference)
    donor = TTFont(find_built(args.built, "Regular"))
    half, keep = select(reference, donor, not args.no_math_letters)
    ref_cmap = reference.getBestCmap()
    print(f"reference half-width advance: {half}")
    print(f"keeping {len(keep)} codepoints missing in the reference")

    for suffix in STYLES:
        path = find_built(args.built, suffix)
        font = TTFont(path)

        options = Options()
        options.layout_features = []
        options.notdef_outline = True
        options.hinting = False
        subsetter = Subsetter(options)
        subsetter.populate(unicodes=sorted(keep))
        subsetter.subset(font)
        for table in font["cmap"].tables:
            table.cmap = {cp: g for cp, g in table.cmap.items() if cp in keep}

        advances = {w for w, _ in font["hmtx"].metrics.values()} - {0}
        if advances != {half}:
            msg = f"{path.name}: advances {sorted(advances)} do not match {half}"
            if not args.allow_width_mismatch:
                sys.exit("error: " + msg)
            print("warning: " + msg)

        overlap = set(font.getBestCmap()) & set(ref_cmap)
        if overlap:
            sys.exit(f"error: {path.name}: {len(overlap)} codepoints overlap the reference")

        apply_vertical_metrics(font, reference)
        apply_names_and_style(font, args.family, suffix)
        target = args.out / f"{args.family.replace(' ', '')}-{suffix}.ttf"
        font.save(target)
        print(f"wrote {target} ({target.stat().st_size // 1024} KiB, "
              f"{len(font.getBestCmap())} codepoints)")


if __name__ == "__main__":
    main()
