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
agent_id, api_key = load_agent_config("analyser", config_path=CONFIG_PATH)

client = OpenAI(
    api_key=os.getenv("ANTHROPIC_API_KEY"),
    base_url=os.getenv("ANTHROPIC_BASE_URL")
)


def analyse_bug(ctx: dict) -> str:
    prompt = f"""
You are an expert software debugger.
Analyse this bug and provide:
1. Root cause (1-2 sentences)
2. Severity: low / medium / high / critical
3. All affected files (list)
4. Why this bug occurred

Bug Details:
- Repo: {ctx['repo_name']}
- File: {ctx['bug_file']}
- Line: {ctx['bug_line']}
- Error Type: {ctx['error_type']}
- Error Message: {ctx['error_message']}

Surrounding Code:
{ctx['surrounding_code']}

Respond in this exact format:
ROOT_CAUSE: <your analysis>
SEVERITY: <low/medium/high/critical>
AFFECTED_FILES: <file1.py, file2.py>
REASON: <why this happened>
"""
    response = client.chat.completions.create(
        model=os.getenv("ANTHROPIC_MODEL"),
        messages=[
            {"role": "system", "content": "You are an expert bug analyser. Be concise and precise."},
            {"role": "user", "content": prompt}
        ],
        max_tokens=500
    )
    msg = response.choices[0].message
    return msg.content or msg.reasoning_content


def parse_analysis(analysis: str) -> dict:
    result = {"root_cause": "", "severity": "medium", "affected_files": [], "reason": ""}
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


class AnalyserAdapter(SimpleAdapter):

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
        text =str(msg.content or "")
        print("=" * 50)
        print("ANALYSER RECEIVED")
        print("CONTENT:", text)
        print("=" * 50)
      

        tokens = text.split()

        if "analyse" not in tokens:
            print("No analyse command found")
            return

        idx = tokens.index("analyse")
        raw = " ".join(tokens[idx + 1:])
        print("JSON LENGTH:", len(raw))
        try:
            ctx = json.loads(raw)
            print("JSON PARSED OK")
        except json.JSONDecodeError as e :
            print("JSON ERROR:",e)
            await tools.send_message(
                "AnalyserAgent: invalid JSON context received",
                mentions=["pekanksh"]
         )
            return

        await tools.send_message(
            "Analysing bug with AI...",
            mentions=["pekanksh"]
         )
      

        ctx["current_agent"] = "AnalyserAgent"

        analysis = analyse_bug(ctx)
        parsed = parse_analysis(analysis)

        ctx["root_cause"] = parsed["root_cause"]
        ctx["severity"] = parsed["severity"]
        ctx["affected_files"] = parsed["affected_files"]

        await tools.send_message(
            f"Analysis done — Severity: {ctx['severity']}",
             mentions=["pekanksh"]
)
        await tools.send_message(
            f"Root cause: {ctx['root_cause']}",
             mentions=["pekanksh"] 
)

        # Hand off to FixerAgent
        await tools.send_message(
            f"fix {json.dumps(ctx)}",
             mentions=["pekanksh/autodebug-fixer"]
                                               
)


adapter = AnalyserAdapter()
agent = Agent.create(adapter=adapter, agent_id=agent_id, api_key=api_key)
import asyncio

async def main():
    async with agent:
        await agent.run_forever()
print("ANALYSER STARTING...")
asyncio.run(main())
