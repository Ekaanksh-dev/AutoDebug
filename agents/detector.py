# AutoDebug — Multi-Agent Bug Fixing System
# Copyright 2026 Ekaanksh (github.com/Ekaanksh-dev)
# Licensed under Apache License 2.0

import os
import subprocess
import requests
from pathlib import Path
from dotenv import load_dotenv
from core.context import BugContext
from band.client import BandClient

load_dotenv()

band = BandClient("DetectorAgent")


def get_headers() -> dict:
    return {
        "Authorization": f"token {os.getenv('GITHUB_TOKEN')}",
        "Accept": "application/vnd.github.v3+json"
    }


def clone_repo(repo_name: str, commit_sha: str) -> str:
    token = os.getenv("GITHUB_TOKEN")
    clone_url = f"https://{token}@github.com/{repo_name}.git"
    clone_path = f"/tmp/{repo_name.replace('/', '_')}"
    subprocess.run(["rm", "-rf", clone_path])
    band.log(f"Cloning {repo_name}...")
    subprocess.run(["git", "clone", clone_url, clone_path], capture_output=True)
    subprocess.run(["git", "checkout", commit_sha], cwd=clone_path, capture_output=True)
    band.log(f"✅ Cloned to {clone_path}")
    return clone_path


def get_failed_run(repo_name: str) -> dict:
    """Find the latest failed GitHub Actions run"""
    runs = requests.get(
        f"https://api.github.com/repos/{repo_name}/actions/runs?per_page=10",
        headers=get_headers()
    ).json()

    for run in runs.get("workflow_runs", []):
        if run["conclusion"] == "failure":
            band.log(f"Found failed run: {run['id']}")
            return {
                "found": True,
                "run_id": run["id"],
                "run_url": run["html_url"]
            }

    return {"found": False}


def get_log_text(repo_name: str, run_id: int) -> str:
    """Get plain text log from failed job"""
    band.log("Downloading logs...")

    jobs = requests.get(
        f"https://api.github.com/repos/{repo_name}/actions/runs/{run_id}/jobs",
        headers=get_headers()
    ).json()

    failed_job_id = None
    for job in jobs.get("jobs", []):
        if job["conclusion"] == "failure":
            failed_job_id = job["id"]
            band.log(f"Failed job: {job['name']} (id: {job['id']})")
            break

    if not failed_job_id:
        return ""

    log_response = requests.get(
        f"https://api.github.com/repos/{repo_name}/actions/jobs/{failed_job_id}/logs",
        headers=get_headers(),
        allow_redirects=True
    )

    return log_response.text[:10000]


def extract_bug_from_log(log: str, clone_path: str = "") -> dict:
    """Parse error from log text"""
    error_types = [
        "SyntaxError", "TypeError", "ValueError", "KeyError",
        "AttributeError", "ImportError", "IndexError", "NameError",
        "ZeroDivisionError", "FileNotFoundError", "RuntimeError",
        "AssertionError", "ModuleNotFoundError", "PermissionError"
    ]

    error_type = "UnknownError"
    error_message = ""
    bug_file = ""
    bug_line = 0

    lines = log.split("\n")
    for line in lines:
        # Strip GitHub Actions timestamps
        if "Z " in line:
            line = line.split("Z ", 1)[-1]

        for et in error_types:
            if et in line:
                error_type = et
                error_message = line.strip()

        if "File " in line and ", line " in line:
            try:
                parts = line.strip().split(",")
                bug_file = parts[0].replace("File ", "").strip().strip('"')
                # Strip clone path to get relative path
                if clone_path and bug_file.startswith(clone_path):
                    bug_file = bug_file[len(clone_path):].lstrip("/")
                bug_line = int(parts[1].replace("line", "").strip())
            except:
                pass

    return {
        "error_type": error_type,
        "error_message": error_message,
        "bug_file": bug_file,
        "bug_line": bug_line
    }


def fallback_local_scan(clone_path: str) -> dict:
    """Fallback — execute Python files and catch errors directly"""
    band.log("⚡ Fallback: scanning files locally...")

    for py_file in sorted(Path(clone_path).rglob("*.py")):
        if any(p in str(py_file) for p in [".git", "venv", "__pycache__", ".github"]):
            continue

        result = subprocess.run(
            ["python", str(py_file)],
            capture_output=True, text=True, timeout=10
        )

        if result.returncode != 0 and result.stderr:
            band.log(f"🐛 Error found in {py_file.name}")
            return {
                "found": True,
                "log": result.stderr,
                "run_url": f"file://{py_file}"
            }

    return {"found": False}


def get_surrounding_code(file_path: str, line: int, window: int = 10) -> str:
    try:
        with open(file_path, "r") as f:
            lines = f.readlines()
        start = max(0, line - window)
        end = min(len(lines), line + window)
        return "".join(f"{start + i + 1}: {l}" for i, l in enumerate(lines[start:end]))
    except:
        return ""


def run(repo_name: str, commit_sha: str, branch: str) -> BugContext:
    band.log(f"🔍 Starting detection on {repo_name}")

    ctx = BugContext(
        repo_name=repo_name,
        repo_url=f"https://github.com/{repo_name}",
        branch=branch,
        commit_sha=commit_sha,
        current_agent="DetectorAgent"
    )

    log_text = ""
    run_url = ""
    clone_path = f"/tmp/{repo_name.replace('/', '_')}"

    # Step 1 — check GitHub Actions for failed run
    failed_run = get_failed_run(repo_name)

    if failed_run["found"]:
        log_text = get_log_text(repo_name, failed_run["run_id"])
        run_url = failed_run["run_url"]
        band.log("✅ Got log from GitHub Actions")
        # Clone repo for code context
        clone_path = clone_repo(repo_name, commit_sha)
    else:
        # Step 2 — fallback: clone and scan locally
        band.log("No failed Actions run — trying local scan...")
        clone_path = clone_repo(repo_name, commit_sha)
        fallback = fallback_local_scan(clone_path)

        if not fallback["found"]:
            band.log("✅ No errors found anywhere")
            ctx.pipeline_complete = True
            return ctx

        log_text = fallback["log"]
        run_url = fallback["run_url"]

    # Step 3 — extract bug from log
    bug = extract_bug_from_log(log_text, clone_path)
    ctx.error_type = bug["error_type"]
    ctx.error_message = bug["error_message"]
    ctx.bug_file = bug["bug_file"]
    ctx.bug_line = bug["bug_line"]
    ctx.repo_url = run_url

    # Step 4 — get surrounding code
    full_path = os.path.join(clone_path, ctx.bug_file)
    ctx.surrounding_code = get_surrounding_code(full_path, ctx.bug_line)

    # Step 5 — read full file
    try:
        with open(full_path, "r") as f:
            ctx.raw_code = f.read()
    except:
        ctx.raw_code = ""

    band.log(f"🐛 Bug detected: {ctx.summary()}")

    # Step 6 — send to Analyser via Band
    band.send("AnalyserAgent", ctx.to_dict())

    return ctx
