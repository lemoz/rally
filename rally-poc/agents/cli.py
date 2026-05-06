#!/usr/bin/env python3
"""Minimal operator CLI for Rally agentic studio runs."""
from __future__ import annotations

import argparse
import os
from pathlib import Path

from .studio import (
    ALL_GATES,
    USER_APPROVAL_GATES,
    append_retry_request,
    ensure_run_defaults,
    load_json,
    set_gate_decision,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Operate a Rally agentic studio run")
    sub = parser.add_subparsers(dest="command", required=True)

    status = sub.add_parser("status", help="Summarize roles, gates, blockers, budget, and artifacts")
    status.add_argument("--run-dir", required=True)
    status.set_defaults(func=_status)

    approve = sub.add_parser("approve-gate", help="Approve, reject, or block a gate")
    approve.add_argument("--run-dir", required=True)
    approve.add_argument("--gate", required=True, choices=ALL_GATES)
    approve.add_argument("--decision", required=True, choices=("approve", "reject", "block"))
    approve.add_argument("--actor", default=os.environ.get("USER", "operator"))
    approve.add_argument("--notes", default="")
    approve.add_argument("--artifact", action="append", default=[], help="Artifact path or ref")
    approve.set_defaults(func=_approve_gate)

    retry = sub.add_parser("retry-shot", help="Record a critic retry request without spending money")
    retry.add_argument("--run-dir", required=True)
    retry.add_argument("--shot", required=True)
    retry.add_argument("--reason", required=True)
    retry.add_argument("--suggested-fix", required=True)
    retry.add_argument("--requested-by", default="critic")
    retry.set_defaults(func=_retry_shot)

    args = parser.parse_args()
    args.func(args)


def _status(args: argparse.Namespace) -> None:
    run_dir = Path(args.run_dir).resolve()
    run = ensure_run_defaults(load_json(run_dir / "run.json", default={}))
    budgets = run["budgets"]

    print(f"Run: {run.get('run_id', run_dir.name)}")
    print(f"Project: {run.get('project', 'unknown')}  Style: {run.get('style_id', 'unknown')}")
    print(f"Mode: {run['studio_policy']['operating_mode']}")
    print(
        "Budget: "
        f"${float(budgets.get('spent_usd', 0.0)):.2f}/"
        f"${float(budgets.get('candidate_budget_usd', 0.0)):.2f} candidate, "
        f"${float(budgets.get('style_exploration_budget_usd', 0.0)):.2f} style cap"
    )

    print("\nGates:")
    for gate in ALL_GATES:
        payload = load_json(run_dir / "gates" / f"{gate}.json", default={})
        status = payload.get("status", "missing")
        required = "user" if payload.get("user_approval_required", gate in USER_APPROVAL_GATES) else "auto"
        print(f"- {gate}: {status} ({required})")

    print("\nRoles:")
    for path in sorted((run_dir / "status").glob("*.json")):
        payload = load_json(path, default={})
        role = payload.get("role", path.stem)
        status = payload.get("status", "unknown")
        tick = payload.get("tick")
        suffix = f" tick={tick}" if tick is not None else ""
        print(f"- {role}: {status}{suffix}")

    blocker_paths = sorted((run_dir / "blockers").glob("*.json"))
    if blocker_paths:
        print("\nBlockers:")
        for path in blocker_paths:
            payload = load_json(path, default={})
            blockers = "; ".join(payload.get("blockers", []))
            print(f"- {payload.get('role', path.stem)}: {blockers}")

    artifacts = sorted(p for p in (run_dir / "artifacts").glob("*") if p.is_file())
    if artifacts:
        print("\nArtifacts:")
        for path in artifacts[:20]:
            print(f"- {path.relative_to(run_dir)}")
        if len(artifacts) > 20:
            print(f"- ... {len(artifacts) - 20} more")


def _approve_gate(args: argparse.Namespace) -> None:
    run_dir = Path(args.run_dir).resolve()
    payload = set_gate_decision(
        run_dir,
        args.gate,
        decision=args.decision,
        actor=args.actor,
        notes=args.notes,
        artifact_refs=args.artifact,
    )
    print(f"{args.gate}: {payload['status']} by {args.actor}")


def _retry_shot(args: argparse.Namespace) -> None:
    run_dir = Path(args.run_dir).resolve()
    request = append_retry_request(
        run_dir,
        shot=args.shot,
        reason=args.reason,
        suggested_fix=args.suggested_fix,
        requested_by=args.requested_by,
    )
    print(f"retry requested for {request['shot']}: {request['reason']}")


if __name__ == "__main__":
    main()
