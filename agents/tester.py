# AutoDebug — Multi-Agent Bug Fixing System
# Copyright 2026 Ekaanksh (github.com/Ekaanksh-dev)
# Licensed under Apache License 2.0

import os
import subprocess
from dotenv import load_dotenv
from core.context import BugContext
from band.client import BandClient

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


def confirm_bug_exists(test_output: str, error_type: str) -> bool:
    """Check if the known bug appears in test output"""
    indicators = [
        "FAILED",
        "ERROR",
        "error",
        error_type,
        "AssertionError",
        "Exception"
    ]

    for indicator in indicators:
        if indicator in test_output:
            return True

    return False


def run() -> BugContext:
    """Main tester function"""
    band.log("⏳ Waiting for Fixer...")

    # Receive context from Fixer via Band
    data = band.receive(timeout=60)

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
    ctx.bug_confirmed = confirm_bug_exists(
        test_result["output"],
        ctx.error_type
    )

    if ctx.bug_confirmed:
        band.log(f"🐛 Bug confirmed by tests!")
        band.log(f"📊 Test output:\n{ctx.test_output[:300]}")
    else:
        band.log("✅ No bug confirmed in tests")

    # Send to Resolver via Band regardless
    band.send("ResolverAgent", ctx.to_dict())

    return ctx
