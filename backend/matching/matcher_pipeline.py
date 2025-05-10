# matcher_pipeline.py

import re
import traceback
from sentence_transformers import SentenceTransformer, util
import spacy
import json
from pathlib import Path

DEBUG_LOGGING = True
bert_model = SentenceTransformer("all-MiniLM-L6-v2")

# Load spaCy models
nlp_en = spacy.load("en_core_web_lg")
nlp_sv = spacy.load("sv_core_news_md")

def load_tech_patterns():
    config_path = Path(__file__).parent / "tech_terms.json"
    with open(config_path, "r", encoding="utf-8") as f:
        terms = json.load(f)
    
    patterns = {"ROLE": [], "TECH": []}
    
    for term in terms["roles"]:
        tokens = [token.strip().lower() for token in term.split()]
        patterns["ROLE"].append({"label": "ROLE", "pattern": [{"LOWER": t} for t in tokens]})
    
    for term in terms["tech"]:
        tokens = [token.strip().lower() for token in term.split()]
        patterns["TECH"].append({"label": "TECH", "pattern": [{"LOWER": t} for t in tokens]})
    
    return patterns["ROLE"] + patterns["TECH"]

def create_custom_ner(nlp):
    ruler = nlp.add_pipe("entity_ruler", before="ner")
    ruler.add_patterns(load_tech_patterns())
    return nlp

nlp_en = create_custom_ner(nlp_en)
nlp_sv = create_custom_ner(nlp_sv)

def is_swedish(text):
    swedish_keywords = {'och', 'att', 'för', 'med', 'inte', 'som', 'på', 'är', 'det'}
    return sum(1 for word in swedish_keywords if word in text.lower()) >= 2

def clean_text(text):
    return re.sub(r"\s+", " ", str(text or "").strip())

def extract_entities(text, locations="", total_exp=0):
    # First ensure we have clean, concatenated text
    if isinstance(text, dict):  # If passed a candidate dict
        full_text = " ".join([
            text.get("about", ""),
            text.get("experiences", ""),
            text.get("degrees", ""),
            text.get("certifications", ""),
            text.get("languages", ""),
            text.get("courses", "")
        ])
        text = clean_text(full_text)
    else:  # If passed regular text
        text = clean_text(text)
    
    lang = "sv" if is_swedish(text) else "en"
    nlp = nlp_sv if lang == "sv" else nlp_en
    
    doc = nlp(text)  # Process concatenated text
    loc_doc = nlp(clean_text(locations)) if locations else None
    
    entities = {
        "ROLES": set(),
        "LOCATIONS": set(),
        "TECH": set(),
        "EXPERIENCE": total_exp,
        "TEXT_EXPERIENCE": 0
    }

    # Entity extraction logic
    for ent in doc.ents:
        if ent.label_ == "GPE":
            entities["LOCATIONS"].add(ent.text)
        elif ent.label_ == "ROLE":
            entities["ROLES"].add(ent.text)
        elif ent.label_ == "TECH":
            entities["TECH"].add(ent.text)

    if loc_doc:
        for ent in loc_doc.ents:
            if ent.label_ == "GPE":
                entities["LOCATIONS"].add(ent.text)

    # Improved experience extraction
    exp_pattern = r"(\d+\.?\d*)[+\s]*(?:years?|yrs?|år|years of experience|experience|exp\.?)"
    exp_matches = re.findall(exp_pattern, text, re.IGNORECASE)
    text_exp = max(map(float, exp_matches)) if exp_matches else 0
    
    # Fallback logic for missing experience
    final_exp = max(text_exp, total_exp)
    if final_exp == 0 and (text.strip() or total_exp == 0):
        final_exp = 1  # Default assumption for candidates with missing data

    entities["EXPERIENCE"] = final_exp
    entities["TEXT_EXPERIENCE"] = text_exp

    if DEBUG_LOGGING:
        print(f"\n🔍 Entity Extraction Results:")
        print(f"Text: {text[:200]}...")  # Show first 200 chars of text being analyzed
        print(f"Roles Found: {entities['ROLES']}")
        print(f"Tech Skills Found: {entities['TECH']}")
        print(f"Locations Found: {entities['LOCATIONS']}")
        print(f"Text Experience: {text_exp} | DB Experience: {total_exp}")
        print(f"Final Experience: {entities['EXPERIENCE']}")

    return entities

