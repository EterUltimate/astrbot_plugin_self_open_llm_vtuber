from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from .plugin_runtime import get_plugin_config, update_plugin_config_value


WEBUI_SETTINGS_KEY = "webui_settings"


DEFAULT_WEBUI_SETTINGS: dict[str, Any] = {
    "general": {
        "language": "zh",
        "background_url": "",
        "use_camera_background": False,
        "show_subtitle": True,
        "ws_url": "ws://127.0.0.1:12396",
        "base_url": "http://127.0.0.1:12397",
        "image_compression_quality": 0.8,
        "image_max_width": 0,
    },
    "live2d": {
        "pointer_interactive": True,
        "scroll_to_resize": True,
    },
    "asr": {
        "selected_mic_id": "",
        "auto_stop_mic": False,
        "auto_start_mic_on": False,
        "auto_start_mic_on_conv_end": False,
        "positive_speech_threshold": 50,
        "negative_speech_threshold": 35,
        "redemption_frames": 35,
    },
    "agent": {
        "allow_proactive_speak": False,
        "idle_seconds_to_speak": 5,
        "allow_button_trigger": False,
    },
}


def load_webui_settings() -> dict[str, Any]:
    plugin_config = get_plugin_config()
    raw_settings = _mapping_get(plugin_config, WEBUI_SETTINGS_KEY, {})
    return normalize_webui_settings(raw_settings)


def save_webui_settings(settings: Any) -> dict[str, Any]:
    current = load_webui_settings()
    merged = _deep_merge(current, settings)
    normalized = normalize_webui_settings(merged)
    update_plugin_config_value(WEBUI_SETTINGS_KEY, normalized)
    return normalized


def normalize_webui_settings(settings: Any) -> dict[str, Any]:
    result = deepcopy(DEFAULT_WEBUI_SETTINGS)
    if not isinstance(settings, Mapping):
        return result

    _merge_general_settings(result["general"], settings.get("general"))
    _merge_live2d_settings(result["live2d"], settings.get("live2d"))
    _merge_asr_settings(result["asr"], settings.get("asr"))
    _merge_agent_settings(result["agent"], settings.get("agent"))
    return result


def _merge_general_settings(target: dict[str, Any], source: Any) -> None:
    if not isinstance(source, Mapping):
        return
    _copy_str(source, target, "language", allowed={"en", "zh"})
    _copy_str(source, target, "background_url")
    _copy_bool(source, target, "use_camera_background")
    _copy_bool(source, target, "show_subtitle")
    _copy_str(source, target, "ws_url")
    _copy_str(source, target, "base_url")
    _copy_float(source, target, "image_compression_quality", minimum=0.1, maximum=1.0)
    _copy_int(source, target, "image_max_width", minimum=0)


def _merge_live2d_settings(target: dict[str, Any], source: Any) -> None:
    if not isinstance(source, Mapping):
        return
    _copy_bool(source, target, "pointer_interactive")
    _copy_bool(source, target, "scroll_to_resize")


def _merge_asr_settings(target: dict[str, Any], source: Any) -> None:
    if not isinstance(source, Mapping):
        return
    _copy_str(source, target, "selected_mic_id")
    _copy_bool(source, target, "auto_stop_mic")
    _copy_bool(source, target, "auto_start_mic_on")
    _copy_bool(source, target, "auto_start_mic_on_conv_end")
    _copy_int(source, target, "positive_speech_threshold", minimum=1, maximum=100)
    _copy_int(source, target, "negative_speech_threshold", minimum=0, maximum=100)
    _copy_int(source, target, "redemption_frames", minimum=1, maximum=100)


def _merge_agent_settings(target: dict[str, Any], source: Any) -> None:
    if not isinstance(source, Mapping):
        return
    _copy_bool(source, target, "allow_proactive_speak")
    _copy_float(source, target, "idle_seconds_to_speak", minimum=0)
    _copy_bool(source, target, "allow_button_trigger")


def _mapping_get(config: Any, key: str, default: Any) -> Any:
    if isinstance(config, Mapping):
        return config.get(key, default)
    get_method = getattr(config, "get", None)
    if callable(get_method):
        value = get_method(key, default)
        return default if value is None else value
    return default


def _deep_merge(base: Any, patch: Any) -> Any:
    if not isinstance(base, Mapping) or not isinstance(patch, Mapping):
        return patch if patch is not None else base

    result = dict(base)
    for key, value in patch.items():
        existing = result.get(key)
        if isinstance(existing, Mapping) and isinstance(value, Mapping):
            result[key] = _deep_merge(existing, value)
        else:
            result[key] = value
    return result


def _copy_str(
    source: Mapping[str, Any],
    target: dict[str, Any],
    key: str,
    *,
    allowed: set[str] | None = None,
) -> None:
    value = source.get(key)
    if not isinstance(value, str):
        return
    value = value.strip()
    if allowed is not None and value not in allowed:
        return
    target[key] = value


def _copy_bool(source: Mapping[str, Any], target: dict[str, Any], key: str) -> None:
    value = source.get(key)
    if isinstance(value, bool):
        target[key] = value


def _copy_int(
    source: Mapping[str, Any],
    target: dict[str, Any],
    key: str,
    *,
    minimum: int | None = None,
    maximum: int | None = None,
) -> None:
    try:
        value = int(source.get(key))
    except Exception:
        return
    if minimum is not None:
        value = max(value, minimum)
    if maximum is not None:
        value = min(value, maximum)
    target[key] = value


def _copy_float(
    source: Mapping[str, Any],
    target: dict[str, Any],
    key: str,
    *,
    minimum: float | None = None,
    maximum: float | None = None,
) -> None:
    try:
        value = float(source.get(key))
    except Exception:
        return
    if minimum is not None:
        value = max(value, minimum)
    if maximum is not None:
        value = min(value, maximum)
    target[key] = value
