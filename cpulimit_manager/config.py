"""Persistent configuration for cpulimit-manager.

The config file is stored at ~/.cpulimit-manager.cfg as plain key=value pairs,
one per line (no section headers).  Unknown keys are preserved on load so that
future versions can add settings without overwriting user data.
"""

from __future__ import annotations

import logging
from pathlib import Path

log = logging.getLogger(__name__)

CONFIG_PATH = Path.home() / ".cpulimit-manager.cfg"

_DEFAULTS: dict[str, str] = {
    "refresh": "2",
    "theme": "",
    "limit_percentage": "50",
}


class AppConfig:
    """Simple flat-file key=value configuration manager."""

    def __init__(self, path: Path = CONFIG_PATH) -> None:
        self._path = path
        self._data: dict[str, str] = dict(_DEFAULTS)
        self._load()

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _load(self) -> None:
        """Read key=value pairs from the config file.

        Missing file is silently ignored (first-run case).  Malformed lines
        and read errors are logged and skipped.
        """
        try:
            with open(self._path) as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    if "=" in line:
                        key, _, val = line.partition("=")
                        self._data[key.strip()] = val.strip()
        except FileNotFoundError:
            pass  # first run — defaults will be used
        except Exception as exc:
            log.debug("AppConfig._load: %s", exc)

    def _save(self) -> None:
        """Write all key=value pairs to the config file."""
        try:
            with open(self._path, "w") as f:
                for key, val in self._data.items():
                    f.write(f"{key}={val}\n")
        except Exception as exc:
            log.debug("AppConfig._save: %s", exc)

    # ------------------------------------------------------------------
    # Properties — each setter persists immediately
    # ------------------------------------------------------------------

    @property
    def refresh(self) -> float:
        """Refresh interval in seconds (minimum 0.5)."""
        try:
            return max(0.5, float(self._data.get("refresh", "2")))
        except ValueError:
            return 2.0

    @refresh.setter
    def refresh(self, value: float) -> None:
        self._data["refresh"] = str(value)
        self._save()

    @property
    def theme(self) -> str:
        """Last selected theme name, or empty string if none saved."""
        return self._data.get("theme", "")

    @theme.setter
    def theme(self, value: str) -> None:
        self._data["theme"] = value
        self._save()

    @property
    def limit_percentage(self) -> int:
        """Default CPU limit percentage (1–800)."""
        try:
            return max(1, min(800, int(self._data.get("limit_percentage", "50"))))
        except ValueError:
            return 50

    @limit_percentage.setter
    def limit_percentage(self, value: int) -> None:
        self._data["limit_percentage"] = str(value)
        self._save()
