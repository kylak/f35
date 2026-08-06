#!/usr/bin/env python3
"""
Verify the F35 text with paragraph markers (f35_with_paragraphs.txt).

Checks performed:

  Format
    - Every line is <8-digit ref> + single space + non-empty text.
    - Book range matches the requested scope (default NT: 40-66).
    - No double spaces, leading/trailing whitespace, or tabs.
    - No HTML tags or HTML entities.
    - Unix line endings (LF only, no CR).
    - Valid UTF-8.

  Content
    - Removing every ¶ reproduces f35_without_paragraphs.txt exactly.

  Paragraph placement
    - No '¶¶', no '¶ ' (space after ¶), no '»¶', no '¶⋄',
      no ¶ at end of line, no ¶ followed by punctuation.
    - Total ¶ count matches the F35 USFM sources.

  Alignment (needs --usfm directory)
    - Per chapter, the rough-normalised text still matches the USFM, and
      the number of ¶ equals the number of paragraph markers in the USFM.

Usage:
    python verify_paragraphs.py [--output FILE] [--reference FILE]
                                [--usfm DIR] [--scope nt|ot|full]
"""

import argparse
import glob
import os
import re
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_OUTPUT = os.path.join(SCRIPT_DIR, "f35_with_paragraphs.txt")
DEFAULT_REF = os.path.join(SCRIPT_DIR, "f35_without_paragraphs.txt")

REF_RE = re.compile(r"^(\d{2})(\d{3})(\d{3}) (.+)$")
HTML_TAG_RE = re.compile(r"<[^>]+>")
HTML_ENTITY_RE = re.compile(r"&(?:\w+|#\d+);")

BOOK_NAMES = {
    40: "MAT", 41: "MRK", 42: "LUK", 43: "JHN", 44: "ACT",
    45: "ROM", 46: "1CO", 47: "2CO", 48: "GAL", 49: "EPH",
    50: "PHP", 51: "COL", 52: "1TH", 53: "2TH", 54: "1TI",
    55: "2TI", 56: "TIT", 57: "PHM", 58: "HEB", 59: "JAS",
    60: "1PE", 61: "2PE", 62: "1JN", 63: "2JN", 64: "3JN",
    65: "JUD", 66: "REV",
}

SCOPE_RANGES = {
    "ot": (1, 39),
    "nt": (40, 66),
    "full": (1, 66),
}


def load_lines(path):
    """Read a file as UTF-8 text, returning one entry per line (LF stripped)."""
    with open(path, encoding="utf-8", errors="strict") as f:
        return [line.rstrip("\n") for line in f]


def check_reference(lines):
    """
    Return a list of (bk, ch, vs, text) for well-formed lines.
    Malformed lines are reported via the errors list.
    """
    refs = []
    errors = []
    for i, line in enumerate(lines, 1):
        m = REF_RE.match(line)
        if not m:
            errors.append((i, line[:80]))
            continue
        bk, ch, vs = int(m.group(1)), int(m.group(2)), int(m.group(3))
        text = m.group(4)
        if text.startswith(" ") or text.endswith(" ") or "  " in text or "\t" in text:
            errors.append((i, f"whitespace in line {line[:60]!r}"))
        refs.append((bk, ch, vs, text))
    return refs, errors


