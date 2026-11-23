"""Evaluate New Dale–Chall and compare its Graduate predictions with M0.

Install textstat==0.7.13 for its English word list, then run this script.
Cutoffs are fit only on train. Matrix axes follow the printed level order.
"""

import json
from importlib.metadata import distribution
from urllib.request import urlopen

from m0_majority import LABEL_FIELDS, LEVELS, SOURCE, split_by_question
from m0_word_count import word_count
from m1_flesch_kincaid import SENTENCE_END, WORDS
from m1_flesch_reading_ease import evaluate


def dale_chall(text, easy_words):
    words = [word.lower().replace("’", "'") for word in WORDS.findall(text)]
    if not words:
        raise ValueError("Cannot score an explanation with no words.")
    sentences = sum(bool(WORDS.search(chunk)) for chunk in SENTENCE_END.split(text))
    difficult_percent = 100 * sum(word not in easy_words for word in words) / len(words)
    score = 0.1579 * difficult_percent + 0.0496 * len(words) / sentences
    return score + 3.6365 if difficult_percent > 5 else score


def graduate_comparison(dev, field, baseline, dale, measure):
    transitions = [[0] * len(LEVELS) for _ in LEVELS]
    baseline_low, baseline_high = baseline["thresholds_in_raw_score_order_elementary_then_graduate"]
    dale_low, dale_high = dale["thresholds_in_raw_score_order_elementary_then_graduate"]
    for row in dev:
        if row[field] != "Graduate":
            continue
        length = word_count(row)
        difficulty = measure(row)
        old = int(length > baseline_low) + int(length > baseline_high)
        new = int(difficulty > dale_low) + int(difficulty > dale_high)
        transitions[old][new] += 1
    return transitions


def main():
    # Use the published list only. Score with our own tokenizer and formula.
    package = distribution("textstat")
    if package.version != "0.7.13":
        raise ValueError("Install textstat==0.7.13 for the pinned English word list.")
    path = package.locate_file("textstat/resources/en/easy_words.txt")
    easy_words = frozenset(path.read_text(encoding="utf-8").lower().splitlines())

    def measure(row):
        return dale_chall(row["Explanation"], easy_words)

    with urlopen(SOURCE, timeout=60) as response:
        rows = [json.loads(line) for line in response if line.strip()]
    _, train, dev = split_by_question(rows)
    results = {"level_order": LEVELS}
    for name, field in LABEL_FIELDS.items():
        baseline = evaluate(train, dev, field, word_count)
        dale = evaluate(train, dev, field, measure)
        results[name] = {
            "word_count": baseline,
            "dale_chall": dale,
            "true_graduate_transitions_word_count_rows_dale_chall_columns": (
                graduate_comparison(dev, field, baseline, dale, measure)
            ),
        }
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
