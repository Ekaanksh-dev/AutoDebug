# AutoDebug — Multi-Agent Bug Fixing System
# Copyright 2026 Ekaanksh (github.com/Ekaanksh-dev)
# Licensed under Apache License 2.0

from core.context import BugContext


def format_email_subject(ctx: BugContext) -> str:
    """Format email subject line"""
    severity_emoji = {
        "low":      "🟡",
        "medium":   "🟠",
        "high":     "🔴",
        "critical": "🚨"
    }
    emoji = severity_emoji.get(ctx.severity, "🐛")
    return (
        f"{emoji} AutoDebug [{ctx.severity.upper()}] "
        f"Bug found in {ctx.repo_name} — {ctx.error_type}"
    )


def format_email_body(ctx: BugContext) -> str:
    """Format full email body"""

    steps_text = "\n".join(
        f"  {i+1}. {step}"
        for i, step in enumerate(ctx.fix_steps)
    ) if ctx.fix_steps else "  See fix report below."

    body = f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🤖 AutoDebug — Automated Bug Report
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📦 REPO DETAILS
───────────────
Repository  : {ctx.repo_name}
Branch      : {ctx.branch}
Commit      : {ctx.commit_sha[:7]}
Triggered   : {ctx.triggered_at}
Repo URL    : {ctx.repo_url}

🐛 BUG DETAILS
───────────────
Error Type  : {ctx.error_type}
Error Msg   : {ctx.error_message}
File        : {ctx.bug_file}
Line        : {ctx.bug_line}
Severity    : {ctx.severity.upper()}

🔍 ROOT CAUSE
───────────────
{ctx.root_cause}

📍 WHERE TO FIX
───────────────
Location    : {ctx.fix_location}

🛠️ HOW TO FIX
───────────────
{steps_text}

📋 FULL FIX REPORT
───────────────────
{ctx.fix_report}

🧪 TEST RESULTS
───────────────
Tests Passed  : {ctx.tests_passed}
Bug Confirmed : {ctx.bug_confirmed}
Test Output   :
{ctx.test_output[:500]}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Powered by AutoDebug · github.com/Ekaanksh-dev/AutoDebug
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
    return body


def format_slack_message(ctx: BugContext) -> str:
    """Format short Slack/Discord style message"""
    return (
        f"🐛 *AutoDebug Alert*\n"
        f"*Repo:* {ctx.repo_name}\n"
        f"*Bug:* {ctx.error_type} in `{ctx.bug_file}:{ctx.bug_line}`\n"
        f"*Severity:* {ctx.severity.upper()}\n"
        f"*Root Cause:* {ctx.root_cause}\n"
        f"*Fix Location:* `{ctx.fix_location}`"
    )
