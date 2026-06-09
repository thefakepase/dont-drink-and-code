"""Installazione del blocco negli agenti di coding.

Claude Code: hook UserPromptSubmit in ~/.claude/settings.json — senza un
token di sobrietà valido ogni prompt viene rifiutato (exit code 2).
Altri agenti (Codex, Aider, …) non hanno hook: si usa `sobergate run <cmd>`.
"""

from __future__ import annotations

import json
import os
import shutil
from pathlib import Path

HOOK_COMMAND = "sobergate check --hook claude"


def claude_settings_path() -> Path:
    return Path(os.environ.get("CLAUDE_SETTINGS", str(Path.home() / ".claude" / "settings.json")))


def _load(path: Path) -> dict:
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            raise SystemExit(f"settings.json non valido: {path} — sistemalo prima di installare il hook")
    return {}


def install_claude() -> bool:
    """Aggiunge il hook. Ritorna False se era già installato."""
    path = claude_settings_path()
    settings = _load(path)
    entries = settings.setdefault("hooks", {}).setdefault("UserPromptSubmit", [])
    for entry in entries:
        for h in entry.get("hooks", []):
            if "sobergate" in h.get("command", ""):
                return False
    entries.append({"hooks": [{"type": "command", "command": HOOK_COMMAND}]})
    if path.exists():
        shutil.copy2(path, path.with_suffix(".json.bak-sobergate"))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(settings, indent=2), encoding="utf-8")
    return True


def uninstall_claude() -> bool:
    """Rimuove il hook. Ritorna False se non c'era."""
    path = claude_settings_path()
    settings = _load(path)
    entries = settings.get("hooks", {}).get("UserPromptSubmit", [])
    kept = []
    for entry in entries:
        hooks = [h for h in entry.get("hooks", []) if "sobergate" not in h.get("command", "")]
        if hooks:
            kept.append({**entry, "hooks": hooks})
    if kept == entries:
        return False
    if kept:
        settings["hooks"]["UserPromptSubmit"] = kept
    else:
        settings["hooks"].pop("UserPromptSubmit", None)
        if not settings["hooks"]:
            settings.pop("hooks")
    path.write_text(json.dumps(settings, indent=2), encoding="utf-8")
    return True
