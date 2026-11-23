"""Fit two word-count thresholds on train and report M0 dev metrics."""

import json
import re
from collections import Counter, defaultdict
from urllib.request import urlopen

from m0_majority import LABEL_FIELDS, LEVELS, SOURCE, split_by_question


def word_count(row):
    return len(re.findall(r"\b[\w]+(?:['’-][\w]+)*\b", row["Explanation"]))


def fit_thresholds(train, field):
    by_length = defaultdict(Counter)
    for row in train:
        by_length[word_count(row)][row[field]] += 1
    lengths = sorted(by_length)
    prefixes = [[0, 0, 0]]
    for length in lengths:
        prefixes.append([
            previous + by_length[length][level]
            for previous, level in zip(prefixes[-1], LEVELS)
        ])
    best = None
    best_correct = -1
    for i, low in enumerate(lengths[:-2], start=1):
        for j in range(i + 1, len(lengths)):
            correct = (
                prefixes[i][0]
                + prefixes[j][1] - prefixes[i][1]
                + prefixes[-1][2] - prefixes[j][2]
            )
            if correct > best_correct:
                best = (low, lengths[j - 1])
                best_correct = correct
    if best is None:
        raise ValueError("Need at least three distinct training word counts.")
    return best


def score(dev, field, thresholds):
    low, high = thresholds
    counts = Counter()
    for row in dev:
        length = word_count(row)
        predicted = int(length > low) + int(length > high)
        counts[LEVELS.index(row[field]), predicted] += 1

    total = len(dev)
    f1 = []
    for level in range(len(LEVELS)):
        support = sum(n for (actual, _), n in counts.items() if actual == level)
        predicted = sum(n for (_, guess), n in counts.items() if guess == level)
        f1.append(2 * counts[level, level] / (support + predicted) if support + predicted else 0)
    return {
        "thresholds": thresholds,
        "accuracy": sum(counts[i, i] for i in range(len(LEVELS))) / total,
        "macro_f1": sum(f1) / len(LEVELS),
        "mean_absolute_ordinal_error": sum(abs(a - p) * n for (a, p), n in counts.items()) / total,
    }


def main():
    with urlopen(SOURCE, timeout=60) as response:
        rows = [json.loads(line) for line in response if line.strip()]
    _, train, dev = split_by_question(rows)
    results = {
        name: score(dev, field, fit_thresholds(train, field))
        for name, field in LABEL_FIELDS.items()
    }
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
