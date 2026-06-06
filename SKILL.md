---
name: ideogram4-prompt
description: "Use when designing, reviewing, or fixing Ideogram 4 / 4.0 text-to-image prompts. Produces schema-valid JSON captions (and optional plain-text fallback) with correct key order, normalized 0-1000 bboxes, uppercase hex color palettes, and matching sampler/resolution choices. Bundles templates for photo/illustration/product/text/poster scenarios and a Python validator. Output is a copy-pasteable prompt string — no inference, no model run."
version: 1.0.0
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

**Do not use for:**
- SDXL / SD3 / FLUX / Hunyuan / Qwen-Image prompts (different schemas).
- ComfyUI workflow construction (use the `comfyui` skill).
- Running inference (out of scope — output is the prompt string only).

## Quick Reference: The Schema At A Glance

```
caption = {
  high_level_description?: str,                # one or two sentences
  style_description?: {
    aesthetics: str,                           # REQUIRED if present
    lighting: str,                             # REQUIRED
    medium: str,                               # REQUIRED
    photo: str,              # for photo     -  PHOTO branch key order
    art_style: str,           # for non-photo -  ART branch key order
    color_palette?: [str],                     # 0-16 uppercase #RRGGBB
  },
  compositional_deconstruction: {              # REQUIRED object
    background: str,                           # REQUIRED string
    elements: [                                # REQUIRED list
      {type: "obj",  bbox?: [y,x,Y,X], desc, color_palette?: [str]} |
      {type: "text", bbox?: [y,x,Y,X], text,  desc, color_palette?: [str]}
    ]
  }
}
```

**Key order is enforced.** Wrong order = the model samples outside training distribution.
- Photo branch: `aesthetics → lighting → photo → medium → color_palette`
- Art branch:  `aesthetics → lighting → medium → art_style → color_palette`
- `obj` element:  `type → bbox → desc → color_palette`
- `text` element: `type → bbox → text → desc → color_palette`

**bbox coordinates are `[y_min, x_min, y_max, x_max]` in normalized 0-1000** (origin
top-left). NOT pixels. NOT 0-1 fractions.

**Hex colors are uppercase `#RRGGBB` strings.** No shorthand `#fff`. No `rgb(…)`.

## Workflow: Authoring a Prompt From Scratch

1. **Classify the request.** Photo / illustration / 3D / painting / graphic design → pick the `style_description` branch. Does it include literal in-image text? → add a `type: "text"` element.
2. **Pick resolution first** (it informs composition). See resolution table below.
3. **Pick sampler preset** (almost always `V4_QUALITY_48`; `V4_TURBO_12` for previews).
4. **Write `high_level_description`** in 1-2 sentences. Strongly recommended in every prompt.
5. **Write `style_description`** with strict key order. Default to uppercase hex `color_palette` even if it's only 2 colors — it always helps.
6. **Write `compositional_deconstruction.background`** as one continuous descriptive string (not a list).
7. **Write `compositional_deconstruction.elements`** — one dict per visual element. Use `bbox` for any element whose position matters. Front-to-back depth order usually reads well.
8. **Validate** with `scripts/validate_caption.py`. Fix every warning. Do not ship a prompt with key-order, bbox-range, or hex-case warnings.
9. **Serialize** with `json.dumps(c, separators=(",", ":"), ensure_ascii=False)`.
10. **For plain-text input from the user**, do NOT hand-write JSON. Tell the user the
    `ideogram-4-v1` Magic Prompt (free) will expand it server-side — or write
    a hand-tuned JSON if the user needs exact control.

## Workflow: Fixing a Bad Prompt

When the user says "Ideogram put X in the wrong place / ignored the color /
mangled the text / didn't render element Y", run this triage:

