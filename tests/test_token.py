"""Test del token firmato e del cooldown, isolati via SOBERGATE_HOME."""

import json
import time

import pytest

from sobergate import token_store


@pytest.fixture(autouse=True)
def isolated_home(tmp_path, monkeypatch):
    monkeypatch.setenv("SOBERGATE_HOME", str(tmp_path))
    return tmp_path


class TestToken:
    def test_missing_by_default(self):
        assert token_store.status() == ("missing", None)

    def test_issue_then_valid(self):
        token_store.issue(score=85, hours=1.0)
        state, payload = token_store.status()
        assert state == "valid"
        assert payload["score"] == 85

    def test_expired(self):
        token_store.issue(score=85, hours=0.0)
        state, _ = token_store.status()
        assert state == "expired"

    def test_tampering_detected(self, isolated_home):
        token_store.issue(score=60, hours=1.0)
        f = isolated_home / token_store.TOKEN_FILE
        token = json.loads(f.read_text(encoding="utf-8"))
        token["payload"]["score"] = 100  # l'ubriaco furbo si gonfia il voto
        f.write_text(json.dumps(token), encoding="utf-8")
        state, _ = token_store.status()
        assert state == "tampered"

    def test_forged_token_without_secret_rejected(self, isolated_home):
        payload = {"v": 1, "issued": time.time(), "expires": time.time() + 3600, "score": 100, "host": "x"}
        forged = {"payload": payload, "sig": "0" * 64}
        (isolated_home / token_store.TOKEN_FILE).write_text(json.dumps(forged), encoding="utf-8")
        state, _ = token_store.status()
        assert state == "tampered"

    def test_garbage_file_is_tampered(self, isolated_home):
        (isolated_home / token_store.TOKEN_FILE).write_text("non sono json", encoding="utf-8")
        assert token_store.status()[0] == "tampered"

    def test_revoke(self):
        token_store.issue(score=85)
        token_store.revoke()
        assert token_store.status() == ("missing", None)

    def test_revoke_when_missing_is_noop(self):
        token_store.revoke()  # non deve sollevare


class TestCooldown:
    def test_no_cooldown_by_default(self):
        assert token_store.cooldown_remaining() == 0.0

    def test_cooldown_active_after_failure(self):
        token_store.start_cooldown(minutes=30)
        remaining = token_store.cooldown_remaining()
        assert 0 < remaining <= 30 * 60

    def test_expired_cooldown_is_zero(self):
        token_store.start_cooldown(minutes=0)
        assert token_store.cooldown_remaining() == 0.0

    def test_corrupt_cooldown_file_is_zero(self, isolated_home):
        (isolated_home / token_store.COOLDOWN_FILE).write_text("boh", encoding="utf-8")
        assert token_store.cooldown_remaining() == 0.0
