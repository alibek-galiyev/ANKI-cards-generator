"""Unified command line interface for BookWords."""

import argparse
import logging
from pathlib import Path
import sys

from book_words.extractors import extract_text_sections
from book_words.lemmatizer import VocabularyConfig, VocabularyProcessor
from book_words.anki_generator import LocalAnkiGenerator

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def extract_command(args):
    """Extract vocabulary from a book file."""
    book_path = Path(args.book)
    if not book_path.exists():
        logger.error("File not found: %s", args.book)
        sys.exit(1)

    if args.output:
        output_path = Path(args.output)
    else:
        book_stem = book_path.stem.lower().replace(" ", "_").replace("-", "_")
        output_path = Path("words") / f"{book_stem}_all_words.csv"

    output_path.parent.mkdir(parents=True, exist_ok=True)

    config = VocabularyConfig(
        zipf_min=args.zipf_min,
        zipf_max=args.zipf_max,
        min_book_count=args.min_count,
        sort_by=args.sort_by,
    )

    print(f"Reading '{book_path}'...")
    sections = extract_text_sections(str(book_path))
    if not sections:
        logger.error("No readable text could be extracted from '%s'.", book_path)
        sys.exit(1)

    processor = VocabularyProcessor()
    words = processor.process(sections, config)

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        f.write("word\n")
        for entry in words:
            f.write(f"{entry.lemma}\n")

    print(f"Done! Successfully saved {len(words)} words to '{output_path}'.")
    if words:
        print("\nTop 10 highest-impact words:")
        for w in words[:10]:
            print(f"  • {w.lemma:<15} (in book: {w.count:>3}x, Zipf: {w.zipf_score:.2f})")


def anki_command(args):
    """Generate Anki cards from a vocabulary CSV file."""
    words_path = Path(args.words_file)
    if not words_path.exists():
        logger.error("File not found: %s", args.words_file)
        sys.exit(1)

    if args.output:
        output_path = Path(args.output)
    else:
        stem = words_path.stem.replace("_all_words", "").replace("_words", "")
        output_path = Path("anki_cards") / f"{stem}_anki.csv"

    words = []
    with open(words_path, "r", encoding="utf-8") as f:
        for i, line in enumerate(f):
            word = line.strip().lower()
            if i == 0 and word == "word":
                continue
            if word:
                words.append(word)

    print(f"Generating Anki cards for {len(words)} words locally...")
    generator = LocalAnkiGenerator()
    generator.generate_deck(words, str(output_path))


def main():
    parser = argparse.ArgumentParser(
        description="BookWords - Extract book vocabulary and generate Anki flashcards 100% locally."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Subcommand: extract
    p_extract = subparsers.add_parser("extract", help="Extract base vocabulary from any book file.")
    p_extract.add_argument("book", help="Path to book (.epub, .fb2, .txt, .pdf, .mobi, .csv)")
    p_extract.add_argument("-o", "--output", help="Path to save output CSV (default: words/<name>_all_words.csv)")
    p_extract.add_argument("--zipf-min", type=float, default=0.5, help="Minimum Zipf score (default: 0.5)")
    p_extract.add_argument("--zipf-max", type=float, default=4.0, help="Maximum Zipf score (default: 4.0)")
    p_extract.add_argument("--min-count", type=int, default=2, help="Minimum occurrences in book (default: 2)")
    p_extract.add_argument(
        "--sort-by", choices=["book_count", "rarity"], default="book_count", help="Sort order (default: book_count)"
    )
    p_extract.set_defaults(func=extract_command)

    # Subcommand: anki
    p_anki = subparsers.add_parser("anki", help="Generate Anki cards locally from vocabulary CSV.")
    p_anki.add_argument("words_file", help="Path to words CSV file (e.g. words/mybook_all_words.csv)")
    p_anki.add_argument("-o", "--output", help="Path to save Anki cards (default: anki_cards/<name>_anki.csv)")
    p_anki.set_defaults(func=anki_command)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
