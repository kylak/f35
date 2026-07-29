#!/usr/bin/env python3
"""Verify that a bbcccvvv-formatted Bible file meets the specification.

Checks:
    - Every line matches ^[0-9]{8} .+
    - References are exactly 8 digits
    - Single space between reference and text
    - UTF-8 encoding, Unix line endings
    - Correct book range (NT-only: 40-66)
    - No HTML tags, HTML entities, or multiple consecutive spaces
    - No duplicate verse references (unless intentional)

Usage:
    python verify.py [FILE]
"""

import argparse
import re
import sys


RE_LINE = re.compile(r"^([0-9]{8}) (.+)$")
RE_HTML_TAG = re.compile(r"<[^>]+>")
RE_HTML_ENT = re.compile(r"&[a-zA-Z#][a-zA-Z0-9#]*;")
RE_MULTISPACE = re.compile(r"  ")


def verify(filepath: str) -> bool:
    errors = 0
    warnings = 0
    total = 0
    refs_seen: set[str] = set()

    with open(filepath, encoding="utf-8") as fh:
        raw = fh.read()

    # ------------------------------------------------------------------
    # Encoding checks
    # ------------------------------------------------------------------
    try:
        encoded = raw.encode("utf-8")
    except UnicodeEncodeError as e:
        print(f"  FAIL  File cannot be encoded as UTF-8: {e}")
        errors += 1

    # ------------------------------------------------------------------
    # Line-ending check
    # ------------------------------------------------------------------
    if "\r\n" in raw:
        print("  FAIL  File contains CRLF line endings (should be LF)")
        errors += 1
    elif "\r" in raw:
        print("  FAIL  File contains bare CR line endings (should be LF)")
        errors += 1
    else:
        print("  OK    Unix (LF) line endings")

    lines = raw.splitlines()

    # ------------------------------------------------------------------
    # Per-line checks
    # ------------------------------------------------------------------
    for lineno, line in enumerate(lines, start=1):
        total += 1
        m = RE_LINE.match(line)
        if not m:
            print(f"  FAIL  Line {lineno}: does not match '^[0-9]{{8}} .+'")
            print(f"        → {repr(line[:80])}")
            errors += 1
            continue

        ref, text = m.group(1), m.group(2)

        # Check reference is exactly 8 digits
        if len(ref) != 8:
            print(f"  FAIL  Line {lineno}: reference '{ref}' is not 8 characters")
            errors += 1

        # Check exactly one space between ref and text
        if not line.startswith(ref + " "):
            print(f"  FAIL  Line {lineno}: expected single space after reference")
            errors += 1

        # Check for duplicate refs
        if ref in refs_seen:
            print(f"  WARN  Line {lineno}: duplicate reference {ref}")
            warnings += 1
        refs_seen.add(ref)

    # ------------------------------------------------------------------
    # Book-range check (NT-only: 40-66)
    # ------------------------------------------------------------------
    books = sorted({line[:2] for line in lines})
    book_nums = [int(b) for b in books]
    if book_nums and (min(book_nums) < 40 or max(book_nums) > 66):
        print(f"  FAIL  Book range out of expected NT range (40-66): {books}")
        errors += 1
    else:
        print(f"  OK    Book range: {', '.join(books)}  (NT-only: 40-66)")

    # ------------------------------------------------------------------
    # Content-cleaning checks (sample the raw text without refs)
    # ------------------------------------------------------------------
    texts = [m.group(2) for m in (RE_LINE.match(l) for l in lines) if m]

    combined = " ".join(texts)

    if RE_HTML_TAG.search(combined):
        print("  FAIL  HTML tags found in text")
        errors += 1
    else:
        print("  OK    No HTML tags")

    if RE_HTML_ENT.search(combined):
        print("  FAIL  HTML entities found in text")
        errors += 1
    else:
        print("  OK    No HTML entities")

    if RE_MULTISPACE.search(combined):
        print("  FAIL  Multiple consecutive spaces found in text")
        errors += 1
    else:
        print("  OK    No multiple spaces")

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------
    print()
    print(f"  Total lines: {total}")
    print(f"  Errors:   {errors}")
    print(f"  Warnings: {warnings}")

    if errors:
        print("\n  ❌  VERIFICATION FAILED")
        return False
    else:
        print("\n  ✅  VERIFICATION PASSED")
        return True


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify bbcccvvv Bible file format")
    parser.add_argument("file", nargs="?", default="F35.txt", help="File to verify (default: F35.txt)")
    args = parser.parse_args()

    print(f"Verifying: {args.file}\n")
    ok = verify(args.file)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
