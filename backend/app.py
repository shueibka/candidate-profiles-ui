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
from matching.evaluation import evaluate_recommendations
from matching.recommendations import recommend_candidates_for_job  
import uuid
from matching.matcher_pipeline import match_entities_with_bert
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache
from matching.evaluation import store_prediction  # Move import here
from sentence_transformers import SentenceTransformer, util
from pydantic import ValidationError  
from matching.evaluation import evaluate_matches

# ✨ FIX: Create Flask app
app = Flask(__name__)
CORS(app)
executor = ThreadPoolExecutor(max_workers=4)
tasks = {}
bert_model = SentenceTransformer("all-MiniLM-L6-v2")

# --- ROUTES ---



@app.route("/api/candidates", methods=["GET"])
def list_candidates():
    """List all candidates, with optional search, filter, and sort."""
    session = get_session()
    try:
        search_term = request.args.get("search")
        filter_field = request.args.get("filter_field")
        min_experience_years = request.args.get("min_experience_years", type=int)
        sort_by = request.args.get("sort_by", "experience")

        where_clauses = []
        params = {}

        if search_term and filter_field:
            search_term = f"%{search_term.lower()}%"
            allowed_fields = ["name", "city", "position", "experiences"]
            if filter_field in allowed_fields:
                where_clauses.append(f"LOWER({filter_field}) LIKE :search_term")
                params["search_term"] = search_term
            else:
                return jsonify({"error": "Invalid filter_field"}), 400
        elif search_term:
            search_term = f"%{search_term.lower()}%"
            where_clauses.append("""(
                LOWER(name) LIKE :search_term
             OR LOWER(city) LIKE :search_term
             OR LOWER(position) LIKE :search_term
             OR LOWER(experiences) LIKE :search_term
            )""")
            params["search_term"] = search_term

        if min_experience_years is not None:
            where_clauses.append("total_experience_years >= :min_experience_years")
            params["min_experience_years"] = min_experience_years

        where_sql = " AND ".join(where_clauses)
        query = "SELECT * FROM candidate_profiles_joined"
        if where_sql:
            query += f" WHERE {where_sql}"

        sort_map = {
            "experience": "total_experience_years DESC",
            "name": "name ASC",
            "city": "city ASC"
        }
        query += f" ORDER BY {sort_map.get(sort_by, 'total_experience_years DESC')}"

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
@app.route("/api/candidates/filter", methods=["GET"])
def filter_candidates():
    """Filter candidates dynamically by name, city, or experience."""
    session = get_session()
    try:
        search_term = request.args.get("search", "").lower()
        filter_field = request.args.get("filter_field")
        sort_by = request.args.get("sort_by")  # ✅ NEW
        min_experience_years = request.args.get("min_experience_years", type=int)

        where_clauses = []
        params = {}

        if search_term and filter_field in ["name", "city", "position", "experiences"]:
            where_clauses.append(f"LOWER({filter_field}) LIKE :search_term")
            params["search_term"] = f"%{search_term}%"

        elif search_term:
            where_clauses.append("""(
                LOWER(name) LIKE :search_term
                OR LOWER(city) LIKE :search_term
                OR LOWER(position) LIKE :search_term
                OR LOWER(experiences) LIKE :search_term
            )""")
            params["search_term"] = f"%{search_term}%"

        if min_experience_years is not None:
            where_clauses.append("total_experience_years >= :min_experience_years")
            params["min_experience_years"] = min_experience_years

        where_sql = " AND ".join(where_clauses)
        query = "SELECT * FROM candidate_profiles_joined"
        if where_sql:
            query += f" WHERE {where_sql}"

        # ✅ Handle sorting consistently
        sort_map = {
            "experience": "total_experience_years DESC",
            "name": "name ASC",
            "city": "city ASC"
        }

        if sort_by in sort_map:
            query += f" ORDER BY {sort_map[sort_by]}"
        elif filter_field in ["name", "city"]:
            query += f" ORDER BY {filter_field} ASC"
        elif filter_field == "experience" or min_experience_years is not None:
            query += " ORDER BY total_experience_years DESC"
        else:
            query += " ORDER BY load_date DESC"

        results = session.execute(text(query), params).mappings().all()
        candidates = [dict(row) for row in results]
        return jsonify(candidates)

    except Exception as e:
        print("❌ Exception in /api/candidates/filter:")
        traceback.print_exc()
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




@app.route("/api/evaluate", methods=["POST"])
def evaluate():
    try:
        data = request.get_json()
        true_ids = data.get("true_ids", [])
        predicted = data.get("predicted", [])

        results = evaluate_recommendations(true_ids, predicted)
        return jsonify(results)
    except Exception as e:
        return jsonify({"error": str(e)}), 500




