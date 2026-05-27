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
            "1",
        ]
    )

    assert exit_code == 0
    assert "Auto-Research Improvement Brief" in output.read_text(encoding="utf-8")
