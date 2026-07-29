#!/usr/bin/env python3
"""Step 2: Improve F35_MES with all missing ⋄ markers.

Detects verse-boundary differences between F35 and Stephanus 1551 (ST.txt)
by comparing F35 text against ST text for each chapter, then adds ⋄ markers
where F35 divides verses differently than Stephanus.

Usage:
    python convert_step2.py --f35 F35.txt --st ST.txt --output F35_MES.txt
"""

import argparse
import re
import unicodedata


def load_verses(filepath):
    verses = {}
    with open(filepath, encoding="utf-8") as f:
        for line in f:
            m = re.match(r"^(\d{2})(\d{3})(\d{3})\s+(.*)", line)
            if m:
                bk, ch, vs = int(m.group(1)), int(m.group(2)), int(m.group(3))
                key = (bk, ch, vs)
                verses[key] = (f"{bk:02d}{ch:03d}{vs:03d}", m.group(4))
    return verses


def rough(t):
    """Normalize Greek text for comparison: strip diacritics, punctuation, case."""
    t = re.sub(r'[.,:;!?\-—()\[\]«»"\'··\s]', '', unicodedata.normalize('NFD', t.lower()))
    return ''.join(c for c in t if unicodedata.category(c) != 'Mn')


def _rough_char(c):
    """Rough-normalize a single character for position tracking."""
    c = unicodedata.normalize('NFD', c.lower())
    return ''.join(ch for ch in c if unicodedata.category(ch) != 'Mn' and (ch.isalpha() or ch.isdigit()))


def split_at_st(f35_text, st_next_text):
    """Split f35_text at the boundary where the next ST verse begins.

    Returns (before, after) — before stays in current ST verse,
    after is carryover for the next ST verse.
    Returns (f35_text, '') if boundary not found.
    """
    if not st_next_text or st_next_text == '-':
        return f35_text, ''

    f35_key = rough(f35_text)

    st_key = rough(st_next_text)[:30]
    if not st_key:
        return f35_text, ''

    def _find_pos(needle):
        return f35_key.find(needle)

    pos = _find_pos(st_key)
    if pos <= 0:
        # Try with nu-movable variants: insert optional ν after ε/ι before consonant
        pat_parts = []
        for i, c in enumerate(st_key):
            if c in 'ει' and i + 1 < len(st_key) and st_key[i + 1] not in 'αεηιουω':
                pat_parts.append(re.escape(c) + 'ν?')
            else:
                pat_parts.append(re.escape(c))
        pattern = ''.join(pat_parts)
        m = re.search(pattern, f35_key)
        if m:
            pos = m.start()
        else:
            # Try shorter prefix
            for length in (20, 15, 10, 8, 5):
                st_short = st_key[:length]
                if len(st_short) < 4:
                    break
                pos = _find_pos(st_short)
                if pos > 0:
                    break

    if pos > 0:
        rough_count = 0
        for i, ch in enumerate(f35_text):
            rc = _rough_char(ch)
            if rc:
                rough_count += 1
                if rough_count > pos:
                    return f35_text[:i], f35_text[i:]

    return f35_text, ''


def detect_splits(f35_texts, st_texts):
    """Detect where F35 splits a ST verse into two.
    
    Returns set of st_verse_numbers where a split occurs.
    """
    splits = set()
    for i in range(min(len(f35_texts), len(st_texts)) - 1):
        fv_i, ft_i = f35_texts[i]
        fv_j, ft_j = f35_texts[i + 1]
        sv_k, st_k = st_texts[i]

        if st_k == "-":
            continue

        f35_this = rough(ft_i)
        st_this = rough(st_k)

        if not (f35_this and st_this):
            continue
        if f35_this not in st_this:
            continue

        f35_next_full = rough(ft_j)

        def _find_next(min_len=8):
            for prefix_len in (20, 18, 15, 12, 10, 8):
                if prefix_len < min_len:
                    break
                if prefix_len >= len(f35_next_full):
                    prefix_len = len(f35_next_full)
                key = f35_next_full[:prefix_len]
                if not key or len(key) < min_len:
                    break
                pos = st_this.find(key)
                if pos >= 0:
                    return pos, key
            return -1, ''

        pos_this = st_this.find(f35_this)
        pos_next, matched = _find_next()

        if pos_this >= 0 and pos_next >= pos_this + len(f35_this):
            splits.add(sv_k)

    return splits


