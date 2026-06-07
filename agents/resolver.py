# AutoDebug — Multi-Agent Bug Fixing System
# Copyright 2026 Ekaanksh (github.com/Ekaanksh-dev)
# Licensed under Apache License 2.0

import os
from openai import OpenAI
from dotenv import load_dotenv
from core.context import BugContext
from band.client import BandClient

load_dotenv()

band = BandClient("ResolverAgent")

client = OpenAI(
    api_key=os.getenv("ANTHROPIC_API_KEY"),
    base_url=os.getenv("ANTHROPIC_BASE_URL")
)


def generate_fix_report(ctx: BugContext) -> str:
    """Use AI to write a clear human-readable fix report"""
    band.log("📝 Generating fix report...")

    prompt = f"""
You are a senior software engineer writing a bug report for a developer.

Write a clear, actionable fix report based on this information:

Repo: {ctx.repo_name}
Branch: {ctx.branch}
Commit: {ctx.commit_sha}
Triggered At: {ctx.triggered_at}

Bug Details:
- File: {ctx.bug_file}
- Line: {ctx.bug_line}
- Error Type: {ctx.error_type}
- Error Message: {ctx.error_message}
- Severity: {ctx.severity}

Root Cause:
{ctx.root_cause}

Suggested Fix:
{ctx.suggested_fix}

Fix Explanation:
{ctx.fix_explanation}

Test Results:
- Tests Passed: {ctx.tests_passed}
- Bug Confirmed: {ctx.bug_confirmed}
- Output: {ctx.test_output[:500]}

Write the report in this exact format:

SUMMARY: <one line summary of the bug>

WHERE TO FIX:
- File: <exact file path>
- Line: <line number>
- Function/Section: <function name if known>

WHAT IS WRONG:
<2-3 sentences explaining the bug clearly>

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
    """Extract step by step fix instructions"""
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


def run() -> BugContext:
    """Main resolver function"""
    band.log("⏳ Waiting for Tester...")

    # Receive context from Tester via Band
    data = band.receive(timeout=60)

    if not data:
        band.log("❌ No data received from Tester")
        return BugContext()

    ctx = BugContext.from_dict(data)
    ctx.current_agent = "ResolverAgent"

    band.log(f"📥 Received: {ctx.summary()}")

    # Only generate report if bug was confirmed
    if not ctx.bug_confirmed:
        band.log("✅ No bug confirmed — pipeline complete, no report needed")
        ctx.pipeline_complete = True
        return ctx

    # Generate human readable fix report
    report = generate_fix_report(ctx)

    # Update context
    ctx.fix_report = report
    ctx.fix_location = f"{ctx.bug_file}:{ctx.bug_line}"
    ctx.fix_steps = parse_fix_steps(report)
    ctx.pipeline_complete = True

    band.log("✅ Fix report ready!")
    band.log(f"📍 Fix location: {ctx.fix_location}")
    band.log(f"📋 Steps: {len(ctx.fix_steps)} steps to fix")

    return ctx
