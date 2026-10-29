"""
NLP engine: uses spaCy to analyze sentence structure and flag grammar issues.

This is the "non-trivial AI" part of the project - it's not just calling an
LLM, it's inspecting part-of-speech tags and dependency relations ourselves.

Checks implemented (each returns human-readable strings, same format as before):
    * spelling            - dictionary check + smarter correction ranking,
                            missing-apostrophe contractions (dont -> don't),
                            wrong irregular past tense (goed -> went)
    * subject-verb        - he/she/it + base verb, they/we + is/was, "I has",
                            plural noun + is, singular noun + are, noun + base verb
    * capitalization      - sentence start, lowercase "i"
    * double negative
    * word confusion      - their/they're, your/you're, its/it's, then/than
    * plural after number - "2 subject" -> "2 subjects"
    * a / an

Install requirement:
    pip install spacy pyspellchecker
    python -m spacy download en_core_web_sm
"""

import spacy
from spellchecker import SpellChecker

# Load once at import time (loading per-call is slow)
nlp = spacy.load("en_core_web_sm")
spell = SpellChecker()

# Simple irregular verb "be" agreement rules for demo purposes
SINGULAR_PRONOUNS = {"he", "she", "it"}
PLURAL_PRONOUNS = {"they", "we", "you", "i"}

# Contractions written without the apostrophe -> correct form
CONTRACTION_FIX = {
    "im": "I'm", "ive": "I've", "youre": "you're", "theyre": "they're",
    "dont": "don't", "doesnt": "doesn't", "didnt": "didn't", "cant": "can't",
    "wont": "won't", "isnt": "isn't", "arent": "aren't", "wasnt": "wasn't",
    "werent": "weren't", "havent": "haven't", "hasnt": "hasn't",
    "couldnt": "couldn't", "shouldnt": "shouldn't", "wouldnt": "wouldn't",
    "thats": "that's", "whats": "what's", "alot": "a lot",
}

# Learners often add "-ed" to irregular verbs
IRREGULAR_WRONG = {
    "goed": "went", "eated": "ate", "buyed": "bought", "runned": "ran",
    "teached": "taught", "thinked": "thought", "writed": "wrote",
    "speaked": "spoke", "maked": "made", "taked": "took", "comed": "came",
    "gived": "gave", "falled": "fell", "drinked": "drank", "knowed": "knew",
    "bringed": "brought", "catched": "caught", "feeled": "felt",
    "finded": "found", "getted": "got", "sleeped": "slept", "standed": "stood",
    "telled": "told", "sended": "sent", "builded": "built", "losed": "lost",
    "sayed": "said", "haved": "had", "doed": "did",
}

# Collective / uncountable nouns that can take either verb form
COLLECTIVE_NOUNS = {"team", "family", "staff", "police", "data", "government", "group",
                    "committee", "class", "audience", "couple", "crew", "media",
                    "public", "majority", "minority", "number", "variety", "series", "species",
                    "generation", "youth", "fish", "sheep", "deer", "population", "community",
                    "society", "company", "board", "jury", "orchestra", "army", "staff"}
UNIT_NOUNS = {"percent", "pm", "am", "%", "o'clock", "times", "dollar"}
IRREGULAR_PLURAL_NOUNS = {"child", "man", "woman", "person", "foot", "tooth", "mouse",
                          "sheep", "fish", "deer", "people", "series", "species"}
SPELLED_NUMBERS = {"two", "three", "four", "five", "six", "seven", "eight", "nine",
                   "ten", "twenty", "thirty", "hundred", "thousand", "million"}


def check_grammar_doc(doc, sentence: str) -> list[str]:
    """
    Rule-based checks on an already-parsed sentence (spaCy dependency parse
    + POS tags + dictionary spell check). Returns human-readable issue
    descriptions (empty list = nothing found).
    """
    issues = []

    issues.extend(_check_spelling(doc))
    issues.extend(_check_subject_verb_agreement(doc))
    issues.extend(_check_missing_capitalization(sentence))
    issues.extend(_check_double_negative(doc))
    issues.extend(_check_word_confusion(doc))
    issues.extend(_check_number_plural(doc))
    issues.extend(_check_articles(doc))
    issues.extend(_check_lowercase_i(doc))

    # remove exact duplicates, keep order
    return list(dict.fromkeys(issues))