# @app.route("/api/recommendations/<job_id>", methods=["GET"])
# def recommend_candidates(job_id):
#     session = get_session()
#     try:
#         job = session.query(JobPostingsRaw).filter_by(job_id=job_id).first()
#         if not job:
#             return jsonify({"error": "Job not found"}), 404

#         job_dict = {
#             "job_id": job.job_id,
#             "job_description": job.job_description
#         }

#         candidates = session.execute(text("SELECT * FROM candidate_profiles_joined")).mappings().all()
#         candidate_list = [dict(c) for c in candidates]

#         recommendations = recommend_candidates_for_job(job.job_id)
#         return jsonify(recommendations)

#     except Exception as e:
#         print("❌ Error in /api/recommendations:")
#         traceback.print_exc()
#         return jsonify({"error": str(e)}), 500

#     finally:
#         session.close()

@app.route("/api/hire", methods=["POST"])
def api_store_hire():
    data = request.get_json()
    job_id = data.get("job_id")
    candidate_id = data.get("candidate_id")

    if not job_id or not candidate_id:
        return jsonify({"error": "job_id and candidate_id required"}), 400

    from matching.evaluation import store_hire
    store_hire(job_id, candidate_id)
    return jsonify({"message": "Hired candidate stored successfully"})


@app.route("/api/evaluate/<job_id>", methods=["GET"])
def api_evaluate_recommendations(job_id):
    from matching.evaluation import evaluate_recommendations
    metrics = evaluate_recommendations(job_id)
    return jsonify(metrics)

@app.route("/api/job_titles", methods=["GET"])
def get_job_titles():
    session = get_session()
    try:
        jobs = session.execute(text("SELECT job_id, title FROM job_postings_raw")).mappings().all()
        return jsonify([{"id": job["job_id"], "title": job["title"]} for job in jobs])
    finally:
        session.close()
# Add these imports at the top of app.py

def process_recommendations(job_id, job_description_fallback):
    from matching.evaluation import store_prediction
    session = get_session()
    try:
        # Fetch structured job object from DB
        job = session.query(JobPostingsRaw).filter_by(job_id=job_id).first()
        if not job:
            raise ValueError(f"No job found with id {job_id}")

        # Build fully-structured payload matching matcher_pipeline expectations
        job_payload = {
            "id": job.job_id,
            "title": job.title or "",
            "department": job.department or "",
            "locations": job.locations or "",
            "work_type": job.work_type or "",
            "experience_required": job.experience_required or "",
            "total_experience_years": str(job.total_experience_years or ""),
            "job_description": job.job_description or job_description_fallback
        }

        # Load all candidates
        candidates = session.execute(
            text("SELECT * FROM candidate_profiles_joined")
        ).mappings().all()
        candidate_list = [dict(r) for r in candidates]

        print(f"🔧 Processing {len(candidate_list)} candidates for job ID: {job_id}")
        result = recommend_candidates_for_job(job_payload, candidate_list)

        # Persist predictions
        for cand in result["candidates"]:
            cid = cand.get("id") or cand.get("record_id")
            store_prediction(
                job_id,
                cid,
                {
                    "score":     cand["score"],
                    "precision": cand["precision"],
                    "recall":    cand["recall"],
                    "f1_score":  cand["f1_score"]
                }
            )

        return result

    finally:
        session.close()




# Modified recommendation endpoint
@app.route("/api/recommendations/<job_id>", methods=["GET"])
def recommend_candidates(job_id):
    session = get_session()
    try:
        # Check if job exists first
        job = session.query(JobPostingsRaw).filter_by(job_id=job_id).first()
        if not job:
            return jsonify({"error": "Job not found"}), 404

        # Generate unique task ID
        task_id = str(uuid.uuid4())
        
        # Store future reference
        future = executor.submit(
            process_recommendations,
            job_id,
            job.job_description
        )
        tasks[task_id] = future
        
        return jsonify({
            "message": "Recommendation processing started",
            "task_id": task_id
        }), 202

    except Exception as e:
        print(f"❌ Error in recommendation init: {str(e)}")
        return jsonify({"error": str(e)}), 500
    finally:
        session.close()

# Status checking endpoint
@app.route("/api/recommendations/status/<task_id>", methods=["GET"])
def recommendation_status(task_id):
    future = tasks.get(task_id)

    if not future:
        return jsonify({"error": "Invalid task ID"}), 404

    if not future.done():
        return jsonify({
            "status": "processing",
            "progress": "0"
        }), 200

    try:
        results = future.result()
        del tasks[task_id]
        return jsonify({
            "status": "complete",
            "results": results
        })

    except Exception as e:
        import traceback
        print("\n❌ Exception in recommendation task:")
        traceback.print_exc()  # ← This will show the real error!
        return jsonify({
            "status": "error",
            "error": str(e)
        }), 500


