"""
Progress page (opened from the sidebar "Progress" item).

Shows, for the signed-in user only:
  * summary cards  - practised, correct, accuracy, quizzes passed
  * mistakes by category (bars, with the plain-language level)
  * accuracy over time (small line chart drawn as SVG)
  * recent mistakes to review
  * quiz history

Everything is read from data the app already saves (the progress file and the
quiz history file), so nothing here changes how checking or scoring works.
"""

import html

import streamlit as st

from nlp_engine import ISSUE_CATEGORIES, DEFAULT_CATEGORY

# Sections shown on the page. We build the page step by step: add the next section's name here
# ("category", "trend", "recent", "quizzes") when that step is ready.
ENABLED = ("cards", "category", "trend")

CSS = """
<style>
.pg-title { font-size: 22px; font-weight: 800; color: #1F2D2E; margin: 4px 0 2px; }
.pg-sub { color: #5F7172; font-size: 14px; margin-bottom: 14px; }
.pg-cards { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-bottom: 18px; }
.pg-card { background: #FFFFFF; border: 1px solid #D9E2E3; border-radius: 14px; padding: 14px 16px; }
.pg-card .n { font-size: 26px; font-weight: 800; color: #17696B; line-height: 1.1; }
.pg-card .c { font-size: 12px; font-weight: 600; letter-spacing: .05em; text-transform: uppercase; color: #5F7172; margin-top: 4px; }
.pg-panel { background: #FFFFFF; border: 1px solid #D9E2E3; border-radius: 14px; padding: 16px 18px; margin-bottom: 16px; }
.pg-panel h3 { margin: 0 0 12px; font-size: 16px; font-weight: 800; color: #1F2D2E; }
.pg-empty { color: #5F7172; font-size: 14px; }
.pg-bar-row { display: grid; grid-template-columns: 190px 1fr 36px; align-items: center; gap: 12px; margin: 9px 0; font-size: 14px; color: #1F2D2E; }
.pg-bar-track { background: #E8EEEF; border-radius: 999px; height: 12px; overflow: hidden; }
.pg-bar-fill { background: #008B8B; height: 100%; border-radius: 999px; }
.pg-lv { font-size: 11px; font-weight: 700; padding: 1px 8px; border-radius: 999px; margin-left: 6px; background: #E6F2F2; color: #17696B; border: 1px solid #BFDCDC; }
.pg-lv.basic { background: #E6F4EC; color: #2E7D5B; border-color: #BFE0CE; }
.pg-lv.intermediate { background: #FFF1D6; color: #9A6B12; border-color: #F0D9A6; }
.pg-num { text-align: right; font-weight: 700; color: #17696B; }
.pg-mist { padding: 9px 0; border-bottom: 1px dashed #D9E2E3; font-size: 14px; color: #1F2D2E; }
.pg-mist:last-child { border-bottom: 0; }
.pg-mist .s { font-weight: 600; margin-bottom: 3px; }
.pg-mist .bad { color: #C0392B; font-weight: 700; text-decoration: line-through; }
.pg-mist .good { color: #2E7D5B; font-weight: 700; }
.pg-mist .badge { display: inline-block; font-size: 11px; font-weight: 700; padding: 1px 8px; margin-right: 6px; border-radius: 999px;
  background: #E6F2F2; color: #17696B; border: 1px solid #BFDCDC; }
.pg-table { width: 100%; border-collapse: collapse; font-size: 14px; color: #1F2D2E; }
.pg-table th { text-align: left; font-size: 12px; text-transform: uppercase; letter-spacing: .05em; color: #5F7172; padding: 6px 8px; border-bottom: 1px solid #D9E2E3; }
.pg-table td { padding: 8px; border-bottom: 1px solid #EEF2F3; }
.pg-pass { color: #2E7D5B; font-weight: 700; } .pg-fail { color: #C0392B; font-weight: 700; }
@media (max-width: 900px) { .pg-cards { grid-template-columns: repeat(2, 1fr); } .pg-bar-row { grid-template-columns: 120px 1fr 30px; } }
</style>
"""


def _levels() -> dict:
    """category -> level name, taken from the same table the badges use."""
    levels = {cat: lvl for _, (cat, lvl, _cefr) in ISSUE_CATEGORIES}
    levels[DEFAULT_CATEGORY[0]] = DEFAULT_CATEGORY[1]
    return levels


