"""Alert notification system supporting Discord, Slack, and stdout channels."""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

import httpx

from nano_sre.agent.core import SkillResult

logger = logging.getLogger(__name__)


class AlertChannel(Enum):
    """Supported alert notification channels."""

    DISCORD = "discord"
    SLACK = "slack"
    STDOUT = "stdout"


@dataclass
class AlertRateLimiter:
    """Rate limiter for duplicate alerts."""

    cache: dict[str, datetime] = field(default_factory=dict)
    default_cooldown_seconds: int = 3600  # 1 hour default

    def should_send_alert(
        self, alert_key: str, cooldown_seconds: Optional[int] = None
    ) -> bool:
        """
        Check if an alert should be sent based on rate limiting.

        Args:
            alert_key: Unique identifier for the alert (e.g., skill_name + status)
            cooldown_seconds: Custom cooldown period, defaults to 1 hour

        Returns:
            True if alert should be sent, False if within cooldown period
        """
        cooldown = cooldown_seconds or self.default_cooldown_seconds
        now = datetime.now(timezone.utc)

        if alert_key not in self.cache:
            self.cache[alert_key] = now
            return True

        last_sent = self.cache[alert_key]
        time_since_last = (now - last_sent).total_seconds()

        if time_since_last >= cooldown:
            self.cache[alert_key] = now
            return True

        logger.debug(
            f"Alert rate limited: {alert_key} "
            f"(sent {time_since_last:.0f}s ago, cooldown: {cooldown}s)"
        )
        return False

    def clear_cache(self) -> None:
        """Clear the rate limit cache."""
        self.cache.clear()


