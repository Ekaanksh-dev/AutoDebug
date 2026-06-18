# AutoDebug — Multi-Agent Bug Fixing System
# Copyright 2026 Ekaanksh (github.com/Ekaanksh-dev)
# Licensed under Apache License 2.0

import os
import subprocess
from dotenv import load_dotenv
from core.context import BugContext
from band_local.client import BandClient

load_dotenv()

band = BandClient("TesterAgent")


def run_pytest(repo_path: str) -> dict:
    """Run pytest on the cloned repo"""
    band.log("🧪 Running pytest...")

    try:
        result = subprocess.run(
            ["python", "-m", "pytest", repo_path,
             "--tb=short", "-q", "--no-header"],
            capture_output=True,
            text=True,
            timeout=int(os.getenv("TIMEOUT_SECONDS", 30))
        )

        passed = result.returncode == 0
        output = result.stdout + result.stderr

        return {
            "passed": passed,
            "output": output[:2000],
            "returncode": result.returncode
        }

    except subprocess.TimeoutExpired:
        return {
            "passed": False,
            "output": "❌ Tests timed out",
            "returncode": -1
        }
    except Exception as e:
        return {
            "passed": False,
            "output": f"❌ pytest error: {str(e)}",
            "returncode": -1
        }


def confirm_bug_exists(test_output: str, error_type: str, clone_path: str, bug_file: str) -> bool:
    """Check pytest output OR directly run the buggy file"""
    indicators = ["FAILED", "ERROR", "error", error_type, "AssertionError", "Exception"]
    for indicator in indicators:
        if indicator in test_output:
            return True

    # No tests found — run the actual buggy file directly
    full_path = os.path.join(clone_path, bug_file.lstrip("/"))
    if os.path.exists(full_path):
        result = subprocess.run(
            ["python", full_path],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode != 0 and error_type in result.stderr:
            return True

    return False

def run() -> BugContext:
    """Main tester function"""
    band.log("⏳ Waiting for Fixer...")

    # Receive context from Fixer via Band
    data = band.receive(timeout=120)

    if not data:
        band.log("❌ No data received from Fixer")
        return BugContext()

    ctx = BugContext.from_dict(data)
    ctx.current_agent = "TesterAgent"

    band.log(f"📥 Received: {ctx.summary()}")

    # Build repo path
    repo_path = f"/tmp/{ctx.repo_name.replace('/', '_')}"

    # Run tests
    test_result = run_pytest(repo_path)

    # Update context
    ctx.tests_passed = test_result["passed"]
    ctx.test_output = test_result["output"]
    repo_path = f"/tmp/{ctx.repo_name.replace('/', '_')}"
    ctx.bug_confirmed = confirm_bug_exists(
        test_result["output"],
        ctx.error_type,
        repo_path,
        ctx.bug_file
    )

    if ctx.bug_confirmed:
        band.log(f"🐛 Bug confirmed by tests!")
        band.log(f"📊 Test output:\n{ctx.test_output[:300]}")
    else:
        band.log("✅ No bug confirmed in tests")

    # Send to Resolver via Band regardless
    band.send("ResolverAgent", ctx.to_dict())

    return ctx
