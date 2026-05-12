"""Utilities for handling secret/sensitive values in job configurations."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional

_REDACTED = "***"


@dataclass
class SecretRef:
    """A reference to a secret value resolved from an environment variable."""

    env_var: str
    default: Optional[str] = None

    def resolve(self) -> Optional[str]:
        """Return the secret value, falling back to *default* when absent."""
        return os.environ.get(self.env_var, self.default)

    def is_available(self) -> bool:
        """Return True if the environment variable is set."""
        return self.env_var in os.environ or self.default is not None


def secrets_for(job) -> Dict[str, SecretRef]:
    """Return the SecretRef mapping declared on *job*, or an empty dict."""
    raw = getattr(job, "secrets", None)
    if not raw or not isinstance(raw, dict):
        return {}
    result: Dict[str, SecretRef] = {}
    for key, spec in raw.items():
        if isinstance(spec, dict):
            result[key] = SecretRef(
                env_var=spec["env_var"],
                default=spec.get("default"),
            )
        elif isinstance(spec, str):
            result[key] = SecretRef(env_var=spec)
    return result


def resolve_secrets(job) -> Dict[str, str]:
    """Resolve all secrets for *job* and return a plain string mapping.

    Secrets whose environment variable is not set and have no default are
    omitted from the result.
    """
    resolved: Dict[str, str] = {}
    for key, ref in secrets_for(job).items():
        value = ref.resolve()
        if value is not None:
            resolved[key] = value
    return resolved


def missing_secrets(job) -> List[str]:
    """Return names of secrets that cannot be resolved for *job*."""
    return [
        key
        for key, ref in secrets_for(job).items()
        if not ref.is_available()
    ]


def redacted_secrets(job) -> Dict[str, str]:
    """Return the secrets mapping with all values replaced by '***'."""
    return {key: _REDACTED for key in secrets_for(job)}
