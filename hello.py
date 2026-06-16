import os
from dotenv import load_dotenv
from groq import Groq

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

prompt = """You are a SQL expert. Given this schema:

TABLE: agriculture
COLUMNS:
  - state (TEXT)
  - crop (TEXT)
  - year (INTEGER)
  - production_tonnes (REAL)

Convert this question to a SQLite query:
"Which 5 states had the highest rice production in 2023?"

Return ONLY the SQL query, no explanations, no markdown fences."""

response = client.chat.completions.create(
    model="llama-3.3-70b-versatile",
    messages=[
        {"role": "user", "content": prompt}
    ]
)

print(response.choices[0].message.content)