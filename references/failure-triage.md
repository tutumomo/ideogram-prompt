# Failure Triage & Common Pitfalls

When an Ideogram 4 prompt produces wrong output, or when you're about to ship a prompt and want to catch issues early, use this reference.

## Symptom → Cause → Fix (Bad-Output Triage)

Use when the user says "Ideogram put X in the wrong place / ignored the color / mangled the text / didn't render element Y".

| Symptom | Likely cause | Fix |
|---|---|---|
| Layout drift (subject in wrong quadrant) | `bbox` missing or out of `[0, 1000]` | Add explicit `bbox` to that element. Use the resolution's quadrant convention (center ~ 500,500). |
| Text shows wrong glyphs / missing letters | Text element placed without `bbox`, or `text` field set to a description instead of literal | Use `type: "text"` with `text` = the exact string and a `bbox` per word/line. |
| Colors ignored | `color_palette` missing or in lowercase `#fff` form | Use 2-5 uppercase `#RRGGBB` codes. Include the background color in the palette. |
| `medium` / `photo` swapped branch | Photo prompt uses `art_style` (or vice versa) | Photo → use `photo` field. Non-photo → use `art_style`. Mismatch drops quality noticeably. |
| Elements merged or missing | Two elements with overlapping bboxes and similar `desc`s | Tighten `desc` per element to a single subject. Use distinctive bboxes. |
| Generic / "AI looking" output | Plain text prompt, not JSON | Convert to JSON. Quality gap is large (esp. for in-image text and layout). |
| Image blocked by safety filter | Non-NSFW prompt rejected | Try rephrasing to JSON form; plain-text false-positive rate is higher. |

## Common Pitfalls (12-item Checklist)

1. **Writing JSON by eye and forgetting key order.** Always run the validator. The `dict` literal order matters; Python 3.7+ preserves insertion order, but LLM-generated code often does not.
2. **Using `bbox` in pixels or 0-1.** The model expects normalized 0-1000. A 1024×1024 image's center is `[500, 500]`, not `[512, 512]`.
3. **Lowercase hex.** `#ff8800` is rejected. The training captions used uppercase only.
4. **`text` field set to a description.** The `text` field on a `"text"` element is the LITERAL string to render — `"SALE"` not `"the word SALE in big letters"`. The visual styling goes in `desc`.
5. **Two branches in one prompt.** Setting both `photo` and `art_style` is rejected. Pick one. The `medium` field tells the model which surface you want; `photo`/`art_style` describes how.
6. **Forgetting `compositional_deconstruction`.** It is the only required top-level field. Plain `style_description` alone does not work for the reference pipeline.
7. **Inferring bbox = "anywhere".** An element with no `bbox` is allowed but the model will pick a position; if you care where it goes, set the bbox.
8. **Hand-writing JSON when the user just gave a casual description.** Recommend `ideogram-4-v1` Magic Prompt (free, server-side, default in `run_inference.py`) for casual use; only hand-write when exact control is required.
9. **Treating the model as plain-text-trained.** Ideogram 4 is **exclusively** trained on structured JSON. Plain text works but quality drops. Default to JSON unless the user explicitly asks for plain text.
10. **Mixing `compositional_deconstruction.elements` `type` typos.** `type` must be exactly `"obj"` or `"text"`. `"object"`, `"image"`, `"label"` are all rejected.
11. **Silently deciding for the user.** Every response MUST end with a `📋 我做的假設` block listing what you assumed. The Clarification Gate is non-negotiable.
12. **Asking with < 3 choices or adding a 4th "其他" option.** The `clarify` tool auto-appends "Other (type your answer)", so a 4th "其他" choice is redundant. And asking with only 1–2 choices forces the user to type. Always provide 3–4 real, mutually exclusive choices, and let `Other` handle edge cases.

## Workflow: Fixing a Bad Prompt (Recipe C)

1. Run `python scripts/validate_caption.py <file>`; fix anything that fires.
2. If validator is clean, walk the Symptom→Cause→Fix table above to identify the cause.
3. Suggest the **minimum surgical change** (add a bbox, uppercase the hex, etc.) — do not rewrite the whole prompt.

## Pre-Ship Verification Checklist

Before handing any prompt to the user:

- [ ] Ran `python scripts/validate_caption.py <file>` with zero warnings.
- [ ] Picked a sampler preset (default `V4_QUALITY_48`).
- [ ] Picked a resolution appropriate to the use case.
- [ ] If the prompt has in-image text, every `text` element has a `bbox` and a literal `text` field.
- [ ] If the prompt has color guidance, the `color_palette` uses uppercase `#RRGGBB` only.
- [ ] If the user provided plain text and wants JSON control, told them about `ideogram-4-v1` Magic Prompt as the alternative.
- [ ] Serialized with `json.dumps(..., separators=(",", ":"), ensure_ascii=False)` if they want a compact string.
- [ ] **Response ends with a `📋 我做的假設` block** listing every dimension where I had to assume a value (Clarification Gate).
- [ ] If I called `clarify`: it had **3 or 4 choices, 1 question per call**, value/label separated, and no "其他" choice (let the tool's auto-Other do that).
