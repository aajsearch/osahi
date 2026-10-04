"""Reference harness configuration. Not read by the conformance checker."""

from __future__ import annotations

import copy
import json
import re
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType

import jsonschema

from osahi.errors import OsahiError
from osahi.schema import load_schema

# Visible profile defaults. The schema still rejects a budget below 2, a
# checkpoint flag other than true, and telemetry turned off. Enterprise does
# not get a second runtime; it gets a tighter budget, a tighter retry cap,
# and required audit metadata.
STARTUP_CONTEXT_BUDGET = 8
STARTUP_RETRY_CAP = 2
ENTERPRISE_CONTEXT_BUDGET = 4
ENTERPRISE_RETRY_CAP = 1
ENTERPRISE_METADATA_KEYS = ("owner", "environment")

_REQUIRED_PROPERTY = re.compile(r"'([^']+)' is a required property")
_UNEXPECTED_PROPERTY = re.compile(r"\('([^']+)' was unexpected\)")


def _sections(budget: int, retries: int) -> dict:
    return {
        "context": {"budget": budget},
        "recovery": {"max_retries": retries, "checkpoints": True},
        "telemetry": {"enabled": True},
    }


PROFILE_DEFAULTS = {
    "startup": _sections(STARTUP_CONTEXT_BUDGET, STARTUP_RETRY_CAP),
    "enterprise": _sections(ENTERPRISE_CONTEXT_BUDGET, ENTERPRISE_RETRY_CAP),
    "custom": _sections(STARTUP_CONTEXT_BUDGET, STARTUP_RETRY_CAP),
}


class ConfigError(OsahiError):
    """The reference config is invalid. The run has not started."""

    def __init__(self, errors: list[tuple[str, str]]) -> None:
        self.errors = tuple(errors)
        parts = [f"{path}: {message}" for path, message in self.errors]
        super().__init__("\n".join(parts) if parts else "invalid harness config")


@dataclass(frozen=True)
class ModelConfig:
    provider: str
    name: str


@dataclass(frozen=True)
class WorkloadConfig:
    id: str
    name: str


@dataclass(frozen=True)
class HarnessIdentity:
    name: str
    version: str


@dataclass(frozen=True)
class PolicyConfig:
    policy_id: str
    allow: tuple[str, ...]


@dataclass(frozen=True)
class ContextConfig:
    budget: int


@dataclass(frozen=True)
class RecoveryConfig:
    max_retries: int
    checkpoints: bool


@dataclass(frozen=True)
class TelemetryConfig:
    enabled: bool


@dataclass(frozen=True)
class HarnessConfig:
    spec_version: str
    profile: str
    model: ModelConfig
    workload: WorkloadConfig
    harness: HarnessIdentity
    policy: PolicyConfig
    context: ContextConfig
    recovery: RecoveryConfig
    telemetry: TelemetryConfig
    metadata: MappingProxyType


def load_config(source: dict | str | Path) -> HarnessConfig:
    """Load a JSON object or a JSON file, apply profile defaults, and validate."""

    raw = _read(source)
    if not isinstance(raw, dict):
        raise ConfigError([("<root>", "config must be a JSON object")])
    merged = _apply_profile_defaults(raw)
    _validate(merged)
    return _freeze(merged)


def _read(source: dict | str | Path) -> object:
    if isinstance(source, dict):
        return copy.deepcopy(source)
    path = Path(source)
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ConfigError([("<root>", f"could not read config: {exc.strerror or exc}")]) from exc
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise ConfigError([("<root>", f"invalid JSON: {exc.msg}")]) from exc


def _apply_profile_defaults(raw: dict) -> dict:
    profile = raw.get("profile")
    defaults = PROFILE_DEFAULTS.get(profile, PROFILE_DEFAULTS["custom"])
    merged = copy.deepcopy(raw)
    for key, value in defaults.items():
        if key not in merged:
            merged[key] = copy.deepcopy(value)
            continue
        if isinstance(value, dict) and isinstance(merged[key], dict):
            for inner_key, inner_value in value.items():
                merged[key].setdefault(inner_key, copy.deepcopy(inner_value))
    return merged


def _validate(document: dict) -> None:
    validator = jsonschema.Draft202012Validator(load_schema("harness-config.schema.json"))
    found = sorted(validator.iter_errors(document), key=_error_sort_key)
    leaves = [error for error in found if not error.context]
    errors = [
        (_field_path(error), error.message)
        for error in (leaves or found)
    ]
    if errors:
        raise ConfigError(errors)


def _error_sort_key(error: jsonschema.ValidationError) -> tuple:
    return (list(error.absolute_path), error.message)


def _field_path(error: jsonschema.ValidationError) -> str:
    parts = [str(part) for part in error.absolute_path]
    if error.validator == "required":
        match = _REQUIRED_PROPERTY.search(error.message)
        if match:
            parts.append(match.group(1))
    elif error.validator == "additionalProperties":
        match = _UNEXPECTED_PROPERTY.search(error.message)
        if match and match.group(1) not in parts:
            parts.append(match.group(1))
    if not parts:
        return "<root>"
    return ".".join(parts)


def _freeze(document: dict) -> HarnessConfig:
    metadata = document.get("metadata") or {}
    return HarnessConfig(
        spec_version=document["spec_version"],
        profile=document["profile"],
        model=ModelConfig(**document["model"]),
        workload=WorkloadConfig(**document["workload"]),
        harness=HarnessIdentity(**document["harness"]),
        policy=PolicyConfig(
            policy_id=document["policy"]["policy_id"],
            allow=tuple(document["policy"]["allow"]),
        ),
        context=ContextConfig(budget=document["context"]["budget"]),
        recovery=RecoveryConfig(
            max_retries=document["recovery"]["max_retries"],
            checkpoints=document["recovery"]["checkpoints"] is True,
        ),
        telemetry=TelemetryConfig(enabled=document["telemetry"]["enabled"] is True),
        metadata=MappingProxyType(dict(metadata)),
    )
