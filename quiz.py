"""
Scenario quiz (pop-up) for the Language Agent.

How it works
------------
* 6 fixed real-life scenarios (cafe, airport, hospital, hotel, office, bank);
  each has a fixed illustration, 5 fill-in-the-blank lines and a word bank
  that mixes correct and incorrect choices.
* A quiz is picked at random from the 6 (shuffled; the same one is never
  shown twice in a row).
* 2 minutes per attempt, 3 attempts. All blanks must be right to pass.
* Pass  -> congratulations + party-popper animation.
* 3 fails -> the correct answers are shown and a "Practise this topic"
  card appears on the Practice page.
* The quiz result is NOT added to the Practiced / Correct / Accuracy numbers.

The quiz opens inside Streamlit's st.dialog pop-up. app.py only needs to call
start_quiz(), nudge_due(), render_practice_card() and the small helpers below.
"""

import html
import json
import os
import random
import time
from datetime import datetime

import streamlit as st
import streamlit.components.v1 as components

from quiz_scenes import SCENES

def _stretch(fn) -> dict:
    """width="stretch" on new Streamlit (use_container_width is deprecated); old versions keep the old flag."""
    import inspect
    try:
        return {"width": "stretch"} if "width" in inspect.signature(fn).parameters else {"use_container_width": True}
    except (TypeError, ValueError):
        return {"use_container_width": True}


STRETCH = _stretch(st.button)
STRETCH_FORM = _stretch(st.form_submit_button)

QUIZ_SECONDS = 120   # fixed 2 minutes for every attempt
MAX_ATTEMPTS = 3
NUDGE_EVERY = 3      # offer the quiz every 3rd mistake in one category

