"""Role contracts for the tmux-visible agentic production pipeline."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RoleSpec:
    order: int
    role: str
    title: str
    mission: str
    primary_output: str
    gate: str | None
    inputs: tuple[str, ...]
    outputs: tuple[str, ...]
    checks: tuple[str, ...]

    @property
    def pane_name(self) -> str:
        return f"{self.order:02d}_{self.role}"


ROLE_SPECS: tuple[RoleSpec, ...] = (
    RoleSpec(
        order=0,
        role="producer",
        title="Producer",
        mission="Own run state, budget, gates, handoffs, and final decision quality.",
        primary_output="artifacts/producer_run_summary.md",
        gate=None,
        inputs=("run.json", "all status files", "all handoffs"),
        outputs=(
            "artifacts/producer_run_summary.md",
            "artifacts/decision_log.md",
            "gates/*.json",
        ),
        checks=(
            "Every role has a concrete artifact contract.",
            "No expensive generation starts before the required gate passes.",
            "Every rejection has a named owner and next action.",
        ),
    ),
    RoleSpec(
        order=1,
        role="research",
        title="Research",
        mission="Build the source truth pack and mark which claims are safe to use.",
        primary_output="artifacts/source_pack.md",
        gate="source_pack",
        inputs=("run.json", "project URLs", "local project notes"),
        outputs=("artifacts/source_pack.md", "artifacts/claim_inventory.json"),
        checks=(
            "All proof-bearing claims have a URL or local source path.",
            "Claims that cannot be verified are downgraded or removed.",
            "Generated visuals are never treated as evidence.",
        ),
    ),
    RoleSpec(
        order=2,
        role="trend_style",
        title="Trend Style",
        mission="Define the target visual language and distinguish real style from format variant.",
        primary_output="artifacts/style_brief.md",
        gate="style_brief",
        inputs=("artifacts/source_pack.md", "style card", "trend notes"),
        outputs=("artifacts/style_brief.md", "artifacts/reference_manifest.md"),
        checks=(
            "The style brief names camera, rhythm, typography, audio, and visual texture.",
            "The style is not only a content format.",
            "Any borrowed trend element is structural, not copied protected media.",
        ),
    ),
    RoleSpec(
        order=3,
        role="creative_director",
        title="Creative Director",
        mission="Pitch concepts, pick the strongest hook, and define the emotional arc.",
        primary_output="artifacts/selected_concept.md",
        gate="concept",
        inputs=("artifacts/source_pack.md", "artifacts/style_brief.md"),
        outputs=("artifacts/concepts.md", "artifacts/selected_concept.md"),
        checks=(
            "At least two concepts were considered.",
            "The selected concept has a first-two-seconds hook.",
            "The concept explains why a stranger would keep watching.",
        ),
    ),
    RoleSpec(
        order=4,
        role="storyboard",
        title="Storyboard",
        mission="Turn the selected concept into a six-panel sequence with shot contracts.",
        primary_output="artifacts/storyboard.json",
        gate="storyboard",
        inputs=("artifacts/selected_concept.md", "style card"),
        outputs=("artifacts/storyboard.json", "artifacts/shot_list.md"),
        checks=(
            "Every panel has one beat.",
            "Every panel has claim type, source requirement, motion intent, and caption safe area.",
            "Create a second batch instead of overcrowding more than six panels.",
        ),
    ),
    RoleSpec(
        order=5,
        role="art_director",
        title="Art Director",
        mission="Convert storyboard panels into keyframe specs and prompt packs.",
        primary_output="artifacts/keyframe_specs.json",
        gate="keyframes",
        inputs=("artifacts/storyboard.json", "artifacts/style_brief.md"),
        outputs=("artifacts/keyframe_specs.json", "artifacts/prompt_pack.md"),
        checks=(
            "Prompts specify visual composition, motion source, and continuity anchors.",
            "Proof-bearing panels are routed to deterministic render or source capture.",
            "Keyframes are reviewable before video spend.",
        ),
    ),
    RoleSpec(
        order=6,
        role="generation",
        title="Generation",
        mission="Run image/video/audio generation and record every attempt.",
        primary_output="artifacts/generation_manifest.json",
        gate="clips",
        inputs=("artifacts/keyframe_specs.json", "artifacts/prompt_pack.md"),
        outputs=("artifacts/generation_manifest.json", "assets/"),
        checks=(
            "Every generated asset has a prompt, model, cost estimate, and attempt number.",
            "Failed shots are isolated for retry.",
            "No proof-bearing exact text is delegated to a generative video model.",
        ),
    ),
    RoleSpec(
        order=7,
        role="editor",
        title="Editor",
        mission="Assemble pacing, captions, audio, proof cards, and rough/final cuts.",
        primary_output="artifacts/edit_decisions.md",
        gate="final_edit",
        inputs=("artifacts/generation_manifest.json", "assets/"),
        outputs=("artifacts/edit_decisions.md", "final/rough_cut.mp4", "final/final.mp4"),
        checks=(
            "The first two seconds show the promise.",
            "Captions are readable and do not cover important visuals.",
            "Hard cuts, music, and VO timing are intentional.",
        ),
    ),
    RoleSpec(
        order=8,
        role="critic",
        title="Critic",
        mission="Review artifacts for taste, factuality, pacing, trend fit, and retry needs.",
        primary_output="artifacts/critique.md",
        gate=None,
        inputs=("all artifacts", "final/rough_cut.mp4"),
        outputs=("artifacts/critique.md", "artifacts/retry_requests.json"),
        checks=(
            "Critique names exact shots and exact failure modes.",
            "Taste failures are not hidden behind technical eval passes.",
            "Retry requests are cheaper than full reruns where possible.",
        ),
    ),
    RoleSpec(
        order=9,
        role="publisher_packet",
        title="Publisher Packet",
        mission="Prepare posting handoff, caption, source notes, and measurement instructions.",
        primary_output="artifacts/publish_packet.md",
        gate=None,
        inputs=("final/final.mp4", "artifacts/source_pack.md", "artifacts/critique.md"),
        outputs=("artifacts/publish_packet.md", "final/"),
        checks=(
            "Caption matches the video promise.",
            "Sources and caveats are preserved.",
            "Measurement instructions are clear enough for an operator or friend.",
        ),
    ),
)


ROLE_BY_NAME = {spec.role: spec for spec in ROLE_SPECS}


def get_role(role: str) -> RoleSpec:
    try:
        return ROLE_BY_NAME[role]
    except KeyError as exc:
        known = ", ".join(sorted(ROLE_BY_NAME))
        raise ValueError(f"Unknown role {role!r}. Known roles: {known}") from exc
