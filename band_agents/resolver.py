# AutoDebug — Multi-Agent Bug Fixing System
# Copyright 2026 Ekaanksh (github.com/Ekaanksh-dev)
# Licensed under Apache License 2.0

import os
import json
from pathlib import Path
from openai import OpenAI
from dotenv import load_dotenv
from band import Agent
from band.config import load_agent_config
from band.core.simple_adapter import SimpleAdapter
from band.core.types import PlatformMessage
from band.core.protocols import AgentToolsProtocol

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

Write a clear, actionable fix report based on this information:

Repo: {ctx['repo_name']}
Branch: {ctx['branch']}
Commit: {ctx['commit_sha']}

Bug Details:
- File: {ctx['bug_file']}
- Line: {ctx['bug_line']}
- Error Type: {ctx['error_type']}
- Error Message: {ctx['error_message']}
- Severity: {ctx['severity']}

Root Cause: {ctx['root_cause']}

Suggested Fix:
{ctx['suggested_fix']}

Fix Explanation: {ctx['fix_explanation']}

Test Results:
- Tests Passed: {ctx['tests_passed']}
- Bug Confirmed: {ctx['bug_confirmed']}
- Output: {ctx['test_output'][:500]}

Write the report in this exact format:

SUMMARY: <one line summary of the bug>

WHERE TO FIX:
- File: <exact file path>
- Line: <line number>
- Function/Section: <function name if known>

WHAT IS WRONG: <2-3 sentences explaining the bug clearly>

HOW TO FIX IT:
Step 1: <first thing to do>
Step 2: <second thing to do>
Step 3: <verify the fix>

CODE TO CHANGE:
<exact code snippet that needs to change>

SEVERITY: <low/medium/high/critical>
ESTIMATED FIX TIME: <5 mins / 15 mins / 1 hour>
"""
    response = client.chat.completions.create(
        model=os.getenv("ANTHROPIC_MODEL"),
        messages=[
            {
                "role": "system",
                "content": "You are a senior engineer writing clear bug reports for developers. Be specific and actionable."
            },
            {
                "role": "user",
                "content": prompt
            }
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
            elif line.startswith("CODE TO CHANGE:"):
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

        print("TOKENS:", text.split())

        if "resolve" not in text.split():
            print("NO RESOLVE COMMAND FOUND")
            return

        idx = text.split().index("resolve")
        raw = " ".join(text.split()[idx + 1:])

        try:
            ctx = json.loads(raw)
            print("JSON PARSED OK")
        except json.JSONDecodeError as e :
            print("JSON ERROR:",e)
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
            ctx["pipeline_complete"] = True
            return

        await tools.send_message(
            "Generating fix report with AI...",
             mentions=["pekanksh"]
)

        report = generate_fix_report(ctx)
        steps = parse_fix_steps(report)

        ctx["fix_report"] = report
        ctx["fix_location"] = f"{ctx['bug_file']}:{ctx['bug_line']}"
        ctx["fix_steps"] = steps
        ctx["pipeline_complete"] = True

        await tools.send_message(
            "AutoDebug pipeline complete!",
             mentions=["pekanksh"]
)
        await tools.send_message(
            f"Fix location: {ctx['fix_location']}",
             mentions=["pekanksh"]

)
        await tools.send_message(
            f"{len(steps)} steps to fix",
             mentions=["pekanksh"]

)
        await tools.send_message(
            f"\nFull Report:\n{report}",
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
