"""100% Local Anki card generator using WordNet, local translation caching, and book context."""

import csv
import logging
from pathlib import Path
import sqlite3
import time
from typing import Optional

import nltk
from nltk.corpus import wordnet as wn
import translators as ts
from wordfreq import zipf_frequency

logger = logging.getLogger(__name__)


class TranslationCache:
    """Persistent SQLite cache for English-to-Russian word translations."""

    def __init__(self, db_path: str = "data/translations_cache.sqlite"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self._init_db()

    def _init_db(self):
        with self.conn:
            self.conn.execute(
                """
                CREATE TABLE IF NOT EXISTS translations (
                    word TEXT PRIMARY KEY,
                    translation TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """
            )

    def get(self, word: str) -> Optional[str]:
        cur = self.conn.cursor()
        cur.execute("SELECT translation FROM translations WHERE word = ?", (word.lower().strip(),))
        row = cur.fetchone()
        return row[0] if row else None

    def get_many(self, words: list[str]) -> dict[str, str]:
        results = {}
        cur = self.conn.cursor()
        for i in range(0, len(words), 500):
            chunk = words[i : i + 500]
            placeholders = ",".join("?" for _ in chunk)
            cur.execute(
                f"SELECT word, translation FROM translations WHERE word IN ({placeholders})",
                [w.lower().strip() for w in chunk],
            )
            for row in cur.fetchall():
                results[row[0]] = row[1]
        return results

    def set(self, word: str, translation: str):
        with self.conn:
            self.conn.execute(
                "INSERT OR REPLACE INTO translations (word, translation) VALUES (?, ?)",
                (word.lower().strip(), translation.strip()),
            )

    def set_many(self, pairs: dict[str, str]):
        with self.conn:
            self.conn.executemany(
                "INSERT OR REPLACE INTO translations (word, translation) VALUES (?, ?)",
                [(k.lower().strip(), v.strip()) for k, v in pairs.items()],
            )


class LocalAnkiGenerator:
    """Generates Anki cards entirely locally in Python (zero Gemini calls)."""

    def __init__(self, cache_db: str = "data/translations_cache.sqlite"):
        # Ensure WordNet is available locally
        try:
            wn.synsets("dog")
        except LookupError:
            logger.info("Downloading NLTK WordNet dataset locally...")
            nltk.download("wordnet", quiet=True)

        self.cache = TranslationCache(cache_db)

    def get_definition(self, word: str) -> str:
        """Fetch short English definition from Princeton WordNet."""
        syns = wn.synsets(word)
        if syns:
            definition = syns[0].definition().strip()
            # Sanitize internal semicolons
            return definition.replace(";", ",")
        return "Definition not available"

    def get_example_sentence(self, word: str, context_sentence: Optional[str] = None) -> str:
        """Return sentence context from novel, or fallback to WordNet example."""
        if context_sentence and 15 <= len(context_sentence) <= 220:
            return context_sentence.replace(";", ",")

        syns = wn.synsets(word)
        if syns and syns[0].examples():
            return syns[0].examples()[0].replace(";", ",")

        return f"The {word} appeared in the story."

    def translate_batch(self, words: list[str]) -> dict[str, str]:
        """Translate words in batches with persistent local cache."""
        cached = self.cache.get_many(words)
        missing = [w for w in words if w not in cached]

        if not missing:
            return cached

        logger.info("Translating %d words (batch of %d)...", len(missing), len(words))
        new_translations = {}

        # Translate missing words in batches of up to 40 words
        batch_size = 40
        for i in range(0, len(missing), batch_size):
            chunk = missing[i : i + batch_size]
            text = "\n".join(chunk)
            translated_lines = []

            for engine in ("bing", "google", "yandex"):
                try:
                    res = ts.translate_text(
                        text, from_language="en", to_language="ru", translator=engine, timeout=15
                    )
                    translated_lines = [line.strip().replace(";", ",") for line in res.splitlines()]
                    if len(translated_lines) == len(chunk):
                        break
                except Exception as e:
                    logger.debug("Engine '%s' failed: %s", engine, e)
                    continue

            if len(translated_lines) == len(chunk):
                for w, t in zip(chunk, translated_lines):
                    new_translations[w] = t
            else:
                # Individual fallback if batch alignment failed
                for w in chunk:
                    try:
                        res = ts.translate_text(w, from_language="en", to_language="ru", translator="bing")
                        new_translations[w] = res.strip().replace(";", ",")
                    except Exception:
                        new_translations[w] = w  # fallback

            time.sleep(0.3)

        self.cache.set_many(new_translations)
        cached.update(new_translations)
        return cached

    def build_card(
        self,
        word: str,
        translation: str,
        context_sentence: Optional[str] = None,
    ) -> str:
        """Format a single Anki card string following the exact prompt schema."""
        word = word.lower().strip()
        definition = self.get_definition(word)
        sentence = self.get_example_sentence(word, context_sentence)

        zipf = zipf_frequency(word, "en")
        importance = min(10, max(1, round(zipf * 1.5)))

        back = (
            f"<b>Present form:</b> {word}<br>"
            f"<b>Definition (EN):</b> {definition}<br>"
            f"<b>Importance (1–10):</b> {importance}<br>"
            f"<b>Translation (RU):</b> {translation}<br>"
            f"<b>Formed from:</b> Base form<br>"
            f"<b>Simple sentence:</b> {sentence}"
        )

        return f"{word};{back}"

    def generate_deck(
        self,
        words: list[str],
        output_file: str,
        sentences_map: Optional[dict[str, str]] = None,
    ):
        """Generate full Anki CSV deck from list of words."""
        sentences_map = sentences_map or {}
        out_path = Path(output_file)
        out_path.parent.mkdir(parents=True, exist_ok=True)

        existing_words = set()
        if out_path.exists():
            with open(out_path, "r", encoding="utf-8") as f:
                for line in f:
                    if ";" in line:
                        existing_words.add(line.split(";", 1)[0].strip().lower())

        remaining = [w for w in words if w.lower().strip() not in existing_words]
        logger.info("Total words: %d | Existing: %d | Remaining: %d", len(words), len(existing_words), len(remaining))

        if not remaining:
            print(f"All {len(words)} cards are already generated in '{output_file}'!")
            return

        # Translate in batches
        translations = self.translate_batch(remaining)

        with open(out_path, "a", newline="", encoding="utf-8") as f:
            for w in remaining:
                trans = translations.get(w, w)
                ctx = sentences_map.get(w)
                card = self.build_card(w, trans, ctx)
                f.write(card + "\n")

        print(f"Successfully generated and saved {len(words)} Anki cards to '{output_file}'.")
