from fastapi import APIRouter, HTTPException

from app.models.scan import Job, ScanRequest
from app.services.extractor import extract_repo
from app.services.jobs import get_job, start_scan

router = APIRouter(tags=["analysis"])


@router.post("/scan", response_model=Job)
async def create_scan(req: ScanRequest):
    return start_scan(req.git_url, req.github_token)


@router.get("/scan/{job_id}", response_model=Job)
async def scan_status(job_id: str):
    job = get_job(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    return job


@router.get("/extract")
async def extract(git_url: str):
    """Raw repo extraction (files, branches, metadata) without analysis."""
    repo = await extract_repo(git_url)
    return {
        "metadata": repo.metadata,
        "branches": repo.branches,
        "files": repo.files,
        "truncated": repo.truncated,
    }
