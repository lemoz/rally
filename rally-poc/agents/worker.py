#!/usr/bin/env python3
"""Visible worker process for one Rally production role.

The worker always writes a prompt, handoff template, and status file. If
RALLY_AGENT_COMMAND_TEMPLATE is set, it delegates to that command. Otherwise it
stays alive as a readable tmux pane so the operator can inspect the contract.
"""
from __future__ import annotations

import argparse
import json
import shlex
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

from .studio import (
    build_prompt_text,
    command_template_for_role,
    generation_preflight_blockers,
    missing_upstream_artifacts,
    prompt_metadata,
    record_blocker,
    write_json,
)
from .roles import get_role


def main() -> None:
    parser = argparse.ArgumentParser(description="Run one visible Rally agent role")
    parser.add_argument("--run-dir", required=True, help="Run directory")
    parser.add_argument("--role", required=True, help="Role name")
    parser.add_argument("--once", action="store_true", help="Write artifacts and exit")
    args = parser.parse_args()

    run_dir = Path(args.run_dir).resolve()
    role = get_role(args.role)
    run = _load_run(run_dir)

    _ensure_dirs(run_dir)
    prompt_path = _write_prompt(run_dir, run, role)
    handoff_path = _ensure_handoff(run_dir, run, role)
    _write_status(run_dir, role.role, "ready", {
        "prompt": str(prompt_path),
        "handoff": str(handoff_path),
        "primary_output": role.primary_output,
    })

    command_template = command_template_for_role(role.role)
    _print_header(run_dir, run, role, prompt_path, handoff_path, bool(command_template))

    blockers: list[str] = []
    if command_template:
        blockers.extend(missing_upstream_artifacts(run_dir, role))
    if role.role == "generation":
        blockers.extend(generation_preflight_blockers(run_dir, run))
    if blockers:
        blocker_path = record_blocker(run_dir, run, role, blockers)
        _write_status(run_dir, role.role, "blocked", {
            "prompt": str(prompt_path),
            "handoff": str(handoff_path),
            "blocker": str(blocker_path),
            "blockers": blockers,
        })
        if args.once:
            return
        _watch_loop(run_dir, role.role, handoff_path, blockers=blockers)
        return

    if command_template:
        _write_status(run_dir, role.role, "running_command", {"template": command_template})
        code = _run_command_template(command_template, run_dir, run, role.role, prompt_path)
        _write_status(run_dir, role.role, "command_completed" if code == 0 else "command_failed", {"exit_code": code})
        raise SystemExit(code)

    complete = _primary_output_exists(run_dir, role.primary_output)
    if complete:
        _write_status(run_dir, role.role, "complete", {
            "prompt": str(prompt_path),
            "handoff": str(handoff_path),
            "primary_output": role.primary_output,
        })

    if args.once:
        return

    _watch_loop(run_dir, role.role, handoff_path, complete=complete)


def _load_run(run_dir: Path) -> dict:
    run_path = run_dir / "run.json"
    if not run_path.exists():
        raise FileNotFoundError(f"Missing run.json: {run_path}")
    return json.loads(run_path.read_text(encoding="utf-8"))


def _ensure_dirs(run_dir: Path) -> None:
    for name in (
        "artifacts",
        "gates",
        "handoffs",
        "logs",
        "prompts",
        "status",
        "assets",
        "final",
        "blockers",
        "memory",
    ):
        (run_dir / name).mkdir(parents=True, exist_ok=True)


def _write_prompt(run_dir: Path, run: dict, role) -> Path:
    prompt_path = run_dir / "prompts" / f"{role.pane_name}.md"
    template = command_template_for_role(role.role)
    prompt_path.write_text(build_prompt_text(run, role), encoding="utf-8")
    write_json(
        run_dir / "prompts" / f"{role.pane_name}.json",
        prompt_metadata(run, role, prompt_path, template),
    )
    return prompt_path


