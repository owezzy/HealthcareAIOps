"""JSON Schema for strict structured output.

Providers' strict modes (OpenAI `response_format: json_schema, strict: true`)
accept a subset of JSON Schema: every object closed, every property listed in
`required` (optional values expressed as nullable), and no length or default
keywords. This turns a contract's Pydantic schema into that subset.

Dropping keywords only loosens what the provider enforces. The full rules
still apply when the output is parsed with the Pydantic model itself
(e.g. `parse_findings`), so nothing is lost.
"""

from typing import Any

from pydantic import BaseModel

#: Keywords strict mode rejects; Pydantic validation re-checks them after parsing.
UNSUPPORTED_KEYWORDS = frozenset(
    {"minLength", "maxLength", "default", "minProperties", "maxProperties", "title"}
)


def strict_json_schema(model: type[BaseModel]) -> dict[str, Any]:
    return _strict(model.model_json_schema())


def _strict(node: Any) -> Any:
    if isinstance(node, list):
        return [_strict(item) for item in node]
    if not isinstance(node, dict):
        return node
    out = {
        key: _strict(value) if key not in ("properties", "$defs") else value
        for key, value in node.items()
        if key not in UNSUPPORTED_KEYWORDS
    }
    for key in ("properties", "$defs"):
        if key in node:
            # Property and definition names are data, never keywords to drop.
            out[key] = {name: _strict(schema) for name, schema in node[key].items()}
    if out.get("type") == "object" and "properties" in out:
        out["required"] = list(out["properties"])
        out["additionalProperties"] = False
    return out
