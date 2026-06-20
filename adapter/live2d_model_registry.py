from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

from astrbot.api import logger


MODEL_DICT_FILENAME = "model_dict.json"
CONF_SCHEMA_FILENAME = "_conf_schema.json"


def sync_live2d_model_registry(
    *,
    plugin_dir: Path,
    live2ds_dir: Path,
) -> list[dict[str, Any]]:
    entries = merge_detected_live2d_models(live2ds_dir=live2ds_dir)
    sync_conf_schema_model_options(
        conf_schema_path=plugin_dir / CONF_SCHEMA_FILENAME,
        model_entries=entries,
    )
    return entries


def merge_detected_live2d_models(*, live2ds_dir: Path) -> list[dict[str, Any]]:
    model_dict_path = live2ds_dir / MODEL_DICT_FILENAME
    existing_entries = _load_model_dict(model_dict_path)
    detected_entries = detect_live2d_models(live2ds_dir=live2ds_dir)

    merged_entries: list[dict[str, Any]] = []
    index_by_name: dict[str, int] = {}
    for entry in existing_entries:
        model_name = _normalize_model_name(entry.get("name"))
        if not model_name or model_name in index_by_name:
            continue
        index_by_name[model_name] = len(merged_entries)
        merged_entries.append(deepcopy(entry))

    added_models: list[str] = []
    for detected in detected_entries:
        model_name = _normalize_model_name(detected.get("name"))
        if not model_name:
            continue
        if model_name in index_by_name:
            _ensure_model_url(merged_entries[index_by_name[model_name]], detected)
            continue
        index_by_name[model_name] = len(merged_entries)
        merged_entries.append(detected)
        added_models.append(model_name)

    if merged_entries != existing_entries:
        model_dict_path.parent.mkdir(parents=True, exist_ok=True)
        model_dict_path.write_text(
            json.dumps(merged_entries, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        logger.info(
            "[ModelSync] Live2D model_dict updated. detected=%s added=%s",
            len(detected_entries),
            ", ".join(added_models) if added_models else "<none>",
        )

    return merged_entries


def detect_live2d_models(*, live2ds_dir: Path) -> list[dict[str, Any]]:
    if not live2ds_dir.exists():
        return []

    detected_entries: list[dict[str, Any]] = []
    for model_path in sorted(live2ds_dir.glob("*/*.model3.json")):
        entry = build_live2d_model_entry(live2ds_dir=live2ds_dir, model_path=model_path)
        if entry is not None:
            detected_entries.append(entry)
    return detected_entries


def build_live2d_model_entry(
    *,
    live2ds_dir: Path,
    model_path: Path,
) -> dict[str, Any] | None:
    try:
        payload = json.loads(model_path.read_text(encoding="utf-8-sig"))
    except Exception as exc:
        logger.warning("[ModelSync] Failed to parse Live2D model `%s`: %s", model_path, exc)
        return None

    if not _looks_like_cubism_model(payload):
        return None

    model_dir = model_path.parent
    model_name = _resolve_model_name(live2ds_dir=live2ds_dir, model_path=model_path)
    relative_model_path = model_path.relative_to(live2ds_dir).as_posix()
    file_references = payload.get("FileReferences")
    file_references = file_references if isinstance(file_references, dict) else {}
    motion_map = _build_motion_map(file_references.get("Motions"))
    emotion_map = _build_emotion_map(
        file_references.get("Expressions"),
        model_dir=model_dir,
    )
    hit_areas = _collect_hit_area_ids(payload.get("HitAreas"))

    return {
        "name": model_name,
        "description": f"Auto-detected Live2D model from {model_dir.name}.",
        "url": f"/live2ds/{relative_model_path}",
        "kScale": 0.5,
        "initialXshift": 0,
        "initialYshift": 0,
        "kXOffset": 1150,
        "idleMotionGroupName": _resolve_idle_motion_group(file_references.get("Motions")),
        "emotionMap": emotion_map,
        "motionMap": motion_map,
        "tapMotions": {hit_area_id: {"": 1} for hit_area_id in hit_areas},
    }


def sync_conf_schema_model_options(
    *,
    conf_schema_path: Path,
    model_entries: list[dict[str, Any]],
) -> None:
    if not conf_schema_path.exists():
        return

    try:
        conf_schema = json.loads(conf_schema_path.read_text(encoding="utf-8-sig"))
    except Exception as exc:
        logger.warning("[ModelSync] Failed to read `%s`: %s", conf_schema_path, exc)
        return

    if not isinstance(conf_schema, dict):
        return

    live2d_schema = conf_schema.get("live2d_model_name")
    if not isinstance(live2d_schema, dict):
        return

    model_names = [
        name
        for name in (_normalize_model_name(item.get("name")) for item in model_entries)
        if name
    ]
    if not model_names:
        return

    old_options = live2d_schema.get("options", [])
    live2d_schema["options"] = model_names
    default_name = _normalize_model_name(live2d_schema.get("default"))
    if default_name not in model_names:
        live2d_schema["default"] = model_names[0]

    if live2d_schema.get("options") == old_options and default_name in model_names:
        return

    conf_schema_path.write_text(
        json.dumps(conf_schema, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    logger.info("[ModelSync] Config schema model options synced: %s", model_names)


def _load_model_dict(model_dict_path: Path) -> list[dict[str, Any]]:
    if not model_dict_path.exists():
        return []
    try:
        payload = json.loads(model_dict_path.read_text(encoding="utf-8-sig"))
    except Exception as exc:
        logger.warning("[ModelSync] Failed to read `%s`: %s", model_dict_path, exc)
        return []
    if not isinstance(payload, list):
        logger.warning("[ModelSync] Ignoring invalid `%s`: expected a JSON array.", model_dict_path)
        return []
    return [item for item in payload if isinstance(item, dict)]


def _looks_like_cubism_model(payload: Any) -> bool:
    if not isinstance(payload, dict):
        return False
    references = payload.get("FileReferences")
    if not isinstance(references, dict):
        return False
    moc = references.get("Moc")
    textures = references.get("Textures")
    return isinstance(moc, str) and moc.endswith(".moc3") and isinstance(textures, list)


def _resolve_model_name(*, live2ds_dir: Path, model_path: Path) -> str:
    try:
        first_part = model_path.relative_to(live2ds_dir).parts[0]
    except Exception:
        first_part = model_path.parent.name
    return _normalize_model_name(first_part) or _normalize_model_name(model_path.stem)


def _build_emotion_map(expressions: Any, *, model_dir: Path) -> dict[str, str]:
    expression_files: dict[str, str] = {}
    if isinstance(expressions, list):
        for item in expressions:
            if not isinstance(item, dict):
                continue
            name = _normalize_action_key(item.get("Name") or item.get("name"))
            file_name = _normalize_asset_path(item.get("File") or item.get("file"))
            if name and file_name:
                expression_files[name] = file_name

    if not expression_files:
        for expression_path in sorted(model_dir.rglob("*.exp3.json")):
            try:
                relative_path = expression_path.relative_to(model_dir).as_posix()
            except Exception:
                continue
            expression_key = _normalize_action_key(
                expression_path.name.removesuffix(".exp3.json")
            )
            if expression_key and relative_path:
                expression_files[expression_key] = relative_path

    if not expression_files:
        return {}

    result: dict[str, str] = {}
    for semantic_key, candidates in _EXPRESSION_CANDIDATES.items():
        for candidate in candidates:
            if candidate in expression_files:
                result[semantic_key] = expression_files[candidate]
                break
    if "neutral" not in result:
        first_file = next(iter(expression_files.values()), "")
        if first_file:
            result["neutral"] = first_file
    return result


def _build_motion_map(motions: Any) -> dict[str, str]:
    if not isinstance(motions, dict):
        return {}

    motion_files: dict[str, str] = {}
    first_motion = ""
    for group_name, motion_items in motions.items():
        if not isinstance(motion_items, list):
            continue
        for item in motion_items:
            if not isinstance(item, dict):
                continue
            file_name = _normalize_asset_path(item.get("File") or item.get("file"))
            if not file_name:
                continue
            if not first_motion:
                first_motion = file_name
            file_key = _normalize_action_key(Path(file_name).stem.replace(".motion3", ""))
            group_key = _normalize_action_key(group_name)
            if file_key and file_key not in motion_files:
                motion_files[file_key] = file_name
            if group_key and group_key not in motion_files:
                motion_files[group_key] = file_name

    if not motion_files and first_motion:
        motion_files["neutral"] = first_motion

    result: dict[str, str] = {}
    for semantic_key, candidates in _MOTION_CANDIDATES.items():
        for candidate in candidates:
            if candidate in motion_files:
                result[semantic_key] = motion_files[candidate]
                break
    if "neutral" not in result and first_motion:
        result["neutral"] = first_motion
    return result


def _resolve_idle_motion_group(motions: Any) -> str:
    if not isinstance(motions, dict) or not motions:
        return "Idle"
    for group_name in motions:
        if isinstance(group_name, str) and group_name.strip().lower() == "idle":
            return group_name
    for group_name in motions:
        if isinstance(group_name, str) and group_name.strip():
            return group_name
    return "Idle"


def _collect_hit_area_ids(hit_areas: Any) -> list[str]:
    if not isinstance(hit_areas, list):
        return []
    result: list[str] = []
    seen: set[str] = set()
    for item in hit_areas:
        if not isinstance(item, dict):
            continue
        hit_area_id = _normalize_model_name(item.get("Id") or item.get("id"))
        if not hit_area_id or hit_area_id in seen:
            continue
        seen.add(hit_area_id)
        result.append(hit_area_id)
    return result


def _ensure_model_url(existing: dict[str, Any], detected: dict[str, Any]) -> None:
    if not isinstance(existing.get("url"), str) or not existing.get("url"):
        existing["url"] = detected.get("url", "")


def _normalize_model_name(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def _normalize_action_key(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return (
        value.strip()
        .replace(" ", "_")
        .replace("-", "_")
        .replace(".motion3", "")
        .replace(".exp3", "")
        .lower()
    )


def _normalize_asset_path(value: Any) -> str:
    return value.strip().replace("\\", "/") if isinstance(value, str) else ""


_EXPRESSION_CANDIDATES: dict[str, tuple[str, ...]] = {
    "neutral": ("neutral", "normal", "default", "idle", "exp_01"),
    "happy": ("happy", "joy", "smile", "blush", "exp_04"),
    "joy": ("joy", "happy", "smile", "blush", "exp_04"),
    "smirk": ("smirk", "embarrassed", "happy", "exp_04"),
    "anger": ("anger", "angry", "murderous", "exp_03"),
    "angry": ("angry", "anger", "murderous", "exp_03"),
    "disgust": ("disgust", "messy", "angry", "exp_03"),
    "fear": ("fear", "confused", "question", "exp_02"),
    "sad": ("sad", "sadness", "tired", "extremelytired", "exp_02"),
    "sadness": ("sadness", "sad", "tired", "extremelytired", "exp_02"),
    "surprise": ("surprise", "surprised", "exclamation", "question", "exp_04"),
    "surprised": ("surprised", "surprise", "exclamation", "question", "exp_04"),
    "thinking": ("thinking", "loading", "question", "confused", "neutral"),
    "confused": ("confused", "question", "fear", "loading"),
    "embarrassed": ("embarrassed", "blush", "happy"),
    "tired": ("tired", "extremelytired", "sad", "sadness"),
}

_MOTION_CANDIDATES: dict[str, tuple[str, ...]] = {
    "neutral": ("neutral", "idle", "normal"),
    "happy": ("happy", "joy", "smile", "开心", "开心轻晃", "微笑"),
    "joy": ("joy", "happy", "smile", "开心", "开心轻晃", "微笑"),
    "smirk": ("smirk", "happy", "微笑_左偏头", "歪头坏笑"),
    "embarrassed": ("embarrassed", "害羞躲闪", "微笑_眨眼_右"),
    "excited": ("excited", "surprised", "surprise", "惊讶"),
    "surprise": ("surprise", "surprised", "惊讶", "惊讶后缩"),
    "surprised": ("surprised", "surprise", "惊讶", "惊讶后缩"),
    "anger": ("anger", "angry", "生气", "不耐烦前倾"),
    "angry": ("angry", "anger", "生气", "不耐烦前倾"),
    "disgust": ("disgust", "angry", "生气"),
    "sad": ("sad", "sadness", "伤心", "失落下垂"),
    "sadness": ("sadness", "sad", "伤心", "失落下垂"),
    "tired": ("tired", "疲惫哈欠", "伤心"),
    "fear": ("fear", "confused", "左右晃动", "困惑歪头"),
    "thinking": ("thinking", "思考停顿", "loading", "左右晃动"),
    "confused": ("confused", "困惑歪头", "左右晃动"),
}
