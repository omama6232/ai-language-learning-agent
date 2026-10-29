"""
Trains and evaluates the machine-learning grammar-error detector.

PROBLEM (supervised binary classification)
    Input : one English sentence
    Output: 1 = "contains a grammar/spelling error", 0 = "looks correct"

DATA
    data/test.csv is the JFLEG corpus: each row has an erroneous learner
    sentence and 4 human-corrected versions.
        erroneous original  -> label 1
        corrected versions  -> label 0
    JFLEG alone is small (~565 erroneous sentences), so the training set is
    enlarged with SYNTHETIC ERRORS: correct sentences are deliberately
    corrupted (typos, wrong verb forms, dropped articles, wrong prepositions,
    homophone swaps ...). Synthetic data is used for TRAINING ONLY.

FEATURES (see ml_detector.py)
    word TF-IDF, character TF-IDF, part-of-speech n-gram TF-IDF, plus what the
    rule-based checker found (rule_flag, rule_issue_count) and sentence length.

EVALUATION PROTOCOL (no data leakage)
    * 20% of the source sentences are locked away as a HOLDOUT set that is
      never used for training, tuning or threshold selection.
    * Model selection / tuning uses 5-fold GroupKFold on the remaining 80%.
      Groups = the source sentence, so an original and its corrections never
      sit on opposite sides of a split.
    * Synthetic sentences are only generated from training-fold sentences.

OUTPUTS (written to models/)
    error_detector.joblib  trained model used by the app
    metrics.json           every number reported below
    split.json             which sentences are holdout (used by evaluate.py)
    *.png                  charts for the report / presentation

Usage:  python train_model.py
"""

import csv
import json
import os
import random
import re
import time
import warnings

import joblib
import numpy as np
import sklearn
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (accuracy_score, auc, confusion_matrix,
                             precision_recall_curve, precision_recall_fscore_support,
                             roc_auc_score, roc_curve)
from sklearn.model_selection import GroupKFold, GroupShuffleSplit
from sklearn.naive_bayes import ComplementNB
from sklearn.ensemble import RandomForestClassifier
from sklearn.svm import LinearSVC

import ml_detector as md
from nlp_engine import check_grammar, check_grammar_doc, nlp

warnings.filterwarnings("ignore")

HERE = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(HERE, "data", "test.csv")
OUT_DIR = os.path.join(HERE, "models")
SEED = 42
MAX_SYN_PER_SENTENCE = 4

os.makedirs(OUT_DIR, exist_ok=True)
random.seed(SEED)
np.random.seed(SEED)
T0 = time.time()


def log(*a):
    print(f"[{time.time() - T0:6.0f}s]", *a, flush=True)


# ===================================================================== data
_QUOTED = re.compile(r"'((?:[^'\\]|\\.)*)'|\"((?:[^\"\\]|\\.)*)\"")


def load_dataset():
    """Returns texts, labels (1=error), groups (source-sentence id)."""
    texts, labels, groups = [], [], []
    with open(CSV_PATH, encoding="utf-8") as f:
        for gid, row in enumerate(csv.DictReader(f)):
            original = row["sentence"].strip()
            fixes = {a.strip() or b.strip() for a, b in _QUOTED.findall(row["corrections"])}
            fixes = {x for x in fixes if x}
            if original not in fixes:           # original really was erroneous
                texts.append(original); labels.append(1); groups.append(gid)
            for fx in sorted(fixes):
                texts.append(fx); labels.append(0); groups.append(gid)
    return texts, np.array(labels), np.array(groups)


# ============================================================ synthetic errors
PREPOSITION_SWAP = {"in": "on", "on": "at", "at": "in", "of": "for", "for": "of",
                    "to": "at", "with": "by", "from": "of", "by": "with"}
HOMOPHONE_SWAP = {"their": "there", "there": "their", "they're": "their", "your": "you're",
                  "you're": "your", "its": "it's", "it's": "its", "than": "then",
                  "then": "than", "too": "to", "affect": "effect", "effect": "affect",
                  "lose": "loose", "were": "where", "where": "were"}


def _typo(word, rng):
    i = rng.randrange(1, len(word) - 1)
    kind = rng.choice(("swap", "drop", "double"))
    if kind == "swap":
        return word[:i] + word[i + 1] + word[i] + word[i + 2:]
    if kind == "drop":
        return word[:i] + word[i + 1:]
    return word[:i] + word[i] + word[i:]


