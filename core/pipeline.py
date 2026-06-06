# AutoDebug — Multi-Agent Bug Fixing System
# Copyright 2026 Ekaanksh (github.com/Ekaanksh-dev)
# Licensed under Apache License 2.0

import os
import threading
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel

from agents import detector, analyser, fixer, tester, resolver
from core.context import BugContext

load_dotenv()
console = Console()


def print_banner():
    console.print(Panel.fit(
        "[bold green]AutoDebug[/bold green] — Multi-Agent Bug Fixing System\n"
        "[dim]5 agents · Band communication · DevOps Notifier[/dim]",
        border_style="green"
    ))


def run_pipeline(repo_name: str, commit_sha: str, branch: str) -> BugContext:
    """
    Run all 5 agents in sequence.
    Each agent runs in its own thread — communicates via Band.
    """
    print_banner()
    console.print(f"\n[bold]🚀 Pipeline started for:[/bold] {repo_name}")
    console.print(f"[dim]Branch: {branch} | Commit: {commit_sha[:7]}[/dim]\n")

    # ── Run agents in threads ─────────────────────────

    ctx_holder = {"ctx": BugContext()}

    def run_detector():
        ctx_holder["detector"] = detector.run(repo_name, commit_sha, branch)

    def run_analyser():
        ctx_holder["analyser"] = analyser.run()

    def run_fixer():
        ctx_holder["fixer"] = fixer.run()

    def run_tester():
        ctx_holder["tester"] = tester.run()

    def run_resolver():
        ctx_holder["ctx"] = resolver.run()

    # Start all agent threads
    threads = [
        threading.Thread(target=run_detector, name="Detector"),
        threading.Thread(target=run_analyser, name="Analyser"),
        threading.Thread(target=run_fixer,    name="Fixer"),
        threading.Thread(target=run_tester,   name="Tester"),
        threading.Thread(target=run_resolver, name="Resolver"),
    ]

    for t in threads:
        t.daemon = True
        t.start()

    # Wait for all to complete
    for t in threads:
        t.join(timeout=300)

    final_ctx = ctx_holder["ctx"]

    # ── Pipeline Summary ──────────────────────────────

    console.print("\n")
    if final_ctx.bug_confirmed:
        console.print(Panel.fit(
            f"[bold red]🐛 Bug Found![/bold red]\n"
            f"File: {final_ctx.bug_file}:{final_ctx.bug_line}\n"
            f"Type: {final_ctx.error_type}\n"
            f"Severity: {final_ctx.severity.upper()}\n"
            f"Fix Steps: {len(final_ctx.fix_steps)}",
            border_style="red",
            title="AutoDebug Report"
        ))
    else:
        console.print(Panel.fit(
            "[bold green]✅ No bugs found![/bold green]\n"
            "All tests passed. Repo looks healthy.",
            border_style="green",
            title="AutoDebug Report"
        ))

    return final_ctx
