# Schema Cheatsheet & Bundled Assets

Quick-reference for the Ideogram 4 JSON caption schema, resolution/sampler choices, and the bundled templates/validator.

## The Schema At A Glance

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

**bbox coordinates are `[y_min, x_min, y_max, x_max]` in normalized 0-1000** (origin top-left). NOT pixels. NOT 0-1 fractions.

**Hex colors are uppercase `#RRGGBB` strings.** No shorthand `#fff`. No `rgb(…)`.

## Resolution Cheat-Sheet

Multiples of 16, range 256-2048, aspect ratios up to 6:1.

| Use case | Resolution | Aspect |
|---|---|---|
| Square | 1024 × 1024 | 1:1 |
| Landscape | 1536 × 1024 | 3:2 |
| Portrait | 1024 × 1536 | 2:3 |
| Widescreen | 1920 × 1088 | ~16:9 |
| Ultrawide | 2048 × 768 | ~21:9 |
| Phone wallpaper | 1024 × 1792 | ~9:16 |
| Social banner | 1600 × 400 | 4:1 |

## Sampler Presets

| Preset | Steps | CFG schedule | `mu` | `std` | Use when |
|---|---|---|---|---|---|
| `V4_QUALITY_48` (default) | 48 | 45 × gw=7 + 3 × gw=3 polish | 0.0 | 1.5 | Production-quality output |
| `V4_DEFAULT_20` | 20 | 18 × gw=7 + 2 × gw=3 | 0.0 | 1.75 | Faster iteration |
| `V4_TURBO_12` | 12 | 11 × gw=7 + 1 × gw=3 | 0.5 | 1.75 | Preview / brainstorming |

Maximum quality: `--height 2048 --width 2048 --sampler-preset V4_QUALITY_48`.

**"Polish tail" design:** the last few steps drop CFG to gw=3, sharpening fine detail without over-saturating the global composition.

## Bundled Templates

All templates are pre-validated JSON strings in `templates/`. Copy, edit, validate.

| File | Scenario | Branch |
|---|---|---|
| `templates/photo-natural.json` | Outdoor / nature photography with explicit bboxes | photo |
| `templates/product-still-life.json` | Studio product on neutral background | photo |
| `templates/illustration-flat.json` | Flat vector illustration, marketing style | art |
| `templates/cinematic-film-still.json` | 35mm film look with moody lighting | photo |
| `templates/graphic-design-poster.json` | Event poster with multiple text elements | art (graphic_design) |
| `templates/typography-card.json` | Business card with two text elements | art (graphic_design) |

## Bundled Validator

`scripts/validate_caption.py` mirrors the upstream `CaptionVerifier` rules. Run it on any candidate prompt before handing it back. Catches:

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

## Serialization Convention

When producing the final compact string to send to the model:

```python
import json
s = json.dumps(caption, separators=(",", ":"), ensure_ascii=False)
```

The `separators` arg strips default whitespace; `ensure_ascii=False` keeps non-ASCII characters literal (recommended for non-English in-image text or color descriptions). The validator warns on `\uXXXX` escapes when no literal non-ASCII content exists — that's the encoding-hint check at work.

## Source Of Truth

The schema, examples, and rules in this skill are derived from `ideogram-oss/ideogram4/docs/prompting.md`, `inference.md`, and the official model card. The bundled knowledge base in `workspace/ideogram4-knowledge.md` has the full derivation. The model card is the authority if this skill and upstream ever disagree.
