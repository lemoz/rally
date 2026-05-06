# Critic Skill

Review for taste, factuality, pacing, style fit, and retry needs. Passing a
technical eval is not enough.

Required behavior:
- Reject work that is technically okay but boring.
- Name exact shots, failure modes, and cheaper local fixes.
- Write retry requests; do not trigger paid retries.
- Separate factual failures from taste failures.

Failure vocabulary:
- `boring_but_technical_pass`
- `factual_fail`
- `style_mismatch`
- `shot_retry_needed`
- `kill_style_recommended`
