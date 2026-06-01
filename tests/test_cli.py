import subprocess
import sys

from auto_research.cli import main


def test_cli_keeps_legacy_task_argument(tmp_path, capsys):
    db = tmp_path / "memory.sqlite"

    exit_code = main(["Research a small task", "--db", str(db), "--max-steps", "1"])

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "Research Report" in output


def test_cli_improve_writes_brief(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "README.md").write_text("# Example\n", encoding="utf-8")
    output = tmp_path / "brief.md"
    db = tmp_path / "memory.sqlite"

    exit_code = main(
        [
            "improve",
            "--repo",
            str(repo),
            "--db",
            str(db),
            "--output",
            str(output),
            "--max-steps",
            "2",
        ]
    )

    assert exit_code == 0
    assert "Auto-Research Improvement Brief" in output.read_text(encoding="utf-8")


def test_cli_memory_search_and_consolidate(tmp_path, capsys):
    db = tmp_path / "memory.sqlite"

    remember_code = main(
        [
            "memory",
            "remember",
            "Use BM25 retrieval workflow for memory.",
            "--db",
            str(db),
            "--scope",
            "episodic",
            "--tag",
            "retrieval",
        ]
    )
    search_code = main(["memory", "search", "BM25 retrieval", "--db", str(db)])
    consolidate_code = main(["memory", "consolidate", "--db", str(db)])

    output = capsys.readouterr().out
    assert remember_code == 0
    assert search_code == 0
    assert consolidate_code == 0
    assert "bm25" in output.lower()
    assert "Memory Consolidation" in output


def test_cli_runs_start_step_status(tmp_path, capsys):
    db = tmp_path / "memory.sqlite"
    state_dir = tmp_path / "runs"

    start_code = main(
        [
            "runs",
            "start",
            "Long running research task",
            "--db",
            str(db),
            "--state-dir",
            str(state_dir),
            "--max-steps",
            "2",
        ]
    )
    output = capsys.readouterr().out
    run_id = output.split()[1]

    step_code = main(["runs", "step", run_id, "--db", str(db), "--state-dir", str(state_dir)])
    status_code = main(["runs", "status", run_id, "--state-dir", str(state_dir)])

    output = capsys.readouterr().out
    assert start_code == 0
    assert step_code == 0
    assert status_code == 0
    assert "status=" in output
    assert "Long running research task" in output


def test_cli_runs_multi_step_and_brief(tmp_path, capsys):
    db = tmp_path / "memory.sqlite"
    state_dir = tmp_path / "runs"

    main(
        [
            "runs",
            "start",
            "Build an auto-research equipment brief",
            "--db",
            str(db),
            "--state-dir",
            str(state_dir),
            "--max-steps",
            "4",
        ]
    )
    run_id = capsys.readouterr().out.split()[1]

    step_code = main(
        [
            "runs",
            "step",
            run_id,
            "--db",
            str(db),
            "--state-dir",
            str(state_dir),
            "--steps",
            "2",
        ]
    )
    brief_code = main(["runs", "brief", run_id, "--db", str(db), "--state-dir", str(state_dir)])

    output = capsys.readouterr().out
    assert step_code == 0
    assert brief_code == 0
    assert "Auto-Research Run Brief" in output
    assert "Recent Events" in output


def test_cli_runs_step_writes_prompt_file(tmp_path, capsys):
    db = tmp_path / "memory.sqlite"
    state_dir = tmp_path / "runs"
    prompt_dir = tmp_path / "prompts"

    main(
        [
            "runs",
            "start",
            "Write deterministic prompt files",
            "--db",
            str(db),
            "--state-dir",
            str(state_dir),
            "--prompt-dir",
            str(prompt_dir),
        ]
    )
    run_id = capsys.readouterr().out.split()[1]
    exit_code = main(
        [
            "runs",
            "step",
            run_id,
            "--db",
            str(db),
            "--state-dir",
            str(state_dir),
            "--prompt-dir",
            str(prompt_dir),
        ]
    )

    assert exit_code == 0
    assert list(prompt_dir.glob(f"{run_id}/*.md"))


def test_cli_agent_next_and_complete(tmp_path, capsys):
    db = tmp_path / "memory.sqlite"
    state_dir = tmp_path / "runs"
    prompt_dir = tmp_path / "prompts"
    observation_file = tmp_path / "observation.md"
    observation_file.write_text(
        "The coding agent completed this step using local tools and returned a detailed observation.",
        encoding="utf-8",
    )

    main(
        [
            "runs",
            "start",
            "Use current coding agent as executor",
            "--db",
            str(db),
            "--state-dir",
            str(state_dir),
            "--max-steps",
            "2",
        ]
    )
    run_id = capsys.readouterr().out.split()[1]
    next_code = main(
        [
            "agent",
            "next",
            run_id,
            "--db",
            str(db),
            "--state-dir",
            str(state_dir),
            "--prompt-dir",
            str(prompt_dir),
        ]
    )
    output = capsys.readouterr().out
    step_id = [line for line in output.splitlines() if line.startswith("Step:")][0].split()[1]

    complete_code = main(
        [
            "agent",
            "complete",
            run_id,
            "--step-id",
            step_id,
            "--observation-file",
            str(observation_file),
            "--db",
            str(db),
            "--state-dir",
            str(state_dir),
        ]
    )

    output = capsys.readouterr().out
    assert next_code == 0
    assert complete_code == 0
    assert "Auto-Research Run Brief" in output
    assert list(prompt_dir.glob(f"{run_id}/*.md"))


def test_cli_human_request_status_and_respond(tmp_path, capsys):
    db = tmp_path / "memory.sqlite"
    state_dir = tmp_path / "runs"

    main(
        [
            "runs",
            "start",
            "Use human checkpoints",
            "--db",
            str(db),
            "--state-dir",
            str(state_dir),
            "--max-steps",
            "2",
        ]
    )
    run_id = capsys.readouterr().out.split()[1]

    request_code = main(
        [
            "human",
            "request",
            run_id,
            "--kind",
            "approval",
            "--prompt",
            "Approve the next step?",
            "--state-dir",
            str(state_dir),
        ]
    )
    status_code = main(["human", "status", run_id, "--state-dir", str(state_dir)])
    respond_code = main(
        [
            "human",
            "respond",
            run_id,
            "--decision",
            "revise",
            "--content",
            "Use a smaller baseline first.",
            "--db",
            str(db),
            "--state-dir",
            str(state_dir),
        ]
    )

    output = capsys.readouterr().out
    assert request_code == 0
    assert status_code == 0
    assert respond_code == 0
    assert "needs_human" in output
    assert "Use a smaller baseline first." in output


def test_cli_compare_reports_regression_against_git_base(tmp_path, capsys):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "check.py").write_text("raise SystemExit(0)\n", encoding="utf-8")
    subprocess.run(["git", "init"], cwd=repo, check=True, stdout=subprocess.DEVNULL)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=repo, check=True)
    subprocess.run(["git", "add", "check.py"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-m", "baseline"], cwd=repo, check=True, stdout=subprocess.DEVNULL)
    (repo / "check.py").write_text("raise SystemExit(1)\n", encoding="utf-8")

    exit_code = main(
        [
            "compare",
            "--repo",
            str(repo),
            "--base",
            "HEAD",
            "--command",
            f"{sys.executable} check.py",
        ]
    )

    output = capsys.readouterr().out
    assert exit_code == 1
    assert "regression" in output
