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
agent_id, api_key = load_agent_config("fixer", config_path=CONFIG_PATH)

client = OpenAI(
    api_key=os.getenv("ANTHROPIC_API_KEY"),
    base_url=os.getenv("ANTHROPIC_BASE_URL")
)


def generate_fix(ctx: dict) -> str:
    prompt = f"""
You are an expert software engineer.
Generate a precise fix for this bug.

Bug Details:
- Repo: {ctx['repo_name']}
- File: {ctx['bug_file']}
- Line: {ctx['bug_line']}
- Error Type: {ctx['error_type']}
- Error Message: {ctx['error_message']}
- Root Cause: {ctx['root_cause']}
- Severity: {ctx['severity']}

Surrounding Code:
{ctx['surrounding_code']}

Full File Content:
{ctx.get('raw_code', '')[:2000]}

Respond in this exact format:
FIXED_CODE: <only the corrected lines, not the whole file>
EXPLANATION: <what you changed and why>
"""
    response = client.chat.completions.create(
        model=os.getenv("ANTHROPIC_MODEL"),
        messages=[
            {"role": "system", "content": "You are an expert software engineer. Generate clean, minimal fixes."},
            {"role": "user", "content": prompt}
        ],
        max_tokens=800
    )
    msg = response.choices[0].message
    return msg.content or msg.reasoning_content


def parse_fix(fix: str) -> dict:
    result = {"suggested_fix": "", "fix_explanation": ""}
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


class FixerAdapter(SimpleAdapter):

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
        print("FIXER RECEIVED")
        print("CONTENT:", msg.content)
        print("=" * 50)


        text = str(msg.content or "")

        print("TOKENS:", text.split())

        if "fix" not in text.split():
            print("NO FIX COMMAND FOUND")
            return

        idx = text.split().index("fix")
        raw = " ".join(text.split()[idx + 1:])

        try:
            ctx = json.loads(raw)
            print("JSON PARSED OK")
        except json.JSONDecodeError as e:
            print("JSON ERROR:",e)
            await tools.send_message(
                "FixerAgent: invalid JSON context received",
                 mentions=["pekanksh"]
)
            return

        await tools.send_message(
            "Generating fix with AI...",
             mentions=["pekanksh"]
)

        ctx["current_agent"] = "FixerAgent"

        fix_raw = generate_fix(ctx)
        fix = parse_fix(fix_raw)

        ctx["suggested_fix"] = fix["suggested_fix"]
        ctx["fix_explanation"] = fix["fix_explanation"]

        await tools.send_message(
            "Fix generated!",
             mentions=["pekanksh"]
)
        await tools.send_message(
            f"Explanation: {ctx['fix_explanation'][:100]}...",
             mentions=["pekanksh"]
)

        print("SENDING TO TESTER")
        print("CTX SIZE:", len(json.dumps(ctx)))
        await tools.send_message( 
            f"test {json.dumps(ctx)}",
             mentions=["pekanksh/autodebug-tester"]
            
        
)


adapter = FixerAdapter()
agent = Agent.create(adapter=adapter, agent_id=agent_id, api_key=api_key)
import asyncio

async def main():
    async with agent:
        await agent.run_forever()
print("FIXER STARTING...")
asyncio.run(main())
