from services.evidence_extractor import extract_rule_based_evidence

def test_python_evidence_has_source_location():
    source = {
        "source_id": "repo",
        "source_type": "github_repository",
        "source_name": "owner/project",
        "owner_confirmed": False,
        "content": "### FILE: app.py\nimport streamlit as st\n\ndef main():\n    return 1\n",
    }
    results = extract_rule_based_evidence(source)
    assert any(item["skill"] == "Python" for item in results)
    assert all(item.get("quote") for item in results)
    assert all(item.get("location") for item in results)

def test_resume_keyword_is_weak_document_evidence():
    source = {
        "source_id": "resume",
        "source_type": "resume",
        "source_name": "resume.txt",
        "owner_confirmed": True,
        "content": "Skills: Python, SQL and machine learning",
    }
    results = extract_rule_based_evidence(source)
    assert results
    assert all(item["strength"] == "weak" for item in results)
