"""SQLite-based state management for check runs, baselines, and incidents."""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import sqlite_utils

logger = logging.getLogger(__name__)


class Store:
    """SQLite-based data store for agent state."""

    def __init__(self, db_path: str):
        """Initialize store with database file path."""
        self.db_path = Path(db_path)
        self.db = sqlite_utils.Database(str(self.db_path))
        self._init_tables()

    def _init_tables(self) -> None:
        """Initialize database tables if they don't exist."""
        # Check runs table
        if "check_runs" not in self.db.table_names():
            self.db["check_runs"].create(
                {
                    "id": int,
                    "timestamp": str,
                    "store_url": str,
                    "skill_name": str,
                    "status": str,
                    "summary": str,
                    "details": str,
                    "screenshots": str,
                    "error": str,
                },
                pk="id",
            )
            self.db["check_runs"].create_index(
                ["timestamp", "store_url", "skill_name"],
                index_name="idx_check_runs",
                if_not_exists=True,
            )

        # Baselines table
        if "baselines" not in self.db.table_names():
            self.db["baselines"].create(
                {
                    "id": int,
                    "skill_name": str,
                    "store_url": str,
                    "baseline_data": str,
                    "created_at": str,
                    "updated_at": str,
                },
                pk="id",
            )
            self.db["baselines"].create_index(
                ["skill_name", "store_url"],
                index_name="idx_baselines",
                unique=True,
                if_not_exists=True,
            )

        # Incidents table
        if "incidents" not in self.db.table_names():
            self.db["incidents"].create(
                {
                    "id": int,
                    "created_at": str,
                    "resolved_at": str,
                    "store_url": str,
                    "skill_name": str,
                    "severity": str,
                    "title": str,
                    "details": str,
                    "status": str,
                },
                pk="id",
            )
            self.db["incidents"].create_index(
                ["store_url", "status"],
                index_name="idx_incidents",
                if_not_exists=True,
            )

    def record_check(
        self,
        store_url: str,
        skill_name: str,
        status: str,
        summary: str,
        details: Optional[dict[str, Any]] = None,
        screenshots: Optional[list[str]] = None,
        error: Optional[str] = None,
    ) -> int:
        """
        Record a skill check run.

        Args:
            store_url: Store URL being monitored.
            skill_name: Name of the skill that ran.
            status: Result status (PASS, WARN, FAIL).
            summary: Human-readable summary.
            details: Additional details dict.
            screenshots: List of screenshot paths.
            error: Error message if applicable.

        Returns:
            ID of the recorded check run.
        """
        row = {
            "timestamp": datetime.utcnow().isoformat(),
            "store_url": store_url,
            "skill_name": skill_name,
            "status": status,
            "summary": summary,
            "details": json.dumps(details or {}),
            "screenshots": json.dumps(screenshots or []),
            "error": error,
        }
        result = self.db["check_runs"].insert(row)
        logger.info(f"Recorded check run: {skill_name} -> {status}")
        return result.last_pk

    def get_latest_baseline(self, skill_name: str, store_url: str) -> Optional[dict[str, Any]]:
        """
        Get the latest baseline for a skill.

        Args:
            skill_name: Name of the skill.
            store_url: Store URL.

        Returns:
            Baseline data dict or None if not found.
        """
        row = self.db["baselines"].rows_where(
            "skill_name = ? AND store_url = ?",
            [skill_name, store_url],
            order_by="-updated_at",
            limit=1,
        )
        rows_list = list(row)
        if rows_list:
            baseline_data = rows_list[0].get("baseline_data")
            if baseline_data:
                return json.loads(baseline_data)
        return None

    def update_baseline(
        self, skill_name: str, store_url: str, baseline_data: dict[str, Any]
    ) -> int:
        """
        Update or create a baseline for a skill.

        Args:
            skill_name: Name of the skill.
            store_url: Store URL.
            baseline_data: Baseline data dict.

        Returns:
            ID of the baseline record.
        """
        now = datetime.utcnow().isoformat()
        existing = list(
            self.db["baselines"].rows_where(
                "skill_name = ? AND store_url = ?",
                [skill_name, store_url],
                limit=1,
            )
        )

        row = {
            "skill_name": skill_name,
            "store_url": store_url,
            "baseline_data": json.dumps(baseline_data),
            "updated_at": now,
        }

        if existing:
            row["created_at"] = existing[0]["created_at"]
            row["id"] = existing[0]["id"]
            self.db["baselines"].update(row["id"], row)
            result_id = row["id"]
        else:
            row["created_at"] = now
            result = self.db["baselines"].insert(row)
            result_id = result.last_pk

        logger.info(f"Updated baseline: {skill_name} for {store_url}")
        return result_id

    def create_incident(
        self,
        store_url: str,
        skill_name: str,
        severity: str,
        title: str,
        details: Optional[dict[str, Any]] = None,
    ) -> int:
        """
        Create an incident record.

        Args:
            store_url: Store URL.
            skill_name: Skill that detected the issue.
            severity: Severity level (P0, P1, P2, P3).
            title: Incident title.
            details: Additional details dict.

        Returns:
            ID of the new incident.
        """
        row = {
            "created_at": datetime.utcnow().isoformat(),
            "resolved_at": None,
            "store_url": store_url,
            "skill_name": skill_name,
            "severity": severity,
            "title": title,
            "details": json.dumps(details or {}),
            "status": "open",
        }
        result = self.db["incidents"].insert(row)
        logger.info(f"Created incident: {title} (severity: {severity})")
        return result.last_pk

    def resolve_incident(self, incident_id: int) -> None:
        """
        Mark an incident as resolved.

        Args:
            incident_id: ID of the incident.
        """
        self.db["incidents"].update(
            incident_id,
            {
                "resolved_at": datetime.utcnow().isoformat(),
                "status": "resolved",
            },
        )
        logger.info(f"Resolved incident: {incident_id}")

    def get_open_incidents(self, store_url: Optional[str] = None) -> list[dict]:
        """
        Get all open incidents.

        Args:
            store_url: Optional filter by store URL.

        Returns:
            List of incident records.
        """
        if store_url:
            rows = self.db["incidents"].rows_where(
                "status = ? AND store_url = ?",
                ["open", store_url],
                order_by="-created_at",
            )
        else:
            rows = self.db["incidents"].rows_where(
                "status = ?",
                ["open"],
                order_by="-created_at",
            )
        return list(rows)

    def get_recent_check_runs(self, store_url: str, limit: int = 10) -> list[dict]:
        """
        Get recent check runs for a store.

        Args:
            store_url: Store URL.
            limit: Maximum number of results.

        Returns:
            List of check run records.
        """
        rows = self.db["check_runs"].rows_where(
            "store_url = ?",
            [store_url],
            order_by="-timestamp",
            limit=limit,
        )
        return list(rows)
