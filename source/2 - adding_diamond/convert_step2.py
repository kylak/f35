#!/usr/bin/env python3
"""
Step 2: Align F35 Greek New Testament to the Stephanus 1551 versification.

Reads F35.txt (F35 NA versification) and ST.txt (Stephanus 1551 reference),
then writes F35_MES.txt where every verse follows the Stephanus verse numbering.

When F35 divides a verse differently from Stephanus, a diamond marker (⋄) is
inserted to show where the F35 verse boundary actually falls.

Usage:
    python convert_step2.py --f35 F35.txt --st ST.txt --output F35_MES.txt
"""

import argparse
import re
import unicodedata


def load_verses(filepath):
    """
    Load a bbcccvvv-formatted text file into a dictionary.

    Returns:
        dict: (book, chapter, verse) -> (reference_string, verse_text)
    """
    verses = {}
    with open(filepath, encoding="utf-8") as f:
        for line in f:
            m = re.match(r"^(\d{2})(\d{3})(\d{3})\s+(.*)", line)
            if m:
                bk = int(m.group(1))
                ch = int(m.group(2))
                vs = int(m.group(3))
                key = (bk, ch, vs)
                ref = f"{bk:02d}{ch:03d}{vs:03d}"
                verses[key] = (ref, m.group(4))
    return verses


def rough(t):
    """
    Normalize Greek text for fuzzy comparison.

    Strips diacritics, punctuation, spacing, and lowercases everything,
    so that textual variants (e.g., different breathing marks or punctuation)
    do not prevent matching.

    Example:
        "γνωστὸν οὖν ἔστω ὑμῖν" -> "γνωστονουνεστωυμιν"
    """
    # Normalize Unicode (NFD splits base char + combining marks)
    t = unicodedata.normalize("NFD", t.lower())
    # Remove punctuation and whitespace
    t = re.sub(r'[.,:;!?\-—()\[\]«»"\'··\s]', "", t)
    # Strip combining diacritical marks (category Mn = Mark, Nonspacing)
    return "".join(c for c in t if unicodedata.category(c) != "Mn")


def _rough_char(c):
    """
    Rough-normalize a single character for position tracking.

    Unlike rough(), this preserves one character per original character,
    which is needed to map rough positions back to the original text.
    """
    c = unicodedata.normalize("NFD", c.lower())
    return "".join(
        ch for ch in c
        if unicodedata.category(ch) != "Mn" and (ch.isalpha() or ch.isdigit())
    )


def split_at_st(f35_text, st_next_text):
    """
    Split F35 text at the boundary where the next Stephanus verse begins.

    When a diamond split is detected, this function partitions the overflow
    F35 verse text into two parts:
      - 'before':  text that belongs to the current ST verse
      - 'after':   text that carries over to the next ST verse

    The split point is found by locating the rough-normalized start of the
    next ST verse within the rough-normalized F35 verse text.

    Nu-movable (ν at the end of a word before a vowel) is handled via regex,
    and shorter prefixes are tried as fallback for textual variants.

    Args:
        f35_text:      The full text of the overflow F35 verse.
        st_next_text:  The text of the next Stephanus verse.

    Returns:
        tuple: (before, after) — both are substrings of f35_text.
               If no boundary is found, returns (f35_text, '').
    """
    # If the next ST verse is empty, there is nothing to split at.
    if not st_next_text or st_next_text == "-":
        return f35_text, ""

    f35_key = rough(f35_text)

    # Use the first 30 rough characters of the next ST verse as the boundary marker.
    st_key = rough(st_next_text)[:30]
    if not st_key:
        return f35_text, ""

    def _find_pos(needle):
        return f35_key.find(needle)

    pos = _find_pos(st_key)

    if pos <= 0:
        # --- Nu-movable fallback ---
        # Greek often adds or omits a final ν before a vowel.
        # Build a pattern where ε/ι can optionally be followed by ν.
        pat_parts = []
        for i, c in enumerate(st_key):
            if c in "ει" and i + 1 < len(st_key) and st_key[i + 1] not in "αεηιουω":
                pat_parts.append(re.escape(c) + "ν?")
            else:
                pat_parts.append(re.escape(c))
        pattern = "".join(pat_parts)
        m = re.search(pattern, f35_key)
        if m:
            pos = m.start()
        else:
            # --- Shorter prefix fallback ---
            # If the full 30-char prefix does not match (e.g. due to textual
            # variants between F35 and ST), try progressively shorter prefixes.
            for length in (20, 15, 10, 8, 5):
                st_short = st_key[:length]
                if len(st_short) < 4:
                    break
                pos = _find_pos(st_short)
                if pos > 0:
                    break

    if pos > 0:
        # Map the rough character position back to an index in the original text.
        # Each original character may produce zero or one rough character.
        rough_count = 0
        for i, ch in enumerate(f35_text):
            rc = _rough_char(ch)
            if rc:
                rough_count += 1
                if rough_count > pos:
                    return f35_text[:i], f35_text[i:]

    # No boundary found — the entire F35 verse stays in the current ST verse.
    return f35_text, ""


