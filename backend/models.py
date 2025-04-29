# backend/models.py

from sqlalchemy import Column, Integer, String, Float, TIMESTAMP, Text, DateTime
from sqlalchemy.orm import declarative_base
from datetime import datetime
import uuid

Base = declarative_base()

def generate_uuid():
    return str(uuid.uuid4())

class PersonRaw(Base):
    __tablename__ = "person_raw"
    person_id = Column(String, primary_key=True)
    name = Column(String)
    country_code = Column(String)
    city = Column(String)
    url = Column(String)
    position = Column(String)
    current_company_name = Column(String)
    about = Column(String)

class ExperienceRaw(Base):
    __tablename__ = "experience_raw"
    id = Column(Integer, primary_key=True, autoincrement=True)
    person_id = Column(String)
    title = Column(String)
    start_date = Column(String)
    end_date = Column(String)

class EducationRaw(Base):
    __tablename__ = "education_raw"
    id = Column(Integer, primary_key=True, autoincrement=True)
    person_id = Column(String)
    degree = Column(String)

class CertificationsRaw(Base):
    __tablename__ = "certifications_raw"
    id = Column(Integer, primary_key=True, autoincrement=True)
    person_id = Column(String)
    title = Column(String)

class LanguagesRaw(Base):
    __tablename__ = "languages_raw"
    id = Column(Integer, primary_key=True, autoincrement=True)
    person_id = Column(String)
    title = Column(String)

class CoursesRaw(Base):
    __tablename__ = "courses_raw"
    id = Column(Integer, primary_key=True, autoincrement=True)
    person_id = Column(String)
    title = Column(String)

class AuditLog(Base):
    __tablename__ = "candidate_profiles_audit_log"
    audit_id = Column(String, primary_key=True)
    record_id = Column(String)
    operation = Column(String)
    status = Column(String)
    error_message = Column(String)
    utc_timestamp = Column(TIMESTAMP)
    swedish_timestamp = Column(TIMESTAMP)

# 🔥 --- ADD THIS MISSING CLASS ---
class CandidateProfilesJoined(Base):
    __tablename__ = "candidate_profiles_joined"
    record_id = Column(String, primary_key=True)
    person_id = Column(String)
    name = Column(String)
    country_code = Column(String)
    city = Column(String)
    url = Column(String)
    position = Column(String)
    about = Column(String)
    total_experience_years = Column(Integer)
    experiences = Column(String)
    degrees = Column(String)
    certifications = Column(String)
    languages = Column(String)
    courses = Column(String)
    load_date = Column(TIMESTAMP)

class JobPostingsRaw(Base):
    __tablename__ = "job_postings_raw"

    job_id = Column(String, primary_key=True, default=generate_uuid)
    title = Column(String)
    department = Column(String)
    locations = Column(String)
    work_type = Column(String)
    required_skills = Column(Text)
    preferred_skills = Column(Text)
    education_level = Column(String)
    languages_required = Column(String)
    experience_required = Column(Text)  # Free text, ex: "5+ years in Backend Development"
    total_experience_years = Column(Integer)  # Numeric value for filtering
    responsibilities = Column(Text)
    qualifications = Column(Text)
    job_description = Column(Text)
    load_date = Column(DateTime, default=datetime.now)
    
class NerTrainingData(Base):
    __tablename__ = "ner_training_data"

    id = Column(Integer, primary_key=True, autoincrement=True)
    source = Column(String)  # 'candidate' or 'job_posting'
    record_id = Column(String)  # To trace back if needed
    text = Column(String)  # The raw text for NER training
    created_at = Column(TIMESTAMP, default=datetime.now)
