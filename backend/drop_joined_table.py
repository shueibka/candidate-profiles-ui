# backend/drop_joined_table.py

from sqlalchemy import text
from db_connection import get_engine

def drop_joined_table():
    engine = get_engine()
    with engine.connect() as conn:
        conn.execute(text("DROP TABLE IF EXISTS candidate_profiles_joined;"))
        conn.commit()
    print("✅ candidate_profiles_joined table dropped successfully.")

if __name__ == "__main__":
    drop_joined_table()
