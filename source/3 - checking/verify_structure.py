#!/usr/bin/env python3
"""
Verify that F35_MES.txt has exactly the same verse structure as ST.txt.

Checks performed:
  - Total line count matches the Stephanus reference.
  - Book range is NT-only (40-66) and matches ST.
  - Every chapter contains exactly the same verse numbers as ST.
  - Empty verses are listed.
  - Diamond markers are enumerated.

Usage:
    python verify_structure.py
"""

import re
import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
MES_PATH = os.path.join(SCRIPT_DIR, "../../../F35_MES.txt")
ST_PATH = os.path.join(SCRIPT_DIR, "../2 - adding_diamond/ST.txt")


def load_refs(path):
    """
    Load a bbcccvvv file and return a dict of (book, ch, vs) -> full_line.

    Only the reference prefix (bbcccvvv) is parsed; the text is stored as-is.
    """
    verses = {}
    with open(path, encoding="utf-8") as f:
        for line in f:
            m = re.match(r"^(\d{2})(\d{3})(\d{3})\s", line)
            if m:
                bk = int(m.group(1))
                ch = int(m.group(2))
                vs = int(m.group(3))
                verses[(bk, ch, vs)] = line.strip()
    return verses


def verify():
    errors = 0
    mes = load_refs(MES_PATH)
    st = load_refs(ST_PATH)

    # ------------------------------------------------------------------
    # 1. Total line count
    # ------------------------------------------------------------------
    print(f"Lines: {len(mes)} (ST: {len(st)})", end="")
    if len(mes) != len(st):
        print(f"  ✗ (expected {len(st)})")
        errors += 1
    else:
        print("  ✓")

    # ------------------------------------------------------------------
    # 2. Book range
    # ------------------------------------------------------------------
    mes_books = sorted({k[0] for k in mes})
    st_books = sorted({k[0] for k in st})
    print(f"Books: {len(mes_books)} ({mes_books[0]}-{mes_books[-1]})", end="")
    if mes_books != st_books:
        print(f"  ✗ ST={st_books} MES={mes_books}")
        errors += 1
    else:
        print("  ✓")

    # ------------------------------------------------------------------
    # 3. Per-chapter verse counts
    # ------------------------------------------------------------------
    errors_ch = 0
    BOOK_NAMES = {
        40: "MAT", 41: "MRK", 42: "LUK", 43: "JHN", 44: "ACT",
        45: "ROM", 46: "1CO", 47: "2CO", 48: "GAL", 49: "EPH",
        50: "PHP", 51: "COL", 52: "1TH", 53: "2TH", 54: "1TI",
        55: "2TI", 56: "TIT", 57: "PHM", 58: "HEB", 59: "JAS",
        60: "1PE", 61: "2PE", 62: "1JN", 63: "2JN", 64: "3JN",
        65: "JUD", 66: "REV",
    }
    for bk in st_books:
        st_chs = sorted({k[1] for k in st if k[0] == bk})
        mes_chs = sorted({k[1] for k in mes if k[0] == bk})
        name = BOOK_NAMES.get(bk, str(bk))
        # Check that the set of chapters is identical.
        if st_chs != mes_chs:
            print(f"  {bk:02d} {name}: chapters ✗ ST={st_chs} MES={mes_chs}")
            errors += 1
            continue
        print(f"  {bk:02d} {name}:")
        for ch in st_chs:
            st_vs = sorted([k[2] for k in st if k[0] == bk and k[1] == ch])
            mes_vs = sorted([k[2] for k in mes if k[0] == bk and k[1] == ch])
            if st_vs != mes_vs:
                missing = sorted(set(st_vs) - set(mes_vs))
                extra = sorted(set(mes_vs) - set(st_vs))
                print(f"    {ch:03d}: {len(st_vs)}v expected, {len(mes_vs)}v found ✗", end="")
                if missing:
                    print(f"  missing: {missing}", end="")
                if extra:
                    print(f"  extra: {extra}", end="")
                print()
                errors += 1
                errors_ch += 1
            else:
                print(f"    {ch:03d}: {len(mes_vs)}v  ✓")
    if errors_ch == 0:
        print("  All chapters: verse count correct ✓")

    # ------------------------------------------------------------------
    # 4. Empty verses (marked with "-" instead of text)
    # ------------------------------------------------------------------
    mes_empty = sum(1 for v in mes.values() if v.endswith(" -"))
    st_empty = sum(1 for v in st.values() if v.endswith(" -"))
    print(f"Empty verses (MES): {mes_empty}")
    if mes_empty > 0:
        empty_refs = sorted([k for k, v in mes.items() if v.endswith(" -")])
        refs_str = " ".join(
            f"{b:02d}:{c:03d}:{v:03d}" for b, c, v in empty_refs
        )
        print(f"  {refs_str}")

    # ------------------------------------------------------------------
    # 5. Diamond (⋄) markers — show where F35 splits ST verses differently
    # ------------------------------------------------------------------
    mes_diamonds = sum(v.count("⋄") for v in mes.values())
    diamond_lines = [k for k, v in mes.items() if "⋄" in v]
    print(f"Diamond markers ⋄: {mes_diamonds} (on {len(diamond_lines)} lines)")
    for bk, ch, vs in diamond_lines:
        print(f"  {bk:02d}:{ch:03d}:{vs:03d} ({mes[(bk, ch, vs)].count('⋄')} ⋄)")

    print()
    if errors:
        print(f"❌ {errors} error(s)")
        return False
    else:
        print("✅ VERIFICATION PASSED")
        return True


if __name__ == "__main__":
    ok = verify()
    sys.exit(0 if ok else 1)
