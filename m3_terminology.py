"""M3 terminology measure: term density and defined-term ratio.

Run: python m3_terminology.py   (needs the M2 requirements)

Term inventory. Candidates are noun and adjective unigrams plus noun-chunk
n-grams (2-3 words, determiners removed) from the M2 chunker. Termhood is a
log-likelihood ratio (Dunning's G2) on document frequency, contrasting the
explanations written for Graduate readers (foreground) with those written for
Elementary readers (background). Because every question has one explanation
per intended level, topic words appear on both sides and cancel; what remains
is vocabulary that the generators reserve for expert readers. A candidate is
a term when G2 >= 10.83 (p < 0.001), it is more frequent in the foreground,
and it occurs in at least MIN_DOCS foreground texts.

Leakage control. The inventory is built from train only. Train scores, which
are used to fit cutoffs, are cross-fitted: each train explanation is scored
with an inventory built from the other folds of train questions, so a text
never helps choose its own terms. Dev and test use the full-train inventory.

Scores per explanation:
  term_density             share of tokens inside an inventory term
  rare_term_density        inventory terms plus any noun or adjective rarer
                           than Zipf 3.0, so domain words unseen in train
                           (e.g. a dev-only topic) still count
  defined_term_ratio       share of distinct terms that the text defines at
                           least once, via patterns such as "X is a ...",
                           "X, which means ...", "X (...)", "called X"
                           (higher = easier; 1.0 when the text has no terms)
  undefined_term_density   rare_term_density counting only undefined terms
"""

import json
import math
import random
import re
from collections import Counter
from functools import lru_cache

from common import LABEL_FIELDS, LEVELS, SEED, evaluate_measure, load_split
from m2_features import _zipf, noun_chunks, tagged

G2_CUTOFF = 10.83
MIN_DOCS = 3
RARE_TERM_ZIPF = 3.0
FOLDS = 5
INTENDED = LABEL_FIELDS["intended"]

AFTER_TERM = re.compile(
    r"^(?:"
    r"\s+(?:is|are|was|were)\s+(?:a|an|the|when|how|what|basically|just|like|called|kind|type|where)\b"
    r"|\s+(?:refers?\s+to|means?|describes?|stands\s+for)\b"
    r"|\s*,?\s+(?:which|that|who)\s+(?:is|are|means?|refers?)\b"
    r"|\s*\("
    r"|\s*,\s+(?:or|also\s+called|also\s+known\s+as|meaning|i\.e\.|a|an|the)\b"
    r"|\s*[:—–]|\s+-\s"
    r")",
    re.IGNORECASE,
)
BEFORE_TERM = re.compile(
    r"\b(?:called|known\s+as|termed|named|term|word|concept\s+of)\s+(?:an?\s+|the\s+)?[\"'“‘]?$",
    re.IGNORECASE,
)


def _norm(word):
    return word.lower().replace("’", "'")


@lru_cache(maxsize=4096)
def candidates(text):
    """Distinct candidate terms (tuples of lowercased words) in one text."""
    found = set()
    for sent in tagged(text):
        for word, tag in sent:
            if tag.startswith(("NN", "JJ")) and word.isalpha():
                found.add((_norm(word),))
    for chunk in noun_chunks(text):
        words = tuple(_norm(w) for w, t in chunk if t != "DT")
        for n in (2, 3):
            for i in range(len(words) - n + 1):
                found.add(words[i:i + n])
    return frozenset(found)


def g2(a, b, n_fg, n_bg):
    """Dunning log-likelihood for a term in a of n_fg and b of n_bg documents."""
    cells = ((a, n_fg - a), (b, n_bg - b))
    total = n_fg + n_bg
    present = a + b
    score = 0.0
    for (k_in, k_out), n in zip(cells, (n_fg, n_bg)):
        for observed, column in ((k_in, present), (k_out, total - present)):
            expected = n * column / total
            if observed:
                score += observed * math.log(observed / expected)
    return 2 * score


