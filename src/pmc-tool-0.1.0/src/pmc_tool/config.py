from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import tomllib

CONFIG_DIR = Path.home() / ".config" / "pmc-tool"
CONFIG_PATH = CONFIG_DIR / "config.toml"

DEFAULT_CONFIG = {
    "api": {
        "base_url": "https://www.ebi.ac.uk/europepmc/webservices/rest",
        "default_result_type": "lite",
        "email": "",
    },
    "search": {
        "default_page_size": 1000,
        "default_preprints_only": False,
        "synonym_expansion": True,
    },
    "output": {
        "default_format": "jsonl",
    },
}


def _merge(base: dict, override: dict) -> dict:
    result = deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _merge(result[key], value)
        else:
            result[key] = value
    return result


def load_config() -> dict:
    if not CONFIG_PATH.exists():
        return deepcopy(DEFAULT_CONFIG)
    with CONFIG_PATH.open("rb") as handle:
        loaded = tomllib.load(handle)
    return _merge(DEFAULT_CONFIG, loaded)


def save_config(config: dict) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    lines = []
    for section, values in config.items():
        lines.append(f"[{section}]")
        for key, value in values.items():
            if isinstance(value, bool):
                encoded = "true" if value else "false"
            elif isinstance(value, int):
                encoded = str(value)
            else:
                escaped = str(value).replace("\\", "\\\\").replace('"', '\\"')
                encoded = f'"{escaped}"'
            lines.append(f"{key} = {encoded}")
        lines.append("")
    CONFIG_PATH.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def reset_config() -> dict:
    config = deepcopy(DEFAULT_CONFIG)
    save_config(config)
    return config
