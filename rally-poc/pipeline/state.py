"""Pipeline state: JSON checkpoint/resume system."""
from __future__ import annotations

import json
import os
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

_save_lock = threading.Lock()


STEP_NAMES = ("image", "audio", "video", "lipsync")
STATUS_PENDING = "pending"
STATUS_RUNNING = "running"
STATUS_COMPLETED = "completed"
STATUS_FAILED = "failed"
STATUS_SKIPPED = "skipped"


@dataclass
class StepState:
    status: str = STATUS_PENDING
    path: Optional[str] = None
    cost: float = 0.0
    error: Optional[str] = None
    attempts: int = 0

    def to_dict(self) -> dict:
        d: dict = {"status": self.status}
        if self.path:
            d["path"] = self.path
        if self.cost:
            d["cost"] = round(self.cost, 4)
        if self.error:
            d["error"] = self.error
        if self.attempts:
            d["attempts"] = self.attempts
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "StepState":
        return cls(
            status=d.get("status", STATUS_PENDING),
            path=d.get("path"),
            cost=d.get("cost", 0.0),
            error=d.get("error"),
            attempts=d.get("attempts", 0),
        )


@dataclass
class ShotState:
    image: StepState = field(default_factory=StepState)
    audio: StepState = field(default_factory=StepState)
    video: StepState = field(default_factory=StepState)
    lipsync: StepState = field(default_factory=StepState)

    def step(self, name: str) -> StepState:
        return getattr(self, name)

    def to_dict(self) -> dict:
        return {name: self.step(name).to_dict() for name in STEP_NAMES}

    @classmethod
    def from_dict(cls, d: dict) -> "ShotState":
        return cls(**{name: StepState.from_dict(d.get(name, {})) for name in STEP_NAMES})

    @property
    def total_cost(self) -> float:
        return sum(self.step(n).cost for n in STEP_NAMES)


@dataclass
class PipelineState:
    project: str
    output_dir: str
    shots: dict[str, ShotState] = field(default_factory=dict)
    assembly_status: str = STATUS_PENDING
    assembly_path: Optional[str] = None
    started_at: str = ""
    updated_at: str = ""

    @property
    def state_path(self) -> str:
        return os.path.join(self.output_dir, "state.json")

    @property
    def total_cost(self) -> float:
        return sum(s.total_cost for s in self.shots.values())

    def shot(self, name: str) -> ShotState:
        if name not in self.shots:
            self.shots[name] = ShotState()
        return self.shots[name]

    def is_step_done(self, shot_name: str, step_name: str) -> bool:
        """Check if a step is completed and its output file exists."""
        ss = self.shot(shot_name).step(step_name)
        if ss.status != STATUS_COMPLETED:
            return False
        if ss.path and not os.path.exists(ss.path):
            return False
        return True

    def save(self) -> None:
        with _save_lock:
            self.updated_at = _now()
            Path(self.output_dir).mkdir(parents=True, exist_ok=True)
            data = {
                "project": self.project,
                "started_at": self.started_at,
                "updated_at": self.updated_at,
                "total_cost": round(self.total_cost, 4),
                "assembly": {
                    "status": self.assembly_status,
                    "path": self.assembly_path,
                },
                "shots": {name: ss.to_dict() for name, ss in self.shots.items()},
            }
            tmp = self.state_path + f".{threading.get_ident()}.tmp"
            with open(tmp, "w") as f:
                json.dump(data, f, indent=2)
            os.replace(tmp, self.state_path)

    @classmethod
    def load(cls, output_dir: str, project: str) -> "PipelineState":
        """Load existing state or create fresh."""
        path = os.path.join(output_dir, "state.json")
        if os.path.exists(path):
            with open(path) as f:
                data = json.load(f)
            state = cls(
                project=data.get("project", project),
                output_dir=output_dir,
                started_at=data.get("started_at", _now()),
                updated_at=data.get("updated_at", ""),
            )
            assembly = data.get("assembly", {})
            state.assembly_status = assembly.get("status", STATUS_PENDING)
            state.assembly_path = assembly.get("path")
            for name, sd in data.get("shots", {}).items():
                state.shots[name] = ShotState.from_dict(sd)
            return state

        return cls(
            project=project,
            output_dir=output_dir,
            started_at=_now(),
        )

    def print_cost_report(self) -> None:
        """Print per-shot cost breakdown."""
        print(f"\n{'='*50}")
        print(f"COST REPORT: {self.project}")
        print(f"{'='*50}")
        for name, ss in self.shots.items():
            cost = ss.total_cost
            if cost > 0:
                parts = []
                for step in STEP_NAMES:
                    sc = ss.step(step).cost
                    if sc > 0:
                        parts.append(f"{step}=${sc:.2f}")
                print(f"  {name}: ${cost:.2f} ({', '.join(parts)})")
        print(f"\n  TOTAL: ${self.total_cost:.2f}")
        print()


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