| Symptom | Likely cause | Fix |
|---|---|---|
| Layout drift (subject in wrong quadrant) | `bbox` missing or out of `[0, 1000]` | Add explicit `bbox` to that element. Use the resolution's quadrant convention (center ~ 500,500). |
| Text shows wrong glyphs / missing letters | Text element placed without `bbox`, or `text` field set to a description instead of literal | Use `type: "text"` with `text` = the exact string and a `bbox` per word/line. |
| Colors ignored | `color_palette` missing or in lowercase `#fff` form | Use 2-5 uppercase `#RRGGBB` codes. Include the background color in the palette. |
| `medium` / `photo` swapped branch | Photo prompt uses `art_style` (or vice versa) | Photo → use `photo` field. Non-photo → use `art_style`. Mismatch drops quality noticeably. |
| Elements merged or missing | Two elements with overlapping bboxes and similar `desc`s | Tighten `desc` per element to a single subject. Use distinctive bboxes. |
| Generic / "AI looking" output | Plain text prompt, not JSON | Convert to JSON. Quality gap is large (esp. for in-image text and layout). |
| Image blocked by safety filter | Non-NSFW prompt rejected | Try rephrasing to JSON form; plain-text false-positive rate is higher. |

## Resolution & Sampler Cheat-Sheet

**Resolution** (multiples of 16, range 256-2048, aspect ratios up to 6:1):

| Use case | Resolution | Aspect |
|---|---|---|
| Square | 1024 × 1024 | 1:1 |
| Landscape | 1536 × 1024 | 3:2 |
| Portrait | 1024 × 1536 | 2:3 |
| Widescreen | 1920 × 1088 | ~16:9 |
| Ultrawide | 2048 × 768 | ~21:9 |
| Phone wallpaper | 1024 × 1792 | ~9:16 |
| Social banner | 1600 × 400 | 4:1 |

**Sampler presets** (see `docs/inference.md` upstream for full reference):

| Preset | Steps | CFG | Use when |
|---|---|---|---|
| `V4_QUALITY_48` | 48 | 45 × gw=7 + 3 × gw=3 polish | Default. Production-quality output. |
| `V4_DEFAULT_20` | 20 | 18 × gw=7 + 2 × gw=3 | Faster iteration. |
| `V4_TURBO_12` | 12 | 11 × gw=7 + 1 × gw=3 | Preview / brainstorming. |

Maximum quality: `--height 2048 --width 2048 --sampler-preset V4_QUALITY_48`.

## Bundled Templates

All templates are pre-validated JSON strings in `templates/`. Copy, edit, validate.

| File | Scenario | Branch |
|---|---|---|
| `photo-natural.json` | Outdoor / nature photography with explicit bboxes | photo |
| `product-still-life.json` | Studio product on neutral background | photo |
| `illustration-flat.json` | Flat vector illustration, marketing style | art |
| `cinematic-film-still.json` | 35mm film look with moody lighting | photo |
| `graphic-design-poster.json` | Event poster with multiple text elements | art (graphic_design) |
| `typography-card.json` | Business card with two text elements | art (graphic_design) |

## Bundled Validator

`scripts/validate_caption.py` mirrors the upstream `CaptionVerifier` rules. Run it on
any candidate prompt before handing it back. Catches:

- Unknown top-level / nested keys
- Missing required fields (`compositional_deconstruction`, its `background` & `elements`)
- Wrong key order in `style_description` and per-element dicts
- `bbox` not a 4-int list in `[0, 1000]`
- `color_palette` entries not matching `^#[0-9A-F]{6}$` (uppercase required)
- `color_palette` length > 16 (style) or > 5 (per-element)
- `medium` missing when `style_description` is present
- `photo` / `art_style` both set or neither set
- `text` element without `text` field, or `obj` element with `text` field
- `\uXXXX` escapes present with no literal non-ASCII content (encoding hint)

```bash
python scripts/validate_caption.py templates/photo-natural.json
python scripts/validate_caption.py my_prompt.json --json
```

Exits 0 on clean, 1 on any warning. Use `--json` for machine-readable output.

## Common Pitfalls

