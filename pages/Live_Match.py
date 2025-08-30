# pages/live_match.py
import os
import json
import requests
import streamlit as st
from dotenv import load_dotenv
from datetime import datetime
from zoneinfo import ZoneInfo

# —————————————————— Page setup
st.set_page_config(page_title="Live / Recent Matches", page_icon="🟢", layout="wide")
st.title("🟢 Live Match Page")

# top bar (refresh + timestamp)
left, right = st.columns([1, 3])
with left:
    if st.button("🔄 Refresh data"):
        st.cache_data.clear()
        st.rerun()
with right:
    now_ist = datetime.now(ZoneInfo("Asia/Kolkata")).strftime("%Y-%m-%d %H:%M:%S IST")
    st.caption(f"Last updated: {now_ist}")

# —————————————————— Env & API
load_dotenv()
API_KEY = os.getenv("RAPIDAPI_KEY")
API_HOST = os.getenv("RAPIDAPI_HOST", "cricbuzz-cricket.p.rapidapi.com")

if not API_KEY:
    st.error("No API key found. Add RAPIDAPI_KEY to your .env file.")
    st.stop()

HEADERS = {
    "X-RapidAPI-Key": API_KEY,
    "X-RapidAPI-Host": API_HOST,
}

LIVE_URL    = f"https://{API_HOST}/matches/v1/live"
RECENT_URL  = f"https://{API_HOST}/matches/v1/recent"
MCENTER_URL = f"https://{API_HOST}/mcenter/v1/{{match_id}}"

# —————————————————— Small utils
def g(d, *ks, default=None):
    """Very small safe-get for nested dicts. I use this everywhere."""
    cur = d
    for k in ks:
        if not isinstance(cur, dict) or k not in cur:
            return default
        cur = cur[k]
    return cur

def show_innings(inn: dict) -> str:
    """Return 'runs/wkts (overs)' or empty if it doesn't make sense."""
    if not isinstance(inn, dict) or not inn:
        return ""
    runs = inn.get("runs")
    wkts = inn.get("wickets")
    overs = inn.get("overs")
    if overs is None:
        # payloads use balls; convert to x.y where y is balls%6
        balls = inn.get("balls")
        overs = f"{balls//6}.{balls%6}" if isinstance(balls, int) else "-"
    if runs is None and wkts is None:
        return ""
    return f"{runs}/{wkts} ({overs})" if wkts is not None else f"{runs} ({overs})"

def guess_format(info: dict, fallback="UNKNOWN") -> str:
    """I don't trust one field for format; check a couple."""
    s = (info or {}).get("matchFormat")
    if isinstance(s, str):
        u = s.upper()
        if "TEST" in u: return "TEST"
        if "ODI"  in u: return "ODI"
        if "T20"  in u: return "T20"
    for k in ("matchDesc", "stateTitle", "seriesName"):
        s = (info or {}).get(k)
        if isinstance(s, str):
            u = s.upper()
            if "TEST" in u: return "TEST"
            if "ODI"  in u: return "ODI"
            if "T20"  in u: return "T20"
    return fallback

def overs_to_float(overs):
    if overs is None:
        return -1.0
    if isinstance(overs, (int, float)):
        return float(overs)
    try:
        s = str(overs)
        if "." in s:
            o, b = s.split(".")
            return float(o) + (int(b) / 6.0)
        return float(s)
    except:
        return -1.0

def _extract_extras(inn: dict):
    """Extras can be in a few shapes; try to normalize to a total."""
    if not isinstance(inn, dict):
        return "—"
    if isinstance(inn.get("extras"), (int, float, str)):
        return inn["extras"]
    if isinstance(inn.get("extraRuns"), (int, float, str)):
        return inn["extraRuns"]
    ed = inn.get("extras") if isinstance(inn.get("extras"), dict) else inn.get("extraDetail")
    if isinstance(ed, dict):
        total = 0
        for k in ("byes", "legByes", "wides", "noBalls", "penalty"):
            v = ed.get(k)
            if isinstance(v, (int, float)):
                total += v
        return total if total > 0 else "—"
    return "—"