def corrupt(doc, rng):
    """Inject ONE error into a correct sentence. Returns (text, kind) or None."""
    toks = [t.text_with_ws for t in doc]
    options = []
    for i, t in enumerate(doc):
        low = t.lower_
        if t.is_alpha and len(low) > 3 and t.pos_ != "PROPN":
            options.append(("typo", i))
        if t.tag_ == "VBZ" and low not in ("is", "has", "does") and len(low) > 3:
            options.append(("verb_agreement", i))
        if t.tag_ == "VBD" and low.endswith("ed") and len(low) > 4:
            options.append(("verb_tense", i))
        if low in ("a", "an", "the"):
            options.append(("article_drop", i))
        if low in ("a", "an"):
            options.append(("article_swap", i))
        if t.tag_ == "NNS" and low.endswith("s") and len(low) > 3:
            options.append(("plural_noun", i))
        if low in PREPOSITION_SWAP:
            options.append(("preposition", i))
        if low in HOMOPHONE_SWAP:
            options.append(("homophone", i))
        if low in ("are", "is", "were", "was"):
            options.append(("be_agreement", i))
        if low == "has" and i > 0 and doc[i - 1].lower_ in ("he", "she", "it"):
            options.append(("have_agreement", i))
        if low == "have" and i > 0 and doc[i - 1].lower_ in ("he", "she", "it"):
            options.append(("have_agreement", i))
        if low == "n't":
            options.append(("contraction", i))
    alpha = [i for i, t in enumerate(doc) if t.is_alpha]
    if len(alpha) >= 4:
        options.append(("word_order", None))
    if not options:
        return None

    kind, i = rng.choice(options)
    if kind == "word_order":
        k = rng.choice(alpha[:-1])
        if doc[k + 1].i != doc[k].i + 1:
            return None
        a, b = doc[k], doc[k + 1]
        toks[k], toks[k + 1] = b.text + a.whitespace_, a.text + b.whitespace_
    else:
        t = doc[i]; ws = t.whitespace_; w = t.text
        if kind == "typo":
            toks[i] = _typo(w, rng) + ws
        elif kind == "verb_agreement":
            base = w[:-2] if w.lower().endswith(("ses", "shes", "ches", "xes", "oes")) else w[:-1]
            toks[i] = base + ws
        elif kind == "verb_tense":
            toks[i] = w[:-2] + ws
        elif kind == "article_drop":
            toks[i] = ""
        elif kind == "article_swap":
            toks[i] = ("an" if w.lower() == "a" else "a") + ws
        elif kind == "plural_noun":
            toks[i] = w[:-1] + ws
        elif kind == "preposition":
            toks[i] = PREPOSITION_SWAP[w.lower()] + ws
        elif kind == "homophone":
            toks[i] = HOMOPHONE_SWAP[w.lower()] + ws
        elif kind == "be_agreement":
            toks[i] = {"are": "is", "is": "are", "were": "was", "was": "were"}[w.lower()] + ws
        elif kind == "have_agreement":
            toks[i] = ("have" if w.lower() == "has" else "has") + ws
        elif kind == "contraction":
            toks[i] = "nt" + ws
        if w[:1].isupper() and toks[i]:
            toks[i] = toks[i][0].upper() + toks[i][1:]
    out = "".join(toks).strip()
    if not out or out == doc.text.strip():
        return None
    return out, kind


# ============================================================== metrics utils
def prf(y_true, y_pred):
    p, r, f, _ = precision_recall_fscore_support(y_true, y_pred, average="binary", zero_division=0)
    return {"accuracy": accuracy_score(y_true, y_pred), "precision": p, "recall": r, "f1": f}


def full_metrics(y_true, y_pred, scores=None):
    m = prf(y_true, y_pred)
    if scores is not None:
        m["roc_auc"] = roc_auc_score(y_true, scores)
    tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=[0, 1]).ravel()
    m.update({"tp": int(tp), "fp": int(fp), "tn": int(tn), "fn": int(fn)})
    return {k: (round(float(v), 4) if isinstance(v, (float, np.floating)) else v) for k, v in m.items()}


# ============================================================= build features
log("loading JFLEG ...")
texts, y, groups = load_dataset()
log(f"{len(texts)} sentences | errors={int(y.sum())} correct={int((y == 0).sum())} | "
    f"source sentences={len(set(groups))}")

log("parsing sentences with spaCy ...")
docs = list(nlp.pipe(texts, batch_size=64))
rule_n = np.array([len(check_grammar_doc(d, d.text)) for d in docs])
tags = [md.tag_sequence(d) for d in docs]
dense = [md.dense_features(int(n), len(d)) for n, d in zip(rule_n, docs)]

