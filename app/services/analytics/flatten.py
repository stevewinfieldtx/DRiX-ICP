"""Flatten a lead's nested speculative_data into typed, comparable features.

- scalars (bool/int/float/str) -> one feature
- lists of scalars -> membership booleans  f"{path}:{item}"  + f"{path}__count"
- dicts -> recursed with dotted paths
Noisy/raw/identifying keys are skipped so the miner compares signal, not text.
"""
from typing import Any

_SKIP_KEYS = {
    "_captured_at", "pages_fetched", "spf_record", "dmarc_record", "mx_hosts",
    "_headcounts_used", "description", "specialties", "social_links",
    "open_roles",
}
_MAX_LIST_ITEMS = 25


def flatten(data: dict | None, prefix: str = "") -> dict[str, Any]:
    out: dict[str, Any] = {}
    if not isinstance(data, dict):
        return out
    for key, value in data.items():
        if key in _SKIP_KEYS or key.startswith("__"):
            continue
        path = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict):
            out.update(flatten(value, path))
        elif isinstance(value, list):
            scalars = [v for v in value if isinstance(v, (str, int, float, bool))]
            out[f"{path}__count"] = len(scalars)
            for item in scalars[:_MAX_LIST_ITEMS]:
                out[f"{path}:{item}"] = True
        elif isinstance(value, (bool, int, float, str)):
            out[path] = value
        # None and other types are dropped (treated as 'unknown')
    return out


def is_numeric(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)
