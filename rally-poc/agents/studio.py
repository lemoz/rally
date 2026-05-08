"""Shared contracts for the Rally tmux-visible agent studio."""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping


AGENTS_DIR = Path(__file__).resolve().parent
POC_ROOT = AGENTS_DIR.parent
REPO_ROOT = POC_ROOT.parent
TOOL_MANIFEST_PATH = AGENTS_DIR / "tool_manifest.json"
SKILLS_DIR = AGENTS_DIR / "skills"

ALL_GATES = (
    "source_pack",
    "style_brief",
    "concept",
    "storyboard",
    "keyframes",
    "clips",
    "final_edit",
)
USER_APPROVAL_GATES = ("concept", "storyboard", "keyframes", "final_edit")

DEFAULT_RETRY_LIMITS = {
    "image": 3,
    "video": 2,
    "audio": 2,
    "lip_sync": 1,
}

DEFAULT_BUDGETS = {
    "candidate_budget_usd": 20.0,
    "style_exploration_budget_usd": 100.0,
    "spent_usd": 0.0,
    "budget_upgrade": "explicit_only",
    "over_budget_behavior": "pause_for_approval",
}

DEFAULT_STUDIO_POLICY = {
    "operating_mode": "visible_studio",
    "future_autonomy": {
        "enabled": False,
        "requires_review_memory": True,
        "note": "Autonomy can be enabled later after enough approved/rejected examples exist.",
    },
    "approval_required_gates": list(USER_APPROVAL_GATES),
    "producer_gate_authority": "recommend_only",
    "parallelism": "parallel_with_gates",
    "blocked_agent_behavior": "blocker_handoff_and_heartbeat",
}

