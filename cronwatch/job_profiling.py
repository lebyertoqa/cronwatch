"""Job execution profiling: tracks duration statistics per job."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional


@dataclass
class DurationStats:
    job_name: str
    samples: List[float] = field(default_factory=list)

    @property
    def count(self) -> int:
        return len(self.samples)

    @property
    def mean(self) -> Optional[float]:
        if not self.samples:
            return None
        return sum(self.samples) / len(self.samples)

    @property
    def minimum(self) -> Optional[float]:
        return min(self.samples) if self.samples else None

    @property
    def maximum(self) -> Optional[float]:
        return max(self.samples) if self.samples else None

    @property
    def p95(self) -> Optional[float]:
        """95th-percentile duration in seconds."""
        if not self.samples:
            return None
        sorted_samples = sorted(self.samples)
        idx = max(0, int(len(sorted_samples) * 0.95) - 1)
        return sorted_samples[idx]


class ProfilingStore:
    """Persists per-job duration samples as JSON on disk."""

    def __init__(self, data_dir: str) -> None:
        self._path = Path(data_dir) / "profiling.json"
        self._data: Dict[str, List[float]] = self._load()

    def _load(self) -> Dict[str, List[float]]:
        if not self._path.exists():
            return {}
        try:
            return json.loads(self._path.read_text())
        except (json.JSONDecodeError, OSError):
            return {}

    def _save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps(self._data, indent=2))

    def record(self, job_name: str, duration_seconds: float) -> None:
        self._data.setdefault(job_name, []).append(round(duration_seconds, 4))
        self._save()

    def stats_for(self, job_name: str) -> DurationStats:
        samples = list(self._data.get(job_name, []))
        return DurationStats(job_name=job_name, samples=samples)

    def all_job_names(self) -> List[str]:
        return list(self._data.keys())

    def clear(self, job_name: str) -> None:
        self._data.pop(job_name, None)
        self._save()
