# backend/data_fetching.py

import requests
from sqlalchemy.orm import Session
from db_connection import get_engine, get_session
from models import Base, PersonRaw, ExperienceRaw, EducationRaw, CertificationsRaw, LanguagesRaw, CoursesRaw
from audit_log import log_audit

def create_tables():
    engine = get_engine()
    Base.metadata.create_all(bind=engine)
    print("✅ Tables created.")

def fetch_api_data():
    url = "https://ahmednurmahamud.github.io/Recruitment_System/Recruitment_system.json"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        log_audit("N/A", "API_FETCH", "SUCCESS")
        print(f"✅ Fetched {len(data)} candidates from API.")
        return data
    except Exception as e:
        log_audit("N/A", "API_FETCH", "FAILED", str(e))
        raise Exception(f"API fetch failed: {str(e)}")

def normalize_and_insert(data):
    session = get_session()

    try:
        for person in data:
            person_id = person.get("linkedin_num_id")

            existing_person = session.query(PersonRaw).filter_by(person_id=person_id).first()

            if existing_person:
                existing_person.name = person.get("name")
                existing_person.country_code = person.get("country_code")
                existing_person.city = person.get("city")
                existing_person.url = person.get("url")
                existing_person.position = person.get("position")
                existing_person.current_company_name = person.get("current_company_name")
                existing_person.about = person.get("about")
                print(f"🔄 Updated existing person: {person_id}")
            else:
                new_person = PersonRaw(
                    person_id=person_id,
                    name=person.get("name"),
                    country_code=person.get("country_code"),
                    city=person.get("city"),
                    url=person.get("url"),
                    position=person.get("position"),
                    current_company_name=person.get("current_company_name"),
                    about=person.get("about")
                )
                session.add(new_person)
                print(f"➕ Inserted new person: {person_id}")

            session.query(ExperienceRaw).filter_by(person_id=person_id).delete()
            session.query(EducationRaw).filter_by(person_id=person_id).delete()
            session.query(CertificationsRaw).filter_by(person_id=person_id).delete()
            session.query(LanguagesRaw).filter_by(person_id=person_id).delete()
            session.query(CoursesRaw).filter_by(person_id=person_id).delete()

            for exp in person.get("experience") or []:
                if exp.get("positions"):
                    for sub in exp.get("positions"):
                        session.add(ExperienceRaw(
                            person_id=person_id,
                            title=sub.get("title"),
                            start_date=sub.get("start_date"),
                            end_date=sub.get("end_date")
                        ))
                else:
                    session.add(ExperienceRaw(
                        person_id=person_id,
                        title=exp.get("title"),
                        start_date=exp.get("start_date"),
                        end_date=exp.get("end_date")
                    ))

            for edu in person.get("education") or []:
                session.add(EducationRaw(
                    person_id=person_id,
                    degree=edu.get("degree")
                ))

            for cert in person.get("certifications") or []:
                session.add(CertificationsRaw(
                    person_id=person_id,
                    title=cert.get("title")
                ))

            for lang in person.get("languages") or []:
                session.add(LanguagesRaw(
                    person_id=person_id,
                    title=lang.get("title")
                ))

            for course in person.get("courses") or []:
                session.add(CoursesRaw(
                    person_id=person_id,
                    title=course.get("title")
                ))

        session.commit()
        log_audit("N/A", "DATA_UPSERT", "SUCCESS")
        print("✅ Data upsert (insert/update) completed.")

    except Exception as e:
        session.rollback()
        log_audit("N/A", "DATA_UPSERT", "FAILED", str(e))
        raise Exception(f"Data upsert failed: {str(e)}")

    finally:
        session.close()

if __name__ == "__main__":
    create_tables()
    data = fetch_api_data()
    normalize_and_insert(data)
