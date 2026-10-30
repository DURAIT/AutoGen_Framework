"""
Weather News dashboard: AutoGen agent + DuckDuckGo search + Streamlit frontend.

Setup:
    pip install -U autogen-agentchat "autogen-ext[openai]" ddgs python-dotenv streamlit

Create a .env file next to this script containing:
    OPENAI_API_KEY=your-key-here

Run:
    streamlit run weather_news.py
"""

import asyncio
import html
import os
import re
from datetime import datetime

import streamlit as st
from autogen_agentchat.agents import AssistantAgent
from autogen_ext.models.openai import OpenAIChatCompletionClient
from ddgs import DDGS  # free, keyless DuckDuckGo search
from dotenv import load_dotenv

# Load OPENAI_API_KEY (and anything else) from the .env file.
load_dotenv()


# --------------------------------------------------------------------------
# Tool: a plain Python function. AutoGen reads its name, type hints and
# docstring to decide when to call it.
# --------------------------------------------------------------------------
def search_weather_news(query: str) -> str:
    """Search the web with DuckDuckGo for current weather conditions and weather news.

    Use this tool whenever you need up-to-date weather information for a city.
    Pass a focused search query such as "Chennai weather today" or
    "Chennai weather forecast news". Returns the top results as plain text,
    each with a title, a short snippet and a source URL.
    """
    try:
        results = DDGS().text(query, max_results=5)
    except Exception as exc:  # network errors, rate limits, etc.
        return f"Search failed: {exc}"

    if not results:
        return "No results found."

    lines = []
    for i, item in enumerate(results, start=1):
        title = item.get("title", "")
        snippet = item.get("body", "")
        url = item.get("href", "")
        lines.append(f"{i}. {title}\n   {snippet}\n   {url}")
    return "\n".join(lines)


# --------------------------------------------------------------------------
# Agent runner
# --------------------------------------------------------------------------
SYSTEM_MESSAGE = (
    "You are a Weather News assistant. For the city the user gives, "
    "call the search tool to find current weather and weather news. "
    "Reply in EXACTLY 3 short lines (one sentence each, no bullets, "
    "no numbering, no extra text): "
    "line 1 = current conditions and temperature, "
    "line 2 = today's outlook or forecast, "
    "line 3 = any notable weather news or alert "
    "(say 'No major weather alerts.' if none)."
)


def to_three_lines(text: str) -> list[str]:
    """Normalise the model reply into exactly 3 short lines."""
    bullet = re.compile(r"^\s*(?:[-*\u2022]|\d+[.)])\s*")
    lines = [bullet.sub("", ln).strip() for ln in text.splitlines() if ln.strip()]

    # If the model put everything in one paragraph, split by sentence.
    if len(lines) < 3:
        lines = [s.strip() for s in re.split(r"(?<=[.!?])\s+", " ".join(lines)) if s.strip()]

    lines = lines[:3]
    while len(lines) < 3:
        lines.append("No further details available.")
    return lines


async def get_weather_news(city: str) -> list[str]:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is missing. Add it to your .env file.")

    model_client = OpenAIChatCompletionClient(model="gpt-4o-mini", api_key=api_key)
    try:
        agent = AssistantAgent(
            name="weather_news_agent",
            model_client=model_client,
            tools=[search_weather_news],
            # Write an answer from the tool results instead of dumping raw output.
            reflect_on_tool_use=True,
            system_message=SYSTEM_MESSAGE,
        )
        result = await agent.run(task=f"Give me the weather news for {city}.")
        return to_three_lines(str(result.messages[-1].content))
    finally:
        # Always release the underlying HTTP client.
        await model_client.close()


# --------------------------------------------------------------------------
# Small helpers for the UI
# --------------------------------------------------------------------------
def pick_icon(text: str) -> str:
    t = text.lower()
    if "thunder" in t or "storm" in t:
        return "⛈️"
    if any(w in t for w in ("rain", "shower", "drizzle", "monsoon")):
        return "🌧️"
    if "snow" in t:
        return "❄️"
    if any(w in t for w in ("fog", "haze", "mist", "smog")):
        return "🌫️"
    if "partly" in t or "mostly sunny" in t:
        return "⛅"
    if "cloud" in t or "overcast" in t:
        return "☁️"
    if any(w in t for w in ("sunny", "clear", "sun")):
        return "☀️"
    return "🌤️"


def extract_temp(text: str) -> str:
    m = re.search(r"(-?\d{1,3})\s*(?:°|º|degrees?)?\s*(?:C|F)\b", text)
    return m.group(1) if m else "--"


def extract_unit(text: str) -> str:
    m = re.search(r"-?\d{1,3}\s*(?:°|º|degrees?)?\s*(C|F)\b", text)
    return m.group(1) if m else "C"


def run_search(city: str) -> None:
    city = city.strip()
    if not city:
        st.warning("Please enter a city.")
        return
    try:
        with st.spinner(f"Fetching weather news for {city}..."):
            st.session_state["lines"] = asyncio.run(get_weather_news(city))
            st.session_state["city"] = city
            st.session_state["time"] = datetime.now().strftime("%A, %d %B · %I:%M %p")
    except Exception as exc:
        st.session_state.pop("lines", None)
        st.error(f"Something went wrong: {exc}")


