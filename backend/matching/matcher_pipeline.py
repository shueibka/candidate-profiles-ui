import re
from sentence_transformers import SentenceTransformer, util
from spacy.matcher import Matcher
import spacy

DEBUG_LOGGING = True
bert_model = SentenceTransformer("all-MiniLM-L6-v2")
nlp_en = spacy.load("en_core_web_sm")
nlp_sv = spacy.load("sv_core_news_sm")

# Skill extraction patterns
SKILL_PATTERNS = [
    {"label": "SKILL", "pattern": [
        {"LOWER": {"IN": ["proficient", "skilled", "experienced"]}},
        {"LOWER": "in"},
        {"POS": {"IN": ["NOUN", "PROPN"]}}
    ]},
    {"label": "SKILL", "pattern": [
        {"LOWER": "skills"},
        {"LOWER": ":"},
        {"IS_ASCII": True, "OP": "+"}
    ]},
    {"label": "SKILL", "pattern": [
        {"LOWER": "expertise"},
        {"LOWER": "in"},
        {"POS": {"IN": ["NOUN", "PROPN"]}}
    ]}
]

def is_swedish(text):
    return any(word in text.lower() for word in ["och", "att", "för", "med", "inte"])

def clean_text(text):
    return re.sub(r"\s+", " ", text or "").strip()

def extract_structured_skills(text):
    skills = set()
    lang = "sv" if is_swedish(text) else "en"
    nlp_model = nlp_sv if lang == "sv" else nlp_en
    doc = nlp_model(text)
    matcher = Matcher(nlp_model.vocab)

    for pattern in SKILL_PATTERNS:
        matcher.add(pattern["label"], [pattern["pattern"]])

    for match_id, start, end in matcher(doc):
        skills.add(doc[start:end].text.lower())

    return skills

def extract_relationships(text):
    relations = []
    pattern = r"(?P<subject>\b[A-Z][a-z]+) (?:worked at|joined|collaborated with|developed|built|used|managed|designed|led) (?P<object>[A-Z][a-zA-Z0-9\-& ]+)"
    for match in re.finditer(pattern, text):
        relations.append((match.group("subject"), match.group("object")))
    return relations

def calculate_semantic_similarity(text1, text2):
    if not text1 or not text2:
        return 0.0
    embeddings = bert_model.encode([text1, text2], convert_to_tensor=True)
    return util.cos_sim(embeddings[0], embeddings[1]).item()

def match_entities_with_bert(job, candidate):
    # Combine fields for job
    job_text = " ".join([
        job.get("title", ""),
        job.get("department", ""),
        job.get("locations", ""),
        job.get("work_type", ""),
        job.get("experience_required", ""),
        str(job.get("total_experience_years") or ""),
        job.get("job_description", "")
    ])

    # Combine fields for candidate
    candidate_text = " ".join([
        candidate.get("about", ""),
        candidate.get("experiences", ""),
        candidate.get("degrees", ""),
        candidate.get("certifications", ""),
        candidate.get("skills", ""),
        candidate.get("courses", ""),
        candidate.get("languages", "")
    ])

    job_text = clean_text(job_text)
    candidate_text = clean_text(candidate_text)

    job_skills = extract_structured_skills(job_text)
    candidate_skills = extract_structured_skills(candidate_text)

    job_rels = extract_relationships(job_text)
    cand_rels = extract_relationships(candidate_text)

    if DEBUG_LOGGING:
        print("\n🔗 Job Relationships:", job_rels)
        print("🔗 Candidate Relationships:", cand_rels)

    intersection = job_skills & candidate_skills
    true_positive = len(intersection)
    false_positive = len(candidate_skills - job_skills)
    false_negative = len(job_skills - candidate_skills)

    precision = true_positive / (true_positive + false_positive) if (true_positive + false_positive) else 0.0
    recall = true_positive / (true_positive + false_negative) if (true_positive + false_negative) else 0.0
    f1_score = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0

    exact_score = true_positive / len(job_skills) if job_skills else 0.0
    semantic_score = calculate_semantic_similarity(job_text, candidate_text)
    final_score = round((0.7 * exact_score + 0.3 * semantic_score) * 100, 2)

    if DEBUG_LOGGING:
        print("\n🧶 SCORE BREAKDOWN:")
        print(f"Exact Skill Match: {exact_score * 100:.1f}%")
        print(f"Semantic Similarity: {semantic_score * 100:.1f}%")
        print(f"Final Score: {final_score:.1f}%")
        print(f"Precision: {precision:.2f}")
        print(f"Recall: {recall:.2f}")
        print(f"F1 Score: {f1_score:.2f}")

    return {
        "score": final_score,
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1_score": round(f1_score, 4)
    }
