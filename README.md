# ideogram-prompt

> Ideogram 4 文生圖提示詞工具包 — schema 驗證、預驗證範本、JSON 結構化 prompt 撰寫指南。

把分散在官方文件、model card、技術部落格的「Ideogram 4 prompt 規則」打包成可立即使用的工具集。

## 為什麼需要這個工具

Ideogram 4 是一個 **完全以結構化 JSON caption 訓練** 的 9.3B 開源文生圖模型。Plain text prompt 也能跑，但品質會掉 — 尤其在以下場景：

- 圖中含特定文字（招牌、標題、卡片）
- 需要精準位置（bbox 布局）
- 需要精準色調（color palette 控色）
- 多元素組合（人物、物件、背景各別描述）

這個工具提供：

1. **6 個預驗證 JSON 範本** — 直接複製、改寫、出圖
2. **Python 驗證器** — 任何候選 prompt 在送進模型前先檢查一遍
3. **完整規則速查** — key 順序、bbox 座標、hex 顏色格式等細節一次整理

## 內容

```
ideogram-prompt/
├── README.md                 ← 你正在看
├── LICENSE                   ← MIT
├── SKILL.md                  ← 完整規則、triage 表、撰寫流程
├── scripts/
│   └── validate_caption.py   ← 純 stdlib 驗證器，CLI 可用
├── templates/                ← 6 個預驗證 JSON 範本
│   ├── photo-natural.json
│   ├── product-still-life.json
│   ├── illustration-flat.json
│   ├── cinematic-film-still.json
│   ├── graphic-design-poster.json
│   └── typography-card.json
└── tests/
    └── bad_caption.json      ← 故意壞的測試樣本（驗證器會抓出 14 類錯誤）
```

## 快速開始

### 1. 挑一個範本開始

```bash
# 範例：做一張電影感的單桅船日落照
cp templates/cinematic-film-still.json my_prompt.json
```

編輯 `my_prompt.json`，改 `high_level_description` / `style_description.*` / `compositional_deconstruction.*`。

### 2. 驗證

```bash
python scripts/validate_caption.py my_prompt.json
# [OK] my_prompt.json
# 1 file(s); 1 clean, 0 with warnings.
```

零警告才能用。有警告會附 `T*` / `S*` / `E*` / `X1` 代碼，照訊息修。

### 3. 送進模型

本機若裝了官方 [ideogram4](https://github.com/ideogram-oss/ideogram4) 推論管線（需要 fp8/nf4 權重，gated，記得先到 Hugging Face 同意授權）：

```python
import json
from ideogram4 import PRESETS

caption = json.dumps(json.load(open("my_prompt.json")), separators=(",", ":"), ensure_ascii=False)
preset = PRESETS["V4_QUALITY_48"]
images = pipe(caption, height=1024, width=1024, num_steps=preset.num_steps,
              guidance_schedule=preset.guidance_schedule, mu=preset.mu, std=preset.std)
```

或用 [ComfyUI](https://github.com/comfyanonymous/ComfyUI) + [Comfy-Org/Ideogram-4](https://huggingface.co/Comfy-Org/Ideogram-4) 節點；或在 [ideogram.ai](https://ideogram.ai/) 上傳。

## 核心規則速查

完整版見 [`SKILL.md`](./SKILL.md)。最常踩的三個雷：

| 規則 | 範例 | 反例 |
|---|---|---|
| bbox 用 **0–1000 標準化座標**，順序 `[y_min, x_min, y_max, x_max]`，原點左上 | `[200, 300, 800, 900]` | `[200, 300, 100, 150]`（像素、顛倒）|
| 顏色用 **大寫 `#RRGGBB`**，不可簡寫 | `#1B1B2F` | `#fff`、`#abc`、`rgb(0,0,0)` |
| key 順序嚴格（照片：`aesthetics, lighting, photo, medium, color_palette`；非照片：把 `photo` 換成 `art_style`）| 照 schema | 換成 `medium, aesthetics, photo, ...` |

## 驗證器能力

`scripts/validate_caption.py` 鏡像官方 `CaptionVerifier` 規則，能抓：

- 頂層 / 巢狀未知 key
- 必填欄位缺漏（`compositional_deconstruction` / `background` / `elements`）
- key 順序錯（`style_description` 與每個 element）
- `bbox` 格式錯、值超出 `[0, 1000]`、顛倒
- 顏色字串不符合 `^#[0-9A-F]{6}$`
- `color_palette` 數量超出限制（style 16 / element 5）
- 缺少 `medium`、`photo` / `art_style` 衝突或都缺
- `text` 元素缺 `text` 欄位；`obj` 元素多了 `text` 欄位
- 序列化提示：`\uXXXX` 跳脫但原文無非 ASCII 字元

```bash
python scripts/validate_caption.py templates/*.json tests/bad_caption.json
# 對前 6 個會 [OK]，對 bad_caption 會 [FAIL] 並列出每個錯誤
```

支援 `--json` 機器可讀輸出（給 CI / pre-commit 用），exit 0 = 全乾淨 / exit 1 = 有警告。

## 適用場景對照

| 場景 | 範本 |
|---|---|
| 戶外風景、人物攝影 | `templates/photo-natural.json` |
| 產品照、靜物 | `templates/product-still-life.json` |
| 35mm 電影感、氛圍照 | `templates/cinematic-film-still.json` |
| 平面風插畫、行銷素材 | `templates/illustration-flat.json` |
| 活動海報、多文字排版 | `templates/graphic-design-poster.json` |
| 名片、卡片類設計 | `templates/typography-card.json` |

## 適用模型

- `ideogram-ai/ideogram-4-fp8`（fp8 量化）
- `ideogram-ai/ideogram-4-nf4`（nf4 量化，diffusers 支援）
- `Comfy-Org/Ideogram-4`（ComfyUI 打包版，含 fp8 與 nvfp4 雙變體）

模型本體授權為 **Ideogram 4 Non-Commercial**（不可商用）。本工具程式碼採 MIT，兩者獨立。

## Plain text 想偷懶？

Ideogram 4 官方有 **Magic Prompt** 機制：把 plain text 用 LLM 即時展開成 JSON，server-side 跑、**免費**。在官方 Python 管線中是預設行為。`claude-opus-v1` / `claude-sonnet-v1` 是另外兩個可選後端（透過 OpenRouter）。

只有當你需要**精準控制**（特定字串、特定位置、特定色票）時才需要手寫 JSON — 也就是本工具的設計場景。

## 上游

- 官方 model card：https://huggingface.co/ideogram-ai/ideogram-4-fp8
- 推論程式碼：https://github.com/ideogram-oss/ideogram4
- 技術部落格：https://ideogram.ai/blog/ideogram-4.0/
- ComfyUI 打包：https://huggingface.co/Comfy-Org/Ideogram-4
- API 申請：https://developer.ideogram.ai/

## License

MIT — 見 [`LICENSE`](./LICENSE)。

模型本體授權為 Ideogram 4 Non-Commercial，與本工具程式碼授權無關。
