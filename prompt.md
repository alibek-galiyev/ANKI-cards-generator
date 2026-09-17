# Task
Your task is to read English words from the file `words/dungeon_crawler_carl_all_words.csv` and generate Anki flashcard data, saving the result into an output file inside `anki_cards/` (e.g., `anki_cards/dungeon_crawler_carl_anki.csv`).

---

## Input File
- **Source path:** `words/dungeon_crawler_carl_all_words.csv`
- **Structure:** A CSV file containing a single column `word` listing one word per line (ordered by frequency in the novel).

## Output File
- **Target path:** `anki_cards/dungeon_crawler_carl_anki.csv`
- **Format:** Anki-compatible CSV using a semicolon (`;`) as the field delimiter.
- **File Mode:** If the output file does not exist, create it. If it exists and you are processing subsequent batches, append the new cards to the end of the file.

---

## Batching Instructions
Because the source file contains thousands of words, process words in batches (e.g., the top 50, 100, or a specified range of words, such as rows 1–50, 51–100):
- Read the specified slice of words from `words/dungeon_crawler_carl_all_words.csv`.
- Skip the header row (`word`).
- Generate one card per input word.
- Write or append the generated lines directly into `anki_cards/dungeon_crawler_carl_anki.csv`.

---

## Card Structure & Formatting Rules
Each line in the output file must represent exactly one Anki card with two fields:
```
[Front];[Back]
```

1. **Front:**
   - Use the word from the input CSV, in lowercase.

2. **Delimiter:**
   - Strictly one semicolon (`;`) separating the Front and Back fields.

3. **Back:**
   - Format the entire back side as a single continuous block using `<br>` for line breaks and `<b>` only for labels:
   ```html
   <b>Present form:</b> [the present/base form of the word]<br><b>Definition (EN):</b> [a short and clear definition in English]<br><b>Importance (1–10):</b> [a rating from 1 to 10 indicating how common and useful the word is]<br><b>Translation (RU):</b> [Russian translation of the present/base form]<br><b>Formed from:</b> [if derived, specify original base form and part of speech. If it is a base word, write "Base form"]<br><b>Simple sentence:</b> [one very simple sentence using the present/base form]
   ```

---

## Rules for Identifying the Present Form
- If the input is a past-tense verb, provide its present/base form. *(Example: went → go)*
- If the input is a past participle, provide its present/base form. *(Example: written → write)*
- If the input is a gerund/present participle, provide its base form. *(Example: running → run)*
- If the input is a third-person singular verb, provide its base form. *(Example: works → work)*
- If the input is a plural noun, provide its singular/base form. *(Example: children → child)*
- If the input is already in its base form, use the same word.
- For adjectives and other words without tense, use the standard dictionary base form.

---

## Strict Constraints
- **NO internal semicolons:** Never use semicolons (`;`) inside definitions, Russian translations, or example sentences, as this will break Anki's CSV column parsing. Use commas, hyphens, or periods instead.
- **NO extra lines per card:** Each card must be strictly on a single line. Use `<br>` for all line breaks on the Back.
- **NO Markdown or chatter in the CSV:** The file must contain only raw Anki card lines (`[Front];[Back]`).
- **One card per input word:** Exactly one card for each word processed from the input list.