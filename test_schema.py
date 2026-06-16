import sqlite3
import pandas as pd

conn = sqlite3.connect("ipl.db")

teams = pd.read_sql("SELECT DISTINCT team1 FROM matches ORDER BY team1", conn)["team1"].tolist()
batters = pd.read_sql("SELECT DISTINCT batter FROM deliveries ORDER BY batter LIMIT 10", conn)["batter"].tolist()

conn.close()

print("TEAMS IN DATABASE:")
print(teams)

print("\nBATTERS IN DATABASE (first 10):")
print(batters)