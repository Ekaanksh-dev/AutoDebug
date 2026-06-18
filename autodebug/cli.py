import argparse
import subprocess
import sys
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

AGENTS = [
    "detector.py",
    "analyser.py",
    "fixer.py",
    "tester.py",
    "resolver.py",
]

AGENT_DIR = ROOT / "band_agents"


def start_agents():
    print("Starting AutoDebug agents...\n")

    for agent in AGENTS:
        path = AGENT_DIR / agent

        subprocess.Popen(
            [sys.executable, str(path)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        print(f"✓ {agent}")

    print("\nAutoDebug started.")


def stop_agents():
    print("Stopping AutoDebug agents...\n")

    for agent in AGENTS:
        subprocess.run(
            ["pkill", "-f", agent],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        print(f"✓ {agent}")

    print("\nAutoDebug stopped.")


def status_agents():
    print("Agent Status\n")

    for agent in AGENTS:
        result = subprocess.run(
            ["pgrep", "-f", agent],
            capture_output=True,
            text=True,
        )

        running = result.returncode == 0

        if running:
            print(f"✓ {agent:<15} RUNNING")
        else:
            print(f"✗ {agent:<15} STOPPED")


def show_logs():
    log_dir = ROOT / "logs"

    if not log_dir.exists():
        print("No logs directory found.")
        return

    files = sorted(log_dir.glob("*.log"))

    if not files:
        print("No log files found.")
        return

    latest = files[-1]

    print(f"Showing: {latest.name}")
    print("-" * 60)

    try:
        print(latest.read_text()[-5000:])
    except Exception as e:
        print(e)


def doctor():
    print("Running diagnostics...\n")

    checks = [
        (".env", ROOT / ".env"),
        ("agent_config.yaml", ROOT / "agent_config.yaml"),
        ("band_agents", ROOT / "band_agents"),
        ("logs", ROOT / "logs"),
    ]

    for name, path in checks:
        if path.exists():
            print(f"✓ {name}")
        else:
            print(f"✗ {name}")

    print()

    for agent in AGENTS:
        file = AGENT_DIR / agent

        try:
            subprocess.run(
                [sys.executable, "-m", "py_compile", str(file)],
                check=True,
                capture_output=True,
            )
            print(f"✓ {agent}")
        except subprocess.CalledProcessError:
            print(f"✗ {agent}")

    print("\nDoctor finished.")


def detect(repo, commit, branch):
    print("Detection request")
    print(f"Repo   : {repo}")
    print(f"Commit : {commit}")
    print(f"Branch : {branch}")

    print(
        "\nUse this command in Band:\n"
        f"@AutoDebug-Detector detect {repo} {commit} {branch}"
    )


def main():
    parser = argparse.ArgumentParser(
        prog="autodebug",
        description="AutoDebug CLI"
    )

    sub = parser.add_subparsers(dest="command")

    sub.add_parser("start")
    sub.add_parser("stop")
    sub.add_parser("status")
    sub.add_parser("logs")
    sub.add_parser("doctor")

    detect_parser = sub.add_parser("detect")
    detect_parser.add_argument("repo")
    detect_parser.add_argument("commit")
    detect_parser.add_argument("branch")

    args = parser.parse_args()

    if args.command == "start":
        start_agents()

    elif args.command == "stop":
        stop_agents()

    elif args.command == "status":
        status_agents()

    elif args.command == "logs":
        show_logs()

    elif args.command == "doctor":
        doctor()

    elif args.command == "detect":
        detect(
            args.repo,
            args.commit,
            args.branch
        )

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
