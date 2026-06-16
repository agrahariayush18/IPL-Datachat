import os
import sqlite3
import pandas as pd
import streamlit as st
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# Auto-build database if it doesn't exist (needed for cloud deployment)
def ensure_database():
    if not os.path.exists("ipl.db"):
        matches = pd.read_csv("matches.csv")
        deliveries = pd.read_csv("deliveries.csv")
        conn = sqlite3.connect("ipl.db")
        matches.to_sql("matches", conn, if_exists="replace", index=False)
        deliveries.to_sql("deliveries", conn, if_exists="replace", index=False)
        conn.close()

ensure_database()  # Run it on startup

# ── Build dynamic schema with actual player/team names ──────────────────────
def get_schema() -> str:
    conn = sqlite3.connect("ipl.db")
    
    # Get unique teams
    teams = pd.read_sql("SELECT DISTINCT team1 FROM matches ORDER BY team1", conn)["team1"].tolist()
    
    # Get top 50 batters (to keep prompt size reasonable)
    batters = pd.read_sql(
    "SELECT DISTINCT batter FROM deliveries ORDER BY batter", 
    conn
    )["batter"].tolist()

    bowlers = pd.read_sql(
    "SELECT DISTINCT bowler FROM deliveries ORDER BY bowler", 
    conn
    )["bowler"].tolist()
    
    conn.close()
    
    schema = f"""
You have access to an IPL (Indian Premier League) cricket database with 2 tables:

TABLE: matches (1095 rows)
COLUMNS:
  - id (INTEGER) — unique match ID
  - season (TEXT) — e.g. '2007/08', '2021'
  - city (TEXT) — city where match was played
  - date (TEXT) — match date
  - match_type (TEXT) — 'League', 'Final', 'Semi Final' etc.
  - player_of_match (TEXT) — player name
  - venue (TEXT) — stadium name
  - team1 (TEXT) — first team
  - team2 (TEXT) — second team
  - toss_winner (TEXT) — team that won the toss
  - toss_decision (TEXT) — 'bat' or 'field'
  - winner (TEXT) — winning team name
  - result (TEXT) — 'runs' or 'wickets'
  - result_margin (REAL) — margin of victory

TABLE: deliveries (260920 rows)
COLUMNS:
  - match_id (INTEGER) — links to matches.id
  - inning (INTEGER) — 1 or 2
  - batting_team (TEXT) — team batting
  - bowling_team (TEXT) — team bowling
  - over (INTEGER) — over number (0-19)
  - ball (INTEGER) — ball number in over
  - batter (TEXT) — batsman name
  - bowler (TEXT) — bowler name
  - batsman_runs (INTEGER) — runs scored by batsman
  - total_runs (INTEGER) — total runs on this ball
  - is_wicket (INTEGER) — 1 if wicket fell, 0 otherwise
  - player_dismissed (TEXT) — name of dismissed player (if any)

VALID TEAM NAMES (use EXACTLY these):
{', '.join(teams)}

VALID BATTER NAMES (examples — use EXACTLY these spellings):
{', '.join(batters)}

VALID BOWLER NAMES (examples — use EXACTLY these spellings):
{', '.join(bowlers)}

IMPORTANT RULES:
- Always match player names EXACTLY as shown above (e.g., use 'V Kohli', not 'Virat Kohli')
- Always use JOIN on matches.id = deliveries.match_id when combining tables
- For player runs: SUM(batsman_runs) grouped by batter
- For wickets taken by bowler: SUM(is_wicket) grouped by bowler
- Return ONLY the SQL query, no explanations, no markdown, no backticks
- Use SQLite syntax only

CRICKET DOMAIN RULES (very important — SQL must follow these exactly):

1. DUCK = batsman got out with 0 total runs in the ENTIRE innings.
   ALWAYS use this subquery pattern for ducks:
   SELECT batter, COUNT(*) as ducks FROM (
       SELECT match_id, inning, batter,
              SUM(batsman_runs) as total_runs,
              MAX(is_wicket) as got_out
       FROM deliveries
       GROUP BY match_id, inning, batter
   ) WHERE total_runs = 0 AND got_out = 1
   GROUP BY batter ORDER BY ducks DESC

2. SIXES = deliveries where batsman_runs = 6
   COUNT them with: SUM(CASE WHEN batsman_runs = 6 THEN 1 ELSE 0 END)

3. FOURS = deliveries where batsman_runs = 4
   COUNT them with: SUM(CASE WHEN batsman_runs = 4 THEN 1 ELSE 0 END)

4. STRIKE RATE = (total runs / total balls faced) * 100
   Use: ROUND(SUM(batsman_runs) * 100.0 / COUNT(*), 2)

5. ECONOMY RATE for bowler = runs conceded per over
   Use: ROUND(SUM(total_runs) * 1.0 / (COUNT(*) / 6.0), 2)

6. MAIDEN OVER = an over where bowler conceded 0 runs
   Group by match_id, inning, bowler, over — then check SUM(total_runs) = 0

7. PARTNERSHIP = runs scored while two specific batters were together
   Use SUM(batsman_runs + extra_runs) grouped by match_id, inning

8. POWERPLAY = overs 0 to 5 (first 6 overs)
   Filter with: WHERE over BETWEEN 0 AND 5

9. DEATH OVERS = overs 16 to 19 (last 4 overs)
   Filter with: WHERE over BETWEEN 16 AND 19

10. NET RUN RATE requires match-level aggregation — avoid unless explicitly asked

11. IPL WINNER of a season = the team that won the FINAL match of that season.
    ALWAYS use this pattern:
    SELECT winner FROM matches 
    WHERE season = '2023' AND match_type = 'Final'
    
12. When asked "who won IPL [year]" or "IPL [year] winner" or "IPL [year] champion":
    ALWAYS filter by match_type = 'Final' AND the specific season.
    Never return all match winners for that season.
"""
    return schema

