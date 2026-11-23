"""Shared data loading, splitting and evaluation for every measure.

New measures only need a function that maps a row to a number. Everything
else (download, question split, train-only cutoffs, dev metrics) lives here
so that all measures are scored the same way.
"""

import hashlib
import json
from pathlib import Path
from statistics import mean
from urllib.request import urlopen

from m0_majority import LABEL_FIELDS, LEVELS, SEED, SOURCE, split_by_question
from m1_flesch_reading_ease import evaluate as evaluate_cutoffs

CACHE = Path(__file__).resolve().parent / "data" / "perceived_background_match.jsonl"


def load_rows(path=None):
    """Return the annotated rows and the SHA-256 of the raw file.

    Downloads the pinned JSONL once and caches it under data/ (git-ignored).
    """
    path = Path(path) if path else CACHE
    if path.exists():
        raw = path.read_bytes()
    else:
        with urlopen(SOURCE, timeout=60) as response:
            raw = response.read()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
    rows = [json.loads(line) for line in raw.splitlines() if line.strip()]
    return rows, hashlib.sha256(raw).hexdigest()


def load_split(path=None):
    """Return (splits, train, dev, test) using the seed-469 question split."""
    rows, digest = load_rows(path)
    splits, train, dev = split_by_question(rows)
    test_questions = set(splits["test"])
    test = [row for row in rows if row["Question"] in test_questions]
    return splits, train, dev, test, digest


def row_id(row, split_of_question):
    """Stable id: split, question index within the sorted split, intended level."""
    split, index = split_of_question[row["Question"]]
    level = LEVELS.index(row[LABEL_FIELDS["intended"]])
    return f"{split}-{index:03d}-{level}"


def question_index(splits):
    return {
        question: (name, i)
        for name, questions in splits.items()
        for i, question in enumerate(questions)
    }


def ranks(values):
    """Average ranks (1-based), ties share the mean rank."""
    order = sorted(range(len(values)), key=values.__getitem__)
    result = [0.0] * len(values)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and values[order[j + 1]] == values[order[i]]:
            j += 1
        for k in range(i, j + 1):
            result[order[k]] = (i + j) / 2 + 1
        i = j + 1
    return result


def spearman(xs, ys):
    """Spearman rho with tie correction (Pearson correlation of average ranks)."""
    rx, ry = ranks(xs), ranks(ys)
    mx, my = mean(rx), mean(ry)
    cov = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    vx = sum((a - mx) ** 2 for a in rx)
    vy = sum((b - my) ** 2 for b in ry)
    return cov / (vx * vy) ** 0.5 if vx and vy else 0.0


def evaluate_measure(train, dev, measure, *, higher_means_easier=False):
    """Score one measure on dev for both label targets.

    Cutoffs are fit on train only (accuracy-maximizing, as in M0/M1).
    Spearman rho is reported in the "harder is larger" direction, so a
    positive value always means the measure agrees with the level order.
    """
    direction = -1 if higher_means_easier else 1
    dev_scores = [direction * measure(row) for row in dev]
    results = {}
    for name, field in LABEL_FIELDS.items():
        result = evaluate_cutoffs(
            train, dev, field, measure, higher_means_easier=higher_means_easier
        )
        result["spearman_rho"] = spearman(
            dev_scores, [LEVELS.index(row[field]) for row in dev]
        )
        results[name] = result
    return results


__all__ = [
    "LABEL_FIELDS", "LEVELS", "SEED", "SOURCE", "evaluate_measure", "load_rows",
    "load_split", "question_index", "row_id", "spearman",
]