DEFAULT_MODEL_POLICY = {
    "model_tier": "one_strong_model",
    "runner_policy": "role_specific_command_templates",
    "role_template_env_prefix": "RALLY_AGENT_COMMAND_TEMPLATE_",
    "legacy_role_template_env_pattern": "RALLY_{ROLE}_AGENT_COMMAND_TEMPLATE",
    "global_fallback_env": "RALLY_AGENT_COMMAND_TEMPLATE",
    "browsing_roles": ["research", "trend_style"],
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_json(path: Path, default: Any | None = None) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def build_run_payload(
    *,
    run_id: str,
    project: str,
    style_id: str,
    goal: str,
    session: str,
    repo_root: Path,
    poc_root: Path,
    roles: list[str],
) -> dict[str, Any]:
    payload = {
        "run_id": run_id,
        "project": project,
        "style_id": style_id,
        "goal": goal,
        "tmux_session": session,
        "created_at": utc_now(),
        "repo_root": str(repo_root),
        "poc_root": str(poc_root),
        "roles": roles,
    }
    return ensure_run_defaults(payload)


def ensure_run_defaults(run: dict[str, Any]) -> dict[str, Any]:
    run.setdefault("studio_policy", json.loads(json.dumps(DEFAULT_STUDIO_POLICY)))
    run.setdefault("model_policy", json.loads(json.dumps(DEFAULT_MODEL_POLICY)))
    run.setdefault("budgets", json.loads(json.dumps(DEFAULT_BUDGETS)))
    run.setdefault("retry_limits", dict(DEFAULT_RETRY_LIMITS))
    return run


def gate_template(gate: str) -> dict[str, Any]:
    if gate not in ALL_GATES:
        raise ValueError(f"Unknown gate: {gate}")
    user_required = gate in USER_APPROVAL_GATES
    return {
        "gate": gate,
        "status": "pending",
        "approved_by": None,
        "updated_at": None,
        "notes": "",
        "user_approval_required": user_required,
        "user_approval": {
            "status": "pending" if user_required else "not_required",
            "actor": None,
            "updated_at": None,
            "notes": "",
        },
        "producer_recommendation": {
            "status": None,
            "actor": "producer",
            "updated_at": None,
            "notes": "",
        },
        "artifact_refs": [],
        "blockers": [],
        "review_memory_refs": [],
    }


def load_tool_manifest(path: Path | None = None) -> dict[str, Any]:
    manifest_path = path or TOOL_MANIFEST_PATH
    manifest = load_json(manifest_path)
    if not isinstance(manifest, dict):
        raise ValueError(f"Tool manifest must be an object: {manifest_path}")
    if "roles" not in manifest or not isinstance(manifest["roles"], dict):
        raise ValueError(f"Tool manifest missing roles object: {manifest_path}")
    return manifest


def role_tool_policy(role: str, manifest: dict[str, Any] | None = None) -> dict[str, Any]:
    manifest = manifest or load_tool_manifest()
    defaults = manifest.get("defaults", {})
    roles = manifest.get("roles", {})
    if role not in roles:
        known = ", ".join(sorted(roles))
        raise ValueError(f"Missing tool policy for role {role!r}. Known roles: {known}")
    policy = dict(defaults)
    policy.update(roles[role])
    return policy


def load_role_skill(role: str, skills_dir: Path | None = None) -> str:
    path = (skills_dir or SKILLS_DIR) / f"{role}.md"
    if not path.exists():
        return "No local skill file found for this role yet."
    return path.read_text(encoding="utf-8").strip()


def load_style_card(style_id: str, poc_root: Path | None = None) -> dict[str, Any]:
    path = (poc_root or POC_ROOT) / "style_cards" / f"{style_id}.json"
    if not path.exists():
        return {}
    return load_json(path, default={})


def command_template_for_role(role: str, env: Mapping[str, str] | None = None) -> str:
    env = env or os.environ
    upper = role.upper()
    candidates = (
        f"RALLY_AGENT_COMMAND_TEMPLATE_{upper}",
        f"RALLY_{upper}_AGENT_COMMAND_TEMPLATE",
        "RALLY_AGENT_COMMAND_TEMPLATE",
    )
    for key in candidates:
        value = env.get(key, "").strip()
        if value:
            return value
    return ""


def budget_allows_generation(run: dict[str, Any], *, projected_cost: float = 0.0) -> bool:
    ensure_run_defaults(run)
    budgets = run["budgets"]
    spent = float(budgets.get("spent_usd", 0.0))
    cap = float(budgets.get("candidate_budget_usd", DEFAULT_BUDGETS["candidate_budget_usd"]))
    return spent + projected_cost <= cap


def generation_preflight_blockers(run_dir: Path, run: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    keyframes = load_json(run_dir / "gates" / "keyframes.json", default={})
    if keyframes.get("status") != "approved":
        blockers.append("keyframes gate is not approved; paid generation is blocked")
    if not budget_allows_generation(run):
        budgets = ensure_run_defaults(run)["budgets"]
        blockers.append(
            "candidate budget is exhausted "
            f"(${float(budgets.get('spent_usd', 0.0)):.2f}/"
            f"${float(budgets.get('candidate_budget_usd', 0.0)):.2f})"
        )
    blockers.extend(keyframes_preflight_blockers(run_dir))
    return blockers


def concept_preflight_blockers(run_dir: Path) -> list[str]:
    """Producer's gate check before approving the `concept` gate.

    The concept artifact must contain a master_script — the pipeline's
    audio-drives-timing contract requires VO text per beat to be derived
    from a single source-of-truth script.
    """
    blockers: list[str] = []
    concept_path = run_dir / "artifacts" / "selected_concept.md"
    if not concept_path.exists():
        blockers.append("selected_concept.md not written; creative_director hasn't run")
        return blockers
    body = concept_path.read_text(encoding="utf-8").lower()
    if "master_script" not in body and "## script" not in body and "## master script" not in body:
        blockers.append(
            "selected_concept.md is missing a master_script section "
            "(audio-drives-timing requires script as source of truth)"
        )
    return blockers


def storyboard_preflight_blockers(run_dir: Path) -> list[str]:
    """Storyboard gate check.

    Every shot in storyboard.json must have a `vo_text` entry, and the timing
    module must be able to measure VO durations once they're generated. We do
    a structural check here; the actual VO measurement happens after the
    Generation role runs the deterministic pipeline.
    """
    blockers: list[str] = []
    storyboard_path = run_dir / "artifacts" / "storyboard.json"
    if not storyboard_path.exists():
        blockers.append("storyboard.json not written; storyboard role hasn't run")
        return blockers
    try:
        data = json.loads(storyboard_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        blockers.append(f"storyboard.json is not valid JSON: {exc}")
        return blockers

    shots = data.get("shots") or data.get("panels") or []
    if not shots:
        blockers.append("storyboard.json has no shots/panels array")
        return blockers
    missing_vo = [s.get("name", "?") for s in shots if not s.get("vo_text")]
    if missing_vo:
        blockers.append(
            f"shots without vo_text: {missing_vo[:3]}"
            f"{' (and more)' if len(missing_vo) > 3 else ''}"
        )
    return blockers


def keyframes_preflight_blockers(run_dir: Path) -> list[str]:
    """Keyframes gate check.

    Every shot in storyboard.json must have a corresponding entry in
    keyframe_specs.json so the Generation role doesn't get to a shot
    with no prompt pack.
    """
    blockers: list[str] = []
    storyboard_path = run_dir / "artifacts" / "storyboard.json"
    keyframes_path = run_dir / "artifacts" / "keyframe_specs.json"
    if not keyframes_path.exists():
        # Not yet written; this is fine before art_director runs.
        return blockers
    if not storyboard_path.exists():
        blockers.append("keyframe_specs.json exists without storyboard.json")
        return blockers
    try:
        sb = json.loads(storyboard_path.read_text(encoding="utf-8"))
        kf = json.loads(keyframes_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        blockers.append(f"keyframe gate JSON parse error: {exc}")
        return blockers

    sb_names = {s.get("name") for s in (sb.get("shots") or sb.get("panels") or []) if s.get("name")}
    kf_specs = kf.get("specs") or kf.get("keyframes") or kf.get("shots") or []
    kf_names = {s.get("name") for s in kf_specs if s.get("name")}
    missing = sb_names - kf_names
    if missing:
        blockers.append(
            f"keyframe_specs.json is missing entries for: {sorted(missing)[:3]}"
            f"{' (and more)' if len(missing) > 3 else ''}"
        )
    return blockers


def missing_upstream_artifacts(run_dir: Path, role) -> list[str]:
    missing: list[str] = []
    for item in role.inputs:
        if not item.startswith("artifacts/"):
            continue
        path = run_dir / item
        if not path.exists():
            missing.append(f"required upstream artifact is missing: {item}")
    return missing


def record_blocker(run_dir: Path, run: dict[str, Any], role, blockers: list[str]) -> Path:
    payload = {
        "run_id": run.get("run_id"),
        "role": role.role,
        "status": "blocked",
        "blockers": blockers,
        "updated_at": utc_now(),
    }
    json_path = run_dir / "blockers" / f"{role.role}.json"
    write_json(json_path, payload)

    md_path = run_dir / "handoffs" / f"{role.pane_name}_blocker.md"
    md_path.write_text(
        "\n".join([
            f"# {role.title} Blocker",
            "",
            f"Run: `{run.get('run_id')}`",
            f"Role: `{role.role}`",
            "",
            "## Blockers",
            *[f"- {blocker}" for blocker in blockers],
            "",
            "## Next Action",
            "- Resolve the blocker or approve the required upstream gate, then restart this role command.",
            "",
        ]),
        encoding="utf-8",
    )
    return json_path


def set_gate_decision(
    run_dir: Path,
    gate: str,
    *,
    decision: str,
    actor: str,
    notes: str = "",
    artifact_refs: list[str] | None = None,
) -> dict[str, Any]:
    if decision not in {"approve", "reject", "block"}:
        raise ValueError("decision must be approve, reject, or block")
    gate_path = run_dir / "gates" / f"{gate}.json"
    payload = load_json(gate_path, default=gate_template(gate))
    status = {"approve": "approved", "reject": "rejected", "block": "blocked"}[decision]
    now = utc_now()
    payload["status"] = status
    payload["updated_at"] = now
    payload["notes"] = notes
    payload["artifact_refs"] = artifact_refs or payload.get("artifact_refs", [])
    if decision == "approve":
        payload["approved_by"] = actor
    payload.setdefault("user_approval", {})
    payload["user_approval"].update({
        "status": status,
        "actor": actor,
        "updated_at": now,
        "notes": notes,
    })
    event_id = append_review_event(
        run_dir,
        run_id=load_json(run_dir / "run.json", default={}).get("run_id"),
        gate=gate,
        decision=decision,
        actor=actor,
        notes=notes,
        artifact_refs=artifact_refs or [],
    )
    payload.setdefault("review_memory_refs", []).append(event_id)
    write_json(gate_path, payload)
    return payload


def append_review_event(
    run_dir: Path,
    *,
    run_id: str | None,
    gate: str,
    decision: str,
    actor: str,
    notes: str,
    artifact_refs: list[str],
) -> str:
    event_id = f"{gate}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}"
    event = {
        "event_id": event_id,
        "run_id": run_id,
        "gate": gate,
        "decision": decision,
        "actor": actor,
        "notes": notes,
        "artifact_refs": artifact_refs,
        "created_at": utc_now(),
    }
    path = run_dir / "memory" / "review_events.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event) + "\n")
    return event_id


def append_retry_request(
    run_dir: Path,
    *,
    shot: str,
    reason: str,
    suggested_fix: str,
    requested_by: str,
) -> dict[str, Any]:
    request = {
        "shot": shot,
        "reason": reason,
        "suggested_fix": suggested_fix,
        "requested_by": requested_by,
        "status": "requested",
        "created_at": utc_now(),
    }
    path = run_dir / "artifacts" / "retry_requests.json"
    payload = load_json(path, default={"requests": []})
    if isinstance(payload, list):
        payload = {"requests": payload}
    payload.setdefault("requests", []).append(request)
    write_json(path, payload)

    memory = run_dir / "memory" / "retry_requests.jsonl"
    memory.parent.mkdir(parents=True, exist_ok=True)
    with memory.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(request) + "\n")
    return request


def build_prompt_text(run: dict[str, Any], role, *, poc_root: Path | None = None) -> str:
    ensure_run_defaults(run)
    manifest = load_tool_manifest()
    policy = role_tool_policy(role.role, manifest)
    skill = load_role_skill(role.role)
    style_card = load_style_card(run.get("style_id", ""), poc_root=poc_root)

    inputs = "\n".join(f"- {item}" for item in role.inputs)
    outputs = "\n".join(f"- {item}" for item in role.outputs)
    checks = "\n".join(f"- {item}" for item in role.checks)
    allowed = "\n".join(f"- {item}" for item in policy.get("allowed_tools", [])) or "- None"
    forbidden = "\n".join(f"- {item}" for item in policy.get("forbidden_tools", [])) or "- None"
    gates = ", ".join(run["studio_policy"]["approval_required_gates"])
    retry_limits = ", ".join(f"{key}={value}" for key, value in run["retry_limits"].items())
    budgets = run["budgets"]
    style_rubric = _style_rubric_text(style_card)

    return f"""# Rally Agent Role: {role.title}

## Run

- Run id: `{run["run_id"]}`
- Project: `{run["project"]}`
- Style id: `{run["style_id"]}`
- Goal: {run["goal"]}
- Operator brief: `artifacts/operator_brief.md`
- Operating mode: `{run["studio_policy"]["operating_mode"]}`
- Producer authority: `{run["studio_policy"]["producer_gate_authority"]}`

## Mission

{role.mission}

## Inputs

{inputs}

## Required Outputs

{outputs}

Primary output: `{role.primary_output}`

## Tool Access

Allowed tools:
{allowed}

Forbidden tools:
{forbidden}

- Can spend money: `{bool(policy.get("can_spend_money"))}`
- Can browse web: `{bool(policy.get("can_browse_web"))}`
- Can capture sources: `{bool(policy.get("can_capture_sources"))}`

## Budget And Retry Rules

- Candidate budget: `${float(budgets["candidate_budget_usd"]):.2f}`
- Style exploration budget: `${float(budgets["style_exploration_budget_usd"]):.2f}`
- Over-budget behavior: `{budgets["over_budget_behavior"]}`
- Budget upgrade: `{budgets["budget_upgrade"]}`
- Retry limits: {retry_limits}

## Gate Rules

- User approval required for: {gates}
- The producer can recommend gate decisions but cannot approve user-gated work.
- "Technically okay but boring" is a hard rejection for concept, storyboard, keyframes, and final edit.
- Unsupported factual/source claims are hard failures.
- Proof-bearing claims must be source-backed or deterministic.

## Quality Checks

{checks}

## Artifact Schema

- Human-readable output: write the required Markdown artifact when applicable.
- Machine-readable output: for gate-critical outputs, write the paired JSON artifact with status, artifact refs, reject reasons, and next action.
- Handoff: update your handoff with status, blockers, decisions made, and next action.

## Role Skill

{skill}

## Style Card Rubric

{style_rubric}

## Upstream Context

{_upstream_text(role.order)}

## Instructions

Read `artifacts/operator_brief.md` first, then read upstream artifacts before
writing. If a required upstream artifact is missing, write a blocker in your
handoff instead of inventing it. Keep all claims source-backed. Keep handoff
notes short, specific, and actionable.
"""


def prompt_metadata(run: dict[str, Any], role, prompt_path: Path, template: str) -> dict[str, Any]:
    ensure_run_defaults(run)
    return {
        "prompt_version": 1,
        "run_id": run["run_id"],
        "role": role.role,
        "title": role.title,
        "style_id": run["style_id"],
        "model_policy": run["model_policy"],
        "command_template_env": [
            f"RALLY_AGENT_COMMAND_TEMPLATE_{role.role.upper()}",
            f"RALLY_{role.role.upper()}_AGENT_COMMAND_TEMPLATE",
            "RALLY_AGENT_COMMAND_TEMPLATE",
        ],
        "resolved_command_template": template,
        "inputs": list(role.inputs),
        "outputs": list(role.outputs),
        "prompt_path": str(prompt_path),
        "created_at": utc_now(),
    }


def _style_rubric_text(style_card: dict[str, Any]) -> str:
    if not style_card:
        return "No style card found. Treat this as a blocker for style-dependent work."
    qa = style_card.get("qa", {})
    generation = style_card.get("generation_rules", {})
    routing = style_card.get("routing", {})
    lines = [
        f"- Style: `{style_card.get('style_id', 'unknown')}`",
        f"- Display name: {style_card.get('display_name', 'unknown')}",
        f"- Generation rules: {json.dumps(generation, sort_keys=True)}",
        f"- Default routes: {json.dumps(routing.get('default_routes', {}), sort_keys=True)}",
        f"- Pass checks: {', '.join(qa.get('pass_checks', [])) or 'unspecified'}",
        f"- Reject reasons: {', '.join(qa.get('reject_reasons', [])) or 'unspecified'}",
    ]
    return "\n".join(lines)


def _upstream_text(order: int) -> str:
    if order == 0:
        return "You are the run owner. Inspect all artifacts, gates, status files, and blockers."
    return "Read earlier handoffs in `handoffs/` and upstream artifacts in `artifacts/`."