def calculate_metrics(job_ents, cand_ents):
    tp_roles = len(job_ents["ROLES"] & cand_ents["ROLES"])
    tp_tech = len(job_ents["TECH"] & cand_ents["TECH"])
    
    precision_roles = tp_roles / len(cand_ents["ROLES"]) if cand_ents["ROLES"] else 0
    recall_roles = tp_roles / len(job_ents["ROLES"]) if job_ents["ROLES"] else 0
    
    precision_tech = tp_tech / len(cand_ents["TECH"]) if cand_ents["TECH"] else 0
    recall_tech = tp_tech / len(job_ents["TECH"]) if job_ents["TECH"] else 0
    
    f1_roles = 2*(precision_roles*recall_roles)/(precision_roles+recall_roles) if (precision_roles+recall_roles) else 0
    f1_tech = 2*(precision_tech*recall_tech)/(precision_tech+recall_tech) if (precision_tech+recall_tech) else 0
    
    if DEBUG_LOGGING:
        print("\n📊 Matching Metrics:")
        print(f"Role Precision: {precision_roles:.2f} (TP: {tp_roles}, Candidate Roles: {len(cand_ents['ROLES'])})")
        print(f"Role Recall: {recall_roles:.2f} (Job Roles: {len(job_ents['ROLES'])})")
        print(f"Tech Precision: {precision_tech:.2f} (TP: {tp_tech}, Candidate Tech: {len(cand_ents['TECH'])})")
        print(f"Tech Recall: {recall_tech:.2f} (Job Tech: {len(job_ents['TECH'])})")
    
    return {
        "precision": (precision_roles + precision_tech)/2,
        "recall": (recall_roles + recall_tech)/2,
        "f1_score": (f1_roles + f1_tech)/2,
        "role_metrics": {
            "precision": precision_roles,
            "recall": recall_roles,
            "f1": f1_roles
        },
        "tech_metrics": {
            "precision": precision_tech,
            "recall": recall_tech,
            "f1": f1_tech
        }
    }
