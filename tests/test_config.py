"""Tests for the agent configuration."""

from nano_sre.config.settings import Settings


def test_settings_creation():
    """Test Settings object creation."""
    settings = Settings(
        store_url="https://test.myshopify.com",
        shopify_admin_api_key="test_key",
        llm_provider="openai",
        llm_api_key="test_llm_key",
        llm_model="gpt-4",
        alert_webhook_url="https://example.com/webhook",
        check_interval_minutes=5,
        sqlite_db_path=":memory:",
        redact_pii=True,
        screenshot_blur_enabled=True,
    )

    assert str(settings.store_url) == "https://test.myshopify.com/"
    assert settings.shopify_admin_api_key == "test_key"
    assert settings.llm_provider == "openai"
    assert settings.llm_model == "gpt-4"
    assert settings.redact_pii is True
    assert settings.screenshot_blur_enabled is True


def test_settings_defaults():
    """Test Settings default values."""
    settings = Settings(
        store_url="https://test.myshopify.com",
        shopify_admin_api_key="test_key",
        llm_provider="openai",
        llm_api_key="test_llm_key",
        llm_model="gpt-4",
        alert_webhook_url="https://example.com/webhook",
        check_interval_minutes=5,
        sqlite_db_path=":memory:",
    )

    # Defaults for privacy settings should be False
    assert settings.redact_pii is False
    assert settings.screenshot_blur_enabled is False
    assert settings.check_interval_minutes == 5
    assert settings.llm_provider == "openai"


def test_settings_url_normalization():
    """Test that URLs are normalized properly."""
    settings = Settings(
        store_url="test.myshopify.com",
        llm_api_key="test",
    )

    # URL should be normalized to HTTPS
    assert "https://" in str(settings.store_url)
