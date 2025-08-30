# pages/top_player_stats.py


import os
import json
import requests
import pandas as pd
import streamlit as st
from dotenv import load_dotenv

# ──────────────────────────────────────────────────────────────────────────────
# Setup
# ──────────────────────────────────────────────────────────────────────────────
st.set_page_config(page_title="Top Player Stats", page_icon="⭐", layout="wide")
st.title("⭐ Top Player Stats")

load_dotenv()
API_KEY  = os.getenv("RAPIDAPI_KEY")
API_HOST = os.getenv("RAPIDAPI_HOST", "cricbuzz-cricket.p.rapidapi.com")

if not API_KEY:
    st.error("No API key found. Please add RAPIDAPI_KEY to your .env file.")
    st.stop()

HEADERS = {"X-RapidAPI-Key": API_KEY, "X-RapidAPI-Host": API_HOST}

# ──────────────────────────────────────────────────────────────────────────────
# Small helpers
# ──────────────────────────────────────────────────────────────────────────────
def _get_json(url: str, params: dict | None = None):
    """GET and parse JSON with a short, friendly error message."""
    try:
        r = requests.get(url, headers=HEADERS, params=params, timeout=20)
    except requests.RequestException as e:
        return None, f"Network error: {e}"
    if r.status_code != 200:
        # Show only a small preview of body to avoid dumping JSON
        return None, f"API error {r.status_code}: {r.text[:160]}"
    try:
        return r.json(), None
    except Exception:
        try:
            return json.loads(r.text), None
        except Exception:
            return None, "Server did not return valid JSON."

def _safe_df(items):
    if not isinstance(items, list) or not items:
        return pd.DataFrame()
    try:
        return pd.DataFrame(items)
    except Exception:
        return pd.DataFrame()

def _normalize_rankings(data: dict) -> pd.DataFrame:
    # support multiple mirrors: "rank", "ranks", "list"
    items = data.get("rank") or data.get("ranks") or data.get("list") or []
    df = _safe_df(items)
    if df.empty:
        return df
    order = [c for c in ["rank", "name", "country", "rating", "points"] if c in df.columns]
    return df[order] if order else df

# Cache by host/key so swapping creds actually refreshes
@st.cache_data(ttl=60)
def fetch_rankings(host: str, key: str, endpoint: str, fmt: str):
    url = f"https://{host}/stats/v1/rankings/{endpoint}"
    headers = {"X-RapidAPI-Key": key, "X-RapidAPI-Host": host}
    try:
        r = requests.get(url, headers=headers, params={"formatType": fmt}, timeout=20)
        if r.status_code != 200:
            return None, f"API error {r.status_code}: {r.text[:160]}"
        return r.json(), None
    except requests.RequestException as e:
        return None, f"Network error: {e}"

# Robust player search: try several known paths and result shapes
@st.cache_data(ttl=60)
def search_players(host: str, key: str, name: str):
    base = f"https://{host}"
    candidates = [
        (f"{base}/stats/v1/player/search", {"plrN": name}),   # common on many mirrors
        (f"{base}/stats/v1/search",         {"q": name}),     # alt
        (f"{base}/search/v1",               {"q": name}),     # alt
        (f"{base}/search/v2",               {"query": name}), # alt
    ]
    headers = {"X-RapidAPI-Key": key, "X-RapidAPI-Host": host}
    tried = 0
    for url, params in candidates:
        tried += 1
        try:
            r = requests.get(url, headers=headers, params=params, timeout=20)
            if r.status_code != 200:
                continue
            try:
                data = r.json()
            except Exception:
                data = json.loads(r.text)

            items = (
                data.get("player") or data.get("players") or data.get("list")
                or data.get("results") or data.get("result") or []
            )
            if isinstance(items, list) and items:
                # map into {id, name, country}
                out = []
                for p in items:
                    pid = p.get("id") or p.get("playerId") or p.get("idPlayer") or p.get("pid")
                    pname = p.get("name") or p.get("fullName") or p.get("playerName")
                    pcountry = p.get("country") or p.get("teamName") or p.get("team") or ""
                    if pid and pname:
                        out.append({"id": str(pid), "name": str(pname), "country": str(pcountry)})
                if out:
                    return out, None
        except requests.RequestException:
            continue
        except Exception:
            continue
    if tried == 0:
        return None, "Could not reach search service."
    return [], None  # reached but found nothing

