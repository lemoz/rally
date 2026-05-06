# Generation Skill

Execute only approved generation work. Record every paid or generated attempt
with prompt, model, cost, output, and failure reason.

Required behavior:
- Verify keyframes gate approval before paid generation.
- Stop before spend if budget is exhausted.
- Respect retry limits: image 3, video 2, audio 2, lip sync 1.
- Never generate proof-bearing exact text or evidence.

Failure vocabulary:
- `gate_not_approved`
- `budget_exhausted`
- `retry_limit_exceeded`
- `provider_failure`
- `generated_evidence_risk`
