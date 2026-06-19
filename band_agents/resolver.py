# AutoDebug — Multi-Agent Bug Fixing System
# Copyright 2026 Ekaanksh (github.com/Ekaanksh-dev)
# Licensed under Apache License 2.0

import os
import json
import sys
from pathlib import Path
from openai import OpenAI
from dotenv import load_dotenv
from band import Agent
from band.config import load_agent_config
from band.core.simple_adapter import SimpleAdapter
from band.core.types import PlatformMessage
from band.core.protocols import AgentToolsProtocol

# Reuse existing notifier logic from the local pipeline
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core.context import BugContext
from notifier.emailer import send_email
from integrations.devops_notifier import trigger_devops_notifier, should_notify

load_dotenv()

CONFIG_PATH = Path(__file__).resolve().parent.parent / "agent_config.yaml"
agent_id, api_key = load_agent_config("resolver", config_path=CONFIG_PATH)

client = OpenAI(
    api_key=os.getenv("ANTHROPIC_API_KEY"),
    base_url=os.getenv("ANTHROPIC_BASE_URL")
)


def generate_fix_report(ctx: dict) -> str:
    prompt = f"""
You are a senior software engineer writing a bug report for a developer.

Repo: {ctx['repo_name']}
Branch: {ctx['branch']}
Commit: {ctx['commit_sha']}

Bug Details:
- File: {ctx['bug_file']}
- Line: {ctx['bug_line']}
- Error Type: {ctx['error_type']}
- Error Message: {ctx['error_message']}
- Severity: {ctx['severity']}

Root Cause:
{ctx['root_cause']}

Suggested Fix:
{ctx['suggested_fix']}

Fix Explanation:
{ctx['fix_explanation']}

Test Results:
- Tests Passed: {ctx['tests_passed']}
- Bug Confirmed: {ctx['bug_confirmed']}

Write the report in this exact format:

SUMMARY: <one line summary of the bug>

WHERE TO FIX:
- File: <exact file path>
- Line: <line number>

WHAT IS WRONG:
<2-3 sentences explaining the bug clearly>

HOW TO FIX IT:
Step 1: <first thing to do>
Step 2: <second thing to do>
Step 3: <verify the fix>

SEVERITY: <low/medium/high/critical>
"""
    response = client.chat.completions.create(
        model=os.getenv("ANTHROPIC_MODEL"),
        messages=[
            {"role": "system", "content": "You are a senior engineer writing clear bug reports."},
            {"role": "user", "content": prompt}
        ],
        max_tokens=1000
    )
    msg = response.choices[0].message
    return msg.content or msg.reasoning_content


def parse_fix_steps(report: str) -> list:
    steps = []
    in_steps = False
    for line in report.split("\n"):
        if "HOW TO FIX IT:" in line:
            in_steps = True
            continue
        if in_steps:
            if line.startswith("Step"):
                steps.append(line.strip())
            elif line.startswith("SEVERITY:"):
                break
    return steps


class ResolverAdapter(SimpleAdapter):

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
        print("RESOLVER RECEIVED")
        print("CONTENT:", msg.content)
        print("=" * 50)

        text = str(msg.content or "")

        if "resolve" not in text.split():
            print("NO RESOLVE COMMAND FOUND")
            return

        idx = text.split().index("resolve")
        raw = " ".join(text.split()[idx + 1:])

        try:
            ctx = json.loads(raw)
            print("JSON PARSED OK")
        except json.JSONDecodeError as e:
            print("JSON ERROR:", e)
            await tools.send_message(
                "ResolverAgent: invalid JSON context received",
                mentions=["pekanksh"]
            )
            return

        ctx["current_agent"] = "ResolverAgent"

        if not ctx.get("bug_confirmed"):
            await tools.send_message(
                "No bug confirmed — pipeline complete, no report needed",
                mentions=["pekanksh"]
            )
            return

        await tools.send_message(
            "Generating fix report...",
            mentions=["pekanksh"]
        )

        report = generate_fix_report(ctx)
        ctx["fix_report"] = report
        ctx["fix_location"] = f"{ctx['bug_file']}:{ctx['bug_line']}"
        ctx["fix_steps"] = parse_fix_steps(report)
        ctx["pipeline_complete"] = True

        await tools.send_message(
            f"Fix report ready! Location: {ctx['fix_location']}",
            mentions=["pekanksh"]
        )

        # Build BugContext and trigger email + DevOps Notifier
        bug_ctx = BugContext.from_dict(ctx)

        if should_notify(bug_ctx):
            send_email(bug_ctx)
            trigger_devops_notifier(bug_ctx)
            await tools.send_message(
                "Email report sent and DevOps Notifier triggered!",
                mentions=["pekanksh"]
            )


adapter = ResolverAdapter()
agent = Agent.create(adapter=adapter, agent_id=agent_id, api_key=api_key)

import asyncio

async def main():
    async with agent:
        await agent.run_forever()
print("RESOLVER STARTING...")
asyncio.run(main())
