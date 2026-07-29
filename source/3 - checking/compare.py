#!/usr/bin/env python3
"""Extract plain text (no refs, no diamonds) from F35_MES.txt and readaloud,
then compare them."""

import re
import os
import glob

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
MES_PATH = os.path.join(SCRIPT_DIR, "../../../F35_MES.txt")
READALOUD_DIR = os.path.join(SCRIPT_DIR, "../1 - format_f35/source/readaloud")
OUT_DIR = SCRIPT_DIR


def extract_from_mes(path):
    with open(path, encoding="utf-8") as f:
        lines = f.readlines()
    parts = []
    for line in lines:
        line = re.sub(r"^\d{8} ", "", line.strip())
        if line == "-":
            continue
        line = re.sub(r"⋄\d+", "", line)
        parts.append(line.strip())
    return " ".join(parts)


def extract_from_readaloud(directory):
    all_files = sorted(glob.glob(os.path.join(directory, "grcf35_*.txt")))
    # Exclude book 000 (metadata/readme file)
    all_files = [f for f in all_files if not os.path.basename(f).startswith("grcf35_000_")]

    def sort_key(p):
        m = re.search(r"grcf35_(\d{3})_\w+_(\d+)_read", os.path.basename(p))
        return (int(m.group(1)), int(m.group(2))) if m else (0, 0)

    all_files.sort(key=sort_key)
    parts = []
    for fpath in all_files:
        with open(fpath, encoding="utf-8") as f:
            lines = f.readlines()
        for line in lines[2:]:
            line = line.strip()
            if line:
                parts.append(line)
    return " ".join(parts)


if __name__ == "__main__":
    mes_text = extract_from_mes(MES_PATH)
    ra_text = extract_from_readaloud(READALOUD_DIR)

    out_mes = os.path.join(OUT_DIR, "f35_from_mes.txt")
    out_ra = os.path.join(OUT_DIR, "f35_from_readaloud.txt")

    with open(out_mes, "w", encoding="utf-8") as f:
        f.write(mes_text + "\n")
    with open(out_ra, "w", encoding="utf-8") as f:
        f.write(ra_text + "\n")

    mes_norm = re.sub(r"\s+", "", mes_text)
    ra_norm = re.sub(r"\s+", "", ra_text)

    print(f"MES: {len(mes_text):>8} chars, {len(mes_norm)} normalized")
    print(f"RA:  {len(ra_text):>8} chars, {len(ra_norm)} normalized")

    if mes_norm == ra_norm:
        print("\nIDENTIQUES ✓")
    else:
        print("\nDIFFÉRENTS ✗")
