import pandas as pd
import sqlite3

# Load both CSVs
matches = pd.read_csv("matches.csv")
deliveries = pd.read_csv("deliveries.csv")

print("=== MATCHES ===")
print("Shape:", matches.shape)
print("Columns:", matches.columns.tolist())
print(matches.head(3))

print("\n=== DELIVERIES ===")
print("Shape:", deliveries.shape)
print("Columns:", deliveries.columns.tolist())
print(deliveries.head(3))

# Load into SQLite
conn = sqlite3.connect("ipl.db")
matches.to_sql("matches", conn, if_exists="replace", index=False)
deliveries.to_sql("deliveries", conn, if_exists="replace", index=False)
conn.close()

print("\n✅ IPL database created successfully — ipl.db")
print(f"   matches table: {len(matches)} rows")
print(f"   deliveries table: {len(deliveries)} rows")