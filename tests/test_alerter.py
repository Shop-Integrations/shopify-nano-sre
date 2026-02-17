"""Tests for the alerter module."""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, Mock, patch

import pytest

from nano_sre.agent.alerter import AlertChannel, Alerter, AlertRateLimiter
from nano_sre.agent.core import SkillResult


@pytest.fixture
def sample_skill_result():
    """Create a sample skill result for testing."""
    return SkillResult(
        skill_name="test_skill",
        status="PASS",
        summary="Test completed successfully",
        details={"test": "data"},
        screenshots=[],
        timestamp=datetime(2026, 2, 17, 12, 0, 0),
    )


@pytest.fixture
def fail_skill_result():
    """Create a failed skill result for testing."""
    return SkillResult(
        skill_name="test_skill",
        status="FAIL",
        summary="Test failed",
        error="Something went wrong",
        details={"test": "data"},
        screenshots=["screenshot1.png", "screenshot2.png"],
        timestamp=datetime(2026, 2, 17, 12, 0, 0),
    )


@pytest.fixture
def warn_skill_result():
    """Create a warning skill result for testing."""
    return SkillResult(
        skill_name="test_skill",
        status="WARN",
        summary="Test completed with warnings",
        details={"test": "data"},
        screenshots=[],
        timestamp=datetime(2026, 2, 17, 12, 0, 0),
    )


class TestAlertRateLimiter:
    """Test rate limiting functionality."""

    def test_rate_limiter_creation(self):
        """Test rate limiter initialization."""
        limiter = AlertRateLimiter()
        assert limiter.default_cooldown_seconds == 3600
        assert len(limiter.cache) == 0

    def test_first_alert_always_sent(self):
        """Test that first alert is always sent."""
        limiter = AlertRateLimiter()
        assert limiter.should_send_alert("test_key") is True

    def test_rate_limiting_within_cooldown(self):
        """Test that alerts within cooldown are blocked."""
        limiter = AlertRateLimiter(default_cooldown_seconds=60)
        assert limiter.should_send_alert("test_key") is True
        assert limiter.should_send_alert("test_key") is False

    def test_rate_limiting_after_cooldown(self):
        """Test that alerts after cooldown are allowed."""
        limiter = AlertRateLimiter(default_cooldown_seconds=1)
        limiter.should_send_alert("test_key")

        # Manually set the timestamp to be in the past
        limiter.cache["test_key"] = datetime.now(timezone.utc) - timedelta(seconds=2)

        assert limiter.should_send_alert("test_key") is True

    def test_custom_cooldown(self):
        """Test custom cooldown override."""
        limiter = AlertRateLimiter(default_cooldown_seconds=3600)
        limiter.should_send_alert("test_key", cooldown_seconds=1)

        # Set timestamp in the past
        limiter.cache["test_key"] = datetime.now(timezone.utc) - timedelta(seconds=2)

        assert limiter.should_send_alert("test_key", cooldown_seconds=1) is True

    def test_different_keys_independent(self):
        """Test that different alert keys are independent."""
        limiter = AlertRateLimiter()
        assert limiter.should_send_alert("key1") is True
        assert limiter.should_send_alert("key2") is True
        assert limiter.should_send_alert("key1") is False
        assert limiter.should_send_alert("key2") is False

    def test_clear_cache(self):
        """Test clearing the rate limit cache."""
        limiter = AlertRateLimiter()
        limiter.should_send_alert("test_key")
        assert len(limiter.cache) == 1

        limiter.clear_cache()
        assert len(limiter.cache) == 0