@st.cache_data(ttl=60)
def fetch_profile(host: str, key: str, player_id: str):
    base = f"https://{host}"
    headers = {"X-RapidAPI-Key": key, "X-RapidAPI-Host": host}
    # profile endpoints we can try
    prof_candidates = [
        f"{base}/stats/v1/player/{player_id}",  # common
        f"{base}/player/v1/{player_id}",        # alt on some mirrors
    ]
    for url in prof_candidates:
        data, err = _get_json(url)
        if data and not err:
            return data, None
    return None, "Profile not available on this mirror."

@st.cache_data(ttl=60)
def fetch_career(host: str, key: str, player_id: str):
    base = f"https://{host}"
    url = f"{base}/stats/v1/player/{player_id}/career"
    return _get_json(url)

# ──────────────────────────────────────────────────────────────────────────────
# Rankings section (simple)
# ──────────────────────────────────────────────────────────────────────────────
st.subheader("🏆 Rankings")

c1, c2 = st.columns(2)
with c1:
    role = st.selectbox("Role", ["Batsmen", "Bowlers"])
with c2:
    fmt_label = st.selectbox("Format", ["Test", "ODI", "T20I"])

fmt_map = {"Test": "test", "ODI": "odi", "T20I": "t20i"}
fmt = fmt_map[fmt_label]
endpoint = "batsmen" if role == "Batsmen" else "bowlers"

with st.spinner("Loading rankings…"):
    data, err = fetch_rankings(API_HOST, API_KEY, endpoint, fmt)

if err:
    st.error(err)
else:
    df = _normalize_rankings(data or {})
    if df.empty:
        st.info("No ranking data available right now.")
    else:
        st.dataframe(df, use_container_width=True, hide_index=True)

st.divider()

# ──────────────────────────────────────────────────────────────────────────────
# Player Stat Loader (search → profile + career)
# ──────────────────────────────────────────────────────────────────────────────
st.subheader("🧍 Player Stat Loader")

with st.form("player_search", clear_on_submit=False):
    query = st.text_input("Type player name (e.g., Virat Kohli)", "")
    submitted = st.form_submit_button("Search")

players = []
if submitted and query.strip():
    with st.spinner("Searching players…"):
        players, err = search_players(API_HOST, API_KEY, query.strip())
    if err:
        st.error(err)
    elif players == []:
        st.warning("No players found for that name.")

if players:
    labels = [f"{p['name']} ({p['country']})" if p['country'] else p['name'] for p in players]
    pick = st.selectbox("Select a player", labels)
    chosen = players[labels.index(pick)]
    pid = chosen["id"]

    if st.button("Load Player Stats"):
        # 1) Profile
        with st.spinner("Loading player profile…"):
            profile, perr = fetch_profile(API_HOST, API_KEY, pid)

        # 2) Career (separate endpoint; sometimes profile already contains it)
        with st.spinner("Loading career stats…"):
            career, cerr = fetch_career(API_HOST, API_KEY, pid)

        # Render Profile (friendly table of common fields)
        st.markdown("#### 👤 Profile")
        rows = []
        if isinstance(profile, dict):
            rows.append(("Name", profile.get("name") or profile.get("fullName")))
            rows.append(("Country/Team", profile.get("country") or profile.get("teamName")))
            rows.append(("Role", profile.get("role") or profile.get("playingRole")))
            rows.append(("Batting Style", profile.get("battingStyle")))
            rows.append(("Bowling Style", profile.get("bowlingStyle")))
            rows.append(("DOB", profile.get("dob")))
            rows.append(("Bio", profile.get("bio")))
        rows = [(k, v) for (k, v) in rows if v]
        if rows:
            st.table(pd.DataFrame(rows, columns=["Field", "Value"]))
        else:
            st.info("Basic profile details not available.")

        # If separate career call failed, try to pull from profile
        if (not career or cerr) and isinstance(profile, dict) and "career" in profile:
            career = profile["career"]
            cerr = None

        # Render Career as one or more tables if present
        st.markdown("#### 📈 Career Stats")
        def _render_career(obj):
            if isinstance(obj, list):
                dfc = _safe_df(obj)
                if not dfc.empty:
                    st.dataframe(dfc, use_container_width=True, hide_index=True)
                    return True
                return False
            if isinstance(obj, dict):
                shown_any = False
                for k, v in obj.items():
                    if isinstance(v, list) and v:
                        dfk = _safe_df(v)
                        if not dfk.empty:
                            st.markdown(f"**{k.capitalize()}**")
                            st.dataframe(dfk, use_container_width=True, hide_index=True)
                            shown_any = True
                return shown_any
            return False

        if not career or cerr:
            st.info("Career data not available.")
        else:
            shown = _render_career(career)
            if not shown:
                st.info("Career data not available in a tabular form.")
