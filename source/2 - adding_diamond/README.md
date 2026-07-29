# Step 2 — Convert F35 to MES format (Stephanus versification)

Convertit F35.txt (F35 NA versification) en F35_MES.txt (Stephanus 1551 versification).

## Usage

```bash
python3 convert_step2.py --f35 F35.txt --st ST.txt --output F35_MES.txt
```

## Entrée

- `F35.txt` — texte grec du F35 (versification F35 NA)
- `ST.txt` — texte grec du Stephanus 1551 (versification de référence)

## Sortie

- `F35_MES.txt` — 7957 lignes, format `bbcccvvv texte`
  - Versets alignés sur la versification Stephanus
  - `⋄` marque les endroits où la frontière F35 diffère de ST
  - `-` pour les versets ST vides dans F35
  - 18 marqueurs ⋄, 8 versets vides

## Algorithme

1. Charge F35 et ST par référence `(book, chapter, verse)`
2. Pour chaque verset ST v(k), cherche `rough(F35 v(i))` dans `rough(ST v(k))`
3. Si trouvé, cherche le début du prochain verset F35 (préfixe 20→8 caractères)
4. Si trouvé après la fin du verset courant → la frontière diffère → insère `⋄`
5. `split_at_st()` découpe le texte F35 à la frontière du verset ST suivant