# def process_recommendations(job_id, job_description):
#     session = get_session()
#     try:
#         job = session.query(JobPostingsRaw).filter_by(job_id=job_id).first()
#         candidates = session.execute(text("""
#             SELECT * FROM candidate_profiles_joined 
#             WHERE about IS NOT NULL AND experiences IS NOT NULL
#         """)).mappings().all()

#         results = []
#         for candidate in candidates:
#             try:
#                 # Use actual matcher pipeline
#                 score = match_entities_with_bert(
#                     job.job_description, 
#                     candidate["about"] + "\nSkills: " + candidate["experiences"]
#                 )

#                 # Get validation details
#                 score_data = {
#                     "score": score,
#                     "domain_mismatch": score == 0,  # From matcher logic
#                     "missing_skills": score < 50      # Example threshold
#                 }

#                 store_prediction(job_id, candidate["record_id"], score_data)

#                 results.append({
#                     "candidate_id": candidate["record_id"],
#                     **score_data
#                 })

#             except ValidationError as e:
#                 results.append({
#                     "error": str(e),
#                     "validation_failed": True,
#                     "candidate_id": candidate["record_id"]
#                 })

#         return sorted(results, key=lambda x: x.get("score", 0), reverse=True)
    
#     finally:
#         session.close()

# def recommend_candidates_for_job(job, candidates):
    
#     job_text = job.get("description", "")
#     if not job_text.strip():
#         raise ValueError("Job description is missing or empty.")
#     job_id = job.get("id", "unknown")

#     print("\n" + "=" * 40)
#     print(f"🧑💼 JOB DESCRIPTION ANALYSIS for Job ID: {job_id}")
#     match_entities_with_bert(job_text, "")  # For job logging only

#     scored_candidates = []

#     for candidate in candidates:
#         candidate_id = candidate.get("record_id") or candidate.get("id", "unknown")
#         candidate_text = candidate.get("about", "")
#         candidate_name = candidate.get("name", "Unnamed")

#         print("\n" + "=" * 40)
#         print(f"👤 CANDIDATE PROFILE ANALYSIS: {candidate_name} ({candidate_id})")

#         try:
#             if not candidate_text or not candidate_text.strip():
#                 print("❌ Candidate has empty 'about' field → score = 0")
#                 scored_candidates.append({
#                     "id": candidate_id,
#                     "score": 0.0,
#                     "precision": 0.0,
#                     "recall": 0.0,
#                     "f1_score": 0.0,
#                     "domain_mismatch": False,
#                     "missing_skills": True
#                 })
#                 continue

#             print("🔍 Running entity match with BERT...")
#             result = match_entities_with_bert(job_text, candidate_text)
#             print(f"✅ Match score: {result.get('score', 0.0)}")

#             scored_candidates.append({
#                 "id": candidate_id,
#                 "score": result.get("score", 0.0),
#                 "precision": result.get("precision", 0.0),
#                 "recall": result.get("recall", 0.0),
#                 "f1_score": result.get("f1_score", 0.0),
#                 "domain_mismatch": result.get("domain_mismatch", False),
#                 "missing_skills": result.get("missing_skills", False)
#             })

#         except Exception as e:
#             print(f"❌ Error processing candidate {candidate_id}: {e}")
#             traceback.print_exc()
#             scored_candidates.append({
#                 "id": candidate_id,
#                 "score": 0.0,
#                 "precision": 0.0,
#                 "recall": 0.0,
#                 "f1_score": 0.0,
#                 "domain_mismatch": False,
#                 "missing_skills": True
#             })

#     print("\n✅ All candidates processed. Running evaluation...\n")
#     evaluation = evaluate_matches(job, scored_candidates)
#     print("📊 Evaluation Results:", evaluation)

#     return {
#         "candidates": scored_candidates,
#         "evaluation": evaluation
#     }



def batch_similarity(job_text, candidate_texts):
    if not job_text or not candidate_texts:
        return [0.0 for _ in candidate_texts]

    job_embedding = bert_model.encode(job_text, convert_to_tensor=True)
    candidate_embeddings = bert_model.encode(candidate_texts, convert_to_tensor=True)
    cosine_scores = util.cos_sim(job_embedding, candidate_embeddings)[0]
    return cosine_scores.cpu().tolist()

# app.py
@app.route("/api/recommendations/details/<job_id>", methods=["GET"])
def get_recommendation_details(job_id):
    session = get_session()
    try:
        results = session.execute(text("""
            SELECT * FROM recommendation_results
            WHERE job_id = :job_id
            ORDER BY score DESC
        """), {"job_id": job_id}).mappings().all()
        
        return jsonify([dict(row) for row in results])
    finally:
        session.close()


@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Resource not found"}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({"error": "Internal server error"}), 500
# --- MAIN ---

if __name__ == "__main__":
    app.run(debug=True, port=5000)
