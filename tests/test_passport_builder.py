from services.passport_builder import build_passport

def test_ai_quote_not_in_source_is_rejected():
    source = {
        "source_id": "resume",
        "source_type": "resume",
        "source_name": "resume.txt",
        "url": "",
        "owner_confirmed": False,
        "content": "Skills: Python",
    }
    ai_result = {
        "skills": [{
            "skill": "Python",
            "summary": "Strong Python engineer",
            "level": "Expert",
            "status": "Verified",
            "confidence": 0.99,
            "evidence": [{
                "source_name": "resume.txt",
                "quote": "Built a production Python system serving millions",
                "location": "resume.txt",
                "explanation": "Claimed expertise",
                "evidence_type": "resume_claim",
                "strength": "strong",
            }],
            "limitations": [],
        }],
        "notes": [],
    }
    result = build_passport({"name": "", "headline": ""}, [source], [], ai_result)
    assert result["skills"] == []
    assert any("Rejected a quotation" in note for note in result["notes"])

def test_repository_ownership_not_confirmed_cannot_be_verified():
    source = {
        "source_id": "repo",
        "source_type": "github_repository",
        "source_name": "owner/project",
        "url": "",
        "owner_confirmed": False,
        "content": "def build():\n    return 'x'\n",
    }
    ai_result = {
        "skills": [{
            "skill": "Python",
            "summary": "Python code exists",
            "level": "Intermediate",
            "status": "Verified",
            "confidence": 0.9,
            "evidence": [{
                "source_name": "owner/project",
                "quote": "def build():",
                "location": "app.py: line 1",
                "explanation": "Python function",
                "evidence_type": "code",
                "strength": "strong",
            }],
            "limitations": [],
        }],
        "notes": [],
    }
    result = build_passport({"name": "", "headline": ""}, [source], [], ai_result)
    assert result["skills"][0]["status"] == "Partially supported"

def test_candidate_self_attestation_never_makes_ai_skill_verified():
    source = {
        "source_id": "repo", "source_type": "github_repository", "source_name": "owner/project",
        "url": "https://github.com/owner/project", "owner_confirmed": True,
        "content": "def build():\n    return 'x'\n",
    }
    ai_result = {"skills": [{
        "skill": "Python", "summary": "Code exists", "level": "Intermediate", "status": "Verified", "confidence": 0.9,
        "evidence": [{"source_name": "owner/project", "quote": "def build():", "location": "app.py:1", "explanation": "Function", "evidence_type": "code", "strength": "strong"}],
        "limitations": [],
    }], "notes": []}
    result = build_passport({"name": "", "headline": ""}, [source], [], ai_result)
    assert result["skills"][0]["status"] == "Partially supported"
    assert "independent issuer verification" in " ".join(result["skills"][0]["limitations"])
