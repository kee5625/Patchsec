from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

Severity = Literal["critical", "high", "medium", "low", "info"]
Category = Literal["vuln", "logic"]
Source = Literal["static", "llm"]
JobState = Literal["queued", "running", "done", "error"]


class ScanRequest(BaseModel):
    git_url: str
    github_token: str | None = None


class Finding(BaseModel):
    severity: Severity
    category: Category
    source: Source
    file: str
    line: int | None = None
    title: str
    detail: str
    confidence: Literal["high", "medium", "low"] = "medium"


class ScanResult(BaseModel):
    repo: str
    head: str
    findings: list[Finding] = Field(default_factory=list)
    files_scanned: int = 0
    files_skipped: int = 0
    truncated: bool = False
    notes: list[str] = Field(default_factory=list)


class Job(BaseModel):
    id: str
    state: JobState = "queued"
    progress: str = "queued"
    git_url: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    result: ScanResult | None = None
    error: str | None = None