def build_inventory(rows):
    fg = [r for r in rows if r[INTENDED] == "Graduate"]
    bg = [r for r in rows if r[INTENDED] == "Elementary"]
    df_fg = Counter(t for r in fg for t in candidates(r["Explanation"]))
    df_bg = Counter(t for r in bg for t in candidates(r["Explanation"]))
    inventory = {}
    for term, a in df_fg.items():
        b = df_bg[term]
        if a < MIN_DOCS or a / len(fg) <= b / len(bg):
            continue
        score = g2(a, b, len(fg), len(bg))
        if score >= G2_CUTOFF:
            inventory[term] = score
    return inventory


def _term_spans(words, tags, inventory, include_rare):
    """Greedy longest-match spans (start, end) of terms in a token list."""
    spans, i = [], 0
    while i < len(words):
        for n in (3, 2, 1):
            gram = tuple(words[i:i + n])
            if len(gram) == n and gram in inventory:
                spans.append((i, i + n))
                i += n
                break
        else:
            if (include_rare and tags[i].startswith(("NN", "JJ")) and words[i].isalpha()
                    and _zipf(words[i]) < RARE_TERM_ZIPF):
                spans.append((i, i + 1))
            i += 1
    return spans


def _is_defined(sentence_text, term):
    """True if this sentence defines the term with one of the patterns."""
    pattern = r"\b" + r"[\s-]+".join(map(re.escape, term)) + r"\b"
    for match in re.finditer(pattern, sentence_text, re.IGNORECASE):
        if AFTER_TERM.match(sentence_text[match.end():]) or BEFORE_TERM.search(
            sentence_text[:match.start()]
        ):
            return True
    return False


def score_text(text, inventory):
    from m1_flesch_kincaid import SENTENCE_END

    raw_sentences = [s for s in SENTENCE_END.split(text) if s.strip()]
    sentences = tagged(text)
    total = sum(len(s) for s in sentences)
    inv_tokens = rare_tokens = 0
    terms = {}
    for sent in sentences:
        words = [_norm(w) for w, _ in sent]
        tags = [t for _, t in sent]
        for start, end in _term_spans(words, tags, inventory, include_rare=False):
            inv_tokens += end - start
        for start, end in _term_spans(words, tags, inventory, include_rare=True):
            rare_tokens += end - start
            term = tuple(words[start:end])
            terms[term] = terms.get(term, 0) + end - start
    defined = {t for t in terms if any(_is_defined(s, t) for s in raw_sentences)}
    undefined_tokens = sum(n for t, n in terms.items() if t not in defined)
    return {
        "term_density": inv_tokens / total,
        "rare_term_density": rare_tokens / total,
        "defined_term_ratio": len(defined) / len(terms) if terms else 1.0,
        "undefined_term_density": undefined_tokens / total,
    }


# name -> higher_means_easier
SCORES = {
    "term_density": False,
    "rare_term_density": False,
    "defined_term_ratio": True,
    "undefined_term_density": False,
}


def key(row):
    return row["Question"], row[INTENDED]


def score_splits(train, others):
    """Cross-fitted train scores and full-inventory scores for other rows.

    Returns {(question, intended level): score dict} and the full-train inventory.
    """
    questions = sorted({r["Question"] for r in train})
    random.Random(SEED).shuffle(questions)
    fold_of = {q: i % FOLDS for i, q in enumerate(questions)}
    scores = {}
    for fold in range(FOLDS):
        inventory = build_inventory([r for r in train if fold_of[r["Question"]] != fold])
        for r in train:
            if fold_of[r["Question"]] == fold:
                scores[key(r)] = score_text(r["Explanation"], inventory)
    full = build_inventory(train)
    for r in others:
        scores[key(r)] = score_text(r["Explanation"], full)
    return scores, full


def main():
    _, train, dev, test, digest = load_split()
    scores, inventory = score_splits(train, dev + test)
    top = sorted(inventory.items(), key=lambda kv: -kv[1])[:40]
    results = {
        "level_order": LEVELS,
        "source_sha256": digest,
        "inventory_size": len(inventory),
        "top_terms_by_g2": [[" ".join(t), round(s, 1)] for t, s in top],
    }
    for name, easier in SCORES.items():
        results[name] = evaluate_measure(
            train, dev, lambda row, n=name: scores[key(row)][n], higher_means_easier=easier
        )
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
