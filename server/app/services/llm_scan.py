import json

from openai import AsyncOpenAI

from app.config import settings
from app.models.scan import Finding

_SYSTEM = """You are a senior security + code-quality auditor reviewing a GitHub \
repository, often a "vibe-coded" app built quickly with AI assistance. Such apps \
commonly ship with: hardcoded secrets, missing authz/authn checks, injection \
(SQL/command/XSS), insecure direct object references, unvalidated input, broken \
access control, and large logic flaws (wrong conditionals, race conditions, \
state mismatches, money/auth handled client-side, etc).

You are given source files and a list of findings from a static analyzer (bandit). \
Your job:
1. Find real, high-impact security vulnerabilities AND serious logic problems.
2. Triage the static findings: drop obvious false positives, keep real ones.
3. Be specific. Cite file + line. No style nitpicks, no speculative low-value noise.

Respond with JSON only:
{"findings":[{"severity":"critical|high|medium|low","category":"vuln|logic",
"file":"path","line":int|null,"title":"short","detail":"why it matters + fix",
"confidence":"high|medium|low"}]}"""


def _build_user_msg(files: dict[str, str], static: list[Finding]) -> str:
    parts = []
    if static:
        parts.append("STATIC ANALYZER FINDINGS (triage these):")
        for f in static:
            parts.append(f"- {f.file}:{f.line} [{f.severity}] {f.title}")
        parts.append("")
    parts.append("SOURCE FILES:")
    for path, content in files.items():
        parts.append(f"\n===== {path} =====\n{content}")
    return "\n".join(parts)


async def run_llm_scan(
    files: dict[str, str], static: list[Finding]
) -> tuple[list[Finding], list[str]]:
    """Return (findings, notes). notes carries non-fatal warnings."""
    if not settings.openai_api_key:
        return [], ["OPENAI_API_KEY not set; skipped LLM analysis"]
    if not files:
        return [], ["No source files eligible for LLM analysis"]

    client = AsyncOpenAI(api_key=settings.openai_api_key)
    resp = await client.chat.completions.create(
        model=settings.openai_model,
        response_format={"type": "json_object"},
        temperature=0,
        messages=[
            {"role": "system", "content": _SYSTEM},
            {"role": "user", "content": _build_user_msg(files, static)},
        ],
    )
    raw = resp.choices[0].message.content or "{}"
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return [], ["LLM returned non-JSON output; no findings parsed"]

    findings = []
    for item in data.get("findings", []):
        try:
            findings.append(
                Finding(
                    severity=item["severity"],
                    category=item["category"],
                    source="llm",
                    file=item.get("file", "?"),
                    line=item.get("line"),
                    title=item["title"],
                    detail=item.get("detail", ""),
                    confidence=item.get("confidence", "medium"),
                )
            )
        except (KeyError, ValueError):
            continue  # skip malformed entries
    return findings, []