def detect_splits(f35_texts, st_texts):
    """
    Detect where F35 splits a single Stephanus verse into two or more verses.

    For each aligned pair (F35 v(i), ST v(k)), check whether the beginning of
    the next F35 verse (v(i+1)) appears inside ST v(k) after the end of F35 v(i).
    If it does, F35 draws the verse boundary earlier than Stephanus — a ⋄ split.

    The routine tries progressively shorter prefixes of F35 v(i+1) (down to 8
    rough characters) to cope with textual variants between the two traditions.

    Returns:
        set: Stephanus verse numbers where a split was detected.
    """
    splits = set()
    # Iterate over all verse pairs that have a next verse to compare.
    for i in range(min(len(f35_texts), len(st_texts)) - 1):
        fv_i, ft_i = f35_texts[i]       # F35 verse i
        fv_j, ft_j = f35_texts[i + 1]   # F35 verse i+1
        sv_k, st_k = st_texts[i]         # ST verse k

        # Skip empty Stephanus verses (e.g. LUK 17:36).
        if st_k == "-":
            continue

        f35_this = rough(ft_i)
        st_this = rough(st_k)

        if not (f35_this and st_this):
            continue
        # F35 v(i) must appear somewhere inside ST v(k).
        if f35_this not in st_this:
            continue

        f35_next_full = rough(ft_j)

        def _find_next(min_len=8):
            """Try prefixes of f35_next_full (longest first) in st_this."""
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
            return -1, ""

        # Where does F35 v(i) start in ST v(k)?
        pos_this = st_this.find(f35_this)
        # Where does the next F35 verse start in ST v(k)?
        pos_next, matched = _find_next()

        # A genuine split: the next F35 verse starts after the current F35
        # verse ends inside the same ST verse.
        if pos_this >= 0 and pos_next >= pos_this + len(f35_this):
            splits.add(sv_k)

    return splits


def align_chapter(f35_verses, st_verses, bk, ch):
    """
    Align all verses of one chapter from F35 to the Stephanus verse structure.

    This function walks through ST verses in order and matches them to F35
    verses.  When a split is detected (via detect_splits), two F35 verses are
    merged into one ST line with a ⋄ marker.  When F35 has extra verses beyond
    ST (or vice versa), the remaining verses are either absorbed with ⋄ markers
    or left empty ('-').

    Args:
        f35_verses: list of (verse_number, text) for this chapter in F35.
        st_verses:  list of (verse_number, text) for this chapter in ST.
        bk:         book number.
        ch:         chapter number.

    Returns:
        list of formatted output lines.
    """
    lines = []
    f35_idx = 0                # current index into the F35 verse list
    f35_count = len(f35_verses)
    st_count = len(st_verses)

    # Pre-detect all splits for this chapter.
    splits = detect_splits(f35_verses, st_verses)

    carryover = ""             # text split from a previous verse, pending for the next
    st_empty_count = 0         # number of empty ST verses seen (for offset tracking)

    for i, (st_vs, st_text) in enumerate(st_verses):
        st_ref = f"{bk:02d}{ch:03d}{st_vs:03d}"

        # --- Empty ST verse (e.g. LUK 17:36) ---
        if st_text == "-":
            st_empty_count += 1
            lines.append(f"{st_ref} -")
            continue

        # --- No F35 verse left to assign ---
        if f35_idx >= f35_count and not carryover:
            lines.append(f"{st_ref} -")
            continue

        # --- Split handling ---
        # ST v(k) contains text from both F35 v(i) and F35 v(i+1).
        if st_vs in splits:
            # Consume F35 v(i) (the main text).
            f35_vs_a, f35_text_a = f35_verses[f35_idx]
            f35_idx += 1

            # Consume F35 v(i+1) (the overflow text that starts inside ST v(k)).
            f35_vs_b, f35_text_b = f35_verses[f35_idx]
            f35_idx += 1

            # Try to split the overflow verse at the boundary where the next
            # ST verse begins.  Anything after the boundary carries over.
            st_next_text = st_verses[i + 1][1] if i + 1 < st_count else ""
            before, after = split_at_st(f35_text_b, st_next_text)
            carryover = after

            diamond_num = str(f35_vs_b)
            merged = f"{f35_text_a} ⋄{diamond_num}{before}"
            lines.append(f"{st_ref} {merged.rstrip()}")
            continue

        # --- Normal (non-split) verse ---
        else:
            if carryover:
                # There is pending text from a previous split that was not
                # consumed yet — assign it to this ST verse.
                f35_text = carryover
                carryover = ""
                f35_vs = None  # verse number determined by context
            else:
                # Normal 1-to-1 mapping: consume the next F35 verse.
                f35_vs, f35_text = f35_verses[f35_idx]
                f35_idx += 1

            # How many non-empty ST verses remain (including this one)?
            remaining_st = sum(
                1 for j in range(i, st_count) if st_verses[j][1] != "-"
            )
            # How many F35 verses remain (including carryover)?
            remaining_f35 = f35_count - f35_idx + (1 if carryover else 0)

            # --- Last non-empty ST verse: absorb extra F35 verses ---
            # If we are on the last ST verse and there are still unconsumed
            # F35 verses (or a verse-number mismatch not explained by empty
            # ST verses), we merge them all into one line with ⋄ markers.
            if not carryover and remaining_st == 1 and (
                remaining_f35 > 0 or f35_vs != st_vs - st_empty_count
            ):
                merged = f35_text
                if f35_vs != st_vs:
                    merged = f"⋄{f35_vs}{merged}"
                while f35_idx < f35_count:
                    extra_vs, extra_text = f35_verses[f35_idx]
                    merged += f" ⋄{extra_vs}{extra_text}"
                    f35_idx += 1
                lines.append(f"{st_ref} {merged}")
            else:
                # Standard output: one F35 verse → one ST line.
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

    # Iterate over all chapters present in the Stephanus reference.
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
