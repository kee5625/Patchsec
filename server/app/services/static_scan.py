import asyncio
import json
import os
import subprocess
import sys
import tempfile

from app.models.scan import Finding

_SEV_MAP = {"HIGH": "high", "MEDIUM": "medium", "LOW": "low"}
_CONF_MAP = {"HIGH": "high", "MEDIUM": "medium", "LOW": "low"}


def _run_bandit_sync(files: dict[str, str]) -> list[Finding]:
    with tempfile.TemporaryDirectory(prefix="patchsec_") as tmp:
        for rel, content in files.items():
            dest = os.path.join(tmp, rel)
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            with open(dest, "w", encoding="utf-8") as f:
                f.write(content)

        # bandit exits 1 when issues found; that is not an error for us.
        proc = subprocess.run(
            [sys.executable, "-m", "bandit", "-r", tmp, "-f", "json", "-q"],
            capture_output=True,
            text=True,
        )
        try:
            data = json.loads(proc.stdout or "{}")
        except json.JSONDecodeError:
            return []

        findings = []
        for r in data.get("results", []):
            rel = os.path.relpath(r["filename"], tmp).replace("\\", "/")
            findings.append(
                Finding(
                    severity=_SEV_MAP.get(r.get("issue_severity", "LOW"), "low"),
                    category="vuln",
                    source="static",
                    file=rel,
                    line=r.get("line_number"),
                    title=f'{r.get("test_id", "")}: {r.get("issue_text", "")[:80]}',
                    detail=r.get("issue_text", ""),
                    confidence=_CONF_MAP.get(r.get("issue_confidence", "MEDIUM"), "medium"),
                )
            )
        return findings


async def run_bandit(files: dict[str, str]) -> list[Finding]:
    """Write Python files to a temp dir, run bandit in a thread, return findings.

    Uses a worker thread (not asyncio subprocess) because uvicorn's Windows
    SelectorEventLoop raises NotImplementedError on create_subprocess_exec.
    """
    py_files = {p: c for p, c in files.items() if p.endswith(".py")}
    if not py_files:
        return []
    return await asyncio.to_thread(_run_bandit_sync, py_files)
