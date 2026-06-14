# AutoDebug — Multi-Agent Bug Fixing System
# Copyright 2026 Ekaanksh (github.com/Ekaanksh-dev)
# Licensed under Apache License 2.0

import os
from openai import OpenAI
from dotenv import load_dotenv
from core.context import BugContext
from band.client import BandClient

load_dotenv()

band = BandClient("FixerAgent")

client = OpenAI(
    api_key=os.getenv("ANTHROPIC_API_KEY"),
    base_url=os.getenv("ANTHROPIC_BASE_URL")
)


def generate_fix(ctx: BugContext) -> dict:
    """Use AI to generate a code fix"""
    band.log("🔧 Generating fix with AI...")

    prompt = f"""
You are an expert software engineer.

Generate a precise fix for this bug.

Bug Details:
- Repo: {ctx.repo_name}
- File: {ctx.bug_file}
- Line: {ctx.bug_line}
- Error Type: {ctx.error_type}
- Error Message: {ctx.error_message}
- Root Cause: {ctx.root_cause}
- Severity: {ctx.severity}

Surrounding Code:
{ctx.surrounding_code}

Full File Content:
{ctx.raw_code[:2000]}

Respond in this exact format:
FIXED_CODE: <only the corrected lines, not the whole file>
EXPLANATION: <what you changed and why>
"""

    response = client.chat.completions.create(
        model=os.getenv("ANTHROPIC_MODEL"),
        messages=[
            {
                "role": "system",
                "content": "You are an expert software engineer. Generate clean, minimal fixes."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        max_tokens=800
    )

    msg = response.choices[0].message
    return msg.content or msg.reasoning_content


def parse_fix(fix: str) -> dict:
    """Parse AI fix response"""
    result = {
        "suggested_fix": "",
        "fix_explanation": ""
    }

    lines = fix.split("\n")
    current_key = None
    buffer = []

    for line in lines:
        if line.startswith("FIXED_CODE:"):
            if current_key and buffer:
                result[current_key] = "\n".join(buffer).strip()
            current_key = "suggested_fix"
            buffer = [line.replace("FIXED_CODE:", "").strip()]
        elif line.startswith("EXPLANATION:"):
            if current_key and buffer:
                result[current_key] = "\n".join(buffer).strip()
            current_key = "fix_explanation"
            buffer = [line.replace("EXPLANATION:", "").strip()]
        else:
            if current_key:
                buffer.append(line)

    if current_key and buffer:
        result[current_key] = "\n".join(buffer).strip()

    return result


def run() -> BugContext:
    """Main fixer function"""
    band.log("⏳ Waiting for Analyser...")

    # Receive context from Analyser via Band
    data = band.receive(timeout=120)

    if not data:
        band.log("❌ No data received from Analyser")
        return BugContext()

    ctx = BugContext.from_dict(data)
    ctx.current_agent = "FixerAgent"

    band.log(f"📥 Received: {ctx.summary()}")

    # Generate fix
    fix_raw = generate_fix(ctx)
    fix = parse_fix(fix_raw)

    # Update context
    ctx.suggested_fix = fix["suggested_fix"]
    ctx.fix_explanation = fix["fix_explanation"]

    band.log("✅ Fix generated!")
    band.log(f"📝 Explanation: {ctx.fix_explanation[:100]}...")

    # Send to Tester via Band
    band.send("TesterAgent", ctx.to_dict())

    return ctx
