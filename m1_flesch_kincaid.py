"""Evaluate Flesch-Kincaid Grade Level with train-only ordinal cutoffs.

Run with python m1_flesch_kincaid.py. For --validate-textstat, install
textstat==0.7.13 and have the NLTK cmudict corpus available.
"""

import argparse
import json
import random
import re
from collections import Counter, defaultdict
from statistics import mean
from urllib.request import urlopen

from m0_majority import LABEL_FIELDS, LEVELS, SOURCE, split_by_question

WORDS = re.compile(r"\b[\w]+(?:['’-][\w]+)*\b")
SENTENCE_END = re.compile(r"""[.!?]+['"’”)]*(?=\s|$)""")
VOWELS = re.compile(r"[aeiouy]+")


def syllables(word):
    parts = re.findall(r"[a-z]+", word.lower())
    count = 0
    for part in parts:
        groups = len(VOWELS.findall(part))
        consonant_le = re.search(r"[^aeiouy]le$", part)
        if groups > 1 and part.endswith("e") and not consonant_le:
            groups -= 1
        count += max(1, groups)
    return max(1, count)


def grade_level(text):
    words = WORDS.findall(text)
    if not words:
        raise ValueError("Cannot score an explanation with no words.")
    sentences = sum(bool(WORDS.search(chunk)) for chunk in SENTENCE_END.split(text))
    return 0.39 * len(words) / sentences + 11.8 * mean(map(syllables, words)) - 15.59


def fit_thresholds(examples):
    groups = defaultdict(Counter)
    for grade, level in examples:
        groups[grade][level] += 1
    grades = sorted(groups)
    if len(grades) < 3:
        raise ValueError("Need at least three distinct training grade scores.")
    prefix = [[0] * len(LEVELS)]
    for grade in grades:
        prefix.append([n + groups[grade][i] for i, n in enumerate(prefix[-1])])

    best_correct = -1
    for low in range(1, len(grades) - 1):
        for high in range(low + 1, len(grades)):
            correct = (
                prefix[low][0]
                + prefix[high][1] - prefix[low][1]
                + prefix[-1][2] - prefix[high][2]
            )
            if correct > best_correct:
                best_correct = correct
                thresholds = (grades[low - 1], grades[high - 1])
    return thresholds


def evaluate(examples, thresholds):
    low, high = thresholds
    counts = Counter((level, int(grade > low) + int(grade > high))
                     for grade, level in examples)
    f1 = []
    for i in range(len(LEVELS)):
        support = sum(n for (actual, _), n in counts.items() if actual == i)
        predicted = sum(n for (_, guess), n in counts.items() if guess == i)
        f1.append(2 * counts[i, i] / (support + predicted) if support + predicted else 0)
    return {
        "thresholds": thresholds,
        "accuracy": sum(counts[i, i] for i in range(len(LEVELS))) / len(examples),
        "macro_f1": mean(f1),
        "mean_absolute_ordinal_error": (
            sum(abs(a - p) * n for (a, p), n in counts.items()) / len(examples)
        ),
    }


def compare_with_textstat(train):
    from textstat import textstat

    textstat.set_lang("en_US")
    sample = random.Random(469).sample(train, 100)
    errors = [
        grade - textstat.flesch_kincaid_grade(row["Explanation"])
        for row, grade in sample
    ]
    return {
        "n_train": len(sample),
        "mean_signed_grade_difference": mean(errors),
        "mean_absolute_grade_difference": mean(map(abs, errors)),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--validate-textstat", action="store_true",
                        help="Compare 100 training scores with textstat 0.7.13.")
    args = parser.parse_args()
    with urlopen(SOURCE, timeout=60) as response:
        rows = [json.loads(line) for line in response if line.strip()]
    _, train, dev = split_by_question(rows)
    train = [(row, grade_level(row["Explanation"])) for row in train]
    dev = [(row, grade_level(row["Explanation"])) for row in dev]
    results = {}
    for name, field in LABEL_FIELDS.items():
        train_examples = [(grade, LEVELS.index(row[field])) for row, grade in train]
        dev_examples = [(grade, LEVELS.index(row[field])) for row, grade in dev]
        results[name] = evaluate(dev_examples, fit_thresholds(train_examples))
    if args.validate_textstat:
        results["textstat_validation"] = compare_with_textstat(train)
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
