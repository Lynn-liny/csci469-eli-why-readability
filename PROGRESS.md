# Progress summary (as of Nov 23, 2026)

Project: which readability measures recover the audience level of LLM-generated ELI-Why explanations. The primary evaluation uses the human-perceived level, and the intended level is a secondary analysis. The data is the 1,200 annotated explanations (400 questions × 3 intended levels), split by question into 200/80/120 train/dev/test with seed 469. All numbers below are on **dev**. Test has not been touched.

## Done

| Step | What | Where |
| --- | --- | --- |
| M0 | Majority class and word-count baselines | `m0_*.py` |
| M1 | Six classic formulas (Flesch–Kincaid, Reading Ease, ARI, Dale–Chall, SMOG, Coleman–Liau), our own implementations, checked against textstat (rank agreement ≥ 0.90 for all) | `m1_*.py`, `validate_textstat.py`, `M1_REPRODUCTION.md` |
| Infra | Shared loading, split and evaluation; one command that scores every measure and writes the summary tables | `common.py`, `measures.py`, `run_all.py`, `outputs/` |
| Metrics | Accuracy, macro-F1, ordinal error, Spearman ρ, ρ with word count partialled out | `outputs/dev_summary.md` |
| M2 | Ten single lexical and syntactic features (word length, sentence length, MATTR, word frequency, words outside the top 5,000, POS shares, noun-chunk length) | `m2_features.py` |
| M3 | Terminology measure: G² term inventory (Graduate vs Elementary train texts, cross-fitted to avoid leakage), term density, rare-term density, defined-term ratio, undefined-term density | `m3_terminology.py`, `M2_M3_RESULTS.md` |
| Error analysis | The 50 worst dev errors per measure, with heuristic category tags and an empty column for manual labels | `error_analysis.py`, `outputs/error_analysis_*.csv` |
| Secondary | Within-question ordering of the three intended versions; bootstrap CIs over questions with paired differences vs word count | `secondary_analysis.py`, `SECONDARY_RESULTS.md` |
| Annotation kit | Blind 100-item sheets, a draft guideline and a weighted-κ script | `annotation/`, `make_annotation_sheet.py`, `kappa.py` |
| Test script | One-time test evaluation that refuses a second run. **Not run yet** | `final_test.py` |

## Key findings so far

1. **Length dominates the perceived labels.** Word count is the best single predictor (accuracy 57.9%, ρ 0.52). No formula, feature or terminology measure beats it, and almost none of them recognize Graduate texts (Graduate F1 ≤ 0.15).
2. **Terminology adds the most beyond length.** With word count controlled for, the M3 rare-term density has the highest partial ρ (0.33). The best classic formula, Dale–Chall, reaches 0.22.
3. **Generators change audience through length and vocabulary, not sentence length.** In all 80 dev questions, the Graduate version is longer than the Elementary one. Mean sentence length orders the three versions at chance, so sentence-length-heavy formulas (Flesch–Kincaid, SMOG, ARI) do poorly. This contradicts part of our original hypothesis and should be stated in the paper.
4. **Lower-level explanations keep technical vocabulary.** In the worst intended-level errors of M3, 48–49 of 50 rate the text harder than its intended level.
5. **Dev is small.** Accuracy CIs are about ±6 points, so most accuracy differences from word count are not significant. For ρ, only the M3 measures and Dale–Chall are statistically tied with word count. All others are significantly lower.
6. **Some perceived labels look noisy** (for example, short plain texts labelled Graduate), which is why the self-annotation check matters.

## Open decisions for the team

1. **100-item self-annotation and κ.** Two people each fill one sheet (`annotation/sheet_A.csv`, `annotation/sheet_B.csv`) independently, following `annotation/GUIDELINE.md`. Check the level definitions against the ELI-Why paper's annotation instructions before starting. Then run `python kappa.py annotation/sheet_A.csv annotation/sheet_B.csv`. Do not open `annotation/key.csv` before both sheets are finished.
2. **Defined-term ratio: revise or drop, then run test once.** The ratio currently performs at chance level. After deciding, all measures are frozen, and someone runs `python final_test.py --confirm-final` exactly once.
3. **Generator ranking and STEM breakdown: join the full ELI-Why data or drop.** The annotated subset has no generator or domain field. Either join with the full ELI-Why release (which also allows Kendall τ between generator rankings) or remove these analyses from the paper.

Also: the **LLM upper bound** (one frozen prompt, open-weight model) needs someone with NYU HPC access to run it. The prompt and script can be prepared in advance.

## Remaining plan

| When | What |
| --- | --- |
| Nov 24–30 | Self-annotation and κ; decisions 2 and 3; manual pass over the error-analysis sheets; LLM upper bound if HPC is available |
| Dec 1–3 | Freeze measures, run test once, final tables; prepare slides (check our talk date, Dec 3–10) |
| Dec 4–10 | Write the paper (≤ 8 pages) and submit on Dec 10 |

Cut unless time allows: M4 (logistic regression), OneStopEnglish control.

## How to reproduce

```sh
pip install -r requirements.txt
python -m nltk.downloader averaged_perceptron_tagger_eng cmudict
python run_all.py && python error_analysis.py && python secondary_analysis.py
```
