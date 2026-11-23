"""SMOG and Coleman-Liau, scored with the shared M1 tokenizer.

Run: python m1_smog_coleman_liau.py
Both reuse the word, sentence and syllable rules from m1_flesch_kincaid.py,
so differences from the other M1 formulas come from the formula only.
"""

import json

from common import LEVELS, evaluate_measure, load_split
from m1_flesch_kincaid import SENTENCE_END, WORDS, syllables


def _counts(text):
    words = WORDS.findall(text)
    if not words:
        raise ValueError("Cannot score an explanation with no words.")
    sentences = sum(bool(WORDS.search(chunk)) for chunk in SENTENCE_END.split(text))
    return words, max(1, sentences)


def smog(text):
    """McLaughlin (1969) SMOG grade, normalized to a 30-sentence sample."""
    words, sentences = _counts(text)
    polysyllables = sum(syllables(word) >= 3 for word in words)
    return 1.0430 * (polysyllables * 30 / sentences) ** 0.5 + 3.1291


def coleman_liau(text):
    """Coleman and Liau (1975) index: letters and sentences per 100 words."""
    words, sentences = _counts(text)
    letters = sum(char.isalpha() for word in words for char in word)
    per_100 = 100 / len(words)
    return 0.0588 * letters * per_100 - 0.296 * sentences * per_100 - 15.8


def main():
    _, train, dev, _, digest = load_split()
    results = {"level_order": LEVELS, "source_sha256": digest}
    for name, formula in (("smog", smog), ("coleman_liau", coleman_liau)):
        results[name] = evaluate_measure(train, dev, lambda row, f=formula: f(row["Explanation"]))
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
