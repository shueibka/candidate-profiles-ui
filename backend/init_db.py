from sqlalchemy import create_engine, text
from db_connection import get_session

def init_tables():
    engine = create_engine("sqlite:///recruitment.db")  # Or replace with your full DB URI
    with engine.connect() as conn:
        # Create or update recommendation_results table
        conn.execute(text("""
        CREATE TABLE IF NOT EXISTS recommendation_results (
            job_id TEXT,
            candidate_id TEXT,
            score FLOAT,
            PRIMARY KEY (job_id, candidate_id)
        )
        """))

        # Create or update hires table
        conn.execute(text("""
        CREATE TABLE IF NOT EXISTS hires (
            job_id TEXT,
            candidate_id TEXT,
            PRIMARY KEY (job_id, candidate_id)
        )
        """))

        print("✅ Tables initialized")

if __name__ == "__main__":
    init_tables()
