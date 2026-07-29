# F35 → F35_MES Pipeline

Reproducible conversion of the Family 35 Greek New Testament (`F35.txt`) to the
MES specification format with Stephanus 1551 versification (`F35_MES.txt`).

## Contents

| File | Description |
|---|---|
| `F35.txt` | Family 35 Greek NT in `bbcccvvv` format (7954 verses, NT-only) |
| `ST.txt` | Stephanus 1551 reference exemplar (7957 verses, NT-only) |
| `convert_mes.py` | Re-aligns F35 verses to Stephanus 1551 boundaries |
| `verify.py` | Validates `bbcccvvv` format, encoding, scope, cleanliness |
| `Makefile` | Build automation |
| `MES.g4` | ANTLR grammar for the MES specification format |

## Prerequisites

- Python ≥ 3.8

## Usage

```bash
# Re-verse F35 to Stephanus 1551 versification
make

# Same as above, but manually:
python convert_mes.py --input F35.txt --sr ST.txt --output F35_MES.txt

# Verify the output
make verify

# Or manually:
python verify.py F35_MES.txt

# Clean generated files
make clean
```

## Output

`F35_MES.txt` — 7957 lines, one per Stephanus verse:

```
40001001 Βίβλος γενέσεως Ἰησοῦ Χριστοῦ…
…
44019040 …⋄41Καὶ ταῦτα εἰπὼν ἀπέλυσεν τὴν ἐκκλησίαν.
…
66022021 Ἡ χάρις τοῦ Κυρίου Ἰησοῦ Χριστοῦ μετὰ πάντων τῶν ἁγίων. Ἀμήν.,
```

- **All lines** match `^[0-9]{8} .+`
- **References** are 8 digits: `bbcccvvv` (book 40–66, NT-only)
- **Empty verses** (present in SR but absent in F35) show `-`
- **⋄ markers** indicate where F35 verse boundaries differ from Stephanus

## Versification differences

Nine chapters have verse-count differences between F35 and Stephanus 1551 (ST).  
Where F35 has more verses than ST, the extra content is merged into the last ST  
verse with ⋄ markers. Where ST has more verses than F35, the difference is shown  
as `-` (empty).

| Chapter | ST vv. | F35 vv. | Δ | Notes |
|---|---|---|---|---|
| Luke 17 | 37 | 36 | −1 | ST v. 36 empty (even in TR) |
| Acts 8 | 40 | 39 | −1 | F35 one verse shorter |
| Acts 15 | 41 | 40 | −1 | F35 one verse shorter |
| Acts 19 | 40 | 41 | +1 | F35 v. 41 merged with ⋄ into ST v. 40 |
| Acts 24 | 27 | 26 | −1 | F35 one verse shorter |
| Romans 14 | 23 | 26 | +3 | F35 vv. 24–26 merged with ⋄ into ST v. 23 |
| Romans 16 | 27 | 24 | −3 | ST vv. 24, 26, 27 empty (no doxology in F35) |
| 2 Cor 13 | 13 | 14 | +1 | F35 v. 14 merged with ⋄ into ST v. 13 |
| Rev 12 | 18 | 17 | −1 | ST v. 18 empty |
