# backend/generate_ner_training_data.py

from db_connection import get_session
from models import CandidateProfilesJoined, JobPostingsRaw, NerTrainingData
from datetime import datetime


# backend/create_tables.py

from db_connection import engine
from models import Base

def create_all_tables():
    Base.metadata.create_all(engine)
    print("✅ All tables created successfully.")

if __name__ == "__main__":
    create_all_tables()

def generate_ner_training_data():
    session = get_session()

    try:
        # Collect from candidate_profiles_joined
        candidates = session.query(CandidateProfilesJoined).filter(CandidateProfilesJoined.about.isnot(None)).all()
        for c in candidates:
            ner_entry = NerTrainingData(
                source="candidate",
                record_id=c.record_id,
                text=c.about.strip(),
                created_at=datetime.now()
            )
            session.add(ner_entry)

        # Collect from job_postings_raw
        jobs = session.query(JobPostingsRaw).filter(JobPostingsRaw.job_description.isnot(None)).all()
        for j in jobs:
            ner_entry = NerTrainingData(
                source="job_posting",
                record_id=j.job_id,
                text=j.job_description.strip(),
                created_at=datetime.now()
            )
            session.add(ner_entry)

        session.commit()
        print("✅ NER training data generated successfully.")

    except Exception as e:
        session.rollback()
        print(f"❌ Error generating NER training data: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    generate_ner_training_data()
