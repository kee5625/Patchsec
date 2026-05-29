import asyncio
import uuid

from app.models.scan import Finding, Job, ScanResult
from app.services.extractor import extract_repo
from app.services.llm_scan import run_llm_scan
from app.services.selection import select_files
from app.services.static_scan import run_bandit

_SEV_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}

# In-memory store. Lost on restart; single-process only. Swap for Redis later.
_jobs: dict[str, Job] = {}


def create_job(git_url: str) -> Job:
    job = Job(id=uuid.uuid4().hex[:12], git_url=git_url)
    _jobs[job.id] = job
    return job


_tokens: dict[str, str | None] = {}


def get_job(job_id: str) -> Job | None:
    return _jobs.get(job_id)


def _merge(static: list[Finding], llm: list[Finding]) -> list[Finding]:
    # Drop static findings the LLM already reported (same file+line).
    llm_keys = {(f.file, f.line) for f in llm}
    merged = llm + [f for f in static if (f.file, f.line) not in llm_keys]
    merged.sort(key=lambda f: (_SEV_ORDER.get(f.severity, 9), f.file))
    return merged


async def run_scan(job_id: str) -> None:
    job = _jobs[job_id]
    try:
        job.state = "running"

        job.progress = "fetching repo via GitHub API"
        repo = await extract_repo(job.git_url, _tokens.get(job_id))

        job.progress = "selecting files"
        selected, skipped, sel_trunc = select_files(repo.files)

        job.progress = "static analysis (bandit)"
        static = await run_bandit(selected)

        job.progress = "LLM analysis (OpenAI)"
        llm, notes = await run_llm_scan(selected, static)

        job.progress = "merging findings"
        findings = _merge(static, llm)

        job.result = ScanResult(
            repo=repo.full_name,
            head=repo.metadata["head"],
            findings=findings,
            files_scanned=len(selected),
            files_skipped=skipped,
            truncated=repo.truncated or sel_trunc,
            notes=notes,
        )
        job.state = "done"
        job.progress = "done"
    except Exception as e:  # noqa: BLE001 - surface any failure to caller
        job.state = "error"
        job.error = f"{type(e).__name__}: {e}"
        job.progress = "error"
    finally:
        _tokens.pop(job_id, None)


def start_scan(git_url: str, github_token: str | None = None) -> Job:
    job = create_job(git_url)
    _tokens[job.id] = github_token
    asyncio.create_task(run_scan(job.id))
    return job
