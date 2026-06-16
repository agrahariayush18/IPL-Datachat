# 🏏 IPL DataChat — Ask Cricket Data Anything in Plain English

A natural-language-to-SQL agent that lets anyone query 15 years of IPL (Indian Premier League) data without writing a single line of SQL. Ask a question in plain English → get accurate SQL, live results, and an auto-generated chart.

**Built with:** Python · Groq (LLaMA 3.3 70B) · Streamlit · SQLite · Pandas

> 🔗 **Live demo:** _(add your Streamlit URL here after deployment)_

---

## What it does

Type a question like *"Who are the top 5 run scorers in IPL history?"* or *"Which bowler has the best economy rate in death overs?"* and DataChat:

1. Sends your question + the database schema to an LLM
2. Gets back a SQLite query
3. Validates and runs it against a 260,000-row ball-by-ball database
4. Shows you the generated SQL (full transparency) and the results, with an automatic chart

---

## Why I built it

Natural-language-to-SQL is one of the most in-demand enterprise AI use cases in 2026 — but most implementations are black boxes. I wanted to build one that's **transparent** (shows the SQL), **accurate on domain-specific questions** (cricket has tricky definitions), and **honest about its limitations**. IPL data was the perfect testbed: rich, well-known, and full of edge cases.

---

## The engineering problems I solved

This project is less about the happy path and more about the failure modes I had to debug:

### 1. Entity resolution
Users type `"Virat Kohli"` but the database stores `"V Kohli"`. SQL was syntactically perfect but returned zero rows. **Fix:** I dynamically pull the actual player and team names from the database and inject them into the prompt, so the model always uses the correct spellings.

### 2. Self-correcting retry loop
LLMs sometimes generate SQL that references non-existent columns. Instead of failing, the app catches the database error, feeds it back to the model with the original query, and asks it to fix itself — up to 2 retries.

### 3. Silent semantic bugs (the hardest)
The model counted "ducks" as *any ball where a batter scored 0 and got out* — but a duck means **0 total runs in the entire innings**. The SQL ran without error but gave a wrong answer. No error message catches this — only domain knowledge does. **Fix:** I added explicit cricket-domain calculation rules to the prompt (ducks, strike rate, economy rate, powerplay, death overs, season winners, etc.).

### 4. Context vs. accuracy tradeoff
I initially capped the injected player list at 50 names to keep prompts short, but obscure players failed. Removing the cap raised accuracy at the cost of ~0.3s latency — a deliberate tradeoff favoring correctness for this use case.

---

## Tech stack

| Layer | Tool |
|---|---|
| LLM | Groq API — LLaMA 3.3 70B (`temperature=0.1` for consistent SQL) |
| UI | Streamlit |
| Database | SQLite (built from CSVs at startup, reproducible) |
| Data handling | Pandas |
| Secrets | python-dotenv (local) / Streamlit secrets (cloud) |

---

## Run it locally

```bash
# 1. Clone the repo
git clone https://github.com/agrahariayush18/IPL-Datachat.git
cd IPL-Datachat

# 2. Create a virtual environment
python -m venv venv
source venv/bin/activate        # Mac/Linux
# venv\Scripts\activate         # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Add your Groq API key (free at console.groq.com)
echo 'GROQ_API_KEY=your_key_here' > .env

# 5. Run
streamlit run app.py
```

The database (`ipl.db`) is built automatically from `matches.csv` and `deliveries.csv` on first run.

---

## Dataset

IPL ball-by-ball data covering **2008–2024**: 1,095 matches and 260,920 deliveries. Sourced from public Kaggle IPL datasets.

---

## Known limitations

Being honest about what doesn't work yet:

- **"Balls bowled" includes wides/no-balls** — economy and strike-rate calculations are very slightly inflated because they count every delivery, not just legal balls.
- **Data ends in 2024** — questions about later seasons return no results.
- **Very complex multi-step questions** (e.g. season-over-season net run rate) can still trip up the model.
- **No conversation memory yet** — each question is independent.

---

## What's next

- Exclude extras from legal-ball counts for precise bowling stats
- Add conversation memory ("show me that by season instead")
- Build an eval harness with a labeled question set to measure accuracy systematically
- Add query result caching for common questions

---

## About me

Built by **Ayush Agrahari** — final-year B.Tech student at NIT Jalandhar, focused on data engineering and applied AI.
[LinkedIn](https://linkedin.com/in/ayush-agrahari) · [GitHub](https://github.com/agrahariayush18)