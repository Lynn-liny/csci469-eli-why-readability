"""Registry of every measure: name -> (row -> score, higher_means_easier).

Add a new measure here and run_all.py picks it up. Each function takes a
row from the ELI-Why JSONL and returns one number.
"""

from importlib.metadata import distribution

from m0_word_count import word_count
from m1_ari import automated_readability_index
from m1_dale_chall import dale_chall
from m1_flesch_kincaid import grade_level
from m1_flesch_reading_ease import reading_ease
from m1_smog_coleman_liau import coleman_liau, smog


def _easy_words():
    package = distribution("textstat")
    if package.version != "0.7.13":
        raise ValueError("Install textstat==0.7.13 for the pinned English word list.")
    path = package.locate_file("textstat/resources/en/easy_words.txt")
    return frozenset(path.read_text(encoding="utf-8").lower().splitlines())


def build():
    easy_words = _easy_words()

    def text(formula):
        return lambda row: formula(row["Explanation"])

    # (version, function, higher_means_easier)
    return {
        "word_count": ("M0", word_count, False),
        "flesch_kincaid": ("M1", text(grade_level), False),
        "flesch_reading_ease": ("M1", text(reading_ease), True),
        "ari": ("M1", text(automated_readability_index), False),
        "dale_chall": ("M1", lambda row: dale_chall(row["Explanation"], easy_words), False),
        "smog": ("M1", text(smog), False),
        "coleman_liau": ("M1", text(coleman_liau), False),
    }