# --- locked-away holdout (by source sentence) -------------------------------
splitter = GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=SEED)
dev_idx, hold_idx = next(splitter.split(texts, y, groups))
dev_idx = np.array(sorted(dev_idx)); hold_idx = np.array(sorted(hold_idx))
log(f"dev={len(dev_idx)} sentences, holdout={len(hold_idx)} sentences")

# --- synthetic errors, generated ONLY from dev correct sentences -------------
rng = random.Random(SEED)
syn_text, syn_src, syn_rank, syn_kind = [], [], [], []
for i in dev_idx:
    if y[i] != 0:
        continue
    seen, rank, tries = {texts[i]}, 0, 0
    while rank < MAX_SYN_PER_SENTENCE and tries < 12:
        tries += 1
        res = corrupt(docs[i], rng)
        if res and res[0] not in seen:
            seen.add(res[0]); syn_text.append(res[0]); syn_src.append(i)
            syn_rank.append(rank); syn_kind.append(res[1]); rank += 1
syn_src = np.array(syn_src); syn_rank = np.array(syn_rank)
log(f"generated {len(syn_text)} synthetic erroneous sentences")
kind_counts = {k: syn_kind.count(k) for k in sorted(set(syn_kind))}
syn_docs = list(nlp.pipe(syn_text, batch_size=64))
syn_rule_n = np.array([len(check_grammar_doc(d, d.text)) for d in syn_docs])
syn_tags = [md.tag_sequence(d) for d in syn_docs]
syn_dense = [md.dense_features(int(n), len(d)) for n, d in zip(syn_rule_n, syn_docs)]
log(f"rule-based checker alone flags {np.mean(syn_rule_n > 0) * 100:.0f}% of the synthetic errors")


# ============================================================ model factories
MODELS = {
    "Logistic Regression": lambda C=3.0: LogisticRegression(C=C, max_iter=3000, class_weight="balanced"),
    "Linear SVM": lambda C=0.5: LinearSVC(C=C, class_weight="balanced"),
    "Complement Naive Bayes": lambda a=0.3: ComplementNB(alpha=a),
    "Random Forest": lambda n=200: RandomForestClassifier(
        n_estimators=n, class_weight="balanced_subsample", n_jobs=-1, random_state=SEED, min_samples_leaf=1),
}


def make_train_set(real_idx, n_syn):
    """Real training rows + synthetic rows derived from those same rows."""
    sel = np.where(np.isin(syn_src, real_idx) & (syn_rank < n_syn))[0] if n_syn else np.array([], dtype=int)
    T = [texts[i] for i in real_idx] + [syn_text[j] for j in sel]
    G = [tags[i] for i in real_idx] + [syn_tags[j] for j in sel]
    D = [dense[i] for i in real_idx] + [syn_dense[j] for j in sel]
    Y = np.concatenate([y[real_idx], np.ones(len(sel), dtype=int)])
    return T, G, D, Y


def fit_model(factory, real_idx, n_syn, groups_used=("word", "char", "pos", "dense")):
    T, G, D, Y = make_train_set(real_idx, n_syn)
    vecs = md.new_vectorizers()
    X = md.build_matrix(vecs, T, G, D, fit=True, groups=groups_used)
    model = factory().fit(X, Y)
    return vecs, model


def score_rows(vecs, model, idx, groups_used=("word", "char", "pos", "dense")):
    X = md.build_matrix(vecs, [texts[i] for i in idx], [tags[i] for i in idx],
                        [dense[i] for i in idx], groups=groups_used)
    return md.score_of(model, X)


def cv_run(factory, n_syn, groups_used=("word", "char", "pos", "dense"), folds=5):
    """5-fold grouped CV on the dev set. Returns metrics + out-of-fold scores."""
    oof = np.zeros(len(texts)); oof[:] = np.nan
    for tr, te in GroupKFold(folds).split(dev_idx, y[dev_idx], groups[dev_idx]):
        tr_i, te_i = dev_idx[tr], dev_idx[te]
        vecs, model = fit_model(factory, tr_i, n_syn, groups_used)
        oof[te_i] = score_rows(vecs, model, te_i, groups_used)
    s = oof[dev_idx]
    pred = (s >= 0.5).astype(int)
    m = full_metrics(y[dev_idx], pred, s)
    return m, oof


