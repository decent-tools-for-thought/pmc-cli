from __future__ import annotations

from copy import deepcopy
import os
from pathlib import Path
import tomllib


def _xdg_config_home() -> Path:
    configured = os.environ.get("XDG_CONFIG_HOME")
    return Path(configured).expanduser() if configured else Path.home() / ".config"


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


def config_dir() -> Path:
    return _xdg_config_home() / "pmc-tool"


def config_path() -> Path:
    return config_dir() / "config.toml"


def _merge(base: dict, override: dict) -> dict:
    result = deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _merge(result[key], value)
        else:
            result[key] = value
    return result


def load_config() -> dict:
    path = config_path()
    if not path.exists():
        return deepcopy(DEFAULT_CONFIG)
    with path.open("rb") as handle:
        loaded = tomllib.load(handle)
    return _merge(DEFAULT_CONFIG, loaded)


def save_config(config: dict) -> None:
    path = config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
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
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def reset_config() -> dict:
    config = deepcopy(DEFAULT_CONFIG)
    save_config(config)
    return config
