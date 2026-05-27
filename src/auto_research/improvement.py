from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

from auto_research.memory import LongTermMemory
from auto_research.pipeline import ResearchPipeline, ResearchReport


@dataclass(frozen=True)
class RepoSnapshot:
    path: Path
    files: list[str]
    git_status: str
    test_files: list[str]
    skill_files: list[str]

    def to_prompt_context(self) -> str:
        return "\n".join(
            [
                f"Repository: {self.path}",
                f"Tracked source-like files: {len(self.files)}",
                f"Test files: {', '.join(self.test_files) or 'none found'}",
                f"Skill files: {', '.join(self.skill_files) or 'none found'}",
                f"Git status: {self.git_status or 'clean'}",
                "Important files:",
                *[f"- {file}" for file in self.files[:80]],
            ]
        )


@dataclass(frozen=True)
class ImprovementResult:
    snapshot: RepoSnapshot
    report: ResearchReport
    output_path: Path


def collect_repo_snapshot(repo_path: Path) -> RepoSnapshot:
    repo_path = repo_path.resolve()
    interesting_suffixes = {".md", ".py", ".toml", ".yaml", ".yml", ".json"}
    ignored_parts = {".git", ".venv", "__pycache__", ".pytest_cache", ".auto_research"}
    files = [
        str(path.relative_to(repo_path))
        for path in repo_path.rglob("*")
        if path.is_file()
        and path.suffix in interesting_suffixes
        and not any(part in ignored_parts for part in path.parts)
    ]
    files.sort()
    return RepoSnapshot(
        path=repo_path,
        files=files,
        git_status=_git_status(repo_path),
        test_files=[file for file in files if file.startswith("tests/") or file.endswith("_test.py")],
        skill_files=[file for file in files if file.endswith("SKILL.md")],
    )


def improve_repository(
    repo_path: Path,
    db_path: Path,
    max_steps: int = 5,
    session_id: str | None = "repo-improvement",
    output_path: Path = Path(".auto_research/improvement_brief.md"),
) -> ImprovementResult:
    snapshot = collect_repo_snapshot(repo_path)
    task = _build_improvement_task(snapshot)
    memory = LongTermMemory(db_path)
    try:
        report = ResearchPipeline(memory).run(task, max_steps=max_steps, session_id=session_id)
    finally:
        memory.close()

    resolved_output = output_path if output_path.is_absolute() else snapshot.path / output_path
    resolved_output.parent.mkdir(parents=True, exist_ok=True)
    resolved_output.write_text(_render_improvement_brief(snapshot, report), encoding="utf-8")
    return ImprovementResult(snapshot=snapshot, report=report, output_path=resolved_output)


def _build_improvement_task(snapshot: RepoSnapshot) -> str:
    return (
        "Improve this coding-agent auto-research repository. Focus on making it more useful "
        "as a reusable agent skill and pipeline. Identify the smallest high-value next changes, "
        "risks, validation steps, and how a coding agent should use it.\n\n"
        f"{snapshot.to_prompt_context()}"
    )


def _render_improvement_brief(snapshot: RepoSnapshot, report: ResearchReport) -> str:
    return "\n".join(
        [
            "# Auto-Research Improvement Brief",
            "",
            "## Repository Snapshot",
            snapshot.to_prompt_context(),
            "",
            report.to_markdown(),
            "",
            "## Agent Usage",
            "- Run this command before substantial repo work: `auto-research improve --repo .`.",
            "- Read this brief, choose the smallest useful change, implement it, then run tests.",
            "- Run the command again after changes to preserve long-term improvement memory.",
        ]
    )


def _git_status(repo_path: Path) -> str:
    try:
        result = subprocess.run(
            ["git", "status", "--short"],
            cwd=repo_path,
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.TimeoutExpired):
        return ""
    return result.stdout.strip()