results = {"dataset": {
    "sentences": len(texts), "erroneous": int(y.sum()), "correct": int((y == 0).sum()),
    "source_sentences": int(len(set(groups))), "dev": int(len(dev_idx)), "holdout": int(len(hold_idx)),
    "synthetic_generated": len(syn_text), "synthetic_by_type": kind_counts},
    "library_versions": {"scikit-learn": sklearn.__version__}}

# ====================== baseline: the existing rule-based checker (no ML) ====
rule_pred_dev = (rule_n[dev_idx] > 0).astype(int)
results["baseline_rules_dev_cv"] = full_metrics(y[dev_idx], rule_pred_dev)
log("BASELINE rules-only on dev:", results["baseline_rules_dev_cv"])

# ================================ EXPERIMENT 1: algorithm comparison =========
log("EXPERIMENT 1: comparing algorithms (5-fold grouped CV, default settings) ...")
exp1 = {}
for name, factory in MODELS.items():
    for n_syn in (0, 3):
        t = time.time()
        m, _ = cv_run(factory, n_syn)
        m["seconds"] = round(time.time() - t, 1)
        exp1[f"{name} | synthetic x{n_syn}"] = m
        log(f"  {name:24s} syn x{n_syn}: F1={m['f1']:.3f} P={m['precision']:.3f} "
            f"R={m['recall']:.3f} AUC={m['roc_auc']:.3f}  ({m['seconds']}s)")
results["experiment1_algorithms"] = exp1

# ================================ EXPERIMENT 2: hyper-parameter tuning =======
log("EXPERIMENT 2: tuning the two best linear model families ...")
exp2 = {}
best = {"f1": -1}
for fam, grid in (("Logistic Regression", [0.3, 1.0, 3.0, 10.0, 30.0]),
                  ("Linear SVM", [0.05, 0.2, 0.5, 1.0])):
    for C in grid:
        for n_syn in (0, 2, 4):
            m, _ = cv_run(lambda C=C, fam=fam: MODELS[fam](C), n_syn)
            exp2[f"{fam} | C={C} | syn x{n_syn}"] = m
            if m["f1"] > best["f1"]:
                best = {"f1": m["f1"], "family": fam, "C": C, "n_syn": n_syn}
    log(f"  done {fam}; best so far {best}")
results["experiment2_tuning"] = exp2
results["best_config"] = best
log("BEST CONFIG:", best)

best_factory = lambda: MODELS[best["family"]](best["C"])

# ====================== EXPERIMENT 3: decision-threshold optimisation =========
log("EXPERIMENT 3: choosing the decision threshold on out-of-fold scores ...")
m_best, oof = cv_run(best_factory, best["n_syn"])
oof_dev = oof[dev_idx]
rule_flag_dev = rule_n[dev_idx] > 0
thr_rows, best_thr, best_thr_f1 = [], 0.5, -1
for thr in np.round(np.arange(0.2, 0.86, 0.025), 3):
    ml_only = (oof_dev >= thr)
    hyb = ml_only | rule_flag_dev                 # what the app actually does
    mh = prf(y[dev_idx], hyb.astype(int))
    thr_rows.append({"threshold": float(thr), **{k: round(v, 4) for k, v in mh.items()}})
    if mh["f1"] > best_thr_f1:
        best_thr_f1, best_thr = mh["f1"], float(thr)
results["experiment3_threshold"] = {"chosen": best_thr, "curve": thr_rows}
log(f"  chosen threshold = {best_thr} (hybrid F1 on dev = {best_thr_f1:.3f})")

# ====================== EXPERIMENT 4: feature ablation ========================
log("EXPERIMENT 4: ablation - which feature groups matter? ...")
exp4 = {}
all_groups = ("word", "char", "pos", "dense")
for label, grp in (("all features", all_groups),
                   ("without word n-grams", ("char", "pos", "dense")),
                   ("without char n-grams", ("word", "pos", "dense")),
                   ("without POS n-grams", ("word", "char", "dense")),
                   ("without rule features", ("word", "char", "pos"))):
    m, _ = cv_run(best_factory, best["n_syn"], grp)
    exp4[label] = m
    log(f"  {label:26s} F1={m['f1']:.3f} AUC={m['roc_auc']:.3f}")
results["experiment4_ablation"] = exp4