# ---------------------------------------------------------------- content
SCENARIOS = [
    {
        "key": "cafe", "title": "At the Café", "topic": "Articles (a / an / the)",
        "intro": 'You stop at a café on your way to work. Fill in the blanks.',
        "lines": [("", 'On my way to work, I stopped at ___ small café near the station. I ordered ___ espresso and ___ blueberry muffin. While I waited, I noticed ___ umbrella that someone had forgotten, so I handed it to ___ barista who had served me.')],
        "answers": ["a", "an", "a", "an", "the"],
        "bank": ["a", "an", "the", "some", "any", "two"],
        "rule": "Use 'a' before a consonant sound and 'an' before a vowel sound. Use 'the' for something specific that both people know.",
        "examples": [("a apple", "an apple"), ("an book", "a book"), ("I saw a umbrella", "I saw an umbrella")],
    },
    {
        "key": "airport", "title": "At the Airport", "topic": "Subject-verb agreement",
        "intro": 'You are travelling for a business trip. Fill in the blanks.',
        "lines": [("", 'My flight to Dubai ___ at 9:40 a.m., so I arrived at the airport early. All passengers ___ to show their passports at the desk. My luggage ___ already been checked in, and there ___ only two security lines open. My sister ___ not like waiting, so we went straight to the gate.')],
        "answers": ["departs", "need", "has", "are", "does"],
        "bank": ["departs", "depart", "need", "needs", "has", "have", "are", "is", "does", "do"],
        "rule": "A singular subject (he, she, it, my luggage) takes the singular verb (goes, has, does, is). A plural subject (they, passengers) takes the plural verb (go, have, do, are).",
        "examples": [("He go to work", "He goes to work"), ("The students is late", "The students are late"), ("She do not know", "She does not know")],
    },
    {
        "key": "hospital", "title": "At the Hospital", "topic": "Spelling",
        "intro": 'You are visiting a doctor. Choose the correctly spelled word for each blank.',
        "lines": [("", 'I woke up with a high ___ and a terrible headache, so I booked an ___ with Dr. Rahman. At the clinic, the nurse asked if I was ___ to any medicine. I showed my ___ card at reception. After the examination, the doctor gave me a ___ for antibiotics.')],
        "answers": ["temperature", "appointment", "allergic", "insurance", "prescription"],
        "bank": ["appointment", "apointment", "temperature", "temprature", "allergic", "alergic",
                 "insurance", "insurence", "prescription", "perscription"],
        "rule": "Many English words are spelled differently from how they sound. Read the word slowly, break it into syllables (ap-point-ment) and check double letters.",
        "examples": [("apointment", "appointment"), ("temprature", "temperature"), ("perscription", "prescription")],
    },
    {
        "key": "hotel", "title": "At the Hotel", "topic": "Word choice (their / there, your / you're, its / it's, than / then)",
        "intro": 'You are checking in at a hotel. Choose the right word for each blank.',
        "lines": [("", 'We arrived at the hotel late on Friday. I told the receptionist that ___ was a reservation under my name. My colleagues were arriving later, and ___ rooms were booked too. The clerk smiled and said, “Sir, ___ room is on the fifth floor.” I asked about the pool and heard ___ closed for repairs, but the room was much bigger ___ I expected.')],
        "answers": ["there", "their", "your", "it's", "than"],
        "bank": ["there", "their", "they're", "your", "you're", "its", "it's", "than", "then"],
        "rule": "their = belongs to them; there = a place or 'there is'; they're = they are. your = belongs to you; you're = you are. its = belongs to it; it's = it is. than = comparison; then = next in time.",
        "examples": [("Their going home", "They're going home"), ("Your welcome", "You're welcome"), ("Its raining", "It's raining")],
    },
    {
        "key": "office", "title": "At the Office", "topic": "Plural nouns and capital letters",
        "intro": 'You are preparing for a team meeting. Fill in the blanks.',
        "lines": [("", 'Our team meeting is on ___ at 10 a.m. Please send me the three ___ before then. We also have two new ___ joining us from ___, so I will welcome them. After lunch, ___ will present the budget to the manager.')],
        "answers": ["Monday", "reports", "employees", "Lahore", "I"],
        "bank": ["reports", "report", "employees", "employee", "Monday", "monday", "Lahore", "lahore", "I", "i"],
        "rule": "After a number above one, the noun is plural (two employees). Days, months, names of places and the word 'I' always start with a capital letter.",
        "examples": [("two employee", "two employees"), ("on monday", "on Monday"), ("i will present", "I will present")],
    },
    {
        "key": "bank", "title": "At the Bank", "topic": "Double negatives",
        "intro": 'You are sorting out a problem with your bank card. Choose the word that avoids a double negative.',
        "lines": [("", "I went to the bank yesterday, but I didn't have ___ cash with me. The manager didn't tell ___ about the problem with my card, and I haven't received ___ from the head office yet. There isn't ___ else to withdraw money near here. Luckily, I have ___ missed a payment, so my record is clean.")],
        "answers": ["any", "anyone", "anything", "anywhere", "never"],
        "bank": ["any", "no", "anyone", "no one", "anything", "nothing", "anywhere", "nowhere", "ever", "never"],
        "rule": "English uses only one negative word in a clause. After 'don't / didn't / haven't / isn't' use any-words (any, anyone, anything, anywhere), not no-words.",
        "examples": [("I don't have no money", "I don't have any money"), ("She didn't say nothing", "She didn't say anything"), ("I haven't never been", "I have never been")],
    },
]

# --------------------------------------------------------------- nudge logic
def _is_error(issue: str) -> bool:
    """Same rule app.py uses for the red 'Errors' card (suggestions don't count)."""
    return issue.startswith("Possible spelling") or issue.startswith("Possible subject-verb")


def _error_counts(records) -> dict:
    counts = {}
    for r in records:
        for issue in r["issues"]:
            if _is_error(issue):
                key = issue.split(":")[0]
                counts[key] = counts.get(key, 0) + 1
    return counts


