#!/usr/bin/env python3
"""
Step 4: Add paragraph markers (¶) to the F35 MES text.

The F35 edition defines its own paragraph structure.  This script reads that
structure from the F35 USFM source files (grcf35_*.usfm), which mark every
paragraph with a \\p (paragraph) or \\m (margin, after a section heading) marker.

Because the output file (f35_without_paragraphs.txt) uses the MES versification
(the verse boundaries may differ from F35's own), the paragraph break positions
are mapped by aligning the two texts character-by-character at the chapter
level rather than assuming the verse numbers match.

Usage:
    python add_paragraphs.py \\
        --input f35_without_paragraphs.txt \\
        --usfm source \\
        --output f35_with_paragraphs.txt
"""

import argparse
import glob
import os
import re
import sys
import unicodedata

# USFM book numbering 46-72 maps to bb 40-66 (bb = usfm_no - 6).
USFM_BOOK_FILES = {}

# Heading / metadata markers whose (usually English) content is skipped.
HEADINGS = ("ms", "s", "mt", "h", "toc", "ip", "is", "imi",
            "fig", "tr", "tc", "nd", "ili", "fv")

# Markers that introduce a new paragraph (longest first for alternation).
PARA_MARKERS = "pi1|mi|ib|im|pc|p|m"
PARA_RE = re.compile(r"\\v (\d+)|\\(" + PARA_MARKERS + r")")


def rough(t):
    """Normalise Greek text for fuzzy comparison."""
    t = unicodedata.normalize("NFD", t.lower())
    t = t.replace("ς", "σ")
    t = re.sub(r"[.,:;!?\-—()\[\]«»\"'··\s]", "", t)
    return "".join(c for c in t if unicodedata.category(c) != "Mn")


def rough_char(c):
    """Rough-normalise a single character, preserving 1 char per original."""
    c = unicodedata.normalize("NFD", c.lower())
    c = c.replace("ς", "σ")
    return "".join(
        ch for ch in c
        if unicodedata.category(ch) != "Mn"
        and ch not in ".,:;!?—()[]«»\"'··¶- " and not ch.isspace()
    )


def rough_index(text, target):
    """
    Return the character index in `text` at which the (target+1)-th rough
    character begins.  Used to convert a rough-space offset back to the
    original text so a ¶ can be inserted at the right place.
    """
    count = 0
    for i, ch in enumerate(text):
        if rough_char(ch):
            count += 1
            if count > target:
                return i
    return len(text)


def parse_usfm_chapter(filepath, chapter):
    """
    Parse one chapter from a USFM file.

    Returns:
        list of (verse_no, text) where `text` already contains ¶ markers
        embedded at the correct positions (start-of-verse or mid-verse).
    """
    with open(filepath, encoding="utf-8") as f:
        content = f.read()

    # Strip footnotes (may span lines) and inline markup.
    content = re.sub(r"\\f(?:\s.*?)\\f\*", "", content, flags=re.S)
    content = re.sub(r"\\w ([^|]*?)\|strong=\"[^\"]*\"\\w\*", r" \1 ", content)
    content = re.sub(r"\\w ([^\\]*?)\\w\*", r" \1 ", content)
    content = re.sub(r"\\\+[a-z0-9]+\*?", "", content)
    content = re.sub(r"\\([a-z]{2,8})\b(.*?)\\\1\*", r"\2", content, flags=re.S)
    content = re.sub(r"\\[a-z]{2,8}\*", "", content)
    content = re.sub(r"\\nb", " ", content)

    # Isolate the chapter block.
    cpat = re.compile(r"\\c (\d+)(.*?)(?=\\c \d+|\Z)", re.S)
    block = None
    for m in cpat.finditer(content):
        if int(m.group(1)) == chapter:
            block = m.group(2)
            break
    if block is None:
        return None

    verses = []           # (verse_no, text with ¶ embedded)
    current_verse = None
    current_parts = []
    pending_para = False

    def flush():
        nonlocal current_verse
        if current_verse is not None and "".join(current_parts).strip():
            verses.append((current_verse, "".join(current_parts).strip()))
        current_verse = None
        current_parts.clear()

    for line in block.splitlines():
        line = line.strip()
        if not line:
            continue
        mh = re.match(r"^\\([a-zA-Z]+)(?:\d+)?", line)
        if mh and mh.group(1).lower() in HEADINGS:
            continue
        if not line.startswith("\\"):
            if current_verse is not None:
                current_parts.append((" " if current_parts else "") + line)
            continue

        pos = 0
        for m in PARA_RE.finditer(line):
            before = line[pos:m.start()].strip()
            if before and current_verse is not None:
                current_parts.append((" " if current_parts else "") + before)
            if m.group(1) is not None:
                flush()
                current_verse = int(m.group(1))
                current_parts = []
                if pending_para:
                    current_parts.append("¶")
                    pending_para = False
            else:
                rest = line[m.end():]
                nxt = PARA_RE.search(rest)
                after = (rest[:nxt.start()] if nxt else rest).strip()
                if after and current_verse is not None:
                    # Text follows on the same line -> paragraph break mid-verse.
                    current_parts.append("¶")
                else:
                    # Nothing follows -> paragraph starts before next verse.
                    pending_para = True
            pos = m.end()
        if pos < len(line):
            txt = line[pos:].strip()
            if txt and current_verse is not None:
                current_parts.append((" " if current_parts else "") + txt)

    flush()
    return verses


