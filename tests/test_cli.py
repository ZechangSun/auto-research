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
