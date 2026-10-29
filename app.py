"""
Streamlit interface for the Language Learning Agent.

UI/UX layer only - all grammar-checking / AI logic still lives in
agent.py, nlp_engine.py and progress_tracker.py, completely untouched.

Run with:
    streamlit run app.py
"""

# FILE OVERVIEW - Roman Urdu: Yeh Streamlit ka asli web app hai (screen, buttons, rang, chat). Yahan sirf shakal aur user se baat-cheet hai;
# grammar check agent.py aur nlp_engine.py mein hota hai. Is file ke hisse: (1) rang aur CSS, (2) login/sign-up pop-up, (3) sidebar (navigation, accuracy ring, stats,
# Top mistake, Quick Quiz, Log out), (4) Progress page ka rasta, (5) Practice page (greeting banner, chat, quiz ki dawat, sentence likhne ka form).
# Chalane ke liye: streamlit run app.py
import html
import re
from datetime import datetime
import streamlit as st
import streamlit.components.v1 as components
from agent import LanguageAgent
from nlp_engine import categorize_issue, vocabulary_tip
import quiz
import progress_page
import auth

# Browser tab title/icon, wide layout and an open sidebar. Must be the first Streamlit call.
# Roman Urdu: Browser tab ka naam/icon, chauri layout aur khula sidebar. Yeh sab se pehla Streamlit call hona zaroori hai.
st.set_page_config(
    page_title="Language Learning Agent",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ============================================================
# 🎨 COLOR PALETTE — change any value here to re-theme the whole app.
#    Nothing else in this file needs to change.
# ============================================================
# One colour table for the whole app: change a value here and every page changes.
# Roman Urdu: Poori app ke rang ek hi table mein hain: yahan ek rang badlen to saari app ka rang badal jata hai.
COLORS = {
    "background":     "#F1F5F6",  # light grey-white page background
    "card":           "#FFFFFF",  # white cards
    "card_hover":     "#EEF4F4",
    "primary":        "#008B8B",  # teal accent
    "primary_hover":  "#007377",
    "primary_soft":   "#E3F4F3",
    "ring":           "#287F80",  # accuracy ring colours (kept exactly as before)
    "ring_track":     "#D9E2E3",
    "sidebar":        "#172D35",  # dark navy-teal sidebar
    "sidebar_text":   "#E8F0F2",
    "sidebar_muted":  "#8DA5AC",
    "sidebar_card":   "rgba(255,255,255,.06)",
    "sidebar_border": "rgba(255,255,255,.09)",
    "nav_active":     "rgba(0,139,139,.26)",
    "nav_active_text":"#8FE6DF",
    "success":        "#2E7D5B",
    "success_bg":     "#E8F5EE",
    "success_border": "#BFE0CF",
    "suggestion":     "#9A6B12",
    "suggestion_bg":  "#FFF6E0",
    "suggestion_border": "#F0DDA8",
    "error":          "#C0392B",
    "error_bg":       "#FDEDEB",
    "error_border":   "#F3C6C1",
    "text":           "#1F2D2E",
    "text_muted":     "#5F7172",
    "border":         "#D9E2E3",
}

# ============================================================
# CSS — built from COLORS above using an f-string, so editing the
# dictionary is enough to change the whole theme.
# ============================================================
# Global CSS: fonts, sidebar, accuracy ring, cards, chat bubbles, buttons. It is an f-string, so {COLORS[...]} fills in the colours.
# Roman Urdu: Poori app ki CSS (shakal): font, sidebar, accuracy ring, cards, chat ke bubbles, buttons. f-string hai is liye {COLORS[...]} se rang khud bhar jate hain.
st.markdown(f"""
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
<style>
    :root {{ color-scheme: light; }}
    html, body, [class*="css"] {{ font-family: 'Inter', sans-serif; }}
    .stApp {{ background: {COLORS['background']}; }}

    /* Header stays but is recolored to match the page, so its sidebar
       toggle arrow keeps working while the bar itself disappears visually. */
    header[data-testid="stHeader"] {{
        background: {COLORS['background']} !important;
        box-shadow: none !important;
        height: 2.75rem;
    }}
    header[data-testid="stHeader"] svg {{ fill: {COLORS['text_muted']} !important; }}
    header[data-testid="stHeader"] button {{ color: {COLORS['text_muted']} !important; }}
    [data-testid="stToolbar"], #MainMenu, footer {{ visibility: hidden; }}
    /* Keep the "reopen sidebar" arrow visible (it lives inside the hidden toolbar). */
    [data-testid="stExpandSidebarButton"], [data-testid="stExpandSidebarButton"] *,
    [data-testid="stSidebarCollapsedControl"], [data-testid="stSidebarCollapsedControl"] * {{ visibility: visible !important; }}
    [data-testid="stExpandSidebarButton"], [data-testid="stExpandSidebarButton"] * {{ color: {COLORS['text']} !important; opacity: .85; }}

    .block-container {{ padding-top: 2.75rem; padding-bottom: 5rem; max-width: 960px; margin-left: auto; margin-right: auto; padding-left: 2rem; padding-right: 2rem; }}
    div[data-testid="stBottom"], div[data-testid="stBottom"] > div {{ background: {COLORS['background']}; }}

    /* ---------- Sidebar (dark navy-teal) ---------- */
    section[data-testid="stSidebar"] {{ background: {COLORS['sidebar']}; border-right: 0; }}
    /* fixed 25% / 75% split */
    section[data-testid="stSidebar"] {{ width: 25vw !important; min-width: 25vw !important; max-width: 25vw !important; }}
    section[data-testid="stSidebar"] > div {{ width: 100% !important; }}
    /* the fixed width above is wider than Streamlit's slide-out distance, so hide a collapsed sidebar fully */
    section[data-testid="stSidebar"][data-collapsed="true"] {{ display: none !important; }}
    @media (max-width: 900px) {{
        section[data-testid="stSidebar"] {{ width: 85vw !important; min-width: 85vw !important; max-width: 85vw !important; }}
    }}
    section[data-testid="stSidebar"] .block-container {{ padding: 2rem 1.25rem; }}
    [data-testid="stSidebarCollapseButton"] button, [data-testid="stSidebarCollapseButton"] span, [data-testid="stSidebarCollapseButton"] svg {{ color: {COLORS['sidebar_muted']} !important; fill: {COLORS['sidebar_muted']} !important; }}

    .brand {{ display: flex; align-items: center; gap: 10px; color: {COLORS['sidebar_text']}; font-size: 16px; font-weight: 700; margin-bottom: 1.4rem; }}
    .brand .logo {{ width: 40px; height: 40px; flex: none; border-radius: 12px; background: rgba(255,255,255,.12); padding: 4px; display: flex; align-items: center; justify-content: center; }}
    .brand .logo svg {{ width: 100%; height: 100%; display: block; }}
    .brand-text {{ display: flex; flex-direction: column; line-height: 1.25; }}
    .brand-text .bn {{ font-size: 16px; font-weight: 700; color: {COLORS['sidebar_text']}; }}
    .brand-text .bs {{ font-size: 11.5px; font-weight: 500; color: {COLORS['sidebar_muted']}; }}
    .nav {{ display: flex; flex-direction: column; gap: 4px; margin-bottom: 1.6rem; }}
    .nav-item {{ display: flex; align-items: center; gap: 11px; padding: 10px 12px; border-radius: 10px; color: {COLORS['sidebar_muted']}; font-size: 14px; font-weight: 500; }}
    section[data-testid="stSidebar"] .st-key-nav_practice button, section[data-testid="stSidebar"] .st-key-nav_progress button {{
        background: transparent !important; border: 0 !important; box-shadow: none !important; color: {COLORS['sidebar_muted']} !important;
        justify-content: flex-start !important; padding: 10px 12px !important; border-radius: 10px !important; min-height: 42px; font-weight: 500;
        display: flex; align-items: center; gap: 11px; }}
    section[data-testid="stSidebar"] .st-key-nav_practice button > div, section[data-testid="stSidebar"] .st-key-nav_progress button > div {{ justify-content: flex-start !important; }}
    section[data-testid="stSidebar"] .st-key-nav_practice button:hover, section[data-testid="stSidebar"] .st-key-nav_progress button:hover {{ background: rgba(255,255,255,.07) !important; color: {COLORS['sidebar_text']} !important; }}
    section[data-testid="stSidebar"] .st-key-nav_practice button::before, section[data-testid="stSidebar"] .st-key-nav_progress button::before {{
        content: ""; width: 18px; height: 18px; flex: 0 0 18px; background: currentColor; -webkit-mask: var(--ico) center / contain no-repeat; mask: var(--ico) center / contain no-repeat; }}
    section[data-testid="stSidebar"] .st-key-nav_practice button {{ --ico: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='black' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'><path d='M12 20h9'/><path d='M16.5 3.5a2.12 2.12 0 0 1 3 3L7 19l-4 1 1-4z'/></svg>"); }}
    section[data-testid="stSidebar"] .st-key-nav_progress button {{ --ico: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='black' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'><path d='M18 20V10'/><path d='M12 20V4'/><path d='M6 20v-6'/></svg>"); }}
    .nav-item.active {{ background: {COLORS['nav_active']}; color: {COLORS['nav_active_text']}; font-weight: 600; }}

    .sidebar-title {{
        color: {COLORS['sidebar_muted']}; font-size: 11px; font-weight: 700; letter-spacing: .09em;
        text-transform: uppercase; margin-bottom: .5rem;
    }}

    /* Accuracy ring — unchanged */
    .ring-wrap {{ display: flex; justify-content: center; margin: .25rem 0 1.5rem; }}
    .ring {{
        width: 130px; height: 130px; border-radius: 50%; padding: 8px;
        display: flex; align-items: center; justify-content: center;
        background: conic-gradient({COLORS['ring']} calc(var(--pct) * 1%), {COLORS['ring_track']} 0);
    }}
    .ring-inner {{
        width: 100%; height: 100%; border-radius: 50%; background: {COLORS['card']};
        display: flex; flex-direction: column; align-items: center; justify-content: center;
        box-shadow: inset 0 0 0 1px {COLORS['border']};
    }}
    .ring-inner .pct {{ color: {COLORS['text']}; font-size: 24px; font-weight: 800; line-height: 1; }}
    .ring-inner .lbl {{ color: {COLORS['text_muted']}; font-size: 10px; font-weight: 700; margin-top: 6px; text-transform: uppercase; letter-spacing: .05em; }}

    /* Progress cards: same size, soft background */
    .stat-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 10px; }}
    .stat-card {{
        display: flex; flex-direction: column; gap: 10px; min-height: 92px; padding: 13px 13px 12px;
        background: {COLORS['sidebar_card']}; border: 1px solid {COLORS['sidebar_border']}; border-radius: 12px;
    }}
    .stat-card .ico {{
        width: 30px; height: 30px; border-radius: 8px; background: {COLORS['nav_active']}; color: {COLORS['nav_active_text']};
        display: flex; align-items: center; justify-content: center;
    }}
    .stat-card .num {{ color: {COLORS['sidebar_text']}; font-size: 22px; font-weight: 700; line-height: 1; }}
    .stat-card .cap {{ color: {COLORS['sidebar_muted']}; font-size: 12px; font-weight: 500; margin-top: 4px; }}

    .user-card {{
        display: flex; align-items: center; gap: .75rem; margin: 0 0 10px; padding: 11px 13px;
        background: {COLORS['sidebar_card']}; border: 1px solid {COLORS['sidebar_border']}; border-radius: 12px;
    }}
    .user-card .avatar {{
        width: 34px; height: 34px; border-radius: 50%; background: {COLORS['primary']}; color: #fff;
        display: flex; align-items: center; justify-content: center; font-weight: 700; font-size: 15px;
    }}
    .user-card .meta {{ display: flex; flex-direction: column; line-height: 1.25; }}
    .user-card .meta .small {{ color: {COLORS['sidebar_muted']}; font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: .05em; }}
    .user-card .meta .name {{ color: {COLORS['sidebar_text']}; font-size: 14px; font-weight: 700; overflow-wrap: anywhere; }}

    section[data-testid="stSidebar"] .stButton button {{
        background: transparent; color: {COLORS['sidebar_muted']};
        border: 1px solid {COLORS['sidebar_border']}; border-radius: 10px; font-weight: 600; min-height: 40px;
        transition: background-color .15s ease, color .15s ease;
    }}
    section[data-testid="stSidebar"] .stButton button:hover {{ background: {COLORS['sidebar_card']}; color: {COLORS['sidebar_text']}; border-color: {COLORS['sidebar_border']}; }}
    section[data-testid="stSidebar"] .stButton button p {{ color: inherit; }}

    div[data-testid="InputInstructions"] {{ display: none; }}  /* use our own Enter hint */
    .kbd-hint {{ color: {COLORS['text_muted']}; font-size: 12px; margin: 6px 2px 0; }}
    .ok-line {{ color: {COLORS['success']}; font-size: 13px; font-weight: 600; margin: 2px 0; }}
    .hist-cap {{ color: {COLORS['text_muted']}; font-size: 12px; margin: 0 0 4px; }}

    /* ---------- Welcome ---------- */
    /* Hero banner: greeting on top, supporting text underneath, robot on the right */
    .hero {{
        display: flex; align-items: center; justify-content: space-between; gap: 1rem;
        background: {COLORS['sidebar']};
        border-radius: 14px; padding: 16px 22px; margin: 0 0 1.1rem;
    }}
    .hero h1 {{ color: #FFFFFF; font-size: clamp(20px, 3vw, 25px); font-weight: 700; letter-spacing: -.015em; margin: 0; padding: 0; line-height: 1.25; }}
    .hero p {{ color: #D5F0F0; font-size: 14px; margin: 4px 0 0; }}
    .hero p.hero-sub {{ color: #B3E3E0; font-size: 13px; font-style: italic; margin-top: 2px; }}
    .hero-bot {{
        width: 58px; height: 58px; flex: none; padding: 7px; border-radius: 50%;
        background: rgba(255,255,255,.14);
    }}
    .hero-bot svg, .av-bot svg {{ width: 100%; height: 100%; display: block; }}
    .eye {{ transform-box: fill-box; transform-origin: center; animation: blink 4.5s infinite; }}
    .ant {{ animation: ant-glow 2s ease-in-out infinite; }}
    @keyframes blink {{ 0%, 92%, 100% {{ transform: scaleY(1); }} 96% {{ transform: scaleY(.1); }} }}
    @keyframes ant-glow {{ 0%, 100% {{ opacity: 1; }} 50% {{ opacity: .45; }} }}

    /* ---------- Conversation rows (custom avatars) ---------- */
    .msg {{ display: flex; align-items: flex-start; gap: 12px; margin: 12px 0; }}
    .msg.new {{ animation: slide-in .35s ease-out both; }}
    @keyframes slide-in {{ from {{ opacity: 0; transform: translateY(10px); }} to {{ opacity: 1; transform: none; }} }}
    .av {{
        width: 40px; height: 40px; flex: none; border-radius: 50%; position: relative;
        display: flex; align-items: center; justify-content: center;
        background: {COLORS['primary']}; color: #fff; font-weight: 700; font-size: 16px;
    }}
    .av-bot {{ padding: 5px; background: {COLORS['primary_soft']}; border: 1px solid {COLORS['border']}; }}
    .av-bot .dot {{
        position: absolute; width: 10px; height: 10px; right: -2px; bottom: -2px; border-radius: 50%;
        background: {COLORS['success']}; box-shadow: 0 0 0 2px {COLORS['card']}; animation: pulse-dot 2.4s ease-in-out infinite;
    }}
    .msg-body {{ flex: 1; min-width: 0; }}
    .msg-user {{ flex-direction: row-reverse; }}
    .msg-user .msg-body {{ display: flex; justify-content: flex-end; }}
    .ok-line {{ display: flex; align-items: center; gap: 8px; padding-top: 9px; }}
    .ok-line .tick {{
        width: 20px; height: 20px; border-radius: 50%; background: {COLORS['success']}; color: #fff;
        display: inline-flex; align-items: center; justify-content: center; font-size: 12px;
    }}
    .msg.new .ok-line .tick {{ animation: tick-pop .5s ease-out .15s both; }}
    @keyframes tick-pop {{ 0% {{ transform: scale(0); }} 70% {{ transform: scale(1.25); }} 100% {{ transform: scale(1); }} }}
    .typing {{ display: inline-flex; gap: 5px; padding: 14px 4px; }}
    .typing span {{ width: 8px; height: 8px; border-radius: 50%; background: {COLORS['primary']}; animation: bounce-dot 1s infinite ease-in-out; }}
    .typing span:nth-child(2) {{ animation-delay: .15s; }}
    .typing span:nth-child(3) {{ animation-delay: .3s; }}
    @keyframes bounce-dot {{ 0%, 80%, 100% {{ transform: translateY(0); opacity: .45; }} 40% {{ transform: translateY(-6px); opacity: 1; }} }}

    /* ---------- Conversation ---------- */
    [data-testid="stChatMessage"] {{ background: transparent; padding: .35rem 0; }}

    .avatar-wrap {{ position: relative; display: inline-block; }}
    [data-testid="chatAvatarIcon-assistant"] {{ background: {COLORS['primary']} !important; border-radius: 50% !important; }}
    [data-testid="chatAvatarIcon-user"] {{ background: {COLORS['card_hover']} !important; border: 1px solid {COLORS['border']}; border-radius: 50% !important; }}

    /* Subtle AI "online" pulse dot on the assistant avatar */
    [data-testid="chatAvatarIcon-assistant"]::after {{
        content: "";
        position: absolute;
        width: 8px; height: 8px;
        background: {COLORS['success']};
        border-radius: 50%;
        bottom: -1px; right: -1px;
        box-shadow: 0 0 0 2px {COLORS['card']};
        animation: pulse-dot 2.4s ease-in-out infinite;
    }}
    @keyframes pulse-dot {{
        0%, 100% {{ opacity: 0.55; }}
        50% {{ opacity: 1; }}
    }}

    .user-bubble {{
        background: {COLORS['primary']}; color: #fff; border-radius: 14px 14px 4px 14px;
        padding: 11px 15px; font-size: 14.5px; line-height: 1.5; max-width: min(80%, 560px); overflow-wrap: anywhere;
    }}

    .fb-card {{ border-radius: 4px 14px 14px 14px; padding: 13px 16px; margin: 4px 0; border: 1px solid transparent; max-width: 640px; }}
    .fb-card .fb-title {{ display: flex; align-items: center; gap: 7px; font-size: 14px; font-weight: 700; margin-bottom: 7px; }}
    .fb-correct {{ background: {COLORS['success_bg']}; border-color: {COLORS['success_border']}; }}
    .fb-correct .fb-title {{ color: {COLORS['success']}; }}
    .fb-suggestion {{ background: {COLORS['suggestion_bg']}; border-color: {COLORS['suggestion_border']}; }}
    .fb-suggestion .fb-title {{ color: {COLORS['suggestion']}; }}
    .fb-error {{ background: {COLORS['error_bg']}; border-color: {COLORS['error_border']}; }}
    .fb-error .fb-title {{ color: {COLORS['error']}; }}
    .fb-item {{ color: {COLORS['text']}; font-size: 14px; line-height: 1.6; margin: 3px 0; }}
    .fb-item .bad {{ color: {COLORS['error']}; font-weight: 700; text-decoration: line-through; text-decoration-thickness: 2px; }}
    .badge {{ display: inline-block; font-size: 11px; font-weight: 700; padding: 1px 8px; margin-right: 6px; border-radius: 999px;
             background: rgba(0,139,139,.12); color: #17696B; border: 1px solid rgba(0,139,139,.3); cursor: help; vertical-align: 1px; }}
    .badge.lv-basic {{ background: #E6F4EC; color: #2E7D5B; border-color: #BFE0CE; }}
    .badge.lv-elementary {{ background: #E6F2F2; color: #17696B; border-color: #BFDCDC; }}
    .badge.lv-intermediate {{ background: #FFF1D6; color: #9A6B12; border-color: #F0D9A6; }}
    .protip {{ margin-top: 8px; padding: 9px 14px; border-radius: 10px; background: #EAF5F5; border: 1px dashed #9CCFCF;
              color: {COLORS['text']}; font-size: 13.5px; max-width: 640px; }}
    .protip b {{ color: #17696B; }}
    button[data-testid="stBaseButton-primary"], button[kind="primary"] {{ background: {COLORS['primary']} !important; border-color: {COLORS['primary']} !important; color: #FFFFFF !important; }}
    button[data-testid="stBaseButton-primary"]:hover, button[kind="primary"]:hover {{ background: {COLORS['primary_hover']} !important; border-color: {COLORS['primary_hover']} !important; }}
    div[data-testid="stMain"] button[data-testid="stBaseButton-secondary"] {{ background: #FFFFFF; color: {COLORS['text']}; border: 1px solid {COLORS['border']}; }}
    .nudge {{ margin: 6px 0 2px 52px; max-width: 640px; padding: 10px 14px; border-radius: 12px; background: #FFFFFF;
             border: 1px solid #BFDCDC; border-left: 4px solid #008B8B; color: {COLORS['text']}; font-size: 14px; }}
    .quiz-card {{ margin: 8px 0 4px; padding: 11px 13px; border-radius: 12px; background: rgba(0,139,139,.18);
                 border: 1px solid rgba(143,230,223,.25); color: #E8F0F2; }}
    .quiz-card .qt {{ font-weight: 700; font-size: 14px; color: #FFFFFF; }}
    .quiz-card .qs {{ font-size: 12px; color: #A9C4C8; margin-top: 2px; }}
    section[data-testid="stSidebar"] .st-key-mixed_quiz button {{ background: {COLORS['primary']}; color: #FFFFFF; border: 0; margin-top: -2px; }}
    section[data-testid="stSidebar"] .st-key-mixed_quiz button:hover {{ background: {COLORS['primary_hover']}; color: #FFFFFF; }}
    .top-issue {{ margin: 8px 0 4px; padding: 8px 12px; border-radius: 10px; background: rgba(255,255,255,.07);
                 color: #CFE3E5; font-size: 12.5px; }}
    .top-issue b {{ color: #FFFFFF; }}
    .fb-item .good {{ color: {COLORS['success']}; font-weight: 700; }}

    /* ---------- Input ---------- */
    div[data-testid="stForm"] {{
        background: {COLORS['card']}; border: 2px solid #8FA9AC; border-radius: 12px;
        padding: 8px 8px 8px 16px; margin-top: 1rem;
        transition: border-color .15s ease;
    }}
    div[data-testid="stForm"]:focus-within {{ border-color: {COLORS['primary']}; }}
    div[data-testid="stForm"] [data-testid="stHorizontalBlock"] {{ align-items: center; gap: 12px; flex-wrap: nowrap; }}
    /* input takes the free space; the button column has a fixed width */
    div[data-testid="stForm"] [data-testid="stHorizontalBlock"] > div:first-child {{ flex: 1 1 auto !important; min-width: 0 !important; width: auto !important; }}
    div[data-testid="stForm"] [data-testid="stHorizontalBlock"] > div:last-child {{ flex: 0 0 150px !important; width: 150px !important; min-width: 150px !important; }}
    div[data-testid="stForm"] [data-testid="stTextInputRootElement"] {{ border: none !important; box-shadow: none !important; background: transparent !important; min-height: 44px; }}
    div[data-testid="stForm"] input {{ border: 0 !important; background: transparent !important; font-size: 15px !important; font-weight: 500 !important; color: {COLORS['text']} !important; }}
    div[data-testid="stForm"] input::placeholder {{ color: #3F5557 !important; font-weight: 600 !important; opacity: 1 !important; }}
    div[data-testid="stFormSubmitButton"] button {{
        min-height: 44px; height: 44px; width: 150px; background: {COLORS['primary']} !important; color: white !important;
        border: 0 !important; border-radius: 8px !important; font-weight: 600 !important;
        padding: 0 16px !important; white-space: nowrap; transition: background-color .15s ease;
    }}
    div[data-testid="stFormSubmitButton"] button:hover {{ background: {COLORS['primary_hover']} !important; }}
    div[data-testid="stFormSubmitButton"] button:disabled {{ opacity: .4; }}
    .empty-hint {{ color: {COLORS['error']}; font-size: 13px; margin: 7px 2px 0; }}

    @media (max-width: 720px) {{
        .block-container {{ padding: 2.75rem .9rem 4rem; }}
        .hero {{ padding: 16px 18px; }}
        .hero-bot {{ width: 46px; height: 46px; padding: 5px; }}
        .user-bubble {{ max-width: 88%; }}
        div[data-testid="stForm"] {{ padding-left: 10px; }}
        div[data-testid="stFormSubmitButton"] button {{ padding-inline: 12px !important; }}
    }}
    @media (prefers-reduced-motion: reduce) {{ * {{ animation: none !important; transition: none !important; }} }}
</style>
""", unsafe_allow_html=True)


# Small label next to a mistake, e.g. 'Spelling · Basic' (the CEFR code appears only on hover).
# Roman Urdu: Ghalti ke saath chhota label, jaise 'Spelling · Basic' (CEFR code sirf mouse le jane par dikhta hai).
def issue_badge(issue: str) -> str:
    """Small pill like 'Subject-Verb Agreement · Elementary' (CEFR code only in the tooltip)."""
    category, level, cefr = categorize_issue(issue)
    return (f'<span class="badge lv-{level.lower()}" '
            f'title="Level: {level} (CEFR {cefr})">{category} · {level}</span>')


# Shows a mistake as: badge + wrong word (red, struck through) -> right word (green).
# Roman Urdu: Ghalti ko is shakal mein dikhata hai: badge + ghalat lafz (laal, kata hua) -> sahi lafz (hara).
def highlight_issue(issue: str) -> str:
    """Turn "'word' -> try 'fix'" into a styled strikethrough/replacement snippet."""
    # the suggested fix runs to the LAST quote so words like "doesn't" stay whole
    match = re.search(r"'([^']+)'\s*->\s*try\s*'(.+)'\s*$", issue)
    if match:
        bad, good = match.group(1), match.group(2)
        return f'{issue_badge(issue)}<span class="bad">{bad}</span> → <span class="good">{good}</span>'
    return f'{issue_badge(issue)}{issue}'


# Only spelling and subject-verb problems are red 'Errors'; everything else is an amber 'Suggestion'.
# Roman Urdu: Sirf spelling aur subject-verb ki ghaltiyan laal 'Errors' hain; baaki sab peeli 'Suggestions' hain.
def classify_issue(issue: str) -> str:
    """Group issues into error (red) vs suggestion (amber) for display."""
    if issue.startswith("Possible spelling") or issue.startswith("Possible subject-verb"):
        return "error"
    return "suggestion"


# Login page picture: our own flat illustration (robot on a dark panel, chat bubbles, plants, clouds), drawn in code like the quiz scenes.
# Roman Urdu: Login page ki tasveer: hamari apni flat illustration (dark panel par robot, chat bubbles, paude, badal), jo quiz ki tasveeron ki tarah code se bani hai.
def _login_art() -> str:
    robot = (
        '<line x1="60" y1="16" x2="60" y2="30" stroke="#CFEDED" stroke-width="4" stroke-linecap="round"/>'
        '<circle class="ant" cx="60" cy="12" r="6" fill="#FFD27A"/>'
        '<rect x="6" y="54" width="12" height="24" rx="6" fill="#CFEDED"/>'
        '<rect x="102" y="54" width="12" height="24" rx="6" fill="#CFEDED"/>'
        '<rect x="16" y="28" width="88" height="76" rx="26" fill="#F2FBFB"/>'
        '<rect x="27" y="42" width="66" height="44" rx="18" fill="#1F6667"/>'
        '<ellipse class="eye" cx="46" cy="62" rx="6" ry="7.5" fill="#9FF0EA"/>'
        '<ellipse class="eye" cx="74" cy="62" rx="6" ry="7.5" fill="#9FF0EA"/>'
        '<path d="M50 75 Q60 83 70 75" stroke="#9FF0EA" stroke-width="3.5" fill="none" stroke-linecap="round"/>'
        '<circle cx="36" cy="74" r="3.5" fill="#FF9FB2" opacity=".75"/>'
        '<circle cx="84" cy="74" r="3.5" fill="#FF9FB2" opacity=".75"/>'
    )
    cloud = lambda x, y, s=1: (f'<g transform="translate({x} {y}) scale({s})" fill="#FFFFFF"><ellipse cx="0" cy="12" rx="40" ry="14"/>'
                               '<circle cx="-12" cy="2" r="15"/><circle cx="12" cy="-2" r="19"/></g>')
    plant = lambda x, y, leaf, pot, s=1: (
        f'<g transform="translate({x} {y}) scale({s})"><path d="M-16 0 h32 l-5 34 h-22z" fill="{pot}"/>'
        f'<ellipse cx="-12" cy="-18" rx="7" ry="22" fill="{leaf}" transform="rotate(-28 -12 -18)"/>'
        f'<ellipse cx="12" cy="-20" rx="7" ry="24" fill="{leaf}" transform="rotate(28 12 -20)"/>'
        '<ellipse cx="0" cy="-26" rx="7" ry="28" fill="#2F7F5C"/></g>')
    return (
        '<svg viewBox="0 0 600 440" xmlns="http://www.w3.org/2000/svg" style="width:100%;height:auto;display:block" aria-hidden="true">'
        '<path d="M96 210 C70 120 150 40 270 52 C380 62 400 20 482 80 C566 142 560 260 512 330 C462 402 340 420 230 396 C130 374 120 300 96 210Z" fill="#E4F4F4"/>'
        '<path d="M150 232 C136 160 196 100 280 108 C350 114 420 90 470 140 C520 192 500 290 440 332 C380 372 270 372 210 330 C170 302 160 270 150 232Z" fill="#D2ECEC"/>'
        + cloud(96, 70) + cloud(520, 60, .8) + cloud(540, 330, .6) +
        '<ellipse cx="305" cy="396" rx="170" ry="13" fill="#BFDCDC" opacity=".6"/>'
        '<rect x="200" y="86" width="210" height="270" rx="26" fill="#172D35"/>'
        '<circle cx="224" cy="108" r="5" fill="#008B8B"/><circle cx="240" cy="108" r="5" fill="#F2B84B"/><circle cx="256" cy="108" r="5" fill="#E8735A"/>'
        f'<svg x="222" y="126" width="166" height="166" viewBox="0 0 120 120">{robot}</svg>'
        '<rect x="226" y="304" width="120" height="14" rx="7" fill="#008B8B"/>'
        '<rect x="264" y="326" width="120" height="14" rx="7" fill="#E3F4F3" opacity=".9"/>'
        # bubbles
        '<rect x="62" y="146" width="132" height="62" rx="16" fill="#008B8B"/><path d="M168 208 l12 16 l4-16z" fill="#008B8B"/>'
        '<rect x="80" y="162" width="96" height="7" rx="3.5" fill="#FFFFFF"/><rect x="80" y="177" width="76" height="7" rx="3.5" fill="#FFFFFF"/><rect x="80" y="192" width="88" height="7" rx="3.5" fill="#FFFFFF"/>'
        '<rect x="414" y="104" width="136" height="62" rx="16" fill="#FFFFFF" stroke="#BFDCDC" stroke-width="2"/><path d="M430 166 l-10 16 l22-16z" fill="#FFFFFF" stroke="#BFDCDC" stroke-width="2"/>'
        '<text x="434" y="143" font-size="24" font-weight="800" fill="#17696B">Hello!</text>'
        '<rect x="432" y="212" width="112" height="54" rx="16" fill="#F2B84B"/><path d="M450 266 l-8 14 l20-14z" fill="#F2B84B"/>'
        '<text x="452" y="248" font-size="26" font-weight="800" fill="#172D35">A+</text>'
        '<rect x="58" y="262" width="122" height="52" rx="16" fill="#172D35"/><path d="M80 314 l-8 14 l20-14z" fill="#172D35"/>'
        '<rect x="74" y="277" width="90" height="6" rx="3" fill="#8FE6DF"/><rect x="74" y="291" width="64" height="6" rx="3" fill="#8FE6DF"/>'
        '<circle cx="398" cy="322" r="22" fill="#2E7D5B"/><path d="M388 322 l8 8 l14 -16" stroke="#FFFFFF" stroke-width="5" fill="none" stroke-linecap="round" stroke-linejoin="round"/>'
        + plant(104, 378, "#3E9B73", "#C9855B") + plant(500, 372, "#4DAE86", "#E0A458", .8) +
        '<path d="M470 190 l4 10 l10 4 l-10 4 l-4 10 l-4-10 l-10-4 l10-4z" fill="#FFFFFF"/>'
        '<path d="M150 112 l3 8 l8 3 l-8 3 l-3 8 l-3-8 l-8-3 l8-3z" fill="#FFFFFF"/>'
        '</svg>'
    )


# ============================================================
# 🔐 LOGIN GATE — a single popup card (like ChatGPT / Claude).
#    Nothing below runs until a user is signed in.
# ============================================================
# LOGIN GATE: nothing below runs until a user has signed in. st.session_state keeps values while the page reruns.
# Roman Urdu: LOGIN: jab tak user login na kare, neeche ka koi hissa nahi chalta. st.session_state page dobara chalne par bhi values yaad rakhta hai.
if "user" not in st.session_state:
    st.session_state.user = None
if "auth_mode" not in st.session_state:
    st.session_state.auth_mode = "login"


# The login / sign-up form (shown in the white card on the left of the login page).
# Roman Urdu: Login / sign-up ka form (login page par baen taraf safed card mein dikhta hai).
def login_dialog():
    signup = st.session_state.auth_mode == "signup"
    st.markdown('<div class="auth-title">Welcome</div>', unsafe_allow_html=True)
    st.markdown(
        f'<div class="auth-sub">{"Create your account to start practicing" if signup else "Log in to continue your practice"}</div>',
        unsafe_allow_html=True,
    )
    # Form with username and password (plus confirm password when signing up).
    # Roman Urdu: Username aur password ka form (sign-up par confirm password bhi).
    with st.form("auth_form", border=False):
        username = st.text_input("Username", placeholder="Username", label_visibility="collapsed")
        password = st.text_input("Password", type="password", placeholder="Password", label_visibility="collapsed")
        confirm = ""
        if signup:
            confirm = st.text_input("Confirm password", type="password", placeholder="Confirm password",
                                    label_visibility="collapsed")
        if signup:
            st.markdown(f'<div class="auth-hint">{auth.PASSWORD_HINT}</div>', unsafe_allow_html=True)
        clicked = st.form_submit_button("Sign up" if signup else "Continue", **quiz.STRETCH_FORM)

    # On submit: sign-up -> check both passwords match, then auth.register; login -> auth.authenticate.
    # Roman Urdu: Submit par: sign-up mein dono password milao aur auth.register chalao; login mein auth.authenticate chalao.
    if clicked:
        if signup:
            if password != confirm:
                st.session_state.auth_error = "Passwords do not match."
            else:
                ok, msg = auth.register(username, password)
                if ok:
                    st.session_state.user = auth.normalize_username(username)
                    st.session_state.pop("auth_error", None)
                    st.rerun()
                st.session_state.auth_error = msg
        elif auth.authenticate(username, password):
            st.session_state.user = auth.normalize_username(username)
            st.session_state.pop("auth_error", None)
            st.rerun()
        else:
            st.session_state.auth_error = "Invalid username or password."

    if st.session_state.get("auth_error"):
        st.markdown(f'<div class="auth-err">{st.session_state.auth_error}</div>', unsafe_allow_html=True)

    prompt = "Already have an account?" if signup else "Don't have an account?"
    st.markdown(f'<div class="auth-switch">{prompt}</div>', unsafe_allow_html=True)
    if st.button("Log in" if signup else "Sign up", key="auth_switch_btn", **quiz.STRETCH):
        st.session_state.auth_mode = "login" if signup else "signup"
        st.session_state.pop("auth_error", None)
        st.rerun()


# Not signed in: hide the sidebar, show the login page (form on the left, picture on the right), then stop the script here.
# Roman Urdu: Login nahi hai: sidebar chhupao, login page dikhao (baen taraf form, dayen taraf tasveer) aur yahin script rok do.
if st.session_state.user is None:
    st.markdown(f"""
    <style>
        section[data-testid="stSidebar"], [data-testid="stExpandSidebarButton"], [data-testid="stSidebarCollapsedControl"] {{ display: none !important; }}
        .stApp {{ background: #F3FAFB; }}
        header[data-testid="stHeader"] {{ background: transparent !important; }}
        .block-container {{ max-width: 1100px; padding-top: 9vh; }}
        div[data-testid="stHorizontalBlock"] {{ align-items: center; gap: 2rem; }}
        /* left: white login card */
        div[data-testid="stHorizontalBlock"] > div:first-child {{
            background: {COLORS['card']}; border-radius: 18px; padding: 2.2rem 2.4rem 1.8rem;
            box-shadow: 0 6px 24px rgba(23,45,53,.07);
        }}
        .auth-title {{ font-size: 30px; font-weight: 800; color: {COLORS['primary_hover']}; letter-spacing: -.02em; margin-bottom: 2px; }}
        .auth-sub {{ color: {COLORS['text_muted']}; font-size: 14px; margin: 0 0 18px; }}
        .auth-hint {{ color: {COLORS['text_muted']}; font-size: 12.5px; margin: -2px 2px 12px; }}
        .auth-err {{ color: {COLORS['error']}; font-size: 13px; text-align: center; margin: 8px 0 0; }}
        .auth-switch {{ text-align: center; color: {COLORS['text_muted']}; font-size: 13px; margin: 18px 0 0; }}
        /* fields: soft teal fill with a small icon */
        div[data-testid="stForm"] {{ background: transparent; border: 0; padding: 0; margin: 0; }}
        div[data-testid="stForm"] [data-testid="stTextInputRootElement"] {{
            background: #E8F5F5 !important; border: 1px solid #CFE7E7 !important; border-radius: 10px !important; min-height: 46px;
        }}
        div[data-testid="stForm"] [data-testid="stTextInputRootElement"]:focus-within {{ border-color: {COLORS['primary']} !important; }}
        div[data-testid="stForm"] input {{ background-repeat: no-repeat !important; background-position: 14px center !important; background-size: 18px !important; padding-left: 44px !important; color: {COLORS['text']} !important; }}
        div[data-testid="stForm"] input[aria-label="Username"] {{ background-image: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%2317696B' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'><path d='M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2'/><circle cx='12' cy='7' r='4'/></svg>") !important; }}
        div[data-testid="stForm"] input[type="password"], div[data-testid="stForm"] input[aria-label="Confirm password"] {{ background-image: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%2317696B' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'><rect x='3' y='11' width='18' height='11' rx='2'/><path d='M7 11V7a5 5 0 0 1 10 0v4'/></svg>") !important; }}
        div[data-testid="stForm"] [data-testid="stTextInputRootElement"] button, div[data-testid="stForm"] [data-testid="stTextInputRootElement"] button svg {{ color: {COLORS['text_muted']} !important; fill: {COLORS['text_muted']} !important; }}
        div[data-testid="stForm"] [data-testid="stTextInputRootElement"] > div {{ margin-bottom: 0; }}
        /* main button: fixed width, centred */
        div[data-testid="stFormSubmitButton"] {{ display: flex; justify-content: center; margin-top: 8px; }}
        div[data-testid="stFormSubmitButton"] button {{ width: 220px; min-height: 46px; border-radius: 10px !important; background: {COLORS['primary']} !important; color: #FFFFFF !important; border: 0 !important; font-weight: 600; }}
        div[data-testid="stFormSubmitButton"] button:hover {{ background: {COLORS['primary_hover']} !important; }}
        /* "Sign up / Log in" switch = plain text link */
        .st-key-auth_switch_btn button {{
            background: transparent !important; border: 0 !important; color: {COLORS['primary_hover']} !important;
            font-weight: 700; min-height: 0; padding: 4px 0 0 !important; box-shadow: none !important;
        }}
        .st-key-auth_switch_btn button:hover {{ text-decoration: underline; }}
        @media (max-width: 900px) {{ div[data-testid="stHorizontalBlock"] > div:last-child {{ display: none; }} .block-container {{ padding-top: 4vh; }} }}
    </style>
    """, unsafe_allow_html=True)
    form_col, art_col = st.columns([1, 1.25], gap="large")
    with form_col:
        login_dialog()
    with art_col:
        st.markdown(_login_art(), unsafe_allow_html=True)
    st.stop()

# From here on the user is signed in.
# Roman Urdu: Yahan se aage user login ho chuka hai.
current_user = st.session_state.user

# --- Dynamic greeting ---
# Greeting depends on the time of day: morning / afternoon / evening.
# Roman Urdu: Salam waqt ke hisab se: subah / dopahar / shaam.
hour = datetime.now().hour
if hour < 12:
    greeting = "Good Morning! 🌤️"
elif hour < 18:
    greeting = "Good Afternoon! ☀️"
else:
    greeting = "Good Evening! 🌙"

# --- Session state ---
# Each user gets their own agent + progress file (rebuilt if a different user logs in).
# Each user gets their own agent and progress file. If a different user logs in, everything is rebuilt for them.
# Roman Urdu: Har user ka apna agent aur progress file. Doosra user login kare to uske liye sab naye sire se banta hai.
if st.session_state.get("agent_user") != current_user:
    st.session_state.agent = LanguageAgent(auth.progress_file_for(current_user))
    st.session_state.agent_user = current_user
    st.session_state.chat_history = []
    st.session_state.tips = {}
    quiz.reset_quiz_state()
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []  # (role, text/issues, status)
if "tips" not in st.session_state:
    st.session_state.tips = {}  # reply index -> vocabulary Pro Tip
# Session values that must exist: the current page (Practice/Progress), Pro Tips and quiz offers.
# Roman Urdu: Zaroori session values: maujooda page (Practice/Progress), Pro Tips aur quiz ki dawatein.
if "page" not in st.session_state:
    st.session_state.page = "Practice"  # which page the sidebar navigation shows
if "nudges" not in st.session_state:
    st.session_state.nudges = {}  # reply index -> "offer the quiz here"

# The robot picture (drawn in code): used in the sidebar logo, the banner and next to the bot's replies.
# Roman Urdu: Robot ki tasveer (code se bani hui): sidebar ke logo, banner aur bot ke jawabon mein use hoti hai.
ROBOT_SVG = (
    '<svg viewBox="0 0 120 120" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">'
    '<line x1="60" y1="16" x2="60" y2="30" stroke="#CFEDED" stroke-width="4" stroke-linecap="round"/>'
    '<circle class="ant" cx="60" cy="12" r="6" fill="#FFD27A"/>'
    '<rect x="6" y="54" width="12" height="24" rx="6" fill="#CFEDED"/>'
    '<rect x="102" y="54" width="12" height="24" rx="6" fill="#CFEDED"/>'
    '<rect x="16" y="28" width="88" height="76" rx="26" fill="#F2FBFB"/>'
    '<rect x="27" y="42" width="66" height="44" rx="18" fill="#1F6667"/>'
    '<ellipse class="eye" cx="46" cy="62" rx="6" ry="7.5" fill="#9FF0EA"/>'
    '<ellipse class="eye" cx="74" cy="62" rx="6" ry="7.5" fill="#9FF0EA"/>'
    '<path d="M50 75 Q60 83 70 75" stroke="#9FF0EA" stroke-width="3.5" fill="none" stroke-linecap="round"/>'
    '<circle cx="36" cy="74" r="3.5" fill="#FF9FB2" opacity=".75"/>'
    '<circle cx="84" cy="74" r="3.5" fill="#FF9FB2" opacity=".75"/>'
    '</svg>'
)

# --- Sidebar: navigation + progress (existing features, restyled only) ---
# Makes a small SVG icon from drawing paths (used in the sidebar cards).
# Roman Urdu: Drawing paths se chhota SVG icon banata hai (sidebar ke cards ke liye).
def _icon(paths: str, size: int = 18) -> str:
    return (f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
            f'stroke-width="2" stroke-linecap="round" stroke-linejoin="round">{paths}</svg>')

ICON_LOGO = _icon('<path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>', 17)
ICON_PRACTICE = _icon('<path d="M12 20h9"/><path d="M16.5 3.5a2.12 2.12 0 0 1 3 3L7 19l-4 1 1-4z"/>')
ICON_PROGRESS = _icon('<path d="M18 20V10"/><path d="M12 20V4"/><path d="M6 20v-6"/>')
ICON_BOOK = _icon('<path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z"/><path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"/>')
ICON_CHECK = _icon('<path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><path d="M22 4 12 14.01l-3-3"/>')

# SIDEBAR: logo, navigation, accuracy ring, Practiced/Correct cards, Top mistake, Quick Quiz, user card and Log out.
# Roman Urdu: SIDEBAR: logo, navigation, accuracy ring, Practiced/Correct cards, Top mistake, Quick Quiz, user card aur Log out.
with st.sidebar:
    st.markdown(f"""
    <div class="brand"><span class="logo">{ROBOT_SVG}</span><span class="brand-text"><span class="bn">Language Agent</span><span class="bs">Learn · Practice · Improve</span></span></div>
    """, unsafe_allow_html=True)

    def _go(page_name: str):
        st.session_state.page = page_name

    # Navigation buttons: clicking one changes st.session_state.page; the active one is highlighted.
    # Roman Urdu: Navigation buttons: click par st.session_state.page badalta hai; jo page khula ho wo highlight hota hai.
    st.button("Practice", key="nav_practice", on_click=_go, args=("Practice",), **quiz.STRETCH)
    st.button("Progress", key="nav_progress", on_click=_go, args=("Progress",), **quiz.STRETCH)
    _active = "practice" if st.session_state.page == "Practice" else "progress"
    st.markdown(f"""
    <style>
    section[data-testid="stSidebar"] .st-key-nav_{_active} button {{ background: {COLORS['nav_active']} !important; color: {COLORS['nav_active_text']} !important; font-weight: 600 !important; }}
    </style>
    <div class="sidebar-title">Your Learning</div>
    """, unsafe_allow_html=True)

    # Numbers for the ring and cards: accuracy = correct sentences / all sentences.
    # Roman Urdu: Ring aur cards ke numbers: accuracy = sahi jumle / kul jumle.
    stats = st.session_state.agent.tracker.get_stats()
    total = stats["total"]
    correct = stats["correct"]
    accuracy = (correct / total * 100) if total else 0

    # 'Top mistake' = the category with the highest count (capital-letter slips are not counted).
    # Roman Urdu: 'Top mistake' = jis category ki ghalti sab se zyada hai (capital letter ki ghalti nahi ginte).
    breakdown = st.session_state.agent.tracker.get_category_breakdown()
    top_issue_html = (f'<div class="top-issue">Top mistake: <b>{next(iter(breakdown))}</b> ({next(iter(breakdown.values()))}×)</div>'
                      if breakdown else "")

    st.markdown(f"""
    <div class="ring-wrap">
        <div class="ring" style="--pct:{accuracy:.0f};">
            <div class="ring-inner">
                <div class="pct">{accuracy:.0f}%</div>
                <div class="lbl">Accuracy</div>
            </div>
        </div>
    </div>
    <div class="stat-grid">
        <div class="stat-card"><span class="ico">{ICON_BOOK}</span><div><div class="num">{total}</div><div class="cap">Practiced</div></div></div>
        <div class="stat-card"><span class="ico">{ICON_CHECK}</span><div><div class="num">{correct}</div><div class="cap">Correct</div></div></div>
    </div>
    {top_issue_html}
    <div class="quiz-card"><div class="qt">🎯 Quick Quiz</div><div class="qs">Mixed scenario · 2 minutes</div></div>
    """, unsafe_allow_html=True)
    # Start quiz button: opens a random scenario quiz (handled after the sidebar, see below).
    # Roman Urdu: Start quiz button: koi bhi random scenario quiz kholta hai (neeche sidebar ke baad handle hota hai).
    start_mixed_quiz = st.button("Start quiz", key="mixed_quiz", **quiz.STRETCH)

    st.markdown(f"""
    <div class="user-card">
        <div class="avatar">{current_user[:1].upper()}</div>
        <div class="meta"><span class="small">Signed in as</span><span class="name">{current_user}</span></div>
    </div>
    """, unsafe_allow_html=True)

    # Log out: remove this user's data from memory and rerun, which shows the login pop-up again.
    # Roman Urdu: Log out: is user ka data memory se hatao aur dobara chalao, jis se login pop-up wapas aata hai.
    if st.button("Log out", **quiz.STRETCH):
        for k in ("user", "agent", "agent_user", "chat_history", "tips", "nudges", "nudge_dismissed", "quiz", "quiz_pool", "quiz_last", "practice_topic", "auth_mode", "auth_error"):
            st.session_state.pop(k, None)
        st.rerun()

# Open the quiz pop-up if the sidebar button was pressed.
# Roman Urdu: Sidebar ka button dabaya gaya ho to quiz ka pop-up kholo.
if start_mixed_quiz or st.session_state.pop("start_offer_quiz", False):
    quiz.start_quiz()  # opens the pop-up

# Progress page: draw it (progress_page.py) and stop, so the chat below is only for the Practice page.
# Roman Urdu: Progress page: usay banao (progress_page.py) aur ruk jao, taake neeche ka chat sirf Practice page par aaye.
if st.session_state.page == "Progress":
    progress_page.render(st.session_state.agent.tracker, quiz.load_history(), highlight_issue)
    st.stop()  # the chat area below belongs to the Practice page

# --- Practice page only: layout styling (UI only, no logic) ---
# Roman Urdu: Sirf Practice page ki shakal (layout aur rang); koi logic nahi badla.
st.markdown(f"""
<style>
    /* fixed dashboard: no page scroll; hero + chat on the left, cards on the right; only the chat messages scroll */
    header[data-testid="stHeader"] {{ display: none !important; }}
    [data-testid="stMain"] {{ overflow: hidden !important; }}
    [data-testid="stMain"] .block-container {{ max-width: 1180px; height: 100vh; padding: .75rem 1rem .5rem; overflow-y: auto; overflow-x: hidden; scrollbar-width: thin; }}
    /* sidebar can scroll when the window is short, so Quick Quiz / Log out are never hidden */
    [data-testid="stSidebarContent"] {{ overflow-y: auto !important; }}
    .hero {{ margin: 0 0 12px; border-radius: 16px; padding: 14px 24px; }}
    /* right column: cards stay at the top; scrolls inside itself only if the window is very short */
    div[data-testid="stColumn"]:has(.st-key-streakcard) {{ max-height: calc(100vh - 1.4rem); overflow-y: auto; scrollbar-width: none; }}
    div[data-testid="stColumn"]:has(.st-key-streakcard)::-webkit-scrollbar {{ display: none; }}
    /* chat box fills the height left under the hero, so the input bar is always visible at the bottom */
    div[data-testid="stLayoutWrapper"]:has(> .st-key-chatbox), .st-key-chatbox {{ height: calc(100vh - 335px) !important; flex: 0 0 auto !important; max-height: none; min-height: 130px; }}

    /* chat card: white rounded card = scrollable chat + input bar */
    .st-key-chatcard {{ background: {COLORS['card']}; border: 1px solid {COLORS['border']}; border-radius: 16px; padding: 14px 16px 10px; gap: .5rem; }}
    .st-key-chatbox {{ padding-right: 6px; }}

    /* messages: user = teal bubble on the right, robot = light card on the left */
    .msg {{ margin: 10px 0; }}
    .av {{ width: 42px; height: 42px; }}
    .av-bot {{ background: {COLORS['primary_soft']}; border: 2px solid #FFFFFF; box-shadow: 0 0 0 1px {COLORS['border']}; }}
    .av-user {{ background: {COLORS['primary_hover']}; }}
    .user-bubble {{ background: {COLORS['primary']}; color: #FFFFFF; border-radius: 16px 16px 4px 16px; }}
    .bot-bubble {{ display: inline-block; max-width: min(92%, 640px); padding: 12px 16px; border-radius: 4px 16px 16px 16px;
                  border: 1px solid {COLORS['border']}; background: #F4F8F9; color: {COLORS['text']}; font-size: 14.5px; line-height: 1.55; }}
    .bot-bubble.ok {{ background: {COLORS['success_bg']}; border-color: {COLORS['success_border']}; }}
    .bot-bubble.err {{ background: {COLORS['error_bg']}; border-color: {COLORS['error_border']}; }}
    .bot-bubble.sug {{ background: {COLORS['suggestion_bg']}; border-color: {COLORS['suggestion_border']}; }}
    .bot-bubble .fb-card {{ background: transparent; border: 0; border-radius: 0; padding: 0; margin: 0; max-width: none; }}
    .bot-bubble .fb-card + .fb-card {{ margin-top: 10px; }}
    .bot-bubble .protip {{ background: rgba(255,255,255,.78); border: 1px solid rgba(23,45,53,.08); border-radius: 10px;
                          padding: 8px 12px; margin-top: 9px; max-width: none; font-size: 13.5px; }}
    .bot-bubble .ok-line {{ padding-top: 0; }}
    .bot-bubble .typing {{ padding: 4px 2px; }}

    /* quiz offer = a message inside the chat, with its two buttons */
    .st-key-nudge_msg {{ margin: 2px 0 10px 54px; max-width: 560px; background: {COLORS['primary_soft']}; border: 1px solid #BFDCDC;
                        border-left: 4px solid {COLORS['primary']}; border-radius: 12px; padding: 12px 14px; gap: .9rem; }}
    .st-key-nudge_msg .nudge {{ margin: 0 0 8px; padding: 0; border: 0; background: transparent; max-width: none; font-size: 14px; }}
    .st-key-nudge_msg [data-testid="stHorizontalBlock"] {{ gap: .5rem; flex-wrap: nowrap; }}
    .st-key-nudge_msg [data-testid="stHorizontalBlock"] > div:nth-child(1), .st-key-nudge_msg [data-testid="stHorizontalBlock"] > div:nth-child(2) {{ flex: 0 0 auto !important; width: auto !important; min-width: 0 !important; }}
    .st-key-nudge_msg [data-testid="stHorizontalBlock"] > div:nth-child(3) {{ display: none; }}
    [class*="st-key-nudge_take"] button {{ background: {COLORS['primary']} !important; color: #FFFFFF !important; border: 0 !important; }}
    [class*="st-key-nudge_later"] button {{ background: #FFFFFF !important; color: {COLORS['text']} !important; border: 1px solid {COLORS['border']} !important; }}

    /* input bar: filled teal, white text, white button */
    .st-key-chatcard div[data-testid="stForm"] {{ background: {COLORS['primary']}; border: 0; border-radius: 14px; padding: 8px 8px 8px 18px; margin-top: .25rem; }}
    .st-key-chatcard div[data-testid="stForm"]:focus-within {{ box-shadow: 0 0 0 3px rgba(0,139,139,.28); }}
    .st-key-chatcard div[data-testid="stForm"] input {{ color: #FFFFFF !important; caret-color: #FFFFFF; }}
    .st-key-chatcard div[data-testid="stForm"] input::placeholder {{ color: rgba(255,255,255,.92) !important; font-weight: 600 !important; opacity: 1 !important; }}
    .st-key-chatcard div[data-testid="stFormSubmitButton"] button {{ background: #FFFFFF !important; color: {COLORS['primary_hover']} !important; font-weight: 700 !important; border: 0 !important; }}
    .st-key-chatcard div[data-testid="stFormSubmitButton"] button:hover {{ background: #E8F6F6 !important; }}
    .st-key-chatcard div[data-testid="stFormSubmitButton"] button p {{ color: {COLORS['primary_hover']} !important; }}
    .kbd-hint {{ margin: 0 2px; }}

    /* right-hand preview panels (layout only, no logic yet) */
    .side-card {{ background: {COLORS['card']}; border: 1px solid {COLORS['border']}; border-radius: 16px; padding: 14px 16px; margin-bottom: 14px; }}
    .side-head {{ display: flex; align-items: center; justify-content: space-between; gap: 8px; margin-bottom: 12px; }}
    .side-title {{ display: flex; align-items: center; gap: 8px; font-weight: 800; font-size: 14.5px; color: {COLORS['text']}; }}
    .side-title svg {{ color: {COLORS['primary']}; flex: none; }}
    .side-tags {{ display: flex; align-items: center; gap: 6px; }}
    .pill {{ background: {COLORS['primary']}; color: #FFFFFF; font-size: 11px; font-weight: 700; padding: 3px 10px; border-radius: 999px; }}
    .pv {{ font-size: 10px; font-weight: 700; letter-spacing: .06em; text-transform: uppercase; color: {COLORS['text_muted']}; background: #EEF2F3; border-radius: 999px; padding: 3px 8px; }}
    /* streak calendar card */
    .st-key-streakcard {{ background: {COLORS['card']}; border: 1px solid {COLORS['border']}; border-radius: 16px; padding: 12px 14px 12px; gap: .35rem; }}
    .st-key-streakcard .side-head {{ margin-bottom: 4px; flex-wrap: wrap; row-gap: 6px; }}
    .st-key-streakcard .side-title {{ white-space: nowrap; }}
    .st-key-streakcard .pill {{ font-size: 12px; padding: 4px 11px; white-space: nowrap; }}
    .st-key-streakcard [data-testid="stHorizontalBlock"] {{ align-items: center; gap: .25rem; flex-wrap: nowrap; }}
    .st-key-streakcard [data-testid="stHorizontalBlock"] > div:nth-child(1), .st-key-streakcard [data-testid="stHorizontalBlock"] > div:nth-child(3) {{ flex: 0 0 34px !important; min-width: 34px !important; width: 34px !important; }}
    .st-key-streakcard [data-testid="stHorizontalBlock"] > div:nth-child(2) {{ flex: 1 1 auto !important; min-width: 0 !important; }}
    .st-key-streakcard button {{ min-height: 30px; height: 30px; padding: 0; border-radius: 8px; border: 1px solid {COLORS['border']}; background: #FFFFFF; color: {COLORS['text']}; }}
    .st-key-streakcard button:disabled {{ opacity: .35; }}
    .cal-month {{ text-align: center; font-weight: 700; font-size: 14px; color: {COLORS['text']}; }}
    .cal {{ display: grid; grid-template-columns: repeat(7, 1fr); gap: 3px; text-align: center; font-size: 12px; }}
    .cal .h {{ color: {COLORS['text_muted']}; font-size: 11px; font-weight: 600; padding-bottom: 2px; }}
    .cal .c {{ aspect-ratio: 1 / 1; max-width: 32px; width: 100%; margin: 0 auto; display: flex; align-items: center; justify-content: center; border-radius: 50%; color: {COLORS['text']}; }}
    .cal .c.on {{ background: {COLORS['primary']}; color: #FFFFFF; font-weight: 700; }}
    .cal .c.today {{ box-shadow: inset 0 0 0 2px {COLORS['primary']}; font-weight: 700; }}
    .cal .c.on.today {{ box-shadow: 0 0 0 2px #FFFFFF, 0 0 0 4px {COLORS['primary']}; }}
    .days {{ display: grid; grid-template-columns: repeat(7, 1fr); gap: 4px; text-align: center; font-size: 11.5px; color: {COLORS['text_muted']}; }}
    .days .d {{ width: 18px; height: 18px; border-radius: 50%; margin: 7px auto 0; background: #E3EDEE; }}
    .days .on {{ background: {COLORS['primary']}; }}
    .word {{ display: flex; align-items: flex-start; justify-content: space-between; gap: 8px; background: #F1F8F8; border: 1px solid #DCEBEB; border-radius: 12px; padding: 10px 12px; margin-bottom: 9px; }}
    .word b {{ color: {COLORS['text']}; font-size: 14px; }}
    .word i {{ color: {COLORS['text_muted']}; font-size: 12px; margin-left: 6px; }}
    .word p {{ margin: 3px 0 0; font-size: 13px; color: {COLORS['text_muted']}; }}
    .word svg {{ color: {COLORS['primary']}; flex: none; margin-top: 2px; }}
    .side-btn {{ display: block; text-align: center; background: {COLORS['primary']}; color: #FFFFFF; font-weight: 700; font-size: 13.5px; padding: 10px; border-radius: 10px; margin-top: 2px; }}
    @media (max-width: 1000px) {{
        div[data-testid="stHorizontalBlock"]:has(.st-key-streakcard) > div:last-child {{ display: none; }}
        div[data-testid="stHorizontalBlock"]:has(.st-key-streakcard) > div:first-child {{ flex: 1 1 100% !important; width: 100% !important; }}
    }}
</style>
""", unsafe_allow_html=True)

# --- Conversation rows: custom avatars (user initial / animated robot) ---
USER_INITIAL = current_user[:1].upper()


# HTML for the user's chat bubble (text is escaped so it cannot inject HTML).
# Roman Urdu: User ke chat bubble ka HTML (text escape hota hai taake koi HTML na ghusa sake).
def user_row(text: str) -> str:
    return (
        '<div class="msg msg-user">'
        f'<div class="av av-user">{USER_INITIAL}</div>'
        f'<div class="msg-body"><div class="user-bubble">{html.escape(text)}</div></div>'
        '</div>'
    )


# HTML for the bot's reply row; new=True plays the slide-in animation; tone colours the card (ok = green, err = red, sug = amber).
# Roman Urdu: Bot ke jawab wali row ka HTML; new=True par slide-in animation chalti hai; tone card ka rang tay karta hai (ok = hara, err = laal, sug = peela).
def bot_row(inner: str, new: bool = False, tone: str = "") -> str:
    return (
        f'<div class="msg msg-bot{" new" if new else ""}">'
        f'<div class="av av-bot">{ROBOT_SVG}<span class="dot"></span></div>'
        f'<div class="msg-body"><div class="bot-bubble{" " + tone if tone else ""}">{inner}</div></div>'
        '</div>'
    )


# The 'Pro Tip' line (a better word to use), if there is one.
# Roman Urdu: 'Pro Tip' wali line (behtar lafz ka mashwara), agar ho.
def tip_html(tip) -> str:
    return f'<div class="protip">✨ <b>Pro Tip:</b> {html.escape(tip)}</div>' if tip else ""


# Builds the reply: a one-line tick if correct; otherwise an Errors part and a Suggestions part, then the Pro Tip.
# Roman Urdu: Jawab banata hai: sahi ho to ek line wala tick; warna Errors wala hissa aur Suggestions wala hissa, phir Pro Tip.
def feedback_html(payload, status, tip=None) -> str:
    if status is True:
        # Correct sentence: no card, just a light one-line confirmation.
        return ('<div class="ok-line"><span class="tick">✓</span>Looks correct — nice work!</div>'
                + tip_html(tip))
    errors = [highlight_issue(i) for i in payload if classify_issue(i) == "error"]
    suggestions = [highlight_issue(i) for i in payload if classify_issue(i) == "suggestion"]
    out = ""
    if errors:
        items = "".join(f'<div class="fb-item">{e}</div>' for e in errors)
        out += f'<div class="fb-card fb-error"><div class="fb-title">❌ Errors</div>{items}</div>'
    if suggestions:
        items = "".join(f'<div class="fb-item">{x}</div>' for x in suggestions)
        out += f'<div class="fb-card fb-suggestion"><div class="fb-title">💡 Suggestions</div>{items}</div>'
    return out + tip_html(tip)


# Right-hand panel: "Your Learning Streak" = a month calendar of the practice days (teal = practised) + the current streak.
# Dates come from this user's own progress file; the streak is only CALCULATED from them each time (it is never stored).
# Roman Urdu: Dayen panel: "Your Learning Streak" = mahine ka calendar (jin dino practice ki wo teal) + maujooda streak.
# Dates is user ki apni progress file se aati hain; streak har baar sirf hisaab se nikalti hai (kahin save nahi hoti).
import calendar as _calendar
from streak_tracker import StreakTracker
from datetime import date as _date

_today = _date.today()
if "cal_ym" not in st.session_state:  # the month being shown (year, month); starts at the current month
    st.session_state.cal_ym = (_today.year, _today.month)


# Previous / Next month arrows: only change the month that is displayed.
# Roman Urdu: Pichla / Agla mahina arrows: sirf dikhaya jane wala mahina badalte hain.
def _cal_shift(step: int):
    y, m = st.session_state.cal_ym
    m += step
    if m == 0:
        y, m = y - 1, 12
    elif m == 13:
        y, m = y + 1, 1
    st.session_state.cal_ym = (y, m)


_FLAME = ('<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" '
          'stroke-linejoin="round"><path d="M8.5 14.5A2.5 2.5 0 0 0 11 12c0-1.38-.5-2-1-3-1.07-2.14-.22-4.05 2-6 .5 2.5 2 4.9 4 6.5 2 1.6 3 3.5 3 5.5a7 7 0 1 1-14 0c0-1.15.43-2.3 1-3a2.5 2.5 0 0 0 2.5 2.5z"/></svg>')


# HTML of the calendar grid for one month: 7 headers, then the dates (teal = practised, ring = today).
# Roman Urdu: Ek mahine ke calendar ka HTML: 7 din ke headers, phir tareekhein (teal = practice hui, ring = aaj).
def calendar_html(year: int, month: int, practised: set) -> str:
    cells = "".join(f'<div class="h">{d}</div>' for d in ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"])
    for week in _calendar.Calendar(firstweekday=0).monthdayscalendar(year, month):
        for day in week:
            if day == 0:
                cells += '<div></div>'
                continue
            iso = f"{year:04d}-{month:02d}-{day:02d}"
            cls = "c" + (" on" if iso in practised else "") + (" today" if iso == _today.isoformat() else "")
            cells += f'<div class="{cls}">{day}</div>'
    return f'<div class="cal">{cells}</div>'


# --- Chat history: the whole conversation of this session stays in the chat and scrolls (older messages are above) ---
# Roman Urdu: Chat history: is session ki poori chat rehti hai aur scroll hoti hai (purane messages upar hain).
HISTORY_LIMIT = 500  # number of recent checks (sentence + feedback) kept in the scrollable chat
recent = st.session_state.chat_history[-HISTORY_LIMIT * 2:]

# Only the newest bot reply animates in (and only right after a submit), so old rows stay still.
# Build the chat rows: user sentence, then the bot's feedback (with its Pro Tip). Only the newest reply animates.
# Roman Urdu: Chat ki rows banao: user ka jumla, phir bot ki feedback (Pro Tip ke saath). Sirf sab se naya jawab animate hota hai.
animate_new = st.session_state.pop("just_submitted", False)
rows = []
for idx, (role, payload, status) in enumerate(recent):
    if role == "user":
        rows.append(user_row(payload))
    else:
        abs_idx = len(st.session_state.chat_history) - len(recent) + idx
        tip = st.session_state.tips.get(abs_idx)
        tone = "ok" if status is True else ("err" if any(classify_issue(i) == "error" for i in payload) else "sug")
        rows.append(bot_row(feedback_html(payload, status, tip), new=animate_new and idx == len(recent) - 1, tone=tone))

# Layout: chat card on the left, preview panels on the right.
# Roman Urdu: Layout: baen taraf chat card, dayen taraf preview panels.
chat_col, side_col = st.columns([2.2, 1], gap="medium")
with side_col:
    _tracker = StreakTracker(st.session_state.agent.tracker.data_file)  # this user's practice days (separate file, not the progress data)
    _practised = _tracker.days
    _y, _m = st.session_state.cal_ym
    with st.container(key="streakcard"):
        st.markdown('<div class="side-head"><div class="side-title">' + _FLAME + 'Your Learning Streak</div>'
                    f'<span class="pill">🔥 {_tracker.current_streak()}-day streak</span></div>', unsafe_allow_html=True)
        _c1, _c2, _c3 = st.columns([1, 4, 1])
        _c1.button("‹", key="cal_prev", on_click=_cal_shift, args=(-1,), help="Previous month")
        _c2.markdown(f'<div class="cal-month">{_calendar.month_name[_m]} {_y}</div>', unsafe_allow_html=True)
        _c3.button("›", key="cal_next", on_click=_cal_shift, args=(1,), help="Next month",
                   disabled=(_y, _m) >= (_today.year, _today.month))
        st.markdown(calendar_html(_y, _m, _practised), unsafe_allow_html=True)

take_quiz = False
with chat_col:
    # --- Main area: hero banner (greeting on top, supporting text below, robot on the right) ---
    # The hero banner. (The robot picture ROBOT_SVG is defined above the sidebar, because the sidebar logo uses it too.)
    # Roman Urdu: Upar wala hero banner. (Robot ki tasveer ROBOT_SVG sidebar se pehle define hai, kyunke sidebar ka logo bhi usi se banta hai.)
    st.markdown(
        '<div class="hero"><div class="hero-text">'
        f'<h1>{greeting}</h1>'
        '<p>Ready to improve your English today?</p>'
        '<p class="hero-sub">Practice English, improve your grammar, and build confidence with AI.</p>'
        f'</div><div class="hero-bot">{ROBOT_SVG}</div></div>',
        unsafe_allow_html=True,
    )

    # Practice page: the 'Practise this topic' card appears only after a quiz was failed 3 times.
    # Roman Urdu: Practice page: 'Practise this topic' card sirf 3 baar quiz fail hone ke baad aata hai.
    quiz.render_practice_card()  # appears only after a quiz was failed 3 times

    with st.container(key="chatcard"):
        # The scrollable chat area (fixed height); older messages are reached by scrolling up.
        # Roman Urdu: Scroll hone wali chat ki jagah (fixed unchai); purane messages upar scroll karke milte hain.
        chat_box = st.container(height=440, border=False, key="chatbox")
        with chat_box:
            if rows:
                st.markdown("".join(rows), unsafe_allow_html=True)

            # Quiz offer: a message inside the chat (under the newest reply) when one error type reaches 3, 6, 9... mistakes.
            # Roman Urdu: Quiz ki dawat: chat ke andar ek message (sab se naye jawab ke neeche) jab ek hi qism ki ghalti 3, 6, 9... baar ho.
            _last = len(st.session_state.chat_history) - 1
            if st.session_state.nudges.get(_last) and st.session_state.get("nudge_dismissed") != _last:
                with st.container(key="nudge_msg"):
                    st.markdown('<div class="nudge">🎯 You\'ve made a few mistakes of the same kind. Want to attempt a quick quiz?</div>',
                                unsafe_allow_html=True)
                    nc1, nc2, _sp = st.columns([1, 1, 3])
                    take_quiz = nc1.button("Take the quiz", key=f"nudge_take_{_last}", type="primary")
                    if nc2.button("Later", key=f"nudge_later_{_last}"):
                        st.session_state.nudge_dismissed = _last
                        st.rerun()

            # Empty placeholder that is filled with the 'typing...' animation while the sentence is being checked.
            # Roman Urdu: Khali jagah jahan jumla check hote waqt 'typing...' animation dikhti hai.
            typing_slot = st.empty()  # shows the new sentence + "typing" dots while it is being checked

        # --- Input form: Enter-to-submit, loading spinner, session-state persistence ---
        # The sentence box + 'Check & Learn' button. Enter also submits; the box is cleared afterwards.
        # Roman Urdu: Jumla likhne ka dabba + 'Check & Learn' button. Enter dabane se bhi submit hota hai; baad mein dabba khali ho jata hai.
        with st.form("practice_form", clear_on_submit=True):
            col1, col2 = st.columns([4, 1.4])  # widths are fixed by the CSS (button column = 150px)
            with col1:
                user_input = st.text_input(
                    "Your sentence", placeholder="Type an English sentence...",
                    label_visibility="collapsed", key="sentence_input",
                )
            with col2:
                submitted = st.form_submit_button("Check & Learn", **quiz.STRETCH_FORM)
        st.markdown('<div class="kbd-hint">Press Enter to submit</div>', unsafe_allow_html=True)
        hint_slot = st.empty()  # place for the 'type a sentence first' message

        # Keep the chat opened at the newest message after every reply (the message count makes the script new each time).
        # Roman Urdu: Har jawab ke baad chat sab se naye message par khulti hai (message ginti se script har baar nayi hoti hai).
        components.html(
            "<script>/*" + str(len(st.session_state.chat_history)) + "*/[0,150,500,1200].forEach(function(t){setTimeout(function(){"
            "var b=window.parent.document.querySelector('.st-key-chatbox');if(!b){return;}"
            "var els=[b].concat(Array.prototype.slice.call(b.querySelectorAll('div')));"
            "for(var i=0;i<els.length;i++){var s=window.parent.getComputedStyle(els[i]);"
            "if((s.overflowY==='auto'||s.overflowY==='scroll')&&els[i].scrollHeight>els[i].clientHeight){els[i].scrollTop=els[i].scrollHeight;}}"
            "},t);});</script>", height=0)

# Start the quiz from the in-chat offer (done outside the containers, like the sidebar button).
# Roman Urdu: Chat ke andar wali dawat se quiz shuru karo (containers se bahar, sidebar ke button ki tarah).
if take_quiz:
    quiz.start_quiz()

# MAIN FLOW when a sentence is submitted: (1) show it, (2) agent checks it and saves progress, (3) add Pro Tip, (4) decide on a quiz offer, (5) store the reply and rerun.
# Roman Urdu: ASAL FLOW jab jumla submit ho: (1) jumla dikhao, (2) agent check karke progress save karta hai, (3) Pro Tip lagao, (4) quiz ki dawat ka faisla, (5) jawab save karke page dobara chalao.
if submitted and user_input.strip():
    st.session_state.chat_history.append(("user", user_input, None))
    StreakTracker(st.session_state.agent.tracker.data_file).mark_today()  # remember today as a practice day

    typing_slot.markdown(
        user_row(user_input) + bot_row('<div class="typing"><span></span><span></span><span></span></div>'),
        unsafe_allow_html=True,
    )
    # The agent runs the NLP checks and returns {correct, issues}.
    # Roman Urdu: Agent NLP checks chalata hai aur {correct, issues} wapas deta hai.
    result = st.session_state.agent.process_message_detailed(user_input)
    # Pro Tip is only a suggestion; it never changes whether the sentence counts as correct.
    # Roman Urdu: Pro Tip sirf mashwara hai; is se jumla sahi ya ghalat hone par koi asar nahi parta.
    tip = vocabulary_tip(user_input)  # optional vocabulary Pro Tip (never affects correctness)
    if tip:
        st.session_state.tips[len(st.session_state.chat_history)] = tip  # index of the reply about to be added
    # Quiz offer rule: 3rd, 6th, 9th... error of the same type.
    # Roman Urdu: Quiz ki dawat ka usool: ek hi qism ki 3rd, 6th, 9th... ghalti par.
    if quiz.nudge_due(st.session_state.agent.tracker.records):
        st.session_state.nudges[len(st.session_state.chat_history)] = True  # offer the quiz under this reply

    if result["correct"]:
        st.session_state.chat_history.append(("assistant", [], True))
    else:
        st.session_state.chat_history.append(("assistant", result["issues"], False))

    st.session_state.just_submitted = True
    st.rerun()
# Empty box: ask the user to type something.
# Roman Urdu: Dabba khali ho to user se kuch likhne ko kaho.
elif submitted and not user_input.strip():
    hint_slot.markdown('<div class="empty-hint">Type a sentence before checking.</div>', unsafe_allow_html=True)
