# recommendations.py

import traceback
from matching.matcher_pipeline import match_entities_with_bert, clean_text
from matching.evaluation import evaluate_matches

# recommendations.py

def recommend_candidates_for_job(job, candidates):
    job_id = job.get("id", "unknown")
    print(f"\n🧑💼 Processing job: {job['title']} ({job_id})")

    scored_candidates = []
    
    for candidate in candidates:
        try:
            candidate_id = candidate.get("record_id", "unknown")
            result = match_entities_with_bert(
                job,
                {
                    "about": clean_text(candidate.get("about", "")),
                    "experiences": clean_text(candidate.get("experiences", "")),
                    "city": clean_text(candidate.get("city", "")),
                    "degrees": clean_text(candidate.get("degrees", "")),
                    "certifications": clean_text(candidate.get("certifications", "")),
                    "languages": clean_text(candidate.get("languages", "")),
                    "courses": clean_text(candidate.get("courses", "")),
                    "total_experience": candidate.get("total_experience_years", 0)
                }
            )
            
            scored_candidates.append({
                "id": candidate_id,
                "score": result["score"],
                "precision": result["precision"],
                "recall": result["recall"],
                "f1_score": result["f1_score"],
                "details": {
                    # Corrected keys below
                    "roles": list(result["details"]["matched_roles"]),
                    "locations": list(result["details"]["matched_locations"]),
                    "tech_skills": list(result["details"]["matched_tech"]),
                    "matched_degrees": list(result["details"].get("degrees", [])),
                    "matched_certifications": list(result["details"].get("certifications", [])),
                    "job_experience": float(result["details"]["experience_ratio"].split("/")[1]),
                    "candidate_experience": float(result["details"]["experience_ratio"].split("/")[0])
                }
            })


        except Exception as e:
            print(f"❌ Error processing {candidate_id}: {str(e)}")
            traceback.print_exc()
            scored_candidates.append({
                "id": candidate_id,
                "score": 0,
                "precision": 0,
                "recall": 0,
                "f1_score": 0,
                "error": str(e)
            })

    # Sort candidates by score
    sorted_candidates = sorted(scored_candidates, key=lambda x: x["score"], reverse=True)
    
    return {
        "candidates": sorted_candidates,
        "evaluation": evaluate_matches(job, sorted_candidates)
    }