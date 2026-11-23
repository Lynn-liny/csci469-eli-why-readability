# M2 features, M3 terminology measure and first error analysis

All numbers are on the 240 dev explanations, with cutoffs fit on the 600 train explanations (same seed-469 question split as M0/M1). `python run_all.py` regenerates `outputs/dev_summary.md`, which has the full tables for both label targets; `python error_analysis.py` regenerates the error-analysis files.

## Method notes

**M2** (`m2_features.py`). Every feature is scored alone. Tokens and sentences reuse the M1 boundaries. Word frequencies come from wordfreq 3.1.1 (Zipf scale); "outside 5,000" uses its top-5,000 English list. POS tags come from the NLTK averaged perceptron tagger, and noun chunks from a regular-expression chunker over the tags (determiner, adjectives/nouns, head noun). We use the moving-average type-token ratio (window 50) instead of plain TTR, because plain TTR falls with text length and would mostly re-measure word count. The direction of every feature (whether higher means harder) was fixed before looking at dev, and the train Spearman signs agree with it.

**M3** (`m3_terminology.py`). Candidate terms are noun and adjective unigrams and 2–3-word noun-chunk n-grams. Termhood is Dunning's log-likelihood (G²) on document frequency, contrasting train explanations written for Graduate readers with those written for Elementary readers. Each question has one explanation per level, so topic words occur on both sides and cancel. A term needs G² ≥ 10.83 (p < 0.001), a higher foreground rate, and at least 3 foreground documents. To prevent leakage into the cutoffs, train explanations are scored with an inventory built from the other four folds of train questions; dev and test use the full-train inventory.

- `term_density`: share of tokens inside inventory terms.
- `rare_term_density`: inventory terms plus any noun or adjective with Zipf < 3.0. The train inventory is small (46 terms, mostly general academic words such as *psychological*, *factors*, *phenomenon*), and dev questions have new topics, so this variant also catches topic-specific technical words.
- `defined_term_ratio`: share of distinct terms the text defines at least once ("X is a …", "X, which means …", "X (…)", "called X", …).
- `undefined_term_density`: `rare_term_density` counting only undefined terms.

## Dev results, human-perceived level (primary)

"ρ | length" is Spearman ρ with word count partialled out: what the measure tells us beyond "longer text reads as more advanced".

| Measure | Version | Accuracy | Macro-F1 | Spearman ρ | ρ \| length |
| --- | --- | ---: | ---: | ---: | ---: |
| word_count | M0 | 57.92% | 0.379 | 0.521 | — |
| dale_chall | M1 | 57.08% | 0.387 | 0.418 | 0.215 |
| oov_5000 | M2 | 56.67% | 0.335 | 0.328 | 0.205 |
| rare_word_share | M2 | 53.33% | 0.342 | 0.353 | 0.235 |
| flesch_kincaid | M1 | 55.00% | 0.391 | 0.347 | 0.198 |
| rare_term_density | M3 | 56.67% | 0.379 | **0.476** | **0.329** |
| undefined_term_density | M3 | 56.67% | 0.378 | 0.456 | 0.302 |
| term_density | M3 | 55.42% | 0.391 | 0.340 | 0.161 |
| defined_term_ratio | M3 | 30.00% | 0.295 | −0.029 | −0.037 |

## Findings so far

1. **Length dominates the perceived labels.** Word count is still the best single predictor of the perceived level (accuracy 57.92%, ρ 0.521). No measure beats it on accuracy, and all measures almost never predict Graduate correctly (Graduate F1 ≤ 0.15).
2. **Terminology adds the most beyond length.** Once word count is controlled for, `rare_term_density` has the highest partial ρ of all 20 measures (0.329, vs. 0.215 for the best formula, Dale–Chall). This is the first piece of evidence for the hypothesis that content difficulty matters beyond surface form.
3. **For intended levels, M3 errors almost all point the same way.** In the 50 worst intended-level errors, `term_density`, `rare_term_density` and `undefined_term_density` call the text *harder* than its intended level in 49, 48 and 48 cases. In other words, explanations written for lower levels still carry technical vocabulary, which is what the hypothesis predicts. The surface formulas split more evenly between too easy and too hard.
4. **Perceived-level errors are mostly "too easy".** Most measures place texts that humans perceived as advanced one level too low. Among the heuristic tags, `undefined_terms` and `short_sent_technical` are the most common tags in the worst errors of nearly every measure.
5. **Definition detection does not work yet.** `defined_term_ratio` is at chance level. Regex definitions are rare in these texts, and texts with no terms default to 1.0. It should be revised (e.g. count appositives and "such as" lists) or dropped.
6. **Some perceived labels look noisy.** Several top errors are short, plain texts labelled Graduate (for example, a series-circuit explanation written for Elementary). This is a reason to do the planned 100-item annotation with weighted κ before over-interpreting the perceived results.

## Error-analysis files

`outputs/error_analysis_perceived.csv` and `outputs/error_analysis_intended.csv` list, for every measure, the 50 dev explanations with the largest level gap (ties broken by how far the score crossed the cutoff). The `auto_tags` column holds heuristic tags (thresholds from train): `short_sent_technical`, `long_sent_common`, `list_formatting`, `analogy`, `undefined_terms`, `other`. The `manual_category` column is empty, ready for hand labelling. Counts per measure are in `outputs/error_analysis_<target>.md`.

## Limitations

- Only the 1,200 annotated explanations are used. The term inventory comes from 200 Graduate and 200 Elementary train texts, which is small.
- The annotated subset has no generator field, so these results cannot be broken down by generator.
- Thresholds maximize train accuracy, which favors predicting High School (the majority perceived class).
