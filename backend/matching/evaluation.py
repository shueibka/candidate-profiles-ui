from sqlalchemy import text
from db_connection import get_session

from sqlalchemy import text
from db_connection import get_session

def store_prediction(job_id, candidate_id, data):
    session = get_session()
    try:
        session.execute(text("""
            INSERT OR REPLACE INTO recommendation_results
            (job_id, candidate_id, score)
            VALUES (:job_id, :candidate_id, :score)
        """), {
            "job_id": job_id,
            "candidate_id": candidate_id,
            "score": data["score"]
        })
        session.commit()
    except Exception as e:
        session.rollback()
        print(f"❌ Failed to store prediction for {candidate_id}: {e}")
    finally:
        session.close()



def store_hire(job_id, candidate_id):
    session = get_session()
    try:
        session.execute(text("""
            INSERT INTO hires (job_id, candidate_id)
            VALUES (:job_id, :candidate_id)
        """), {"job_id": job_id, "candidate_id": candidate_id})
        session.commit()
    finally:
        session.close()

def evaluate_recommendations(job_id):
    session = get_session()
    try:
        predictions = session.execute(text("""
            SELECT candidate_id, domain_mismatch, missing_skills 
            FROM recommendation_results
            WHERE job_id = :job_id
            ORDER BY score DESC
            LIMIT 10
        """), {"job_id": job_id}).fetchall()
        
        actual_hires = session.execute(text("""
            SELECT candidate_id FROM hires
            WHERE job_id = :job_id
        """), {"job_id": job_id}).scalars().all()

        # Calculate precision/recall metrics
        predicted_set = {row.candidate_id for row in predictions}
        actual_set = set(actual_hires)
        
        tp = len(predicted_set & actual_set)
        fp = len(predicted_set - actual_set)
        fn = len(actual_set - predicted_set)

        precision = tp / (tp + fp) if (tp + fp) > 0 else 0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0
        f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0

        return {
            "precision": precision,
            "recall": recall,
            "f1_score": f1,
            "role_match_rate": len(predicted_roles & actual_roles) / len(actual_roles) if actual_roles else 0,
            "location_match_rate": len(predicted_locations & actual_locations) / len(actual_locations) if actual_locations else 0,
            "experience_accuracy": exp_accuracy
        }
    finally:
        session.close()

def evaluate_matches(job, scored_candidates):
    total = len(scored_candidates)
    avg_score = sum(c["score"] for c in scored_candidates) / total if total > 0 else 0
    high_score_count = sum(1 for c in scored_candidates if c["score"] >= 0)

    return {
        "total_candidates": total,
        "average_score": avg_score,
        "above_50_count": high_score_count
    }
