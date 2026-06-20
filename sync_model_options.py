#!/usr/bin/env python3
"""
同步 model_dict.json 中的模型列表到 _conf_schema.json 的下拉选项。

使用方法:
    python sync_model_options.py
"""

from pathlib import Path

from adapter.live2d_model_registry import sync_live2d_model_registry

PLUGIN_DIR = Path(__file__).parent
MODEL_DICT_PATH = PLUGIN_DIR / "live2ds" / "model_dict.json"
CONF_SCHEMA_PATH = PLUGIN_DIR / "_conf_schema.json"


def main():
    print("识别 Live2D 模型并同步模型选项...")
    print(f"模型字典: {MODEL_DICT_PATH}")
    print(f"配置模式: {CONF_SCHEMA_PATH}")

    entries = sync_live2d_model_registry(
        plugin_dir=PLUGIN_DIR,
        live2ds_dir=PLUGIN_DIR / "live2ds",
    )
    if not entries:
        print("警告: 未找到有效的 Live2D 模型")
        return 1

    model_names = [
        item["name"].strip()
        for item in entries
        if isinstance(item.get("name"), str) and item["name"].strip()
    ]

    print(f"找到 {len(model_names)} 个模型: {', '.join(model_names)}")
    print("更新完成!")
    print("请重启 AstrBot 或刷新配置页面以查看更改。")
    return 0


if __name__ == "__main__":
    exit(main())
