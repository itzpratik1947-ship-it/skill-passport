def create_learning_plan(passport, role_result=None, role_name="", job_description=""):
    gaps = []
    if role_result:
        for item in role_result.get("requirements", []):
            if item.get("status") != "Supported by available evidence":
                gaps.append(item["skill"])
    if not gaps:
        gaps = [
            skill["skill"] for skill in passport.get("skills", [])
            if skill.get("status") != "Verified" and (skill.get("assessment_score") is None or skill.get("assessment_score", 0) < 80)
        ]
    if not gaps:
        gaps = ["project documentation", "testing", "technical communication"]

    unique_gaps = list(dict.fromkeys(gaps))[:8]
    focus = unique_gaps[0] if unique_gaps else "target role fundamentals"
    weeks = [
        {
            "week": "Week 1 (Days 1-7)",
            "theme": f"Baseline and fundamentals: {focus}",
            "tasks": [
                {"title": "Map the gap", "action": f"Write down what you can currently demonstrate for {focus}, then list what the target role expects.", "deliverable": "One-page gap checklist"},
                {"title": "Study with a small scope", "action": f"Complete a focused tutorial or documentation path for {focus}. Avoid collecting courses like decorative trophies.", "deliverable": "Notes with 5 key concepts"},
                {"title": "Build a tiny exercise", "action": f"Create one small, working exercise using {focus} and commit it to a repository.", "deliverable": "Runnable example with README"},
            ],
        },
        {
            "week": "Week 2 (Days 8-14)",
            "theme": "Apply the skill",
            "tasks": [
                {"title": "Build a focused feature", "action": f"Implement a feature that uses {focus} in a realistic mini-project.", "deliverable": "Feature branch or project commit"},
                {"title": "Test the result", "action": "Add normal-case and edge-case tests; record what failed and how you fixed it.", "deliverable": "Test results and brief troubleshooting notes"},
            ],
        },
        {
            "week": "Week 3 (Days 15-21)",
            "theme": "Produce evidence",
            "tasks": [
                {"title": "Improve traceability", "action": "Write a clear README with setup steps, architecture, decisions, limitations and screenshots where useful.", "deliverable": "Readable project documentation"},
                {"title": "Ask for review", "action": "Request feedback from a peer, mentor or public technical community, then address at least one substantive point.", "deliverable": "Review notes and follow-up commit"},
            ],
        },
        {
            "week": "Week 4 (Days 22-30)",
            "theme": "Demonstrate and reflect",
            "tasks": [
                {"title": "Ship a polished version", "action": "Deploy or package the project, confirm a fresh setup works, and document the demo path.", "deliverable": "Working demo or reproducible run instructions"},
                {"title": "Update the passport", "action": "Add links to the code, tests, documentation and demo. Only upgrade a skill claim when the new evidence justifies it.", "deliverable": "Updated evidence-backed skill profile"},
            ],
        },
    ]
    return {
        "role_name": role_name,
        "weeks": weeks,
        "completion_criteria": [
            "A reviewer can run or inspect the project using the supplied instructions.",
            "At least one meaningful feature is supported by readable code and tests.",
            "Claims in the passport link to concrete evidence.",
            "Limitations and personal contributions are described honestly.",
            "The target-role gaps are reviewed again using the new evidence.",
        ],
        "prioritized_gaps": unique_gaps,
    }
