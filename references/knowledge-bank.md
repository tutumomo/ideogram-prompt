# Clarification Gate & Question Format Knowledge Bank

This reference encodes two session-tested workflows: **(a)** how to handle under-specified user requests without silently deciding for them, and **(b)** the exact `clarify` tool call contract (≥3 choices, auto-Other, value/label split).

Use this reference whenever a user asks for a new Ideogram 4 prompt from scratch, or when revising an existing one and the cause is ambiguous.

## Clarification Gate (Default Behavior)

**Default: write a first version, then surface your assumptions — do NOT silently decide things the user did not specify.**

The model needs ~7 decisions to produce a good prompt (branch, resolution, subject matter, mood, color, in-image text, layout intent). Users almost never specify all 7. The original failure mode of this skill was to pick all 7 and ship. Now:

1. **Infer what you can** from the user's message (medium cues like "海報" / "桌布" / "IG", style cues like "電影感" / "扁平", scope cues like "簡單" / "多元素").
2. **Pick reasonable defaults** for the rest (see Assumption Catalog below).
3. **Write the prompt** using those defaults.
4. **Surface every assumption explicitly** in the response, in a `📋 我做的假設` block, so the user can correct any of them in one round-trip.

### When to call `clarify` (use sparingly)

- The user is asking for a *revision* and the cause is genuinely ambiguous (e.g. "改一下" — what to change?).
- A single specific question would unblock a much better output (e.g. "你想要日落還是中午的色溫？" when the user said "海邊照").
- The user explicitly invited a question.
- When you do call `clarify`, follow The Question Format below (≥3 choices, 1 question per call, prefer the pre-built Common Clarification Patterns).

### When NOT to call `clarify`

- The user's request is reasonably specific — just ship with assumptions surfaced.
- The user said "隨便幫我寫一個" — they want to see your taste, not a questionnaire.
- You'd be asking more than 1 question per round — that means the request is underspecified enough that you should ship a draft with assumptions and let them react.

## Assumption Catalog (use when inferring from user input)

| Dimension | Default to use | When to ask |
|---|---|---|
| Branch (photo vs art) | "photo" unless the user mentions illustration / 設計 / 圖示 / 海報 / 字型 | "想要照片感還是插畫？" only if user is genuinely undecided |
| Resolution | Match the use case mentioned (桌布 → phone wallpaper 1024×1792; IG → square 1024×1024 or 4:5; 海報 → 2:3 portrait; 桌布桌機 → 16:9 widescreen). If no use case: 1024×1024 square. | "要什麼尺寸/用途？" only when the user wants exact dimensions and you can't infer |
| Sampler | `V4_QUALITY_48` always. Only switch to `V4_TURBO_12` if the user said "先看個草稿" or "快速". | Never ask. |
| Color palette | 2-4 hex codes picked to match the subject's mood. Include a background color. | "你有指定的色票嗎？" only if the user mentioned "品牌色" / "用 XX 顏色" or attached a color reference |
| In-image text | Add `type: "text"` elements only if the user mentioned specific words / titles / a brand name | "圖上要放文字嗎？" when the user said "標題是 X" but the wording is unclear |
| Layout | Default to single subject centered + soft background. Add explicit `bbox` only when the user described placement ("左邊" / "在角落" / "占滿背景"). | Never ask. |
| Subject fidelity | Use the user's nouns verbatim. Do not invent elements they didn't ask for. | Never. |

## Assumption Surfacing — Required Output Format

Every prompt response MUST end with a `📋 我做的假設` block:

```
📋 我做的假設（如需調整告訴我，就改對應那一行）：
- branch: photo
- resolution: 1536 × 1024 (3:2 landscape, 用於桌布桌機)
- sampler: V4_QUALITY_48
- color_palette: 暖橘夕陽配色 (#FF6B35, #F7C59F, #1A659E, #2B2D42)
- in-image text: 無
- 構圖: 單一主體（船）放右三分之一，水平線在下三分之一
```

Only list dimensions where you actually had to assume. If the user specified everything explicitly, this block can be omitted (but still mention the few defaults you kept, like the sampler).

## The Question Format — How to Call `clarify`

