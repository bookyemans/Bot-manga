from __future__ import annotations

from pathlib import Path

from config.settings import Settings


def test_default_gemini_models_are_current_documented_ids(monkeypatch):
    monkeypatch.setenv("MANGA_BOT_TELEGRAM_BOT_TOKEN", "test-token")
    monkeypatch.delenv("MANGA_BOT_GEMINI_MODELS", raising=False)
    settings = Settings(_env_file=None)
    models = [model.strip() for model in settings.gemini_models.split(",")]
    assert models == ["gemini-3.5-flash-lite", "gemini-3.8-flash"]
    assert not any(model.startswith("gemini-2.5-") for model in models)


def test_release_archive_configuration_documents_model_fallbacks():
    env_example = Path(__file__).resolve().parents[1] / ".env.example"
    content = env_example.read_text(encoding="utf-8")
    assert "MANGA_BOT_GEMINI_MODELS=gemini-3.5-flash-lite,gemini-3.8-flash" in content


def test_bootstrap_loads_one_settings_snapshot_and_validates_token(monkeypatch):
    from config.bootstrap import load_settings, validate_startup_settings

    monkeypatch.setenv("MANGA_BOT_TELEGRAM_BOT_TOKEN", "test-token")
    settings = load_settings(env_file=None)
    validate_startup_settings(settings)
    assert settings.telegram_bot_token == "test-token"


def test_bootstrap_rejects_placeholder_token(monkeypatch):
    import pytest
    from config.bootstrap import load_settings, validate_startup_settings

    monkeypatch.setenv("MANGA_BOT_TELEGRAM_BOT_TOKEN", "replace_me")
    settings = load_settings(env_file=None)
    with pytest.raises(RuntimeError, match="MANGA_BOT_TELEGRAM_BOT_TOKEN"):
        validate_startup_settings(settings)


def test_bootstrap_rejects_invalid_log_level(monkeypatch):
    import pytest
    from config.bootstrap import configure_logging, load_settings

    monkeypatch.setenv("MANGA_BOT_TELEGRAM_BOT_TOKEN", "test-token")
    monkeypatch.setenv("MANGA_BOT_LOG_LEVEL", "NOT_A_LEVEL")
    with pytest.raises(ValueError, match="MANGA_BOT_LOG_LEVEL"):
        configure_logging(load_settings(env_file=None))
