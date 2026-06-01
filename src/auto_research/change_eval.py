from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
import time
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(frozen=True)
class CommandResult:
    name: str
    command: str
    cwd: str
    exit_code: int
    stdout: str
    stderr: str
    duration_seconds: float

    @property
    def passed(self) -> bool:
        return self.exit_code == 0


@dataclass(frozen=True)
class CommandComparison:
    name: str
    command: str
    baseline_exit_code: int
    current_exit_code: int
    status: str
    summary: str


@dataclass(frozen=True)
class ChangeComparison:
    status: str
    recommendation: str
    commands: list[CommandComparison]
    baseline: list[CommandResult]
    current: list[CommandResult]

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2)

    def to_markdown(self) -> str:
        lines = [
            "# Change Comparison",
            "",
            f"Status: {self.status}",
            f"Recommendation: {self.recommendation}",
            "",
            "## Commands",
        ]
        for item in self.commands:
            lines.append(
                f"- [{item.status}] `{item.command}` "
                f"baseline={item.baseline_exit_code} current={item.current_exit_code}: {item.summary}"
            )
        return "\n".join(lines)


def run_command(command: str, cwd: str | Path, timeout: int = 120) -> CommandResult:
    start = time.monotonic()
    completed = subprocess.run(
        command,
        cwd=Path(cwd),
        shell=True,
        text=True,
        capture_output=True,
        timeout=timeout,
    )
    return CommandResult(
        name=command,
        command=command,
        cwd=str(cwd),
        exit_code=completed.returncode,
        stdout=_tail(completed.stdout),
        stderr=_tail(completed.stderr),
        duration_seconds=time.monotonic() - start,
    )


def compare_command_results(
    baseline: list[CommandResult],
    current: list[CommandResult],
) -> ChangeComparison:
    comparisons = []
    for before, after in zip(baseline, current, strict=True):
        if before.passed and not after.passed:
            status = "regression"
            summary = "passed before and fails now"
        elif not before.passed and after.passed:
            status = "improved"
            summary = "failed before and passes now"
        elif before.passed and after.passed:
            status = "stable_pass"
            summary = "passes in both versions"
        else:
            status = "stable_fail"
            summary = "fails in both versions"
        comparisons.append(
            CommandComparison(
                name=after.name,
                command=after.command,
                baseline_exit_code=before.exit_code,
                current_exit_code=after.exit_code,
                status=status,
                summary=summary,
            )
        )

    statuses = {item.status for item in comparisons}
    if "regression" in statuses:
        overall = "regression"
        recommendation = "Fix the regression before continuing; compare the failing command output against baseline."
    elif "improved" in statuses and statuses <= {"improved", "stable_pass"}:
        overall = "improved"
        recommendation = "Keep the change and run broader validation before archiving the result."
    elif statuses == {"stable_pass"}:
        overall = "stable"
        recommendation = "No command-level regression detected; continue with the next planned improvement."
    elif "improved" in statuses:
        overall = "mixed"
        recommendation = "Preserve the improvements, then investigate commands that still fail."
    else:
        overall = "still_failing"
        recommendation = "Do not stop as complete; use the shared failure output to plan the next adjustment."
    return ChangeComparison(overall, recommendation, comparisons, baseline, current)


def run_git_comparison(
    repo: str | Path,
    commands: list[str],
    base: str = "HEAD~1",
    head: str = "working-tree",
    timeout: int = 120,
) -> ChangeComparison:
    repo_path = Path(repo).resolve()
    with tempfile.TemporaryDirectory(prefix="auto-research-compare-") as tmp:
        tmp_path = Path(tmp)
        base_path = tmp_path / "base"
        _git(repo_path, "worktree", "add", "--detach", str(base_path), base)
        try:
            baseline = [run_command(command, base_path, timeout=timeout) for command in commands]
            if head == "working-tree":
                current_path = repo_path
                current = [run_command(command, current_path, timeout=timeout) for command in commands]
            else:
                head_path = tmp_path / "head"
                _git(repo_path, "worktree", "add", "--detach", str(head_path), head)
                try:
                    current = [run_command(command, head_path, timeout=timeout) for command in commands]
                finally:
                    _remove_worktree(repo_path, head_path)
        finally:
            _remove_worktree(repo_path, base_path)
    return compare_command_results(baseline, current)


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            ["git", *args],
            cwd=repo,
            text=True,
            capture_output=True,
            check=True,
        )
    except subprocess.CalledProcessError as exc:
        message = (exc.stderr or exc.stdout or str(exc)).strip()
        raise RuntimeError(message) from exc


def _remove_worktree(repo: Path, path: Path) -> None:
    subprocess.run(
        ["git", "worktree", "remove", "--force", str(path)],
        cwd=repo,
        text=True,
        capture_output=True,
        check=False,
    )
    if path.exists():
        shutil.rmtree(path, ignore_errors=True)


def _tail(text: str, limit: int = 4000) -> str:
    if len(text) <= limit:
        return text
    return text[-limit:]
