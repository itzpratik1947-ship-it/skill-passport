from copy import deepcopy

from services.privacy import build_shareable_passport


def sample_passport():
    return {
        "passport_id": "sp-test",
        "candidate": {"name": "Ada Example", "headline": "Python learner"},
        "sources": [{"source_name": "repo", "url": "https://github.com/example/repo"}],
        "skills": [
            {
                "skill": "Python",
                "level": "Not assessed",
                "status": "Unverified",
                "evidence": [{
                    "source_name": "repo", "quote": "print('hello')",
                    "explanation": "A code example exists.",
                }],
            },
            {"skill": "SQL", "level": "Not assessed", "status": "Unverified", "evidence": []},
        ],
        "notes": ["Prototype only"],
    }


def test_shareable_passport_filters_skills_and_identity_without_mutating_original():
    original = sample_passport()
    before = deepcopy(original)
    shared = build_shareable_passport(
        original,
        selected_skills=["Python"],
        include_name=False,
        include_headline=False,
        include_evidence=True,
        include_source_links=False,
    )
    assert [s["skill"] for s in shared["skills"]] == ["Python"]
    assert shared["candidate"]["name"] == "Anonymous candidate"
    assert shared["candidate"]["headline"] == ""
    assert shared["sources"][0]["url"] == ""
    assert original == before


def test_shareable_passport_can_remove_evidence_entirely():
    shared = build_shareable_passport(sample_passport(), include_evidence=False)
    assert all(skill["evidence"] == [] for skill in shared["skills"])


def test_shareable_passport_keeps_source_links_only_when_selected():
    shared = build_shareable_passport(sample_passport(), include_source_links=True)
    assert shared["sources"][0]["url"] == "https://github.com/example/repo"
