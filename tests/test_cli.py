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


def test_cli_usage_without_a_file(capsys):
    assert main([]) == 2
    err = capsys.readouterr().err
    assert err.startswith("usage: osahi-check <trajectory.json>\n")
    assert "check-config" in err
    assert "reference config" in err
    assert "|" not in err


def test_check_config_accepts_the_startup_profile(capsys):
    path = repo_root() / "profiles" / "startup.json"
    assert main(["check-config", str(path)]) == 0
    assert "ok config startup" in capsys.readouterr().out


def test_check_config_names_the_bad_field(tmp_path, capsys):
    path = tmp_path / "broken.json"
    document = json.loads((repo_root() / "profiles" / "startup.json").read_text(encoding="utf-8"))
    document["context"]["budget"] = 1
    path.write_text(json.dumps(document), encoding="utf-8")
    assert main(["check-config", str(path)]) == 1
    assert "context.budget" in capsys.readouterr().out


def test_check_config_requires_a_file(capsys):
    assert main(["check-config"]) == 2
    err = capsys.readouterr().err
    assert err.startswith("usage: osahi-check check-config ")
    assert "reference config" in err


def test_checked_file_is_json():
    path = repo_root() / "conformance" / "fixtures" / "accept-finish.json"
    assert isinstance(json.loads(path.read_text(encoding="utf-8")), list)