def align_chapter(f35_verses, st_verses, bk, ch):
    """Align F35 verses to ST verse structure with ⋄ markers.
    
    Returns list of formatted lines.
    """
    lines = []
    f35_idx = 0
    f35_count = len(f35_verses)
    st_count = len(st_verses)

    splits = detect_splits(f35_verses, st_verses)

    carryover = ''

    for i, (st_vs, st_text) in enumerate(st_verses):
        st_ref = f"{bk:02d}{ch:03d}{st_vs:03d}"

        if st_text == "-":
            lines.append(f"{st_ref} -")
            continue

        if f35_idx >= f35_count and not carryover:
            lines.append(f"{st_ref} -")
            continue

        if st_vs in splits:
            f35_vs_a, f35_text_a = f35_verses[f35_idx]
            f35_idx += 1

            f35_vs_b, f35_text_b = f35_verses[f35_idx]
            f35_idx += 1

            # Split F35 v(i+1) text at ST v(i+1) boundary
            st_next_text = st_verses[i + 1][1] if i + 1 < st_count else ''
            before, after = split_at_st(f35_text_b, st_next_text)
            carryover = after

            diamond_num = str(f35_vs_b)
            merged = f"{f35_text_a} ⋄{diamond_num}{before}"
            lines.append(f"{st_ref} {merged.rstrip()}")
            continue

        else:
            if carryover:
                f35_text = carryover
                carryover = ''
                f35_vs = None  # will be set from context
                # Determine the f35 source verse number for ⋄ check
                # The carryover text is part of the last consumed F35 verse
            else:
                f35_vs, f35_text = f35_verses[f35_idx]
                f35_idx += 1

            remaining_st = sum(1 for j in range(i, st_count) if st_verses[j][1] != "-")
            remaining_f35 = f35_count - f35_idx + (1 if carryover else 0)

            if not carryover and remaining_st == 1 and (remaining_f35 > 0 or f35_vs != st_vs):
                merged = f35_text
                if f35_vs != st_vs:
                    merged = f"⋄{f35_vs}{merged}"
                while f35_idx < f35_count:
                    extra_vs, extra_text = f35_verses[f35_idx]
                    merged += f" ⋄{extra_vs}{extra_text}"
                    f35_idx += 1
                lines.append(f"{st_ref} {merged}")
            else:
                lines.append(f"{st_ref} {f35_text}")

    return lines


def main():
    parser = argparse.ArgumentParser(
        description="Step 2: Add missing ⋄ markers to F35 MES output"
    )
    parser.add_argument("--f35", default="F35.txt", help="F35 bbcccvvv file")
    parser.add_argument("--st", default="ST.txt", help="Stephanus reference file")
    parser.add_argument("--output", default="F35_MES.txt", help="Output file")
    args = parser.parse_args()

    print(f"Loading F35 from: {args.f35}")
    f35_data = load_verses(args.f35)

    print(f"Loading Stephanus from: {args.st}")
    st_data = load_verses(args.st)

    print("Aligning with ⋄ detection...")

    chapters = sorted({(bk, ch) for (bk, ch, _) in st_data})

    lines = []
    split_count = 0

    for bk, ch in chapters:
        f35_ch = sorted([
            (vs, txt) for (b, c, vs), (ref, txt) in f35_data.items()
            if b == bk and c == ch
        ])
        st_ch = sorted([
            (vs, txt) for (b, c, vs), (ref, txt) in st_data.items()
            if b == bk and c == ch
        ])

        if not st_ch:
            continue

        chapter_lines = align_chapter(f35_ch, st_ch, bk, ch)

        splits = detect_splits(f35_ch, st_ch)
        if splits:
            split_count += len(splits)

        lines.extend(chapter_lines)

    with open(args.output, "w", encoding="utf-8", newline="\n") as f:
        for line in lines:
            f.write(line + "\n")

    print(f"Wrote {len(lines)} lines to {args.output}")
    print(f"Found {split_count} verse-split boundaries (⋄ markers added)")


if __name__ == "__main__":
    main()