def usfm_para_offsets(verses):
    """
    Concatenate the chapter's verse texts into a rough-normalised stream and
    record the rough-space offset of every ¶ marker in it.

    Returns:
        (usfm_rough, para_offsets)
    """
    rough_chars = []
    para_offsets = []
    for vs, text in verses:
        for ch in text:
            if ch == "¶":
                para_offsets.append(len(rough_chars))
            else:
                rc = rough_char(ch)
                if rc:
                    rough_chars.append(rc)
    return "".join(rough_chars), para_offsets


def build_output_stream(lines):
    """
    Convert the output chapter lines into rough-text entries.

    Returns:
        list of (orig_line_text, raw_text, rough_text, start_rough_offset)
        for every non-empty line, in file order.  `orig_line_text` retains
        the ⋄ markers; `raw_text` is ⋄-stripped.
    """
    entries = []
    offset = 0
    for line in lines:
        m = re.match(r"^\d{8}\s+(.*)", line)
        if not m:
            continue
        orig = m.group(1).strip()
        if orig == "-":
            continue
        raw = re.sub(r"⋄\d+", "", orig).strip()
        r = rough(raw)
        if not r:
            continue
        entries.append((orig, raw, r, offset))
        offset += len(r)
    return entries


def raw_to_orig(orig, raw, ci):
    """
    Map a character index in `raw` (⋄-stripped) back to an index in `orig`.
    """
    oi = 0
    ci2 = 0
    while ci2 < ci:
        if orig[oi] == "⋄":
            m = re.match(r"⋄\d+", orig[oi:])
            oi += m.end() if m else 1
            continue
        oi += 1
        ci2 += 1
    while oi < len(orig) and orig[oi] == "⋄":
        m = re.match(r"⋄\d+", orig[oi:])
        oi += m.end() if m else 1
    return oi


def back_over_prefix(raw, ci):
    """
    Move an insertion index leftwards across any leading quote (» « ‹ ›)
    that belongs to the start of the paragraph, so a ¶ ends up before it.
    """
    i = ci
    while i > 0 and raw[i - 1] in "»«‹›":
        i -= 1
    return i


def orig_after_verse_markers(orig):
    """Index in `orig` just past any leading ⋄N verse markers."""
    m = re.match(r"(?:⋄\d+)+", orig)
    return m.end() if m else 0


