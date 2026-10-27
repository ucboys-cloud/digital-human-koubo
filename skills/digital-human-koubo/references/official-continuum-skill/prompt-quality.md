# H3 prompt quality rules

These are model-facing authoring recommendations for MiniMax H3. They complement, but never replace, the Continuum routing rules in `continuum-contract.md`. `[Chunk N]` routes logical Continuum chunks; `[Shot N]` describes cinematic shots inside the text sent to H3. A chunk boundary does not imply a camera cut.

This document combines the official MiniMax H3 prompt structure already referenced by this skill with practical observations summarized in the Japanese community guide at https://dskjal.com/deeplearning/minimax-h3-prompt-guide (inspected 2026-09-10). Treat community observations as heuristics, not guaranteed model contracts.

## Use the simplest structure that is sufficient

Short, simple requests can remain concise natural language. For long, multi-reference, multi-speaker, or multi-shot prompts, use the official H3 field structure and explicit identities rather than adding more prose without structure. When a prompt is not following well, reduce it to the smallest working description and add one constraint at a time.

For base modes, prefer:

```text
integrated_multimodal_description: [Shot 1] ...
overall_soundscape: ...
non_diegetic_music: ...
```

For complex reference generation, define references before they are used with `subject_definitions`, then use `summary`, `retention_analysis`, `detailed_description`, `overall_soundscape`, and `non_diegetic_music` as appropriate.

## Define references before use

Define every model-facing reference label before using it in a shot. Keep identity systems explicit: `<Subject N>`, `<Picture N>`, `<Video N>`, `<Audio N>` and speaker IDs such as `(S1)` are not interchangeable.

Describe only the attributes that must survive into the requested framing. Excess full-body clothing or background detail can bleed into a close-up and make framing harder. If one reference supplies a face and another supplies clothing or an accessory, prefer separate subject/attribute definitions and explicitly state the transfer relationship instead of pretending they are one source object.

Use `fully_preserved` or attribute-transfer language only when the user actually wants preservation. It is guidance, not a hard constraint, and conflicting shot instructions can override it.

## Describe observable states and actions

Prefer concrete visible or audible facts over abstract intent. State the current pose, object state, spatial relation, then the next action and its observable result.

H3 distinguishes motion qualities. Use physically meaningful verbs and modifiers when the distinction matters, for example `bounce`, `sway`, `swing`, `rock`, `wobble`, `jiggle`, `wiggle`, with material/elasticity descriptions when relevant. Avoid stacking synonyms that conflict.

For ordered actions, use explicit sequencing such as `then` or a new sentence. For concurrent actions, use `while`, `throughout`, or `simultaneously`. Do not rely on a bare `and` when order versus simultaneity materially changes the scene.

## Shots, framing and camera

Start `[Shot 1]` without a timestamp. Use `[Shot 2]`, `[Shot 3]`, and increasing cut times only for intentional cinematic cuts. Prefer continuous camera motion instead of creating a new shot for a small framing or angle change.

When camera control matters, specify the useful dimensions explicitly:

- framing / shot size, such as close-up, medium shot, wide shot;
- angle, such as eye-level, high angle, low angle, overhead or over-the-shoulder;
- motion type, such as pan, tilt, dolly, truck, orbit, push-in or pull-back;
- speed and amplitude only when they materially matter.

Unqualified left/right is normally interpreted from the camera/viewer perspective. When actor-relative direction matters, state it explicitly (`to her left`) or use stage-left/stage-right language. For POV interaction, `camera` can be more reliable than `viewer` when the intended target is the viewing position, but do not use that wording if a physical camera is visible in the scene.

## Dialogue and audio

Always identify the speaker for each line. A dialogue block without speaker ownership can be assigned to the wrong visible character. When a voice reference is supplied, explicitly map `<Audio N>` to the intended subject/speaker and describe it as a timbre/reference source rather than copied waveform audio.

Use `<d>[Language] exact supplied words</d>` when appropriate and preserve the user's wording. Do not overload a short clip with more speech than can plausibly fit; excessive dialogue can become rushed, truncated, or degraded. For off-screen narration, make the voiceover role explicit and state that visible non-speaking characters keep their lips closed when that distinction matters.

`overall_soundscape` is not inert metadata: descriptions there can influence scene generation. Keep it focused on ambience, physical action sounds, and nonverbal human sound. Use `non_diegetic_music: N/A` when no audience-only score is wanted rather than repeatedly phrasing a negative command.

Community reports suggest IPA/accent cues and inline nonverbal tags can sometimes work, but these are less reliable than speaker/language/timbre mapping. Use them only when requested or needed, and never rewrite supplied dialogue merely to force an accent.

## Prefer desired states over negative phrasing

Express the state you want rather than repeatedly naming what must not happen. Examples: `locked camera` is preferable to a long list of forbidden camera movements; `non_diegetic_music: N/A` is preferable to repeated instructions about unwanted background music. Preserve explicit user negatives when they are semantically necessary, but do not amplify them.

For a gaze, pose or body orientation inherited from a reference, describe an active source-to-target transition. A bare instruction such as `Do not look at the camera` or `Discard the studio gaze` leaves the replacement state underspecified. Prefer a formulation such as: `The flat studio gaze from <Picture 1> transitions into a downward gaze toward the camera; her head, eyes, shoulders and body orientation follow naturally.` If `discard`, `remove` or equivalent wording is useful, pair it with the exact replacement state and the physical motion that reaches it.

Use the correct `<Picture N>` and `<Subject N>` mapping. Name the source pose or gaze only when it is visible in a supplied reference or explicitly described by the user; otherwise state only the desired target behavior. For Chunk 2 and later, this redirection can follow `Continuation of Chunk N.` and should inherit the prior physical and camera state rather than re-establishing the reference pose.

This source-to-target pattern is a practical prompting candidate derived from community feedback. It is not a guaranteed model behavior or a replacement for testing the actual reference and prompt combination.

## Continuum-specific long-video discipline

Keep stable appearance facts in the common preamble only when they truly must remain invariant. Each chunk body should focus on the current state, action, camera evolution, dialogue and handoff state for that interval.

Do not repeatedly intensify appearance adjectives in every chunk. Repetition of terms such as high contrast, glossy skin, extreme sharpness or vivid saturation can confound long-video appearance-drift evaluation. This is a Continuum authoring precaution, not a proven fix for Issue #13.

Do not reset an I2VA continuation to the original first image in every chunk. Do not force FL2VA/L2VA terminal convergence before the actual terminal chunk. Keep chunk routing and shot timing independent.

## Practical drafting checks

Before returning a complex prompt, verify:

- every reference label is defined before use;
- each dialogue line has an explicit speaker and language when relevant;
- sequential versus simultaneous actions are unambiguous;
- left/right perspective is explicit where it could be misunderstood;
- `[Shot N]` is used only for actual cinematic shots, not Continuum chunks;
- dialogue density is plausible for the available duration;
- fixed appearance constraints are not needlessly repeated per chunk;
- soundscape and non-diegetic music describe only what is intended;
- unwanted reference gaze, pose or orientation is redirected to an explicit desired state rather than rejected without a replacement;
- no unseen image/frame details were invented.

## Sources

- Japanese translation and community-practice compilation: https://dskjal.com/deeplearning/minimax-h3-prompt-guide
- Official MiniMax H3 skill and base/ref guides: see `h3-and-audio.md`.
