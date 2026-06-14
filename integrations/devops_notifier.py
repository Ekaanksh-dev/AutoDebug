# AutoDebug — Multi-Agent Bug Fixing System
# Copyright 2026 Ekaanksh (github.com/Ekaanksh-dev)
# Licensed under Apache License 2.0

import os
import requests
from dotenv import load_dotenv
from rich.console import Console
from core.context import BugContext

load_dotenv()
console = Console()


def trigger_devops_notifier(ctx: BugContext) -> bool:
    """
    Trigger DevOps AI Notifier repo via GitHub repo_dispatch.
    Notifier will use Groq API to summarise and send email.
    """

    token = os.getenv("GITHUB_TOKEN")
    username = os.getenv("GITHUB_USERNAME")
    notifier_repo = os.getenv("DEVOPS_NOTIFIER_REPO")

    if not all([token, username, notifier_repo]):
        console.print("[red]❌ Missing GitHub config in .env[/red]")
        return False

    payload = {
        "event_type": "bug_found",
        "client_payload": {
        "repo_name":    ctx.repo_name,
        "bug_file":     ctx.bug_file,
        "bug_line":     str(ctx.bug_line),
        "error_type":   ctx.error_type,
        "severity":     ctx.severity,
        "root_cause":   ctx.root_cause,
        "fix_location": ctx.fix_location,
        "fix_report":   ctx.fix_report[:500],
        "triggered_at": ctx.triggered_at,
        "repo_url":     ctx.repo_url,
        }
    }

    try:
        response = requests.post(
            f"https://api.github.com/repos/{username}/{notifier_repo}/dispatches",
            json=payload,
            headers={
                "Authorization": f"token {token}",
                "Accept": "application/vnd.github.v3+json"
            }
        )

        if response.status_code == 204:
            console.print(f"[green]✅ DevOps Notifier triggered![/green]")
            console.print(f"[dim]📧 Email will arrive shortly...[/dim]")
            return True
        else:
            console.print(f"[red]❌ Trigger failed: {response.status_code}[/red]")
            console.print(f"[dim]{response.text}[/dim]")
            return False

    except Exception as e:
        console.print(f"[red]❌ Error triggering notifier: {e}[/red]")
        return False


def should_notify(ctx: BugContext) -> bool:
    """Only notify if bug was actually confirmed"""
    return ctx.bug_confirmed and ctx.pipeline_complete