def _trend_svg(records, limit: int = 40) -> str:
    """Cumulative accuracy after each check, as a small line chart."""
    points, correct = [], 0
    for i, r in enumerate(records, 1):
        correct += 1 if r["correct"] else 0
        points.append(correct / i * 100)
    points = points[-limit:]
    w, h, pad = 640, 170, 28
    step = (w - 2 * pad) / max(len(points) - 1, 1)
    xy = [(pad + i * step, h - pad - (v / 100) * (h - 2 * pad)) for i, v in enumerate(points)]
    grid = "".join(
        f'<line x1="{pad}" y1="{h - pad - g / 100 * (h - 2 * pad):.1f}" x2="{w - pad}" y2="{h - pad - g / 100 * (h - 2 * pad):.1f}" '
        f'stroke="#E3E8EB"/><text x="2" y="{h - pad - g / 100 * (h - 2 * pad) + 4:.1f}" font-size="11" fill="#5F7172">{g}%</text>'
        for g in (0, 50, 100))
    line = " ".join(f"{x:.1f},{y:.1f}" for x, y in xy)
    dots = "".join(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3" fill="#008B8B"/>' for x, y in xy[-1:])
    return (f'<svg viewBox="0 0 {w} {h}" style="width:100%;height:auto" xmlns="http://www.w3.org/2000/svg">'
            f'{grid}<polyline points="{line}" fill="none" stroke="#008B8B" stroke-width="2.5" stroke-linejoin="round"/>{dots}</svg>')


def render(tracker, history: list, fmt_issue) -> None:
    """Draw the page. `fmt_issue` turns an issue string into badge + strikethrough HTML (from app.py)."""
    st.markdown(CSS, unsafe_allow_html=True)
    records = tracker.records
    stats = tracker.get_stats()
    total, correct = stats["total"], stats["correct"]
    accuracy = (correct / total * 100) if total else 0
    passed = sum(1 for h in history if h.get("passed"))

    st.markdown('<div class="pg-title">Your Progress</div>'
                '<div class="pg-sub">A summary of your practice so far. Quiz results are shown separately and do not change your accuracy.</div>',
                unsafe_allow_html=True)
    st.markdown(
        '<div class="pg-cards">'
        f'<div class="pg-card"><div class="n">{total}</div><div class="c">Sentences practised</div></div>'
        f'<div class="pg-card"><div class="n">{correct}</div><div class="c">Correct</div></div>'
        f'<div class="pg-card"><div class="n">{accuracy:.0f}%</div><div class="c">Accuracy</div></div>'
        f'<div class="pg-card"><div class="n">{passed}/{len(history)}</div><div class="c">Quizzes passed</div></div>'
        '</div>', unsafe_allow_html=True)

    if "trend" in ENABLED:
        _trend_section(records)
    if "category" in ENABLED:
        _category_section(tracker)
    if "recent" in ENABLED:
        _recent_section(records, fmt_issue)
    if "quizzes" in ENABLED:
        _quiz_section(history)


def _category_section(tracker) -> None:
    breakdown = tracker.get_category_breakdown()
    if breakdown:
        top = max(breakdown.values())
        lv = _levels()
        rows = "".join(
            f'<div class="pg-bar-row"><div>{html.escape(cat)}<span class="pg-lv {lv.get(cat, "elementary").lower()}">{lv.get(cat, "Elementary")}</span></div>'
            f'<div class="pg-bar-track"><div class="pg-bar-fill" style="width:{n / top * 100:.0f}%"></div></div>'
            f'<div class="pg-num">{n}</div></div>' for cat, n in breakdown.items())
    else:
        rows = '<div class="pg-empty">No mistakes yet. Keep practising!</div>'
    note = '<div class="pg-empty" style="margin-top:8px;font-size:12px">Capital-letter slips are not counted here.</div>'
    st.markdown(f'<div class="pg-panel"><h3>Mistakes by category</h3>{rows}{note}</div>', unsafe_allow_html=True)



def _trend_section(records) -> None:
    if len(records) >= 2:
        body = _trend_svg(records)
    else:
        body = '<div class="pg-empty">Practise at least 2 sentences to see your accuracy trend.</div>'
    cap = '<div class="pg-empty" style="margin-top:6px;font-size:12px">Accuracy after each sentence you checked (last 40 shown). A rising line means you are improving.</div>' if len(records) >= 2 else ''
    st.markdown(f'<div class="pg-panel"><h3>Accuracy over time</h3>{body}{cap}</div>', unsafe_allow_html=True)



def _recent_section(records, fmt_issue) -> None:
    wrong = [r for r in records if not r["correct"]][-6:][::-1]
    if wrong:
        items = "".join(
            f'<div class="pg-mist"><div class="s">{html.escape(r["sentence"])}</div>'
            + "".join(f"<div>{fmt_issue(i)}</div>" for i in r["issues"]) + "</div>" for r in wrong)
    else:
        items = '<div class="pg-empty">Nothing to review yet.</div>'
    st.markdown(f'<div class="pg-panel"><h3>Recent mistakes to review</h3>{items}</div>', unsafe_allow_html=True)



def _quiz_section(history) -> None:
    if history:
        trs = "".join(
            f'<tr><td>{html.escape(h.get("when", "")[:16].replace("T", " "))}</td><td>{html.escape(h["scenario"])}</td>'
            f'<td>{html.escape(h["topic"])}</td><td class="{"pg-pass" if h["passed"] else "pg-fail"}">{"Passed" if h["passed"] else "Not passed"}</td>'
            f'<td>{h["attempts"]}/3</td></tr>' for h in history[-8:][::-1])
        table = ('<table class="pg-table"><tr><th>When</th><th>Scenario</th><th>Topic</th><th>Result</th><th>Attempts</th></tr>'
                 + trs + "</table>")
    else:
        table = '<div class="pg-empty">You have not taken a quiz yet. Use "Start quiz" in the sidebar.</div>'
    st.markdown(f'<div class="pg-panel"><h3>Quiz history</h3>{table}</div>', unsafe_allow_html=True)
