"""Run the M0 majority-class baseline on the ELI-Why human-annotated subset.

Run: python m0_majority.py
Dev reference: perceived accuracy 128/240, macro-F1 0.231884,
mean absolute ordinal error 0.466667. Intended accuracy 80/240.
This split covers the annotated subset. Reuse its question assignments
when constructing the full split to avoid question leakage.
"""

import argparse
import hashlib
import json
import random
from collections import Counter, defaultdict
from pathlib import Path
from urllib.request import urlopen

SOURCE = (
    "https://huggingface.co/datasets/INK-USC/eli-why-perceived-background-match"
    "/resolve/aa89f444f176eafa00f4c5c75e1d66746c1b60bf/"
    "perceived_background_match_with_explanations.jsonl"
)
LEVELS = ("Elementary", "High School", "Graduate")
SEED = 469
LABEL_FIELDS = {
    "perceived": "Perceived Educational Background",
    "intended": "Intended Educational Background",
}


def split_by_question(rows):
    grouped = defaultdict(list)
    for row in rows:
        grouped[row["Question"]].append(row)
    if len(grouped) != 400 or any(
        Counter(row[LABEL_FIELDS["intended"]] for row in group) != Counter(LEVELS)
        for group in grouped.values()
    ):
        raise ValueError("Expected 400 questions with one row per intended level.")

    questions = sorted(grouped)
    random.Random(SEED).shuffle(questions)
    splits = {
        "train": sorted(questions[:200]),
        "dev": sorted(questions[200:280]),
        "test": sorted(questions[280:]),
    }
    train, dev = (
        [row for question in splits[name] for row in grouped[question]]
        for name in ("train", "dev")
    )
    return splits, train, dev


def evaluate(train, dev, field):
    train_counts = Counter(row[field] for row in train)
    dev_counts = Counter(row[field] for row in dev)
    if (train_counts.keys() | dev_counts.keys()) - set(LEVELS):
        raise ValueError(f"Unexpected label in {field}.")

    # Resolve ties in the fixed order Elementary, High School, Graduate.
    prediction = max(LEVELS, key=train_counts.__getitem__)
    correct = dev_counts[prediction]
    total = len(dev)
    # Only the predicted class can have nonzero F1 in a constant classifier.
    predicted_class_f1 = 2 * correct / (total + correct)
    ordinal_error = sum(
        abs(LEVELS.index(prediction) - index) * dev_counts[level]
        for index, level in enumerate(LEVELS)
    ) / total
    return {
        "prediction": prediction,
        "train_counts": {level: train_counts[level] for level in LEVELS},
        "dev_counts": {level: dev_counts[level] for level in LEVELS},
        "accuracy": correct / total,
        "macro_f1": predicted_class_f1 / len(LEVELS),
        "mean_absolute_ordinal_error": ordinal_error,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, help="Optional local copy of the source JSONL.")
    parser.add_argument("--output", type=Path, default=Path("m0_outputs"))
    args = parser.parse_args()
    if args.input:
        raw = args.input.read_bytes()
    else:
        with urlopen(SOURCE, timeout=60) as response:
            raw = response.read()
    rows = [json.loads(line) for line in raw.splitlines() if line.strip()]
    splits, train, dev = split_by_question(rows)
    metrics = {
        "source": SOURCE,
        "source_sha256": hashlib.sha256(raw).hexdigest(),
        "seed": SEED,
        "question_counts": {name: len(questions) for name, questions in splits.items()},
        "dev": {name: evaluate(train, dev, field) for name, field in LABEL_FIELDS.items()},
    }
    args.output.mkdir(parents=True, exist_ok=True)
    for name, data in (("question_splits", splits), ("dev_metrics", metrics)):
        (args.output / f"{name}.json").write_text(
            json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
