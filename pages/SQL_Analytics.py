# pages/sql_analytics.py
import os, sys
import streamlit as st
import pandas as pd
from datetime import datetime
from zoneinfo import ZoneInfo

# Ensure we can import from project root (..)
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from utils.db_connection import run_query

st.set_page_config(page_title="SQL Analytics", page_icon="📊", layout="wide")
st.title("📊 SQL Queries & Analytics")

st.caption(
    "Note: Some advanced queries need extra columns/tables; if one errors, "
    "check the note in its title for what to add."
)

# -----------------------
# Query Catalog (25 items)
# -----------------------
QUERY_MAP = {
    # BEGINNER (1–8)
    "1) Players from India (name, role, batting, bowling)": """
        SELECT p.full_name, p.role, p.batting_style, p.bowling_style
        FROM players p
        JOIN teams t ON p.team_id = t.team_id
        WHERE t.country = 'India'
        ORDER BY p.full_name;
    """,

    "2) Matches in last 30 days (desc, teams, venue, date) — most recent first": """
        SELECT CONCAT(m.series_name, ' - ', m.match_type) AS match_desc,
               t1.team_name AS team1, t2.team_name AS team2,
               CONCAT(v.name, ', ', v.city) AS venue,
               m.match_date, m.status
        FROM matches m
        JOIN teams t1 ON m.team1_id = t1.team_id
        JOIN teams t2 ON m.team2_id = t2.team_id
        JOIN venues v ON m.venue_id = v.venue_id
        WHERE m.match_date >= DATE_SUB(NOW(), INTERVAL 30 DAY)
        ORDER BY m.match_date DESC;
    """,

    "3) Top 10 ODI run scorers (approx avg via runs/matches, 100s via runs>=100)": """
        SELECT p.full_name,
               SUM(pms.runs) AS total_runs,
               ROUND(SUM(pms.runs) / NULLIF(COUNT(*),0), 2) AS approx_bat_avg,
               SUM(CASE WHEN pms.runs >= 100 THEN 1 ELSE 0 END) AS centuries
        FROM player_match_stats pms
        JOIN players p ON pms.player_id = p.player_id
        WHERE pms.format = 'odi'
        GROUP BY p.player_id, p.full_name
        ORDER BY total_runs DESC
        LIMIT 10;
    """,

    "4) Venues with capacity > 50k (name, city, country, capacity) — largest first": """
        SELECT name, city, country, capacity
        FROM venues
        WHERE capacity > 50000
        ORDER BY capacity DESC;
    """,

    "5) Matches won by each team (count, desc)": """
        SELECT t.team_name, COUNT(*) AS wins
        FROM matches m
        JOIN teams t ON m.winning_team_id = t.team_id
        GROUP BY t.team_name
        ORDER BY wins DESC, t.team_name ASC;
    """,

    "6) Players per role (role counts)": """
        SELECT role, COUNT(*) AS players_count
        FROM players
        GROUP BY role
        ORDER BY players_count DESC, role ASC;
    """,

    "7) Highest individual batting score per format (from per-match stats)": """
        SELECT format, MAX(runs) AS highest_individual_score
        FROM player_match_stats
        WHERE format IN ('test','odi','t20i')
        GROUP BY format;
    """,

    "8) Series in 2024 (proxy via matches.series_name) — name, match_type, first_date, total_matches": """
        SELECT m.series_name,
               m.match_type,
               MIN(m.match_date) AS start_date,
               COUNT(*) AS matches_planned
        FROM matches m
        WHERE YEAR(m.match_date) = 2024
        GROUP BY m.series_name, m.match_type
        ORDER BY start_date ASC;
    """,

    # INTERMEDIATE (9–16)
    "9) All-rounders with >1000 runs AND >50 wickets (by format)": """
        SELECT p.full_name, pms.format,
               SUM(pms.runs) AS total_runs,
               SUM(pms.wickets) AS total_wickets
        FROM player_match_stats pms
        JOIN players p ON pms.player_id = p.player_id
        GROUP BY p.player_id, p.full_name, pms.format
        HAVING SUM(runs) > 1000 AND SUM(wickets) > 50
        ORDER BY total_runs DESC, total_wickets DESC;
    """,

    "10) Last 20 completed matches (desc, teams, winner, venue) — most recent first": """
        SELECT CONCAT(m.series_name, ' - ', m.match_type) AS match_desc,
               t1.team_name AS team1, t2.team_name AS team2,
               tw.team_name AS winner,
               v.name AS venue, v.city,
               m.status, m.match_date
        FROM matches m
        JOIN teams t1 ON m.team1_id = t1.team_id
        JOIN teams t2 ON m.team2_id = t2.team_id
        LEFT JOIN teams tw ON m.winning_team_id = tw.team_id
        JOIN venues v ON m.venue_id = v.venue_id
        WHERE m.status IS NOT NULL AND m.status <> ''
        ORDER BY m.match_date DESC
        LIMIT 20;
    """,

    "11) Players with ≥2 formats: runs by format + overall approx avg": """
        WITH per_fmt AS (
            SELECT p.player_id, p.full_name, pms.format,
                   SUM(pms.runs) AS runs_fmt, COUNT(*) AS inns_fmt
            FROM player_match_stats pms
            JOIN players p ON p.player_id = pms.player_id
            GROUP BY p.player_id, p.full_name, pms.format
        ),
        formats_played AS (
            SELECT player_id, COUNT(DISTINCT format) AS fmt_cnt
            FROM per_fmt
            GROUP BY player_id
            HAVING COUNT(DISTINCT format) >= 2
        ),
        totals AS (
            SELECT pf.player_id, pf.full_name,
                   SUM(pf.runs_fmt) AS total_runs_all,
                   SUM(pf.inns_fmt) AS inns_all
            FROM per_fmt pf
            GROUP BY pf.player_id, pf.full_name
        )
        SELECT pf.player_id, pf.full_name,
               MAX(CASE WHEN pf.format='test' THEN pf.runs_fmt END) AS runs_test,
               MAX(CASE WHEN pf.format='odi'  THEN pf.runs_fmt END) AS runs_odi,
               MAX(CASE WHEN pf.format='t20i' THEN pf.runs_fmt END) AS runs_t20i,
               ROUND(t.total_runs_all/NULLIF(t.inns_all,0),2) AS approx_overall_avg
        FROM per_fmt pf
        JOIN formats_played fp ON pf.player_id = fp.player_id
        JOIN totals t ON pf.player_id = t.player_id
        GROUP BY pf.player_id, pf.full_name, t.total_runs_all, t.inns_all
        ORDER BY approx_overall_avg DESC;
    """,

    "12) Team wins: Home vs Away (venue.country vs team.country)": """
        SELECT t.team_name,
               SUM(CASE WHEN v.country = t.country AND m.winning_team_id = t.team_id THEN 1 ELSE 0 END) AS home_wins,
               SUM(CASE WHEN v.country <> t.country AND m.winning_team_id = t.team_id THEN 1 ELSE 0 END) AS away_wins
        FROM matches m
        JOIN teams t ON t.team_id IN (m.team1_id, m.team2_id)
        JOIN venues v ON v.venue_id = m.venue_id
        GROUP BY t.team_name
        ORDER BY (home_wins + away_wins) DESC, t.team_name;
    """,

    "13) Partnerships ≥100 by consecutive positions (REQUIRES EXTRA FIELDS)": """
        SELECT 'Add batting_innings table (match_id, innings_no, position, player_id, runs_scored, partnership_runs)' AS todo;
    """,

    "14) Bowling at venues (>=3 matches at same venue; ≥4 overs each match)": """
        SELECT p.full_name, v.name AS venue, v.city, v.country,
               ROUND(AVG(pms.economy),2) AS avg_economy,
               SUM(pms.wickets) AS total_wkts,
               COUNT(*) AS matches_played
        FROM player_match_stats pms
        JOIN matches m ON pms.match_id = m.match_id
        JOIN venues v ON m.venue_id = v.venue_id
        JOIN players p ON p.player_id = pms.player_id
        WHERE pms.overs IS NOT NULL AND pms.overs >= 4.0
        GROUP BY p.player_id, p.full_name, v.venue_id, v.name, v.city, v.country
        HAVING COUNT(*) >= 3
        ORDER BY avg_economy ASC, total_wkts DESC;
    """,

    "15) Players in close matches (approx via status text <50 runs or <5 wickets)": """
        WITH close_matches AS (
            SELECT m.match_id,
                   CASE
                     WHEN (m.status REGEXP 'won by [0-4] wickets') THEN 1
                     WHEN (m.status REGEXP 'won by [0-4][0-9] runs') THEN 1
                     ELSE 0
                   END AS is_close
            FROM matches m
        ),
        player_close AS (
            SELECT pms.player_id,
                   AVG(CASE WHEN cm.is_close=1 THEN pms.runs END) AS avg_runs_close,
                   SUM(CASE WHEN cm.is_close=1 THEN 1 ELSE 0 END) AS close_matches_played
            FROM player_match_stats pms
            JOIN close_matches cm ON cm.match_id = pms.match_id
            GROUP BY pms.player_id
        )
        SELECT p.full_name, pc.avg_runs_close, pc.close_matches_played
        FROM player_close pc
        JOIN players p ON p.player_id = pc.player_id
        WHERE pc.close_matches_played > 0
        ORDER BY pc.avg_runs_close DESC;
    """,

    "16) Since 2020: per-player yearly avg runs & avg strike rate (>=5 matches/year)": """
        SELECT p.full_name,
               YEAR(m.match_date) AS year,
               ROUND(AVG(pms.runs),2) AS avg_runs_per_match,
               ROUND(AVG(pms.strike_rate),2) AS avg_sr,
               COUNT(*) AS matches_in_year
        FROM player_match_stats pms
        JOIN players p ON p.player_id = pms.player_id
        JOIN matches m ON m.match_id = pms.match_id
        WHERE m.match_date >= '2020-01-01'
        GROUP BY p.player_id, p.full_name, YEAR(m.match_date)
        HAVING COUNT(*) >= 5
        ORDER BY year DESC, avg_runs_per_match DESC;
    """,

    # ADVANCED (17–25)
    "17) Toss advantage by decision (REQUIRES EXTRA FIELDS)": """
        SELECT 'Add columns to matches: toss_winner_team_id, toss_decision' AS todo;
    """,

    "18) Most economical bowlers (ODI/T20I; ≥10 matches; ≥2 overs/match avg)": """
        WITH agg AS (
            SELECT p.player_id, p.full_name, pms.format,
                   SUM(pms.overs) AS overs_sum,
                   SUM(pms.wickets) AS wkts_sum,
                   COUNT(*) AS matches_cnt,
                   AVG(pms.economy) AS avg_econ
            FROM player_match_stats pms
            JOIN players p ON p.player_id = pms.player_id
            WHERE pms.format IN ('odi','t20i') AND pms.overs IS NOT NULL
            GROUP BY p.player_id, p.full_name, pms.format
        )
        SELECT full_name, format,
               ROUND(avg_econ,2) AS avg_economy,
               wkts_sum AS total_wickets,
               matches_cnt
        FROM agg
        WHERE matches_cnt >= 10 AND (overs_sum / matches_cnt) >= 2.0
        ORDER BY avg_economy ASC, total_wickets DESC
        LIMIT 30;
    """,

    "19) Consistency since 2022: avg runs & stddev of runs (approx)": """
        SELECT p.full_name,
               ROUND(AVG(pms.runs),2) AS avg_runs,
               ROUND(STDDEV_SAMP(pms.runs),2) AS stddev_runs,
               COUNT(*) AS inns_count
        FROM player_match_stats pms
        JOIN players p ON p.player_id = pms.player_id
        JOIN matches m ON m.match_id = pms.match_id
        WHERE m.match_date >= '2022-01-01'
        GROUP BY p.player_id, p.full_name
        HAVING inns_count >= 5
        ORDER BY stddev_runs ASC, avg_runs DESC;
    """,

    "20) Matches played by format + batting averages (approx via runs/matches)": """
        WITH agg AS (
            SELECT p.player_id, p.full_name, pms.format,
                   COUNT(*) AS matches_cnt,
                   SUM(pms.runs) AS runs_sum
            FROM player_match_stats pms
            JOIN players p ON p.player_id = pms.player_id
            GROUP BY p.player_id, p.full_name, pms.format
        ),
        pivoted AS (
            SELECT player_id, full_name,
                   SUM(CASE WHEN format='test' THEN matches_cnt ELSE 0 END) AS test_matches,
                   SUM(CASE WHEN format='odi'  THEN matches_cnt ELSE 0 END) AS odi_matches,
                   SUM(CASE WHEN format='t20i' THEN matches_cnt ELSE 0 END) AS t20_matches,
                   SUM(CASE WHEN format='test' THEN runs_sum ELSE 0 END) AS test_runs,
                   SUM(CASE WHEN format='odi'  THEN runs_sum ELSE 0 END) AS odi_runs,
                   SUM(CASE WHEN format='t20i' THEN runs_sum ELSE 0 END) AS t20_runs,
                   SUM(matches_cnt) AS total_matches
            FROM agg
            GROUP BY player_id, full_name
        )
        SELECT full_name,
               test_matches, odi_matches, t20_matches,
               ROUND(test_runs/NULLIF(test_matches,0),2) AS test_avg_approx,
               ROUND(odi_runs/NULLIF(odi_matches,0),2)  AS odi_avg_approx,
               ROUND(t20_runs/NULLIF(t20_matches,0),2)  AS t20_avg_approx
        FROM pivoted
        WHERE total_matches >= 20
        ORDER BY total_matches DESC, full_name;
    """,

    "21) Composite player ranking (REQUIRES EXTRA FIELDS)": """
        SELECT 'Create player_format_totals to compute composite ranking fields' AS todo;
    """,

    "22) Head-to-head summary last 3 years (REQUIRES EXTRA FIELDS)": """
        SELECT 'Add numeric margin fields + who batted first to enable full H2H analysis' AS todo;
    """,

    "23) Recent form (last 10 inns): averages, 50+ counts, stddev trend": """
        WITH ranked AS (
            SELECT pms.player_id, p.full_name, pms.runs, pms.strike_rate, m.match_date,
                   ROW_NUMBER() OVER (PARTITION BY pms.player_id ORDER BY m.match_date DESC) AS rn
            FROM player_match_stats pms
            JOIN players p ON p.player_id = pms.player_id
            JOIN matches m ON m.match_id = pms.match_id
        ),
        last10 AS (SELECT * FROM ranked WHERE rn <= 10),
        last5  AS (SELECT * FROM ranked WHERE rn <= 5)
        SELECT l10.full_name,
               ROUND(AVG(l5.runs),2)  AS avg_last5,
               ROUND(AVG(l10.runs),2) AS avg_last10,
               ROUND(STDDEV_SAMP(l10.runs),2) AS std_runs_last10,
               SUM(CASE WHEN l10.runs >= 50 THEN 1 ELSE 0 END) AS fifties_last10
        FROM last10 l10
        LEFT JOIN last5 l5 ON l5.player_id = l10.player_id
        GROUP BY l10.player_id, l10.full_name
        ORDER BY avg_last10 DESC;
    """,

    "24) Best batting partnerships (REQUIRES EXTRA FIELDS)": """
        SELECT 'Add partnerships table or compute from detailed innings data' AS todo;
    """,

    "25) Quarterly batting trend since 2020: avg runs & avg SR; improvement tag": """
        WITH base AS (
            SELECT p.player_id, p.full_name,
                   CONCAT(YEAR(m.match_date), '-Q', QUARTER(m.match_date)) AS year_quarter,
                   AVG(pms.runs) AS avg_runs_q,
                   AVG(pms.strike_rate) AS avg_sr_q
            FROM player_match_stats pms
            JOIN players p ON p.player_id = pms.player_id
            JOIN matches m ON m.match_id = pms.match_id
            WHERE m.match_date >= '2020-01-01'
            GROUP BY p.player_id, p.full_name, YEAR(m.match_date), QUARTER(m.match_date)
        ),
        ranked AS (
            SELECT b.*,
                   ROW_NUMBER() OVER (PARTITION BY player_id ORDER BY year_quarter) AS rn
            FROM base b
        ),
        with_prev AS (
            SELECT a.*,
                   LAG(a.avg_runs_q) OVER (PARTITION BY a.player_id ORDER BY a.rn) AS prev_runs_q
            FROM ranked a
        )
        SELECT full_name, year_quarter,
               ROUND(avg_runs_q,2) AS avg_runs_q,
               ROUND(avg_sr_q,2)   AS avg_sr_q,
               CASE
                 WHEN prev_runs_q IS NULL THEN 'First period'
                 WHEN avg_runs_q > prev_runs_q THEN 'Improving'
                 WHEN avg_runs_q < prev_runs_q THEN 'Declining'
                 ELSE 'Stable'
               END AS trend_vs_prev
        FROM with_prev
        ORDER BY full_name, year_quarter;
    """,
}

# -----------------------
# UI (single selector)
# -----------------------
top_row = st.columns([2, 1])
with top_row[0]:
    question = st.selectbox("Pick a question", list(QUERY_MAP.keys()))
with top_row[1]:
    now_ist = datetime.now(ZoneInfo("Asia/Kolkata")).strftime("%Y-%m-%d %H:%M:%S IST")
    st.caption(f"Queried at: {now_ist}")

sql = QUERY_MAP[question]

with st.expander("Show SQL"):
    st.code(sql, language="sql")

if st.button("▶ Run query"):
    try:
        rows = run_query(sql)
        df = pd.DataFrame(rows)
        if df.empty:
            st.info("No rows returned.")
        else:
            st.dataframe(df, use_container_width=True)
    except Exception as e:
        st.error(f"SQL error: {e}")
        st.warning("This query may require extra fields/tables not in the base schema. See the title note.")
