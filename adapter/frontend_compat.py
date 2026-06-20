from __future__ import annotations

from typing import Any, Awaitable, Callable
from uuid import uuid4

from .payload_builder import build_error, build_live2d_models, build_webui_settings
from .webui_settings import load_webui_settings, save_webui_settings


SUPPORTED_COMPAT_MESSAGE_TYPES = {
    "fetch-backgrounds",
    "fetch-history-list",
    "fetch-live2d-models",
    "fetch-webui-settings",
    "refresh-live2d-models",
    "update-webui-settings",
    "create-new-history",
    "fetch-and-set-history",
    "delete-history",
    "heartbeat",
    "audio-play-start",
}


class FrontendCompatHandler:
    def __init__(
        self,
        *,
        background_files_getter: Callable[[], list[str]],
        live2d_model_entries_getter: Callable[[], list[dict[str, Any]]],
        refresh_live2d_models: Callable[[], list[dict[str, Any]]],
        history_bridge,
    ) -> None:
        self._background_files_getter = background_files_getter
        self._live2d_model_entries_getter = live2d_model_entries_getter
        self._refresh_live2d_models = refresh_live2d_models
        self._history_bridge = history_bridge
        self._history_uid = str(uuid4())

    @staticmethod
    def can_handle(msg_type: str | None) -> bool:
        return msg_type in SUPPORTED_COMPAT_MESSAGE_TYPES

    async def handle(
        self,
        message: dict[str, Any],
        *,
        send_json: Callable[[dict[str, Any]], Awaitable[bool]],
        refresh_and_send_model: Callable[..., Awaitable[None]],
    ) -> None:
        msg_type = message.get("type")

        if msg_type == "fetch-backgrounds":
            await send_json(
                {"type": "background-files", "files": self._background_files_getter()}
            )
        elif msg_type == "fetch-live2d-models":
            await send_json(build_live2d_models(self._live2d_model_entries_getter()))
        elif msg_type == "refresh-live2d-models":
            entries = self._refresh_live2d_models()
            await send_json(build_live2d_models(entries))
            await refresh_and_send_model(force=True)
        elif msg_type == "fetch-webui-settings":
            await send_json(build_webui_settings(load_webui_settings()))
        elif msg_type == "update-webui-settings":
            try:
                settings = save_webui_settings(message.get("settings"))
            except Exception as exc:
                await send_json(build_error(f"Failed to save WebUI settings: {exc}"))
                return
            await send_json(build_webui_settings(settings))
        elif msg_type == "fetch-history-list":
            histories = await self._history_bridge.list_histories()
            await send_json({"type": "history-list", "histories": histories})
        elif msg_type == "create-new-history":
            history_uid = await self._history_bridge.create_history()
            self._history_uid = history_uid or str(uuid4())
            await send_json(
                {"type": "new-history-created", "history_uid": self._history_uid}
            )
        elif msg_type == "fetch-and-set-history":
            history_uid = str(message.get("history_uid") or "").strip()
            messages = await self._history_bridge.fetch_history(history_uid)
            if history_uid:
                self._history_uid = history_uid
            await send_json({"type": "history-data", "messages": messages})
        elif msg_type == "delete-history":
            history_uid = str(message.get("history_uid") or "").strip()
            success = await self._history_bridge.delete_history(history_uid)
            await send_json(
                {
                    "type": "history-deleted",
                    "success": success,
                    "history_uid": history_uid,
                }
            )
        elif msg_type == "heartbeat":
            await send_json({"type": "heartbeat-ack"})
