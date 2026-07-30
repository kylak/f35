#!/usr/bin/env python3
"""
Extract the raw Greek text from F35_MES.txt and from the original readaloud
source files, then compare them to verify that no text was altered during the
formatting and alignment pipeline.

Output:
  - f35_from_mes.txt        — plain text extracted from F35_MES.txt
  - f35_from_readaloud.txt  — plain text extracted from the readaloud files

Both files contain the entire Greek New Testament as a single line, with all
reference numbers and diamond markers stripped out.
"""

import re
import os
import glob

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
MES_PATH = os.path.join(SCRIPT_DIR, "../../../F35_MES.txt")
READALOUD_DIR = os.path.join(SCRIPT_DIR, "../1 - format_f35/source/readaloud")
OUT_DIR = SCRIPT_DIR


def extract_from_mes(path):
    """
    Read a bbcccvvv file and return all verse texts joined by spaces.

    Strips:
      - the 8-digit reference prefix
      - empty-verse markers ('-')
      - diamond markers and their verse numbers (e.g. ⋄14, ⋄24)
    """
    with open(path, encoding="utf-8") as f:
        lines = f.readlines()
    parts = []
    for line in lines:
        # Remove the leading reference (e.g. "40001001 ").
        text = re.sub(r"^\d{8} ", "", line.strip())
        # Skip empty verse markers.
        if text == "-":
            continue
        # Remove diamond markers (e.g. ⋄14, ⋄24).
        text = re.sub(r"⋄\d+", "", text)
        parts.append(text.strip())
    return " ".join(parts)


def extract_from_readaloud(directory):
    """
    Read all readaloud chapter files and return their verse texts joined.

    Each file has the format:
      Line 1: Book title (e.g. "ΕΥΑΓΓΕΛΙΟΝ ΚΑΤΑ ΜΑΤΘΑΙΟΝ.")
      Line 2: Chapter number (e.g. "1.")
      Line 3+: One verse per line.

    We skip the first two lines (title and chapter number) and collect
    everything from line 3 onward.

    Files are sorted first by book number (070-096, extracted from the
    filename) and then by chapter number within each book.
    """
    all_files = sorted(glob.glob(os.path.join(directory, "grcf35_*.txt")))
    # Exclude book 000 (a metadata / readme file, not actual Bible text).
    all_files = [
        f for f in all_files
        if not os.path.basename(f).startswith("grcf35_000_")
    ]

    def sort_key(p):
        """Extract (book_number, chapter_number) from a filename like
        grcf35_070_MAT_01_read.txt."""
        m = re.search(r"grcf35_(\d{3})_\w+_(\d+)_read", os.path.basename(p))
        return (int(m.group(1)), int(m.group(2))) if m else (0, 0)

    all_files.sort(key=sort_key)

    parts = []
    for fpath in all_files:
        with open(fpath, encoding="utf-8") as f:
            lines = f.readlines()
        # Lines 0 and 1 are the book title and chapter number — skip them.
        for line in lines[2:]:
            line = line.strip()
            if line:
                parts.append(line)

    return " ".join(parts)


if __name__ == "__main__":
    mes_text = extract_from_mes(MES_PATH)
    ra_text = extract_from_readaloud(READALOUD_DIR)

    # Write the two plain-text versions to disk.
    out_mes = os.path.join(OUT_DIR, "f35_from_mes.txt")
    out_ra = os.path.join(OUT_DIR, "f35_from_readaloud.txt")

    with open(out_mes, "w", encoding="utf-8") as f:
        f.write(mes_text + "\n")
    with open(out_ra, "w", encoding="utf-8") as f:
        f.write(ra_text + "\n")

    # Normalise by removing all whitespace for a character-by-character comparison.
    mes_norm = re.sub(r"\s+", "", mes_text)
    ra_norm = re.sub(r"\s+", "", ra_text)

    print(f"MES: {len(mes_text):>8} chars, {len(mes_norm)} normalised")
    print(f"RA:  {len(ra_text):>8} chars, {len(ra_norm)} normalised")

    if mes_norm == ra_norm:
        print("\nIDENTICAL ✓")
    else:
        print("\nDIFFERENT ✗")
