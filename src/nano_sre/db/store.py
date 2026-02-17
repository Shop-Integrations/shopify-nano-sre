"""SQLite-based state management for check runs, baselines, and incidents."""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Optional, cast

import sqlite_utils
from sqlite_utils.db import Table

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
            check_runs = self._table("check_runs")
            check_runs.create(
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
            check_runs.create_index(
                ["timestamp", "store_url", "skill_name"],
                index_name="idx_check_runs",
                if_not_exists=True,
            )

        # Baselines table
        if "baselines" not in self.db.table_names():
            baselines = self._table("baselines")
            baselines.create(
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
            baselines.create_index(
                ["skill_name", "store_url"],
                index_name="idx_baselines",
                unique=True,
                if_not_exists=True,
            )

        # Incidents table
        if "incidents" not in self.db.table_names():
            incidents = self._table("incidents")
            incidents.create(
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
            incidents.create_index(
                ["store_url", "status"],
                index_name="idx_incidents",
                if_not_exists=True,
            )

    def _table(self, name: str) -> Table:
        """Return a typed table instance for mypy."""
        return cast(Table, self.db.table(name))

    def _ensure_last_pk(self, result: Any, action: str) -> int:
        """Return a valid primary key from an insert result."""
        last_pk = getattr(result, "last_pk", None)
        if last_pk is None:
            raise ValueError(f"Insert did not return a primary key for {action}")
        return int(last_pk)

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
        row: dict[str, Any] = {
            "timestamp": datetime.utcnow().isoformat(),
            "store_url": store_url,
            "skill_name": skill_name,
            "status": status,
            "summary": summary,
            "details": json.dumps(details or {}),
            "screenshots": json.dumps(screenshots or []),
            "error": error,
        }
        result = self._table("check_runs").insert(row)
        logger.info(f"Recorded check run: {skill_name} -> {status}")
        return self._ensure_last_pk(result, "check_runs")

    def get_latest_baseline(self, skill_name: str, store_url: str) -> Optional[dict[str, Any]]:
        """
        Get the latest baseline for a skill.

        Args:
            skill_name: Name of the skill.
            store_url: Store URL.

        Returns:
            Baseline data dict or None if not found.
        """
        row = self._table("baselines").rows_where(
            "skill_name = ? AND store_url = ?",
            [skill_name, store_url],
            order_by="-updated_at",
            limit=1,
        )
        rows_list = list(row)
        if rows_list:
            baseline_data = rows_list[0].get("baseline_data")
            if baseline_data:
                data = json.loads(baseline_data)
                if isinstance(data, dict):
                    return data
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
            self._table("baselines").rows_where(
                "skill_name = ? AND store_url = ?",
                [skill_name, store_url],
                limit=1,
            )
        )

        row: dict[str, Any] = {
            "skill_name": skill_name,
            "store_url": store_url,
            "baseline_data": json.dumps(baseline_data),
            "updated_at": now,
        }

        if existing:
            row["created_at"] = existing[0]["created_at"]
            existing_id = int(existing[0]["id"])
            row["id"] = existing_id
            self._table("baselines").update(existing_id, row)
            result_id = existing_id
        else:
            row["created_at"] = now
            result = self._table("baselines").insert(row)
            result_id = self._ensure_last_pk(result, "baselines")

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
        row: dict[str, Any] = {
            "created_at": datetime.utcnow().isoformat(),
            "resolved_at": None,
            "store_url": store_url,
            "skill_name": skill_name,
            "severity": severity,
            "title": title,
            "details": json.dumps(details or {}),
            "status": "open",
        }
        result = self._table("incidents").insert(row)
        logger.info(f"Created incident: {title} (severity: {severity})")
        return self._ensure_last_pk(result, "incidents")

    def resolve_incident(self, incident_id: int) -> None:
        """
        Mark an incident as resolved.

        Args:
            incident_id: ID of the incident.
        """
        self._table("incidents").update(
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
            rows = self._table("incidents").rows_where(
                "status = ? AND store_url = ?",
                ["open", store_url],
                order_by="-created_at",
            )
        else:
            rows = self._table("incidents").rows_where(
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
        rows = self._table("check_runs").rows_where(
            "store_url = ?",
            [store_url],
            order_by="-timestamp",
            limit=limit,
        )
        return list(rows)
