# Long-form continuity and extension

Separate implemented routing from creative recommendations. A better prompt can clarify intent; it cannot guarantee removal of cumulative saturation, contrast, sharpness or oily-skin drift (Issue #13).

For no-cut progression, maintain stable identity, clothes, lighting, exposure intent, environment, props, movement direction, camera and voices. Common preamble contains only invariants. Each chunk supplies its current state and a concrete next action, with an intended end state that the next chunk can inherit. Never claim the end state was observed if generated frames were not supplied.

For appearance invariants, prefer one stable description in the common preamble instead of re-amplifying the same adjectives in every chunk. Repeated terms such as high contrast, glossy skin, extreme sharpness or vivid saturation can contaminate an Issue #13 drift comparison. This is a prompt-discipline precaution, not an established drift cure.

## Explicit boundary opener

For newly authored multi-chunk prompts, prefer an explicit continuation sentence as the first sentence of every chunk body after Chunk 1. Use the immediately preceding logical chunk number:

- Chunk 2 begins with `Continuation of Chunk 1.`
- Chunk 3 begins with `Continuation of Chunk 2.`

In Timeline, keep the routing header unchanged and place the sentence at the beginning of the body:

```text
[Chunk 2]
Continuation of Chunk 1. The action continues...
```

In List, place it at the beginning of each item after the first:

```text
Chunk 1 prompt...
---
Continuation of Chunk 1. Chunk 2 continues...
---
Continuation of Chunk 2. Chunk 3 continues...
```

Treat this as a preferred prompt-level mitigation candidate when a chunk boundary may be reinterpreted as a new scene or may reset pose or camera state. The sentence does not replace a concrete inherited state: follow it with the carried pose, support, momentum, gaze, camera position or camera motion that matters. It is not a verified quality guarantee or sampler/runtime fix. Preserve existing generated chunk bodies during append-only extension unless the user explicitly requests a rewrite.

A locked camera can contain breathing, speech and natural movement. Prefer a single ongoing action to unnecessary story escalation when the user requests a static long take. Fixed can suit repetitive activity; distinct dialogue or ordered phases generally need explicit chunk sections. Avoid contradictory over-specification and repeated opening gestures. Intermediate movement or music can remain unresolved; resolution belongs only at the requested final ending.

## Extend without rewriting old prompts

For a complete 2 × 15-second sequence, changing the target to 3 × 15 means one additional logical chunk and a nominal total of 45 seconds. Chunks = 1 would not mean “add one.” Normal extension uses settings, not History branching.

Preserve old chunk bodies AND the shared preamble. New facts placed in a shared preamble also change old effective prompts. Keep new-only details in the new section, beginning that appended body with the explicit continuation sentence for the preceding chunk. With Fixed, changing the fixed text changes every chunk. Preserve runtime conditions including seed, inputs, model and prompt format when reuse is intended; compatible storage is also necessary. Do not promise reuse from text alone. Do not rewrite an already generated final pose merely to make extension easier; continue plausibly from it or explain the tradeoff.

Do not change settings or a workflow just because a user asks for a prompt. If giving operating guidance, distinguish proposed settings from actions actually performed. Physical grouping can constrain independent terminal-chunk reuse.

## External observations

[The supplied Reddit discussion](https://www.reddit.com/r/StableDiffusion/comments/1waa9k0/advise_on_how_to_do_h3minimax_longer_static_no/) describes long static dialogue and quality drift, with suggestions involving several different continuation nodes. It is anecdotal, not a controlled comparison establishing a best Continuum prompt. In particular, another node's 39-frame overlap workaround is not a Continuum default and must not be imported as a rule.

For suspected regressions, separate text/routing errors from runtime or model behavior. Offer a same-input comparison if asked; do not turn ordinary prompt authoring into GPU testing or production repair.
