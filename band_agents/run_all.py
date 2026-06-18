# AutoDebug — Multi-Agent Bug Fixing System
# Copyright 2026 Ekaanksh (github.com/Ekaanksh-dev)
# Licensed under Apache License 2.0

import subprocess
import sys
import os
import signal
import time

AGENTS = ["detector.py", "analyser.py", "fixer.py", "tester.py", "resolver.py"]

processes = []


def start_agents():
    print("🚀 AutoDebug — Starting all agents...\n")
    for agent_file in AGENTS:
        name = agent_file.replace(".py", "").capitalize()
        print(f"  ▶ Starting {name}Agent ({agent_file})")
        proc = subprocess.Popen(
            [sys.executable, agent_file],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )
        processes.append((name, proc))
        time.sleep(0.5)  # slight stagger so Band connections don't collide

    print(f"\n✅ All {len(AGENTS)} agents running!\n")
    print("━" * 50)
    print("📡 Trigger the pipeline from the Band dashboard:")
    print("   → Open DetectorAgent's chat room")
    print("   → Send: detect <owner/repo> <commit_sha> <branch>")
    print("   → e.g.: detect Ekaanksh-dev/myrepo abc1234 main")
    print("━" * 50)
    print("\n📜 Live logs:\n")


def stream_logs():
    """Stream logs from all agent processes to terminal."""
    import select
    fds = {proc.stdout.fileno(): name for name, proc in processes}

    while True:
        # Check if all processes are still alive
        alive = [proc for _, proc in processes if proc.poll() is None]
        if not alive:
            print("\n⚠️  All agent processes have exited.")
            break

        readable, _, _ = select.select(
            [proc.stdout for _, proc in processes if proc.poll() is None],
            [], [], 1.0
        )
        for f in readable:
            line = f.readline()
            if line:
                name = fds.get(f.fileno(), "unknown")
                print(f"[{name:>10}] {line}", end="")


def shutdown(sig=None, frame=None):
    print("\n\n🛑 Shutting down all agents...")
    for name, proc in processes:
        if proc.poll() is None:
            proc.terminate()
            print(f"  ✖ Stopped {name}Agent")
    sys.exit(0)


if __name__ == "__main__":
    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    start_agents()

    try:
        stream_logs()
    except KeyboardInterrupt:
        shutdown()