**Hard rules** (these are not style preferences — they map to the tool's contract):

1. **Always provide at least 3 `choices`.** Tool max is 4. Three is the default. Two is a bug.
2. **The tool auto-appends a 5th "Other (type your answer)" option** — never add a 4th choice that says "其他"/"Custom"/"自己寫". The `Other` is built in.
3. **Each `choice` has a stable `value` (English slug) and a human `label` (繁中).** Use slugs like `"photo"`, `"landscape_3x2"`, `"warm_sunset"` — never change a slug after it ships, since future prompts may key off it.
4. **One question per `clarify` call.** Never batch two questions in one call. Ask the most-blocking question first; defer the rest to subsequent rounds.
5. **The `question` field is 繁中**, ends in `？` (not `?`), and references the dimension the user needs to decide.
6. **Choices are mutually exclusive and collectively cover the obvious options.** If 80% of users will pick from choices 1–3, those 3 are required. The 20% edge case goes to `Other`.

**Correct shape:**

```python
clarify(
  question="這張圖主要給誰看、用在哪裡？",
  choices=[
    {"value": "ig_post",  "label": "Instagram / 社群貼文（1:1 方形，1024×1024）"},
    {"value": "desktop",  "label": "桌機桌布（16:9 寬螢幕，1920×1088）"},
    {"value": "phone",    "label": "手機桌布（9:16 直式，1024×1792）"},
    {"value": "print_a3", "label": "A3 海報印刷（2:3 直式，1024×1536）"},
  ],
  # 工具會自動加第 5 個 Other (type your answer)
)
```

**Wrong shapes (do not do these):**

```python
# ❌ 只有 2 個選項 — 用戶被擠到只能選 Other
clarify(question="要用什麼顏色？", choices=[{"value": "warm", ...}, {"value": "cool", ...}])

# ❌ 把 "其他" 列為第 4 個選項 — 重複
clarify(question="...", choices=[..., {"value": "other", "label": "其他"}])

# ❌ 開放式 yes/no — 浪費一次 round-trip
clarify(question="要加文字嗎？", choices=[{"value": "yes", ...}, {"value": "no", ...}])

# ❌ 一次問兩題 — 工具只回一題，第二題就消失
clarify(question="要什麼尺寸跟顏色？", choices=[...])

# ❌ value 用中文（會被後續邏輯當 key 引用，難處理）
choices=[{"value": "暖橘夕陽", "label": "暖橘夕陽"}]
```

## Common Clarification Patterns — Reusable Templates

Copy the exact wording rather than re-inventing it — the labels are calibrated to match common user vocabulary and the defaults downstream expect.

**Pattern 1: Resolution / use case** (ask when no use case is implied)

```python
clarify(
  question="這張圖主要給誰看、用在哪裡？這會決定比例與尺寸。",
  choices=[
    {"value": "ig_post",     "label": "Instagram / 社群貼文（1:1 方形）"},
    {"value": "desktop",     "label": "桌機桌布（16:9 寬螢幕）"},
    {"value": "phone",       "label": "手機桌布（9:16 直式）"},
    {"value": "print_poster","label": "海報 / 印刷品（2:3 直式）"},
  ],
)
```

**Pattern 2: Branch (photo vs art)** (ask when the user is genuinely undecided)

```python
clarify(
  question="你想要照片感、還是插畫/設計感？",
  choices=[
    {"value": "photo",      "label": "照片感（相機寫實風格）"},
    {"value": "flat_illus", "label": "扁平插畫（向量、乾淨、編輯設計感）"},
    {"value": "3d_render",  "label": "3D 渲染（Cinema 4D / Blender 質感）"},
    {"value": "painting",   "label": "繪畫感（水彩、油畫、拼貼等）"},
  ],
)
```

**Pattern 3: Color / mood** (ask when the user said "品牌色" / "用 XX 顏色" / attached a reference, or when the subject is mood-heavy and you can't guess)

```python
clarify(
  question="整體色調想要哪個方向？",
  choices=[
    {"value": "warm_sunset",   "label": "暖橘夕陽（#FF6B35 / #F7C59F 調性）"},
    {"value": "cool_minimal",  "label": "冷色極簡（#1B3A5C / #5B8FB9 調性）"},
    {"value": "earthy_natural","label": "大地自然（#5C1B1B / #E6B422 調性）"},
    {"value": "high_contrast", "label": "高對比黑白（#0E1A2B / #FFFFFF）"},
  ],
)
```

**Pattern 4: In-image text** (ask when the user said "標題是 X" or "上面要寫" but the wording is unclear)

```python
clarify(
  question="圖上要放的文字內容是什麼？",
  choices=[
    {"value": "no_text",     "label": "不放文字（純視覺）"},
    {"value": "title_only",  "label": "只要一個主標題（你直接告訴我文字）"},
    {"value": "title_date",  "label": "主標題 + 日期/副標題（兩行文字）"},
    {"value": "full_poster", "label": "完整海報（標題/副標/日期/小字/QR code）"},
  ],
)
```

**Pattern 5: Subject / focal element** (ask when the user said something like "做一張 XX 的圖" but did not name a specific focal point — common for abstract requests like "做一張安靜的感覺")

```python
clarify(
  question="這張圖的主體是什麼？",
  choices=[
    {"value": "environment", "label": "環境為主（沒明確主體，重氛圍）"},
    {"value": "single_obj",  "label": "單一物件（明確主角，例如一個人、一件物品）"},
    {"value": "multi_scene", "label": "多元素場景（人物 + 物件 + 背景）"},
    {"value": "abstract",    "label": "抽象構圖（色塊、光影、幾何，不指認物體）"},
  ],
)
```

**Pattern 6: Mood** (ask when the request is heavy on adjective but light on nouns — "做一張安靜 / 戲劇性 / 寂寞的圖")

```python
clarify(
  question="想要的情緒基調是哪一個？",
  choices=[
    {"value": "serene",     "label": "平靜 / 寧靜（低對比、冷暖溫和）"},
    {"value": "dramatic",   "label": "戲劇性 / 強烈（高對比、深色或高彩）"},
    {"value": "joyful",     "label": "歡樂 / 明亮（高彩、暖光、開放構圖）"},
    {"value": "mysterious", "label": "神秘 / 內斂（低光、剪影、有限細節）"},
  ],
)
```

## Decision rule: which dimension to ask first

When multiple dimensions are unclear, ask the most-blocking one first:

1. **Subject / focal element** (Pattern 5) — if you don't know what's in the image, everything else is moot.
2. **Branch** (Pattern 2) — photo vs art completely changes the rest of the prompt structure.
3. **Resolution / use case** (Pattern 1) — informs composition, but can be patched after the prompt is written.
4. **Mood** (Pattern 6) — usually inferable; ask only if the request is adjective-heavy with no nouns.
5. **Color / palette** (Pattern 3) — default works for most cases; ask only if the user mentioned brand colors.
6. **In-image text** (Pattern 4) — ask only if text was implied.

Never ask all 6 in one session. Ask at most 2 questions across the whole conversation; the rest should land in the `📋 我做的假設` block as already-decided values.

## One-Shot Recipes

**Recipe A: User says "幫我寫一張海邊日落的 Ideogram prompt"**

1. **Read the message and run the Assumption Catalog.** "海邊日落" → photo branch, landscape resolution, 暖橘色調, 環境為主, 沒有 in-image text. Note: the user did not specify resolution ratio or mood (peaceful vs dramatic).
2. **Make a draft with assumed values:**
   - branch: photo
   - resolution: 1536 × 1024 (3:2 landscape, 預設桌機桌布尺寸)
   - sampler: V4_QUALITY_48
   - color_palette: 暖橘夕陽 (`#FF6B35`, `#F7C59F`, `#1A659E`, `#2B2D42`)
   - layout: 水平線在下三分之一，主體留空 (因為用戶沒指定主體)
3. **Copy `templates/cinematic-film-still.json` as base**, replace `high_level_description`, `style_description.aesthetics/lighting/photo`, and `compositional_deconstruction` with the user's specifics.
4. **Validate** with `scripts/validate_caption.py`. Zero warnings.
5. **Serialize and emit the `📋 我做的假設` block** with branch / resolution / color / sampler / layout / (in-image text: none) / (subject: unspecified → left as environment).
6. **Hand back the JSON string + the assumption block.** Do not re-ask "你想要什麼比例？" — the user can answer once after seeing the draft.

**Recipe B: User pastes a plain-text prompt and asks to convert**

1. **Run the validator on the user's existing prompt** if they pasted JSON; if plain text, skip.
2. **Run the Assumption Catalog against the plain text.** What is the user *trying* to depict? What's the *implicit* use case? What color/mood/text is implied?
3. **Write a hand-tuned JSON** that captures all of the user's intent plus your inferred values.
4. **Validate, serialize, emit the `📋 我做的假設` block.** Highlight the dimensions where the user did not specify and you had to guess.
5. **Mention the alternative path once** (in the assumption block or as a footer): "如果你只想要直觀擴寫、不需要精確控制，可以用官方 `ideogram-4-v1` Magic Prompt（免費，server-side）自動展開 plain text。"
