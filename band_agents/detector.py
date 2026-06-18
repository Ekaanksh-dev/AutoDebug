# AutoDebug — Multi-Agent Bug Fixing System
# Copyright 2026 Ekaanksh (github.com/Ekaanksh-dev)
# Licensed under Apache License 2.0

import os
import json
import subprocess
import requests
from pathlib import Path
from dotenv import load_dotenv
from band import Agent
from band.config import load_agent_config
from band.core.simple_adapter import SimpleAdapter
from band.core.types import PlatformMessage
from band.core.protocols import AgentToolsProtocol

load_dotenv()

CONFIG_PATH = Path(__file__).resolve().parent.parent / "agent_config.yaml"
agent_id, api_key = load_agent_config("detector", config_path=CONFIG_PATH)

def get_headers() -> dict:
    return {
        "Authorization": f"token {os.getenv('GITHUB_TOKEN')}",
        "Accept": "application/vnd.github.v3+json"
    }


def clone_repo(repo_name: str, commit_sha: str) -> str:
    print("CLONING:", repo_name)
    print("CHECKOUT:", commit_sha)

    token = os.getenv("GITHUB_TOKEN")
    clone_url = f"https://{token}@github.com/{repo_name}.git"
    clone_path = f"/tmp/{repo_name.replace('/', '_')}"
    subprocess.run(["rm", "-rf", clone_path])
    subprocess.run(["git", "clone", clone_url, clone_path], capture_output=True)
    subprocess.run(["git", "checkout", commit_sha], cwd=clone_path, capture_output=True)
    return clone_path


def get_failed_run(repo_name: str) -> dict:
    runs = requests.get(
        f"https://api.github.com/repos/{repo_name}/actions/runs?per_page=10",
        headers=get_headers()
    ).json()
    for run in runs.get("workflow_runs", []):
        if run["conclusion"] == "failure":
            return {"found": True, "run_id": run["id"], "run_url": run["html_url"]}
    return {"found": False}


def get_log_text(repo_name: str, run_id: int) -> str:
    jobs = requests.get(
        f"https://api.github.com/repos/{repo_name}/actions/runs/{run_id}/jobs",
        headers=get_headers()
    ).json()
    failed_job_id = None
    for job in jobs.get("jobs", []):
        if job["conclusion"] == "failure":
            failed_job_id = job["id"]
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
    for line in log.split("\n"):
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
                if clone_path and bug_file.startswith(clone_path):
                    bug_file = bug_file[len(clone_path):].lstrip("/")
                bug_line = int(parts[1].replace("line", "").strip())
            except:
                pass
    return {"error_type": error_type, "error_message": error_message,
            "bug_file": bug_file, "bug_line": bug_line}


def fallback_local_scan(clone_path: str) -> dict:
    for py_file in sorted(Path(clone_path).rglob("*.py")):
        if any(p in str(py_file) for p in [".git", "venv", "__pycache__", ".github"]):
            continue
        result = subprocess.run(
            ["python", str(py_file)],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode != 0 and result.stderr:
            return {"found": True, "log": result.stderr, "run_url": f"file://{py_file}"}
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


class DetectorAdapter(SimpleAdapter):

    async def on_message(
        self,
        msg: PlatformMessage,
        tools: AgentToolsProtocol,
        history,
        participants_msg,
        contacts_msg,
        *,
        is_session_bootstrap: bool,
        room_id: str,
) -> None:

        print("=" * 50)
        print("ON_MESSAGE CALLED")
        print("CONTENT:", getattr(msg, "content", None))
        print("=" * 50)

        text = str(msg.content or "")

        tokens = text.strip().split()

        if "detect" not in tokens:
            print("No detect command found")
            return

        idx = tokens.index("detect")
        parts = tokens[idx:]

        print("PARTS:", parts)

        if len(parts) < 4:
            await tools.send_message(
               "Usage: detect <owner/repo> <commit_sha> <branch>",
                 mentions=["pekanksh"]
        )
            return

        _, repo_name, commit_sha, branch = parts[0], parts[1], parts[2], parts[3]

        print("REPO:", repo_name)
        print("SHA:", commit_sha)
        print("BRANCH:", branch)

        await tools.send_message(
            f"Starting detection on {repo_name}...",
            mentions=["pekanksh"]
    )
        ctx = {
            "repo_name": repo_name,
            "repo_url": f"https://github.com/{repo_name}",
            "branch": branch,
            "commit_sha": commit_sha,
            "current_agent": "DetectorAgent",
            "pipeline_complete": False,
            "error_type": "",
            "error_message": "",
            "bug_file": "",
            "bug_line": 0,
            "raw_code": "",
            "surrounding_code": "",
            "root_cause": "",
            "severity": "",
            "affected_files": [],
            "suggested_fix": "",
            "fix_explanation": "",
            "tests_passed": False,
            "test_output": "",
            "bug_confirmed": False,
            "fix_report": "",
            "fix_location": "",
            "fix_steps": [],
            "error_in_pipeline": None,
        }

        clone_path = f"/tmp/{repo_name.replace('/', '_')}"
        log_text = ""
        run_url = ""

        print("STEP 1")
        failed_run = get_failed_run(repo_name)
        print("FAILED RUN:", failed_run)
        print("STEP 2")

        if failed_run["found"]:
            print("FOUND FAILED ACTION")
            log_text = get_log_text(repo_name, failed_run["run_id"])
            run_url = failed_run["run_url"]
            clone_path = clone_repo(repo_name, commit_sha)
            print("AFTER CLONE")
            await tools.send_message(
                "Got log from GitHub Actions",
                mentions=["pekanksh"]
           )
        else:
            print("NO FAILED ACTION")
            await tools.send_message(
                "No failed Actions run — trying local scan...",
                mentions=["pekanksh"]
           )
            clone_path = clone_repo(repo_name, commit_sha)
            print("AFTER CLONE")
            fallback = fallback_local_scan(clone_path)
            if not fallback["found"]:
                await tools.send_message(
                    "No errors found anywhere — pipeline complete",
                    mentions=["pekanksh"]
           )
                ctx["pipeline_complete"] = True
                return
            log_text = fallback["log"]
            run_url = fallback["run_url"]

        bug = extract_bug_from_log(log_text, clone_path)
        ctx.update(bug)
        ctx["repo_url"] = run_url

        full_path = os.path.join(clone_path, ctx["bug_file"])
        ctx["surrounding_code"] = get_surrounding_code(full_path, ctx["bug_line"])

        try:
            with open(full_path, "r") as f:
                ctx["raw_code"] = f.read()
        except:
            ctx["raw_code"] = ""

        await tools.send_message(
            f"Bug detected: [{ctx['error_type']}] in {ctx['bug_file']}:{ctx['bug_line']}",
              mentions=["pekanksh"]
        )

        # Internal handoff
        await tools.send_message(
            f"analyse {json.dumps(ctx)}",
             mentions=["pekanksh/autodebug-analyser"]
)
        
adapter = DetectorAdapter()
agent = Agent.create(adapter=adapter, agent_id=agent_id, api_key=api_key)
import asyncio

async def main():
    async with agent:
        await agent.run_forever()

asyncio.run(main())
