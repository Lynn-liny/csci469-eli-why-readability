"""Evaluate the Automated Readability Index on the ELI-Why dev split."""

import json
from urllib.request import urlopen

from m0_majority import LABEL_FIELDS, LEVELS, SOURCE, split_by_question
from m1_flesch_kincaid import SENTENCE_END, WORDS
from m1_flesch_reading_ease import evaluate


def automated_readability_index(text):
    words = WORDS.findall(text)
    if not words:
        raise ValueError("Cannot score an explanation with no words.")
    # Count letters and digits inside word tokens and reuse M1 sentence boundaries.
    characters = sum(char.isalnum() for word in words for char in word)
    sentences = sum(bool(WORDS.search(chunk)) for chunk in SENTENCE_END.split(text))
    return 4.71 * characters / len(words) + 0.5 * len(words) / sentences - 21.43


def main():
    with urlopen(SOURCE, timeout=60) as response:
        rows = [json.loads(line) for line in response if line.strip()]
    _, train, dev = split_by_question(rows)
    results = {"level_order": LEVELS}
    for name, field in LABEL_FIELDS.items():
        results[name] = evaluate(
            train, dev, field, lambda row: automated_readability_index(row["Explanation"])
        )
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
