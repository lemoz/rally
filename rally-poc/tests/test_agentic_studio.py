from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from agents.launch_tmux import _build_tmux_commands, _init_run_dir
from agents.roles import ROLE_SPECS, get_role
from agents.studio import (
    DEFAULT_RETRY_LIMITS,
    POC_ROOT,
    append_retry_request,
    budget_allows_generation,
    build_prompt_text,
    command_template_for_role,
    gate_template,
    load_json,
    load_tool_manifest,
    record_blocker,
    role_tool_policy,
    set_gate_decision,
)


class AgenticStudioTest(unittest.TestCase):
    def test_manifest_role_permissions(self) -> None:
        manifest = load_tool_manifest()

        research = role_tool_policy("research", manifest)
        generation = role_tool_policy("generation", manifest)
        critic = role_tool_policy("critic", manifest)

        self.assertTrue(research["can_browse_web"])
        self.assertTrue(research["can_capture_sources"])
        self.assertTrue(generation["can_spend_money"])
        self.assertFalse(critic["can_trigger_retries"])
        self.assertIn("write retry requests", critic["allowed_tools"])

    def test_command_template_precedence(self) -> None:
        env = {
            "RALLY_AGENT_COMMAND_TEMPLATE": "global --prompt-file {prompt_file}",
            "RALLY_AGENT_COMMAND_TEMPLATE_GENERATION": "generation --prompt-file {prompt_file}",
        }

        self.assertEqual(
            command_template_for_role("generation", env),
            "generation --prompt-file {prompt_file}",
        )
        self.assertEqual(
            command_template_for_role("critic", env),
            "global --prompt-file {prompt_file}",
        )

    def test_prompt_includes_skill_tools_budget_and_rubric(self) -> None:
        run = {
            "run_id": "test",
            "project": "openscreen",
            "style_id": "psyop_anime_90s",
            "goal": "test prompt",
        }

        prompt = build_prompt_text(run, get_role("generation"))

        self.assertIn("## Tool Access", prompt)
        self.assertIn("Generation Skill", prompt)
        self.assertIn("Can spend money: `True`", prompt)
        self.assertIn("Candidate budget: `$20.00`", prompt)
        self.assertIn("## Style Card Rubric", prompt)
        self.assertIn("boring", prompt)

    def test_gate_decision_records_review_memory(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            run_dir = Path(raw)
            (run_dir / "gates").mkdir()
            (run_dir / "run.json").write_text(json.dumps({"run_id": "r1"}), encoding="utf-8")
            (run_dir / "gates" / "concept.json").write_text(
                json.dumps(gate_template("concept"), indent=2),
                encoding="utf-8",
            )

            payload = set_gate_decision(
                run_dir,
                "concept",
                decision="approve",
                actor="tester",
                notes="strong hook",
                artifact_refs=["artifacts/selected_concept.md"],
            )

            self.assertEqual(payload["status"], "approved")
            self.assertEqual(payload["approved_by"], "tester")
            events = (run_dir / "memory" / "review_events.jsonl").read_text(encoding="utf-8")
            self.assertIn('"gate": "concept"', events)
            self.assertIn('"decision": "approve"', events)

    def test_budget_and_retry_defaults(self) -> None:
        run = {"budgets": {"candidate_budget_usd": 20.0, "spent_usd": 19.5}}

        self.assertTrue(budget_allows_generation(run, projected_cost=0.5))
        self.assertFalse(budget_allows_generation(run, projected_cost=0.51))
        self.assertEqual(DEFAULT_RETRY_LIMITS["video"], 2)
        self.assertEqual(DEFAULT_RETRY_LIMITS["lip_sync"], 1)

    def test_blocker_and_retry_request_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            run_dir = Path(raw)
            for name in ("handoffs", "blockers", "artifacts", "memory"):
                (run_dir / name).mkdir()
            run = {"run_id": "r1"}
            role = get_role("generation")

            blocker = record_blocker(run_dir, run, role, ["keyframes gate is not approved"])
            retry = append_retry_request(
                run_dir,
                shot="s01",
                reason="weak hook",
                suggested_fix="stronger opening frame",
                requested_by="critic",
            )

            self.assertTrue(blocker.exists())
            self.assertEqual(retry["status"], "requested")
            self.assertTrue((run_dir / "artifacts" / "retry_requests.json").exists())
            self.assertTrue((run_dir / "memory" / "retry_requests.jsonl").exists())

    def test_launch_init_creates_studio_run_shape_without_tmux(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            run_dir = Path(raw) / "runs" / "studio_test"

            _init_run_dir(
                run_dir,
                "studio_test",
                "openscreen",
                "psyop_anime_90s",
                "test dry run",
                "rally-studio-test",
            )

            run = load_json(run_dir / "run.json")
            concept_gate = load_json(run_dir / "gates" / "concept.json")
            commands = _build_tmux_commands("rally-studio-test", run_dir, "windows")

            self.assertEqual(run["studio_policy"]["operating_mode"], "visible_studio")
            self.assertEqual(run["budgets"]["candidate_budget_usd"], 20.0)
            self.assertTrue(concept_gate["user_approval_required"])
            self.assertTrue((run_dir / "blockers").is_dir())
            self.assertTrue((run_dir / "memory").is_dir())
            self.assertEqual(len(commands), len(ROLE_SPECS) + 1)

    def test_generation_worker_once_writes_blocker_before_paid_generation(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            run_dir = Path(raw) / "runs" / "worker_test"
            _init_run_dir(
                run_dir,
                "worker_test",
                "openscreen",
                "psyop_anime_90s",
                "test worker",
                "rally-worker-test",
            )

            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "agents.worker",
                    "--run-dir",
                    str(run_dir),
                    "--role",
                    "generation",
                    "--once",
                ],
                cwd=POC_ROOT,
                capture_output=True,
                text=True,
                timeout=20,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            status = load_json(run_dir / "status" / "generation.json")
            self.assertEqual(status["status"], "blocked")
            self.assertIn("keyframes gate is not approved", status["blockers"][0])
            self.assertTrue((run_dir / "prompts" / "06_generation.md").exists())
            self.assertTrue((run_dir / "prompts" / "06_generation.json").exists())


if __name__ == "__main__":
    unittest.main()