class TestAlerter:
    """Test alerter functionality."""

    def test_alerter_creation(self):
        """Test alerter initialization."""
        alerter = Alerter()
        assert alerter.rate_limiter is not None
        assert alerter.rate_limiter.default_cooldown_seconds == 3600

    def test_alerter_custom_rate_limit(self):
        """Test alerter with custom rate limit."""
        alerter = Alerter(rate_limit_seconds=1800)
        assert alerter.rate_limiter.default_cooldown_seconds == 1800

    def test_get_alert_key(self, sample_skill_result):
        """Test alert key generation."""
        alerter = Alerter()
        key = alerter._get_alert_key(sample_skill_result)
        assert key == "test_skill:PASS"

    def test_get_status_color_pass(self):
        """Test color code for PASS status."""
        alerter = Alerter()
        assert alerter._get_status_color("PASS") == 0x00FF00

    def test_get_status_color_warn(self):
        """Test color code for WARN status."""
        alerter = Alerter()
        assert alerter._get_status_color("WARN") == 0xFFFF00

    def test_get_status_color_fail(self):
        """Test color code for FAIL status."""
        alerter = Alerter()
        assert alerter._get_status_color("FAIL") == 0xFF0000

    def test_get_status_color_unknown(self):
        """Test color code for unknown status."""
        alerter = Alerter()
        assert alerter._get_status_color("UNKNOWN") == 0x808080

    def test_get_status_emoji_pass(self):
        """Test emoji for PASS status."""
        alerter = Alerter()
        assert alerter._get_status_emoji("PASS") == "✅"

    def test_get_status_emoji_warn(self):
        """Test emoji for WARN status."""
        alerter = Alerter()
        assert alerter._get_status_emoji("WARN") == "⚠️"

    def test_get_status_emoji_fail(self):
        """Test emoji for FAIL status."""
        alerter = Alerter()
        assert alerter._get_status_emoji("FAIL") == "❌"

    def test_format_discord_embed_pass(self, sample_skill_result):
        """Test Discord embed formatting for PASS status."""
        alerter = Alerter()
        payload = alerter._format_discord_embed(
            sample_skill_result, store_url="https://test.myshopify.com"
        )

        assert "embeds" in payload
        assert len(payload["embeds"]) == 1

        embed = payload["embeds"][0]
        assert embed["title"] == "✅ test_skill"
        assert embed["description"] == "Test completed successfully"
        assert embed["color"] == 0x00FF00
        assert "footer" not in embed  # No CTA for PASS

    def test_format_discord_embed_fail(self, fail_skill_result):
        """Test Discord embed formatting for FAIL status."""
        alerter = Alerter()
        payload = alerter._format_discord_embed(fail_skill_result)

        embed = payload["embeds"][0]
        assert embed["title"] == "❌ test_skill"
        assert embed["color"] == 0xFF0000
        assert "footer" in embed
        assert "shopintegrations.com" in embed["footer"]["text"]

        # Check that error field is present
        error_field = next((f for f in embed["fields"] if f["name"] == "Error"), None)
        assert error_field is not None
        assert "Something went wrong" in error_field["value"]

    def test_format_discord_embed_with_store_url(self, sample_skill_result):
        """Test Discord embed includes store URL."""
        alerter = Alerter()
        store_url = "https://test.myshopify.com"
        payload = alerter._format_discord_embed(sample_skill_result, store_url)

        embed = payload["embeds"][0]
        store_field = next((f for f in embed["fields"] if f["name"] == "Store"), None)
        assert store_field is not None
        assert store_url in store_field["value"]

    def test_format_slack_blocks_pass(self, sample_skill_result):
        """Test Slack Block Kit formatting for PASS status."""
        alerter = Alerter()
        payload = alerter._format_slack_blocks(
            sample_skill_result, store_url="https://test.myshopify.com"
        )

        assert "blocks" in payload
        blocks = payload["blocks"]

        # Check header block
        header = blocks[0]
        assert header["type"] == "header"
        assert "✅ test_skill" in header["text"]["text"]

        # Check that no CTA context block is present for PASS
        context_blocks = [b for b in blocks if b["type"] == "context"]
        assert len(context_blocks) == 0

    def test_format_slack_blocks_fail(self, fail_skill_result):
        """Test Slack Block Kit formatting for FAIL status."""
        alerter = Alerter()
        payload = alerter._format_slack_blocks(fail_skill_result)

        blocks = payload["blocks"]

        # Check header block
        header = blocks[0]
        assert "❌ test_skill" in header["text"]["text"]

        # Check for CTA context block
        context_blocks = [b for b in blocks if b["type"] == "context"]
        assert len(context_blocks) > 0
        assert "shopintegrations.com" in str(context_blocks[0])

        # Check for error section
        error_sections = [
            b
            for b in blocks
            if b["type"] == "section" and "Error:" in b.get("text", {}).get("text", "")
        ]
        assert len(error_sections) > 0

    def test_format_slack_blocks_with_store_url(self, sample_skill_result):
        """Test Slack Block Kit includes store URL."""
        alerter = Alerter()
        store_url = "https://test.myshopify.com"
        payload = alerter._format_slack_blocks(sample_skill_result, store_url)

        blocks = payload["blocks"]
        store_blocks = [
            b
            for b in blocks
            if b["type"] == "section"
            and "Store:" in b.get("text", {}).get("text", "")
        ]
        assert len(store_blocks) > 0
        assert store_url in store_blocks[0]["text"]["text"]

    def test_format_stdout(self, sample_skill_result):
        """Test stdout formatting."""
        alerter = Alerter()
        output = alerter._format_stdout(
            sample_skill_result, store_url="https://test.myshopify.com"
        )

        assert "test_skill" in output
        assert "PASS" in output
        assert "Test completed successfully" in output
        assert "https://test.myshopify.com" in output
        assert "=" * 80 in output

    def test_format_stdout_fail(self, fail_skill_result):
        """Test stdout formatting for FAIL status."""
        alerter = Alerter()
        output = alerter._format_stdout(fail_skill_result)

        assert "FAIL" in output
        assert "Something went wrong" in output
        assert "shopintegrations.com" in output
        assert "screenshot1.png" in output or "screenshot2.png" in output

    @pytest.mark.asyncio
    async def test_send_alert_stdout(self, sample_skill_result, capsys):
        """Test sending alert to stdout."""
        alerter = Alerter()
        result = await alerter.send_alert(
            AlertChannel.STDOUT,
            sample_skill_result,
            rate_limit=False,
        )

        assert result is True
        captured = capsys.readouterr()
        assert "test_skill" in captured.out
        assert "PASS" in captured.out

    @pytest.mark.asyncio
    async def test_send_alert_discord_success(self, sample_skill_result):
        """Test sending alert to Discord webhook successfully."""
        alerter = Alerter()

        mock_response = Mock()
        mock_response.status_code = 200

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response

            async with alerter:
                result = await alerter.send_alert(
                    AlertChannel.DISCORD,
                    sample_skill_result,
                    webhook_url="https://discord.com/api/webhooks/test",
                    rate_limit=False,
                )

            assert result is True
            mock_post.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_alert_discord_failure(self, sample_skill_result):
        """Test Discord webhook failure."""
        alerter = Alerter()

        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.text = "Bad Request"

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response

            async with alerter:
                result = await alerter.send_alert(
                    AlertChannel.DISCORD,
                    sample_skill_result,
                    webhook_url="https://discord.com/api/webhooks/test",
                    rate_limit=False,
                )

            assert result is False

    @pytest.mark.asyncio
    async def test_send_alert_discord_no_url(self, sample_skill_result):
        """Test Discord alert without webhook URL."""
        alerter = Alerter()
        result = await alerter.send_alert(
            AlertChannel.DISCORD,
            sample_skill_result,
            rate_limit=False,
        )

        assert result is False

    @pytest.mark.asyncio
    async def test_send_alert_slack_success(self, sample_skill_result):
        """Test sending alert to Slack webhook successfully."""
        alerter = Alerter()

        mock_response = Mock()
        mock_response.status_code = 200

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response

            async with alerter:
                result = await alerter.send_alert(
                    AlertChannel.SLACK,
                    sample_skill_result,
                    webhook_url="https://hooks.slack.com/services/test",
                    rate_limit=False,
                )

            assert result is True
            mock_post.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_alert_slack_failure(self, sample_skill_result):
        """Test Slack webhook failure."""
        alerter = Alerter()

        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response

            async with alerter:
                result = await alerter.send_alert(
                    AlertChannel.SLACK,
                    sample_skill_result,
                    webhook_url="https://hooks.slack.com/services/test",
                    rate_limit=False,
                )

            assert result is False

    @pytest.mark.asyncio
    async def test_send_alert_slack_no_url(self, sample_skill_result):
        """Test Slack alert without webhook URL."""
        alerter = Alerter()
        result = await alerter.send_alert(
            AlertChannel.SLACK,
            sample_skill_result,
            rate_limit=False,
        )

        assert result is False

    @pytest.mark.asyncio
    async def test_send_alert_rate_limiting(self, sample_skill_result):
        """Test that rate limiting works."""
        alerter = Alerter(rate_limit_seconds=60)

        # First alert should go through
        result1 = await alerter.send_alert(
            AlertChannel.STDOUT,
            sample_skill_result,
            rate_limit=True,
        )
        assert result1 is True

        # Second alert should be blocked
        result2 = await alerter.send_alert(
            AlertChannel.STDOUT,
            sample_skill_result,
            rate_limit=True,
        )
        assert result2 is False

    @pytest.mark.asyncio
    async def test_send_alert_rate_limiting_different_status(
        self, sample_skill_result, fail_skill_result
    ):
        """Test that rate limiting is per skill+status combination."""
        alerter = Alerter()

        # PASS alert should go through
        result1 = await alerter.send_alert(
            AlertChannel.STDOUT,
            sample_skill_result,
            rate_limit=True,
        )
        assert result1 is True

        # FAIL alert should also go through (different status)
        result2 = await alerter.send_alert(
            AlertChannel.STDOUT,
            fail_skill_result,
            rate_limit=True,
        )
        assert result2 is True

    @pytest.mark.asyncio
    async def test_send_alert_rate_limiting_disabled(self, sample_skill_result):
        """Test that alerts are not rate limited when disabled."""
        alerter = Alerter()

        result1 = await alerter.send_alert(
            AlertChannel.STDOUT,
            sample_skill_result,
            rate_limit=False,
        )
        assert result1 is True

        result2 = await alerter.send_alert(
            AlertChannel.STDOUT,
            sample_skill_result,
            rate_limit=False,
        )
        assert result2 is True

    @pytest.mark.asyncio
    async def test_send_alert_exception_handling(self, sample_skill_result):
        """Test that exceptions are caught and logged."""
        alerter = Alerter()

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.side_effect = Exception("Network error")

            async with alerter:
                result = await alerter.send_alert(
                    AlertChannel.DISCORD,
                    sample_skill_result,
                    webhook_url="https://discord.com/api/webhooks/test",
                    rate_limit=False,
                )

            assert result is False

    @pytest.mark.asyncio
    async def test_context_manager(self):
        """Test async context manager."""
        alerter = Alerter()

        async with alerter as a:
            assert a.http_client is not None

        # After exiting, the client should be closed
        # (we can't easily test this without accessing private state)

    @pytest.mark.asyncio
    async def test_send_alert_without_context_manager(self, sample_skill_result):
        """Test sending alerts without using context manager."""
        alerter = Alerter()

        mock_response = Mock()
        mock_response.status_code = 200

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.post.return_value = mock_response
            mock_client_class.return_value = mock_client

            result = await alerter.send_alert(
                AlertChannel.DISCORD,
                sample_skill_result,
                webhook_url="https://discord.com/api/webhooks/test",
                rate_limit=False,
            )

            assert result is True
