# backend/app.py

# backend/app.py

from flask import Flask, request, jsonify
from sqlalchemy import text
from db_connection import get_session
from models import CandidateProfilesJoined
from crud_operations import insert_candidate, search_candidates, update_candidate, delete_candidate, record_exists
from audit_log import log_audit
from uuid import uuid4
from datetime import datetime
from models import JobPostingsRaw
from flask_cors import CORS
import traceback


# ✨ FIX: Create Flask app
app = Flask(__name__)
CORS(app)


# --- ROUTES ---

@app.route("/api/candidates", methods=["GET"])
def list_candidates():
    """List all candidates, with optional search and min experience filter."""
    session = get_session()
    try:
        search_term = request.args.get("search")
        min_experience_years = request.args.get("min_experience_years", type=int)

        where_clauses = []
        params = {}

        if search_term:
            search_term = f"%{search_term.lower()}%"
            where_clauses.append("""(
                LOWER(name) LIKE :search_term
             OR LOWER(city) LIKE :search_term
             OR LOWER(position) LIKE :search_term
             OR LOWER(experiences) LIKE :search_term
            )""")
            params['search_term'] = search_term

        if min_experience_years is not None:
            where_clauses.append("total_experience_years >= :min_experience_years")
            params['min_experience_years'] = min_experience_years

        where_sql = " AND ".join(where_clauses)
        query = "SELECT * FROM candidate_profiles_joined"
        if where_sql:
            query += f" WHERE {where_sql}"
        query += " ORDER BY load_date DESC"

        # ✅ FIXED: mappings().all() 
        results = session.execute(text(query), params).mappings().all()
        candidates = [dict(row) for row in results]

        return jsonify(candidates)

    except Exception as e:
        print("❌ Exception occurred in /api/candidates:")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

    finally:
        session.close()

