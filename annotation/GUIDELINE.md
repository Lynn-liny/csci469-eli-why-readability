# Annotation guideline: perceived educational level (draft)

**Purpose.** Two of us label the same 100 explanations independently. Weighted Cohen's κ between us, and between each of us and the released ELI-Why perceived labels, shows whether we understand the labels that our primary evaluation relies on.

**Before you start.** Check these definitions against the annotation instructions in the ELI-Why paper (Joshi et al. 2025, human study appendix) and adjust them if the wording differs. Both annotators must use the same final version, and nobody should change it once labelling has started.

## Task

For each row of your sheet (`sheet_A.csv` or `sheet_B.csv`), read the question and the explanation and write in the `level` column the **lowest** education level of a reader who could understand the explanation without outside help:

| Level | A reader at this level… | Typical signs |
| --- | --- | --- |
| **Elementary** | is about 6–11 years old and has no subject background | everyday words, concrete examples, any new idea is explained in simple terms |
| **High School** | has general school knowledge (basic biology, physics, history, statistics) but no specialization | some subject terms, mostly explained or guessable from context; multi-step reasoning |
| **Graduate** | has specialized training in the field | technical terms used without definition, assumes theories and methods are known, dense or abstract |

## Rules

1. Judge how the explanation **reads**, not what the question is about. A question about quantum physics can still have an Elementary explanation.
2. Do **not** guess which audience the text was written for. We want the perceived level, not the intended one.
3. Length alone is not a reason to go up a level. A long text in plain words is still Elementary.
4. Judge the explanation as a whole. One hard word in an otherwise simple text does not make it Graduate.
5. If you are torn between two levels, choose the lower one and write `unsure` in `notes`.
6. Work alone. Do not discuss items, and do not open `annotation/key.csv` until both sheets are complete.

## Afterwards

```sh
python kappa.py annotation/sheet_A.csv annotation/sheet_B.csv
```

This prints exact agreement and linear and quadratic weighted κ for A vs B, each annotator vs the released perceived labels, and each annotator vs the intended labels. Discuss disagreements only after computing κ, and record any patterns in `notes`. These patterns are useful for the error analysis.
