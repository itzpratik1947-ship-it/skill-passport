from services.role_matcher import analyze_role


def test_role_analysis_falls_back_to_passport_skills_without_job_description():
    passport = {
        "skills": [
            {"skill": "Python", "status": "Unverified", "evidence": []},
            {"skill": "SQL", "status": "Unverified", "evidence": []},
        ]
    }

    result = analyze_role(passport, role_name="Junior Developer", job_description="")

    assert len(result["requirements"]) == 2
    assert {item["skill"] for item in result["requirements"]} == {"Python", "Sql"}
    assert all(item["importance"] == "Required" for item in result["requirements"])
    assert 0 <= result["match_score"] <= 100


def test_role_analysis_with_empty_passport_and_no_description_does_not_crash():
    result = analyze_role({"skills": []}, role_name="Junior Developer", job_description="")
    assert result["requirements"] == []
    assert result["match_score"] == 0
