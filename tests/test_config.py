"""Tests for services/shared/config.py — the API port fallback fix."""

from __future__ import annotations

import pytest

from services.shared import config


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    for name in ("API_URL", "APIPORT", "API_PORT", "API_HOST"):
        monkeypatch.delenv(name, raising=False)


class TestApiBaseUrl:
    def test_default_matches_newstart_sh(self):
        # newstart.sh runs the API on 9100. The old 8090 fallback pointed at
        # nothing whenever a page ran outside the boot script.
        assert config.api_base_url() == "http://localhost:9100"
        assert config.DEFAULT_API_PORT == 9100

    def test_explicit_api_url_wins(self, monkeypatch):
        monkeypatch.setenv("API_URL", "http://api.internal:1234")
        assert config.api_base_url() == "http://api.internal:1234"

    def test_trailing_slash_stripped(self, monkeypatch):
        monkeypatch.setenv("API_URL", "http://api.internal:1234/")
        assert config.api_base_url() == "http://api.internal:1234"

    def test_apiport_env_is_followed(self, monkeypatch):
        monkeypatch.setenv("APIPORT", "9999")
        assert config.api_base_url() == "http://localhost:9999"

    def test_bad_port_falls_back_to_default(self, monkeypatch):
        monkeypatch.setenv("APIPORT", "not-a-port")
        assert config.api_base_url() == "http://localhost:9100"

    def test_custom_host(self, monkeypatch):
        monkeypatch.setenv("API_HOST", "127.0.0.1")
        assert config.api_base_url() == "http://127.0.0.1:9100"

    def test_endpoint_joins_cleanly(self, monkeypatch):
        monkeypatch.setenv("API_URL", "http://api.internal:1234")
        assert config.api_endpoint("challenges") == "http://api.internal:1234/challenges"
        assert config.api_endpoint("/challenges") == "http://api.internal:1234/challenges"
