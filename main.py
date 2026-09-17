"""BookWords - Extract clean base vocabulary from any book file."""

from pathlib import Path
import sys

# Support running directly without installing package
sys.path.insert(0, str(Path(__file__).parent / "src"))

from book_words.extractors import extract_text_sections
from book_words.lemmatizer import VocabularyConfig, VocabularyProcessor

# ================= Configuration =================
# Can be overridden via CLI: `python main.py [path_to_book] [output_csv]`
DEFAULT_BOOK_PATH = "books/Dungeon_Crawler_Carl_-_Matt_Dinniman.epub"
BOOK_PATH = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_BOOK_PATH

if len(sys.argv) > 2:
    OUTPUT_PATH = sys.argv[2]
elif len(sys.argv) > 1:
    book_stem = Path(BOOK_PATH).stem.lower().replace(" ", "_").replace("-", "_")
    OUTPUT_PATH = f"words/{book_stem}_all_words.csv"
else:
    OUTPUT_PATH = "words/dungeon_crawler_carl_all_words.csv"

# Vocabulary frequency filters (Zipf score):
ZIPF_MAX = 4.0
ZIPF_MIN = 0.5
MIN_BOOK_COUNT = 2
SORT_BY = "book_count"
# =================================================


def main():
    print(f"Reading '{BOOK_PATH}'...")
    sections = extract_text_sections(BOOK_PATH)
    print(f"Extracted {len(sections)} sections.")

    config = VocabularyConfig(
        zipf_min=ZIPF_MIN,
        zipf_max=ZIPF_MAX,
        min_book_count=MIN_BOOK_COUNT,
        sort_by=SORT_BY,
    )

    processor = VocabularyProcessor()
    words = processor.process(sections, config)

    output_path = Path(OUTPUT_PATH)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        f.write("word\n")
        for entry in words:
            f.write(f"{entry.lemma}\n")

    print(f"Done! Successfully saved {len(words)} unique words to '{OUTPUT_PATH}'.")
    if words:
        print("\nTop 15 highest-impact words:")
        for w in words[:15]:
            print(f"  • {w.lemma:<15} (in book: {w.count:>3}x, Zipf: {w.zipf_score:.2f})")


if __name__ == "__main__":
    main()