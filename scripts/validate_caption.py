#!/usr/bin/env python3
"""
Validate an Ideogram 4 JSON caption against the upstream CaptionVerifier rules.

Usage:
    python validate_caption.py <path-to-json-or-string> [more ...]
    python validate_caption.py --stdin < prompt.json
    python validate_caption.py --json <path>   # machine-readable output

Exit code:
    0  every file passed with no warnings
    1  one or more warnings emitted
    2  usage / parse error

Checks (in order, with file:line hints when possible):
  T1  caption must be a JSON object
  T2  top-level keys: only high_level_description, style_description, compositional_deconstruction
  T3  compositional_deconstruction is REQUIRED
  T4  compositional_deconstruction has only 'background' and 'elements'
  T5  background is a non-empty string
  T6  elements is a non-empty list
  S1  style_description is an object (or absent)
  S2  when style_description present, requires aesthetics, lighting, medium
  S3  exactly one of {photo, art_style} must be set
  S4  key order: photo branch = aesthetics,lighting,photo,medium[,color_palette]
  S5  key order: art  branch = aesthetics,lighting,medium,art_style[,color_palette]
  S6  color_palette: list of uppercase #RRGGBB, 0-16 entries
  S7  no unknown keys in style_description
  E1  element must be an object
  E2  element requires 'type' = "obj" or "text"
  E3  obj element: key order type,bbox,desc[,color_palette]
  E4  text element: key order type,bbox,text,desc[,color_palette]
  E5  bbox: optional, [y_min,x_min,y_max,x_max], ints in [0,1000]
  E6  text element requires 'text' field as a non-empty string
  E7  obj element must not have 'text' field
  E8  element color_palette: 0-5 uppercase #RRGGBB
  E9  element desc: non-empty string
  X1  encoding: backslash-u XXXX escapes with no literal non-ASCII content
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

HEX_RE = re.compile(r"^#[0-9A-F]{6}$")

# Canonical key orders. The first key sets the branch.
STYLE_KEY_ORDER_PHOTO = ("aesthetics", "lighting", "photo", "medium", "color_palette")
STYLE_KEY_ORDER_ART = ("aesthetics", "lighting", "medium", "art_style", "color_palette")

ELEMENT_KEY_ORDER_OBJ = ("type", "bbox", "desc", "color_palette")
ELEMENT_KEY_ORDER_TEXT = ("type", "bbox", "text", "desc", "color_palette")

TOP_LEVEL_ALLOWED = {"high_level_description", "style_description", "compositional_deconstruction"}
CD_ALLOWED = {"background", "elements"}
STYLE_ALLOWED = {"aesthetics", "lighting", "medium", "photo", "art_style", "color_palette"}


# ----------------------------- helpers ---------------------------------------

def _w(severity: str, code: str, path: str, msg: str) -> dict:
    return {"severity": severity, "code": code, "path": path, "message": msg}


def _check_hex_color(value: Any, path: str, palette: str) -> list[dict]:
    warnings: list[dict] = []
    if not isinstance(value, str):
        return [_w("warning", "X1", f"{path}.{palette}", f"hex color must be a string, got {type(value).__name__}")]
    if not HEX_RE.match(value):
        if re.match(r"^#[0-9a-f]{6}$", value):
            return [_w("warning", "X1", f"{path}.{palette}", f"hex color must be UPPERCASE: {value!r} -> {value.upper()!r}")]
        if re.match(r"^#[0-9a-f]{3}$", value):
            return [_w("warning", "X1", f"{path}.{palette}", f"hex shorthand not allowed: {value!r}; use full #RRGGBB")]
        if value.startswith("rgb") or value.startswith("hsl"):
            return [_w("warning", "X1", f"{path}.{palette}", f"function-form color not allowed: {value!r}; use #RRGGBB")]
        return [_w("warning", "X1", f"{path}.{palette}", f"hex color must match ^#[0-9A-F]{{6}}$, got {value!r}")]
    return warnings


def _check_key_order(actual: list[str], canonical: tuple[str, ...], path: str, label: str) -> list[dict]:
    """Compare actual key order against canonical. The optional keys (those in canonical but not in actual) are removed
    from canonical first; if any remaining canonical key appears in actual, the relative order is checked."""
    warnings: list[dict] = []
    # Only compare keys that are actually present.
    canon_present = [k for k in canonical if k in actual]
    canon_order = {k: i for i, k in enumerate(canon_present)}
    present_sorted = sorted(actual, key=lambda k: canon_order.get(k, 10**9))
    # Anything in `actual` that isn't in the canonical list is an unknown key (handled separately).
    in_canon = [k for k in actual if k in canon_order]
    if in_canon != canon_present:
        warnings.append(_w(
            "warning", "S4" if path.startswith("style_description") else "E3",
            path, f"{label} key order is wrong. Expected {canon_present}, got {in_canon}"
        ))
    return warnings


def _check_unexpected_keys(actual: list[str], allowed: set[str], path: str) -> list[dict]:
    return [
        _w("warning", "T2", f"{path}.{k}", f"unexpected key {k!r}; allowed: {sorted(allowed)}")
        for k in actual if k not in allowed
    ]


# ----------------------------- checks ----------------------------------------

def validate(caption: Any) -> list[dict]:
    warnings: list[dict] = []

    # T1
    if not isinstance(caption, dict):
        return [_w("error", "T1", "$", f"caption must be a JSON object, got {type(caption).__name__}")]

    # T2
    warnings += _check_unexpected_keys(list(caption.keys()), TOP_LEVEL_ALLOWED, "$")

    # T3 / T4 / T5 / T6
    if "compositional_deconstruction" not in caption:
        warnings.append(_w("error", "T3", "$.compositional_deconstruction",
                           "compositional_deconstruction is REQUIRED"))
    else:
        cd = caption["compositional_deconstruction"]
        if not isinstance(cd, dict):
            warnings.append(_w("error", "T3", "$.compositional_deconstruction",
                               f"compositional_deconstruction must be an object, got {type(cd).__name__}"))
        else:
            warnings += _check_unexpected_keys(list(cd.keys()), CD_ALLOWED, "$.compositional_deconstruction")
            if "background" not in cd:
                warnings.append(_w("error", "T5", "$.compositional_deconstruction.background",
                                   "background is REQUIRED"))
            else:
                bg = cd["background"]
                if not isinstance(bg, str) or not bg.strip():
                    warnings.append(_w("error", "T5", "$.compositional_deconstruction.background",
                                       "background must be a non-empty string"))
            if "elements" not in cd:
                warnings.append(_w("error", "T6", "$.compositional_deconstruction.elements",
                                   "elements is REQUIRED"))
            else:
                elements = cd["elements"]
                if not isinstance(elements, list):
                    warnings.append(_w("error", "T6", "$.compositional_deconstruction.elements",
                                       f"elements must be a list, got {type(elements).__name__}"))
                elif not elements:
                    warnings.append(_w("warning", "T6", "$.compositional_deconstruction.elements",
                                       "elements is empty; image will have no foreground objects"))
                else:
                    for i, el in enumerate(elements):
                        warnings += _validate_element(el, f"$.compositional_deconstruction.elements[{i}]")

    # Style checks
    if "style_description" in caption:
        sd = caption["style_description"]
        if not isinstance(sd, dict):
            warnings.append(_w("error", "S1", "$.style_description",
                               f"style_description must be an object, got {type(sd).__name__}"))
        else:
            warnings += _validate_style_description(sd)

    # X1: encoding sanity
    warnings += _check_encoding_hints(caption)

    return warnings


def _validate_style_description(sd: dict) -> list[dict]:
    warnings: list[dict] = []
    keys = list(sd.keys())

    # S7 unexpected keys
    warnings += _check_unexpected_keys(keys, STYLE_ALLOWED, "$.style_description")

    # S2 required
    for req in ("aesthetics", "lighting", "medium"):
        if req not in sd:
            warnings.append(_w("error", "S2", f"$.style_description.{req}",
                               f"{req!r} is required when style_description is present"))
        elif not isinstance(sd[req], str) or not sd[req].strip():
            warnings.append(_w("error", "S2", f"$.style_description.{req}",
                               f"{req!r} must be a non-empty string"))

    # S3 photo XOR art_style
    has_photo = "photo" in sd
    has_art = "art_style" in sd
    if has_photo and has_art:
        warnings.append(_w("error", "S3", "$.style_description",
                           "set either 'photo' or 'art_style', not both"))
    elif not has_photo and not has_art:
        warnings.append(_w("error", "S3", "$.style_description",
                           "must set exactly one of 'photo' or 'art_style'"))

    # S4 / S5 key order
    if has_photo:
        warnings += _check_key_order(keys, STYLE_KEY_ORDER_PHOTO, "$.style_description", "photo-branch style_description")
    elif has_art:
        warnings += _check_key_order(keys, STYLE_KEY_ORDER_ART, "$.style_description", "art-branch style_description")

    # S6 color_palette
    if "color_palette" in sd:
        cp = sd["color_palette"]
        if not isinstance(cp, list):
            warnings.append(_w("error", "S6", "$.style_description.color_palette",
                               f"color_palette must be a list, got {type(cp).__name__}"))
        else:
            if len(cp) > 16:
                warnings.append(_w("warning", "S6", "$.style_description.color_palette",
                                   f"color_palette has {len(cp)} entries; max 16"))
            for j, c in enumerate(cp):
                warnings += _check_hex_color(c, f"$.style_description.color_palette[{j}]", "$")
    return warnings


def _validate_element(el: Any, path: str) -> list[dict]:
    warnings: list[dict] = []

    if not isinstance(el, dict):
        return [_w("error", "E1", path, f"element must be an object, got {type(el).__name__}")]

    keys = list(el.keys())
    allowed = {"type", "bbox", "desc", "text", "color_palette"}
    warnings += _check_unexpected_keys(keys, allowed, path)

    if "type" not in el:
        warnings.append(_w("error", "E2", f"{path}.type", "element requires 'type' = 'obj' or 'text'"))
        return warnings

    t = el["type"]
    if t not in ("obj", "text"):
        warnings.append(_w("error", "E2", f"{path}.type", f"type must be 'obj' or 'text', got {t!r}"))
        return warnings

    # E3 / E4 key order
    if t == "obj":
        warnings += _check_key_order(keys, ELEMENT_KEY_ORDER_OBJ, path, "obj element")
    else:
        warnings += _check_key_order(keys, ELEMENT_KEY_ORDER_TEXT, path, "text element")

    # E5 bbox
    if "bbox" in el:
        bbox = el["bbox"]
        if not (isinstance(bbox, list) and len(bbox) == 4 and all(isinstance(v, int) for v in bbox)):
            warnings.append(_w("warning", "E5", f"{path}.bbox",
                               f"bbox must be [y_min, x_min, y_max, x_max] with 4 ints, got {bbox!r}"))
        else:
            y0, x0, y1, x1 = bbox
            for v, name in zip(bbox, ("y_min", "x_min", "y_max", "x_max")):
                if not 0 <= v <= 1000:
                    warnings.append(_w("warning", "E5", f"{path}.bbox.{name}",
                                       f"bbox {name}={v} out of [0, 1000]"))
            if y0 > y1:
                warnings.append(_w("warning", "E5", f"{path}.bbox",
                                   f"y_min ({y0}) > y_max ({y1}); bbox is inverted"))
            if x0 > x1:
                warnings.append(_w("warning", "E5", f"{path}.bbox",
                                   f"x_min ({x0}) > x_max ({x1}); bbox is inverted"))

    # E6 text element requires literal 'text'
    if t == "text":
        if "text" not in el:
            warnings.append(_w("error", "E6", f"{path}.text", "text element requires 'text' field (literal string)"))
        elif not isinstance(el["text"], str) or not el["text"].strip():
            warnings.append(_w("error", "E6", f"{path}.text", "'text' must be a non-empty string"))

    # E7 obj element must not have 'text'
    if t == "obj" and "text" in el:
        warnings.append(_w("warning", "E7", f"{path}.text",
                           "obj element should not carry a 'text' field; use type='text' instead"))

    # E8 per-element color_palette
    if "color_palette" in el:
        cp = el["color_palette"]
        if not isinstance(cp, list):
            warnings.append(_w("error", "E8", f"{path}.color_palette",
                               f"color_palette must be a list, got {type(cp).__name__}"))
        else:
            if len(cp) > 5:
                warnings.append(_w("warning", "E8", f"{path}.color_palette",
                                   f"per-element color_palette has {len(cp)} entries; max 5"))
            for j, c in enumerate(cp):
                warnings += _check_hex_color(c, f"{path}.color_palette[{j}]", "$")

    # E9 desc non-empty
    if "desc" in el and (not isinstance(el["desc"], str) or not el["desc"].strip()):
        warnings.append(_w("error", "E9", f"{path}.desc", "desc must be a non-empty string"))
    elif t == "obj" and "desc" not in el:
        warnings.append(_w("warning", "E9", f"{path}.desc", "obj element should have a 'desc' field"))

    return warnings


def _check_encoding_hints(caption: Any) -> list[dict]:
    """X1: if serialized form contains \\uXXXX escapes but raw text has no non-ASCII, warn."""
    warnings: list[dict] = []
    try:
        text = json.dumps(caption, ensure_ascii=True)
    except (TypeError, ValueError):
        return warnings
    has_escape = "\\u" in text
    if not has_escape:
        return warnings
    # Sample a few u-escapes and decode them.
    matches = re.findall(r"\\u([0-9a-fA-F]{4})", text)
    if not matches:
        return warnings
    decoded = "".join(chr(int(c, 16)) for c in matches)
    non_ascii_in_decoded = any(ord(ch) > 127 for ch in decoded)
    if not non_ascii_in_decoded:
        warnings.append(_w("warning", "X1", "$",
                           "serialization contains \\uXXXX escapes with no literal non-ASCII content; "
                           "use json.dumps(..., ensure_ascii=False)"))
    return warnings


# ----------------------------- CLI -------------------------------------------

def _load(path: str) -> tuple[str, Any]:
    p = Path(path)
    raw = p.read_text(encoding="utf-8")
    if raw.startswith("\ufeff"):
        raw = raw[1:]
    try:
        return raw, json.loads(raw)
    except json.JSONDecodeError as e:
        return raw, e


def main() -> int:
    ap = argparse.ArgumentParser(description="Validate an Ideogram 4 JSON caption.")
    ap.add_argument("paths", nargs="*", help="Paths to .json files containing a caption.")
    ap.add_argument("--stdin", action="store_true", help="Read caption JSON from stdin.")
    ap.add_argument("--json", action="store_true", help="Emit machine-readable JSON output.")
    args = ap.parse_args()

    if not args.paths and not args.stdin:
        print(__doc__, file=sys.stderr)
        return 2

    results: list[dict] = []
    if args.stdin:
        raw = sys.stdin.read()
        if raw.startswith("\ufeff"):
            raw = raw[1:]
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as e:
            results.append({"path": "<stdin>", "ok": False, "warnings": [
                _w("error", "JSON", "<stdin>", f"invalid JSON: {e}")
            ]})
        else:
            ws = validate(data)
            results.append({"path": "<stdin>", "ok": not any(w["severity"] in ("error", "warning") for w in ws), "warnings": ws})
    for p in args.paths:
        try:
            _, data = _load(p)
        except FileNotFoundError:
            results.append({"path": p, "ok": False, "warnings": [
                _w("error", "IO", p, f"file not found: {p}")
            ]})
            continue
        if isinstance(data, json.JSONDecodeError):
            results.append({"path": p, "ok": False, "warnings": [
                _w("error", "JSON", p, f"invalid JSON: {data}")
            ]})
            continue
        ws = validate(data)
        ok = not any(w["severity"] in ("error", "warning") for w in ws)
        results.append({"path": p, "ok": ok, "warnings": ws})

    if args.json:
        print(json.dumps(results, indent=2, ensure_ascii=False))
    else:
        overall_ok = all(r["ok"] for r in results)
        for r in results:
            tag = "OK" if r["ok"] else "FAIL"
            print(f"[{tag}] {r['path']}")
            for w in r["warnings"]:
                sev = w["severity"].upper()
                print(f"  {sev} {w['code']:>4}  {w['path']}: {w['message']}")
        print()
        print(f"{len(results)} file(s); {sum(1 for r in results if r['ok'])} clean, "
              f"{sum(1 for r in results if not r['ok'])} with warnings.")
    return 0 if all(r["ok"] for r in results) else 1


if __name__ == "__main__":
    sys.exit(main())
