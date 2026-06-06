---
name: ideogram4-prompt
description: "Use when designing, reviewing, or fixing Ideogram 4 / 4.0 text-to-image prompts. Produces schema-valid JSON captions (and optional plain-text fallback) with correct key order, normalized 0-1000 bboxes, uppercase hex color palettes, and matching sampler/resolution choices. Bundles templates for photo/illustration/product/text/poster scenarios and a Python validator. Output is a copy-pasteable prompt string — no inference, no model run."
version: 1.1.0
author: ideogram profile
license: MIT
platforms: [macos, linux, windows]
metadata:
  hermes:
    tags:
      - ideogram
      - ideogram-4
      - text-to-image
      - json-prompt
      - structured-prompt
      - creative
      - prompt-engineering
    related_skills: [comfyui, baoyu-infographic, claude-design]
    category: creative
---

# Ideogram 4 Prompt Authoring

Author Ideogram 4 (a.k.a. Ideogram 4.0) prompts that match the exact JSON
schema the model was trained on. This skill is **prompt-only** — it produces
copy-pasteable prompt strings, never runs inference. Pair it with the
`comfyui` skill (or run on ideogram.ai) to actually generate.

## When to Use

- User asks for an Ideogram 4 / Ideogram 4.0 / Ideogram prompt (with or without mentioning JSON).
- User pastes a plain-text description and wants it converted to Ideogram 4 JSON.
- User has an Ideogram prompt that produced wrong results, layout drift, or text artifacts.
- User asks for "controlled composition", "bounding box layout", "color palette control", or "in-image text" on Ideogram.
- User asks which sampler / resolution / step preset to use for an Ideogram 4 generation.

**Every response MUST follow the [Clarification Gate](#default-behavior-ship-then-surface-assumptions):** ship a first version, then surface assumptions in a `📋 我做的假設` block. Do not silently decide what the user did not specify. When you do call `clarify`, follow [The Question Format](#calling-clarify-≥3-choices--auto-other): **≥3 choices, 1 question per call**. The tool auto-adds a 5th "Other (type your answer)" so the user can always self-specify.

**Do not use for:**
- SDXL / SD3 / FLUX / Hunyuan / Qwen-Image prompts (different schemas).
- ComfyUI workflow construction (use the `comfyui` skill).
- Running inference (out of scope — output is the prompt string only).

## Default Behavior: Ship, Then Surface Assumptions

The model needs ~7 decisions to produce a good prompt (branch, resolution, subject matter, mood, color, in-image text, layout intent). Users almost never specify all 7. **Do not silently decide.** Instead:

1. **Infer what you can** from the user's message.
2. **Pick reasonable defaults** from the [Assumption Catalog](references/knowledge-bank.md#assumption-catalog-use-when-inferring-from-user-input).
3. **Write the prompt** using those defaults.
4. **Emit a `📋 我做的假設` block** at the end of the response (format: [Assumption Surfacing](references/knowledge-bank.md#assumption-surfacing--required-output-format)).
5. **Call `clarify` only if** a single specific question would unblock a much better output, the user is asking for an ambiguous revision, or the user invited a question.

For full rules, the `clarify` tool contract, and 6 reusable `clarify` templates (resolution / branch / color / text / subject / mood), see [`references/knowledge-bank.md`](references/knowledge-bank.md).

## Calling `clarify`: ≥3 Choices + Auto-Other

**Hard rules:**

1. **Always provide at least 3 `choices`.** Tool max is 4. Three is the default. Two is a bug.
2. **The tool auto-appends a 5th "Other (type your answer)"** — never add a 4th choice that says "其他"/"Custom"/"自己寫".
3. **Each `choice` has a stable `value` (English slug) and a human `label` (繁中).** Slugs are referenced by downstream logic — never rename after shipping.
4. **One question per `clarify` call.** Never batch.
5. **Question is 繁中**, ends in `？`.
6. **Choices cover 80% of cases.** Edge cases go to `Other`.

For correct/wrong shapes and 6 ready-to-copy question templates, see [The Question Format in `references/knowledge-bank.md`](references/knowledge-bank.md#the-question-format--how-to-call-clarify).

## Workflow Summary (Authoring from Scratch)

1. Read request → apply [Assumption Catalog](references/knowledge-bank.md#assumption-catalog-use-when-inferring-from-user-input) → note assumed dimensions.
2. Pick the closest template from `templates/` (or build from schema if none fit).
3. Pick resolution (see [Resolution Cheat-Sheet](references/schema-cheatsheet.md#resolution-cheat-sheet); default 1024×1024 if no use case).
4. Sampler = `V4_QUALITY_48` unless user said "fast"/"draft".
5. Write `high_level_description` (1-2 sentences, echo user's own words).
6. Write `style_description` with strict key order (see [Schema Cheat-Sheet](references/schema-cheatsheet.md#the-schema-at-a-glance)).
7. Write `compositional_deconstruction.background` as one string.
8. Write `compositional_deconstruction.elements` — one dict per element the user mentioned. Add `bbox` only if the user described placement.
9. **Validate** with `scripts/validate_caption.py`. Zero warnings required.
10. Serialize: `json.dumps(c, separators=(",", ":"), ensure_ascii=False)`.
11. Emit the `📋 我做的假設` block.
12. If plain-text input: hand-tune a JSON (this skill's primary use case). Only suggest `ideogram-4-v1` Magic Prompt (free, server-side) as alternative if the user explicitly says they don't want exact control.

For Recipe A/B/C walkthroughs, see [`references/knowledge-bank.md`](references/knowledge-bank.md#one-shot-recipes).

## Triage & Pitfalls (for fixing bad prompts)

For the symptom→cause→fix table, the 12-item pitfall checklist, and the pre-ship verification list, see [`references/failure-triage.md`](references/failure-triage.md). Most-frequent issues:

- Wrong key order → validator catches it
- `bbox` in pixels or 0-1 instead of 0-1000 → validator catches it
- Lowercase hex → validator catches it
- `text` field set to a description instead of literal → re-author the `text` element
- "改一下" with no specifics → either surface assumptions or call `clarify` with 3+ choices

## Bundled Assets

- **`templates/`** — 6 pre-validated JSON samples (photo-natural, product-still-life, illustration-flat, cinematic-film-still, graphic-design-poster, typography-card). Full table in [`references/schema-cheatsheet.md`](references/schema-cheatsheet.md#bundled-templates).
- **`scripts/validate_caption.py`** — pure-stdlib CLI mirroring upstream `CaptionVerifier`. Run on every candidate prompt before shipping. Catches the most common schema/format errors. See [`references/schema-cheatsheet.md`](references/schema-cheatsheet.md#bundled-validator) for the full check list.
- **`tests/bad_caption.json`** — deliberately bad sample that exercises 14+ different error paths. Use it to verify the validator after any change.

## Source Of Truth

The schema, examples, and rules in this skill are derived from
`ideogram-oss/ideogram4/docs/prompting.md`, `inference.md`, and the official
model card. The bundled knowledge base in `workspace/ideogram4-knowledge.md`
has the full derivation. The model card is the authority if this skill and
upstream ever disagree.

## Versioning

- **1.1.0** (current) — Added Clarification Gate workflow + standardized `clarify` call format (≥3 choices, auto-Other, 6 reusable patterns). Heavy detail moved to `references/`.
- **1.0.0** — Initial release: schema reference, templates, validator, README/LICENSE.