# ============================ FINAL: train on dev, test once on HOLDOUT =======
log("FINAL: training on the full dev set and testing ONCE on the holdout ...")
vecs, model = fit_model(best_factory, dev_idx, best["n_syn"])
hold_scores = score_rows(vecs, model, hold_idx)
hold_y = y[hold_idx]
hold_rule = (rule_n[hold_idx] > 0)
final = {
    "rule-based checker (the app)": full_metrics(hold_y, hold_rule.astype(int)),
    "ml_only": full_metrics(hold_y, (hold_scores >= best_thr).astype(int), hold_scores),
    "hybrid rules+ML (experiment)": full_metrics(
        hold_y, ((hold_scores >= best_thr) | hold_rule).astype(int), hold_scores),
}
results["final_holdout"] = final
for k, v in final.items():
    log(f"  {k:28s} acc={v['accuracy']:.3f} P={v['precision']:.3f} R={v['recall']:.3f} F1={v['f1']:.3f}")

# --- response latency ---------------------------------------------------------
sample = [texts[i] for i in hold_idx[:100]]
t = time.time()
for s_ in sample:
    check_grammar(s_)
rules_ms = (time.time() - t) / len(sample) * 1000
t = time.time()
for s_ in sample:
    md_doc = nlp(s_)
    X_ = md.build_matrix(vecs, [s_], [md.tag_sequence(md_doc)], [md.dense_features(0, len(md_doc))])
    md.score_of(model, X_)
ml_ms = (time.time() - t) / len(sample) * 1000
results["latency_ms_per_sentence"] = {"rule_checker": round(rules_ms, 1), "ml_scoring_extra": round(ml_ms, 1)}
log(f"latency: rule checker {rules_ms:.1f} ms | ML scoring {ml_ms:.1f} ms per sentence")

# --- which words / POS patterns push a sentence toward "error"? ----------------
names = []
for g in ("word", "char", "pos"):
    names += [f"{g}: {n}" for n in vecs[g].get_feature_names_out()]
names += [f"dense: {n}" for n in md.DENSE_NAMES]
interp = {}
if hasattr(model, "coef_"):
    coef = model.coef_.ravel()
    order = np.argsort(coef)
    pick = lambda prefix, idxs: [(names[i][len(prefix) + 2:], round(float(coef[i]), 3))
                                 for i in idxs if names[i].startswith(prefix + ":")][:12]
    interp["words_pointing_to_error"] = pick("word", order[::-1])
    interp["words_pointing_to_correct"] = pick("word", order)
    interp["pos_patterns_pointing_to_error"] = pick("pos", order[::-1])
    interp["dense_weights"] = {n: round(float(coef[names.index(f"dense: {n}")]), 3) for n in md.DENSE_NAMES}
results["interpretation"] = interp

# ================================================================= save model
artifact = {
    "vectorizers": vecs, "model": model, "threshold": best_thr, "feature_groups": all_groups,
    "meta": {"family": best["family"], "C": best["C"], "synthetic_per_sentence": best["n_syn"],
             "sklearn": sklearn.__version__, "trained_on": "JFLEG dev split + synthetic errors"},
}
joblib.dump(artifact, os.path.join(OUT_DIR, "error_detector.joblib"), compress=3)

hold_groups = sorted(set(int(groups[i]) for i in hold_idx))
with open(os.path.join(OUT_DIR, "split.json"), "w", encoding="utf-8") as f:
    json.dump({
        "note": "Holdout sentences were never used for training, tuning or threshold choice.",
        "holdout_erroneous": [texts[i] for i in hold_idx if y[i] == 1],
        "holdout_correct": [texts[i] for i in hold_idx if y[i] == 0],
    }, f, indent=1)
with open(os.path.join(OUT_DIR, "metrics.json"), "w", encoding="utf-8") as f:
    json.dump(results, f, indent=1, default=float)

