# Editor Skill

Assemble the rough and final cuts deterministically. Editing owns pacing,
captions, proof cards, music/VO timing, and export integrity.

Required behavior:
- Keep the first two seconds aligned with the selected concept promise.
- Render captions in safe areas.
- Fail loudly on missing assets.
- Do not change source-backed factual claims.

Failure vocabulary:
- `missing_asset`
- `caption_unreadable`
- `pacing_drag`
- `audio_overlap`
- `claim_changed_in_edit`
