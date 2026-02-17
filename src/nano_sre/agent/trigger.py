"""Scheduler and webhook trigger system for agent execution."""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


class IntervalTrigger:
    """CRON-like interval-based trigger."""

    def __init__(self, interval_minutes: int):
        """
        Initialize interval trigger.

        Args:
            interval_minutes: Minutes between trigger fires.
        """
        self.interval_minutes = interval_minutes
        self.last_triggered: Optional[datetime] = None

    def should_trigger(self) -> bool:
        """Check if trigger should fire."""
        now = datetime.utcnow()
        if self.last_triggered is None:
            return True

        elapsed = now - self.last_triggered
        return elapsed >= timedelta(minutes=self.interval_minutes)

    def mark_triggered(self) -> None:
        """Mark that trigger has fired."""
        self.last_triggered = datetime.utcnow()

    async def wait_until_next(self) -> None:
        """Async wait until next trigger time."""
        if self.last_triggered is None:
            return

        now = datetime.utcnow()
        next_trigger = self.last_triggered + timedelta(minutes=self.interval_minutes)
        wait_seconds = (next_trigger - now).total_seconds()

        if wait_seconds > 0:
            await asyncio.sleep(wait_seconds)


class WebhookTrigger:
    """Webhook receiver for GitHub Deployment events."""

    def __init__(self, port: int = 8000):
        """
        Initialize webhook trigger.

        Args:
            port: Port to listen on.
        """
        self.port = port
        self.events: list[dict[str, Any]] = []
        self.handlers: list[Callable[[dict[str, Any]], None]] = []

    def register_handler(self, handler: Callable[[dict[str, Any]], None]) -> None:
        """Register a callback handler for webhook events."""
        self.handlers.append(handler)

    def normalize_github_deployment(self, payload: dict[str, Any]) -> dict[str, Any]:
        """
        Normalize GitHub Deployment event into trigger context.

        Args:
            payload: Raw GitHub webhook payload.

        Returns:
            Normalized context dict.
        """
        deployment = payload.get("deployment", {})
        repository = payload.get("repository", {})

        return {
            "trigger_type": "github_deployment",
            "environment": deployment.get("environment"),
            "ref": deployment.get("ref"),
            "sha": deployment.get("sha"),
            "repository": repository.get("full_name"),
            "created_at": datetime.utcnow().isoformat(),
            "original_payload": payload,
        }

    async def receive_webhook(self, payload: dict[str, Any]) -> None:
        """
        Handle incoming webhook.

        Args:
            payload: Webhook payload dict.
        """
        logger.info(f"Received webhook: {payload.get('action', 'unknown')}")
        self.events.append(payload)

        # Normalize and dispatch to handlers
        context = self.normalize_github_deployment(payload)
        for handler in self.handlers:
            try:
                handler(context)
            except Exception as e:
                logger.exception(f"Error in webhook handler: {e}")

    def pop_event(self) -> Optional[dict[str, Any]]:
        """Pop the next pending event, if any."""
        return self.events.pop(0) if self.events else None

    def has_pending_events(self) -> bool:
        """Check if there are pending events."""
        return len(self.events) > 0


class TriggerManager:
    """Manages multiple trigger types."""

    def __init__(self, interval_minutes: int, webhook_port: int = 8000):
        """
        Initialize trigger manager.

        Args:
            interval_minutes: Interval for scheduled checks.
            webhook_port: Port for webhook receiver.
        """
        self.interval = IntervalTrigger(interval_minutes)
        self.webhook = WebhookTrigger(webhook_port)
        self.queue: list[dict[str, Any]] = []

    def add_interval_trigger(self) -> None:
        """Add interval-based trigger to queue."""
        if self.interval.should_trigger():
            self.queue.append(
                {
                    "type": "interval",
                    "timestamp": datetime.utcnow().isoformat(),
                }
            )
            self.interval.mark_triggered()

    def add_webhook_event(self) -> None:
        """Check for pending webhook events."""
        if self.webhook.has_pending_events():
            event = self.webhook.pop_event()
            if event:
                self.queue.append(self.webhook.normalize_github_deployment(event))

    async def wait_for_trigger(self) -> dict[str, Any]:
        """
        Wait for next trigger event.

        Returns:
            Trigger context dict.
        """
        # Check both triggers
        self.add_interval_trigger()
        self.add_webhook_event()

        # If we have events, return immediately
        if self.queue:
            return self.queue.pop(0)

        # Otherwise wait for interval
        await self.interval.wait_until_next()
        self.add_interval_trigger()

        if self.queue:
            return self.queue.pop(0)

        # Fallback
        return {
            "type": "fallback",
            "timestamp": datetime.utcnow().isoformat(),
        }

    async def trigger_loop(self, callback: Callable[[dict[str, Any]], Any]) -> None:
        """
        Run trigger loop indefinitely.

        Args:
            callback: Async callback to invoke on trigger.
        """
        while True:
            try:
                trigger_context = await self.wait_for_trigger()
                logger.info(f"Trigger fired: {trigger_context.get('type')}")
                await callback(trigger_context)
            except KeyboardInterrupt:
                logger.info("Trigger loop interrupted")
                break
            except Exception as e:
                logger.exception(f"Error in trigger loop: {e}")
                await asyncio.sleep(60)
