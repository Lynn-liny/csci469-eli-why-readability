"""Compare three readability scores on the same ELI-Why development split.

Reproduction steps and expected results are in M1_REPRODUCTION.md.
"""

import json
from collections import Counter
from statistics import mean
from urllib.request import urlopen

from m0_majority import LABEL_FIELDS, LEVELS, SOURCE, split_by_question
from m0_word_count import word_count
from m1_flesch_kincaid import SENTENCE_END, WORDS, fit_thresholds, grade_level, syllables


def reading_ease(text):
    """Compute Flesch Reading Ease using the same counts as Grade Level."""
    words = WORDS.findall(text)
    if not words:
        raise ValueError("Cannot score an explanation with no words.")
    sentences = sum(bool(WORDS.search(chunk)) for chunk in SENTENCE_END.split(text))
    return 206.835 - 1.015 * len(words) / sentences - 84.6 * mean(map(syllables, words))


def evaluate(train, dev, field, measure, *, higher_means_easier=False):
    # The common threshold fitter expects larger scores to mean harder text.
    direction = -1 if higher_means_easier else 1
    train_examples = [(direction * measure(row), LEVELS.index(row[field])) for row in train]
    low, high = fit_thresholds(train_examples)

    # Freeze the training cutoffs before scoring development examples.
    counts = Counter()
    for row in dev:
        score = direction * measure(row)
        predicted = int(score > low) + int(score > high)
        counts[LEVELS.index(row[field]), predicted] += 1
    matrix = [[counts[i, j] for j in range(len(LEVELS))] for i in range(len(LEVELS))]
    per_level_f1 = {}
    for i, level in enumerate(LEVELS):
        denominator = sum(matrix[i]) + sum(row[i] for row in matrix)
        per_level_f1[level] = 2 * matrix[i][i] / denominator if denominator else 0.0

    return {
        "thresholds_in_raw_score_order_elementary_then_graduate": [direction * low, direction * high],
        "accuracy": sum(matrix[i][i] for i in range(len(LEVELS))) / len(dev),
        "macro_f1": mean(per_level_f1.values()),
        "mean_absolute_ordinal_error": sum(abs(i - j) * n for (i, j), n in counts.items()) / len(dev),
        "per_level_f1": per_level_f1,
        "confusion_matrix_actual_rows_predicted_columns": matrix,
    }


def main():
    with urlopen(SOURCE, timeout=60) as response:
        rows = [json.loads(line) for line in response if line.strip()]
    _, train, dev = split_by_question(rows)
    results = {"level_order": LEVELS}
    for name, field in LABEL_FIELDS.items():
        results[name] = {
            "word_count": evaluate(train, dev, field, word_count),
            "flesch_kincaid": evaluate(train, dev, field, lambda row: grade_level(row["Explanation"])),
            "flesch_reading_ease": evaluate(
                train, dev, field, lambda row: reading_ease(row["Explanation"]),
                higher_means_easier=True,
            ),
        }
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