# ===================================================================== charts
try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    TEAL, GREY, AMBER = "#287F80", "#9AA9AB", "#D9A441"

    # 1 - algorithm comparison
    fams = list(MODELS)
    f0 = [exp1[f"{n} | synthetic x0"]["f1"] for n in fams]
    f3 = [exp1[f"{n} | synthetic x3"]["f1"] for n in fams]
    x = np.arange(len(fams)); w = 0.38
    fig, ax = plt.subplots(figsize=(8, 4.2))
    ax.bar(x - w / 2, f0, w, label="real data only", color=GREY)
    ax.bar(x + w / 2, f3, w, label="+ synthetic errors", color=TEAL)
    ax.axhline(results["baseline_rules_dev_cv"]["f1"], color=AMBER, ls="--", label="rule-based checker (the app)")
    ax.set_xticks(x); ax.set_xticklabels([n.replace(" ", "\n", 1) for n in fams])
    ax.set_ylabel("F1-score (5-fold grouped CV)"); ax.set_ylim(0, 1)
    ax.set_title("Algorithm comparison"); ax.legend(frameon=False)
    for s in ("top", "right"): ax.spines[s].set_visible(False)
    fig.tight_layout(); fig.savefig(os.path.join(OUT_DIR, "1_algorithm_comparison.png"), dpi=160); plt.close(fig)

    # 2 - ROC and PR on holdout
    fig, axs = plt.subplots(1, 2, figsize=(9, 4))
    fpr, tpr, _ = roc_curve(hold_y, hold_scores)
    axs[0].plot(fpr, tpr, color=TEAL, label=f"ML model (AUC {auc(fpr, tpr):.2f})")
    r = final["rule-based checker (the app)"]
    axs[0].scatter([r["fp"] / max(r["fp"] + r["tn"], 1)], [r["recall"]], color=AMBER, zorder=3, label="rule-based checker (the app)")
    axs[0].plot([0, 1], [0, 1], ls=":", color=GREY); axs[0].set_xlabel("False-positive rate"); axs[0].set_ylabel("True-positive rate")
    axs[0].set_title("ROC curve (holdout)"); axs[0].legend(frameon=False, loc="lower right")
    pr, rc, _ = precision_recall_curve(hold_y, hold_scores)
    axs[1].plot(rc, pr, color=TEAL, label="ML model")
    axs[1].scatter([r["recall"]], [r["precision"]], color=AMBER, zorder=3, label="rule-based checker (the app)")
    axs[1].set_xlabel("Recall"); axs[1].set_ylabel("Precision"); axs[1].set_title("Precision-Recall (holdout)")
    axs[1].legend(frameon=False)
    for a in axs:
        for s in ("top", "right"): a.spines[s].set_visible(False)
    fig.tight_layout(); fig.savefig(os.path.join(OUT_DIR, "2_roc_pr_holdout.png"), dpi=160); plt.close(fig)

    # 3 - confusion matrices (holdout): old vs new
    fig, axs = plt.subplots(1, 2, figsize=(8, 3.6))
    for a, key, title in ((axs[0], "rule-based checker (the app)", "Rule-based checker (the app)"),
                          (axs[1], "hybrid rules+ML (experiment)", "Rules + ML (experiment)")):
        v = final[key]; cm = np.array([[v["tn"], v["fp"]], [v["fn"], v["tp"]]])
        a.imshow(cm, cmap="Greens")
        for (i, j), val in np.ndenumerate(cm):
            a.text(j, i, str(val), ha="center", va="center", fontsize=13)
        a.set_xticks([0, 1]); a.set_yticks([0, 1])
        a.set_xticklabels(["pred correct", "pred error"]); a.set_yticklabels(["is correct", "is error"])
        a.set_title(f"{title}\nF1={v['f1']:.2f}")
    fig.tight_layout(); fig.savefig(os.path.join(OUT_DIR, "3_confusion_matrices.png"), dpi=160); plt.close(fig)

    # 4 - ablation
    labels = list(exp4); vals = [exp4[k]["f1"] for k in labels]
    fig, ax = plt.subplots(figsize=(7.5, 3.6))
    ax.barh(labels[::-1], vals[::-1], color=TEAL); ax.set_xlim(0, 1); ax.set_xlabel("F1 (5-fold grouped CV)")
    ax.set_title("Feature ablation")
    for s in ("top", "right"): ax.spines[s].set_visible(False)
    fig.tight_layout(); fig.savefig(os.path.join(OUT_DIR, "4_feature_ablation.png"), dpi=160); plt.close(fig)

    # 5 - threshold curve
    th = [r_["threshold"] for r_ in thr_rows]
    fig, ax = plt.subplots(figsize=(7, 3.8))
    for key, col in (("precision", TEAL), ("recall", AMBER), ("f1", "#333333")):
        ax.plot(th, [r_[key] for r_ in thr_rows], label=key, color=col)
    ax.axvline(best_thr, ls=":", color=GREY); ax.set_xlabel("Decision threshold"); ax.set_ylim(0, 1)
    ax.set_title("Threshold tuning (rules + ML, dev out-of-fold)"); ax.legend(frameon=False)
    for s in ("top", "right"): ax.spines[s].set_visible(False)
    fig.tight_layout(); fig.savefig(os.path.join(OUT_DIR, "5_threshold_tuning.png"), dpi=160); plt.close(fig)
    log("charts saved")
except Exception as exc:                       # charts are optional
    log("could not draw charts:", exc)

log("DONE. Model + metrics saved in models/")
