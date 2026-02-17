"""Tests for the privacy module."""

from nano_sre.agent.privacy import Redactor, ScreenshotBlurrer


def test_redactor_creation():
    """Test Redactor initialization."""
    redactor = Redactor()
    assert redactor is not None
    assert redactor.REDACTION_MARKER == "[REDACTED]"


def test_redact_email():
    """Test email redaction."""
    redactor = Redactor()
    text = "Contact us at support@example.com for help"
    redacted = redactor.redact_text(text, enabled=True)

    assert "support@example.com" not in redacted
    assert "[REDACTED]" in redacted


def test_redaction_disabled():
    """Test that redaction is skipped when disabled."""
    redactor = Redactor()
    text = "Contact us at support@example.com for help"
    redacted = redactor.redact_text(text, enabled=False)

    assert redacted == text


def test_redact_api_key():
    """Test API key redaction."""
    redactor = Redactor()
    text = 'api_key="sk_test_1234567890"'
    redacted = redactor.redact_text(text, enabled=True)

    assert "sk_test_1234567890" not in redacted
    assert "[REDACTED]" in redacted


def test_redact_dict():
    """Test dictionary redaction."""
    redactor = Redactor()
    data = {
        "user": "john@example.com",
        "api_key": "secret123",
        "nested": {"email": "admin@example.com"},
    }
    redacted = redactor.redact_dict(data, enabled=True)

    assert "[REDACTED]" in str(redacted)
    assert "john@example.com" not in str(redacted)


def test_screenshot_blurrer_creation():
    """Test ScreenshotBlurrer initialization."""
    blurrer = ScreenshotBlurrer()
    assert blurrer is not None
