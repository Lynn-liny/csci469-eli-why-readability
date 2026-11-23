"""Weighted Cohen's kappa for the 100-item self-annotation.

Run after both annotators fill the "level" column of their sheet:
  python kappa.py annotation/sheet_A.csv annotation/sheet_B.csv
Reports linear and quadratic weighted kappa between the two annotators and
of each annotator against the released perceived labels and the intended
labels (from annotation/key.csv). Accepted level spellings: Elementary,
High School, Graduate (case-insensitive; E/H/G also work).
"""

import argparse
import csv
import json

from common import LEVELS

ALIASES = {"e": 0, "elementary": 0, "h": 1, "hs": 1, "high school": 1,
           "g": 2, "graduate": 2}


def read_levels(path, column):
    with open(path, newline="", encoding="utf-8") as handle:
        rows = {int(r["item"]): r[column].strip().lower() for r in csv.DictReader(handle)}
    missing = [item for item, value in rows.items() if value not in ALIASES]
    if missing:
        raise ValueError(f"{path}: missing or unknown level for items {missing[:10]}")
    return {item: ALIASES[value] for item, value in rows.items()}


def weighted_kappa(a, b, power):
    """Cohen's kappa with weights |i-j|**power / (k-1)**power (1 linear, 2 quadratic)."""
    k = len(LEVELS)
    n = len(a)
    observed = [[0] * k for _ in range(k)]
    for x, y in zip(a, b):
        observed[x][y] += 1
    rows = [sum(r) for r in observed]
    cols = [sum(observed[i][j] for i in range(k)) for j in range(k)]
    weight = lambda i, j: (abs(i - j) / (k - 1)) ** power
    disagreement = sum(weight(i, j) * observed[i][j] for i in range(k) for j in range(k)) / n
    expected = sum(weight(i, j) * rows[i] * cols[j] for i in range(k) for j in range(k)) / n ** 2
    return 1 - disagreement / expected if expected else 1.0


def compare(x, y):
    items = sorted(x.keys() & y.keys())
    a, b = [x[i] for i in items], [y[i] for i in items]
    return {
        "n": len(items),
        "exact_agreement": sum(p == q for p, q in zip(a, b)) / len(items),
        "kappa_linear": weighted_kappa(a, b, 1),
        "kappa_quadratic": weighted_kappa(a, b, 2),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("sheet_a")
    parser.add_argument("sheet_b")
    parser.add_argument("--key", default="annotation/key.csv")
    args = parser.parse_args()
    a = read_levels(args.sheet_a, "level")
    b = read_levels(args.sheet_b, "level")
    perceived = read_levels(args.key, "perceived")
    intended = read_levels(args.key, "intended")
    results = {
        "A_vs_B": compare(a, b),
        "A_vs_perceived": compare(a, perceived),
        "B_vs_perceived": compare(b, perceived),
        "A_vs_intended": compare(a, intended),
        "B_vs_intended": compare(b, intended),
    }
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
