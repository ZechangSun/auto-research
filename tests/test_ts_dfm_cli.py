from reproductions.ts_dfm_2511_17229.cli import main


def test_tsdfm_cli_make_synthetic(tmp_path):
    output = tmp_path / "synthetic.jsonl"

    exit_code = main(["make-synthetic", "--output", str(output), "--count", "2", "--atoms", "3"])

    assert exit_code == 0
    assert len(output.read_text(encoding="utf-8").strip().splitlines()) == 2


def test_tsdfm_cli_reports_download_errors(tmp_path, monkeypatch, capsys):
    import reproductions.ts_dfm_2511_17229.cli as cli

    def fail_download(name, output):
        raise RuntimeError("blocked")

    monkeypatch.setattr(cli, "download_dataset", fail_download)

    exit_code = main(["download", "transition1x", "--output", str(tmp_path / "Transition1x.h5")])

    assert exit_code == 2
    assert "blocked" in capsys.readouterr().out
