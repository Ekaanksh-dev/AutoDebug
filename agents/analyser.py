# AutoDebug — Multi-Agent Bug Fixing System
# Copyright 2026 Ekaanksh (github.com/Ekaanksh-dev)
# Licensed under Apache License 2.0

import os
from openai import OpenAI
from dotenv import load_dotenv
from core.context import BugContext
from band.client import BandClient

load_dotenv()

band = BandClient("AnalyserAgent")

client = OpenAI(
    api_key=os.getenv("ANTHROPIC_API_KEY"),
    base_url=os.getenv("ANTHROPIC_BASE_URL")
)


def analyse_bug(ctx: BugContext) -> str:
    """Use AI to find root cause of bug"""
    band.log("🧠 Analysing bug with AI...")

    prompt = f"""
You are an expert software debugger.

Analyse this bug and provide:
1. Root cause (1-2 sentences)
2. Severity: low / medium / high / critical
3. All affected files (list)
4. Why this bug occurred

Bug Details:
- Repo: {ctx.repo_name}
- File: {ctx.bug_file}
- Line: {ctx.bug_line}
- Error Type: {ctx.error_type}
- Error Message: {ctx.error_message}

Surrounding Code:
{ctx.surrounding_code}

Respond in this exact format:
ROOT_CAUSE: <your analysis>
SEVERITY: <low/medium/high/critical>
AFFECTED_FILES: <file1.py, file2.py>
REASON: <why this happened>
"""

    response = client.chat.completions.create(
        model=os.getenv("ANTHROPIC_MODEL"),
        messages=[
            {
                "role": "system",
                "content": "You are an expert bug analyser. Be concise and precise."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        max_tokens=500
    )

    return response.choices[0].message.content


def parse_analysis(analysis: str) -> dict:
    """Parse AI response into structured data"""
    result = {
        "root_cause": "",
        "severity": "medium",
        "affected_files": [],
        "reason": ""
    }

    for line in analysis.split("\n"):
        if line.startswith("ROOT_CAUSE:"):
            result["root_cause"] = line.replace("ROOT_CAUSE:", "").strip()
        elif line.startswith("SEVERITY:"):
            result["severity"] = line.replace("SEVERITY:", "").strip().lower()
        elif line.startswith("AFFECTED_FILES:"):
            files = line.replace("AFFECTED_FILES:", "").strip()
            result["affected_files"] = [f.strip() for f in files.split(",")]
        elif line.startswith("REASON:"):
            result["reason"] = line.replace("REASON:", "").strip()

    return result


def run() -> BugContext:
    """Main analyser function"""
    band.log("⏳ Waiting for Detector...")

    # Receive context from Detector via Band
    data = band.receive(timeout=60)

    if not data:
        band.log("❌ No data received from Detector")
        return BugContext()

    ctx = BugContext.from_dict(data)
    ctx.current_agent = "AnalyserAgent"

    band.log(f"📥 Received: {ctx.summary()}")

    # Run AI analysis
    analysis = analyse_bug(ctx)
    parsed = parse_analysis(analysis)

    # Update context
    ctx.root_cause = parsed["root_cause"]
    ctx.severity = parsed["severity"]
    ctx.affected_files = parsed["affected_files"]

    band.log(f"✅ Analysis done — Severity: {ctx.severity}")
    band.log(f"📌 Root cause: {ctx.root_cause}")

    # Send to Fixer via Band
    band.send("FixerAgent", ctx.to_dict())

    return ctx