# --------------------------------------------------------------------------
# Streamlit dashboard
# --------------------------------------------------------------------------
st.set_page_config(page_title="Weather News", page_icon="🌦️", layout="wide")

st.markdown(
    """
    <style>
      :root { color-scheme: dark; }

      .stApp {
        background:
          radial-gradient(900px 500px at 10% -10%, rgba(56,189,248,0.22), transparent 60%),
          radial-gradient(800px 500px at 100% 0%, rgba(99,102,241,0.20), transparent 60%),
          linear-gradient(180deg, #0b1226 0%, #070b18 100%);
        color: #e8eefc;
      }
      header[data-testid="stHeader"] { background: transparent; }
      .block-container { max-width: 1100px; padding-top: 2rem; }

      /* ---------- Title ---------- */
      .title {
        text-align: center; font-size: 2.4rem; font-weight: 800; letter-spacing: -0.5px;
        background: linear-gradient(90deg, #7dd3fc, #a5b4fc, #7dd3fc);
        -webkit-background-clip: text; background-clip: text;
        -webkit-text-fill-color: transparent; margin: 0;
      }
      .subtitle { text-align: center; color: #8fa3c8; margin: 0.2rem 0 1.4rem; font-size: 0.95rem; }

      /* ---------- Search box (visible text on dark glass) ---------- */
      div[data-testid="stForm"] {
        background: rgba(255,255,255,0.04);
        border: 1px solid rgba(255,255,255,0.10);
        border-radius: 22px;
        padding: 0.9rem 1rem;
        backdrop-filter: blur(8px);
      }
      /* 1) make every layer inside the text input transparent ... */
      div[data-testid="stTextInput"],
      div[data-testid="stTextInput"] div,
      div[data-testid="stTextInput"] input {
        background: transparent !important;
        background-color: transparent !important;
      }
      /* 2) ... then paint ONE dark pill on the BaseWeb wrapper */
      div[data-testid="stTextInput"] div[data-baseweb="input"] {
        background-color: #14203b !important;
        border: 1px solid rgba(125,211,252,0.35) !important;
        border-radius: 999px !important;
        overflow: hidden;
      }
      div[data-testid="stTextInput"] div[data-baseweb="input"]:focus-within {
        border-color: #38bdf8 !important;
        box-shadow: 0 0 0 3px rgba(56,189,248,0.25) !important;
      }
      div[data-testid="stTextInput"] input {
        color: #ffffff !important;
        -webkit-text-fill-color: #ffffff !important;
        caret-color: #38bdf8 !important;
        font-size: 1.05rem !important;
        padding: 0.8rem 1.3rem !important;
      }
      div[data-testid="stTextInput"] input::placeholder {
        color: #8fa3c8 !important;
        -webkit-text-fill-color: #8fa3c8 !important;
        opacity: 1 !important;
      }
      div[data-testid="stTextInput"] input:-webkit-autofill {
        -webkit-text-fill-color: #ffffff !important;
        box-shadow: 0 0 0 1000px #14203b inset !important;
      }

      /* ---------- Buttons (Search + city chips) ---------- */
      div[data-testid="stFormSubmitButton"] button {
        border-radius: 999px; height: 3rem; font-weight: 600;
        border: none; color: #04121f;
        background: linear-gradient(90deg, #38bdf8, #818cf8);
      }
      div[data-testid="stFormSubmitButton"] button:hover { filter: brightness(1.1); color: #04121f; }
      div[data-testid="stButton"] button {
        border-radius: 999px; font-size: 0.85rem;
        background: rgba(255,255,255,0.06); color: #cfe0ff;
        border: 1px solid rgba(255,255,255,0.14);
      }
      div[data-testid="stButton"] button:hover {
        border-color: #38bdf8; color: #ffffff; background: rgba(56,189,248,0.15);
      }

      /* ---------- Cards ---------- */
      @keyframes rise { from {opacity:0; transform: translateY(14px);} to {opacity:1; transform:none;} }
      .card {
        background: linear-gradient(160deg, rgba(255,255,255,0.09), rgba(255,255,255,0.025));
        border: 1px solid rgba(255,255,255,0.12);
        border-radius: 22px;
        padding: 1.3rem 1.5rem;
        box-shadow: 0 10px 34px rgba(0,0,0,0.38);
        backdrop-filter: blur(10px);
        animation: rise .55s ease both;
        transition: transform .2s ease, border-color .2s ease;
        height: 100%;
      }
      .card:hover { transform: translateY(-3px); border-color: rgba(125,211,252,0.45); }
      .card h4 {
        margin: 0 0 0.8rem 0; font-size: 0.78rem; color: #8fa3c8;
        font-weight: 700; text-transform: uppercase; letter-spacing: 1.2px;
      }
      .card p { margin: 0; font-size: 1.08rem; line-height: 1.6; color: #f1f5ff; }

      .hero {
        background: linear-gradient(160deg, rgba(56,189,248,0.35), rgba(30,64,175,0.18) 70%);
        text-align: center; min-height: 100%;
      }
      .hero .icon { font-size: 3.6rem; line-height: 1; margin-top: .2rem; filter: drop-shadow(0 6px 14px rgba(0,0,0,.4)); }
      .hero .temp { font-size: 5rem; font-weight: 800; line-height: 1.05; color: #fff; }
      .hero .temp span { font-size: 2rem; font-weight: 600; color: #bae6fd; vertical-align: top; margin-left: 2px; }
      .hero p { font-size: 1rem; color: #dbeafe; margin-top: .6rem; }

      .alert-calm   { border-left: 4px solid #34d399; }
      .alert-active { border-left: 4px solid #f87171; background: linear-gradient(160deg, rgba(248,113,113,0.22), rgba(255,255,255,0.02)); }
      .outlook      { border-left: 4px solid #818cf8; }

      .pill {
        display: inline-block; padding: .25rem .8rem; border-radius: 999px; font-size: .8rem;
        background: rgba(255,255,255,0.08); border: 1px solid rgba(255,255,255,0.14); color: #bcd0f5;
      }
      .city { text-align: center; margin: 1.6rem 0 1.1rem; animation: rise .45s ease both; }
      .city .name { font-size: 1.9rem; font-weight: 800; color: #fff; }
      .city .when { margin-top: .35rem; }

      .summary p { font-size: 1rem; color: #d3e2ff; line-height: 1.8; }
      .footer { text-align: center; color: #62749a; font-size: .8rem; margin-top: 2rem; }

      /* Info / warning / error boxes */
      div[data-testid="stAlert"] { background: rgba(255,255,255,0.06); border-radius: 14px; }
      div[data-testid="stAlert"] * { color: #dbe7ff !important; }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown("<p class='title'>🌦️ Weather News</p>", unsafe_allow_html=True)
st.markdown(
    "<p class='subtitle'>Live weather snapshot for any city, in 3 short lines</p>",
    unsafe_allow_html=True,
)

# Search bar (form so pressing Enter works too)
with st.form("city_form", clear_on_submit=False):
    col_in, col_btn = st.columns([5, 1])
    city_input = col_in.text_input(
        "City",
        placeholder="🔍  Enter a city, e.g. Chennai, Tamil Nadu, India",
        label_visibility="collapsed",
    )
    submitted = col_btn.form_submit_button("Search", use_container_width=True)

if submitted:
    run_search(city_input)

# Quick-pick city chips
QUICK_CITIES = ["Chennai", "Mumbai", "Delhi", "Bengaluru", "London", "New York"]
chip_cols = st.columns(len(QUICK_CITIES))
for col, name in zip(chip_cols, QUICK_CITIES):
    if col.button(name, key=f"chip_{name}", use_container_width=True):
        run_search(name)

if "lines" in st.session_state:
    raw = st.session_state["lines"]
    l1, l2, l3 = (html.escape(x) for x in raw)

    icon = pick_icon(f"{raw[0]} {raw[1]}")
    temp = extract_temp(raw[0])
    unit = extract_unit(raw[0])
    calm = raw[2].strip().lower().startswith("no")
    alert_cls = "alert-calm" if calm else "alert-active"
    alert_icon = "✅" if calm else "🚨"

    st.markdown(
        f"""
        <div class='city'>
          <div class='name'>📍 {html.escape(st.session_state['city'])}</div>
          <div class='when'><span class='pill'>🕒 {html.escape(st.session_state['time'])}</span></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    left, right = st.columns([1, 2], gap="medium")

    # Line 1 -> big "Current Overview" card
    left.markdown(
        f"""
        <div class='card hero'>
          <h4>Current Overview</h4>
          <div class='icon'>{icon}</div>
          <div class='temp'>{temp}<span>°{unit}</span></div>
          <p>{l1}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Lines 2 and 3 -> stacked cards
    right.markdown(
        f"""
        <div class='card outlook' style='margin-bottom:1rem;'>
          <h4>🕒 Today's Outlook</h4>
          <p>{l2}</p>
        </div>
        <div class='card {alert_cls}'>
          <h4>{alert_icon} News &amp; Alerts</h4>
          <p>{l3}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)
    st.markdown(
        f"""
        <div class='card summary'>
          <h4>✨ AI Weather Summary</h4>
          <p>{l1}<br>{l2}<br>{l3}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
else:
    st.markdown(
        """
        <div class='card' style='text-align:center; margin-top:1.5rem;'>
          <div style='font-size:3rem;'>🌍</div>
          <h4 style='margin-top:.6rem;'>Get started</h4>
          <p>Type a city above or tap a quick pick to see today's weather in 3 short lines.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.markdown(
    "<div class='footer'>Powered by AutoGen · DuckDuckGo search · Streamlit</div>",
    unsafe_allow_html=True,
)
