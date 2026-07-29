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
import re


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

    ref_nonempty_indices = [
        i for i, (_, t) in enumerate(ref_verses) if t != "-"
    ]

    for i, (ref_ref, ref_text) in enumerate(ref_verses):
        if ref_text == "-":
            lines.append(f"{ref_ref} -")
            continue

        if f35_idx >= len(f35_verses):
            lines.append(f"{ref_ref} -")
            continue

        f35_ref, f35_text = f35_verses[f35_idx]
        f35_idx += 1

        is_last_nonempty = (i == ref_nonempty_indices[-1])

        if is_last_nonempty and len(f35_verses) > len(ref_verses):
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
    parser.add_argument("--input", default="F35.txt", help="F35 bbcccvvv file")
    parser.add_argument("--sr", default="ST.txt", help="Stephanus reference file")
    parser.add_argument("--output", default="F35_MES.txt", help="Output file")
    args = parser.parse_args()

    print(f"Loading F35 from: {args.input}")
    f35_data = load_verses(args.input)

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

    with open(args.output, "w", encoding="utf-8", newline="\n") as f:
        for line in lines:
            f.write(line + "\n")

    print(f"Wrote {len(lines)} lines to {args.output}")


if __name__ == "__main__":
    main()
