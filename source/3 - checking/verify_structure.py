#!/usr/bin/env python3
"""Vérifie la structure (livres, chapitres, versets) de F35_MES.txt."""

import re
import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
MES_PATH = os.path.join(SCRIPT_DIR, "../../../F35_MES.txt")
ST_PATH = os.path.join(SCRIPT_DIR, "../2 - adding_diamond/ST.txt")


def load_refs(path):
    verses = {}
    with open(path, encoding="utf-8") as f:
        for line in f:
            m = re.match(r"^(\d{2})(\d{3})(\d{3})\s", line)
            if m:
                bk, ch, vs = int(m.group(1)), int(m.group(2)), int(m.group(3))
                verses[(bk, ch, vs)] = line.strip()
    return verses


def verify():
    errors = 0
    mes = load_refs(MES_PATH)
    st = load_refs(ST_PATH)

    # 1. Total lines
    print(f"Lignes: {len(mes)} (ST: {len(st)})", end="")
    if len(mes) != len(st):
        print(f"  ✗ (devrait être {len(st)})")
        errors += 1
    else:
        print("  ✓")

    # 2. Books
    mes_books = sorted({k[0] for k in mes})
    st_books = sorted({k[0] for k in st})
    print(f"Livres: {len(mes_books)} ({mes_books[0]}-{mes_books[-1]})", end="")
    if mes_books != st_books:
        print(f"  ✗ ST={st_books} MES={mes_books}")
        errors += 1
    else:
        print("  ✓")

    # 3. Chapters & verses per book
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
        if st_chs != mes_chs:
            print(f"  {bk:02d} {name}: chapitres ✗ ST={st_chs} MES={mes_chs}")
            errors += 1
            continue
        ok = True
        for ch in st_chs:
            st_vs = sorted([k[2] for k in st if k[0] == bk and k[1] == ch])
            mes_vs = sorted([k[2] for k in mes if k[0] == bk and k[1] == ch])
            if st_vs != mes_vs:
                missing = sorted(set(st_vs) - set(mes_vs))
                extra = sorted(set(mes_vs) - set(st_vs))
                print(f"    {ch:03d}: {len(st_vs)}v attendu, {len(mes_vs)}v trouvé ✗", end="")
                if missing:
                    print(f"  manque: {missing}", end="")
                if extra:
                    print(f"  extra: {extra}", end="")
                print()
                errors += 1
                errors_ch += 1
                ok = False
        if ok:
            total_vs = sum(len([k[2] for k in st if k[0] == bk and k[1] == ch]) for ch in st_chs)
            print(f"  {bk:02d} {name}: {len(st_chs)} ch, {total_vs} v  ✓")
    if errors_ch == 0:
        print("  Tous les chapitres: nombre de versets correct ✓")

    # 4. Empty verses
    mes_empty = sum(1 for v in mes.values() if v.endswith(" -"))
    st_empty = sum(1 for v in st.values() if v.endswith(" -"))
    print(f"Versets vides (MES): {mes_empty}")
    if mes_empty > 0:
        empty_refs = sorted([k for k, v in mes.items() if v.endswith(" -")])
        print(f"  {' '.join(f'{b:02d}:{c:03d}:{v:03d}' for b, c, v in empty_refs)}")

    # 5. Diamond markers
    mes_diamonds = sum(v.count("⋄") for v in mes.values())
    diamond_lines = [k for k, v in mes.items() if "⋄" in v]
    print(f"Marqueurs ⋄: {mes_diamonds} (sur {len(diamond_lines)} lignes)")
    for bk, ch, vs in diamond_lines:
        print(f"  {bk:02d}:{ch:03d}:{vs:03d} ({mes[(bk, ch, vs)].count('⋄')} ⋄)")

    print()
    if errors:
        print(f"❌ {errors} erreur(s)")
        return False
    else:
        print("✅ VÉRIFICATION PASSÉE")
        return True


if __name__ == "__main__":
    ok = verify()
    sys.exit(0 if ok else 1)
