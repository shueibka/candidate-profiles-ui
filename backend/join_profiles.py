# backend/join_profiles.py

import pandas as pd
import hashlib
from datetime import datetime
from sqlalchemy import create_engine
from db_connection import get_engine, get_session
from models import PersonRaw, ExperienceRaw, EducationRaw, CertificationsRaw, LanguagesRaw, CoursesRaw
from audit_log import log_audit

def sha256_hash(row):
    """Generate SHA256 hash of concatenated row values."""
    concat_string = "||".join(str(v) if v is not None else "" for v in row)
    return hashlib.sha256(concat_string.encode('utf-8')).hexdigest()

def create_joined_profiles():
    session = get_session()

    try:
        # 1. Load normalized tables into DataFrames
        person_df = pd.read_sql_table('person_raw', session.bind)
        experience_df = pd.read_sql_table('experience_raw', session.bind)
        education_df = pd.read_sql_table('education_raw', session.bind)
        certifications_df = pd.read_sql_table('certifications_raw', session.bind)
        languages_df = pd.read_sql_table('languages_raw', session.bind)
        courses_df = pd.read_sql_table('courses_raw', session.bind)
        log_audit("N/A", "LOAD_NORMALIZED_TABLES", "SUCCESS")

        # 2. Calculate total experience years
        experience_df['start_date'] = pd.to_datetime(experience_df['start_date'], errors='coerce')
        experience_df['end_date'] = pd.to_datetime(experience_df['end_date'], errors='coerce')
        experience_df['end_date'] = experience_df['end_date'].fillna(pd.Timestamp.today())

        experience_df = experience_df.dropna(subset=['start_date', 'end_date'])
        experience_df['months'] = (experience_df['end_date'] - experience_df['start_date']).dt.days / 30
        exp_sum = experience_df.groupby('person_id')['months'].sum().reset_index()
        exp_sum['total_experience_years'] = (exp_sum['months'] / 12).astype(int)
        exp_sum = exp_sum[['person_id', 'total_experience_years']]

        # 3. Aggregate experience titles, degrees, certifications, languages, courses
        def aggregate(df, column, alias):
            return df.groupby('person_id')[column].apply(lambda x: ", ".join(x.dropna())).reset_index(name=alias)

        agg_exp = aggregate(experience_df, 'title', 'experiences')
        agg_edu = aggregate(education_df, 'degree', 'degrees')
        agg_cert = aggregate(certifications_df, 'title', 'certifications')
        agg_lang = aggregate(languages_df, 'title', 'languages')
        agg_course = aggregate(courses_df, 'title', 'courses')

        # 4. Join all information
        profile = person_df.merge(exp_sum, on='person_id', how='left') \
                           .merge(agg_exp, on='person_id', how='left') \
                           .merge(agg_edu, on='person_id', how='left') \
                           .merge(agg_cert, on='person_id', how='left') \
                           .merge(agg_lang, on='person_id', how='left') \
                           .merge(agg_course, on='person_id', how='left')

        # Local computer time
        profile['load_date'] = datetime.now()

        # 5. Calculate record_id
        profile['record_id'] = profile.apply(lambda row: sha256_hash(row.values), axis=1)

        # 6. Reorder columns
        profile = profile[[
            'record_id', 'person_id', 'name', 'country_code', 'city', 'url', 'position', 'about',
            'total_experience_years', 'experiences', 'degrees', 'certifications', 'languages', 'courses',
            'load_date'
        ]]

        log_audit("N/A", "JOIN_TRANSFORM", "SUCCESS")
        print("✅ Profile table joined successfully.")

        # 7. Save to SQLite
        engine = get_engine()
        profile.to_sql('candidate_profiles_joined', engine, if_exists='replace', index=False)
        log_audit("N/A", "SAVE_JOINED_TABLE", "SUCCESS")
        print("✅ candidate_profiles_joined saved to database.")

        # 8. Validate table
        if profile.empty:
            raise Exception("Validation failed: candidate_profiles_joined is empty.")
        expected_cols = [
            'record_id', 'person_id', 'name', 'country_code', 'city', 'url',
            'position', 'about', 'total_experience_years',
            'experiences', 'degrees', 'certifications', 'languages', 'courses', 'load_date'
        ]
        for col in expected_cols:
            if col not in profile.columns:
                raise Exception(f"Validation failed: missing column {col}")
        log_audit("N/A", "VALIDATION_JOINED_TABLE", "SUCCESS")
        print("✅ Validation passed: candidate_profiles_joined is valid.")

    except Exception as e:
        session.rollback()
        log_audit("N/A", "JOIN_PROCESS_FAILED", "FAILED", str(e))
        raise Exception(f"Error during join process: {e}")

    finally:
        session.close()

if __name__ == "__main__":
    create_joined_profiles()
