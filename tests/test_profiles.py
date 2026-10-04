import json

import pytest

from osahi.build import build_harness
from osahi.config import ConfigError, load_profile
from osahi.model import ScriptedModel
from osahi.schema import repo_root, validate_document


def test_startup_and_enterprise_profiles_validate_and_differ_by_values():
    startup = load_profile("startup")
    enterprise = load_profile("enterprise")
    for name in ("startup", "enterprise"):
        document = json.loads((repo_root() / "profiles" / f"{name}.json").read_text(encoding="utf-8"))
        validate_document(document, "harness-config.schema.json")
    assert startup.profile == "startup"
    assert enterprise.profile == "enterprise"
    assert startup.context.budget == 8
    assert enterprise.context.budget == 4
    assert startup.recovery.max_retries == 2
    assert enterprise.recovery.max_retries == 1
    assert dict(startup.metadata) == {}
    assert enterprise.metadata["owner"] == "platform-team"
    assert enterprise.metadata["environment"] == "production"
    assert "tool.audit" in enterprise.policy.allow
    assert "tool.audit" not in startup.policy.allow
    startup_harness = build_harness(startup, tools=[], model=ScriptedModel([]))
    enterprise_harness = build_harness(enterprise, tools=[], model=ScriptedModel([]))
    assert type(startup_harness) is type(enterprise_harness)
    assert enterprise_harness.max_retries == 1
    assert startup_harness.context.budget == 8


def test_unknown_profile_name_is_rejected():
    with pytest.raises(ConfigError) as caught:
        load_profile("platform")
    assert caught.value.errors[0][0] == "profile"
