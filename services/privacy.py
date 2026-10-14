"""Privacy filters for recruiter-facing Skill Passport exports."""
from copy import deepcopy


def build_shareable_passport(
    passport,
    selected_skills=None,
    include_name=True,
    include_headline=True,
    include_evidence=True,
    include_source_links=False,
):
    """Return a detached, filtered copy suitable for preview/export.

    The original in-memory passport is never mutated. This is an export filter,
    not access control or a public hosting mechanism.
    """
    result = deepcopy(passport or {})
    candidate = result.get("candidate") or {}
    if not include_name:
        candidate["name"] = "Anonymous candidate"
    if not include_headline:
        candidate["headline"] = ""
    result["candidate"] = candidate

    allowed = set(selected_skills) if selected_skills is not None else None
    result["skills"] = [
        skill for skill in result.get("skills", [])
        if allowed is None or skill.get("skill") in allowed
    ]

    referenced_sources = set()
    for skill in result["skills"]:
        if not include_evidence:
            skill["evidence"] = []
        else:
            for evidence in skill.get("evidence", []):
                source_name = evidence.get("source_name") or evidence.get("source")
                if source_name:
                    referenced_sources.add(source_name)
                if not include_source_links:
                    evidence.pop("url", None)
                    evidence.pop("source_url", None)

    # Do not leak filenames or metadata for sources unrelated to the selected public skills.
    if include_evidence:
        result["sources"] = [
            {key: value for key, value in source.items() if key in {"source_name", "source_type", "url"}}
            for source in result.get("sources", [])
            if source.get("source_name") in referenced_sources
        ]
    else:
        result["sources"] = []
    if not include_source_links:
        for source in result.get("sources", []):
            source["url"] = ""
    result["sharing_settings"] = {
        "include_name": bool(include_name),
        "include_headline": bool(include_headline),
        "include_evidence": bool(include_evidence),
        "include_source_links": bool(include_source_links),
        "selected_skill_count": len(result.get("skills", [])),
    }
    return result
