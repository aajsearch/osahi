import json

import pytest

from osahi.config import (
    ENTERPRISE_CONTEXT_BUDGET,
    ENTERPRISE_RETRY_CAP,
    PROFILE_DEFAULTS,
    STARTUP_CONTEXT_BUDGET,
    STARTUP_RETRY_CAP,
    ConfigError,
    load_config,
)


def _document(**overrides) -> dict:
    document = {
        "spec_version": "0.1.0",
        "profile": "startup",
        "model": {"provider": "scripted", "name": "fixture-model"},
        "workload": {"id": "wl_demo", "name": "demo"},
        "harness": {"name": "osahi-reference", "version": "0.1.0"},
        "policy": {"policy_id": "allowlist", "allow": ["tool.echo"]},
        "metadata": {},
    }
    document.update(overrides)
    return document


def test_profile_defaults_are_visible_and_startup_is_not_enterprise():
    assert PROFILE_DEFAULTS["startup"]["context"]["budget"] == STARTUP_CONTEXT_BUDGET == 8
    assert PROFILE_DEFAULTS["startup"]["recovery"]["max_retries"] == STARTUP_RETRY_CAP == 2
    assert PROFILE_DEFAULTS["enterprise"]["context"]["budget"] == ENTERPRISE_CONTEXT_BUDGET == 4
    assert PROFILE_DEFAULTS["enterprise"]["recovery"]["max_retries"] == ENTERPRISE_RETRY_CAP == 1
    assert PROFILE_DEFAULTS["startup"]["recovery"]["checkpoints"] is True
    assert PROFILE_DEFAULTS["enterprise"]["telemetry"]["enabled"] is True


def test_omitted_startup_limits_use_the_profile_defaults():
    config = load_config(_document())
    assert config.context.budget == 8
    assert config.recovery.max_retries == 2
    assert config.recovery.checkpoints is True
    assert config.telemetry.enabled is True
    assert config.metadata == {}
    assert config.policy.allow == ("tool.echo",)


def test_startup_does_not_require_enterprise_audit_keys():
    config = load_config(_document(metadata={}))
    assert "owner" not in config.metadata
    assert "environment" not in config.metadata


def test_enterprise_defaults_are_stricter_and_metadata_is_kept():
    config = load_config(
        _document(
            profile="enterprise",
            metadata={"owner": "platform-team", "environment": "production"},
        )
    )
    assert config.context.budget == 4
    assert config.recovery.max_retries == 1
    assert config.metadata["owner"] == "platform-team"
    assert config.metadata["environment"] == "production"


def test_explicit_budget_overrides_the_profile_default():
    config = load_config(_document(context={"budget": 3}))
    assert config.context.budget == 3


def test_config_loaded_from_a_file_matches_the_object(tmp_path):
    path = tmp_path / "harness.json"
    path.write_text(json.dumps(_document()), encoding="utf-8")
    assert load_config(path).workload.id == "wl_demo"


@pytest.mark.parametrize(
    ("mutate", "field"),
    [
        ("missing-allow", "policy.allow"),
        ("budget-1", "context.budget"),
        ("unknown-profile", "profile"),
        ("missing-workload-id", "workload.id"),
        ("checkpoints-off", "recovery.checkpoints"),
    ],
)
def test_invalid_config_names_the_field(mutate, field):
    document = _document()
    if mutate == "missing-allow":
        del document["policy"]["allow"]
    elif mutate == "budget-1":
        document["context"] = {"budget": 1}
    elif mutate == "unknown-profile":
        document["profile"] = "platform"
    elif mutate == "missing-workload-id":
        del document["workload"]["id"]
    elif mutate == "checkpoints-off":
        document["recovery"] = {"max_retries": 2, "checkpoints": False}
    with pytest.raises(ConfigError) as caught:
        load_config(document)
    assert field in str(caught.value)
    assert any(error[0] == field or field in error[0] for error in caught.value.errors)


def test_enterprise_missing_owner_names_that_field_and_startup_does_not():
    with pytest.raises(ConfigError) as caught:
        load_config(_document(profile="enterprise", metadata={}))
    assert "metadata.owner" in str(caught.value)
    load_config(_document(profile="startup", metadata={}))


def test_enterprise_blank_environment_is_rejected():
    with pytest.raises(ConfigError) as caught:
        load_config(
            _document(
                profile="enterprise",
                metadata={"owner": "platform-team", "environment": ""},
            )
        )
    assert "metadata.environment" in str(caught.value)


def test_unknown_top_level_field_is_rejected():
    document = _document()
    document["sandbox"] = "wasm"
    with pytest.raises(ConfigError) as caught:
        load_config(document)
    assert caught.value.errors[0][0] == "sandbox"