@app.route("/api/candidates/<record_id>", methods=["GET"])
def get_candidate(record_id):
    """Get a single candidate by record_id."""
    session = get_session()
    try:
        candidate = session.query(CandidateProfilesJoined).filter_by(record_id=record_id).first()
        if not candidate:
            return jsonify({"error": "Candidate not found"}), 404

        return jsonify({
            "record_id": candidate.record_id,
            "person_id": candidate.person_id,
            "name": candidate.name,
            "country_code": candidate.country_code,
            "city": candidate.city,
            "url": candidate.url,
            "position": candidate.position,
            "about": candidate.about,
            "total_experience_years": candidate.total_experience_years,
            "experiences": candidate.experiences,
            "degrees": candidate.degrees,
            "certifications": candidate.certifications,
            "languages": candidate.languages,
            "courses": candidate.courses,
            "load_date": candidate.load_date
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        session.close()

@app.route("/api/candidates", methods=["POST"])
def create_candidate():
    """Insert a new candidate."""
    session = get_session()
    try:
        data = request.get_json()

        insert_candidate(
            session=session,
            person_id=data.get("person_id", str(uuid4())),
            name=data["name"],
            country_code=data.get("country_code"),
            city=data.get("city"),
            url=data.get("url"),
            position=data.get("position"),
            about=data.get("about"),
            total_experience_years=data.get("total_experience_years"),
            experiences=data.get("experiences"),
            degrees=data.get("degrees"),
            certifications=data.get("certifications"),
            languages=data.get("languages"),
            courses=data.get("courses")
        )
        return jsonify({"message": "Candidate created successfully."}), 201

    except Exception as e:
        session.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        session.close()

@app.route("/api/candidates/<record_id>", methods=["PUT"])
def update_candidate_api(record_id):
    """Update an existing candidate."""
    session = get_session()
    try:
        data = request.get_json()

        if not record_exists(session, record_id):
            return jsonify({"error": "Candidate not found"}), 404

        update_candidate(
            session=session,
            record_id=record_id,
            new_name=data.get("name"),
            new_city=data.get("city"),
            new_position=data.get("position"),
            new_experience=data.get("total_experience_years")
        )
        return jsonify({"message": "Candidate updated successfully."})

    except Exception as e:
        session.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        session.close()

@app.route("/api/candidates/<record_id>", methods=["DELETE"])
def delete_candidate_api(record_id):
    """Delete a candidate."""
    session = get_session()
    try:
        if not record_exists(session, record_id):
            return jsonify({"error": "Candidate not found"}), 404

        delete_candidate(session, record_id)
        return jsonify({"message": "Candidate deleted successfully."})

    except Exception as e:
        session.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        session.close()


@app.route("/job_postings", methods=["POST"])
def create_job_posting():
    session = get_session()
    try:
        data = request.get_json()
        print("📥 Received job posting data:", data)  # Add this line

        new_job = JobPostingsRaw(
             job_id=str(uuid4()),
            title=data["title"],
            department=data.get("department"),
            locations=data.get("locations"),
            work_type=data.get("work_type"),   # ✅ Correct name
            required_skills=data.get("required_skills"),
            preferred_skills=data.get("preferred_skills"),
            education_level=data.get("education_level"),
            languages_required=data.get("languages_required"),
            experience_required=data.get("experience_required"),
            total_experience_years=data.get("total_experience_years"),
            responsibilities=data.get("responsibilities"),
            qualifications=data.get("qualifications"),
            job_description=data.get("job_description"),
            load_date=datetime.utcnow()
        )

        session.add(new_job)
        session.commit()
        return jsonify({"message": "✅ Job posting created successfully!"}), 201
    except Exception as e:
        session.rollback()
        import traceback
        traceback.print_exc()  # Add this line to see full traceback
        return jsonify({"error": str(e)}), 500
    finally:
        session.close()


# Read (Get All Job Postings)
@app.route("/api/job_postings", methods=["GET"])
def get_job_postings():
    session = get_session()
    jobs = session.query(JobPostingsRaw).all()
    result = []
    for job in jobs:
        result.append({
            "id": job.job_id,
            "title": job.title,
            "department": job.department,
            "locations": job.locations,
            "work_type": job.work_type,
            "experience_required": job.experience_required,
            "total_experience_years": job.total_experience_years,
            "job_description": job.job_description
        })
    session.close()
    return jsonify(result)

# Read (Get Single Job Posting by job_id)
@app.route("/job_postings/<string:job_id>", methods=["GET"])
def get_job_posting(job_id):
    session = get_session()
    try:
        job = session.query(JobPostingsRaw).filter_by(job_id=job_id).first()
        if job:
            result = job.__dict__
            result.pop("_sa_instance_state", None)
            return jsonify(result)
        else:
            return jsonify({"error": "Job posting not found."}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        session.close()

# Update (Modify a Job Posting)
@app.route("/job_postings/<string:job_id>", methods=["PUT"])
def update_job_posting(job_id):
    session = get_session()

    try:
        job = session.query(JobPostingsRaw).filter_by(job_id=job_id).first()
        if not job:
            return jsonify({"error": "Job posting not found."}), 404

        data = request.get_json()
        for key, value in data.items():
            if hasattr(job, key):
                setattr(job, key, value)

        job.load_date = datetime.utcnow()
        session.commit()
        return jsonify({"message": "✅ Job posting updated successfully."})
    except Exception as e:
        session.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        session.close()

# Delete (Remove a Job Posting)
@app.route("/job_postings/<string:job_id>", methods=["DELETE"])
def delete_job_posting(job_id):
    session = get_session()
    try:
        job = session.query(JobPostingsRaw).filter_by(job_id=job_id).first()
        if not job:
            return jsonify({"error": "Job posting not found."}), 404

        session.delete(job)
        session.commit()
        return jsonify({"message": "✅ Job posting deleted successfully."})
    except Exception as e:
        session.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        session.close()
@app.errorhandler(500)
def internal_error(error):
    return jsonify({"error": "Internal server error"}), 500

@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Resource not found"}), 404

@app.errorhandler(400)
def bad_request(error):
    return jsonify({"error": "Bad request"}), 400

# --- MAIN ---

if __name__ == "__main__":
    app.run(debug=True, port=5000)
