# Flesch readability evaluation

## Reproduce the dev results

Run from the repository root with Python 3:

```sh
python m1_flesch_reading_ease.py
```

The script downloads the pinned ELI-Why human-annotated JSONL and reuses the question-level split in m0_majority.py (seed 469). There are 200 train, 80 dev, and 120 held-out test questions. Every question has three explanations. Cutoffs maximize accuracy on the 600 train explanations for each score and label target separately. Evaluation uses 240 dev explanations.

The raw Reading Ease score increases as text gets easier. The script negates it for cutoff fitting so that all three measures use the same prediction rule. Both Flesch formulas share the same heuristic word, sentence, and syllable counts. The JSON prints F1 by class and confusion matrices for both label targets. Matrix rows are actual labels and columns are predictions. Both axes use Elementary, High School, Graduate.

## Expected results for human-perceived levels

| Method | Accuracy | Macro-F1 | Mean absolute ordinal error | Elementary F1 | High School F1 | Graduate F1 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Word count | 57.92% | 0.379 | 0.421 | 0.435 | 0.702 | 0.000 |
| Flesch–Kincaid Grade Level | 55.00% | 0.391 | 0.463 | 0.388 | 0.675 | 0.111 |
| Flesch Reading Ease | 54.58% | 0.336 | 0.454 | 0.286 | 0.684 | 0.039 |

As a quick check, the Reading Ease confusion matrix should be [[12, 51, 0], [9, 118, 1], [0, 48, 1]]. Word count predicts zero Graduate examples. Grade Level correctly predicts 3 of 49 Graduate examples. Reading Ease correctly predicts 1 of 49. The intended-level accuracy for Reading Ease is 48.33% on this same annotated subset. These are development results. The held-out split is reserved for final evaluation.


## Automated Readability Index (ARI)

Run `python m1_ari.py` from the repository root. ARI uses letters and digits per word and words per sentence. It reuses the word and sentence boundaries from the Flesch evaluation. The implementation follows the [ARI formula documented by NIST](https://tsapps.nist.gov/publication/get_pdf.cfm?pub_id=914701).

The same train/dev split and train-only accuracy fitting apply. For human-perceived levels, the raw cutoffs are approximately 8.729 and 18.280.

| Label target | Accuracy | Macro-F1 | Mean absolute ordinal error | Elementary F1 | High School F1 | Graduate F1 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Human-perceived | 54.17% | 0.349 | 0.471 | 0.214 | 0.686 | 0.145 |
| Intended | 47.08% | 0.433 | 0.713 | 0.513 | 0.210 | 0.576 |

The human-perceived confusion matrix is `[[9, 54, 0], [9, 117, 2], [3, 42, 4]]`. ARI correctly predicts 4 of 49 Graduate texts. Word count correctly predicts zero, but its overall accuracy and macro-F1 are higher on this split.


## New Dale–Chall

Run `python -m pip install textstat==0.7.13` and then `python m1_dale_chall.py` from the repository root. The pinned package supplies its English easy-word list. Our script implements the formula and reuses the M1 word and sentence boundaries. It lowercases words, normalizes curly apostrophes, and uses exact word matches without stemming. The same question split and train-only accuracy fitting apply.

| Label target | Accuracy | Macro-F1 | Mean absolute ordinal error | Elementary F1 | High School F1 | Graduate F1 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Human-perceived | 57.08% | 0.387 | 0.446 | 0.467 | 0.693 | 0.000 |
| Intended | 50.83% | 0.502 | 0.571 | 0.617 | 0.385 | 0.504 |

The human-perceived confusion matrix is `[[25, 38, 0], [15, 112, 1], [4, 45, 0]]`. Of the 49 texts perceived as Graduate, word count classified all 49 as High School. Dale–Chall kept 45 at High School, moved four down to Elementary, and corrected zero. Its sole Graduate prediction was a false positive on a High School text. These dev results use cutoffs optimized for training accuracy. They cover the whole annotated dev subset, so they do not isolate the effect of short sentences with uncommon words.
