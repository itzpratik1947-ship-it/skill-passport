"""Skill-specific quiz generation and transparent assessment scoring.

AI generation is optional. The local question bank keeps the demo functional without API access.
Scores measure performance on this prototype assessment, not an accredited certification.
"""
import json
import os
import re
import requests
from dotenv import load_dotenv

load_dotenv()
ENDPOINT = "https://api.groq.com/openai/v1/chat/completions"

BANK = {
    "python": [
        ("What does a Python dictionary store?", ["Only ordered numbers", "Key-value pairs", "Only unique characters", "Compiled machine code"], 1, "A dictionary maps keys to values."),
        ("What is the purpose of a function?", ["To group reusable logic", "To install packages", "To encrypt every variable", "To replace all loops"], 0, "Functions package reusable behavior behind a name."),
        ("Which construct handles an exception?", ["if/else only", "for/in", "try/except", "class/import"], 2, "try/except handles selected runtime exceptions."),
        ("What does a list comprehension create?", ["A database", "A list from an expression and iterable", "A virtual machine", "A network request"], 1, "A list comprehension builds a list from an iterable."),
        ("Why use a virtual environment?", ["To isolate project dependencies", "To make code automatically correct", "To replace tests", "To publish a package"], 0, "Virtual environments isolate installed dependencies."),
    ],
    "sql": [
        ("Which clause filters rows before grouping?", ["ORDER BY", "WHERE", "HAVING", "LIMIT"], 1, "WHERE filters rows before grouping."),
        ("What does a PRIMARY KEY guarantee?", ["Rows are sorted", "Each row has a unique non-null identifier", "Every column is text", "Queries never fail"], 1, "A primary key uniquely identifies each row and cannot be null."),
        ("Which join returns matching rows from both tables?", ["INNER JOIN", "CROSS JOIN", "FULL OUTER JOIN", "No join"], 0, "INNER JOIN returns rows with matching join conditions."),
        ("What does GROUP BY do?", ["Deletes duplicates from a table", "Groups rows for aggregate calculations", "Renames columns", "Encrypts values"], 1, "GROUP BY groups rows for aggregate functions."),
        ("What is a parameterized query mainly used for?", ["Making SQL colorful", "Reducing SQL injection risk", "Removing indexes", "Creating charts"], 1, "Parameters keep data separate from SQL syntax."),
    ],
    "javascript": [
        ("Which declaration is block-scoped and cannot be reassigned?", ["var", "let", "const", "function"], 2, "const bindings cannot be reassigned."),
        ("What does an async function return?", ["A Promise", "A CSS rule", "Always a string", "A database cursor"], 0, "An async function returns a Promise."),
        ("What is an array map operation used for?", ["Transforming each element", "Sorting a server", "Opening a socket only", "Declaring a class"], 0, "map transforms elements into a new array."),
        ("What does JSON.parse do?", ["Turns a JSON string into a JavaScript value", "Encrypts a password", "Creates a web server", "Formats CSS"], 0, "JSON.parse parses JSON text."),
        ("Why handle a rejected Promise?", ["To observe or recover from failure", "To guarantee success", "To disable the event loop", "To remove all types"], 0, "Rejected promises need explicit error handling when failure matters."),
    ],
    "git": [
        ("What does a Git commit represent?", ["A saved snapshot in repository history", "A cloud backup guaranteed forever", "A pull request review", "A running server"], 0, "A commit records a repository snapshot and metadata."),
        ("What does git pull generally do?", ["Fetches and integrates remote changes", "Deletes all branches", "Creates a programming language", "Encrypts a repository"], 0, "git pull fetches and integrates remote changes."),
        ("Why use a branch?", ["To isolate a line of development", "To make every test pass", "To publish secrets", "To replace commits"], 0, "Branches allow parallel development."),
        ("What should you do with API keys?", ["Commit them publicly", "Store them in environment secrets", "Put them in README screenshots", "Use the same key everywhere"], 1, "Secrets should not be committed to source control."),
        ("What is a pull request for?", ["Proposing and reviewing changes", "Running a local variable", "Changing file encoding only", "Creating a database automatically"], 0, "Pull requests support review and integration of changes."),
    ],
    "machine learning": [
        ("What is a test set used for?", ["Final evaluation on held-out data", "Training every epoch", "Storing passwords", "Choosing a UI theme"], 0, "Held-out test data estimates generalization after model choices are made."),
        ("What is overfitting?", ["Good performance on training data but poor generalization", "A model with no parameters", "A missing CSV header", "A faster network"], 0, "Overfit models learn training-specific patterns that do not generalize."),
        ("Why split data before fitting preprocessing?", ["To avoid leaking test-set information", "To increase file size", "To guarantee 100% accuracy", "To remove all labels"], 0, "Fitting preprocessing on test data leaks information."),
        ("What does precision measure?", ["Correct positive predictions among predicted positives", "All negatives in the dataset", "Training time", "Number of model layers"], 0, "Precision = true positives / (true positives + false positives)."),
        ("Why compare against a baseline?", ["To know whether complexity improves results", "To hide model errors", "To avoid evaluation", "To make labels optional"], 0, "A baseline provides a reference for judging model value."),
    ],
}