def pick_current_innings(score: dict, t1s: str, t2s: str):
    """
    Try to guess the 'current' innings:
    - prefer second innings if present
    - then fallback to first
    - also consider inningsScoreList if available
    """
    cands = []
    t1i1 = g(score, "team1Score", "inngs1") or {}
    t1i2 = g(score, "team1Score", "inngs2") or {}
    t2i1 = g(score, "team2Score", "inngs1") or {}
    t2i2 = g(score, "team2Score", "inngs2") or {}

    for bt, inn in [(t1s, t1i2), (t2s, t2i2), (t1s, t1i1), (t2s, t2i1)]:
        if inn:
            cands.append((overs_to_float(inn.get("overs")), bt, inn))

    isl = score.get("inningsScoreList")
    if isinstance(isl, list):
        for inn in isl:
            if not isinstance(inn, dict):
                continue
            bt_id = inn.get("batTeamId")
            bt = t1s if bt_id == 1 else (t2s if bt_id == 2 else None)
            cands.append((overs_to_float(inn.get("overs")), bt, inn))

    if not cands:
        return "—", "—", {}

    cands.sort(key=lambda x: x[0], reverse=True)
    _, bat_team, inn = cands[0]
    bowl_team = t2s if bat_team == t1s else t1s
    return bat_team or "—", bowl_team or "—", inn or {}

@st.cache_data(ttl=60)
def fetch_json(url: str, headers: dict):
    r = requests.get(url, headers=headers, timeout=15)
    return r.status_code, r.text

@st.cache_data(ttl=60)
def fetch_mcenter(match_id: int):
    url = MCENTER_URL.format(match_id=match_id)
    r = requests.get(url, headers=HEADERS, timeout=15)
    return r.status_code, r.text

def collect_matches(root: dict):
    """Flatten the weird 'typeMatches -> seriesMatches -> seriesAdWrapper' thing."""
    flat = []
    for bucket in (root.get("typeMatches") or []):
        for s in (bucket.get("seriesMatches") or []):
            wrap = s.get("seriesAdWrapper")
            if not isinstance(wrap, dict):
                continue
            series_name = wrap.get("seriesName", "Series")
            for m in (wrap.get("matches") or []):
                info  = m.get("matchInfo")  or {}
                score = m.get("matchScore") or {}
                match_id = info.get("matchId")
                t1 = g(info, "team1", "teamName") or g(info, "team1", "teamSName") or "Team 1"
                t2 = g(info, "team2", "teamName") or g(info, "team2", "teamSName") or "Team 2"
                fmt = guess_format(info)
                label = f"{t1} vs {t2} — {series_name} ({fmt})"
                flat.append({
                    "label": label,
                    "match_id": match_id,
                    "series": series_name,
                    "format": fmt,
                    "info": info,
                    "score": score,
                })
    return flat

# —————————————————— Fetch live, else recent
with st.spinner("📡 Fetching matches…"):
    st.caption(f"Using host: `{API_HOST}` | key: `{API_KEY[:6]}…`")
    code_live, txt_live = fetch_json(LIVE_URL, HEADERS)
    data_live = None
    if code_live == 200:
        try:
            data_live = json.loads(txt_live)
        except:
            data_live = None  # if payload is trash, just ignore

matches = collect_matches(data_live or {}) if data_live else []
mode = "live"

# no live, try recent
if not matches:
    st.warning("⏸️ No live matches right now. Showing **Recent Matches** instead.")
    code_recent, txt_recent = fetch_json(RECENT_URL, HEADERS)
    data_recent = None
    if code_recent == 200:
        try:
            data_recent = json.loads(txt_recent)
        except:
            data_recent = None
    matches = collect_matches(data_recent or {})
    mode = "recent"


if not matches:
    if code_live != 200:
        st.error(f"Live API error {code_live}. Preview: {txt_live[:300]}")
    elif 'code_recent' in locals() and code_recent != 200:
        st.error(f"Recent API error {code_recent}. Preview: {txt_recent[:300]}")
    else:
        st.info("No matches to display.")
    st.stop()

# —————————————————— Selector
choice = st.selectbox(
    "🎯 Select a " + ("live match" if mode == "live" else "recent match"),
    [x["label"] for x in matches],
    index=0
)
chosen = next(x for x in matches if x["label"] == choice)

# —————————————————— Details
info        = chosen["info"]
score       = chosen["score"]
fmt         = chosen["format"]
series_name = chosen["series"]
match_id    = chosen["match_id"]

