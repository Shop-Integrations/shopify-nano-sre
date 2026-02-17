"""Data privacy, redaction, and PII handling utilities."""

import hashlib
import logging
import re
from typing import Any, Optional

logger = logging.getLogger(__name__)


class Redactor:
    """Handles redaction of sensitive data from logs and reports."""

    # Patterns for common sensitive data
    PATTERNS: dict[str, re.Pattern[str]] = {
        "api_key": re.compile(
            r"(?:api[_-]?key|apikey|api_secret)\s*[:=]\s*['\"]?([a-zA-Z0-9_\-]+)['\"]?",
            re.IGNORECASE,
        ),
        "bearer_token": re.compile(
            r"(?:bearer|authorization)\s*[:=]\s*['\"]?Bearer\s+([a-zA-Z0-9_\-.]+)['\"]?",
            re.IGNORECASE,
        ),
        "shopify_token": re.compile(
            r"(?:shopify[_-]?token|x[_-]?shopify[_-]?access[_-]?token)\s*[:=]\s*['\"]?([a-zA-Z0-9_\-]+)['\"]?",
            re.IGNORECASE,
        ),
        "email": re.compile(r"(?:[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})"),
        "phone": re.compile(r"(?:\+?1\s?)?(?:\(\d{3}\)[\s.-]?)?\d{3}[\s.-]?\d{4}"),
        "credit_card": re.compile(r"\b(?:\d{4}[\s-]?){3}\d{4}\b"),
        "url_credentials": re.compile(r"https?://[^:]+:([^@]+)@"),
    }

    REDACTION_MARKER = "[REDACTED]"

    def redact_text(self, text: str, enabled: bool = True) -> str:
        """
        Redact sensitive data from text.

        Args:
            text: Text to redact.
            enabled: Whether redaction is enabled.

        Returns:
            Redacted text.
        """
        if not enabled or not text:
            return text

        result = text
        for pattern_name, pattern in self.PATTERNS.items():
            result = pattern.sub(self._replace_match, result)

        return result

    def _replace_match(self, match: re.Match[str]) -> str:
        """Replace sensitive data with marker."""
        # If there's a capture group, redact just that
        if match.groups():
            prefix = match.group(0)[: match.start(1) - match.start(0)]
            return prefix + self.REDACTION_MARKER
        # Otherwise redact the whole match
        return self.REDACTION_MARKER

    def redact_dict(self, data: dict[str, Any], enabled: bool = True) -> dict[str, Any]:
        """
        Redact sensitive data from dictionary.

        Args:
            data: Dictionary to redact.
            enabled: Whether redaction is enabled.

        Returns:
            Dictionary with redacted values.
        """
        if not enabled:
            return data

        result: dict[str, Any] = {}
        for key, value in data.items():
            if isinstance(value, str):
                result[key] = self.redact_text(value, enabled=True)
            elif isinstance(value, dict):
                result[key] = self.redact_dict(value, enabled=True)
            elif isinstance(value, list):
                result[key] = [
                    self.redact_text(item, enabled=True) if isinstance(item, str) else item
                    for item in value
                ]
            else:
                result[key] = value
        return result


class ScreenshotBlurrer:
    """
    Handles blurring of PII in screenshots.

    Note: This is a placeholder for more sophisticated image processing.
    In production, you would use PIL/Pillow or similar for actual image manipulation.
    """

    def __init__(self, enabled: bool = False):
        """Initialize screenshot blurrer."""
        self.enabled = enabled

    def blur_selectors(self, image_path: str, selectors: list[str]) -> Optional[str]:
        """
        Blur elements matching selectors in a screenshot.

        Args:
            image_path: Path to screenshot file.
            selectors: CSS selectors of elements to blur.

        Returns:
            Path to blurred image, or None if not enabled.
        """
        if not self.enabled:
            return image_path

        # Placeholder: In production, would use Playwright's locator.screenshot()
        # or PIL to blur regions based on selector coordinates
        logger.info(f"Screenshot blur enabled for {len(selectors)} selectors")
        return image_path

    def blur_pii_patterns(
        self,
        image_path: str,
        patterns: Optional[list[str]] = None,
    ) -> Optional[str]:
        """
        Blur regions matching PII patterns.

        Args:
            image_path: Path to screenshot file.
            patterns: PII patterns to blur (email, phone, etc).

        Returns:
            Path to blurred image.
        """
        if not self.enabled:
            return image_path

        default_patterns = ["email", "phone", "credit_card"]
        patterns = patterns or default_patterns

        logger.info(f"Screenshot blur enabled for patterns: {patterns}")
        return image_path


class PrivacyConfig:
    """Privacy settings configuration."""

    def __init__(
        self,
        redact_pii: bool = False,
        screenshot_blur_enabled: bool = False,
    ):
        """
        Initialize privacy config.

        Args:
            redact_pii: Enable PII redaction in logs.
            screenshot_blur_enabled: Enable blurring in screenshots.
        """
        self.redact_pii = redact_pii
        self.screenshot_blur_enabled = screenshot_blur_enabled
        self.redactor = Redactor()
        self.blurrer = ScreenshotBlurrer(enabled=screenshot_blur_enabled)

    def hash_pii_for_metrics(self, value: str) -> str:
        """
        Hash PII for use in metrics without exposing it.

        Args:
            value: PII value to hash.

        Returns:
            SHA256 hash of the value.
        """
        return hashlib.sha256(value.encode()).hexdigest()

    def redact_log_entry(self, entry: str) -> str:
        """
        Redact a log entry.

        Args:
            entry: Log entry text.

        Returns:
            Redacted log entry.
        """
        return self.redactor.redact_text(entry, enabled=self.redact_pii)

    def redact_report_data(self, data: dict[str, Any]) -> dict[str, Any]:
        """
        Redact data for reports.

        Args:
            data: Report data dict.

        Returns:
            Data with redacted sensitive fields.
        """
        return self.redactor.redact_dict(data, enabled=self.redact_pii)
