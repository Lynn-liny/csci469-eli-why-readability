"""M2 lexical and syntactic features, each scored alone as a measure.

Run: python m2_features.py
Needs wordfreq==3.1.1 (frequency list) and nltk with the
averaged_perceptron_tagger_eng model (POS tags). Tokens and sentences reuse
the M1 boundaries so features differ only in what they count.

Features (higher = harder unless noted):
  mean_word_length        letters per word
  mean_sentence_length    words per sentence
  mattr                   moving-average type-token ratio, window 50
                          (plain TTR falls with length, so it would mostly
                          re-measure word count)
  mean_zipf               mean wordfreq Zipf frequency (higher = easier)
  oov_5000                share of words outside the 5,000 most frequent
  rare_word_share         share of words with Zipf < 3.5 (rarer than about
                          3 per million words)
  noun_share, adj_share, verb_share   share of tokens with that POS
  mean_np_length          mean length of noun chunks found by a regular-
                          expression chunker over POS tags
"""

import json
import re
from functools import lru_cache
from statistics import mean

from common import LEVELS, evaluate_measure, load_split
from m1_flesch_kincaid import SENTENCE_END, WORDS

MATTR_WINDOW = 50
RARE_ZIPF = 3.5
# (determiner)? (adjectives or nouns)* noun: a minimal base-NP chunker.
NP = re.compile(r"(?<!\S)(?:DT )?(?:(?:JJ[RS]?|NNP?S?|VBN|VBG) )*NNP?S? ")


@lru_cache(maxsize=1)
def _top_5000():
    from wordfreq import top_n_list

    return frozenset(top_n_list("en", 5000))


@lru_cache(maxsize=None)
def _zipf(word):
    from wordfreq import zipf_frequency

    return zipf_frequency(word, "en")


def sentences(text):
    """Word-token lists per sentence, using the M1 sentence boundaries."""
    result = [WORDS.findall(chunk) for chunk in SENTENCE_END.split(text)]
    return [words for words in result if words]


@lru_cache(maxsize=4096)
def tagged(text):
    """POS tags per sentence (Penn tags), cached because several features use them."""
    from nltk import pos_tag

    return tuple(tuple(pos_tag(words)) for words in sentences(text))


def _normalize(word):
    return word.lower().replace("’", "'")


def mean_word_length(text):
    words = WORDS.findall(text)
    return mean(sum(c.isalpha() for c in w) for w in words)


def mean_sentence_length(text):
    return mean(len(s) for s in sentences(text))


def mattr(text, window=MATTR_WINDOW):
    words = [_normalize(w) for w in WORDS.findall(text)]
    if len(words) <= window:
        return len(set(words)) / len(words)
    counts = {}
    for w in words[:window]:
        counts[w] = counts.get(w, 0) + 1
    total = len(counts)
    for i in range(window, len(words)):
        out, new = words[i - window], words[i]
        counts[out] -= 1
        if not counts[out]:
            del counts[out]
        counts[new] = counts.get(new, 0) + 1
        total += len(counts)
    return total / (len(words) - window + 1)


def mean_zipf(text):
    return mean(_zipf(_normalize(w)) for w in WORDS.findall(text))


def oov_5000(text):
    top = _top_5000()
    words = [_normalize(w) for w in WORDS.findall(text)]
    return sum(w not in top for w in words) / len(words)


def rare_word_share(text):
    words = [_normalize(w) for w in WORDS.findall(text)]
    return sum(_zipf(w) < RARE_ZIPF for w in words) / len(words)


def _pos_share(prefixes):
    def share(text):
        tags = [tag for sent in tagged(text) for _, tag in sent]
        return sum(tag.startswith(prefixes) for tag in tags) / len(tags)
    return share


noun_share = _pos_share(("NN",))
adj_share = _pos_share(("JJ",))
verb_share = _pos_share(("VB",))


def noun_chunks(text):
    """Base noun chunks as lists of (word, tag), from the POS-tag chunker."""
    chunks = []
    for sent in tagged(text):
        tags = "".join(f"{tag} " for _, tag in sent)
        # Map character offsets in the tag string back to token positions.
        starts = [0]
        for _, tag in sent:
            starts.append(starts[-1] + len(tag) + 1)
        position = {offset: i for i, offset in enumerate(starts)}
        for match in NP.finditer(tags):
            i, j = position[match.start()], position[match.end()]
            chunks.append(list(sent[i:j]))
    return chunks


def mean_np_length(text):
    chunks = [[w for w, t in c if t != "DT"] for c in noun_chunks(text)]
    return mean(len(c) for c in chunks) if chunks else 0.0


# name -> (function of text, higher_means_easier)
FEATURES = {
    "mean_word_length": (mean_word_length, False),
    "mean_sentence_length": (mean_sentence_length, False),
    "mattr": (mattr, False),
    "mean_zipf": (mean_zipf, True),
    "oov_5000": (oov_5000, False),
    "rare_word_share": (rare_word_share, False),
    "noun_share": (noun_share, False),
    "adj_share": (adj_share, False),
    "verb_share": (verb_share, True),
    "mean_np_length": (mean_np_length, False),
}


def main():
    _, train, dev, _, digest = load_split()
    results = {"level_order": LEVELS, "source_sha256": digest}
    for name, (feature, easier) in FEATURES.items():
        results[name] = evaluate_measure(
            train, dev, lambda row, f=feature: f(row["Explanation"]),
            higher_means_easier=easier,
        )
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
