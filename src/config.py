"""Global Configuration: Loads settings from .env text file."""

import os
from pathlib import Path


def load_env_file(env_path: str = ".env") -> dict:
    """Reads key-value pairs from a .env text file into os.environ."""
    env_file = Path(env_path)
    config = {}
    if env_file.exists():
        with open(env_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    key, val = line.split("=", 1)
                    key = key.strip()
                    val = val.strip().strip("'\"")
                    os.environ[key] = val
                    config[key] = val
    return config


# Auto-load on import
load_env_file()
