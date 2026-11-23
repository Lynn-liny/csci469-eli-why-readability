"""Check our M1 formula implementations against textstat 0.7.13.

Run: python validate_textstat.py
Uses 100 training explanations sampled with seed 469. textstat is used only
for this check, never for the scores we report. Differences are expected
because textstat counts syllables with a dictionary and splits sentences
differently; the check is that scores agree closely in rank (Spearman rho)
and that the mean absolute difference is small on the formula's scale.
"""

import json
import random
from statistics import mean

from textstat import textstat

from common import SEED, load_split, spearman
from m1_ari import automated_readability_index
from m1_dale_chall import dale_chall
from m1_flesch_kincaid import grade_level
from m1_flesch_reading_ease import reading_ease
from m1_smog_coleman_liau import coleman_liau, smog
from measures import _easy_words


def main():
    textstat.set_lang("en_US")
    _, train, _, _, digest = load_split()
    sample = [row["Explanation"] for row in random.Random(SEED).sample(train, 100)]
    easy_words = _easy_words()
    pairs = {
        "flesch_kincaid": (grade_level, textstat.flesch_kincaid_grade),
        "flesch_reading_ease": (reading_ease, textstat.flesch_reading_ease),
        "ari": (automated_readability_index, textstat.automated_readability_index),
        "dale_chall": (lambda t: dale_chall(t, easy_words), textstat.dale_chall_readability_score),
        "smog": (smog, textstat.smog_index),
        "coleman_liau": (coleman_liau, textstat.coleman_liau_index),
    }
    results = {"n": len(sample), "seed": SEED, "source_sha256": digest}
    for name, (ours, theirs) in pairs.items():
        a = [ours(text) for text in sample]
        b = [theirs(text) for text in sample]
        diffs = [x - y for x, y in zip(a, b)]
        results[name] = {
            "mean_ours": mean(a),
            "mean_textstat": mean(b),
            "mean_signed_difference": mean(diffs),
            "mean_absolute_difference": mean(map(abs, diffs)),
            "spearman_rho": spearman(a, b),
        }
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
