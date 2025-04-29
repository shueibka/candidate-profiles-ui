# backend/crud_operations.py

import pandas as pd
import hashlib
from datetime import datetime
from uuid import uuid4
from sqlalchemy import text
from sqlalchemy.orm import Session
from db_connection import get_engine, get_session
from models import CandidateProfilesJoined
from audit_log import log_audit

def record_exists(session, record_id):
    """Check if a record with record_id exists."""
    result = session.query(CandidateProfilesJoined).filter_by(record_id=record_id).first()
    return result is not None

def insert_candidate(session, person_id, name, country_code, city, url, position, about,
                     total_experience_years, experiences, degrees, certifications, languages, courses):
    """Insert a new candidate."""
    try:
        new_record_id = str(uuid4())
        load_date = datetime.now()

        new_candidate = CandidateProfilesJoined(
            record_id=new_record_id,
            person_id=person_id,
            name=name,
            country_code=country_code,
            city=city,
            url=url,
            position=position,
            about=about,
            total_experience_years=total_experience_years,
            experiences=experiences,
            degrees=degrees,
            certifications=certifications,
            languages=languages,
            courses=courses,
            load_date=load_date
        )

        session.add(new_candidate)
        session.commit()
        log_audit(new_record_id, "INSERT", "SUCCESS")
        print(f"✅ Inserted new candidate: {name}")

    except Exception as e:
        session.rollback()
        log_audit("N/A", "INSERT", "FAILED", str(e))
        print(f"❌ Error inserting candidate: {e}")

def search_candidates(session, search_term=None, min_experience_years=None):
    """Search candidates by name, city, position, experiences, and/or minimum experience years."""
    try:
        where_clauses = []
        params = {}

        # Add search by text
        if search_term:
            search_term = f"%{search_term.lower()}%"
            where_clauses.append("""(
                LOWER(name) LIKE :search_term
             OR LOWER(city) LIKE :search_term
             OR LOWER(position) LIKE :search_term
             OR LOWER(experiences) LIKE :search_term
            )""")
            params['search_term'] = search_term

        # Add filter by minimum experience years
        if min_experience_years is not None:
            where_clauses.append("total_experience_years >= :min_experience_years")
            params['min_experience_years'] = min_experience_years

        # Build the final WHERE clause
        where_sql = " AND ".join(where_clauses)
        final_query = f"SELECT * FROM candidate_profiles_joined"
        if where_sql:
            final_query += f" WHERE {where_sql}"
        final_query += " ORDER BY load_date DESC"

        result = session.execute(text(final_query), params)
        rows = result.fetchall()

        if not rows:
            print("No candidates found.")
            return

        print("\n--- Search Results ---")
        for row in rows:
            print(f"Name: {row.name}")
            print(f"City: {row.city}")
            print(f"Position: {row.position}")
            print(f"Experience Years: {row.total_experience_years}")
            print(f"Experiences: {row.experiences}")
            print("-" * 40)

    except Exception as e:
        print(f"❌ Error searching candidates: {e}")


def update_candidate(session, record_id, new_name=None, new_city=None, new_position=None, new_experience=None):
    """Update candidate information."""
    try:
        if not record_exists(session, record_id):
            log_audit(record_id, "UPDATE", "FAILED", "Record does not exist.")
            print("❌ Record not found.")
            return

        updates = []
        if new_name:
            updates.append(f"name = '{new_name}'")
        if new_city:
            updates.append(f"city = '{new_city}'")
        if new_position:
            updates.append(f"position = '{new_position}'")
        if new_experience is not None:
            updates.append(f"total_experience_years = {new_experience}")

        if not updates:
            print("⚠️ No fields provided to update.")
            return

        updates.append(f"load_date = '{datetime.now()}'")

        update_query = f"""
        UPDATE candidate_profiles_joined
        SET {', '.join(updates)}
        WHERE record_id = :record_id
        """

        session.execute(text(update_query), {"record_id": record_id})
        session.commit()
        log_audit(record_id, "UPDATE", "SUCCESS")
        print("✅ Candidate updated successfully.")

    except Exception as e:
        session.rollback()
        log_audit(record_id, "UPDATE", "FAILED", str(e))
        print(f"❌ Error updating candidate: {e}")

def delete_candidate(session, record_id):
    """Delete a candidate."""
    try:
        if not record_exists(session, record_id):
            log_audit(record_id, "DELETE", "FAILED", "Record does not exist.")
            print("❌ Record not found.")
            return

        delete_query = text("""
        DELETE FROM candidate_profiles_joined
        WHERE record_id = :record_id
        """)
        session.execute(delete_query, {"record_id": record_id})
        session.commit()
        log_audit(record_id, "DELETE", "SUCCESS")
        print("✅ Candidate deleted successfully.")

    except Exception as e:
        session.rollback()
        log_audit(record_id, "DELETE", "FAILED", str(e))
        print(f"❌ Error deleting candidate: {e}")

# --- MOCK TEST SEQUENCE ---

if __name__ == "__main__":
    session = get_session()

    try:
        # Insert a mock candidate
        mock_person_id = "test_001"
        print("\n👉 Inserting mock candidate...")
        insert_candidate(
            session,
            person_id=mock_person_id,
            name="Test Candidate",
            country_code="SE",
            city="Stockholm",
            url="https://linkedin.com/in/testcandidate",
            position="Test Engineer",
            about="This is a mock candidate for testing.",
            total_experience_years=3,
            experiences="Testing, QA",
            degrees="BSc Computer Science",
            certifications="ISTQB",
            languages="English, Swedish",
            courses="Advanced Testing"
        )

        # Search mock candidate
        print("\n👉 Searching for 'Test Candidate'...")
        search_candidates(session, "Test Candidate")

        # Find record_id
        candidate = session.query(CandidateProfilesJoined).filter_by(person_id=mock_person_id).first()
        if candidate:
            mock_record_id = candidate.record_id
            print(f"\n✅ Found mock candidate with record_id: {mock_record_id}")

            # Update mock candidate
            print("\n👉 Updating mock candidate...")
            update_candidate(
                session,
                record_id=mock_record_id,
                new_city="Gothenburg",
                new_position="Senior Test Engineer",
                new_experience=5
            )

            # Verify update
            print("\n👉 Verifying update...")
            search_candidates(session, "Senior Test Engineer")

            # Delete mock candidate
            print("\n👉 Deleting mock candidate...")
            delete_candidate(session, mock_record_id)

            # Verify deletion
            print("\n👉 Verifying deletion...")
            search_candidates(session, "Test Candidate")

        else:
            print("❌ Mock candidate insertion failed. No record_id found.")

    finally:
        session.close()
