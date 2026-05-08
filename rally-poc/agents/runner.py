"""Agentic role runner.

Backs the `RALLY_AGENT_COMMAND_TEMPLATE` env var so each tmux pane in the
agentic studio actually calls a real model instead of running in scaffold
mode. Reads a role's prompt file, gives the model file-scoped read/write
tools rooted at the run dir, and lets it produce its artifacts per the
role contract.

Uses OpenAI Chat Completions with GPT-5.5 (current flagship as of 2026-05).
The Critic role uses pipeline.video_critic directly (Gemini Flash) since
that's already a working vision-model rubric.

Wire it up:
    export RALLY_AGENT_COMMAND_TEMPLATE='python3 -m agents.runner --prompt-file {prompt_file} --run-dir {run_dir} --role {role}'

Then `python3 -m agents.launch_tmux ...` will run each role through this.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Make pipeline.config importable for env loading + key access.
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from pipeline.config import load_all_env, require_key  # noqa: E402

OPENAI_URL = "https://api.openai.com/v1/chat/completions"
DEFAULT_MODEL = "gpt-5.5"
MAX_LOOPS = 12  # plenty of headroom for read/write tool dialogue


def main() -> None:
    parser = argparse.ArgumentParser(description="Run one agentic studio role with a real model.")
    parser.add_argument("--prompt-file", required=True)
    parser.add_argument("--run-dir", required=True)
    parser.add_argument("--role", required=True)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    args = parser.parse_args()

    load_all_env()
    api_key = require_key("OPENAI_API_KEY")

    run_dir = Path(args.run_dir).resolve()
    prompt_path = Path(args.prompt_file).resolve()

    # Critic role uses the vision-model rubric directly.
    if args.role == "critic":
        return _run_critic(run_dir, prompt_path)

    role_prompt = prompt_path.read_text(encoding="utf-8")
    run_json = (run_dir / "run.json").read_text(encoding="utf-8") if (run_dir / "run.json").exists() else "{}"

    system_msg = (
        "You are an agentic role in the Rally video production studio. "
        "Read the role contract carefully. Read upstream artifacts before writing. "
        "Use the provided tools to navigate and write files inside the run directory only. "
        "When you have produced all required outputs, call the `done` tool with a short status summary. "
        "Keep your handoff entry short, specific, and actionable."
    )
    user_msg = (
        f"Role contract:\n\n{role_prompt}\n\n"
        f"Run metadata (run.json):\n\n{run_json}\n\n"
        "Now produce your artifacts. Use list_dir/read_file to gather upstream inputs, "
        "then write_file for every output the role contract specifies. Finally call done."
    )

    messages: list[dict[str, Any]] = [
        {"role": "system", "content": system_msg},
        {"role": "user", "content": user_msg},
    ]

    tools = _tools_schema()
    final_status = "incomplete"
    final_summary = ""
    for loop in range(MAX_LOOPS):
        response = _chat(messages, tools, api_key, args.model)
        choice = response["choices"][0]
        msg = choice["message"]
        messages.append(msg)
        finish_reason = choice.get("finish_reason")

        tool_calls = msg.get("tool_calls") or []
        if not tool_calls:
            # Model returned plain text — record it and stop.
            final_summary = (msg.get("content") or "")[:1000]
            break

        done_called = False
        for call in tool_calls:
            name = call["function"]["name"]
            try:
                args_in = json.loads(call["function"]["arguments"] or "{}")
            except json.JSONDecodeError:
                args_in = {}

            if name == "list_dir":
                out = _safe_list_dir(run_dir, args_in.get("path", "."))
            elif name == "read_file":
                out = _safe_read_file(run_dir, args_in.get("path", ""))
            elif name == "write_file":
                out = _safe_write_file(
                    run_dir,
                    args_in.get("path", ""),
                    args_in.get("content", ""),
                )
            elif name == "done":
                final_status = args_in.get("status", "complete")
                final_summary = args_in.get("summary", "")[:1000]
                done_called = True
                out = {"ok": True}
            else:
                out = {"error": f"unknown tool {name}"}

            messages.append({
                "role": "tool",
                "tool_call_id": call["id"],
                "content": json.dumps(out)[:8000],
            })

        if done_called:
            break
        if finish_reason and finish_reason != "tool_calls":
            break

    # Update status file
    _write_status(run_dir, args.role, final_status, summary=final_summary, loops=loop + 1)

    if final_status == "complete":
        print(f"[runner] role={args.role} complete (loops={loop + 1})")
        return
    print(f"[runner] role={args.role} {final_status} (loops={loop + 1})", file=sys.stderr)
    sys.exit(1 if final_status != "complete" else 0)


# ---- Tools ----

def _tools_schema() -> list[dict]:
    return [
        {
            "type": "function",
            "function": {
                "name": "list_dir",
                "description": "List files in a directory inside the run_dir.",
                "parameters": {
                    "type": "object",
                    "properties": {"path": {"type": "string", "description": "Relative path inside run_dir."}},
                    "required": ["path"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "read_file",
                "description": "Read a UTF-8 text file inside the run_dir.",
                "parameters": {
                    "type": "object",
                    "properties": {"path": {"type": "string"}},
                    "required": ["path"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "write_file",
                "description": "Write a UTF-8 text file inside the run_dir.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string"},
                        "content": {"type": "string"},
                    },
                    "required": ["path", "content"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "done",
                "description": "Signal that all required artifacts are written.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "status": {"type": "string", "enum": ["complete", "blocked"]},
                        "summary": {"type": "string"},
                    },
                    "required": ["status"],
                },
            },
        },
    ]


def _safe_list_dir(run_dir: Path, rel: str) -> dict:
    target = (run_dir / rel).resolve()
    if not _within(run_dir, target):
        return {"error": "path outside run_dir"}
    if not target.exists():
        return {"error": "not found", "path": rel}
    if not target.is_dir():
        return {"error": "not a directory", "path": rel}
    entries = []
    for child in sorted(target.iterdir()):
        entries.append({
            "name": child.name,
            "type": "dir" if child.is_dir() else "file",
            "size": child.stat().st_size if child.is_file() else None,
        })
    return {"path": rel, "entries": entries}


def _safe_read_file(run_dir: Path, rel: str) -> dict:
    target = (run_dir / rel).resolve()
    if not _within(run_dir, target):
        return {"error": "path outside run_dir"}
    if not target.exists() or not target.is_file():
        return {"error": "not found", "path": rel}
    try:
        text = target.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return {"error": "binary file; cannot read as text"}
    if len(text) > 60_000:
        return {"path": rel, "content": text[:60_000], "truncated": True}
    return {"path": rel, "content": text}


def _safe_write_file(run_dir: Path, rel: str, content: str) -> dict:
    target = (run_dir / rel).resolve()
    if not _within(run_dir, target):
        return {"error": "path outside run_dir"}
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    return {"path": rel, "bytes_written": len(content.encode("utf-8"))}


def _within(parent: Path, child: Path) -> bool:
    try:
        child.relative_to(parent.resolve())
    except ValueError:
        return False
    return True


# ---- OpenAI HTTP ----

def _chat(messages: list[dict], tools: list[dict], api_key: str, model: str) -> dict:
    payload = {
        "model": model,
        "messages": messages,
        "tools": tools,
        "tool_choice": "auto",
    }
    body = json.dumps(payload).encode("utf-8")

    # GPT-5.5 is a reasoning model — first token arrival can take minutes.
    # Retry transient 408/429/5xx with exponential backoff.
    import time
    delays = [0, 5, 15, 45]
    last_err: Exception | None = None
    for attempt, delay in enumerate(delays):
        if delay:
            time.sleep(delay)
        req = urllib.request.Request(
            OPENAI_URL,
            data=body,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
                "User-Agent": "rally-agent-runner/1.0",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=600) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            text = e.read().decode("utf-8", errors="replace") if e.fp else ""
            transient = e.code in {408, 429} or 500 <= e.code <= 599
            last_err = RuntimeError(f"OpenAI {e.code}: {text[:500]}")
            if not transient:
                raise last_err from e
            print(
                f"[runner] OpenAI {e.code} (attempt {attempt + 1}/{len(delays)}); "
                f"retrying in {delays[min(attempt + 1, len(delays) - 1)]}s",
                file=sys.stderr,
            )
        except (urllib.error.URLError, TimeoutError) as e:
            last_err = RuntimeError(f"OpenAI network error: {e}")
            print(
                f"[runner] network error (attempt {attempt + 1}/{len(delays)}): {e}",
                file=sys.stderr,
            )
    assert last_err is not None
    raise last_err


# ---- Critic shortcut ----

def _run_critic(run_dir: Path, prompt_path: Path) -> None:
    """Critic uses pipeline.video_critic against final/final.mp4."""
    final_video = run_dir / "final" / "final.mp4"
    storyboard = run_dir / "artifacts" / "storyboard.json"
    if not final_video.exists():
        # Try plan_bridge'd path
        bridge_plan = run_dir / "artifacts" / "plan.json"
        candidate = run_dir / f"output/{run_dir.name}/final.mp4"
        if candidate.exists():
            final_video = candidate

    if not final_video.exists():
        _write_status(run_dir, "critic", "blocked", summary="final.mp4 not found yet")
        sys.exit(1)

    import subprocess
    cmd = ["python3", "-m", "pipeline.video_critic", str(final_video)]
    if storyboard.exists():
        cmd.append(str(storyboard))
    print(f"[runner] critic invoking video_critic on {final_video}")
    result = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
    critique_path = run_dir / "artifacts" / "critique.md"
    out = result.stdout or ""
    err = result.stderr or ""
    critique_path.write_text(
        f"# Critic\n\nVideo: `{final_video}`\n\nReturn code: {result.returncode}\n\n"
        f"## Output\n\n```\n{out[-4000:]}\n```\n\n## Errors\n\n```\n{err[-2000:]}\n```\n",
        encoding="utf-8",
    )
    _write_status(run_dir, "critic", "complete" if result.returncode == 0 else "blocked",
                  summary=f"video_critic exit={result.returncode}")


def _write_status(run_dir: Path, role: str, status: str, *, summary: str = "", loops: int = 0) -> None:
    payload = {
        "role": role,
        "status": status,
        "summary": summary,
        "loops": loops,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    (run_dir / "status").mkdir(parents=True, exist_ok=True)
    (run_dir / "status" / f"{role}.json").write_text(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
