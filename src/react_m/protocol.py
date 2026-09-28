"""JSON protocol and deterministic parameter binding; no expression evaluation."""

import copy
import re
from typing import Any

from jsonschema import Draft202012Validator

_POINTER = {"type": "string", "pattern": r"^(?:/(?:[^~]|~[01])*)*$"}
BINDING_SCHEMA = {
    "type": "object",
    "required": ["action", "pointer"],
    "additionalProperties": False,
    "properties": {
        "action": {"type": "string"},
        "pointer": _POINTER,
        "select": {"const": "only"},
        "project": _POINTER,
    },
    "dependentRequired": {"project": ["select"]},
}
ACTION_SCHEMA = {
    "type": "object",
    "required": ["id", "tool"],
    "additionalProperties": False,
    "properties": {
        "id": {"type": "string", "pattern": "^[A-Za-z][A-Za-z0-9_-]{0,63}$"},
        "tool": {"type": "string", "minLength": 1},
        "args": {"type": "object"},
        "bindings": {"type": "object", "additionalProperties": BINDING_SCHEMA},
        "depends_on": {"type": "array", "items": {"type": "string"}, "uniqueItems": True},
    },
}
BATCH_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": ["actions"],
    "additionalProperties": False,
    "properties": {
        "actions": {"type": "array", "minItems": 1, "maxItems": 32, "items": ACTION_SCHEMA}
    },
}
BATCH_VALIDATOR = Draft202012Validator(BATCH_SCHEMA)


class NeedsReasoning(Exception):
    """A deterministic selection cannot choose a unique result."""


def dependencies(action: dict[str, Any]) -> set[str]:
    return set(action.get("depends_on", [])) | {
        binding["action"] for binding in action.get("bindings", {}).values()
    }


def pointer(value: Any, path: str) -> Any:
    """Resolve an RFC 6901 JSON Pointer, rejecting missing and invalid locations."""
    if path == "":
        return value
    if not re.fullmatch(_POINTER["pattern"], path):
        raise ValueError("Invalid JSON Pointer")
    for encoded in path[1:].split("/"):
        part = encoded.replace("~1", "/").replace("~0", "~")
        if isinstance(value, list):
            if not re.fullmatch(r"0|[1-9][0-9]*", part):
                raise ValueError(f"Invalid array index: {part}")
            value = value[int(part)]
        elif isinstance(value, dict):
            value = value[part]
        else:
            raise ValueError(f"Cannot traverse JSON Pointer {path}")
    return value


def bind_arguments(action: dict[str, Any], results: dict[str, Any]) -> dict[str, Any]:
    args = copy.deepcopy(action.get("args", {}))
    for name, binding in action.get("bindings", {}).items():
        value = pointer(results[binding["action"]]["output"], binding["pointer"])
        if binding.get("select") == "only":
            if not isinstance(value, list):
                raise ValueError("select=only requires an array")
            if len(value) != 1:
                raise NeedsReasoning(f"Expected exactly one candidate, received {len(value)}")
            value = pointer(value[0], binding.get("project", ""))
        args[name] = copy.deepcopy(value)
    return args
