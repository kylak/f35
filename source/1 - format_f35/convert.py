#!/usr/bin/env python3
"""Convert f35 Greek New Testament readaloud files to bbcccvvv format.

Reads the chapter-by-chapter plain-text files in source/readaloud/
and produces a single F35.txt with each line in the format:

    bbcccvvv verse_text

where bb = book number (40-66 for NT), ccc = chapter, vvv = verse.

Usage:
    python convert.py [--readaloud-dir PATH] [--output FILE]

The --readaloud-dir defaults to ../source/readaloud relative to this script.
The --output defaults to F35.txt in the current directory.
"""

import argparse
import glob
import os
import re
import sys


# ---------------------------------------------------------------------------
# Mapping: f35 file number → standard Protestant book number
#
# The readaloud files are named  grcf35_{NNN}_{ABBR}_{CC}_read.txt
# where NNN is an f35-internal book number:
#
#     070 MAT →  40  Matthew
#     071 MRK →  41  Mark
#     072 LUK →  42  Luke
#     073 JHN →  43  John
#     074 ACT →  44  Acts
#     075 ROM →  45  Romans
#     076 1CO →  46  1 Corinthians
#     077 2CO →  47  2 Corinthians
#     078 GAL →  48  Galatians
#     079 EPH →  49  Ephesians
#     080 PHP →  50  Philippians
#     081 COL →  51  Colossians
#     082 1TH →  52  1 Thessalonians
#     083 2TH →  53  2 Thessalonians
#     084 1TI →  54  1 Timothy
#     085 2TI →  55  2 Timothy
#     086 TIT →  56  Titus
#     087 PHM →  57  Philemon
#     088 HEB →  58  Hebrews
#     089 JAS →  59  James
#     090 1PE →  60  1 Peter
#     091 2PE →  61  2 Peter
#     092 1JN →  62  1 John
#     093 2JN →  63  2 John
#     094 3JN →  64  3 John
#     095 JUD →  65  Jude
#     096 REV →  66  Revelation
#
# Formula:  book = f35_number - 30
# ---------------------------------------------------------------------------


F35_MIN = 70   # Matthew
F35_MAX = 96   # Revelation


def f35_to_book(f35_num: int) -> int:
    """Map an f35 file number to a standard Protestant book number."""
    return f35_num - 30


def process_readaloud(readaloud_dir: str) -> list[str]:
    """Read all readaloud files and return verse lines in bbcccvvv format.

    Each readaloud file contains one chapter of one book:
        Line 1:   book title (ignored)
        Line 2:   chapter number (ignored)
        Line 3+:  one verse per line (cleaned plain text)

    The files are processed in alphabetical order (which is the canonical
    NT book order), and verses within each file are processed sequentially.
    """
    pattern = os.path.join(readaloud_dir, "grcf35_*_*_*_read.txt")
    files = sorted(glob.glob(pattern))

    if not files:
        print("No readaloud files found in", readaloud_dir, file=sys.stderr)
        sys.exit(1)

    verses: list[str] = []

    for filepath in files:
        basename = os.path.basename(filepath)
        # Parse: grcf35_070_MAT_01_read.txt
        m = re.match(r"grcf35_(\d+)_([A-Z0-9]+)_(\d+)_read\.txt", basename)
        if not m:
            continue

        f35_num = int(m.group(1))
        if f35_num < F35_MIN or f35_num > F35_MAX:
            continue  # skip non-NT files (e.g. the 000 info file)

        chap_num = int(m.group(3))
        book = f35_to_book(f35_num)

        book_s = str(book).zfill(2)
        chap_s = str(chap_num).zfill(3)

        with open(filepath, encoding="utf-8") as fh:
            lines = fh.readlines()

        # Lines 1-2 are title / chapter header; everything from line 3 is verse text
        for i, line in enumerate(lines[2:], start=1):
            text = line.strip()
            if not text:
                continue
            verse_s = str(i).zfill(3)
            verses.append(f"{book_s}{chap_s}{verse_s} {text}")

    return verses


def main() -> None:
    parser = argparse.ArgumentParser(description="Convert f35 readaloud → bbcccvvv format")
    parser.add_argument(
        "--readaloud-dir",
        default=os.path.join(os.path.dirname(__file__), "..", "source", "readaloud"),
        help="Path to the readaloud directory (default: ../source/readaloud)",
    )
    parser.add_argument(
        "--output",
        default="F35.txt",
        help="Output file name (default: F35.txt)",
    )
    args = parser.parse_args()

    readaloud_dir = os.path.abspath(args.readaloud_dir)
    print(f"Reading from: {readaloud_dir}")

    verses = process_readaloud(readaloud_dir)

    outpath = os.path.abspath(args.output)
    with open(outpath, "w", encoding="utf-8", newline="\n") as fh:
        for verse in verses:
            fh.write(verse + "\n")

    print(f"Wrote {len(verses)} verses to {outpath}")


if __name__ == "__main__":
    main()
