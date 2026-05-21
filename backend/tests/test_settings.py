"""Tests for Settings class (pydantic-settings)."""

import os
from unittest.mock import patch

import pytest

from app.core.settings import Settings, get_settings


class TestSettingsDefaults:
    """Settings should have sensible defaults for all fields."""

    def test_default_llm_model(self):
        settings = Settings()
        assert settings.llm_model == "deepseek-chat"

    def test_default_llm_base_url(self):
        settings = Settings()
        assert settings.llm_base_url == "https://api.deepseek.com/v1"

    def test_default_max_input_length(self):
        settings = Settings()
        assert settings.max_input_length == 1000

    def test_default_llm_timeout(self):
        settings = Settings()
        assert settings.llm_timeout == 30

    def test_default_app_name(self):
        settings = Settings()
        assert settings.app_name == "School Agent Backend"

    def test_default_deepseek_api_key_is_empty(self):
        settings = Settings()
        assert settings.deepseek_api_key == ""

    def test_default_scoring_llm_model(self):
        settings = Settings()
        assert settings.llm_scoring_model == "deepseek-chat"

    def test_default_scoring_llm_base_url(self):
        settings = Settings()
        assert settings.llm_scoring_base_url == "https://api.deepseek.com/v1"

    def test_default_scoring_llm_api_key_is_empty(self):
        settings = Settings()
        assert settings.llm_scoring_api_key == ""


class TestSettingsEnvOverrides:
    """Settings should read overrides from environment variables."""

    def test_deepseek_api_key_from_env(self, monkeypatch):
        monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key-12345")
        settings = Settings()
        assert settings.deepseek_api_key == "test-key-12345"

    def test_llm_model_from_env(self, monkeypatch):
        monkeypatch.setenv("LLM_MODEL", "gpt-4")
        settings = Settings()
        assert settings.llm_model == "gpt-4"

    def test_llm_base_url_from_env(self, monkeypatch):
        monkeypatch.setenv("LLM_BASE_URL", "https://custom.api.com/v1")
        settings = Settings()
        assert settings.llm_base_url == "https://custom.api.com/v1"

    def test_max_input_length_from_env(self, monkeypatch):
        monkeypatch.setenv("MAX_INPUT_LENGTH", "2000")
        settings = Settings()
        assert settings.max_input_length == 2000

    def test_llm_timeout_from_env(self, monkeypatch):
        monkeypatch.setenv("LLM_TIMEOUT", "60")
        settings = Settings()
        assert settings.llm_timeout == 60


class TestGetSettings:
    """get_settings() should be a cached singleton."""

    def test_get_settings_returns_settings_instance(self):
        result = get_settings()
        assert isinstance(result, Settings)

    def test_get_settings_is_singleton(self):
        result1 = get_settings()
        result2 = get_settings()
        assert result1 is result2
