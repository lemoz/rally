"""Drive a full agentic-studio run sequentially without tmux.

`agents.launch_tmux` is the right tool for visible operator workflows. For
verification + scripted runs, this script initializes a run dir and runs
each role through `agents.worker --once`, gating on user-approved gates
between phases. Output streams to stdout so we can see the model's actions
without attaching to tmux panes.

Usage:
    cd rally-poc
    python3 -m agents.run_sequential \\
        --project rally_multiplayer_ai \\
        --style psyop_anime_90s \\
        --run-id rally_014_agentic_v1 \\
        --topic "Stop being alone with AI: 30s anime montage..." \\
        [--auto-approve concept,storyboard,keyframes,final_edit]
"""
from __future__ import annotations

import argparse
import json
import os
import shlex
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from agents.launch_tmux import _init_run_dir, _safe_run_id, _safe_session_name  # noqa: E402
from agents.roles import ROLE_SPECS  # noqa: E402

RUNS_DIR = ROOT / "runs"

# Gates that block progression and require user approval before later roles run.
GATE_AFTER_ROLE = {
    "creative_director": "concept",
    "storyboard": "storyboard",
    "art_director": "keyframes",
    "editor": "final_edit",
}


def main() -> None:
    parser = argparse.ArgumentParser(description="Sequential agentic-studio run")
    parser.add_argument("--project", required=True)
    parser.add_argument("--style", required=True, help="Style card id")
    parser.add_argument("--run-id", help="Stable run id; defaults to project_style_timestamp")
    parser.add_argument("--topic", help="Operator brief content; written into artifacts/operator_brief.md")
    parser.add_argument("--goal", default="Produce one high-quality short-form video candidate.")
    parser.add_argument(
        "--auto-approve",
        default="",
        help="Comma-separated gates to auto-approve (concept, storyboard, keyframes, final_edit).",
    )
    parser.add_argument("--start-at", help="Skip to this role (e.g. 'storyboard' to resume).")
    parser.add_argument("--stop-at", help="Stop after this role.")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    # Set runner command template if not already set.
    if not os.environ.get("RALLY_AGENT_COMMAND_TEMPLATE"):
        os.environ["RALLY_AGENT_COMMAND_TEMPLATE"] = (
            "python3 -m agents.runner --prompt-file {prompt_file} --run-dir {run_dir} --role {role}"
        )

    run_id = _safe_run_id(args.run_id or _default_run_id(args.project, args.style))
    run_dir = RUNS_DIR / run_id
    session_name = _safe_session_name(f"rally-{run_id}")

    print(f"[run] init run_dir={run_dir}")
    _init_run_dir(run_dir, run_id, args.project, args.style, args.goal, session_name)

    # Operator brief
    brief_path = run_dir / "artifacts" / "operator_brief.md"
    if args.topic and not brief_path.exists():
        brief_path.write_text(
            f"# Operator brief — {args.project}\n\n"
            f"Style: {args.style}\nRun: {run_id}\n\n"
            f"## Topic\n\n{args.topic}\n",
            encoding="utf-8",
        )
        print(f"[run] wrote operator_brief.md")

    auto_approve = {g.strip() for g in args.auto_approve.split(",") if g.strip()}

    started = args.start_at is None
    for role in ROLE_SPECS:
        if not started:
            if role.role == args.start_at:
                started = True
            else:
                continue

        print(f"\n[run] === role={role.role} ({role.title}) ===")
        if args.dry_run:
            print("  (dry-run)")
        else:
            cmd = ["python3", "-m", "agents.worker", "--once", "--run-dir", str(run_dir), "--role", role.role]
            print(f"  $ {' '.join(shlex.quote(c) for c in cmd)}")
            result = subprocess.run(cmd, cwd=str(ROOT), env=os.environ.copy())
            if result.returncode != 0:
                print(f"[run] role {role.role} exited {result.returncode}; stopping.")
                sys.exit(result.returncode)

        gate = GATE_AFTER_ROLE.get(role.role)
        if gate:
            decided = _resolve_gate(run_dir, gate, auto_approve, dry_run=args.dry_run)
            if decided != "approved":
                print(f"[run] gate '{gate}' status={decided}; stopping.")
                sys.exit(2)

        if args.stop_at and role.role == args.stop_at:
            print(f"[run] stop-at reached: {role.role}")
            break

    print("\n[run] sequence complete.")


def _resolve_gate(run_dir: Path, gate: str, auto_approve: set[str], *, dry_run: bool) -> str:
    """Return the new status of the gate after handling auto-approval / prompt."""
    if dry_run:
        return "approved"
    if gate in auto_approve:
        cmd = [
            "python3", "-m", "agents.cli", "approve-gate",
            "--run-dir", str(run_dir),
            "--gate", gate,
            "--decision", "approve",
            "--actor", "auto",
            "--notes", "auto-approved by run_sequential",
        ]
        subprocess.run(cmd, cwd=str(ROOT), check=True)
        print(f"[run] gate '{gate}' auto-approved")
        return "approved"

    print(f"\n[run] gate '{gate}' awaits human approval.")
    print(f"[run] inspect run_dir={run_dir}")
    print(f"[run] approve via:  python3 -m agents.cli approve-gate --run-dir {run_dir} --gate {gate} --decision approve --actor $USER")
    try:
        answer = input(f"[run] approve gate '{gate}' now? (yes/no/blocked): ").strip().lower()
    except EOFError:
        answer = "no"
    if answer in ("y", "yes"):
        cmd = [
            "python3", "-m", "agents.cli", "approve-gate",
            "--run-dir", str(run_dir),
            "--gate", gate,
            "--decision", "approve",
            "--actor", os.environ.get("USER", "operator"),
        ]
        subprocess.run(cmd, cwd=str(ROOT), check=True)
        return "approved"
    if answer == "blocked":
        return "blocked"
    return "rejected"


def _default_run_id(project: str, style: str) -> str:
    return f"{project}_{style}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"


if __name__ == "__main__":
    main()
