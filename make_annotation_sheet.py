"""Draw the 100-item self-annotation sample and write blind sheets.

Run: python make_annotation_sheet.py
Writes annotation/sheet_A.csv and annotation/sheet_B.csv (identical, no
labels, rows shuffled) and annotation/key.csv (labels; annotators must not
open it until they finish). Items come from train and dev only, 34/33/33 by
intended level, seed 469. Re-running reproduces the same sample.
"""

import csv
import random
from pathlib import Path

from common import LABEL_FIELDS, LEVELS, SEED, load_split, question_index, row_id

OUT = Path("annotation")
SIZES = {"Elementary": 34, "High School": 33, "Graduate": 33}


def main():
    splits, train, dev, _, _ = load_split()
    index = question_index(splits)
    rng = random.Random(SEED)
    pool = sorted(train + dev, key=lambda r: row_id(r, index))
    sample = []
    for level in LEVELS:
        candidates = [r for r in pool if r[LABEL_FIELDS["intended"]] == level]
        sample += rng.sample(candidates, SIZES[level])
    rng.shuffle(sample)
    OUT.mkdir(exist_ok=True)
    for name in ("A", "B"):
        with (OUT / f"sheet_{name}.csv").open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(["item", "question", "explanation", "level", "notes"])
            for i, row in enumerate(sample, start=1):
                writer.writerow([i, row["Question"], row["Explanation"], "", ""])
    with (OUT / "key.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["item", "id", "intended", "perceived"])
        for i, row in enumerate(sample, start=1):
            writer.writerow([i, row_id(row, index), row[LABEL_FIELDS["intended"]],
                             row[LABEL_FIELDS["perceived"]]])
    print(f"Wrote {len(sample)} items to {OUT}/")


if __name__ == "__main__":
    main()