def _ensure_handoff(run_dir: Path, run: dict, role) -> Path:
    handoff_path = run_dir / "handoffs" / f"{role.pane_name}.md"
    if handoff_path.exists():
        return handoff_path

    outputs = "\n".join(f"- [ ] `{item}`" for item in role.outputs)
    checks = "\n".join(f"- [ ] {item}" for item in role.checks)
    handoff_path.write_text(f"""# {role.title} Handoff

Run: `{run["run_id"]}`
Project: `{run["project"]}`
Style: `{run["style_id"]}`

## Status

- [ ] Not started
- [ ] In progress
- [ ] Blocked
- [ ] Complete

## Outputs

{outputs}

## Checks

{checks}

## Notes

- 

## Blockers

- 

## Next Action

- 
""", encoding="utf-8")
    return handoff_path


def _write_status(run_dir: Path, role: str, status: str, extra: dict | None = None) -> None:
    payload = {
        "role": role,
        "status": status,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    if extra:
        payload.update(extra)
    (run_dir / "status" / f"{role}.json").write_text(
        json.dumps(payload, indent=2),
        encoding="utf-8",
    )


def _primary_output_exists(run_dir: Path, primary_output: str) -> bool:
    path = run_dir / primary_output
    return path.exists()


def _print_header(
    run_dir: Path,
    run: dict,
    role,
    prompt_path: Path,
    handoff_path: Path,
    has_command_template: bool,
) -> None:
    print("=" * 78, flush=True)
    print(f"RALLY AGENT: {role.title} ({role.role})", flush=True)
    print("=" * 78, flush=True)
    print(f"Run dir:        {run_dir}", flush=True)
    print(f"Run id:         {run['run_id']}", flush=True)
    print(f"Project:        {run['project']}", flush=True)
    print(f"Style:          {run['style_id']}", flush=True)
    print(f"Primary output: {role.primary_output}", flush=True)
    print(f"Prompt:         {prompt_path}", flush=True)
    print(f"Handoff:        {handoff_path}", flush=True)
    print("", flush=True)
    print(role.mission, flush=True)
    print("", flush=True)
    if has_command_template:
        print("RALLY_AGENT_COMMAND_TEMPLATE is set; delegating to the configured model runner.", flush=True)
    else:
        print("No RALLY_AGENT_COMMAND_TEMPLATE is set, so this pane is in scaffold mode.", flush=True)
        print("Set that env var to plug in a real model runner.", flush=True)
    print("", flush=True)


def _run_command_template(template: str, run_dir: Path, run: dict, role: str, prompt_path: Path) -> int:
    rendered = template.format(
        prompt_file=str(prompt_path),
        run_dir=str(run_dir),
        role=role,
        project=run["project"],
        style_id=run["style_id"],
    )
    print(f"Running: {rendered}", flush=True)
    return subprocess.run(shlex.split(rendered), cwd=run_dir.parent.parent).returncode


def _watch_loop(
    run_dir: Path,
    role: str,
    handoff_path: Path,
    *,
    blockers: list[str] | None = None,
    complete: bool = False,
) -> None:
    tick = 0
    while True:
        tick += 1
        status = "blocked" if blockers else "complete" if complete else "waiting"
        payload = {
            "handoff": str(handoff_path),
            "tick": tick,
        }
        if blockers:
            payload["blockers"] = blockers
        if complete:
            payload["complete"] = True
        _write_status(run_dir, role, status, payload)
        if blockers:
            joined = "; ".join(blockers)
            print(f"[{datetime.now().strftime('%H:%M:%S')}] blocked: {joined}", flush=True)
            print(f"  handoff: {handoff_path}", flush=True)
        elif complete:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] complete; handoff {handoff_path}", flush=True)
        else:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] waiting; edit/read {handoff_path}", flush=True)
        time.sleep(30)


if __name__ == "__main__":
    main()
