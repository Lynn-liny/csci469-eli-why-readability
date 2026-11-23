# csci469-eli-why-readability
CSCI 469 Group 16 project evaluating readability measures on ELI-Why explanations.

## Quick start

```sh
python -m pip install -r requirements.txt
python -m nltk.downloader averaged_perceptron_tagger_eng cmudict
python run_all.py                   # scores every measure, writes outputs/
python error_analysis.py            # 50 worst dev errors per measure, pre-tagged
python secondary_analysis.py        # within-question ordering, bootstrap CIs
python validate_textstat.py         # checks our M1 formulas against textstat
```

The data is the pinned ELI-Why perceived-background-match JSONL (1,200
explanations, 400 questions). It is downloaded once and cached in `data/`
(git-ignored). Questions are split 200/80/120 into train/dev/test with seed
469; `outputs/question_splits.json` records the split.

## Layout

| File | Purpose |
| --- | --- |
| `common.py` | Data loading and cache, question split, shared evaluation (train-only cutoffs, accuracy, macro-F1, ordinal error, Spearman ρ) |
| `measures.py` | Registry of all measures. Add a new measure here and `run_all.py` includes it |
| `run_all.py` | Writes `outputs/scores.jsonl` (every score for every explanation), `outputs/dev_metrics.json` and `outputs/dev_summary.md` |
| `validate_textstat.py` | Compares each M1 formula with textstat 0.7.13 on 100 train texts |
| `m0_*.py` | M0 baselines: majority class, word count |
| `m1_*.py` | M1 classic formulas: Flesch–Kincaid, Flesch Reading Ease, ARI, New Dale–Chall, SMOG, Coleman–Liau |
| `m2_features.py` | M2 single lexical and syntactic features (word length, MATTR, word frequency, POS shares, noun-chunk length) |
| `m3_terminology.py` | M3 terminology measure: G² term inventory from train (cross-fitted), term density, defined-term ratio |
| `error_analysis.py` | Writes `outputs/error_analysis_<target>.csv` (worst 50 dev errors per measure, with heuristic tags and an empty `manual_category` column) and a summary table |
| `secondary_analysis.py` | Within-question ordering of the three intended versions, perceived-level pairs, bootstrap CIs over questions with paired differences vs word count |
| `make_annotation_sheet.py`, `kappa.py`, `annotation/` | 100-item blind self-annotation sheets, guideline, weighted Cohen's κ |
| `final_test.py` | One-time test-split evaluation (refuses a second run). Not run yet |
| `M1_REPRODUCTION.md` | Per-formula notes and expected dev numbers |
| `M2_M3_RESULTS.md` | M2/M3 method notes, dev results and first error-analysis findings |
| `SECONDARY_RESULTS.md` | Ordering, bootstrap and annotation notes |

The individual `m0_*.py` and `m1_*.py` scripts still run on their own and
print the same numbers as before.

## Current dev results

See `outputs/dev_summary.md`. Test-split rows are scored in
`outputs/scores.jsonl` for later use but are not evaluated.
