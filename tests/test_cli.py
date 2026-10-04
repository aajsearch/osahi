import json

from osahi.cli import main
from osahi.schema import repo_root


def test_cli_accepts_the_handwritten_finish_trajectory(capsys):
    path = repo_root() / "conformance" / "fixtures" / "accept-finish.json"
    assert main([str(path)]) == 0
    assert "ok 4 events" in capsys.readouterr().out


def test_cli_rejects_a_gapped_sequence(capsys):
    path = repo_root() / "conformance" / "fixtures" / "reject-seq-gap.json"
    assert main([str(path)]) == 1
    assert "seq.contiguous" in capsys.readouterr().out


def test_cli_usage_without_a_file():
    assert main([]) == 2


def test_checked_file_is_json():
    path = repo_root() / "conformance" / "fixtures" / "accept-finish.json"
    assert isinstance(json.loads(path.read_text(encoding="utf-8")), list)
