"""Unit tests for AI provider selection."""

from app.core.config import Settings
from app.services.ai_service import resolve_ai_provider_chain


def test_auto_prefers_anthropic_then_openai():
    settings = Settings(
        secret_key="x" * 32,
        database_url="sqlite+aiosqlite:///:memory:",
        anthropic_api_key="sk-ant-test",
        openai_api_key="sk-openai-test",
        ai_provider="auto",
    )
    assert resolve_ai_provider_chain(settings) == ["anthropic", "openai"]


def test_auto_openai_only():
    settings = Settings(
        secret_key="x" * 32,
        database_url="sqlite+aiosqlite:///:memory:",
        openai_api_key="sk-openai-test",
        ai_provider="auto",
    )
    assert resolve_ai_provider_chain(settings) == ["openai"]


def test_forced_openai_ignores_anthropic():
    settings = Settings(
        secret_key="x" * 32,
        database_url="sqlite+aiosqlite:///:memory:",
        anthropic_api_key="sk-ant-test",
        openai_api_key="sk-openai-test",
        ai_provider="openai",
    )
    assert resolve_ai_provider_chain(settings) == ["openai"]


def test_ai_configured_when_either_key_present():
    settings = Settings(
        secret_key="x" * 32,
        database_url="sqlite+aiosqlite:///:memory:",
        openai_api_key="sk-openai-test",
    )
    assert settings.ai_configured is True
