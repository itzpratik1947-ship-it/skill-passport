from services.exporter import passport_markdown, passport_html


def test_assessment_score_is_present_in_exports():
    passport = {"passport_id": "SP-TEST", "created_at": "today", "candidate": {"name": "Demo", "headline": "Learner"},
                "skills": [{"skill": "Python", "level": "Intermediate", "status": "Assessment completed · prototype", "confidence": 0.7,
                            "assessment_score": 80, "assessment_level": "Intermediate", "summary": "Quiz result", "evidence": []}], "notes": []}
    assert "80/100" in passport_markdown(passport)
    assert "80/100" in passport_html(passport)
