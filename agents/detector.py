# AutoDebug — Multi-Agent Bug Fixing System
# Copyright 2026 Ekaanksh (github.com/Ekaanksh-dev)
# Licensed under Apache License 2.0

import os
import subprocess
import requests
from dotenv import load_dotenv
from core.context import BugContext
from band.client import BandClient

load_dotenv()

band = BandClient("DetectorAgent")


def clone_repo(repo_name: str, commit_sha: str) -> str:
    """Clone the triggered repo locally"""
    token = os.getenv("GITHUB_TOKEN")
    clone_url = f"https://{token}@github.com/{repo_name}.git"
    clone_path = f"/tmp/{repo_name.replace('/', '_')}"

    # Remove if already exists
    subprocess.run(["rm", "-rf", clone_path])

    band.log(f"Cloning {repo_name}...")
    subprocess.run(["git", "clone", clone_url, clone_path], capture_output=True)

    # Checkout specific commit
    subprocess.run(
        ["git", "checkout", commit_sha],
        cwd=clone_path,
        capture_output=True
    )

    band.log(f"✅ Cloned to {clone_path}")
    return clone_path


def get_error_from_actions(repo_name: str) -> dict:
    """Fetch latest failed GitHub Actions log"""
    token = os.getenv("GITHUB_TOKEN")
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json"
    }

    # Get latest workflow runs
    runs_url = f"https://api.github.com/repos/{repo_name}/actions/runs"
    runs = requests.get(runs_url, headers=headers).json()

    # Find latest failed run
    for run in runs.get("workflow_runs", []):
        if run["conclusion"] == "failure":
            band.log(f"Found failed run: {run['id']}")

            # Get logs URL
            logs_url = f"https://api.github.com/repos/{repo_name}/actions/runs/{run['id']}/logs"
            logs_response = requests.get(logs_url, headers=headers)

            return {
                "error_found": True,
                "run_id": run["id"],
                "run_url": run["html_url"],
                "log": logs_response.text[:3000]  # first 3000 chars
            }

    return {"error_found": False}


def extract_bug_from_log(log: str) -> dict:
    """Parse error type and message from log"""
    error_types = [
        "SyntaxError", "TypeError", "ValueError", "KeyError",
        "AttributeError", "ImportError", "IndexError", "NameError",
        "ZeroDivisionError", "FileNotFoundError", "RuntimeError"
    ]

    error_type = "UnknownError"
    error_message = ""
    bug_file = ""
    bug_line = 0

    for line in log.split("\n"):
        # Find error type
        for et in error_types:
            if et in line:
                error_type = et
                error_message = line.strip()

        # Find file and line number
        if "File " in line and ", line " in line:
            try:
                parts = line.strip().split(",")
                bug_file = parts[0].replace("File ", "").strip().strip('"')
                bug_line = int(parts[1].replace("line", "").strip())
            except:
                pass

    return {
        "error_type": error_type,
        "error_message": error_message,
        "bug_file": bug_file,
        "bug_line": bug_line
    }


def get_surrounding_code(file_path: str, line: int, window: int = 10) -> str:
    """Get code around the bug line"""
    try:
        with open(file_path, "r") as f:
            lines = f.readlines()

        start = max(0, line - window)
        end = min(len(lines), line + window)
        snippet = lines[start:end]

        return "".join(
            f"{start + i + 1}: {l}" for i, l in enumerate(snippet)
        )
    except:
        return ""


def run(repo_name: str, commit_sha: str, branch: str) -> BugContext:
    """Main detector function — entry point of pipeline"""
    band.log(f"🔍 Starting detection on {repo_name}")

    ctx = BugContext(
        repo_name=repo_name,
        repo_url=f"https://github.com/{repo_name}",
        branch=branch,
        commit_sha=commit_sha,
        current_agent="DetectorAgent"
    )

    # Step 1 — Get error from GitHub Actions
    error_data = get_error_from_actions(repo_name)

    if not error_data["error_found"]:
        band.log("✅ No errors found in latest run")
        ctx.pipeline_complete = True
        return ctx

    # Step 2 — Clone repo
    clone_path = clone_repo(repo_name, commit_sha)

    # Step 3 — Extract bug details from log
    bug = extract_bug_from_log(error_data["log"])
    ctx.error_type = bug["error_type"]
    ctx.error_message = bug["error_message"]
    ctx.bug_file = bug["bug_file"]
    ctx.bug_line = bug["bug_line"]

    # Step 4 — Get surrounding code
    full_path = os.path.join(clone_path, bug["bug_file"].lstrip("/"))
    ctx.surrounding_code = get_surrounding_code(full_path, bug["bug_line"])

    # Step 5 — Read full file
    try:
        with open(full_path, "r") as f:
            ctx.raw_code = f.read()
    except:
        ctx.raw_code = ""

    band.log(f"🐛 Bug detected: {ctx.summary()}")

    # Step 6 — Send to Analyser via Band
    band.send("AnalyserAgent", ctx.to_dict())

    return ctx
