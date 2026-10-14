from datetime import datetime, timezone
from difflib import SequenceMatcher

VALID_LEVELS = {"Beginner", "Intermediate", "Advanced", "Expert", "Not assessed"}
VALID_STATUSES = {"Verified", "Partially supported", "Unverified", "Conflicting"}

def build_passport(candidate, sources, rule_evidence, ai_result=None):
    source_text = {}
    for source in sources:
        source_text[source.get("source_name", "")] = source.get("content", "")
    candidates = list(rule_evidence or [])
    notes = [
        "Repository presence does not prove personal authorship or proficiency.",
        "Candidate confirmation is self-attestation, not independent verification.",
        "A missing evidence item does not prove that the candidate lacks the skill.",
    ]
    if ai_result:
        notes.extend(str(n) for n in ai_result.get("notes", []) if n)
        for claim in ai_result.get("skills", []):
            skill = str(claim.get("skill", "")).strip()
            if not skill:
                continue
            evs = []
            for raw_ev in claim.get("evidence", [])[:8]:
                quote = str(raw_ev.get("quote", "")).strip()
                source_name = str(raw_ev.get("source_name", "")).strip()
                if not quote or not source_name:
                    continue
                actual_source = source_text.get(source_name, "")
                if not _quote_is_present(quote, actual_source):
                    notes.append(f"Rejected a quotation for {skill} because it could not be validated against the provided source text.")
                    continue
                matching = next((s for s in sources if s.get("source_name") == source_name), {})
                evs.append({
                    "source_name": source_name,
                    "source": source_name,
                    "location": str(raw_ev.get("location", source_name)),
                    "quote": quote,
                    "explanation": str(raw_ev.get("explanation", "")),
                    "evidence_type": str(raw_ev.get("evidence_type", "ai_extracted")),
                    "strength": raw_ev.get("strength", "weak") if raw_ev.get("strength") in {"strong", "medium", "weak"} else "weak",
                    "attribution_status": "candidate_confirmed" if matching.get("owner_confirmed") else "not_independently_verified",
                })
            if evs:
                candidates.append({
                    "skill": skill,
                    "source_name": evs[0]["source_name"],
                    "source": evs[0]["source"],
                    "location": evs[0]["location"],
                    "quote": evs[0]["quote"],
                    "explanation": str(claim.get("summary", "")),
                    "evidence_type": "ai_claim",
                    "strength": "medium",
                    "attribution_status": evs[0]["attribution_status"],
                    "_ai_level": claim.get("level", "Not assessed"),
                    "_ai_status": claim.get("status", "Partially supported"),
                    "_ai_confidence": claim.get("confidence", 0.5),
                    "_ai_limitations": claim.get("limitations", []),
                    "_all_evidence": evs,
                })

    grouped = {}
    for ev in candidates:
        skill = str(ev.get("skill", "")).strip()
        if not skill:
            continue
        grouped.setdefault(skill.lower(), {"skill": skill, "evidence": [], "ai_claim": None})
        if ev.get("_all_evidence"):
            grouped[skill.lower()]["ai_claim"] = ev
            grouped[skill.lower()]["evidence"].extend(ev["_all_evidence"])
        else:
            grouped[skill.lower()]["evidence"].append(ev)

    skills = []
    for group in grouped.values():
        evidence = _deduplicate_evidence(group["evidence"])
        ai_claim = group.get("ai_claim")
        if not evidence:
            continue
        if ai_claim:
            proposed_level = ai_claim.get("_ai_level", "Not assessed")
            proposed_status = ai_claim.get("_ai_status", "Partially supported")
            confidence = _safe_confidence(ai_claim.get("_ai_confidence", 0.5))
            limitations = [str(x) for x in ai_claim.get("_ai_limitations", []) if x]
            summary = ai_claim.get("explanation", "")
        else:
            proposed_level = "Not assessed"
            proposed_status = "Unverified"
            confidence = 0.35
            limitations = ["Rule-based pattern detection identifies a possible technology signal, not demonstrated proficiency."]
            summary = "Potential skill signal detected from source content."

        # Strict trust guard: self-attestation and AI extraction are never independent verification.
        # Only a separately verified issuer credential may use the formal Verified status.
        independently_issuer_verified = any(
            ev.get("issuer_verified") is True and ev.get("evidence_type") == "issuer_verified_certificate"
            for ev in evidence
        )
        if proposed_status == "Verified" and not independently_issuer_verified:
            proposed_status = "Partially supported"
            limitations.append("No independent issuer verification was performed; candidate confirmation and AI analysis are not certification.")
        if proposed_status not in VALID_STATUSES:
            proposed_status = "Partially supported" if evidence else "Unverified"
        if proposed_level not in VALID_LEVELS:
            proposed_level = "Not assessed"
        if not ai_claim:
            proposed_status = "Unverified"
        skills.append({
            "skill": group["skill"],
            "level": proposed_level,
            "status": proposed_status,
            "confidence": confidence,
            "summary": summary,
            "evidence": evidence[:12],
            "limitations": list(dict.fromkeys(limitations)),
        })

    skills.sort(key=lambda x: (-len(x["evidence"]), x["skill"].lower()))
    source_summaries = []
    for source in sources:
        source_summaries.append({
            "source_id": source.get("source_id"),
            "source_type": source.get("source_type"),
            "source_name": source.get("source_name"),
            "url": source.get("url", ""),
            "owner_confirmed": bool(source.get("owner_confirmed")),
        })
    return {
        "passport_id": "sp-" + datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S"),
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "candidate": candidate,
        "sources": source_summaries,
        "skills": skills,
        "notes": list(dict.fromkeys(notes)),
    }

def _quote_is_present(quote, source_text):
    if not source_text:
        return False
    if quote in source_text:
        return True
    normalized_quote = " ".join(quote.split())
    normalized_source = " ".join(source_text.split())
    if normalized_quote and normalized_quote in normalized_source:
        return True
    return SequenceMatcher(None, normalized_quote, normalized_source[:max(len(normalized_quote) * 3, 1000)]).ratio() > 0.98

def _deduplicate_evidence(evidence):
    result = []
    seen = set()
    for ev in evidence:
        key = (ev.get("source_name"), ev.get("location"), ev.get("quote"))
        if key not in seen:
            seen.add(key)
            result.append(ev)
    return result

def _safe_confidence(value):
    try:
        return max(0.0, min(1.0, float(value)))
    except (TypeError, ValueError):
        return 0.3
