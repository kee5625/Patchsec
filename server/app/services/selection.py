import re

# Caps to bound cost/latency on big (often vibe-coded) repos.
# Total stays under ~gpt-4o 128k-token ceiling (~400k chars) for single-call scan.
MAX_FILES = 250
MAX_TOTAL_CHARS = 800_000
MAX_FILE_CHARS = 80_000  # per-file cap fed to LLM (head of file)

SKIP_DIR = re.compile(
    r"(^|/)(node_modules|\.git|dist|build|out|vendor|\.next|\.venv|venv|"
    r"__pycache__|\.cache|coverage|target|bin|obj)(/|$)"
)
SKIP_FILE = re.compile(
    r"(\.min\.(js|css)$|\.map$|package-lock\.json$|yarn\.lock$|"
    r"pnpm-lock\.yaml$|poetry\.lock$|uv\.lock$|\.lock$|\.svg$)"
)
SOURCE_EXT = re.compile(
    r"\.(py|js|jsx|ts|tsx|go|rb|php|java|cs|rs|c|cpp|h|sh|sql|"
    r"vue|svelte|env|yaml|yml|toml|json|html)$"
)


def _eligible(path: str, content: str | None) -> bool:
    if content is None:
        return False
    if SKIP_DIR.search(path) or SKIP_FILE.search(path):
        return False
    return bool(SOURCE_EXT.search(path))


def select_files(files: dict[str, str | None]) -> tuple[dict[str, str], int, bool]:
    """Return (selected {path: content}, skipped_count, truncated)."""
    eligible = {p: c for p, c in files.items() if _eligible(p, c)}
    skipped = len(files) - len(eligible)

    # Prefer source code over config; smaller first to fit more files in budget.
    def rank(item):
        path, content = item
        is_code = bool(
            re.search(r"\.(py|js|jsx|ts|tsx|go|rb|php|java|cs|rs|vue|svelte)$", path)
        )
        return (0 if is_code else 1, len(content))

    ordered = sorted(eligible.items(), key=rank)

    selected: dict[str, str] = {}
    total = 0
    truncated = False
    for path, content in ordered:
        if len(selected) >= MAX_FILES:
            truncated = True
            break
        snippet = content[:MAX_FILE_CHARS]
        if len(content) > MAX_FILE_CHARS:
            truncated = True
        if total + len(snippet) > MAX_TOTAL_CHARS:
            truncated = True
            break
        selected[path] = snippet
        total += len(snippet)

    return selected, skipped, truncated
