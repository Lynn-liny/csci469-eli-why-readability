"""Within-question ordering and bootstrap confidence intervals on dev.

Run: python secondary_analysis.py [--resamples 1000]
Writes outputs/secondary_dev.json and outputs/secondary_dev.md.

1. Within-question ordering. Every question has one explanation per intended
   level, so a measure that detects audience-conditioned differences should
   score them Elementary < High School < Graduate. We report pairwise ordering
   accuracy for adjacent pairs (E-H, H-G) and the distant pair (E-G), ties
   counted as half, plus the share of questions with all three in the right
   order (chance 1/6). The same pairwise check is done for pairs whose human-
   perceived labels differ, split into adjacent and distant perceived levels.
   This needs no cutoffs at all.

2. Bootstrap over questions. Dev questions are resampled with replacement
   (all three explanations of a question move together). Cutoffs stay fixed
   from train. We report 95% percentile intervals for perceived-level
   accuracy and Spearman rho, and paired intervals for each measure minus
   word count, which show whether a difference from the baseline is
   distinguishable from noise on 80 dev questions.
"""

import argparse
import json
import random
from collections import defaultdict
from pathlib import Path
from statistics import mean

import measures
from common import LABEL_FIELDS, LEVELS, SEED, evaluate_measure, load_split, spearman

INTENDED = LABEL_FIELDS["intended"]
PERCEIVED = LABEL_FIELDS["perceived"]


def concordance(a, b):
    """1 if a < b, 0.5 on a tie, 0 otherwise (scores in harder-is-larger order)."""
    return 1.0 if a < b else 0.5 if a == b else 0.0


def ordering(by_question, score):
    adjacent, distant, full = [], [], []
    p_adjacent, p_distant = [], []
    for rows in by_question.values():
        s = {LEVELS.index(r[INTENDED]): score(r) for r in rows}
        adjacent += [concordance(s[0], s[1]), concordance(s[1], s[2])]
        distant.append(concordance(s[0], s[2]))
        full.append(float(s[0] < s[1] < s[2]))
        for i, x in enumerate(rows):
            for y in rows[i + 1:]:
                lx, ly = LEVELS.index(x[PERCEIVED]), LEVELS.index(y[PERCEIVED])
                if lx == ly:
                    continue
                lo, hi = (x, y) if lx < ly else (y, x)
                value = concordance(score(lo), score(hi))
                (p_adjacent if abs(lx - ly) == 1 else p_distant).append(value)
    return {
        "intended_adjacent_pairs": mean(adjacent),
        "intended_distant_pairs": mean(distant),
        "intended_fully_ordered_questions": mean(full),
        "perceived_adjacent_pairs": mean(p_adjacent),
        "perceived_distant_pairs": mean(p_distant),
        "n_perceived_adjacent_pairs": len(p_adjacent),
        "n_perceived_distant_pairs": len(p_distant),
    }


def percentile(values, q):
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, round(q * (len(ordered) - 1))))
    return ordered[index]


