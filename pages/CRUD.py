# pages/crud.py

import streamlit as st
from utils.db_connection import run_query, run_execute

st.set_page_config(page_title="Players CRUD", page_icon="🛠", layout="wide")
st.title("🛠 Players — CRUD by Name")

def ok(msg): st.success(msg, icon="✅")
def err(msg): st.error(msg, icon="⚠️")
def info(msg): st.info(msg)

def fetch_by_name(name: str):
    """Return all rows that exactly match full_name."""
    return run_query(
        """SELECT player_id, full_name, role, batting_style, bowling_style, team_id
           FROM players WHERE full_name=%s""",
        (name.strip(),)
    )


# Create

with st.expander("➕ Add Player", expanded=True):
    c_name = st.text_input("Full name *")
    c_role = st.selectbox("Role", ["", "Batsman", "Bowler", "All-rounder", "Wicket-keeper"])
    c_bat  = st.text_input("Batting style", placeholder="Right-hand bat / Left-hand bat")
    c_bowl = st.text_input("Bowling style", placeholder="Right-arm fast / Left-arm orthodox")
    c_tid  = st.number_input("Team ID (optional)", min_value=0, step=1, value=0)

    if st.button("Save Player"):
        if not c_name.strip():
            err("Full name is required.")
        else:
            run_execute(
                """INSERT INTO players (full_name, role, batting_style, bowling_style, team_id)
                   VALUES (%s,%s,%s,%s,%s)""",
                (c_name.strip(),
                 (c_role or None) if c_role else None,
                 c_bat or None,
                 c_bowl or None,
                 (int(c_tid) if c_tid > 0 else None))
            )
            ok("Player added.")


# View (by name)

with st.expander("🔍 View Player by Name"):
    v_name = st.text_input("Enter player name")
    if st.button("Load Player"):
        if not v_name.strip():
            err("Enter a name.")
        else:
            rows = fetch_by_name(v_name)
            if not rows:
                err("No player found.")
            elif len(rows) > 1:
                err(f"Found {len(rows)} players with the same name. Please refine the name.")
                st.table(rows)  # show what matched so you can refine
            else:
                st.json(rows[0])


# Update (by name)

with st.expander("✏️ Update Player by Name"):
    u_lookup = st.text_input("Type the EXACT current name to update")
    if st.button("Fetch for Edit"):
        if not u_lookup.strip():
            err("Enter a name.")
        else:
            rows = fetch_by_name(u_lookup)
            if not rows:
                err("No player found.")
            elif len(rows) > 1:
                err(f"Found {len(rows)} players with the same name. Please refine the name.")
                st.table(rows)
            else:
                st.session_state["_edit_player"] = {"row": rows[0], "lookup": u_lookup.strip()}

    if "_edit_player" in st.session_state:
        r = st.session_state["_edit_player"]["row"]
        old_name = st.session_state["_edit_player"]["lookup"]

        e_name = st.text_input("Full name *", r["full_name"])
        e_role = st.selectbox(
            "Role", ["", "Batsman", "Bowler", "All-rounder", "Wicket-keeper"],
            index=(["", "Batsman", "Bowler", "All-rounder", "Wicket-keeper"].index(r.get("role") or "")
                   if (r.get("role") or "") in ["", "Batsman", "Bowler", "All-rounder", "Wicket-keeper"] else 0)
        )
        e_bat  = st.text_input("Batting style", r.get("batting_style") or "")
        e_bowl = st.text_input("Bowling style", r.get("bowling_style") or "")
        e_tid  = st.number_input("Team ID", min_value=0, step=1, value=int(r["team_id"] or 0))

        if st.button("Save Changes"):
            if not e_name.strip():
                err("Full name is required.")
            else:
                # Update by the original name 
                run_execute(
                    """UPDATE players
                       SET full_name=%s, role=%s, batting_style=%s, bowling_style=%s, team_id=%s
                       WHERE full_name=%s""",
                    (e_name.strip(),
                     (e_role or None) if e_role else None,
                     e_bat or None,
                     e_bowl or None,
                     (int(e_tid) if e_tid > 0 else None),
                     old_name)
                )
                ok("Player updated.")
                del st.session_state["_edit_player"]


# Delete (by name)

with st.expander("🗑 Delete Player by Name"):
    d_name = st.text_input("Enter player name to delete")
    d_confirm = st.checkbox("I understand this cannot be undone.")
    if st.button("Delete Player"):
        if not d_name.strip():
            err("Enter a name.")
        elif not d_confirm:
            err("Please confirm deletion.")
        else:
            rows = fetch_by_name(d_name)
            if not rows:
                err("No player found.")
            elif len(rows) > 1:
                err(f"Refusing to delete: found {len(rows)} players with the same name. Please refine the name.")
                st.table(rows)
            else:
                run_execute("DELETE FROM players WHERE full_name=%s", (d_name.strip(),))
                ok("Player deleted.")
