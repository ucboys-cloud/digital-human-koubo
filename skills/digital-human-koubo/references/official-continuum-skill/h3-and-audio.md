# H3 description, references and audio

This is a concise adaptation of MiniMax guidance, not a reproduction of the full official skill. Do not require a long reference-format essay for every simple chunk.

## Model-facing format

For ordinary base modes, useful field order is:

```text
integrated_multimodal_description: [Shot 1] Concrete visual action, dialogue and diegetic events.
overall_soundscape: Ambience and nonverbal sounds.
non_diegetic_music: Audience-only score, or N/A.
```

For complex Ref2VA use `subject_definitions`, `summary`, `retention_analysis`, `detailed_description`, `overall_soundscape`, `non_diegetic_music` in that order. Describe what each supplied reference contributes and what is transformed or omitted. These fields live INSIDE selected model-facing text, not in place of Continuum routing headers.

Start the first cinematic shot without a timestamp. Later intentional cuts may use sequential shot numbers and increasing `At MM:SS.mmm` times. Do not add a cut merely because a logical chunk changes. Soft timing is not frame-accurate control.

T2VA does not require invented image labels. I2VA develops forward from the actual initial image; do not place an unconditional reset-to-original-first-frame instruction in the common preamble. FL2VA/L2VA convergence belongs to the appropriate terminal segment, not every chunk. Use alignment wording only with known presentation labels and the relevant sampling context; do not mechanically paste whole-video endpoint times into every chunk.

## Asset and speaker identities

`<Picture N>`, `<Subject N>`, `(S1)` and `<Audio N>` are different identity systems. Continuum hybrid presentation can include first image, last image and then reference images. Consequently UI `reference_image_1` is not universally `<Picture 1>`. Establish enabled assets and actual order before assigning labels. If unavailable, describe the intended mapping in a note and request the information needed; do not pretend to inspect unseen assets.

Use stable speaker IDs and explicit voice assignments. For example, if the user deliberately requests reversed numbering: the person on the left is (S1), using `<Audio 2>`; the person on the right is (S2), using `<Audio 1>`. This is a prompt instruction, not guaranteed hard binding. Do not infer Subject 1 automatically uses Audio 1.

Dialogue/lyrics can use `<d>[Language] exact supplied words</d>`. Preserve the user's actual words and language. Do not silently normalize punctuation or translate lyrics. `<scenetrans>` concerns speech across cinematic cuts, not a chunk-continuation API. `<cutoff>` is for intended truncation only.

Always name the speaker for each spoken line. When a voice reference is used, define the `<Audio N>` to subject/speaker mapping before dialogue; it guides timbre and delivery rather than copying the source waveform. Keep speech density realistic for the available clip time: too much dialogue can become rushed, truncated or degraded. For off-screen voiceover, explicitly mark it as off-screen and state that visible non-speakers keep their lips closed when needed. More detailed model-facing drafting rules are in [H3 prompt quality](prompt-quality.md).

## Audio paths

- Reference Audio conditions generation; it does not guarantee waveform copying.
- Driving Audio is a wired runtime path that guides generation and supplies selected source audio through Finalize. Prompt text cannot activate it.
- Audio Continuity carries previous generated audio context and is separate from both inputs.
- Video Guide Frames alone do not imply that the video's audio is connected.
- `overall_soundscape` can influence generated scene content; keep it intentional and concise rather than treating it as inert metadata.

Keep timed speech and diegetic music in the scene description, ambience in soundscape, and audience-only music in non_diegetic_music. `N/A` is appropriate for absent score; use it for soundscape only when complete silence is intended. Distribute unique phrases over chunks; sustain instrumentation, tempo, speaker identity and ongoing musical state. Do not restart the intro or force a final cadence in every chunk. If supplied lyrics cannot fit, flag the duration conflict rather than deleting words. Exact lip sync and phrase timing remain condition-dependent.

## Sources

- [Official skill](https://github.com/MiniMax-AI/MiniMax-H3/blob/main/.agents/skills/h3-prompt-writing/SKILL.md)
- [Base guide](https://github.com/MiniMax-AI/MiniMax-H3/blob/main/.agents/skills/h3-prompt-writing/references/base-en.txt)
- [Reference guide](https://github.com/MiniMax-AI/MiniMax-H3/blob/main/.agents/skills/h3-prompt-writing/references/ref-en.txt)
- [Continuum reference presentation](https://github.com/ukr8b3g-cmyk/ComfyUI-H3-Continuum/blob/49f54b6bc0b87322a3a3b3272f02875d42b356f5/reference.py)

- [Japanese H3 prompt guide translation / community notes](https://dskjal.com/deeplearning/minimax-h3-prompt-guide)

Official main may change. Inspected 2026-09-09, Git blob IDs respectively: `066429d78f72b080a52350a5b165e52cb31b0bca`, `40cf586a634d677d6b7107b367cf0ec9621be728`, `7ae1b2d07d743fd2392258a96449be9e9e322d35`.
