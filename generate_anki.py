"""BookWords - Generate Anki flashcards 100% locally in Python (Zero Gemini calls)."""

from pathlib import Path
import sys

# Support running directly without installing package
sys.path.insert(0, str(Path(__file__).parent / "src"))

from book_words.anki_generator import LocalAnkiGenerator

# ================= Configuration =================
# Can be overridden via CLI: `python generate_anki.py [input_words_csv] [output_anki_csv]`
DEFAULT_INPUT_CSV = "words/dungeon_crawler_carl_all_words.csv"
INPUT_CSV = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_INPUT_CSV

if len(sys.argv) > 2:
    OUTPUT_CSV = sys.argv[2]
elif len(sys.argv) > 1:
    input_stem = Path(INPUT_CSV).stem.replace("_all_words", "").replace("_words", "")
    OUTPUT_CSV = f"anki_cards/{input_stem}_anki.csv"
else:
    OUTPUT_CSV = "anki_cards/dungeon_crawler_carl_anki.csv"
# =================================================


def main():
    words_path = Path(INPUT_CSV)
    if not words_path.exists():
        print(f"Error: Input file '{INPUT_CSV}' not found.")
        sys.exit(1)

    words = []
    with open(words_path, "r", encoding="utf-8") as f:
        for i, line in enumerate(f):
            w = line.strip().lower()
            if i == 0 and w == "word":
                continue
            if w:
                words.append(w)

    print(f"Loaded {len(words)} words from '{INPUT_CSV}'.")
    print(f"Generating Anki cards locally into '{OUTPUT_CSV}'...")

    generator = LocalAnkiGenerator()
    generator.generate_deck(words, OUTPUT_CSV)


if __name__ == "__main__":
    main()
