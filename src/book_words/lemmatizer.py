"""Natural Language Processing pipeline for lemmatization, POS tagging, and Zipf scoring."""

from collections import Counter, defaultdict
from dataclasses import dataclass, field
import logging
import re
from typing import Optional

import lemminflect
import spacy
from wordfreq import zipf_frequency

logger = logging.getLogger(__name__)


@dataclass
class WordEntry:
    lemma: str
    count: int
    zipf_score: float
    pos: str
    example_sentence: Optional[str] = None


@dataclass
class VocabularyConfig:
    zipf_min: float = 0.5
    zipf_max: float = 4.0
    min_book_count: int = 2
    sort_by: str = "book_count"  # "book_count" or "rarity"
    min_word_len: int = 3


class VocabularyProcessor:
    """Processes text with spaCy and lemminflect to extract prioritized vocabulary."""

    def __init__(self, model_name: str = "en_core_web_sm"):
        logger.info("Loading spaCy model '%s' with lemminflect...", model_name)
        self.nlp = spacy.load(model_name, disable=["ner"])
        # Ensure sentence boundaries are enabled for example extraction
        if "sentencizer" not in self.nlp.pipe_names and "parser" not in self.nlp.pipe_names:
            self.nlp.add_pipe("sentencizer")

    def process(
        self, text_sections: list[str], config: Optional[VocabularyConfig] = None
    ) -> list[WordEntry]:
        """Extracts and filters base vocabulary from a list of text sections."""
        if config is None:
            config = VocabularyConfig()

        word_counts = Counter()
        propn_counts = Counter()
        pos_counts = defaultdict(Counter)
        example_sentences = {}

        logger.info("Processing %d text sections through NLP pipeline...", len(text_sections))
        for doc in self.nlp.pipe(text_sections, batch_size=10):
            # Track sentences for context extraction
            for sent in doc.sents:
                sent_text = sent.text.strip()
                # Clean multiple spaces/newlines
                clean_sent = re.sub(r"\s+", " ", sent_text)
                if not (15 <= len(clean_sent) <= 200):
                    continue

                for token in sent:
                    if not token.is_alpha or len(token.text) < config.min_word_len:
                        continue

                    # Accurate dictionary-based lemma
                    lemma = token._.lemma()
                    if not lemma:
                        lemma = token.lemma_
                    lemma = lemma.lower()

                    if lemma not in example_sentences and clean_sent:
                        example_sentences[lemma] = clean_sent

            # Token-level stats across doc
            for token in doc:
                if not token.is_alpha or len(token.text) < config.min_word_len:
                    continue

                lemma = token._.lemma()
                if not lemma:
                    lemma = token.lemma_
                lemma = lemma.lower()

                pos = token.pos_
                pos_counts[lemma][pos] += 1
                if pos == "PROPN":
                    propn_counts[lemma] += 1
                else:
                    word_counts[lemma] += 1

        # Filter words
        results = []
        for lemma, count in word_counts.items():
            # Stopwords filter by base lemma
            if lemma in self.nlp.Defaults.stop_words or self.nlp.vocab[lemma].is_stop:
                continue

            # Proper nouns / character names filter
            if propn_counts[lemma] >= count:
                continue

            # Minimum occurrence threshold
            if count < config.min_book_count:
                continue

            # Zipf frequency score
            score = zipf_frequency(lemma, "en")
            if not (config.zipf_min <= score <= config.zipf_max):
                continue

            # Primary part of speech
            primary_pos = pos_counts[lemma].most_common(1)[0][0] if pos_counts[lemma] else "NOUN"
            sentence = example_sentences.get(lemma)

            results.append(
                WordEntry(
                    lemma=lemma,
                    count=count,
                    zipf_score=score,
                    pos=primary_pos,
                    example_sentence=sentence,
                )
            )

        # Sorting
        if config.sort_by == "book_count":
            results.sort(key=lambda x: (-x.count, x.zipf_score))
        else:
            results.sort(key=lambda x: (x.zipf_score, -x.count))

        logger.info("Extracted %d unique filtered vocabulary words.", len(results))
        return results
