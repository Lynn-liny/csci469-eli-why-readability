"""Dev-set error analysis: the 50 worst explanations per measure, pre-tagged.

Run: python error_analysis.py [--target perceived|intended] [--top 50]
Writes outputs/error_analysis_<target>.csv (one row per measure x example,
with an empty manual_category column for hand labelling) and
outputs/error_analysis_<target>.md (category counts per measure).

Ranking: largest ordinal gap between predicted and gold level first, then
distance of the score past the cutoff it crossed (the most confident
mistakes first). Dev only; test is never read.

Automatic tags are heuristics to speed up manual sorting into the proposal's
categories. Thresholds are medians (or the 75th percentile) on train:
  short_sent_technical  sentence length below median, rare-term density above
  long_sent_common      sentence length above median, rare-word share below
  list_formatting       bullets, numbered items, markdown headers or bold
  analogy               "imagine", "think of", "like a", "similar to", ...
  undefined_terms       undefined-term density at or above the 75th percentile
  other                 none of the above
"""

import argparse
import csv
import json
import re
from collections import Counter
from pathlib import Path
from statistics import median, quantiles

import measures
from common import LABEL_FIELDS, LEVELS, evaluate_measure, load_split, question_index, row_id
from m0_word_count import word_count
from m2_features import mean_sentence_length, rare_word_share

CATEGORIES = (
    "short_sent_technical", "long_sent_common", "list_formatting",
    "analogy", "undefined_terms", "other",
)
LIST = re.compile(r"(?m)^\s*(?:[-*•]|\d+[.)]|#+)\s|\*\*")
ANALOGY = re.compile(
    r"\b(?:imagine|think of|like an?|similar to|just like|as if|picture (?:a|an|this)|"
    r"compare[ds]? (?:it )?to|kind of like)\b",
    re.IGNORECASE,
)


def tagger(train, scores):
    text = lambda row: row["Explanation"]
    m3 = lambda row, n: scores[n](row)
    sent_median = median(mean_sentence_length(text(r)) for r in train)
    rare_word_median = median(rare_word_share(text(r)) for r in train)
    rare_term_median = median(m3(r, "rare_term_density") for r in train)
    undefined_q3 = quantiles([m3(r, "undefined_term_density") for r in train], n=4)[2]

    def tags(row):
        t = text(row)
        sentence = mean_sentence_length(t)
        found = []
        if sentence < sent_median and m3(row, "rare_term_density") > rare_term_median:
            found.append("short_sent_technical")
        if sentence > sent_median and rare_word_share(t) < rare_word_median:
            found.append("long_sent_common")
        if LIST.search(t):
            found.append("list_formatting")
        if ANALOGY.search(t):
            found.append("analogy")
        if m3(row, "undefined_term_density") >= undefined_q3:
            found.append("undefined_terms")
        return found or ["other"]

    return tags


def worst(dev, field, fn, easier, result, top):
    direction = -1 if easier else 1
    low, high = (direction * t for t in result["thresholds_in_raw_score_order_elementary_then_graduate"])
    rows = []
    for row in dev:
        score = direction * fn(row)
        predicted = int(score > low) + int(score > high)
        gold = LEVELS.index(row[field])
        if predicted == gold:
            continue
        # How far past the boundary between gold and predicted the score went.
        boundary = low if min(predicted, gold) == 0 else high
        rows.append((abs(predicted - gold), abs(score - boundary), row, predicted, fn(row)))
    rows.sort(key=lambda item: (-item[0], -item[1]))
    return rows[:top]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", choices=LABEL_FIELDS, default="perceived")
    parser.add_argument("--top", type=int, default=50)
    parser.add_argument("--output", type=Path, default=Path("outputs"))
    args = parser.parse_args()
    field = LABEL_FIELDS[args.target]

    splits, train, dev, test, _ = load_split()
    registry = measures.build(train, dev + test)
    index = question_index(splits)
    tags = tagger(train, {name: fn for name, (_, fn, _) in registry.items()})

    args.output.mkdir(parents=True, exist_ok=True)
    counts, directions = {}, {}
    csv_path = args.output / f"error_analysis_{args.target}.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow([
            "measure", "rank", "id", "gold", "predicted", "gap", "score", "word_count",
            "intended", "perceived", "auto_tags", "manual_category", "question", "explanation",
        ])
        for name, (_, fn, easier) in registry.items():
            result = evaluate_measure(train, dev, fn, higher_means_easier=easier)[args.target]
            selected = worst(dev, field, fn, easier, result, args.top)
            counts[name] = Counter()
            directions[name] = Counter()
            for rank, (gap, _, row, predicted, score) in enumerate(selected, start=1):
                found = tags(row)
                counts[name].update(found)
                gold = LEVELS.index(row[field])
                directions[name]["too_hard" if predicted > gold else "too_easy"] += 1
                writer.writerow([
                    name, rank, row_id(row, index), row[field], LEVELS[predicted], gap,
                    f"{score:.4f}", word_count(row), row[LABEL_FIELDS["intended"]],
                    row[LABEL_FIELDS["perceived"]], ";".join(found), "",
                    row["Question"], row["Explanation"],
                ])

    lines = [
        f"# Error analysis on dev ({args.target} level, generated by error_analysis.py)",
        "",
        f"Top {args.top} errors per measure. A text can carry several tags, so rows can "
        "sum past the total. too_easy means the measure predicted a lower level than the gold label.",
        "",
        "| Measure | Version | too_easy | too_hard | " + " | ".join(CATEGORIES) + " |",
        "| --- | --- | ---: | ---: | " + " | ".join("---:" for _ in CATEGORIES) + " |",
    ]
    for name, (version, _, _) in registry.items():
        lines.append(
            f"| {name} | {version} | {directions[name]['too_easy']} | {directions[name]['too_hard']} | "
            + " | ".join(str(counts[name][c]) for c in CATEGORIES) + " |"
        )
    (args.output / f"error_analysis_{args.target}.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )
    print("\n".join(lines))
    print(json.dumps({"csv": str(csv_path)}))


if __name__ == "__main__":
    main()
