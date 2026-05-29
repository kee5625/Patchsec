import asyncio
import base64
import re

import httpx
from fastapi import HTTPException

from app.config import settings

GITHUB_API = "https://api.github.com"
BLOB_CONCURRENCY = 10
MAX_BLOB_BYTES = 100_000  # skip files larger than this


def parse_repo(git_url: str) -> tuple[str, str]:
    m = re.search(r"github\.com[:/]([^/]+)/([^/.]+)", git_url)
    if not m:
        raise HTTPException(400, f"Not a GitHub URL: {git_url}")
    return m.group(1), m.group(2)


def _headers(token: str | None = None) -> dict[str, str]:
    h = {"Accept": "application/vnd.github+json"}
    token = token or settings.github_token
    if token:
        h["Authorization"] = f"Bearer {token}"
    return h


async def _get(client: httpx.AsyncClient, path: str) -> dict | list:
    r = await client.get(f"{GITHUB_API}{path}")
    if r.status_code == 404:
        raise HTTPException(404, f"Not found: {path}")
    if r.status_code == 403 and r.headers.get("X-RateLimit-Remaining") == "0":
        raise HTTPException(429, "GitHub rate limit exceeded; set GITHUB_TOKEN")
    r.raise_for_status()
    return r.json()


async def _fetch_blob(
    client: httpx.AsyncClient,
    owner: str,
    repo: str,
    path: str,
    sha: str,
    sem: asyncio.Semaphore,
) -> tuple[str, str | None]:
    async with sem:
        blob = await _get(client, f"/repos/{owner}/{repo}/git/blobs/{sha}")
    if blob.get("encoding") != "base64" or not blob.get("content"):
        return path, None
    raw = base64.b64decode(blob["content"])
    try:
        return path, raw.decode()
    except UnicodeDecodeError:
        return path, None  # binary


class ExtractedRepo:
    def __init__(self, owner, repo, metadata, branches, files, truncated):
        self.owner = owner
        self.repo = repo
        self.full_name = f"{owner}/{repo}"
        self.metadata = metadata
        self.branches = branches
        self.files = files  # dict[path, str | None]
        self.truncated = truncated


async def extract_repo(git_url: str, token: str | None = None) -> ExtractedRepo:
    owner, repo = parse_repo(git_url)

    async with httpx.AsyncClient(headers=_headers(token), timeout=30.0) as client:
        info = await _get(client, f"/repos/{owner}/{repo}")
        ref = info["default_branch"]

        commit, branches_raw, tree = await asyncio.gather(
            _get(client, f"/repos/{owner}/{repo}/commits/{ref}"),
            _get(client, f"/repos/{owner}/{repo}/branches"),
            _get(client, f"/repos/{owner}/{repo}/git/trees/{ref}?recursive=1"),
        )

        blobs = [
            n
            for n in tree["tree"]
            if n["type"] == "blob" and n.get("size", 0) <= MAX_BLOB_BYTES
        ]
        sem = asyncio.Semaphore(BLOB_CONCURRENCY)
        results = await asyncio.gather(
            *(
                _fetch_blob(client, owner, repo, n["path"], n["sha"], sem)
                for n in blobs
            )
        )

    metadata = {
        "head": commit["sha"],
        "author": commit["commit"]["author"]["name"],
        "message": commit["commit"]["message"].strip(),
        "committed_date": commit["commit"]["author"]["date"],
        "remotes": [info["clone_url"]],
    }
    return ExtractedRepo(
        owner=owner,
        repo=repo,
        metadata=metadata,
        branches=[b["name"] for b in branches_raw],
        files=dict(results),
        truncated=tree.get("truncated", False),
    )