def match_entities_with_bert(job, candidate):
    """Match job requirements with candidate profile using entity extraction and BERT similarity."""
    try:
        # 1. Prepare and clean text inputs
        job_text = clean_text(" ".join([
            str(job.get("title", "")),
            str(job.get("department", "")),
            str(job.get("locations", "")),
            str(job.get("work_type", "")),
            str(job.get("experience_required", "")),
            str(job.get("job_description", ""))
        ]))
        
        candidate_text = clean_text(" ".join([
            str(candidate.get("about", "")),
            str(candidate.get("experiences", "")),
            str(candidate.get("degrees", "")),
            str(candidate.get("certifications", "")),
            str(candidate.get("languages", "")),
            str(candidate.get("courses", "")),
            str(candidate.get("city", ""))
        ]))

        # if DEBUG_LOGGING:
        #     print("\n📌 Job Details:")
        #     print(f"Title: {job.get('title', '')}")
        #     print(f"Department: {job.get('department', '')}")
        #     print(f"Locations: {job.get('locations', '')}")
        #     print(f"Experience Required: {job.get('experience_required', '')}")
        #     print(f"Description Sample: {job.get('job_description', '')[:200]}...")
            
        #     print("\n📌 Candidate Details:")
        #     print(f"About Sample: {candidate.get('about', '')[:200]}...")
        #     print(f"Experience Years: {candidate.get('total_experience_years', 0)}")
        
        # 2. Extract entities from both job and candidate
        print("\n🔍 Extracting entities from job description...")
        job_ents = extract_entities(job_text, locations=job.get("locations", ""))
        print("✅ Job entities extracted:")
        print(f"- Roles: {job_ents['ROLES'] or 'None'}")
        print(f"- Tech: {job_ents['TECH'] or 'None'}")
        print(f"- Locations: {job_ents['LOCATIONS'] or 'None'}")
        print(f"- Experience: {job_ents['EXPERIENCE']} years")
        
        print("\n🔍 Extracting entities from candidate profile...")
        cand_ents = extract_entities(
            candidate_text,
            locations=f"{candidate.get('city', '')} {candidate.get('country_code', '')}",
            total_exp=candidate.get("total_experience_years", 0)
        )
        print("✅ Candidate entities extracted:")
        print(f"- Roles: {cand_ents['ROLES'] or 'None'}")
        print(f"- Tech: {cand_ents['TECH'] or 'None'}")
        print(f"- Locations: {cand_ents['LOCATIONS'] or 'None'}")
        print(f"- Experience: {cand_ents['EXPERIENCE']} years")
        
        # 3. Calculate matching metrics
        print("\n🧮 Calculating matching metrics...")
        metrics = calculate_metrics(job_ents, cand_ents)
        print("📊 Matching Metrics Results:")
        print(f"- F1 Score: {metrics['f1_score']:.2f}")
        print(f"- Precision: {metrics['precision']:.2f}")
        print(f"- Recall: {metrics['recall']:.2f}")
        print(f"- Role Metrics (P/R/F1): {metrics['role_metrics']['precision']:.2f}/{metrics['role_metrics']['recall']:.2f}/{metrics['role_metrics']['f1']:.2f}")
        print(f"- Tech Metrics (P/R/F1): {metrics['tech_metrics']['precision']:.2f}/{metrics['tech_metrics']['recall']:.2f}/{metrics['tech_metrics']['f1']:.2f}")
        
        # 4. Experience component calculation
        job_exp = job_ents["EXPERIENCE"]
        cand_exp = cand_ents["EXPERIENCE"]
        print(f"\n📅 Experience Analysis (Job: {job_exp}y vs Candidate: {cand_exp}y)")
        
        if job_exp > 0:
            experience_ratio = min(cand_exp, job_exp) / job_exp
            bonus = 0.2 * max(0, (cand_exp - job_exp)/job_exp)
            exp_component = min(experience_ratio + bonus, 1.0)
            print(f"- Experience Ratio: {experience_ratio:.2f}")
            print(f"- Bonus for excess experience: {bonus:.2f}")
        else:
            exp_component = 0
            print("- No experience requirement in job")
        print(f"- Final Experience Component: {exp_component:.2f}")
        
        # 5. Location matching (case-insensitive)
        job_locations = {loc.lower().strip() for loc in job_ents["LOCATIONS"]}
        candidate_locations = {loc.lower().strip() for loc in cand_ents["LOCATIONS"]}
        location_match = len(job_locations & candidate_locations) > 0
        print("\n📍 Location Matching:")
        print(f"- Job Locations: {job_locations or 'None'}")
        print(f"- Candidate Locations: {candidate_locations or 'None'}")
        print(f"- Common Locations: {job_locations & candidate_locations or 'None'}")
        print(f"- Location Match: {'✅' if location_match else '❌'}")
        
        # 6. Semantic similarity with error handling
        print("\n🤖 Calculating BERT Semantic Similarity...")
        try:
            sem_score = util.cos_sim(
                bert_model.encode(job_text, convert_to_tensor=True),
                bert_model.encode(candidate_text, convert_to_tensor=True)
            ).item()
            print(f"- Semantic Similarity Score: {sem_score:.4f}")
        except Exception as e:
            print(f"⚠️ BERT encoding error: {str(e)}")
            sem_score = 0
        
        # 7. Final weighted score calculation
        print("\n🧮 Calculating Final Weighted Score...")
        final_score = (
            0.25 * metrics["f1_score"] +
            0.30 * sem_score +
            0.20 * float(location_match) +
            0.25 * exp_component
        ) * 100
        
        print("\n⭐ Final Score Breakdown:")
        print(f"1. Role/Tech F1 Score: {metrics['f1_score']:.2f} → {0.25 * metrics['f1_score'] * 100:.2f} points")
        print(f"2. Semantic Similarity: {sem_score:.2f} → {0.30 * sem_score * 100:.2f} points")
        print(f"3. Location Match: {location_match} → {0.20 * location_match * 100:.2f} points")
        print(f"4. Experience: {exp_component:.2f} → {0.25 * exp_component * 100:.2f} points")
        print(f"🏆 TOTAL SCORE: {final_score:.2f}/100")

        # Return comprehensive results
        return {
            "score": round(final_score, 2),
            "semantic_similarity": round(sem_score * 100, 2),
            "precision": metrics["precision"],
            "recall": metrics["recall"],
            "f1_score": metrics["f1_score"],
            "details": {
                "matched_roles": sorted(job_ents["ROLES"] & cand_ents["ROLES"]),
                "matched_tech": sorted(job_ents["TECH"] & cand_ents["TECH"]),
                "matched_locations": sorted(job_locations & candidate_locations),
                "experience_ratio": f"{cand_exp}/{job_exp}",
                "experience_component": exp_component,
                "missing_roles": sorted(job_ents["ROLES"] - cand_ents["ROLES"]),
                "missing_tech": sorted(job_ents["TECH"] - cand_ents["TECH"])
            }
        }
        
    except Exception as e:
        print(f"\n❌❌❌ Critical Matching Error ❌❌❌")
        print(f"Error: {str(e)}")
        traceback.print_exc()
        return {
            "score": 0,
            "error": str(e),
            "details": {
                "matched_roles": [],
                "matched_tech": [],
                "matched_locations": []
            }
        }