def check_grammar_rules(sentence: str) -> list[str]:
    """Same as check_grammar (kept as a clearly-named alias for the evaluators)."""
    return check_grammar_doc(nlp(sentence), sentence)


def check_grammar(sentence: str) -> list[str]:
    """
    Runs the full set of rule-based checks over the sentence.
    Returns a list of human-readable issue descriptions (empty list =
    no issues found).
    """
    return check_grammar_doc(nlp(sentence), sentence)


# --------------------------------------------------------------------------
# spelling
# --------------------------------------------------------------------------
def _is_subsequence(small: str, big: str) -> bool:
    it = iter(big)
    return all(ch in it for ch in small)


def _typo_like(word: str, c: str) -> bool:
    return _is_subsequence(word, c) or _is_subsequence(c, word) or sorted(word) == sorted(c)


def _best_correction(word: str):
    """
    pyspellchecker ranks candidates by word frequency alone, so 'bok' becomes
    'boy'. Typing mistakes are usually a missing / extra / swapped letter, so
    prefer those candidates first, then same first letter, then frequency.
    """
    candidates = spell.candidates(word)
    if not candidates:
        return None

    def key(c: str):
        # a word ending in 'd' that is missing its 'e' ("enterd") is most likely a past tense: -> "entered"
        past_tense_fix = word.endswith("d") and not word.endswith("ed") and c.endswith("ed")
        return (not _typo_like(word, c), not past_tense_fix, c[0] != word[0], -spell.word_usage_frequency(c))

    return min(candidates, key=key)


def _check_spelling(doc) -> list[str]:
    """
    Checks each alphabetic word against a dictionary using pyspellchecker.
    Skips punctuation, numbers, and proper nouns (names/places), since
    those often aren't in the dictionary but aren't spelling mistakes.
    """
    issues = []
    for token in doc:
        if not token.is_alpha:
            continue

        word = token.text
        low = word.lower()

        # "do" + "nt" : spaCy splits 'dont' into two tokens
        if low == "nt" and token.i > 0:
            prev = doc[token.i - 1]
            if prev.lower_ == "do" and any(c.lower_ in SINGULAR_PRONOUNS and c.dep_ == "nsubj"
                                           for c in prev.head.children):
                fix = "doesn't"
            elif prev.lower_ == "ca":
                fix = "can't"
            elif prev.lower_ == "wo":
                fix = "won't"
            else:
                fix = prev.text + "n't"
            issues.append(f"Possible spelling mistake: '{prev.text}{word}' -> try '{fix}'")
            continue

        if low in CONTRACTION_FIX:
            issues.append(f"Possible spelling mistake: '{word}' -> try '{CONTRACTION_FIX[low]}'")
            continue

        if low in IRREGULAR_WRONG:
            issues.append(f"Possible spelling mistake: '{word}' -> try '{IRREGULAR_WRONG[low]}'")
            continue

        # Names and acronyms are not in the dictionary but are not mistakes:
        # skip ALL-CAPS words (TV, USA) and capitalised unknown words (Omama,
        # Zainab). The only capitalised word we still flag is one that is an
        # obvious letter swap of a very common word with the same first
        # letter ("Freind" -> "friend").
        if len(word) > 1 and word.isupper():
            continue

        if low not in spell:
            suggestion = _best_correction(low)
            if not suggestion or suggestion == low:
                continue
            if word[0].isupper():
                swapped = sorted(low) == sorted(suggestion) and low[0] == suggestion[0]
                if not (swapped and spell.word_usage_frequency(suggestion) >= 2e-5):
                    continue
            issues.append(f"Possible spelling mistake: '{word}' -> try '{suggestion}'")
    return issues


