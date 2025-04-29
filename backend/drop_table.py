# # backend/drop_job_postings_raw.py

# from db_connection import engine
# from sqlalchemy import text

# def drop_table():
#     with engine.connect() as conn:
#         conn.execute(text("DROP TABLE IF EXISTS job_postings_raw"))
#     print("✅ Dropped table 'job_postings_raw'.")

# if __name__ == "__main__":
#     drop_table()


# create_job_postings_table.py

from sqlalchemy import create_engine
from models import Base, JobPostingsRaw  # Import your Base and the specific model

# Connect to the database
engine = create_engine("sqlite:///candidate_profiles.db")

# Create only the 'job_postings_raw' table
Base.metadata.create_all(engine, tables=[JobPostingsRaw.__table__])

print("✅ 'job_postings_raw' table created successfully.")