t1_obj = info.get("team1") or {}
t2_obj = info.get("team2") or {}
t1  = t1_obj.get("teamName") or t1_obj.get("teamSName") or "Team 1"
t2  = t2_obj.get("teamName") or t2_obj.get("teamSName") or "Team 2"
t1s = t1_obj.get("teamSName") or t1
t2s = t2_obj.get("teamSName") or t2

ground  = g(info, "venueInfo", "ground",  default="-")
city    = g(info, "venueInfo", "city",    default="")
country = g(info, "venueInfo", "country", default="")
status  = info.get("status") or info.get("state") or "-"

# who’s batsman right now (best guess)
batting_team, bowling_team, current_inn = pick_current_innings(score, t1s, t2s)

batter_name = (
    g(score, "batsmanStriker", "batName")
    or g(score, "batsman", "name")
    or g(score, "batsmanNonStriker", "batName")
    or "—"
)
bowler_name = (
    g(score, "bowlerStriker", "bowlName")
    or g(score, "bowler", "name")
    or g(score, "bowlerNonStriker", "bowlName")
    or "—"
)

wickets  = current_inn.get("wickets", "—")
overs    = current_inn.get("overs", "—")
run_rate = current_inn.get("runRate") or current_inn.get("rr") or "—"
extras   = _extract_extras(current_inn)

def _score_lines():
    """Build simple 'TEAM: 123/4 (12.3)' lines from whatever is available."""
    out = []
    t1i1 = g(score, "team1Score", "inngs1")
    t1i2 = g(score, "team1Score", "inngs2")
    t2i1 = g(score, "team2Score", "inngs1")
    t2i2 = g(score, "team2Score", "inngs2")

    if isinstance(t1i1, dict) and t1i1:
        out.append(f"**{t1s}**: {show_innings(t1i1)}")
    if isinstance(t1i2, dict) and t1i2:
        out.append(f"**{t1s}** (Inns 2): {show_innings(t1i2)}")
    if isinstance(t2i1, dict) and t2i1:
        out.append(f"**{t2s}**: {show_innings(t2i1)}")
    if isinstance(t2i2, dict) and t2i2:
        out.append(f"**{t2s}** (Inns 2): {show_innings(t2i2)}")

    isl = score.get("inningsScoreList")
    if isinstance(isl, list):
        for inn in isl[:2]:
            if not isinstance(inn, dict):
                continue
            runs = inn.get("score")
            wkts = inn.get("wkts")
            ov   = inn.get("overs")
            team_short = inn.get("batTeamShortName") or inn.get("batTeamName")
            if runs is not None and ov is not None and team_short:
                line = f"**{team_short}**: {runs}/{wkts if wkts is not None else '-'} ({ov})"
                if line not in out:
                    out.append(line)
    return out

score_html = "<br>".join(_score_lines()) if _score_lines() else "—"

# ———————— Render
st.markdown(f"## 🏏 {t1} 🆚 {t2}")
st.caption(series_name + (" · LIVE" if mode == "live" else " · RECENT"))

c1, c2 = st.columns(2)
with c1:
    st.write(f"**📝 Format:** {fmt}")
    where = ", ".join([x for x in [city, country] if x]) or "—"
    st.write(f"**📍 Venue:** {where}")
with c2:
    st.write(f"**🏟 Stadium:** {ground or '—'}")
    st.write(f"**📌 Status:** {status}")

st.divider()
st.markdown("### 🧾 Live Snapshot")
snap_l, snap_r = st.columns(2)
with snap_l:
    st.write(f"**🏏 Batting team:** {batting_team}")
    st.write(f"**🧢 Batter (on strike):** {batter_name}")
    st.write(f"**🧱 Wickets:** {wickets}")
    st.write(f"**🚀 Run rate:** {run_rate}")
with snap_r:
    st.write(f"**🎯 Bowling team:** {bowling_team}")
    st.write(f"**🎯 Bowler (on strike):** {bowler_name}")
    st.write(f"**⏱ Overs:** {overs}")
st.write(f"**➕ Extras:** {extras}")

st.markdown("### 📊 Current Score")
st.markdown(score_html, unsafe_allow_html=True)

