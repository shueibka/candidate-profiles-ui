from flask import Flask, request, jsonify
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from models import JobPostingsRaw
from uuid import uuid4
from datetime import datetime

# Setup
app = Flask(__name__)
engine = create_engine("sqlite:///candidate_profiles.db")
Session = sessionmaker(bind=engine)

# Create (Insert) a Job Posting
@app.route("/job_postings", methods=["POST"])
def create_job_posting():
    session = Session()
    try:
        data = request.get_json()

        new_job = JobPostingsRaw(
            job_id=str(uuid4()),
            title=data["title"],
            department=data.get("department"),
            seniority_level=data.get("seniority_level"),
            employment_type=data.get("employment_type"),
            locations=data.get("locations"),
            work_model=data.get("work_model"),
            required_skills=data.get("required_skills"),
            preferred_skills=data.get("preferred_skills"),
            education_level=data.get("education_level"),
            languages_required=data.get("languages_required"),
            experience_required=data.get("experience_required"),
            total_experience_years=data.get("total_experience_years"),
            job_description=data.get("job_description"),
            responsibilities=data.get("responsibilities"),
            qualifications=data.get("qualifications"),
            load_date=datetime.utcnow()
        )

        session.add(new_job)
        session.commit()
        return jsonify({"message": "✅ Job posting created successfully!"}), 201
    except Exception as e:
        session.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        session.close()

# Read (Get All Job Postings)
@app.route("/job_postings", methods=["GET"])
def get_all_job_postings():
    session = Session()
    try:
        jobs = session.query(JobPostingsRaw).order_by(JobPostingsRaw.load_date.desc()).all()
        result = [job.__dict__ for job in jobs]
        for r in result:
            r.pop("_sa_instance_state", None)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        session.close()

# Read (Get Single Job Posting by job_id)
@app.route("/job_postings/<string:job_id>", methods=["GET"])
def get_job_posting(job_id):
    session = Session()
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
    session = Session()
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
    session = Session()
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

if __name__ == "__main__":
    app.run(debug=True)
