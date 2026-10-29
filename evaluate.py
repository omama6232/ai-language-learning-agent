"""
Evaluation script: measures the performance of our rule-based grammar
checker (nlp_engine.py) using standard classification metrics.

Why this design:
    Our checker's job is a binary classification task per sentence:
    "does this sentence contain an error?" (yes/no). To measure that
    properly we need TWO kinds of labeled sentences:
      - Sentences that DO contain an error   (label = 1) -> from JFLEG
      - Sentences that do NOT contain an error (label = 0) -> hand-picked
        sentences + the human-corrected JFLEG versions
    Testing only on erroneous sentences (like JFLEG alone) can only tell
    us Recall. Adding correct sentences lets us also measure Precision
    and get a true Accuracy / F1-score - which is what "appropriate
    metrics for evaluation" in an AI course normally expects.

Fair testing:
    If models/split.json exists (created by train_model.py) the evaluation
    uses ONLY the HOLDOUT sentences - sentences that were never used while
    experimenting with models and thresholds. If it is missing, the first
    40 JFLEG sentences are used (as in the original version).

Usage:
    1. Make sure data/test.csv (JFLEG) is in the data/ folder.
    2. (optional, once) python train_model.py     -> creates the holdout split
    3. Run: python evaluate.py
"""

import csv
import json
import os
import time
from nlp_engine import check_grammar

CSV_PATH = os.path.join(os.path.dirname(__file__), "data", "test.csv")
SPLIT_PATH = os.path.join(os.path.dirname(__file__), "models", "split.json")
MAX_ERROR_SENTENCES = 40  # fallback: how many JFLEG (erroneous) sentences to sample

# Hand-picked grammatically correct sentences, used as the "negative" class
# so we can measure false positives (Precision) as well as false negatives.
CORRECT_SENTENCES = [
    "She walks to school every morning.",
    "They are studying for their exam.",
    "He has finished his homework.",
    "We were late for the meeting.",
    "I enjoy reading books in my free time.",
    "The children play in the park after school.",
    "My sister works at a hospital.",
    "This restaurant serves delicious food.",
    "The weather is nice today.",
    "He does not like spicy food.",
    "They have already left for the airport.",
    "She was preparing dinner when I arrived.",
    "We are planning a trip next month.",
    "The teacher explained the lesson clearly.",
    "I have never been to Paris.",
]


def load_error_sentences(csv_path: str, limit: int) -> list[str]:
    sentences = []
    if not os.path.exists(csv_path):
        return sentences
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if "sentence" in row and row["sentence"].strip():
                sentences.append(row["sentence"].strip())
            if len(sentences) >= limit:
                break
    return sentences


def load_test_sets():
    """Returns (erroneous sentences, correct sentences, description)."""
    if os.path.exists(SPLIT_PATH):
        with open(SPLIT_PATH, encoding="utf-8") as f:
            split = json.load(f)
        errors = split["holdout_erroneous"]
        correct = CORRECT_SENTENCES + split["holdout_correct"]
        return errors, correct, "holdout split (never used for tuning)"
    return (load_error_sentences(CSV_PATH, MAX_ERROR_SENTENCES), CORRECT_SENTENCES,
            "first JFLEG sentences (no holdout split found)")


def run_evaluation(verbose: bool = False):
    error_sentences, correct_sentences, source = load_test_sets()

    if not error_sentences:
        print(f"Could not find dataset at: {CSV_PATH}")
        print("Make sure you've placed the JFLEG CSV file (as test.csv) in the data/ folder.")
        return

    labeled_set = [(s, 1) for s in error_sentences] + [(s, 0) for s in correct_sentences]

    tp = fp = tn = fn = 0
    print(f"Test data: {source}")
    print(f"Testing {len(labeled_set)} sentences "
          f"({len(error_sentences)} known-erroneous + {len(correct_sentences)} known-correct)...\n")

    start = time.time()
    for sentence, true_label in labeled_set:
        issues = check_grammar(sentence)
        predicted_label = 1 if issues else 0

        if predicted_label == 1 and true_label == 1:
            tp += 1
            outcome = "TP"
        elif predicted_label == 1 and true_label == 0:
            fp += 1
            outcome = "FP"
        elif predicted_label == 0 and true_label == 0:
            tn += 1
            outcome = "TN"
        else:
            fn += 1
            outcome = "FN"

        if verbose or outcome in ("FP", "FN"):
            print(f"[{outcome}] {sentence}")
    latency_ms = (time.time() - start) / len(labeled_set) * 1000

    total = tp + fp + tn + fn
    accuracy = (tp + tn) / total if total else 0
    precision = tp / (tp + fp) if (tp + fp) else 0
    recall = tp / (tp + fn) if (tp + fn) else 0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0

    print("\n" + "=" * 55)
    print("CONFUSION MATRIX")
    print(f"  True Positive  (correctly flagged an error):     {tp}")
    print(f"  False Positive (flagged a correct sentence):      {fp}")
    print(f"  True Negative  (correctly passed a correct one):  {tn}")
    print(f"  False Negative (missed a real error):             {fn}")
    print("-" * 55)
    print("PERFORMANCE METRICS")
    print(f"  Accuracy:  {accuracy * 100:.1f}%")
    print(f"  Precision: {precision * 100:.1f}%")
    print(f"  Recall:    {recall * 100:.1f}%")
    print(f"  F1-score:  {f1 * 100:.1f}%")
    print(f"  Response time: {latency_ms:.1f} ms per sentence")
    print("=" * 55)


if __name__ == "__main__":
    run_evaluation()
