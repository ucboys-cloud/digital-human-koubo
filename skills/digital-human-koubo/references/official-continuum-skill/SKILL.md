---
name: write-continuum-h3-prompts
description: Write, adapt, or diagnose MiniMax H3 Continuum Sequence Prompts with Fixed, List, or Timeline chunk routing, long-form continuity, image and audio references, and append-only prompt extensions. Use for Continuum prompt authoring, not runtime repair or video generation.
---

# Write Continuum H3 Prompts

## Timeline syntax hard rule

Treat this as a hard formatting rule whenever you write Continuum Timeline prompts: every Continuum timeline header must occupy the entire line. Never place prompt text on the same line as `[0-5s]`, `[5-10s]`, `[Chunk 1]`, or any other Continuum timeline header.

Correct:

```text
[0-5s]
The girl walks forward on a street.

[5-10s]
Continuation of Chunk 1. The scene moves into a parking garage.
```

Incorrect:

```text
[0-5s] The girl walks forward on a street.
[5-10s] The scene moves into a parking garage.
```

Why this matters: the current V3.8 parser recognizes Timeline headers only when the whole line is a valid header. Inline prompt text can prevent Timeline detection; with `Prompt Format = Auto`, the script may then fall back to Fixed behavior and the full script can be sent to every chunk.

If a user supplies inline headers, normalize them to the standalone form in the output instead of preserving the invalid layout. A blank line after the header is optional; the standalone header line itself is mandatory.

This is a Continuum routing rule. H3 shot markers such as `[Shot 1]` belong inside the chunk body and must not be used as Continuum chunk headers.


Produce copy-ready Sequence Prompt text, normally in English. Preserve supplied dialogue, lyrics, names and visible text verbatim unless the user requests a change. This is an independent Continuum adaptation, not an official MiniMax skill or a new model API.

## Workflow

1. Establish the actual generation mode, Chunks, Seconds per Chunk, enabled inputs and creative intent. Reuse known settings. Ask only when missing information materially affects routing; otherwise provide untimed Fixed prose without inventing runtime values.
2. Read [Continuum contract](references/continuum-contract.md) when selecting or repairing routing. It defines the version-pinned parser behavior. Keep model-facing shots separate from logical chunks.
3. For image modes, reference assets, dialogue or music, read [H3 and audio](references/h3-and-audio.md). Do not assume a numbered UI slot is the same as a model presentation label.
4. For complex, multi-shot, multi-reference or dialogue-heavy prompts, read [H3 prompt quality](references/prompt-quality.md). Apply its model-facing rules without confusing `[Shot N]` with Continuum `[Chunk N]` routing.
5. For multiple chunks, no-cut video or extending saved work, read [Continuity](references/continuity.md). When authoring new chunked prompts, prefer an explicit body-opening handoff sentence for Chunk 2 and later, such as `Continuation of Chunk 1.`, using the immediately preceding chunk number. For examples, consult [Examples](references/examples.md); durations there are examples, not defaults.
6. Choose the simplest format that preserves intent: Fixed for an ongoing state without distinct dialogue progression; Timeline with standalone numbered chunk headers for staged progression; time ranges for explicitly timed plans aligned to runtime boundaries; List to preserve a requested or existing list.
7. Write concrete current states and next actions. Keep identity, movement direction, camera, speaker mapping and relevant object states consistent. When changing a gaze, pose or body orientation inherited from a reference, describe the active transition from the observed source state to the desired target state instead of relying only on `do not`, `discard` or `remove`; pair any necessary rejection wording with the exact replacement. In Timeline, keep the routing header such as `[Chunk 2]` unchanged and put the continuation sentence at the beginning of its body. In List, put the sentence at the beginning of each item after the first. Do not invent observations of unseen images or generated frames.
8. Check header placement, coverage, nominal duration, reference mapping, preserved text and boundary handoffs. For complex prompts also check speaker ownership, action sequencing, camera perspective and unnecessary repeated appearance constraints. For extension, compare old text and common preamble without rewriting them.

## Output

Return a short settings note outside one copy-ready Sequence Prompt code block. Include Prompt Format, Chunks and Seconds per Chunk only when known or explicitly proposed. If prompt-only was requested, omit the note. Exclude citations, validation commentary and runtime metadata from the prompt block.

Do not automatically generate videos, modify workflows, install nodes or change settings. Do not promise perfect seams, identity, lip sync or correction of cumulative quality drift. The explicit continuation sentence is a preferred prompt-level mitigation candidate for boundary scene reinterpretation and pose or camera resets, not a verified guarantee or sampler fix. Do not rewrite already generated chunk bodies solely to add it unless the user requests that rewrite. A parsing rule is not a quality guarantee. Use the source baseline in the contract; if a supplied version differs, verify the relevant rules or disclose the mismatch rather than treating this document as universally current.
