# Continuum routing contract

## Current Timeline parser baseline and standalone-header contract

Verified against H3 Continuum V3.8 `main` commit `bd12073c4322a88ce666fe062b7bb265f5de131a` on 2026-09-12.

- `[0-5s]`, `[5-10s]`, `[Chunk 1]`, and `[Clip 1]` are Continuum routing headers only when the header occupies the full line.
- Prompt text starts on the following line. A blank separator line is optional.
- Inline forms such as `[0-5s] walk forward` are not valid Timeline headers for this baseline and must be normalized before output.
- With `Prompt Format = Auto`, an inline-only script can be detected as Fixed and therefore be reused as the complete prompt for every chunk.
- This is a prompt-format contract and does not change MiniMax H3 shot syntax inside each chunk body.

If an older baseline identifier elsewhere in this reference conflicts with this section, this verified baseline supersedes it for Timeline-header syntax.


Baseline: V3.8, commit `bd12073c4322a88ce666fe062b7bb265f5de131a`, inspected 2026-09-09. These are implemented routing rules, not creative recommendations.

## Runtime versus text

Chunks is the target TOTAL count (1–16 INT), not the number to add. Seconds per Chunk is FLOAT, 4.0–30.0 with UI step 0.1 at this baseline. Preserve 10, 15 or fractional seconds when supplied; never impose 5 seconds. Nominal total = count × seconds. Text cannot change these controls. External inputs may override widgets; unknown connected values are not verified values. Actual frame-quantized output duration is a runtime matter.

## Parsing

| Format | Behavior |
| --- | --- |
| Fixed | Same text for every logical chunk; explicitly selecting Fixed overrides header-like content. |
| Auto | Detects supported Timeline or List syntax; otherwise Fixed. Malformed syntax can fall back to Fixed. |
| Timeline | Standalone full-line `[Chunk 1]`, `[Clip 1]`, or `[0-15s]` headers. Numbers are 1-based. Text before the first valid header is a shared preamble added to every selected section. |
| List | Standalone `---` (at least three hyphens) separates items. A JSON array of strings is also accepted. No shared-preamble broadcast. Arbitrary JSON objects are not native routing. |

Timeline chooses explicit chunk-number sections over time-range matches. For time ranges it selects ONE section with greatest overlap per chunk; ties favor the earlier section. Thus a 10-second chunk with `[0-5s]` A and `[5-10s]` B does not receive a deterministic two-part schedule: A wins the tie. Align outer time ranges with chunk boundaries; describe smaller phases inside the chosen body.

Missing Timeline coverage reuses the previous prompt; an initially uncovered chunk uses the first usable section. Missing List entries repeat the last; excess List entries are ignored. Out-of-range Timeline sections may warn. Do not deliberately rely on fallback. Produce full intended coverage and avoid mixing Timeline and List separators.

`[Shot 1]` describes a model-facing cinematic shot, not a routing header. A script containing only shot markers can be treated as Fixed and repeated whole. `[Chunk 2]` does not itself request a cut. Body timestamps are not automatically rebased into clip-local time by this parser.

## Physical grouping

Logical chunks are not always separate physical sampling calls. Under applicable 5-second FL2VA terminal-merge conditions, the last two logical chunks form one physical group. Identical prompts are shared; differing prompts can be combined as local time sections. Do not guarantee an independent review stop or regeneration for every logical chunk. Do not compensate by changing duration, seed, SIGMAS or audio settings.

## Evidence and sources

The proposal's isolated CPU parser probe passed 12 cases: Shot versus Chunk, numbered preamble, aligned times, overlap tie, maximum overlap, List preamble/non-broadcast, excess List, JSON strings, missing chunk, mixed syntax, inline invalid header, explicit Fixed. This does not test LLM obedience or video quality.

- [Parser](https://github.com/ukr8b3g-cmyk/ComfyUI-H3-Continuum/blob/49f54b6bc0b87322a3a3b3272f02875d42b356f5/v2/prompts.py)
- [README](https://github.com/ukr8b3g-cmyk/ComfyUI-H3-Continuum/blob/49f54b6bc0b87322a3a3b3272f02875d42b356f5/README.md)
- [Constants](https://github.com/ukr8b3g-cmyk/ComfyUI-H3-Continuum/blob/49f54b6bc0b87322a3a3b3272f02875d42b356f5/constants.py)
- [Sequence](https://github.com/ukr8b3g-cmyk/ComfyUI-H3-Continuum/blob/49f54b6bc0b87322a3a3b3272f02875d42b356f5/v2/sequence.py)
- [Plan](https://github.com/ukr8b3g-cmyk/ComfyUI-H3-Continuum/blob/49f54b6bc0b87322a3a3b3272f02875d42b356f5/v3/plan.py)