# ── Generate SQL from question ────────────────────────────────────────────────
def generate_sql(question: str) -> str:
    schema = get_schema()  # ← Dynamically load schema with real names
    prompt = f"{schema}\n\nConvert this question to SQL:\n\"{question}\""
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1  # low = more consistent SQL output
    )
    return response.choices[0].message.content.strip()

# ── Run SQL against the database ──────────────────────────────────────────────
def run_sql(sql: str) -> pd.DataFrame:
    conn = sqlite3.connect("ipl.db")
    df = pd.read_sql_query(sql, conn)
    conn.close()
    return df

def generate_sql_with_retry(question: str, max_retries: int = 2) -> tuple:
    """
    Tries to generate and run valid SQL.
    If it fails, sends the error back to the AI and retries.
    Returns (dataframe, final_sql, attempts_taken)
    """
    schema = get_schema()
    sql = generate_sql(question)
    
    for attempt in range(max_retries + 1):
        try:
            df = run_sql(sql)
            return df, sql, attempt + 1  # ✅ Success
            
        except Exception as error:
            if attempt == max_retries:
                raise error  # Give up after max retries
            
            # ❌ Failed — tell the AI what went wrong
            retry_prompt = f"""
{schema}

You previously wrote this SQL query:
{sql}

It failed with this error:
{str(error)}

Fix the SQL query so it works correctly.
Return ONLY the corrected SQL query, nothing else.
"""
            response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": retry_prompt}],
                temperature=0.1
            )
            sql = response.choices[0].message.content.strip()

# ── Streamlit UI ──────────────────────────────────────────────────────────────
st.set_page_config(page_title="IPL DataChat", page_icon="🏏", layout="wide")

st.title("🏏 IPL DataChat")
st.markdown("Ask anything about IPL data in plain English — no SQL needed.")

# Suggested questions
st.markdown("**Try asking:**")
col1, col2, col3 = st.columns(3)
with col1:
    if st.button("🏆 Who won the most IPL titles?"):
        st.session_state.question = "Which team has won the most IPL matches overall?"
with col2:
    if st.button("🏏 Top 5 run scorers ever"):
        st.session_state.question = "Who are the top 5 run scorers of all time in IPL?"
with col3:
    if st.button("🎳 Most wickets in IPL"):
        st.session_state.question = "Which bowler has taken the most wickets in IPL history?"

# Text input
question = st.text_input(
    "Or type your own question:",
    value=st.session_state.get("question", ""),
    placeholder="e.g. Which batsman scored the most runs in 2023?"
)

if question:
    with st.spinner("Thinking..."):
        try:
            # Generate SQL with automatic retry on failure
            df, final_sql, attempts = generate_sql_with_retry(question)

            # Show the SQL
            with st.expander("📝 Generated SQL (click to see)"):
                st.code(final_sql, language="sql")
                if attempts > 1:
                    st.caption(f"⚡ Auto-corrected after {attempts} attempts")

            # Show results
            if df.empty:
                st.warning("Query ran but returned no results. Try rephrasing.")
            else:
                st.success(f"✅ Found {len(df)} rows")

                # Clean ugly column names
                df.columns = [
                    col.split("(")[0].strip() if "(" in col else col 
                    for col in df.columns
                ]
                st.dataframe(df, use_container_width=True)

                # Auto chart
                if len(df.columns) == 2 and pd.api.types.is_numeric_dtype(df.iloc[:, 1]):
                    st.bar_chart(df.set_index(df.columns[0]))
        except Exception as e:
            st.error(f"Could not answer this question: {e}")
            st.info("Try rephrasing your question.")

# Footer
st.markdown("---")
st.markdown("Built with Groq + LLaMA 3.3 · IPL data 2008–2024 · [GitHub](https://github.com/agrahariayush18/IPL-Datachat)")