def interval(values):
    return [percentile(values, 0.025), percentile(values, 0.975)]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--resamples", type=int, default=1000)
    parser.add_argument("--output", type=Path, default=Path("outputs"))
    args = parser.parse_args()

    _, train, dev, test, digest = load_split()
    registry = measures.build(train, dev + test)
    by_question = defaultdict(list)
    for row in dev:
        by_question[row["Question"]].append(row)
    questions = sorted(by_question)

    # Per-measure dev scores (harder = larger) and fixed-cutoff predictions.
    table = {}
    for name, (_, fn, easier) in registry.items():
        direction = -1 if easier else 1
        result = evaluate_measure(train, dev, fn, higher_means_easier=easier)["perceived"]
        low, high = (direction * t for t in
                     result["thresholds_in_raw_score_order_elementary_then_graduate"])
        per_question = {}
        for q in questions:
            items = []
            for r in by_question[q]:
                s = direction * fn(r)
                items.append((s, int(s > low) + int(s > high), LEVELS.index(r[PERCEIVED])))
            per_question[q] = items
        table[name] = {
            "ordering": ordering(by_question, lambda r, f=fn, d=direction: d * f(r)),
            "per_question": per_question,
            "accuracy": result["accuracy"],
            "spearman_rho": result["spearman_rho"],
        }

    rng = random.Random(SEED)
    draws = [[rng.choice(questions) for _ in questions] for _ in range(args.resamples)]

    def stats(name, sample):
        items = [item for q in sample for item in table[name]["per_question"][q]]
        accuracy = mean(float(p == g) for _, p, g in items)
        rho = spearman([s for s, _, _ in items], [g for _, _, g in items])
        return accuracy, rho

    boot = {name: [stats(name, sample) for sample in draws] for name in registry}
    results = {"source_sha256": digest, "seed": SEED, "resamples": args.resamples,
               "dev_questions": len(questions), "measures": {}}
    for name, (version, _, _) in registry.items():
        acc = [a for a, _ in boot[name]]
        rho = [r for _, r in boot[name]]
        diff_acc = [a - b for (a, _), (b, _) in zip(boot[name], boot["word_count"])]
        diff_rho = [a - b for (_, a), (_, b) in zip(boot[name], boot["word_count"])]
        results["measures"][name] = {
            "version": version,
            **table[name]["ordering"],
            "perceived_accuracy": table[name]["accuracy"],
            "perceived_accuracy_ci95": interval(acc),
            "perceived_spearman_rho": table[name]["spearman_rho"],
            "perceived_spearman_rho_ci95": interval(rho),
            "accuracy_minus_word_count_ci95": interval(diff_acc),
            "rho_minus_word_count_ci95": interval(diff_rho),
        }

    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "secondary_dev.json").write_text(json.dumps(results, indent=2) + "\n",
                                                   encoding="utf-8")
    m = results["measures"]
    lines = [
        "# Secondary dev analysis (generated by secondary_analysis.py)",
        "",
        f"{len(questions)} dev questions, {args.resamples} bootstrap resamples over questions, seed {SEED}.",
        "",
        "## Within-question ordering",
        "",
        "Share of pairs a measure orders correctly (ties count half, chance 0.5). "
        "Fully ordered: all three intended versions in the right order (chance 0.167).",
        "",
        "| Measure | Version | Intended adjacent | Intended distant | Fully ordered "
        "| Perceived adjacent | Perceived distant |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for name in sorted(m, key=lambda n: -m[n]["intended_distant_pairs"]):
        r = m[name]
        lines.append(
            f"| {name} | {r['version']} | {r['intended_adjacent_pairs']:.3f} "
            f"| {r['intended_distant_pairs']:.3f} | {r['intended_fully_ordered_questions']:.3f} "
            f"| {r['perceived_adjacent_pairs']:.3f} | {r['perceived_distant_pairs']:.3f} |"
        )
    any_row = next(iter(m.values()))
    lines += [
        "",
        f"Perceived pairs: {any_row['n_perceived_adjacent_pairs']} adjacent, "
        f"{any_row['n_perceived_distant_pairs']} distant.",
        "",
        "## Bootstrap 95% intervals, human-perceived level",
        "",
        "The difference columns are paired (same resample) against word count. "
        "An interval that contains 0 means the difference is not distinguishable on dev.",
        "",
        "| Measure | Version | Accuracy | 95% CI | − word count | Spearman ρ | 95% CI | − word count |",
        "| --- | --- | ---: | --- | --- | ---: | --- | --- |",
    ]
    fmt = lambda pair, p="": f"[{pair[0]:{p}}, {pair[1]:{p}}]"
    for name in sorted(m, key=lambda n: -m[n]["perceived_spearman_rho"]):
        r = m[name]
        lines.append(
            f"| {name} | {r['version']} | {r['perceived_accuracy']:.1%} "
            f"| {fmt(r['perceived_accuracy_ci95'], '.1%')} "
            f"| {fmt(r['accuracy_minus_word_count_ci95'], '+.1%')} "
            f"| {r['perceived_spearman_rho']:.3f} | {fmt(r['perceived_spearman_rho_ci95'], '.3f')} "
            f"| {fmt(r['rho_minus_word_count_ci95'], '+.3f')} |"
        )
    (args.output / "secondary_dev.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