1. **Writing JSON by eye and forgetting key order.** Always run the validator.
   The `dict` literal order matters; Python 3.7+ preserves insertion order, but
   LLM-generated code often does not.
2. **Using `bbox` in pixels or 0-1.** The model expects normalized 0-1000. A 1024×1024 image's center is `[500, 500]`, not `[512, 512]`.
3. **Lowercase hex.** `#ff8800` is rejected. The training captions used uppercase only.
4. **`text` field set to a description.** The `text` field on a `"text"` element is the LITERAL string to render — `"SALE"` not `"the word SALE in big letters"`. The visual styling goes in `desc`.
5. **Two branches in one prompt.** Setting both `photo` and `art_style` is rejected. Pick one. The `medium` field tells the model which surface you want; `photo`/`art_style` describes how.
6. **Forgetting `compositional_deconstruction`.** It is the only required top-level field. Plain `style_description` alone does not work for the reference pipeline.
7. **Inferring bbox = "anywhere".** An element with no `bbox` is allowed but the model will pick a position; if you care where it goes, set the bbox.
8. **Hand-writing JSON when the user just gave a casual description.** Recommend `ideogram-4-v1` Magic Prompt (free, server-side, default in `run_inference.py`) for casual use; only hand-write when exact control is required.
9. **Treating the model as plain-text-trained.** Ideogram 4 is **exclusively** trained on structured JSON. Plain text works but quality drops. Default to JSON unless the user explicitly asks for plain text.
10. **Mixing `compositional_deconstruction.elements` `type` typos.** `type` must be exactly `"obj"` or `"text"`. `"object"`, `"image"`, `"label"` are all rejected.

## Verification Checklist

Before handing any prompt to the user:

- [ ] Ran `python scripts/validate_caption.py <file>` with zero warnings.
- [ ] Picked a sampler preset (default `V4_QUALITY_48`).
- [ ] Picked a resolution appropriate to the use case.
- [ ] If the prompt has in-image text, every `text` element has a `bbox` and a literal `text` field.
- [ ] If the prompt has color guidance, the `color_palette` uses uppercase `#RRGGBB` only.
- [ ] If the user provided plain text and wants JSON control, told them about `ideogram-4-v1` Magic Prompt as the alternative.
- [ ] Serialized with `json.dumps(..., separators=(",", ":"), ensure_ascii=False)` if they want a compact string.

## One-Shot Recipes

**Recipe A: User says "幫我寫一張海邊日落的 Ideogram prompt"**

1. Pick photo branch. Resolution 1536 × 1024 (landscape). `V4_QUALITY_48`.
2. Copy `templates/cinematic-film-still.json` as base.
3. Replace `high_level_description`, `style_description.aesthetics/lighting/photo`, and `compositional_deconstruction` with the user's specifics.
4. Add sunset hexes (`#FF6B35`, `#F7C59F`, `#1A659E`, `#2B2D42`) to `color_palette`.
5. Validate. Hand back JSON string + recipe command.

**Recipe B: User pastes a plain-text prompt and asks to convert**

1. If they want exact control: ask for one clarifying question (output use, aspect ratio, with/without in-image text), then hand-write JSON.
2. If they don't: tell them to use the `ideogram-4-v1` Magic Prompt path — it expands plain text to JSON server-side for free.

**Recipe C: User has a JSON prompt that produced wrong output**

1. Run validator; fix anything that fires.
2. If validator is clean, walk the triage table above to identify the symptom-cause.
3. Suggest the minimum surgical change (add a bbox, uppercase the hex, etc.) — do not rewrite the whole prompt.

## Source Of Truth

The schema, examples, and rules in this skill are derived from
`ideogram-oss/ideogram4/docs/prompting.md`, `inference.md`, and the official
model card. The bundled knowledge base in `workspace/ideogram4-knowledge.md`
has the full derivation. The model card is the authority if this skill and
upstream ever disagree.
