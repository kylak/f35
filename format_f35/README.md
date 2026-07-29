# Format f35 — Greek New Testament (Family 35)

Convert the f35 Greek New Testament from readaloud plain-text files to the
standard `bbcccvvv` reference format.

## Source files

The readaloud files live in `source/readaloud/` and are organised as one file
per chapter.  Each file contains:

    Line 1:   book title
    Line 2:   chapter number
    Line 3+:  one verse per line (already cleaned, no markup)

Example (`source/readaloud/grcf35_070_MAT_01_read.txt`):

    ΕΥΑΓΓΕΛΙΟΝ ΚΑΤΑ ΜΑΤΘΑΙΟΝ.
    1.
    Βίβλος γενέσεως Ἰησοῦ Χριστοῦ, υἱοῦ Δαυίδ, υἱοῦ Ἁβραάμ·
    Ἁβραὰμ ἐγέννησεν τὸν Ἰσαάκ, Ἰσαὰκ δὲ ἐγέννησεν τὸν Ἰακώβ…
    …

## How to reproduce

### Prerequisites

- Python ≥ 3.8
- The readaloud files in `source/readaloud/` (shipped with the f35 distribution)

### 1. Convert

```bash
python convert.py --readaloud-dir ../source/readaloud --output F35.txt
```

Or, from the repository root:

```bash
python format_f35/convert.py
```

This produces `F35.txt` where every line looks like:

```
40001001 Βίβλος γενέσεως Ἰησοῦ Χριστοῦ, υἱοῦ Δαυίδ, υἱοῦ Ἁβραάμ·
```

### 2. Verify

```bash
python verify.py F35.txt
```

The verifier checks:

| Check | Description |
|---|---|
| Format | Every line matches `^[0-9]{8} .+` |
| Reference length | Exactly 8 digits (`bbcccvvv`) |
| Separator | Single space between reference and text |
| Encoding | UTF-8 with Unix (LF) line endings |
| Scope | NT only: books 40–66 |
| Cleaning | No HTML tags, entities, or multiple spaces |

## Book mapping

The f35 internal numbering in filenames (`grcf35_{NNN}_…`) maps to standard
Protestant book numbers via: **book = NNN − 30**

| f35 | Book | # |
|---|---|---|
| 070 | Matthew | 40 |
| 071 | Mark | 41 |
| 072 | Luke | 42 |
| 073 | John | 43 |
| 074 | Acts | 44 |
| 075 | Romans | 45 |
| 076 | 1 Corinthians | 46 |
| 077 | 2 Corinthians | 47 |
| 078 | Galatians | 48 |
| 079 | Ephesians | 49 |
| 080 | Philippians | 50 |
| 081 | Colossians | 51 |
| 082 | 1 Thessalonians | 52 |
| 083 | 2 Thessalonians | 53 |
| 084 | 1 Timothy | 54 |
| 085 | 2 Timothy | 55 |
| 086 | Titus | 56 |
| 087 | Philemon | 57 |
| 088 | Hebrews | 58 |
| 089 | James | 59 |
| 090 | 1 Peter | 60 |
| 091 | 2 Peter | 61 |
| 092 | 1 John | 62 |
| 093 | 2 John | 63 |
| 094 | 3 John | 64 |
| 095 | Jude | 65 |
| 096 | Revelation | 66 |

## Output format

```
bbcccvvv verse text
```

- `bb` — book number, zero-padded (40–66)
- `ccc` — chapter number, zero-padded
- `vvv` — verse number, zero-padded
- single space, then the verse text

### Text cleaning notes

The readaloud files are already clean (no HTML, no footnotes, no Strong’s
numbers, no alternate versification markers), so no additional cleaning is
applied during conversion.