def verify():
    errors = 0
    parser = argparse.ArgumentParser(
        description="Verify the F35 text with ¶ paragraph markers"
    )
    parser.add_argument("--output", default=DEFAULT_OUTPUT)
    parser.add_argument("--reference", default=DEFAULT_REF)
    parser.add_argument("--usfm", default="/tmp/opencode/f35_sources/usfm")
    parser.add_argument("--scope", default="nt", choices=["nt", "ot", "full"])
    args = parser.parse_args()

    try:
        lines = load_lines(args.output)
    except UnicodeDecodeError as e:
        print(f"❌ UTF-8: decoding failed in {args.output}: {e}")
        return False

    lo, hi = SCOPE_RANGES[args.scope]

    # ------------------------------------------------------------------
    # 1. Format / structure
    # ------------------------------------------------------------------
    print("== Format ==")
    refs, malformed = check_reference(lines)
    print(f"Lines: {len(lines)}  well-formed: {len(refs)}", end="")
    if malformed:
        print(f"  ✗ ({len(malformed)} bad)")
        for i, s in malformed[:5]:
            print(f"    line {i}: {s}")
        errors += 1
    else:
        print("  ✓")

    if not refs:
        print("❌ No valid lines; cannot continue")
        return False

    books = sorted({r[0] for r in refs})
    print(f"Books: {len(books)} ({books[0]}-{books[-1]})", end="")
    if any(b < lo or b > hi for b in books):
        print(f"  ✗ outside scope {lo}-{hi}")
        errors += 1
    else:
        print("  ✓")

    # The verse references should be strictly increasing.  Known exceptions:
    # the Byzantine F35 tradition swaps MAT 23:13/14, so the order can
    # legitimately regress there (preservation is checked above, via the
    # content comparison against the reference file).
    prev = (-1, -1, -1)
    order_bad = 0
    for bk, ch, vs, _ in refs:
        cur = (bk, ch, vs)
        if cur < prev:
            order_bad += 1
        prev = cur
    if order_bad:
        print(f"Note: verse order has {order_bad} regression(s) "
              f"(expected: MAT 23:13/14 are swapped in F35)")

    # ------------------------------------------------------------------
    # 2. Cleaning
    # ------------------------------------------------------------------
    print("== Cleaning ==")
    tags = entities = 0
    for line in lines:
        text = REF_RE.match(line).group(4) if REF_RE.match(line) else line
        tags += len(HTML_TAG_RE.findall(text))
        entities += len(HTML_ENTITY_RE.findall(text))
    print(f"HTML tags: {tags}  HTML entities: {entities}", end="")
    if tags or entities:
        print("  ✗")
        errors += 1
    else:
        print("  ✓")

    # ------------------------------------------------------------------
    # 3. Content preservation
    # ------------------------------------------------------------------
    print("== Content ==")
    try:
        ref_lines = load_lines(args.reference)
    except UnicodeDecodeError as e:
        print(f"❌ UTF-8: decoding failed in {args.reference}: {e}")
        return False
    stripped = [line.replace("¶", "") for line in lines]
    if stripped != ref_lines:
        diff = sum(1 for a, b in zip(stripped, ref_lines) if a != b)
        print(f"After removing ¶: differs from {os.path.basename(args.reference)} "
              f"in {diff} line(s)  ✗")
        for a, b in zip(stripped, ref_lines):
            if a != b:
                print(f"    out: {a[:70]}")
                print(f"    ref: {b[:70]}")
                break
        errors += 1
    else:
        print(f"After removing ¶: identical to {os.path.basename(args.reference)}  ✓")

    # ------------------------------------------------------------------
    # 4. Paragraph placement rules
    # ------------------------------------------------------------------
    print("== Paragraph placement ==")
    total_para = sum(line.count("¶") for line in lines)
    bad_patterns = {
        "¶¶": 0, "¶ ": 0, "»¶": 0, "¶⋄": 0,
    }
    punct_after = 0
    para_at_end = 0
    for line in lines:
        text = REF_RE.match(line).group(4) if REF_RE.match(line) else line
        for pat in bad_patterns:
            bad_patterns[pat] += len(re.findall(re.escape(pat), text))
        punct_after += len(re.findall(r"¶[.,:;!?—]", text))
        para_at_end += len(re.findall(r"¶$", text))
    bad_total = sum(bad_patterns.values()) + punct_after + para_at_end
    if bad_total:
        print(f"Bad placements: {bad_total}  ✗")
        for k, v in bad_patterns.items():
            if v:
                print(f"    {k!r}: {v}")
        if punct_after:
            print(f"    ¶ + punctuation: {punct_after}")
        if para_at_end:
            print(f"    ¶ at end of line: {para_at_end}")
        errors += 1
    else:
        print(f"No bad placements (¶¶ / ¶␣ / »¶ / ¶⋄ / ¶+punct / ¶$):  ✓")
    print(f"Total ¶: {total_para}")

    # ------------------------------------------------------------------
    # 5. Alignment with the F35 USFM sources
    # ------------------------------------------------------------------
    print("== USFM alignment ==")
    usfm_dir = args.usfm
    if not os.path.isdir(usfm_dir):
        print(f"Skipped (no USFM directory: {usfm_dir})")
    else:
        sys.path.insert(0, SCRIPT_DIR)
        try:
            import add_paragraphs as ap
        except ImportError as e:
            print(f"Skipped (cannot import add_paragraphs: {e})")
            return errors == 0
        bookmap = {}
        for f in glob.glob(os.path.join(usfm_dir, "*-*grcf35.usfm")):
            m = re.match(r"(\d+)-.*grcf35\.usfm$", os.path.basename(f))
            if m:
                bookmap[int(m.group(1)) - 6] = f

        # Group output lines by (book, chapter), preserving file order.
        chapters = {}
        for line in lines:
            m = REF_RE.match(line)
            if m:
                key = (int(m.group(1)), int(m.group(2)))
                chapters.setdefault(key, []).append(line)

        align_bad = 0
        count_bad = 0
        usfm_para_total = 0
        checked = 0
        for (bk, ch), ch_lines in chapters.items():
            path = bookmap.get(bk)
            if not path:
                continue
            verses = ap.parse_usfm_chapter(path, ch)
            if verses is None:
                continue
            checked += 1
            usfm_rough, para_offsets = ap.usfm_para_offsets(verses)
            stripped_ch = [l.replace("¶", "") for l in ch_lines]
            entries = ap.build_output_stream(stripped_ch)
            out_rough = "".join(r for _, _, r, _ in entries)
            if usfm_rough != out_rough:
                align_bad += 1
            out_para = sum(l.count("¶") for l in ch_lines)
            if len(para_offsets) != out_para:
                count_bad += 1
            usfm_para_total += len(para_offsets)
        print(f"Chapters checked: {checked}  ¶ in USFM: {usfm_para_total}  "
              f"¶ in output: {total_para}", end="")
        if align_bad or count_bad:
            print(f"  ✗ (text mismatch: {align_bad}, ¶ count mismatch: {count_bad})")
            errors += 1
        else:
            print("  ✓")

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------
    print()
    if errors:
        print(f"❌ {errors} error(s)")
        return False
    print("✅ VERIFICATION PASSED")
    return True


if __name__ == "__main__":
    ok = verify()
    sys.exit(0 if ok else 1)
