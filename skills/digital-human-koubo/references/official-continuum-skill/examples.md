# Authoring examples

Illustrative text, not GPU-validated quality claims. Settings notes below are not part of Sequence Prompt. Durations are examples only.

## Fixed: 3 × 10 seconds, ongoing activity

Prompt Format = Fixed; Chunks = 3; Seconds per Chunk = 10; nominal total = 30 seconds.

```text
integrated_multimodal_description: [Shot 1] One uninterrupted live-action take of an adult potter gently shaping a rotating clay bowl. The same hands maintain steady contact with the clay, making small continuous adjustments. The bowl stays centered on the wheel. Locked camera, consistent soft daylight and unchanged framing; no opening gesture, cut or final presentation.
overall_soundscape: Continuous wheel hum, soft wet clay contact and quiet room tone.
non_diegetic_music: N/A
```

## Numbered Timeline: 3 × 15 seconds, progressive action

Prompt Format = Timeline; Chunks = 3; Seconds per Chunk = 15; nominal total = 45 seconds.

```text
One uninterrupted live-action take. The same adult woman in a navy cardigan remains at a wooden desk. Locked camera, neutral daylight and unchanged background.

[Chunk 1]
integrated_multimodal_description: [Shot 1] An open notebook rests on the desk. She reads the page and slowly traces a line with her right index finger, keeping the book open and her posture relaxed.
overall_soundscape: Quiet room tone and faint sleeve movement.
non_diegetic_music: N/A

[Chunk 2]
Continuation of Chunk 1.
integrated_multimodal_description: [Shot 1] Her right hand continues along the open page, then gently turns one page while the left hand steadies the notebook. The camera does not cut or re-establish the scene.
overall_soundscape: The same room tone under a soft page turn.
non_diegetic_music: N/A

[Chunk 3]
Continuation of Chunk 2.
integrated_multimodal_description: [Shot 1] With the turned page open, she continues reading. Her right hand moves toward the notebook's lower edge and gradually rests near the end. The notebook remains open.
overall_soundscape: The same room tone with faint sleeve movement.
non_diegetic_music: N/A
```

## Equivalent outer timing

For the same 3 × 15 settings, replace only the three numbered header lines with `[0-15s]`, `[15-30s]`, `[30-45s]`. Do not put smaller half-chunk ranges outside the body expecting both to run. If duration changes to 10 seconds, the aligned time ranges must change; numbered headers need no renumbering but action density still needs review.

## Extending a saved 2 × 15 sequence

Keep its exact existing preamble and Chunk 1–2 text. Append a new standalone `[Chunk 3]` section whose body begins `Continuation of Chunk 2.` and then continues from the intended or observed final state. Do not replace the old text with a rewritten “improved” version. Target Chunks becomes 3; unchanged compatible conditions are required for reuse.

## Dialogue and music planning

For two known voices, keep a mapping such as `(S1) = left person, <Audio 2>; (S2) = right person, <Audio 1>` consistent in every relevant section. Assign each actual supplied line to its intended speaker using `<d>[Language] ...</d>` syntax, replacing the illustrative dots with the exact words. Do not invent missing reference assets.

For a supplied three-part lyric, put phrase A only in Chunk 1, phrase B only in Chunk 2 and phrase C only in Chunk 3, preserving exact words. Carry tempo, instrumentation and voice identity across the boundary; avoid new intros in parts 2–3. When Driving Audio is actually connected, describe performance to the supplied track without claiming a text instruction changes the audio wiring.

## Redirecting a reference pose or gaze

When the source state is actually visible in `<Picture 1>`, a later Timeline chunk can combine the boundary handoff with an active replacement:

```text
[Chunk 2]
Continuation of Chunk 1.
integrated_multimodal_description: [Shot 1] <Subject 1> continues the same movement from the final moment of Chunk 1. The standing studio pose and flat gaze from <Picture 1> transition into a natural forward walking posture and a downward gaze toward the camera. Her head, eyes, shoulders and torso turn together while the previous movement continues; the camera preserves its existing motion and framing.
```

Do not call the source a standing studio pose or flat gaze unless that state is visible in the supplied reference or provided by the user. When it is unknown, omit the source-state claim and describe only the desired posture, gaze and coordinated body motion.

## Simple Continuum Timeline examples

These examples intentionally keep the H3 body simple. The important Continuum rule is that every timeline header is on its own line.

### 3 x 5 seconds — simple scene progression

```text
[0-5s]
The girl walks forward on a city street at a steady pace. The camera tracks backward in front of the girl.

[5-10s]
Continuation of Chunk 1. The scene changes to a parking garage. The girl looks around, notices a red motorcycle, and walks toward it.

[10-15s]
Continuation of Chunk 2. The girl rides the red motorcycle along a city street and stops at a red traffic light.
```

### 3 x 10 seconds — continuous one-shot motion

```text
[0-10s]
A dancer begins a slow routine in the center of a rehearsal room. The camera tracks laterally while keeping the full body visible.

[10-20s]
Continuation of Chunk 1. The dancer crosses the room with wider steps and turns once while the same lateral tracking shot continues.

[20-30s]
Continuation of Chunk 2. The dancer slows, returns toward center frame, and finishes in a stable standing pose while the camera settles.
```

### 2 x 15 seconds — two-part action

```text
[0-15s]
A mechanic examines a motorcycle beside an open garage door, checks the front wheel, and reaches for a tool on a workbench.

[15-30s]
Continuation of Chunk 1. The mechanic adjusts the motorcycle, puts the tool down, starts the engine, and watches the motorcycle idle in place.
```

### Normalize inline user input before output

User input:

```text
[0-5s] walk forward
[5-10s] enter the garage
```

Skill output:

```text
[0-5s]
walk forward

[5-10s]
Continuation of Chunk 1. enter the garage
```
