# AutoDebug — Multi-Agent Bug Fixing System
# Copyright 2026 Ekaanksh (github.com/Ekaanksh-dev)
# Licensed under Apache License 2.0

import os
import json
import base64
import requests
from dotenv import load_dotenv
from rich.console import Console

load_dotenv()
console = Console()

WATCHED_FILE = "watched_repos.json"
TRIGGER_WORKFLOW = """name: Trigger AutoDebug
on: [push]

jobs:
  notify:
    runs-on: ubuntu-latest
    steps:
      - name: Trigger AutoDebug pipeline
        run: |
          curl -X POST \\
          -H "Authorization: token ${{ secrets.GITHUB_TOKEN }}" \\
          -H "Accept: application/vnd.github.v3+json" \\
          https://api.github.com/repos/Ekaanksh-dev/AutoDebug/dispatches \\
          -d '{
            "event_type": "analyze",
            "client_payload": {
              "repo": "${{ github.repository }}",
              "branch": "${{ github.ref_name }}",
              "commit": "${{ github.sha }}"
            }
          }'
"""


def get_headers() -> dict:
    return {
        "Authorization": f"token {os.getenv('GITHUB_TOKEN')}",
        "Accept": "application/vnd.github.v3+json"
    }


def get_all_repos() -> list:
    """Fetch all repos from GitHub account"""
    console.print("[yellow]📡 Fetching all repos from GitHub...[/yellow]")
    response = requests.get(
        "https://api.github.com/user/repos?per_page=100",
        headers=get_headers()
    )

    if response.status_code != 200:
        console.print(f"[red]❌ Failed to fetch repos: {response.status_code}[/red]")
        return []

    repos = [repo["full_name"] for repo in response.json()]
    console.print(f"[green]✅ Found {len(repos)} repos[/green]")
    return repos


def get_watched_repos() -> list:
    """Read currently watched repos from file"""
    try:
        with open(WATCHED_FILE, "r") as f:
            return json.load(f)
    except:
        return []


def save_watched_repos(repos: list):
    """Save updated watched repos list"""
    with open(WATCHED_FILE, "w") as f:
        json.dump(repos, f, indent=2)


def workflow_exists(repo_name: str) -> bool:
    """Check if trigger workflow already exists in repo"""
    response = requests.get(
        f"https://api.github.com/repos/{repo_name}/contents/.github/workflows/trigger.yml",
        headers=get_headers()
    )
    return response.status_code == 200


def inject_trigger_workflow(repo_name: str) -> bool:
    """Auto inject trigger.yml into new repo"""

    # Skip AutoDebug repo itself
    username = os.getenv("GITHUB_USERNAME")
    if repo_name == f"{username}/AutoDebug":
        console.print(f"[dim]⏭️  Skipping AutoDebug repo itself[/dim]")
        return False

    # Skip if already exists
    if workflow_exists(repo_name):
        console.print(f"[dim]⏭️  {repo_name} already has trigger[/dim]")
        return False

    try:
        content_encoded = base64.b64encode(
            TRIGGER_WORKFLOW.encode()
        ).decode()

        response = requests.put(
            f"https://api.github.com/repos/{repo_name}/contents/.github/workflows/trigger.yml",
            headers=get_headers(),
            json={
                "message": "🤖 AutoDebug: Auto-injected trigger workflow",
                "content": content_encoded
            }
        )

        if response.status_code in [200, 201]:
            console.print(f"[green]✅ Injected trigger into {repo_name}[/green]")
            return True
        else:
            console.print(f"[red]❌ Failed to inject into {repo_name}: {response.status_code}[/red]")
            return False

    except Exception as e:
        console.print(f"[red]❌ Error injecting into {repo_name}: {e}[/red]")
        return False


def discover_new_repos():
    """Main function — find new repos and inject trigger"""
    all_repos  = get_all_repos()
    watched    = get_watched_repos()

    # Find repos not yet watched
    new_repos = [r for r in all_repos if r not in watched]

    if not new_repos:
        console.print("[green]✅ No new repos found — all up to date![/green]")
        save_watched_repos(all_repos)
        return

    console.print(f"\n[yellow]🆕 Found {len(new_repos)} new repo(s):[/yellow]")

    injected = 0
    for repo in new_repos:
        console.print(f"  → {repo}")
        if inject_trigger_workflow(repo):
            injected += 1

    # Update watched list
    save_watched_repos(all_repos)

    console.print(f"\n[green]✅ Done! Injected trigger into {injected} new repo(s)[/green]")
    console.print(f"[dim]Now watching {len(all_repos)} repos total[/dim]")
