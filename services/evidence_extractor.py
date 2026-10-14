import re
from pathlib import PurePosixPath

EXTENSION_SKILLS = {
    ".py": "Python", ".js": "JavaScript", ".jsx": "JavaScript", ".mjs": "JavaScript",
    ".ts": "TypeScript", ".tsx": "TypeScript", ".java": "Java", ".kt": "Kotlin",
    ".kts": "Kotlin", ".cpp": "C++", ".cc": "C++", ".cxx": "C++", ".go": "Go",
    ".rs": "Rust", ".php": "PHP", ".swift": "Swift", ".sql": "SQL",
}
PATTERNS = {
    "Python": [r"\bdef\s+\w+\s*\(", r"\bclass\s+\w+\s*:", r"^\s*(?:import|from)\s+\w+"],
    "JavaScript": [r"\bfunction\s+\w+\s*\(", r"\b(?:const|let)\s+\w+\s*=", r"=>"],
    "TypeScript": [r"\binterface\s+\w+", r"\btype\s+\w+\s*=", r"\bexport\s+(?:type|interface|class|function)\b"],
    "Java": [r"\bpublic\s+class\s+\w+", r"\bpublic\s+static\s+void\s+main\s*\("],
    "Kotlin": [r"\bfun\s+\w+\s*\(", r"\bdata\s+class\s+\w+", r"\bval\s+\w+"],
    "C++": [r"#include\s*<[^>]+>", r"\bint\s+main\s*\(", r"\bstd::\w+"],
    "Go": [r"^\s*func\s+\w+\s*\(", r"^\s*package\s+\w+"],
    "Rust": [r"\bfn\s+\w+\s*\(", r"\bstruct\s+\w+", r"\bimpl\s+\w+"],
    "SQL": [r"\b(?:SELECT|INSERT\s+INTO|CREATE\s+TABLE|UPDATE)\b"],
    "Docker": [r"^\s*(?:FROM|RUN|CMD|ENTRYPOINT|EXPOSE|WORKDIR|COPY)\s+"],
}
STRONG_PATTERNS = {
    "Python": [r"\bdef\s+\w+\s*\(", r"\bclass\s+\w+\s*:"],
    "JavaScript": [r"\bfunction\s+\w+\s*\(", r"=>"],
    "TypeScript": [r"\binterface\s+\w+", r"\btype\s+\w+\s*="],
    "Java": [r"\bpublic\s+class\s+\w+", r"\bpublic\s+static\s+void\s+main\s*\("],
    "Kotlin": [r"\bfun\s+\w+\s*\(", r"\bdata\s+class\s+\w+"],
    "C++": [r"\bint\s+main\s*\(", r"\bstd::\w+"],
    "Go": [r"^\s*func\s+\w+\s*\("],
    "Rust": [r"\bfn\s+\w+\s*\(", r"\bimpl\s+\w+"],
    "SQL": [r"\bCREATE\s+TABLE\b", r"\bSELECT\b.+\bFROM\b"],
    "Docker": [r"^\s*FROM\s+", r"^\s*ENTRYPOINT\s+"],
}
DOC_SKILL_TERMS = {
    "Python": ["python"], "JavaScript": ["javascript", "js"], "TypeScript": ["typescript"],
    "React": ["react", "react.js"], "Java": ["java"], "Kotlin": ["kotlin"],
    "C++": ["c++"], "Go": ["golang", "go language"], "Rust": ["rust"],
    "SQL": ["sql", "postgresql", "mysql", "sqlite"], "Docker": ["docker", "containerization"],
    "Machine Learning": ["machine learning", "scikit-learn", "pytorch", "tensorflow"],
    "Generative AI": ["generative ai", "llm", "large language model", "gemini api", "openai api"],
    "Streamlit": ["streamlit"], "Git": ["git", "github"], "REST APIs": ["rest api", "http api", "api integration"],
    "Data Analysis": ["data analysis", "pandas", "data visualization"],
}

def extract_rule_based_evidence(source_record):
    content = source_record.get("content", "")
    source_name = source_record.get("source_name", "Unknown source")
    source_type = source_record.get("source_type", "document")
    results = []
    seen = set()

    for path, file_content in _split_repository_content(content, source_type):
        ext = PurePosixPath(path).suffix.lower()
        filename = PurePosixPath(path).name.lower()
        skills = []
        if ext in EXTENSION_SKILLS:
            skills.append(EXTENSION_SKILLS[ext])
        if filename.startswith("dockerfile") or filename == "containerfile":
            skills.append("Docker")
        for line_number, line in enumerate(file_content.splitlines(), start=1):
            stripped = line.strip()
            if not stripped or stripped.startswith(("#", "//", "/*", "*")):
                continue
            for skill in skills:
                patterns = PATTERNS.get(skill, [])
                if any(re.search(pattern, stripped, flags=re.IGNORECASE) for pattern in patterns):
                    key = (skill, path, line_number, stripped)
                    if key not in seen:
                        seen.add(key)
                        strong = any(re.search(p, stripped, flags=re.IGNORECASE) for p in STRONG_PATTERNS.get(skill, []))
                        results.append({
                            "skill": skill, "source_name": source_name, "source": path,
                            "location": f"{path}: line {line_number}",
                            "quote": stripped[:500], "explanation": f"Code pattern associated with {skill}.",
                            "evidence_type": "code_pattern", "strength": "strong" if strong else "medium",
                            "attribution_status": "candidate_confirmed" if source_record.get("owner_confirmed") else "not_independently_verified",
                            "source_type": source_type,
                        })

    # Document evidence uses short, exact source sentences rather than keyword-only claims.
    if source_type != "github_repository":
        for line_number, line in enumerate(content.splitlines(), start=1):
            stripped = line.strip().lstrip("-*• ")
            if len(stripped) < 12:
                continue
            low = stripped.lower()
            for skill, terms in DOC_SKILL_TERMS.items():
                if any(term in low for term in terms):
                    key = (skill, line_number, stripped)
                    if key in seen:
                        continue
                    seen.add(key)
                    results.append({
                        "skill": skill, "source_name": source_name, "source": source_name,
                        "location": f"{source_name}: line {line_number}",
                        "quote": stripped[:500],
                        "explanation": f"The source explicitly mentions {skill}; this mention alone does not prove proficiency.",
                        "evidence_type": "document_mention", "strength": "weak",
                        "attribution_status": "document_claim_not_independently_verified",
                        "source_type": source_type,
                    })
    return results

def _split_repository_content(content, source_type):
    if source_type != "github_repository":
        return [(source_type, content)]
    parts = re.split(r"(?m)^### FILE: (.+)$", content)
    result = []
    # Format is [prefix, path1, body1, path2, body2, ...]
    for index in range(1, len(parts), 2):
        path = parts[index].strip()
        body = parts[index + 1] if index + 1 < len(parts) else ""
        result.append((path, body))
    return result
