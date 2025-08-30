# pages/0_Home.py
import streamlit as st
from datetime import datetime
from zoneinfo import ZoneInfo

st.set_page_config(page_title="Cricbuzz LiveStats — Home", page_icon="🏏", layout="wide")

st.title("🏏 Cricbuzz LiveStats — Home")
st.caption("Last opened: " + datetime.now(ZoneInfo("Asia/Kolkata")).strftime("%Y-%m-%d %H:%M:%S IST"))

st.write(
    "Welcome to **Cricbuzz LiveStats** — a Streamlit dashboard powered by Cricbuzz API (RapidAPI) and MySQL."
)
st.write("- 🟢 Live Match Page — live matches (teams, venue, status)")
st.write("- ⭐ Top Player Stats — player rankings by format")
st.write("- 📊 SQL Queries & Analytics — 25 preset SQL insights")
st.write("- 🛠 CRUD Operations — add/update/delete players (extend to matches)")

st.divider()

st.subheader("🚀 Quick Navigation")
st.page_link("pages/live_match.py", label="🟢 Live Match Page")
st.page_link("pages/Player_Stats.py", label="⭐ Top Player Stats")
st.page_link("pages/sql_analytics.py", label="📊 SQL Queries & Analytics")
st.page_link("pages/crud.py", label="🛠 CRUD Operations")

st.divider()


