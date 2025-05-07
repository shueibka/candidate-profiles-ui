import re
from sentence_transformers import SentenceTransformer, util
from spacy.matcher import Matcher
import spacy

DEBUG_LOGGING = True
bert_model = SentenceTransformer("all-MiniLM-L6-v2")
nlp_en = spacy.load("en_core_web_sm")
nlp_sv = spacy.load("sv_core_news_sm")

def is_swedish(text):
    return any(tok in text.lower() for tok in ["och", "att", "för", "med", "inte"])

def clean_text(text):
    return re.sub(r"\s+", " ", text or "").strip()

# 1) extract structured skills exactly as before…
SKILL_PATTERNS = [
    # … your existing patterns …
]

def extract_structured_skills(text):
    skills = set()
    # first comma-list after “skills:”
    for m in re.finditer(r"skills\s*:\s*([^\.]+)", text, flags=re.IGNORECASE):
        for s in m.group(1).split(","):
            skills.add(s.strip().lower())
    # then spaCy matcher
    lang = "sv" if is_swedish(text) else "en"
    doc = (nlp_sv if lang=="sv" else nlp_en)(text)
    matcher = Matcher(doc.vocab)
    for p in SKILL_PATTERNS:
        matcher.add(p["label"], [p["pattern"]])
    for _, start, end in matcher(doc):
        skills.add(doc[start:end].text.lower())
    return skills

# 2) pure NER
def extract_entities(text):
    doc = nlp_en(text)
    ents = {"GPE": set(), "LOC": set(), "ORG": set(), "PRODUCT": set()}
    for ent in doc.ents:
        if ent.label_ in ents:
            ents[ent.label_].add(ent.text)
    return ents

# 3) relationship patterns
def extract_relationships(text):
    relations = []
    verbs = r"(?:worked at|joined|collaborated with|developed|built|used|managed|designed|led|experience\s(?:in|with)|skilled in|are a|are an)"
    pat1 = rf"(?P<sub>[A-Z][\w &]+?)\s+(?:{verbs})\s+(?P<obj>[A-Z][\w &]+)"
    for m in re.finditer(pat1, text, flags=re.IGNORECASE):
        relations.append((m.group("sub").strip(), m.group("obj").strip()))
    for m in re.finditer(r"platforms\s+such\s+as\s+(?P<list>[^\.]+)", text, flags=re.IGNORECASE):
        for item in re.split(r",|\band\b", m.group("list")):
            v = item.strip()
            if v:
                relations.append(("platforms", v))
    for m in re.finditer(r"Role\s*:\s*(?P<role>[^\.]+)", text, flags=re.IGNORECASE):
        relations.append(("Role", m.group("role").strip()))
    return relations

# 4) the main pipeline
def match_entities_with_bert(job, candidate):
    # build the job text
    job_text = clean_text(" ".join([
        job.get("title", ""),
        job.get("department", ""),
        job.get("locations", ""),
        job.get("work_type", ""),
        job.get("experience_required", ""),
        str(job.get("total_experience_years", "")),
        job.get("required_skills", ""),
        job.get("preferred_skills", ""),
        job.get("job_description", ""),
    ]))

    # build the candidate text (now including skills and city)
    cand_text = clean_text(" ".join([
        candidate.get("about", ""),
        candidate.get("experiences", ""),
        candidate.get("degrees", ""),
        candidate.get("certifications", ""),
        candidate.get("courses", ""),
        candidate.get("languages", ""),
        candidate.get("skills", ""),    # ← pull in the skills field
        candidate.get("city", ""),      # ← pull in the city so spaCy can see it
    ]))

    # 1) structured skills
    job_skills = extract_structured_skills(job_text)
    cand_skills = extract_structured_skills(cand_text)

    # 2) relationships
    job_rels = extract_relationships(job_text)
    cand_rels = extract_relationships(cand_text)

    # 3) pure NER
    job_ents = extract_entities(job_text)
    cand_ents = extract_entities(cand_text)

    if DEBUG_LOGGING:
        print("🔗 Job Relationships:", job_rels)
        print("🔗 Candidate Relationships:", cand_rels)
        print("🏷️ Job Entities:", job_ents)
        print("🏷️ Candidate Entities:", cand_ents)

    # you can now look at shared GPEs (e.g. cities)
    shared_locations = job_ents["GPE"] & cand_ents["GPE"]
    if DEBUG_LOGGING and shared_locations:
        print("🚩 Shared Locations:", shared_locations)

    # exact / semantic scoring
    tp = len(job_skills & cand_skills)
    fp = len(cand_skills - job_skills)
    fn = len(job_skills - cand_skills)
    precision = tp / (tp + fp) if tp + fp else 0
    recall    = tp / (tp + fn) if tp + fn else 0
    f1        = 2 * precision * recall / (precision + recall) if precision + recall else 0
    exact     = tp / len(job_skills) if job_skills else 0

    sem_score = util.cos_sim(
        bert_model.encode(job_text, convert_to_tensor=True),
        bert_model.encode(cand_text, convert_to_tensor=True),
    ).item()

    final_score = round((0.7 * exact + 0.3 * sem_score) * 100, 2)

    if DEBUG_LOGGING:
        print(f"Exact Skill Match: {exact*100:.1f}%")
        print(f"Semantic Sim: {sem_score*100:.1f}% → Final {final_score:.1f}%")
        print(f"P={precision:.2f} R={recall:.2f} F1={f1:.2f}")

    return {
        "score": final_score,
        "precision": round(precision, 4),
        "recall":    round(recall, 4),
        "f1_score":  round(f1, 4),
    }