def map_paragraphs(entries, para_offsets):
    """
    Map each USFM paragraph offset onto an output entry + char index.

    Returns:
        dict entry_index -> list of character indices (in the original line
        text, ⋄ markers included) where ¶ must be inserted.
    """
    ins = {}
    for p in para_offsets:
        for idx, (orig, raw, r, start) in enumerate(entries):
            if start <= p < start + len(r):
                tgt = p - start
                if tgt == 0:
                    # Paragraph at the very start of a verse: put ¶ after any
                    # leading ⋄N verse marker, before any leading quote.
                    oi = orig_after_verse_markers(orig)
                else:
                    oi = raw_to_orig(orig, raw,
                                     back_over_prefix(raw, rough_index(raw, tgt)))
                ins.setdefault(idx, []).append(oi)
                break
    return ins


def main():
    parser = argparse.ArgumentParser(
        description="Step 4: Add ¶ paragraph markers to the F35 text"
    )
    parser.add_argument("--input", default="f35_without_paragraphs.txt")
    parser.add_argument("--usfm", default="source")
    parser.add_argument("--output", default="f35_with_paragraphs.txt")
    args = parser.parse_args()

    usfm_files = sorted(glob.glob(os.path.join(args.usfm, "*-*grcf35.usfm")))
    for f in usfm_files:
        m = re.match(r"(\d+)-.*grcf35\.usfm$", os.path.basename(f))
        if m:
            no = int(m.group(1))
            if 46 <= no <= 72:
                USFM_BOOK_FILES[no - 6] = f

    if not USFM_BOOK_FILES:
        print(
            f"ERROR: no USFM source files found in {args.usfm!r} "
            "(expected *-*grcf35.usfm for books 46-72)."
        )
        sys.exit(1)

    chapters = {}
    with open(args.input, encoding="utf-8") as f:
        for line in f:
            m = re.match(r"^(\d{2})(\d{3})(\d{3})\s+", line)
            if m:
                key = (m.group(1), m.group(2))
                chapters.setdefault(key, []).append(line.rstrip("\n"))

    mismatches = []
    total_para = 0
    output_lines = {}

    for (bk, ch), lines in chapters.items():
        usfm_path = USFM_BOOK_FILES.get(int(bk))
        if not usfm_path:
            output_lines[(bk, ch)] = lines
            continue

        verses = parse_usfm_chapter(usfm_path, int(ch))
        if verses is None:
            mismatches.append(f"{bk}:{ch}: no USFM chapter")
            output_lines[(bk, ch)] = lines
            continue

        usfm_rough, para_offsets = usfm_para_offsets(verses)
        entries = build_output_stream(lines)
        out_rough = "".join(r for _, _, r, _ in entries)

        if usfm_rough != out_rough:
            mismatches.append(f"{bk}:{ch}: stream mismatch")
            output_lines[(bk, ch)] = lines
            continue

        ins = map_paragraphs(entries, para_offsets)
        total_para += sum(len(v) for v in ins.values())

        # Rebuild the chapter lines, inserting ¶ at the mapped positions.
        new_lines = []
        ei = 0
        for raw_line in lines:
            m = re.match(r"^(\d{8})\s+(.*)", raw_line)
            if m and m.group(2).strip() not in ("", "-"):
                orig, raw, _, _ = entries[ei]
                cis = sorted(ins.get(ei, []))
                for oi in reversed(cis):
                    orig = orig[:oi] + "¶" + orig[oi:]
                new_lines.append(f"{m.group(1)} {orig}")
                ei += 1
            else:
                new_lines.append(raw_line)
        output_lines[(bk, ch)] = new_lines

    written = 0
    with open(args.output, "w", encoding="utf-8", newline="\n") as f:
        for (bk, ch) in chapters:
            for line in output_lines[(bk, ch)]:
                f.write(line + "\n")
                written += 1

    print(f"Wrote {written} lines to {args.output}")
    print(f"Inserted {total_para} paragraph markers (¶)")

    if mismatches:
        print(f"WARNING: {len(mismatches)} chapter(s) had mismatches:")
        for m in mismatches[:50]:
            print(f"  {m}")
    else:
        print("All chapters aligned successfully ✓")


if __name__ == "__main__":
    main()
