"""Test di installazione/rimozione del hook per Claude Code."""

import json

import pytest

from sobergate import hooks


@pytest.fixture
def settings_file(tmp_path, monkeypatch):
    f = tmp_path / "settings.json"
    monkeypatch.setenv("CLAUDE_SETTINGS", str(f))
    return f


def read(f):
    return json.loads(f.read_text(encoding="utf-8"))


class TestInstall:
    def test_install_creates_hook(self, settings_file):
        assert hooks.install_claude() is True
        data = read(settings_file)
        cmds = [h["command"] for e in data["hooks"]["UserPromptSubmit"] for h in e["hooks"]]
        assert hooks.HOOK_COMMAND in cmds

    def test_install_is_idempotent(self, settings_file):
        hooks.install_claude()
        assert hooks.install_claude() is False
        data = read(settings_file)
        assert len(data["hooks"]["UserPromptSubmit"]) == 1

    def test_install_preserves_existing_settings(self, settings_file):
        settings_file.write_text(json.dumps({"model": "opus", "hooks": {"PreToolUse": []}}), encoding="utf-8")
        hooks.install_claude()
        data = read(settings_file)
        assert data["model"] == "opus"
        assert "PreToolUse" in data["hooks"]

    def test_install_creates_backup(self, settings_file):
        settings_file.write_text("{}", encoding="utf-8")
        hooks.install_claude()
        assert settings_file.with_suffix(".json.bak-sobergate").exists()

    def test_invalid_json_aborts(self, settings_file):
        settings_file.write_text("{rotto", encoding="utf-8")
        with pytest.raises(SystemExit):
            hooks.install_claude()


class TestUninstall:
    def test_uninstall_removes_hook(self, settings_file):
        hooks.install_claude()
        assert hooks.uninstall_claude() is True
        data = read(settings_file)
        assert "hooks" not in data or "UserPromptSubmit" not in data.get("hooks", {})

    def test_uninstall_when_absent(self, settings_file):
        settings_file.write_text("{}", encoding="utf-8")
        assert hooks.uninstall_claude() is False

    def test_uninstall_keeps_other_hooks(self, settings_file):
        other = {"hooks": {"UserPromptSubmit": [{"hooks": [{"type": "command", "command": "altro-tool check"}]}]}}
        settings_file.write_text(json.dumps(other), encoding="utf-8")
        hooks.install_claude()
        hooks.uninstall_claude()
        data = read(settings_file)
        cmds = [h["command"] for e in data["hooks"]["UserPromptSubmit"] for h in e["hooks"]]
        assert cmds == ["altro-tool check"]
