import re

ALIASES = {
    "ml": "machine learning", "machine-learning": "machine learning",
    "gen ai": "generative ai", "llms": "generative ai", "large language models": "generative ai",
    "restful api": "rest apis", "api": "rest apis", "apis": "rest apis",
    "js": "javascript", "ts": "typescript", "postgres": "sql", "postgresql": "sql",
}

def _normalize(text):
    value = re.sub(r"[^a-z0-9+#. ]", " ", str(text).lower())
    value = " ".join(value.split())
    return ALIASES.get(value, value)

def analyze_role(passport, role_name="", job_description=""):
    skills = passport.get("skills", [])
    known = {_normalize(s["skill"]): s for s in skills}
    text = (job_description or "").strip()
    if not text:
        text = role_name or ""
    requirements = _extract_requirements(text)
    if not requirements:
        # Keep the same (skill, importance) shape returned by _extract_requirements.
        # This fallback is used when the user enters only a role name or leaves the
        # job description blank.
        requirements = [(_normalize(s["skill"]), "Required") for s in skills]
    results = []
    weights = {"Required": 3, "Preferred": 1}
    total_weight = 0
    earned_weight = 0

    for requirement, importance in requirements:
        weight = weights[importance]
        total_weight += weight
        match = known.get(_normalize(requirement))
        if not match:
            status = "No supporting evidence found"
            reason = "No matching skill claim was extracted from the submitted sources. This is not proof the candidate lacks the skill."
            evidence = []
            credit = 0
        else:
            evidence = [
                f"{ev.get('source_name', ev.get('source', 'source'))}: {ev.get('quote', '')[:140]}"
                for ev in match.get("evidence", [])[:3]
            ]
            assessment_score = match.get("assessment_score")
            if assessment_score is not None:
                try:
                    score_value = max(0, min(100, int(assessment_score)))
                except (TypeError, ValueError):
                    score_value = 0
                status = "Assessment evidence · prototype"
                credit = 0.75 if score_value >= 80 else 0.6 if score_value >= 60 else 0.35
                reason = f"The learner scored {score_value}/100 on this prototype quiz. It contributes limited evidence but is not an accredited or proctored assessment."
            elif match.get("status") == "Verified":
                status, credit = "Supported by available evidence", 1
                reason = "A matching claim is marked supported, but review the linked evidence and its limitations."
            elif match.get("status") == "Partially supported":
                status, credit = "Partially supported", 0.5
                reason = "Some evidence exists, but it does not fully establish proficiency or authorship."
            elif match.get("status") == "Conflicting":
                status, credit = "Conflicting evidence", 0.25
                reason = "Sources disagree; this requirement needs human review."
            else:
                status, credit = "Unverified evidence", 0.25
                reason = "A possible signal exists, but proficiency is not verified."
        earned_weight += weight * credit
        results.append({
            "skill": requirement.title(),
            "importance": importance,
            "status": status,
            "reason": reason,
            "matched_evidence": evidence,
        })

    score = round(100 * earned_weight / total_weight) if total_weight else 0
    return {
        "role_name": role_name,
        "match_score": score,
        "summary": f"The prototype found evidence for {sum(1 for r in results if r['matched_evidence'])} of {len(results)} listed requirements. The score reflects evidence coverage and support status, not a prediction of job performance.",
        "requirements": results,
        "limitations": [
            "Requirement extraction is keyword-based in the local role matcher; paste a focused job description for better coverage.",
            "The score uses explicit prototype weights: Required = 3, Preferred = 1; fully supported = 1.0 credit, partial = 0.5, unverified = 0.25, no evidence = 0.",
            "Equivalent skill names and nuanced seniority requirements may not be matched perfectly.",
        ],
    }

def _extract_requirements(text):
    aliases = {
        "python": "Python", "javascript": "JavaScript", "typescript": "TypeScript",
        "react": "React", "java": "Java", "kotlin": "Kotlin", "c++": "C++",
        "sql": "SQL", "docker": "Docker", "git": "Git", "github": "Git",
        "machine learning": "Machine Learning", "generative ai": "Generative AI",
        "llm": "Generative AI", "rest api": "REST APIs", "rest apis": "REST APIs",
        "streamlit": "Streamlit", "pandas": "Data Analysis", "data analysis": "Data Analysis",
        "pytorch": "Machine Learning", "tensorflow": "Machine Learning",
    }
    found = {}
    low = text.lower()
    for phrase, skill in aliases.items():
        if re.search(r"(?<!\w)" + re.escape(phrase) + r"(?!\w)", low):
            importance = "Required"
            # Conservative cue: requirements explicitly described as a plus/preferred are lower weight.
            match = re.search(r".{0,55}" + re.escape(phrase) + r".{0,55}", low)
            context = match.group(0) if match else ""
            if any(cue in context for cue in ("preferred", "nice to have", "bonus", "plus")):
                importance = "Preferred"
            found[skill] = (skill, importance)
    return list(found.values())