# --------------------------------------------------------------------------
# subject-verb agreement
# --------------------------------------------------------------------------
def _pluralize(lemma: str) -> str:
    """Naive English 3rd-person-singular suffix rule (covers common cases)."""
    if lemma.endswith(("o", "s", "sh", "ch", "x", "z")):
        return lemma + "es"
    if lemma.endswith("y") and lemma[-2:-1] not in "aeiou":
        return lemma[:-1] + "ies"
    return lemma + "s"


def _check_subject_verb_agreement(doc) -> list[str]:
    issues = []
    irregular_singular = {"have": "has", "be": "is", "do": "does"}
    plural_to_singular_verb = {"is": "are", "was": "were", "has": "have", "does": "do"}
    singular_to_plural_verb = {"are": "is", "were": "was"}
    i_fix = {"has": "have", "is": "am", "are": "am", "does": "do"}

    for token in doc:
        if token.dep_ == "nsubj" and token.head.pos_ in ("VERB", "AUX"):
            subject = token.text.lower()
            verb = token.head
            vlow = verb.lower_
            if verb.is_alpha and vlow not in spell:
                continue  # misspelled verb ("enterd"): the spelling rule reports it; its tag is unreliable
            compound_subject = any(c.dep_ in ("conj", "cc") for c in token.children)
            existential = any(c.dep_ == "expl" for c in verb.children)

            if subject in SINGULAR_PRONOUNS and verb.tag_ == "VBP":
                fix = irregular_singular.get(verb.lemma_, _pluralize(verb.lemma_))
                issues.append(
                    f"Possible subject-verb agreement error: '{subject} {verb.text}' "
                    f"-> try '{subject} {fix}'"
                )
            if subject in PLURAL_PRONOUNS and subject != "i" and verb.tag_ in ("VBZ", "VBD") and vlow in (
                "is", "was",
            ):
                # "be" is irregular: is -> are, was -> were
                fix = {"is": "are", "was": "were"}[vlow]
                issues.append(
                    f"Possible subject-verb agreement error: '{subject} {verb.text}' "
                    f"-> try '{subject} {fix}'"
                )
            if subject == "i" and vlow in i_fix:
                issues.append(
                    f"Possible subject-verb agreement error: '{subject} {verb.text}' "
                    f"-> try '{subject} {i_fix[vlow]}'"
                )
            # noun subjects: "The students is", "The boy are", "The teacher give"
            has_number = any(c.dep_ == "nummod" for c in token.children)
            has_aux = any(c.dep_ in ("aux", "auxpass") for c in verb.children)
            close_to_verb = 0 < verb.i - token.i <= 2
            if token.pos_ == "NOUN" and not compound_subject and not existential \
                    and not has_number and close_to_verb \
                    and token.lower_ not in COLLECTIVE_NOUNS:
                if token.tag_ == "NNS" and vlow in plural_to_singular_verb:
                    issues.append(
                        f"Possible subject-verb agreement error: '{token.text} {verb.text}' "
                        f"-> try '{token.text} {plural_to_singular_verb[vlow]}'"
                    )
                elif token.tag_ == "NN" and vlow in singular_to_plural_verb:
                    issues.append(
                        f"Possible subject-verb agreement error: '{token.text} {verb.text}' "
                        f"-> try '{token.text} {singular_to_plural_verb[vlow]}'"
                    )
                elif token.tag_ == "NN" and (verb.tag_ == "VBP" or (
                        verb.tag_ == "VB" and verb.dep_ == "ROOT" and not has_aux)):
                    fix = irregular_singular.get(verb.lemma_, _pluralize(verb.lemma_))
                    issues.append(
                        f"Possible subject-verb agreement error: '{token.text} {verb.text}' "
                        f"-> try '{token.text} {fix}'"
                    )
    return issues


# --------------------------------------------------------------------------
# capitalization / negation
# --------------------------------------------------------------------------
def _check_missing_capitalization(sentence: str) -> list[str]:
    issues = []
    stripped = sentence.strip()
    if stripped and stripped[0].islower():
        issues.append("Sentence should start with a capital letter.")
    return issues