# quick links
live_scores_url = "https://www.cricbuzz.com/cricket-match/live-scores"
q = f"{t1} vs {t2} {series_name} cricbuzz"
search_link = f"https://www.cricbuzz.com/search?q={q.replace(' ', '%20')}"
lnk1, lnk2 = st.columns(2)
with lnk1:
    st.link_button("🟥 Live Cricket Scores (Cricbuzz)", live_scores_url, use_container_width=True)
with lnk2:
    st.link_button("🔎 Find this match on Cricbuzz", search_link, use_container_width=True)

# ————————— Scorecard 
st.divider()
st.markdown("### 📋 Scorecard")
if match_id and st.button("Load scorecard"):
    with st.spinner("Loading scorecard…"):
        sc_code, sc_text = fetch_mcenter(match_id)

    if sc_code != 200:
        st.error(f"API error {sc_code}")
        st.code(sc_text[:400])
    else:
        try:
            sc = json.loads(sc_text)
        except:
            sc = None

        if not sc or "scoreCard" not in sc:
            st.info("No scorecard available yet.")
        else:
            score_cards = sc.get("scoreCard") or []

            # First Innings — Batting
            if len(score_cards) >= 1:
                c1_sc = score_cards[0] or {}
                st.markdown("#### 🥇 First Innings — Batting")

                rows = []
                bd = g(c1_sc, "batTeamDetails", "batsmenData") or {}
                if isinstance(bd, dict):
                    for b in bd.values():
                        rows.append({
                            "Batsman": b.get("batName"),
                            "Runs": b.get("runs"),
                            "Balls": b.get("balls"),
                            "4s": b.get("fours"),
                            "6s": b.get("sixes"),
                            "Status": b.get("outDesc") or "not out",
                        })

                bl = g(c1_sc, "batTeamDetails", "batsmen") or []
                if isinstance(bl, list):
                    for b in bl:
                        rows.append({
                            "Batsman": b.get("name") or b.get("batName"),
                            "Runs": b.get("r") or b.get("runs"),
                            "Balls": b.get("b") or b.get("balls"),
                            "4s": b.get("4s") or b.get("fours"),
                            "6s": b.get("6s") or b.get("sixes"),
                            "Status": b.get("dismissal") or b.get("outDesc") or "not out",
                        })

                if rows:
                    import pandas as pd
                    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

                ytb = (
                    g(c1_sc, "batTeamDetails", "yetToBat")
                    or g(c1_sc, "batTeamDetails", "didNotBat")
                    or g(c1_sc, "batTeamDetails", "dnb")
                    or g(c1_sc, "batTeamDetails", "nextBatsmen")
                    or g(c1_sc, "didNotBatList")
                )
                if isinstance(ytb, list) and ytb:
                    names = []
                    for v in ytb:
                        if isinstance(v, str):
                            names.append(v)
                        elif isinstance(v, dict):
                            names.append(v.get("name") or v.get("batName") or "")
                    names = [n for n in names if n]
                    if names:
                        st.caption("🧑‍⚖️ **Yet to bat:** " + ", ".join(names))

            # Second Innings — Bowling
            if len(score_cards) >= 2:
                c2_sc = score_cards[1] or {}
                st.markdown("#### 🥈 Second Innings — Bowling")

                bowl_rows = []
                bdict = g(c2_sc, "bowlTeamDetails", "bowlersData") or {}
                if isinstance(bdict, dict):
                    for b in bdict.values():
                        bowl_rows.append({
                            "Bowler": b.get("bowlName"),
                            "Runs": b.get("runs"),
                            "Wickets": b.get("wickets"),
                            "No-balls": b.get("noBalls") or b.get("nb") or 0,
                        })

                blist = g(c2_sc, "bowlTeamDetails", "bowlers") or []
                if isinstance(blist, list):
                    for b in blist:
                        bowl_rows.append({
                            "Bowler": b.get("name") or b.get("bowlName"),
                            "Runs": b.get("r") or b.get("runs"),
                            "Wickets": b.get("w") or b.get("wickets"),
                            "No-balls": b.get("nb") or b.get("noBalls") or 0,
                        })

                if bowl_rows:
                    import pandas as pd
                    st.dataframe(pd.DataFrame(bowl_rows), use_container_width=True, hide_index=True)
                else:
                    st.info("Bowling data not available for second innings yet.")
