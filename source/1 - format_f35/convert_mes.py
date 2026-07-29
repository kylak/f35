#!/usr/bin/env python3
"""Convert F35.txt to MES format with Stephanus 1551 versification.

Takes the F35 Greek New Testament (bbcccvvv format) and re-aligns its verse
references to follow the Stephanus 1551 versification. Where the F35 text
has different verse boundaries, ⋄ markers are inserted.

Usage:
    python convert_mes.py --input F35.txt --sr ST.txt --output F35_MES.txt

Verse alignment strategy:
  - Empty verses (content = '-') become '-' in the output.
  - For each non-empty verse, consume the next available F35 verse.
  - If F35 still has verses left after the last non-empty verse,
    merge them with ⋄ markers into that last verse.
"""

import argparse
import os
import re
import sys


def load_verses(filepath):
    """Load a bbcccvvv file into {(book, chapter): [(ref, text)]}."""
    verses = {}
    with open(filepath, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            m = re.match(r"^(\d{2})(\d{3})(\d{3})\s+(.*)", line)
            if not m:
                continue
            bk, ch, vs, txt = m.group(1), m.group(2), m.group(3), m.group(4)
            ref = bk + ch + vs
            key = (bk, ch)
            verses.setdefault(key, []).append((ref, txt))
    return verses


def align_chapter(f35_verses, ref_verses):
    """Align F35 verses to Stephanus 1551 structure for one chapter.

    Returns list of formatted lines:  ['bbcccvvv text', ...]
    """
    lines = []
    f35_idx = 0

    # First pass: process ST verses left-to-right, consuming F35 verses 1:1.
    # Track which verse indexes are non-empty.
    ref_nonempty_indices = [
        i for i, (_, t) in enumerate(ref_verses) if t != "-"
    ]

    for i, (ref_ref, ref_text) in enumerate(ref_verses):
        if ref_text == "-":
            lines.append(f"{ref_ref} -")
            continue

        if f35_idx >= len(f35_verses):
            # No more F35 content for this SR verse
            lines.append(f"{ref_ref} -")
            continue

        # Consume one F35 verse
        f35_ref, f35_text = f35_verses[f35_idx]
        f35_idx += 1

        # Check if this is the last non-empty verse
        is_last_nonempty = (i == ref_nonempty_indices[-1])

        if is_last_nonempty and len(f35_verses) > len(ref_verses):
            # Merge all remaining F35 verses into this last SR verse
            merged = f35_text
            while f35_idx < len(f35_verses):
                extra_ref, extra_text = f35_verses[f35_idx]
                merged += f" ⋄{extra_ref[-3:].lstrip('0')}{extra_text}"
                f35_idx += 1
            lines.append(f"{ref_ref} {merged}")
        else:
            lines.append(f"{ref_ref} {f35_text}")

    return lines


def main():
    parser = argparse.ArgumentParser(
        description="Convert F35 to MES format (Stephanus 1551 versification)"
    )
    parser.add_argument("--input", default=None, help="F35 bbcccvvv file (default: auto-generate)")
    parser.add_argument(
        "--readaloud-dir",
        default=os.path.join(os.path.dirname(__file__), "..", "source", "readaloud"),
    )
    parser.add_argument(
        "--sr",
        default=os.path.join(os.path.dirname(__file__), "..", "examples", "ST.txt"),
    )
    parser.add_argument("--output", default="F35_MES.txt")
    args = parser.parse_args()

    if args.input:
        print(f"Loading F35 from: {args.input}")
        f35_data = load_verses(args.input)
    else:
        sys.path.insert(0, os.path.dirname(__file__))
        from convert import process_readaloud

        print(f"Generating F35 from readaloud: {args.readaloud_dir}")
        raw_lines = process_readaloud(args.readaloud_dir)
        f35_data = {}
        for line in raw_lines:
            m = re.match(r"^(\d{2})(\d{3})(\d{3})\s+(.*)", line)
            if m:
                bk, ch, vs, txt = m.group(1), m.group(2), m.group(3), m.group(4)
                key = (bk, ch)
                f35_data.setdefault(key, []).append((bk + ch + vs, txt))

    print(f"Loading Stephanus structure from: {args.sr}")
    ref_structure = load_verses(args.sr)

    print("Aligning verses to Stephanus 1551 versification...")
    lines = []

    book_keys = sorted({bk for (bk, _) in ref_structure}, key=lambda x: int(x))

    for bk in book_keys:
        chapters = sorted(
            {int(ch) for (b, ch) in ref_structure if b == bk},
        )
        for ch in chapters:
            ch_pad = f"{ch:03d}"
            ref_verses = ref_structure.get((bk, ch_pad), [])
            f35_verses = f35_data.get((bk, ch_pad), [])

            if not ref_verses:
                continue

            chapter_lines = align_chapter(f35_verses, ref_verses)
            lines.extend(chapter_lines)

    outpath = os.path.abspath(args.output)
    with open(outpath, "w", encoding="utf-8", newline="\n") as f:
        for line in lines:
            f.write(line + "\n")

    print(f"Wrote {len(lines)} lines to {outpath}")


if __name__ == "__main__":
    main()