def _check_lowercase_i(doc) -> list[str]:
    for token in doc:
        if token.text == "i" and token.i > 0 and token.tag_ == "PRP":
            return ["Possible capitalization mistake: 'i' -> try 'I'"]
    return []


def _check_double_negative(doc) -> list[str]:
    negations = [t for t in doc if t.dep_ == "neg" or t.lower_ in ("no", "never", "nothing")]
    if len(negations) >= 2:
        return ["Possible double negative detected — English usually uses only one negative word."]
    return []


# --------------------------------------------------------------------------
# commonly confused words
# --------------------------------------------------------------------------
def _is_noun_tag(tag: str) -> bool:
    return tag.startswith("NN")


def _check_word_confusion(doc) -> list[str]:
    issues = []
    n = len(doc)
    adjectives_after_youre = {"welcome", "right", "wrong", "late", "ready", "sure", "not",
                              "going", "being", "very", "so", "too", "always", "never"}
    for i, t in enumerate(doc):
        low = t.lower_
        nxt = doc[i + 1] if i + 1 < n else None
        nxt2 = doc[i + 2] if i + 2 < n else None
        prev = doc[i - 1] if i > 0 else None

        # words that follow a verb-like word with no noun after it
        def verb_like_then_no_noun() -> bool:
            return (nxt is not None and nxt.tag_ == "VBG"
                    and (nxt2 is None or nxt2.tag_ in ("IN", "TO", "RB", ".", ",")))

        if low == "their" and verb_like_then_no_noun():
            issues.append("Possible word-choice mistake: 'their' -> try 'they're'")
        elif low == "your" and nxt is not None and (
                verb_like_then_no_noun()
                or (nxt.lower_ in adjectives_after_youre and not (nxt2 is not None and _is_noun_tag(nxt2.tag_)))):
            issues.append("Possible word-choice mistake: 'your' -> try 'you're'")
        elif low == "its" and nxt is not None and (
                nxt.lower_ in ("a", "an", "the", "not", "been", "very", "also")
                or verb_like_then_no_noun()):
            issues.append("Possible word-choice mistake: 'its' -> try 'it's'")
        elif low == "then" and prev is not None and (
                prev.tag_ in ("JJR", "RBR") or prev.lower_ in ("more", "less", "rather", "other")):
            issues.append("Possible word-choice mistake: 'then' -> try 'than'")
    return issues


# --------------------------------------------------------------------------
# plural after a number, a / an
# --------------------------------------------------------------------------
def _check_number_plural(doc) -> list[str]:
    issues = []
    for t in doc:
        if t.tag_ != "CD":
            continue
        is_many = (t.text.isdigit() and int(t.text) > 1) or t.lower_ in SPELLED_NUMBERS
        if not is_many:
            continue
        if t.i > 0 and doc[t.i - 1].lower_ in ("class", "grade", "chapter", "page", "number",
                                               "no", "room", "level", "unit", "version",
                                               "section", "figure", "table", "route", "year"):
            continue
        for j in range(t.i + 1, min(t.i + 4, len(doc))):
            w = doc[j]
            if w.tag_ in ("JJ", "JJR", "JJS"):
                continue
            if (w.tag_ == "NN" and w.dep_ not in ("compound", "amod", "nmod")
                    and w.lower_ not in UNIT_NOUNS and w.lower_ not in IRREGULAR_PLURAL_NOUNS
                    and w.lower_ not in COLLECTIVE_NOUNS and w.is_alpha
                    and not (j + 1 < len(doc) and doc[j + 1].text == "-")):
                bad = doc[t.i:j + 1].text
                good = doc[t.i:j].text + " " + _pluralize(w.text)
                issues.append(f"Possible plural error: '{bad}' -> try '{good}'")
            break
    return issues


