from services.assessment import generate_quiz, grade_quiz


def test_offline_quiz_has_four_options_and_task_prompts(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    questions, source = generate_quiz("Python", count=5)
    assert len(questions) == 5
    assert all(len(q["options"]) == 4 for q in questions)
    assert all(q["task_prompt"] for q in questions)
    assert "offline" in source.lower()


def test_quiz_score_is_bounded_and_correct():
    questions, _ = generate_quiz("SQL")
    answers = {str(i): q["answer_index"] for i, q in enumerate(questions)}
    result = grade_quiz(questions, answers)
    assert result["score"] == 100
    assert result["correct"] == result["total"]
    assert result["level"] == "Advanced"
    result = grade_quiz(questions, {})
    assert result["score"] == 0
