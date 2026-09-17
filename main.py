"""BookWords - Extract clean base vocabulary from any book file and optionally generate Anki cards."""

import argparse
from pathlib import Path
import sys

# Support running directly without installing package
sys.path.insert(0, str(Path(__file__).parent / "src"))

from book_words.extractors import extract_text_sections
from book_words.lemmatizer import VocabularyConfig, VocabularyProcessor
from book_words.anki_generator import LocalAnkiGenerator

def main():
    parser = argparse.ArgumentParser(description="Extract vocabulary and generate Anki cards.")
    parser.add_argument("book_path", help="Path to the book file")
    parser.add_argument("output_anki_csv", nargs="?", help="Path for output Anki CSV")
    parser.add_argument("--mode", choices=["python", "llm"], default="python", help="Generation mode (python or llm)")
    parser.add_argument("--min-count", type=int, default=1, help="Minimum occurrences in book")
    parser.add_argument("--zipf-max", type=float, default=4.0, help="Maximum Zipf score")
    parser.add_argument("--zipf-min", type=float, default=0.5, help="Minimum Zipf score")
    parser.add_argument("--sort-by", choices=["book_count", "rarity"], default="book_count", help="Sort order")
    
    args = parser.parse_args()

    book_path = Path(args.book_path)
    if not book_path.exists():
        print(f"Error: File not found: {book_path}")
        sys.exit(1)

    book_stem = book_path.stem.lower().replace(" ", "_").replace("-", "_")
    
    if args.output_anki_csv:
        anki_output_path = Path(args.output_anki_csv)
    else:
        anki_output_path = Path("anki_cards") / f"{book_stem}_anki.csv"

    words_output_path = Path("words") / f"{book_stem}_all_words.csv"

    print(f"Reading '{book_path}'...")
    sections = extract_text_sections(str(book_path))
    if not sections:
        print(f"Error: No readable text could be extracted from '{book_path}'.")
        sys.exit(1)
    
    print(f"Extracted {len(sections)} sections.")

    config = VocabularyConfig(
        zipf_min=args.zipf_min,
        zipf_max=args.zipf_max,
        min_book_count=args.min_count,
        sort_by=args.sort_by,
    )

    processor = VocabularyProcessor()
    words = processor.process(sections, config)

    words_output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(words_output_path, "w", newline="", encoding="utf-8") as f:
        f.write("word\n")
        for entry in words:
            f.write(f"{entry.lemma}\n")

    print(f"Done! Successfully saved {len(words)} unique words to '{words_output_path}'.")
    if words:
        print("\nTop 15 highest-impact words:")
        for w in words[:15]:
            print(f"  • {w.lemma:<15} (in book: {w.count:>3}x, Zipf: {w.zipf_score:.2f})")

    if args.mode == "python":
        print(f"\nGenerating Anki cards for {len(words)} words locally...")
        anki_output_path.parent.mkdir(parents=True, exist_ok=True)
        generator = LocalAnkiGenerator()
        word_list = [entry.lemma for entry in words]
        generator.generate_deck(word_list, str(anki_output_path))
    elif args.mode == "llm":
        print(f"\nVocabulary extracted to {words_output_path}.")
        print("To generate Anki cards using an LLM:")
        print("1. Open prompt.md and copy its contents to your LLM.")
        print(f"2. Provide batches of words from '{words_output_path}' to the LLM.")
        print("3. Save the LLM's output to a CSV file and import into Anki.")

if __name__ == "__main__":
    main()