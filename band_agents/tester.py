# AutoDebug — Multi-Agent Bug Fixing System
# Copyright 2026 Ekaanksh (github.com/Ekaanksh-dev)
# Licensed under Apache License 2.0

import os
import json
import subprocess
from pathlib import Path
from dotenv import load_dotenv
from band import Agent
from band.config import load_agent_config
from band.core.simple_adapter import SimpleAdapter
from band.core.types import PlatformMessage
from band.core.protocols import AgentToolsProtocol

load_dotenv()

CONFIG_PATH = Path(__file__).resolve().parent.parent / "agent_config.yaml"
agent_id, api_key = load_agent_config("tester", config_path=CONFIG_PATH)

def run_pytest(repo_path: str) -> dict:
    try:
        result = subprocess.run(
            ["python", "-m", "pytest", repo_path, "--tb=short", "-q", "--no-header"],
            capture_output=True,
            text=True,
            timeout=int(os.getenv("TIMEOUT_SECONDS", 30))
        )
        passed = result.returncode == 0
        output = result.stdout + result.stderr
        return {"passed": passed, "output": output[:2000], "returncode": result.returncode}
    except subprocess.TimeoutExpired:
        return {"passed": False, "output": "Tests timed out", "returncode": -1}
    except Exception as e:
        return {"passed": False, "output": f"pytest error: {str(e)}", "returncode": -1}


def confirm_bug_exists(test_output: str, error_type: str, clone_path: str, bug_file: str) -> bool:
    indicators = ["FAILED", "ERROR", "error", error_type, "AssertionError", "Exception"]
    for indicator in indicators:
        if indicator in test_output:
            return True
    full_path = os.path.join(clone_path, bug_file.lstrip("/"))
    if os.path.exists(full_path):
        result = subprocess.run(
            ["python", full_path],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode != 0 and error_type in result.stderr:
            return True
    return False


class TesterAdapter(SimpleAdapter):

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
        print("TESTER RECEIVED")
        print("CONTENT:", msg.content)
        print("=" * 50)

        text = str(msg.content or "")

        print("TOKENS:", text.split())

        if "test" not in text.split():
            print("NO TEST COMMAND FOUND")
            return

        idx = text.split().index("test")
        raw = " ".join(text.split()[idx + 1:])

        try:
            ctx = json.loads(raw)
            print("JSON PARSED OK")
        except json.JSONDecodeError as e :
            print("JSON ERROR:",e)
            await tools.send_message(
                "TesterAgent: invalid JSON context received",
                 mentions=["pekanksh"]
)
            return

        await tools.send_message(
            "Running pytest...",
             mentions=["pekanksh"]
)

        ctx["current_agent"] = "TesterAgent"

        repo_path = f"/tmp/{ctx['repo_name'].replace('/', '_')}"
        test_result = run_pytest(repo_path)

        ctx["tests_passed"] = test_result["passed"]
        ctx["test_output"] = test_result["output"]
        ctx["bug_confirmed"] = confirm_bug_exists(
            test_result["output"],
            ctx["error_type"],
            repo_path,
            ctx["bug_file"]
        )

        if ctx["bug_confirmed"]:
            await tools.send_message(
                "Bug confirmed by tests!",
                 mentions=["pekanksh"]
)
            await tools.send_message(
                f"Output:\n{ctx['test_output'][:300]}",
                  mentions=["pekanksh"]
)
        else:
            await tools.send_message(
                "No bug confirmed in tests",
                 mentions=["pekanksh"]
)

        print("SENDING TO RESOLVER")
        print("MENTION:", "pekanksh/autodebug-resolver")
        print("JSON SIZE:", len(json.dumps(ctx)))
        await tools.send_message(
            f"resolve {json.dumps(ctx)}",
             mentions=["pekanksh/autodebug-resolver"]
)


adapter = TesterAdapter()
agent = Agent.create(adapter=adapter, agent_id=agent_id, api_key=api_key)
import asyncio

async def main():
    async with agent:
        await agent.run_forever()
print("TESTER STARTING...")
asyncio.run(main())