class Alerter:
    """Alert notification handler for multiple channels."""

    def __init__(self, rate_limit_seconds: int = 3600):
        """
        Initialize the Alerter.

        Args:
            rate_limit_seconds: Default rate limit cooldown in seconds (default: 1 hour)
        """
        self.rate_limiter = AlertRateLimiter(default_cooldown_seconds=rate_limit_seconds)
        self.http_client: Optional[httpx.AsyncClient] = None

    async def __aenter__(self):
        """Async context manager entry."""
        self.http_client = httpx.AsyncClient(timeout=30.0)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.http_client:
            await self.http_client.aclose()

    def _get_alert_key(self, skill_result: SkillResult) -> str:
        """Generate a unique key for rate limiting."""
        return f"{skill_result.skill_name}:{skill_result.status}"

    def _get_status_color(self, status: str) -> int:
        """
        Get Discord embed color based on status.

        Args:
            status: Status string (PASS, WARN, FAIL)

        Returns:
            Discord color code as integer
        """
        colors = {
            "PASS": 0x00FF00,  # Green
            "WARN": 0xFFFF00,  # Yellow
            "FAIL": 0xFF0000,  # Red
        }
        return colors.get(status, 0x808080)  # Gray for unknown

    def _get_status_emoji(self, status: str) -> str:
        """
        Get emoji for status.

        Args:
            status: Status string (PASS, WARN, FAIL)

        Returns:
            Emoji string
        """
        emojis = {
            "PASS": "✅",
            "WARN": "⚠️",
            "FAIL": "❌",
        }
        return emojis.get(status, "ℹ️")

    def _format_discord_embed(
        self, skill_result: SkillResult, store_url: Optional[str] = None
    ) -> dict[str, Any]:
        """
        Format Discord webhook payload with embeds.

        Args:
            skill_result: Skill execution result
            store_url: Optional store URL to include

        Returns:
            Discord webhook payload
        """
        color = self._get_status_color(skill_result.status)
        emoji = self._get_status_emoji(skill_result.status)

        embed = {
            "title": f"{emoji} {skill_result.skill_name}",
            "description": skill_result.summary,
            "color": color,
            "timestamp": skill_result.timestamp.isoformat(),
            "fields": [],
        }

        # Add status field
        embed["fields"].append(
            {
                "name": "Status",
                "value": skill_result.status,
                "inline": True,
            }
        )

        # Add store URL if provided
        if store_url:
            embed["fields"].append(
                {
                    "name": "Store",
                    "value": f"[Open Store]({store_url})",
                    "inline": True,
                }
            )

        # Add error details if present
        if skill_result.error:
            embed["fields"].append(
                {
                    "name": "Error",
                    "value": skill_result.error[:1024],  # Discord field limit
                    "inline": False,
                }
            )

        # Add CTA for FAIL status
        if skill_result.status == "FAIL":
            embed["footer"] = {
                "text": "Need help? → shopintegrations.com",
            }

        payload = {"embeds": [embed]}

        # Note: Screenshot attachments would require uploading to a hosting service
        # and including the URL in the embed's image field. This is a basic implementation.
        if skill_result.screenshots:
            logger.debug(
                f"Screenshots available but not attached: {len(skill_result.screenshots)}"
            )

        return payload

    def _format_slack_blocks(
        self, skill_result: SkillResult, store_url: Optional[str] = None
    ) -> dict[str, Any]:
        """
        Format Slack webhook payload with Block Kit.

        Args:
            skill_result: Skill execution result
            store_url: Optional store URL to include

        Returns:
            Slack webhook payload
        """
        emoji = self._get_status_emoji(skill_result.status)
        timestamp = int(skill_result.timestamp.timestamp())

        blocks = [
            # Header with emoji and skill name
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"{emoji} {skill_result.skill_name}",
                },
            },
            # Summary section
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*Status:*\n{skill_result.status}",
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Timestamp:*\n<!date^{timestamp}^{{date_short_pretty}} {{time}}|{skill_result.timestamp.isoformat()}>",
                    },
                ],
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Summary:*\n{skill_result.summary}",
                },
            },
        ]

        # Add store URL if provided
        if store_url:
            blocks.append(
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*Store:* <{store_url}|Open Store>",
                    },
                }
            )

        # Add error details if present
        if skill_result.error:
            blocks.append(
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*Error:*\n```{skill_result.error[:2000]}```",  # Slack limit
                    },
                }
            )

        # Add CTA for FAIL status
        if skill_result.status == "FAIL":
            blocks.append(
                {
                    "type": "context",
                    "elements": [
                        {
                            "type": "mrkdwn",
                            "text": "Need help? → shopintegrations.com",
                        }
                    ],
                }
            )

        payload = {"blocks": blocks}

        # Note: Screenshots would require uploading and including in image blocks
        if skill_result.screenshots:
            logger.debug(
                f"Screenshots available but not attached: {len(skill_result.screenshots)}"
            )

        return payload

    def _format_stdout(
        self, skill_result: SkillResult, store_url: Optional[str] = None
    ) -> str:
        """
        Format alert for stdout output.

        Args:
            skill_result: Skill execution result
            store_url: Optional store URL to include

        Returns:
            Formatted string for stdout
        """
        emoji = self._get_status_emoji(skill_result.status)
        lines = [
            "=" * 80,
            f"{emoji} ALERT: {skill_result.skill_name}",
            "=" * 80,
            f"Status:    {skill_result.status}",
            f"Timestamp: {skill_result.timestamp.isoformat()}",
            f"Summary:   {skill_result.summary}",
        ]

        if store_url:
            lines.append(f"Store:     {store_url}")

        if skill_result.error:
            lines.append(f"Error:     {skill_result.error}")

        if skill_result.screenshots:
            lines.append(f"Screenshots: {len(skill_result.screenshots)} available")
            for i, screenshot in enumerate(skill_result.screenshots[:3], 1):
                lines.append(f"  [{i}] {screenshot}")

        if skill_result.status == "FAIL":
            lines.append("")
            lines.append("Need help? → shopintegrations.com")

        lines.append("=" * 80)

        return "\n".join(lines)

    async def send_alert(
        self,
        channel: AlertChannel,
        skill_result: SkillResult,
        webhook_url: Optional[str] = None,
        store_url: Optional[str] = None,
        rate_limit: bool = True,
        rate_limit_seconds: Optional[int] = None,
    ) -> bool:
        """
        Send an alert notification.

        Args:
            channel: Alert channel to use (Discord, Slack, or stdout)
            skill_result: Skill execution result to alert on
            webhook_url: Webhook URL for Discord/Slack (required for those channels)
            store_url: Optional store URL to include in the alert
            rate_limit: Whether to apply rate limiting (default: True)
            rate_limit_seconds: Custom rate limit cooldown in seconds

        Returns:
            True if alert was sent successfully, False otherwise
        """
        # Check rate limiting
        if rate_limit:
            alert_key = self._get_alert_key(skill_result)
            if not self.rate_limiter.should_send_alert(alert_key, rate_limit_seconds):
                logger.info(f"Alert rate limited for {alert_key}")
                return False

        try:
            if channel == AlertChannel.STDOUT:
                message = self._format_stdout(skill_result, store_url)
                print(message)
                logger.info(f"Alert sent to stdout for {skill_result.skill_name}")
                return True

            elif channel == AlertChannel.DISCORD:
                if not webhook_url:
                    logger.error("Discord webhook URL is required")
                    return False

                payload = self._format_discord_embed(skill_result, store_url)
                if not self.http_client:
                    async with httpx.AsyncClient(timeout=30.0) as client:
                        response = await client.post(webhook_url, json=payload)
                else:
                    response = await self.http_client.post(webhook_url, json=payload)

                if response.status_code in (200, 204):
                    logger.info(
                        f"Alert sent to Discord for {skill_result.skill_name}"
                    )
                    return True
                else:
                    logger.error(
                        f"Discord webhook failed: {response.status_code} - {response.text}"
                    )
                    return False

            elif channel == AlertChannel.SLACK:
                if not webhook_url:
                    logger.error("Slack webhook URL is required")
                    return False

                payload = self._format_slack_blocks(skill_result, store_url)
                if not self.http_client:
                    async with httpx.AsyncClient(timeout=30.0) as client:
                        response = await client.post(webhook_url, json=payload)
                else:
                    response = await self.http_client.post(webhook_url, json=payload)

                if response.status_code == 200:
                    logger.info(
                        f"Alert sent to Slack for {skill_result.skill_name}"
                    )
                    return True
                else:
                    logger.error(
                        f"Slack webhook failed: {response.status_code} - {response.text}"
                    )
                    return False

            else:
                logger.error(f"Unsupported alert channel: {channel}")
                return False

        except Exception as e:
            logger.exception(f"Error sending alert to {channel.value}: {e}")
            return False
