import io
import re
import zipfile
from urllib.parse import urlparse

import requests

MAX_REPO_BYTES = 18 * 1024 * 1024
MAX_FILES = 350
MAX_FILE_CHARS = 9000
ALLOWED_EXTENSIONS = {
    ".py", ".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx", ".java", ".kt", ".kts",
    ".cpp", ".cc", ".c", ".h", ".hpp", ".cs", ".go", ".rs", ".php", ".swift",
    ".html", ".css", ".json", ".toml", ".yaml", ".yml", ".md", ".txt", ".sql",
    ".sh", ".xml", ".gradle", ".properties"
}
IMPORTANT_NAMES = {
    "readme", "readme.md", "requirements.txt", "pyproject.toml", "package.json",
    "pom.xml", "cargo.toml", "go.mod", "dockerfile", "docker-compose.yml",
    "docker-compose.yaml", "build.gradle", "build.gradle.kts"
}
IGNORED_PARTS = {
    "node_modules", "vendor", ".git", "dist", "build", ".venv", "venv",
    "__pycache__", "coverage", ".next", "target"
}

def parse_github_url(url):
    parsed = urlparse(url.strip())
    if parsed.scheme not in {"http", "https"} or parsed.netloc.lower() not in {"github.com", "www.github.com"}:
        raise ValueError("Enter a public GitHub repository URL, such as https://github.com/owner/repository.")
    parts = [p for p in parsed.path.strip("/").split("/") if p]
    if len(parts) < 2:
        raise ValueError("The URL must include both the repository owner and repository name.")
    owner, repo = parts[0], parts[1]
    repo = re.sub(r"\.git$", "", repo)
    if not owner or not repo:
        raise ValueError("Could not identify the repository owner/name.")
    return owner, repo

def fetch_github_repository(url):
    owner, repo = parse_github_url(url)
    headers = {"User-Agent": "SkillPassportPrototype/1.0", "Accept": "application/vnd.github+json"}
    last_error = None
    for branch in ("main", "master", "develop"):
        archive_url = f"https://codeload.github.com/{owner}/{repo}/zip/refs/heads/{branch}"
        try:
            response = requests.get(archive_url, headers=headers, timeout=25, stream=True)
            if response.status_code == 404:
                last_error = f"Branch '{branch}' was not found."
                continue
            response.raise_for_status()
            chunks = []
            size = 0
            for chunk in response.iter_content(chunk_size=64 * 1024):
                if not chunk:
                    continue
                size += len(chunk)
                if size > MAX_REPO_BYTES:
                    raise ValueError("Repository archive exceeds the 18 MB prototype limit. Try a smaller repository.")
                chunks.append(chunk)
            payload = b"".join(chunks)
            with zipfile.ZipFile(io.BytesIO(payload)) as archive:
                names = archive.namelist()
                if not names:
                    raise ValueError("The repository archive is empty.")
                root = names[0].split("/")[0]
                candidates = []
                for name in names:
                    if name.endswith("/"):
                        continue
                    relative = name[len(root) + 1:] if name.startswith(root + "/") else name
                    parts = relative.split("/")
                    if any(part.lower() in IGNORED_PARTS for part in parts):
                        continue
                    filename = parts[-1]
                    ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
                    if filename.lower() not in IMPORTANT_NAMES and ext not in ALLOWED_EXTENSIONS:
                        continue
                    try:
                        info = archive.getinfo(name)
                        if info.file_size > MAX_FILE_CHARS * 8:
                            continue
                        raw = archive.read(name)
                        content = raw.decode("utf-8", errors="replace")
                    except (KeyError, RuntimeError, OSError):
                        continue
                    score = 100 if filename.lower() in IMPORTANT_NAMES else 50
                    if any(p.lower() in {"src", "app", "core", "backend", "frontend", "lib"} for p in parts[:-1]):
                        score += 25
                    candidates.append((score, relative, content[:MAX_FILE_CHARS]))
                candidates.sort(key=lambda x: (-x[0], x[1].lower()))
                selected = candidates[:MAX_FILES]
                files = {path: content for _, path, content in selected}
                if not files:
                    raise ValueError("No readable source or documentation files were found in this repository.")
                return {
                    "owner": owner,
                    "repo": repo,
                    "branch": branch,
                    "url": f"https://github.com/{owner}/{repo}",
                    "files": files,
                    "files_available": len(files),
                    "truncated": len(candidates) > MAX_FILES,
                }
        except requests.RequestException as exc:
            last_error = str(exc)
    raise ValueError(f"Could not download the repository archive. Check that it is public and the URL is correct. {last_error or ''}")