def _check_articles(doc) -> list[str]:
    issues = []
    for t in doc[:-1]:
        nxt = doc[t.i + 1]
        if not nxt.is_alpha:
            continue
        low = nxt.lower_
        if t.lower_ == "a" and low[0] in "aeio" and not low.startswith(("eu", "one", "once", "ewe")):
            issues.append(f"Possible article error: '{t.text} {nxt.text}' -> try 'an {nxt.text}'")
        elif (t.lower_ == "an" and low[0] in "bcdfgjklmnpqrstvwxyz"
              and not nxt.text.isupper() and not low.startswith(("hour", "honest", "honor", "honour", "heir"))):
            issues.append(f"Possible article error: '{t.text} {nxt.text}' -> try 'a {nxt.text}'")
    return issues


# --------------------------------------------------------------------------
# Stage 2: issue categories / levels (for badges) and vocabulary Pro Tips.
# These are separate helpers - check_grammar() output is NOT changed.
# --------------------------------------------------------------------------
# prefix of the issue text -> (category shown to the user, level, CEFR code)
# The CEFR code is only shown in a tooltip; learners see the plain level.
ISSUE_CATEGORIES = [
    ("Possible spelling",            ("Spelling",                "Basic",        "A1")),
    ("Possible subject-verb",        ("Subject-Verb Agreement",  "Elementary",   "A2")),
    ("Sentence should start",        ("Capitalization",          "Basic",        "A1")),
    ("Possible capitalization",      ("Capitalization",          "Basic",        "A1")),
    ("Possible double negative",     ("Double Negative",         "Intermediate", "B1")),
    ("Possible word-choice",         ("Word Choice",             "Elementary",   "A2")),
    ("Possible plural",              ("Plural Nouns",            "Basic",        "A1")),
    ("Possible article",             ("Articles",                "Elementary",   "A2")),
]
DEFAULT_CATEGORY = ("Grammar", "Elementary", "A2")


def categorize_issue(issue: str) -> tuple[str, str, str]:
    """Maps an issue string to (category, level, CEFR code)."""
    for prefix, info in ISSUE_CATEGORIES:
        if issue.startswith(prefix):
            return info
    return DEFAULT_CATEGORY


# Simple, overused words -> stronger alternatives (word: (POS, [alternatives])).
VOCAB_TIPS = {
    "good":      ("ADJ", ["excellent", "splendid", "wonderful"]),
    "bad":       ("ADJ", ["terrible", "awful", "poor"]),
    "happy":     ("ADJ", ["delighted", "joyful", "cheerful"]),
    "sad":       ("ADJ", ["unhappy", "gloomy", "heartbroken"]),
    "big":       ("ADJ", ["enormous", "huge", "massive"]),
    "small":     ("ADJ", ["tiny", "compact", "minor"]),
    "nice":      ("ADJ", ["pleasant", "delightful", "lovely"]),
    "pretty":    ("ADJ", ["beautiful", "attractive", "charming"]),
    "tired":     ("ADJ", ["exhausted", "weary", "drained"]),
    "angry":     ("ADJ", ["furious", "irritated", "outraged"]),
    "hard":      ("ADJ", ["challenging", "demanding", "difficult"]),
    "important": ("ADJ", ["essential", "crucial", "vital"]),
    "very":      ("ADV", ["extremely", "remarkably", "truly"]),
    "like":      ("VERB", ["enjoy", "adore", "appreciate"]),
    "said":      ("VERB", ["stated", "explained", "mentioned"]),
}


def vocabulary_tip(doc_or_sentence):
    """
    Returns one 'Pro Tip' string for the first simple word found, or None.
    Uses POS tags so e.g. the verb 'like' is tipped but 'like' as a
    preposition ('looks like') is not. Never affects correctness/accuracy.
    """
    doc = nlp(doc_or_sentence) if isinstance(doc_or_sentence, str) else doc_or_sentence
    for tok in doc:
        entry = VOCAB_TIPS.get(tok.lower_)
        if not entry:
            continue
        pos, alts = entry
        if tok.pos_ == pos or (pos == "ADJ" and tok.pos_ == "ADJ"):
            return f"Instead of '{tok.text}', try '{alts[0]}' or '{alts[1]}'."
    return None