def nudge_due(records) -> bool:
    """True when the newest check pushed an error category to 3, 6, 9 ... mistakes."""
    if not records:
        return False
    before, after = _error_counts(records[:-1]), _error_counts(records)
    return any(n // NUDGE_EVERY > before.get(k, 0) // NUDGE_EVERY for k, n in after.items())


# -------------------------------------------------------------------- state
def _next_scenario() -> int:
    pool = st.session_state.get("quiz_pool", [])
    last = st.session_state.get("quiz_last")
    if not pool:
        pool = list(range(len(SCENARIOS)))
        random.shuffle(pool)
        if len(pool) > 1 and pool[0] == last:          # never repeat back-to-back
            pool.append(pool.pop(0))
    idx = pool.pop(0)
    st.session_state.quiz_pool = pool
    st.session_state.quiz_last = idx
    return idx


def start_quiz():
    """Pick the next scenario, reset the attempt state and open the pop-up."""
    idx = _next_scenario()
    sc = SCENARIOS[idx]
    bank = sc["bank"][:]
    random.shuffle(bank)
    st.session_state.quiz_counter = st.session_state.get("quiz_counter", 0) + 1
    st.session_state.quiz = {
        "id": st.session_state.quiz_counter, "idx": idx, "attempt": 1,
        "deadline": time.time() + QUIZ_SECONDS, "status": "active",
        "locked": [], "wrong": [], "timed_out": False, "bank": bank,
        "fills": [None] * len(sc["answers"]),
    }
    try:
        dlg = st.dialog(sc["title"], width="large")
    except TypeError:                                   # older Streamlit: no width option
        dlg = st.dialog(sc["title"])
    dlg(_render_quiz)()


def reset_quiz_state():
    for k in ("quiz", "quiz_pool", "quiz_last", "practice_topic", "nudges", "nudge_dismissed", "page"):
        st.session_state.pop(k, None)


def _history_path() -> str:
    """Quiz history lives next to the user's progress file: <name>_quiz.json (progress schema untouched)."""
    base = st.session_state.agent.tracker.data_file
    return base.replace("_progress.json", "_quiz.json") if base.endswith("_progress.json") else base + ".quiz.json"


def load_history() -> list:
    try:
        with open(_history_path(), "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return []


def _save_result(q: dict, passed: bool):
    """Append one finished quiz (passed, or failed after 3 attempts) to the user's quiz history."""
    sc = SCENARIOS[q["idx"]]
    history = load_history()
    history.append({"when": datetime.now().isoformat(timespec="minutes"), "scenario": sc["title"],
                    "topic": sc["topic"], "passed": passed, "attempts": q["attempt"]})
    path = _history_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2)


def _submit():
    """Button callback: grade the attempt (runs before the dialog redraws)."""
    q = st.session_state.quiz
    sc = SCENARIOS[q["idx"]]
    answers = q["fills"]
    correct = [a == sc["answers"][i] for i, a in enumerate(answers)]
    timed_out = time.time() > q["deadline"] + 3          # 3 s grace for page lag
    q["timed_out"] = timed_out
    if all(correct) and not timed_out:
        q["status"] = "passed"
        _save_result(q, True)
        return
    q["locked"] = [] if timed_out else [i for i, c in enumerate(correct) if c]
    q["wrong"] = [i for i, c in enumerate(correct) if not c]
    if not timed_out:
        for i in q["wrong"]:
            q["fills"][i] = None                          # wrong blanks are emptied, correct ones stay locked
    if q["attempt"] >= MAX_ATTEMPTS:
        q["status"] = "failed"
        st.session_state.practice_topic = q["idx"]
        _save_result(q, False)
    else:
        q["attempt"] += 1
        q["deadline"] = time.time() + QUIZ_SECONDS


def _pick(word: str):
    """Chip callback: put the tapped word into the next empty blank."""
    q = st.session_state.quiz
    for i, v in enumerate(q["fills"]):
        if v is None and i not in q["locked"]:
            q["fills"][i] = word
            return


def _undo():
    q = st.session_state.quiz
    for i in range(len(q["fills"]) - 1, -1, -1):
        if q["fills"][i] is not None and i not in q["locked"]:
            q["fills"][i] = None
            return


def _clear():
    q = st.session_state.quiz
    q["fills"] = [v if i in q["locked"] else None for i, v in enumerate(q["fills"])]


# ------------------------------------------------------------------ styling
QUIZ_CSS = """
<style>
[role="dialog"] { background: #FFFFFF !important; color: #1F2D2E; }
[role="dialog"] h2, [role="dialog"] h2 * { color: #1F2D2E !important; }
[role="dialog"] button[aria-label="Close"], [role="dialog"] button[aria-label="Close"] svg { color: #1F2D2E !important; fill: #1F2D2E !important; }
[role="dialog"] button[data-testid="stBaseButton-secondary"] { background: #FFFFFF; color: #1F2D2E; border: 1px solid #D9E2E3; }
[role="dialog"] .st-key-qbank { display: flex !important; flex-flow: row wrap !important; gap: 10px !important; margin: 4px 0 12px; }
[role="dialog"] .st-key-qbank > div, [role="dialog"] .st-key-qbank [class*="st-key-qchip"] { width: auto !important; flex: 0 0 auto !important; min-width: 0 !important; }
[role="dialog"] [class*="st-key-qchip"] button { background: #172D35 !important; color: #FFFFFF !important; border: 0 !important; box-shadow: none !important;
    border-radius: 8px !important; min-height: 40px; padding: 0 20px !important; }
[role="dialog"] [class*="st-key-qchip"] button:hover { background: #008B8B !important; }
[role="dialog"] [class*="st-key-qchip"] button p { color: #FFFFFF !important; font-weight: 700 !important; font-size: 16px !important; }
[role="dialog"] button[data-testid="stBaseButton-secondary"], [role="dialog"] button[data-testid="stBaseButton-primary"] { min-height: 42px; }
[role="dialog"] [class*="st-key-qclose"], [role="dialog"] [class*="st-key-qprac"] { width: 100% !important; display: flex !important; justify-content: center !important; margin-top: 6px; }
[role="dialog"] [class*="st-key-qclose"] > div, [role="dialog"] [class*="st-key-qprac"] > div, [role="dialog"] [class*="st-key-qclose"] [data-testid="stButton"], [role="dialog"] [class*="st-key-qprac"] [data-testid="stButton"] { width: auto !important; margin: 0 auto !important; }
[role="dialog"] [class*="st-key-qclose"] button, [role="dialog"] [class*="st-key-qprac"] button { width: 180px !important; min-width: 180px !important; }
.qz-banner { max-width: 440px; aspect-ratio: 16 / 5; margin: 0 auto 12px; border-radius: 14px; overflow: hidden; }
.qz-intro { color: #5F7172; font-size: 14px; margin: 0 0 6px; }
.qz-bank { display: flex; flex-wrap: wrap; gap: 8px; margin: 6px 0 14px; }
.qz-chip { padding: 5px 13px; border-radius: 999px; background: #E3F4F3; color: #17696B; border: 1px solid #BFDCDC; font-weight: 600; font-size: 14px; }
.qz-label { font-size: 12px; font-weight: 700; letter-spacing: .06em; text-transform: uppercase; color: #5F7172; margin-top: 4px; }
.qz-para { font-size: 16px; line-height: 2.2; color: #0B7B7B; background: #FFFFFF; border: 1px solid #E3E8EB; border-radius: 12px; padding: 12px 16px; margin: 6px 0 10px; }
.qz-line { font-size: 15px; line-height: 1.7; color: #1F2D2E; padding-top: 6px; }
.qz-line b { color: #17696B; }
.qz-blank { display: inline-block; min-width: 84px; border-bottom: 2px solid #9FB6B8; text-align: center; font-weight: 700; color: #5F7172; padding: 0 6px; }
.qz-blank.filled { border-color: #0B7B7B; color: #0A4F50; background: #E3F4F3; border-radius: 6px 6px 0 0; }
.qz-blank.ok { border-color: #2E7D5B; color: #2E7D5B; background: #E8F5EE; border-radius: 6px 6px 0 0; }
.qz-blank.bad { border-color: #C0392B; background: #FDEDEB; border-radius: 6px 6px 0 0; }
.qz-blank.active { border-color: #F2B84B; background: #FFF6E0; }
.qz-ok { color: #2E7D5B; font-weight: 700; } .qz-bad { color: #C0392B; font-weight: 700; }
.qz-msg { padding: 9px 13px; border-radius: 10px; font-size: 14px; margin: 8px 0; }
.qz-msg.warn { background: #FFF6E0; border: 1px solid #F0DDA8; color: #7A5410; }
.qz-msg.fail { background: #FDEDEB; border: 1px solid #F3C6C1; color: #A12D20; }
.qz-win { text-align: center; padding: 34px 10px 10px; position: relative; overflow: hidden; }
.qz-win h2 { margin: 0 0 6px; color: #17696B; }
.qz-win p { color: #5F7172 !important; }
.qz-popper { font-size: 64px; display: inline-block; animation: qz-pop .9s ease-out both; }
@keyframes qz-pop { 0% { transform: scale(.2) rotate(-35deg); opacity: 0; } 55% { transform: scale(1.25) rotate(12deg); opacity: 1; } 100% { transform: scale(1) rotate(0); } }
.qz-conf { position: absolute; top: -12px; width: 9px; height: 14px; border-radius: 2px; opacity: 0; animation: qz-fall 2.6s ease-in infinite; }
@keyframes qz-fall { 0% { transform: translateY(0) rotate(0); opacity: 1; } 100% { transform: translateY(330px) rotate(540deg); opacity: 0; } }
.qz-answer { padding: 7px 0; border-bottom: 1px dashed #D9E2E3; font-size: 14px; color: #1F2D2E; }
.qz-answer b { color: #2E7D5B; }
.qz-para b { color: #0A4F50; }
</style>
"""


def _confetti() -> str:
    colors = ["#008B8B", "#F2B84B", "#E8735A", "#3E6FB0", "#2E7D5B", "#9B59B6"]
    rnd = random.Random(7)
    return "".join(
        f'<span class="qz-conf" style="left:{rnd.randint(2, 98)}%;background:{colors[i % len(colors)]};'
        f'animation-delay:{rnd.random() * 1.6:.2f}s;animation-duration:{2 + rnd.random() * 1.5:.2f}s"></span>'
        for i in range(36))


def _timer(seconds_left: float):
    """Countdown shown in the pop-up (JavaScript; the server re-checks the real time on submit)."""
    left = max(0, int(seconds_left))
    components.html(f"""
    <div id="t" style="font:700 15px Inter,Arial,sans-serif;color:#17696B;background:#E3F4F3;border:1px solid #BFDCDC;
      border-radius:999px;padding:6px 14px;display:inline-block">⏱ 2:00</div>
    <script>
      var end = Date.now() + {left} * 1000, el = document.getElementById('t');
      function tick() {{
        var s = Math.max(0, Math.round((end - Date.now()) / 1000));
        el.textContent = s > 0 ? '⏱ ' + Math.floor(s / 60) + ':' + String(s % 60).padStart(2, '0') : "⏱ Time's up";
        if (s <= 20) {{ el.style.color = '#C0392B'; el.style.background = '#FDEDEB'; el.style.borderColor = '#F3C6C1'; }}
      }}
      tick(); setInterval(tick, 500);
    </script>""", height=44)


# ------------------------------------------------------------------- dialog
def _render_quiz():
    q = st.session_state.quiz
    sc = SCENARIOS[q["idx"]]
    st.markdown(QUIZ_CSS, unsafe_allow_html=True)

    if q["status"] == "passed":
        st.markdown(f'<div class="qz-win">{_confetti()}<div class="qz-popper">🎉</div>'
                    '<h2>Congratulations!</h2><p>You completed the quiz. Great work!</p></div>',
                    unsafe_allow_html=True)
        if st.button("Close", type="primary", key=f"qclose{q['id']}"):
            st.rerun()
        return

    st.markdown(f'<div class="qz-banner">{SCENES[sc["key"]]()}</div>', unsafe_allow_html=True)

    if q["status"] == "failed":
        st.markdown(f'<div class="qz-msg fail">You have used all {MAX_ATTEMPTS} attempts. '
                    f'Here are the correct answers — then practise <b>{html.escape(sc["topic"])}</b>.</div>',
                    unsafe_allow_html=True)
        n = 0
        for who, text in sc["lines"]:
            shown = html.escape(text)
            while "___" in shown:
                shown = shown.replace("___", f"<b>{html.escape(sc['answers'][n])}</b>", 1)
                n += 1
            st.markdown(f'<div class="qz-answer">{shown}</div>', unsafe_allow_html=True)
        if st.button("Practise this topic", type="primary", key=f"qprac{q['id']}"):
            st.session_state.page = "Practice"   # the practise card is on the Practice page
            st.rerun()
        return

    # ---- active attempt
    n_blanks = len(sc["answers"])
    st.markdown(f'<div class="qz-intro">{html.escape(sc["intro"])}</div>', unsafe_allow_html=True)
    left = q["deadline"] - time.time()
    c1, c2, c3, c4, _c5 = st.columns([1.1, 0.8, 0.5, 0.5, 1.3])
    c1.markdown(f'<div class="qz-label" style="padding-top:12px">Attempt {q["attempt"]} of {MAX_ATTEMPTS}</div>', unsafe_allow_html=True)
    with c2:
        _timer(left)
    c3.button("↶ Undo", key=f"undo{q['id']}_{q['attempt']}", on_click=_undo, **STRETCH)
    c4.button("Clear", key=f"clear{q['id']}_{q['attempt']}", on_click=_clear, **STRETCH)

    st.markdown('<div class="qz-label">Word bank — tap a word to fill the next blank</div>', unsafe_allow_html=True)
    try:
        bank_box = st.container(key="qbank")     # holds the word boxes; CSS lays them out in a wrapping row
    except TypeError:                            # older Streamlit without container keys: boxes stack in a column
        bank_box = st.container()
    with bank_box:
        for j, w in enumerate(q["bank"]):
            st.button(w, key=f"qchip{q['id']}_{q['attempt']}_{j}", on_click=_pick, args=(w,))

    if q["attempt"] > 1:
        msg = "Time's up on the last attempt. Try again." if q["timed_out"] else \
              f"{len(q['wrong'])} answer(s) need fixing — correct ones are locked (green)."
        st.markdown(f'<div class="qz-msg warn">{msg}</div>', unsafe_allow_html=True)

    # the conversation as one paragraph, blanks inline
    next_empty = next((i for i, v in enumerate(q["fills"]) if v is None and i not in q["locked"]), None)
    n = 0
    parts = []
    for who, text in sc["lines"]:
        pieces = html.escape(text).split("___")
        out = pieces[0]
        for piece in pieces[1:]:
            val = q["fills"][n]
            if n in q["locked"]:
                cls, label = "ok", val
            elif val:
                cls, label = "filled", val
            elif n in q["wrong"] and q["attempt"] > 1:
                cls, label = "bad", str(n + 1)
            elif n == next_empty:
                cls, label = "active", str(n + 1)
            else:
                cls, label = "", str(n + 1)
            out += f'<span class="qz-blank {cls}">{html.escape(label)}</span>' + piece
            n += 1
        parts.append((f"<b>{who}:</b> " if who else "") + out)
    st.markdown('<div class="qz-para">' + "<br>".join(parts) + "</div>", unsafe_allow_html=True)

    _l, mid, _r = st.columns([1.2, 1, 1.2])
    mid.button("Submit answers", type="primary", **STRETCH, key=f"sub{q['id']}_{q['attempt']}",
               on_click=_submit, disabled=any(v is None for v in q["fills"]))


# ------------------------------------------------------- practice-topic card
def render_practice_card():
    """Shown on the Practice page after 3 failed attempts."""
    idx = st.session_state.get("practice_topic")
    if idx is None:
        return
    sc = SCENARIOS[idx]
    ex = "".join(f'<div style="margin:3px 0"><span style="color:#C0392B;text-decoration:line-through;font-weight:700">'
                 f'{html.escape(a)}</span> → <span style="color:#2E7D5B;font-weight:700">{html.escape(b)}</span></div>'
                 for a, b in sc["examples"])
    st.markdown(
        '<div style="background:#FFFFFF;border:1px solid #BFDCDC;border-left:5px solid #008B8B;border-radius:12px;'
        'padding:14px 18px;margin:4px 0 14px">'
        f'<div style="font-weight:800;color:#17696B;font-size:16px">📘 Practise this topic: {html.escape(sc["topic"])}</div>'
        f'<div style="color:#1F2D2E;font-size:14px;margin:6px 0 8px">{html.escape(sc["rule"])}</div>{ex}'
        '<div style="color:#5F7172;font-size:13px;margin-top:8px">Now write 2–3 sentences using this topic in the box below.</div></div>',
        unsafe_allow_html=True)
    if st.button("Got it", key="practice_got_it"):
        st.session_state.pop("practice_topic", None)
        st.rerun()
