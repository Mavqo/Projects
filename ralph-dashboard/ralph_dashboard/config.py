"""Configuration management for Ralph Dashboard."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from .models import DashboardConfig

logger = logging.getLogger(__name__)

CONFIG_DIR = Path.home() / ".ralph-dashboard"
CONFIG_FILE = CONFIG_DIR / "config.json"


def ensure_config_dir() -> Path:
    """Create config directory if it doesn't exist."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    return CONFIG_DIR


def load_config() -> DashboardConfig:
    """Load dashboard configuration from disk, or return defaults."""
    ensure_config_dir()
    if CONFIG_FILE.exists():
        try:
            raw = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
            return DashboardConfig(**raw)
        except (json.JSONDecodeError, ValueError) as exc:
            logger.warning("Failed to parse config file, using defaults: %s", exc)
    return DashboardConfig()


def save_config(config: DashboardConfig) -> None:
    """Save dashboard configuration to disk."""
    ensure_config_dir()
    CONFIG_FILE.write_text(
        json.dumps(config.model_dump(), indent=2),
        encoding="utf-8",
    )
    logger.info("Configuration saved to %s", CONFIG_FILE)


def get_projects_dir(config: DashboardConfig) -> Path:
    """Resolve the projects directory path."""
    return Path(config.projects_dir).expanduser().resolve()
