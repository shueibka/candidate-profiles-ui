import traceback
from matching.matcher_pipeline import match_entities_with_bert
from matching.evaluation import evaluate_matches

def recommend_candidates_for_job(job, candidates):
    job_id = job.get("id", "unknown")

    print("\n" + "=" * 40)
    print(f"🧑💼 JOB DESCRIPTION ANALYSIS for Job ID: {job_id}")
    
    # Debug logging of job only (optional)
    match_entities_with_bert(job, {})  # Just to print job details if needed

    scored_candidates = []

    for candidate in candidates:
        candidate_id = candidate.get("record_id") or candidate.get("id", "unknown")
        candidate_name = candidate.get("name", "Unnamed")

        print("\n" + "=" * 40)
        print(f"👤 CANDIDATE PROFILE ANALYSIS: {candidate_name} ({candidate_id})")

        try:
            about_text = candidate.get("about") or ""
            experiences_text = candidate.get("experiences") or ""

            # Skip completely empty profiles
            if not about_text.strip() and not experiences_text.strip():
                print("❌ Candidate has no usable profile text → score = 0")
                scored_candidates.append({
                    "id": candidate_id,
                    "score": 0.0,
                    "precision": 0.0,
                    "recall": 0.0,
                    "f1_score": 0.0
                })
                continue

            print("🔍 Running entity match with BERT...")
            result = match_entities_with_bert(job, candidate)
            print(f"✅ Match score: {result.get('score', 0.0)}")

            scored_candidates.append({
                "id": candidate_id,
                "score": result.get("score", 0.0),
                "precision": result.get("precision", 0.0),
                "recall": result.get("recall", 0.0),
                "f1_score": result.get("f1_score", 0.0)
            })

        except Exception as e:
            print(f"❌ Error processing candidate {candidate_id}: {e}")
            traceback.print_exc()
            scored_candidates.append({
                "id": candidate_id,
                "score": 0.0,
                "precision": 0.0,
                "recall": 0.0,
                "f1_score": 0.0
            })

    print("\n✅ All candidates processed. Running evaluation...\n")
    evaluation = evaluate_matches(job, scored_candidates)
    print("📊 Evaluation Results:", evaluation)

    return {
        "candidates": scored_candidates,
        "evaluation": evaluation
    }
