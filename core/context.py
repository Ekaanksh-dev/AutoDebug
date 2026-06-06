# AutoDebug — Multi-Agent Bug Fixing System
# Copyright 2026 Ekaanksh (github.com/Ekaanksh-dev)
# Licensed under Apache License 2.0

from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime


@dataclass
class BugContext:
    """
    Shared data structure passed between all 5 agents via Band.
    Every agent reads from this and adds its findings.
    """

    # ── Repo Info (filled by Detector) ───────────────
    repo_name: str = ""
    repo_url: str = ""
    branch: str = ""
    commit_sha: str = ""
    triggered_at: str = field(
        default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    )

    # ── Bug Info (filled by Detector) ────────────────
    error_type: str = ""
    error_message: str = ""
    bug_file: str = ""
    bug_line: int = 0
    raw_code: str = ""
    surrounding_code: str = ""

    # ── Analysis (filled by Analyser) ────────────────
    root_cause: str = ""
    severity: str = ""
    affected_files: list = field(default_factory=list)

    # ── Fix (filled by Fixer) ─────────────────────────
    suggested_fix: str = ""
    fix_explanation: str = ""

    # ── Test Results (filled by Tester) ──────────────
    tests_passed: bool = False
    test_output: str = ""
    bug_confirmed: bool = False

    # ── Fix Report (filled by Resolver) ──────────────
    fix_report: str = ""
    fix_location: str = ""
    fix_steps: list = field(default_factory=list)

    # ── Pipeline Status ───────────────────────────────
    current_agent: str = ""
    pipeline_complete: bool = False
    error_in_pipeline: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "repo_name": self.repo_name,
            "repo_url": self.repo_url,
            "branch": self.branch,
            "commit_sha": self.commit_sha,
            "triggered_at": self.triggered_at,
            "error_type": self.error_type,
            "error_message": self.error_message,
            "bug_file": self.bug_file,
            "bug_line": self.bug_line,
            "raw_code": self.raw_code,
            "surrounding_code": self.surrounding_code,
            "root_cause": self.root_cause,
            "severity": self.severity,
            "affected_files": self.affected_files,
            "suggested_fix": self.suggested_fix,
            "fix_explanation": self.fix_explanation,
            "tests_passed": self.tests_passed,
            "test_output": self.test_output,
            "bug_confirmed": self.bug_confirmed,
            "fix_report": self.fix_report,
            "fix_location": self.fix_location,
            "fix_steps": self.fix_steps,
            "current_agent": self.current_agent,
            "pipeline_complete": self.pipeline_complete,
            "error_in_pipeline": self.error_in_pipeline,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "BugContext":
        ctx = cls()
        for key, value in data.items():
            if hasattr(ctx, key):
                setattr(ctx, key, value)
        return ctx

    def summary(self) -> str:
        return (
            f"[{self.severity.upper()}] {self.error_type} in "
            f"{self.bug_file}:{self.bug_line} → {self.repo_name}"
        )
