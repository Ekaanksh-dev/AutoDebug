# AutoDebug — Multi-Agent Bug Fixing System
# Copyright 2026 Ekaanksh (github.com/Ekaanksh-dev)
# Licensed under Apache License 2.0

import os
import sys
import argparse
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel

from core.pipeline import run_pipeline
from core.repo_watcher import discover_new_repos
from notifier.emailer import send_email, send_test_email
from integrations.devops_notifier import trigger_devops_notifier, should_notify

load_dotenv()
console = Console()


def parse_args():
    parser = argparse.ArgumentParser(
        description="AutoDebug — Multi-Agent Bug Fixing System"
    )
    subparsers = parser.add_subparsers(dest="command")

    # ── analyse command ───────────────────────────────
    analyse = subparsers.add_parser(
        "analyse",
        help="Analyse a repo for bugs"
    )
    analyse.add_argument("--repo",   required=True, help="GitHub repo (owner/name)")
    analyse.add_argument("--commit", required=True, help="Commit SHA")
    analyse.add_argument("--branch", default="main", help="Branch name")

    # ── watch command ─────────────────────────────────
    subparsers.add_parser(
        "watch",
        help="Discover and watch new repos"
    )

    # ── test-email command ────────────────────────────
    subparsers.add_parser(
        "test-email",
        help="Send a test email to verify config"
    )

    return parser.parse_args()


def main():
    args = parse_args()

    if args.command == "analyse":
        console.print(Panel.fit(
            f"[bold green]AutoDebug[/bold green] starting...\n"
            f"[dim]Repo: {args.repo} | Branch: {args.branch}[/dim]",
            border_style="green"
        ))

        # Run all 5 agents
        ctx = run_pipeline(
            repo_name=args.repo,
            commit_sha=args.commit,
            branch=args.branch
        )

        # If bug found → notify
        if should_notify(ctx):
            console.print("\n[yellow]🔔 Bug confirmed — triggering notifications...[/yellow]")

            # Option 1: Direct email
            send_email(ctx)

            # Option 2: Trigger DevOps AI Notifier repo
            trigger_devops_notifier(ctx)

        else:
            console.print("\n[green]✅ No bugs found — no notification needed.[/green]")

        sys.exit(0)

    elif args.command == "watch":
        console.print("[yellow]🔍 Scanning for new repos...[/yellow]")
        discover_new_repos()

    elif args.command == "test-email":
        console.print("[yellow]📧 Sending test email...[/yellow]")
        send_test_email()

    else:
        console.print("[red]❌ No command given. Use --help for options.[/red]")
        console.print("\nExamples:")
        console.print("  python main.py analyse --repo Ekaanksh-dev/my-repo --commit abc1234")
        console.print("  python main.py watch")
        console.print("  python main.py test-email")
        sys.exit(1)


if __name__ == "__main__":
    main()
