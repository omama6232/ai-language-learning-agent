"""
Machine-learning grammar-error detector (inference side).

The model itself is produced by train_model.py and stored in
models/error_detector.joblib. This module only:
  * builds the feature vector for one sentence (the SAME code that training
    uses, so train/test features can never drift apart), and
  * asks the trained classifier "does this sentence contain an error?".

It is deliberately defensive: if scikit-learn or the model file is missing,
or was saved by an incompatible scikit-learn version, every function simply
returns None and the project keeps working with its rule-based checks only.
(Fix: run `python train_model.py` once on your own machine.)
"""

import math
import os
import warnings

import numpy as np
from scipy.sparse import csr_matrix, hstack

MODEL_PATH = os.path.join(os.path.dirname(__file__), "models", "error_detector.joblib")

_artifact = None
_tried = False


# ---------------------------------------------------------------- features
def tag_sequence(doc) -> str:
    """Part-of-speech tag sequence of a spaCy doc, e.g. 'PRP VBZ DT NN .'"""
    return " ".join(t.tag_ for t in doc)


def dense_features(n_rule_issues: int, n_tokens: int) -> list[float]:
    """Small numeric features: what the rule-based checker found + length."""
    return [
        min(n_rule_issues, 3) / 3.0,          # how many rule issues (capped)
        1.0 if n_rule_issues else 0.0,        # did any rule fire?
        min(n_tokens, 60) / 60.0,             # sentence length
    ]


DENSE_NAMES = ["rule_issue_count", "rule_flag", "sentence_length"]


def new_vectorizers() -> dict:
    """Three TF-IDF views of a sentence: words, characters, POS-tag n-grams."""
    from sklearn.feature_extraction.text import TfidfVectorizer
    return {
        "word": TfidfVectorizer(ngram_range=(1, 2), min_df=2, sublinear_tf=True),
        "char": TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 4), min_df=3, sublinear_tf=True),
        "pos": TfidfVectorizer(ngram_range=(1, 3), min_df=2, token_pattern=r"\S+", lowercase=False),
    }


def build_matrix(vecs: dict, sentences, tag_seqs, dense, fit: bool = False,
                 groups=("word", "char", "pos", "dense")):
    """Stack the chosen feature groups into one sparse matrix."""
    parts = []
    if "word" in groups:
        parts.append(vecs["word"].fit_transform(sentences) if fit else vecs["word"].transform(sentences))
    if "char" in groups:
        parts.append(vecs["char"].fit_transform(sentences) if fit else vecs["char"].transform(sentences))
    if "pos" in groups:
        parts.append(vecs["pos"].fit_transform(tag_seqs) if fit else vecs["pos"].transform(tag_seqs))
    if "dense" in groups:
        parts.append(csr_matrix(np.asarray(dense, dtype=float)))
    return hstack(parts).tocsr()


def score_of(model, X) -> np.ndarray:
    """Probability-like score in [0, 1] that each row is an erroneous sentence."""
    if hasattr(model, "predict_proba"):
        return model.predict_proba(X)[:, 1]
    d = model.decision_function(X)
    return 1.0 / (1.0 + np.exp(-d))


# --------------------------------------------------------------- inference
def _load():
    global _artifact, _tried
    if _tried:
        return _artifact
    _tried = True
    try:
        import joblib
        if os.path.exists(MODEL_PATH):
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                _artifact = joblib.load(MODEL_PATH)
    except Exception:
        _artifact = None
    return _artifact


def is_available() -> bool:
    return _load() is not None


def score(doc, n_rule_issues: int):
    """ML probability that the sentence has an error, or None if no model."""
    art = _load()
    if art is None:
        return None
    try:
        sentence = doc.text
        X = build_matrix(
            art["vectorizers"], [sentence], [tag_sequence(doc)],
            [dense_features(n_rule_issues, len(doc))],
            groups=art["feature_groups"],
        )
        return float(score_of(art["model"], X)[0])
    except Exception:
        return None


def ml_issue(doc, n_rule_issues: int):
    """
    Returns an issue message when the model flags a sentence that the rules
    did NOT flag; otherwise None. (If rules already flagged it, we keep the
    rule's more specific message.)
    """
    if n_rule_issues:
        return None
    s = score(doc, n_rule_issues)
    if s is None:
        return None
    art = _load()
    if s >= art["threshold"]:
        return (f"ML-detected possible grammar issue: this sentence may contain "
                f"an error (confidence {s * 100:.0f}%).")
    return None