def _bank_for(skill):
    name = (skill or "").lower()
    for key, questions in BANK.items():
        if key in name or (key == "git" and "github" in name):
            return questions
    return [
        (f"For {skill}, which is the strongest way to demonstrate practical ability?", ["Only list it on a resume", "Complete a task and explain the decisions", "Claim expert status", "Copy a tutorial without understanding it"], 1, "A task plus an explanation provides more useful evidence than a bare claim."),
        (f"When learning {skill}, what is a useful first step?", ["Skip fundamentals", "Define a small measurable task", "Memorize buzzwords", "Avoid feedback"], 1, "A small task creates observable progress and feedback."),
        (f"How should you handle a result you cannot reproduce in {skill}?", ["Report it as proven", "Hide the failure", "Investigate and document the limitation", "Delete the evidence"], 2, "Reproducibility and honest limitations improve evidence quality."),
        (f"What is the best way to validate work involving {skill}?", ["Use no checks", "Run relevant tests or independent checks", "Rely only on appearance", "Assume the first output is correct"], 1, "Tests and independent checks catch errors that appearance misses."),
        (f"Which statement about a self-reported {skill} is accurate?", ["It is automatically certified", "It is a claim until supported by evidence", "It proves expert level", "It needs no context"], 1, "A claim should be distinguished from assessment and issuer verification."),
    ]


def generate_quiz(skill, previous_score=None, count=5):
    """Return quiz questions. Use Groq for adaptive variants when configured, local bank otherwise."""
    key = os.getenv("GROQ_API_KEY", "").strip()
    if key:
        try:
            model = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile").strip()
            prompt = (f"Create {count} concise multiple-choice assessment questions for skill: {skill}. "
                      f"Prior score: {previous_score if previous_score is not None else 'first attempt'}/100. "
                      "If score under 60, focus on fundamentals; 60-79, intermediate application; 80+, practical edge cases. "
                      "Return JSON {questions:[{question,options:[four strings],answer_index:0-3,explanation,task_prompt}]} . "
                      "Exactly four options; one defensible answer; no trick questions; no claim of certification.")
            r = requests.post(ENDPOINT, headers={"Authorization": f"Bearer {key}"}, json={
                "model": model, "messages": [{"role": "system", "content": "Return valid JSON only."}, {"role": "user", "content": prompt}],
                "temperature": 0.3, "response_format": {"type": "json_object"}
            }, timeout=35)
            r.raise_for_status()
            data = r.json()["choices"][0]["message"]["content"]
            data = re.sub(r"^```(?:json)?\s*|\s*```$", "", data.strip(), flags=re.I)
            parsed = json.loads(data)
            valid = []
            for q in parsed.get("questions", [])[:count]:
                opts = q.get("options", [])
                idx = q.get("answer_index")
                if q.get("question") and len(opts) == 4 and isinstance(idx, int) and 0 <= idx < 4:
                    valid.append({"question": str(q["question"]), "options": [str(x) for x in opts], "answer_index": idx,
                                  "explanation": str(q.get("explanation", "")), "task_prompt": str(q.get("task_prompt", ""))})
            if len(valid) >= 3:
                for q in valid:
                    q.setdefault("task_prompt", f"Build a small {skill} example, test it, and explain one design decision and one limitation.")
                return valid, "Groq-generated adaptive assessment"
        except Exception:
            pass
    questions = _bank_for(skill)
    shift = 0 if previous_score is None else (2 if previous_score >= 80 else 1 if previous_score >= 60 else 0)
    questions = questions[shift:] + questions[:shift]
    return [{"question": q[0], "options": q[1], "answer_index": q[2], "explanation": q[3],
             "task_prompt": f"Practical task: create a small {skill} example that solves a real problem. Include a test or validation step, explain one design choice, and state one limitation."} for q in questions[:count]], "Built-in adaptive assessment (offline fallback)"


def grade_quiz(questions, answers):
    total = len(questions)
    correct = sum(1 for i, q in enumerate(questions) if answers.get(str(i)) is not None and int(answers[str(i)]) == q["answer_index"])
    score = round(100 * correct / total) if total else 0
    return {"score": score, "correct": correct, "total": total,
            "level": "Advanced" if score >= 85 else "Intermediate" if score >= 65 else "Beginner" if score >= 40 else "Needs practice",
            "status": "Assessment completed · prototype", "completed_at": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(timespec="seconds"),
            "limitations": "Short multiple-choice assessment; not proctored or externally certified. Complete the practical task for stronger evidence."}
