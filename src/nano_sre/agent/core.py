"""Core agent engine with asyncio loop and skill framework."""

import asyncio
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


@dataclass
class SkillResult:
    """Result returned by a skill execution."""

    skill_name: str
    status: str  # PASS, WARN, FAIL
    summary: str
    details: dict[str, Any] = field(default_factory=dict)
    screenshots: list[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    error: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        """Convert result to dictionary."""
        return {
            "skill_name": self.skill_name,
            "status": self.status,
            "summary": self.summary,
            "details": self.details,
            "screenshots": self.screenshots,
            "timestamp": self.timestamp.isoformat(),
            "error": self.error,
        }


class Skill(ABC):
    """Base class for all skills."""

    @abstractmethod
    def name(self) -> str:
        """Return the skill name."""
        pass

    @abstractmethod
    async def run(self, context: dict[str, Any]) -> SkillResult:
        """
        Execute the skill and return results.

        Args:
            context: Agent context containing page, settings, etc.

        Returns:
            SkillResult instance with execution results.
        """
        pass


class Agent:
    """Main agent orchestrator."""

    def __init__(self, settings: Any):
        """Initialize the agent with settings."""
        self.settings = settings
        self.skills: dict[str, Skill] = {}
        self.results: list[SkillResult] = []
        self.context: dict[str, Any] = {}

    def register_skill(self, skill: Skill) -> None:
        """Register a skill for execution."""
        self.skills[skill.name()] = skill
        logger.info(f"Registered skill: {skill.name()}")

    def unregister_skill(self, skill_name: str) -> None:
        """Unregister a skill."""
        if skill_name in self.skills:
            del self.skills[skill_name]
            logger.info(f"Unregistered skill: {skill_name}")

    async def execute_skills(
        self,
        skill_names: Optional[list[str]] = None,
        context: Optional[dict[str, Any]] = None,
    ) -> list[SkillResult]:
        """
        Execute skills sequentially or a specific set.

        Args:
            skill_names: Optional list of specific skills to run.
            context: Context dict to pass to skills.

        Returns:
            List of SkillResult objects.
        """
        self.context = context or {}
        self.results = []

        skills_to_run = skill_names or list(self.skills.keys())

        for skill_name in skills_to_run:
            if skill_name not in self.skills:
                logger.warning(f"Skill not found: {skill_name}")
                continue

            skill = self.skills[skill_name]
            try:
                logger.info(f"Executing skill: {skill_name}")
                result = await skill.run(self.context)
                self.results.append(result)
                logger.info(f"Skill {skill_name} completed with status: {result.status}")
            except Exception as e:
                logger.exception(f"Error executing skill {skill_name}: {e}")
                error_result = SkillResult(
                    skill_name=skill_name,
                    status="FAIL",
                    summary=f"Skill execution failed: {str(e)}",
                    error=str(e),
                )
                self.results.append(error_result)

        return self.results

    def get_result_summary(self) -> dict[str, Any]:
        """Get summary of all results."""
        total = len(self.results)
        passed = sum(1 for r in self.results if r.status == "PASS")
        warned = sum(1 for r in self.results if r.status == "WARN")
        failed = sum(1 for r in self.results if r.status == "FAIL")

        return {
            "total_skills": total,
            "passed": passed,
            "warned": warned,
            "failed": failed,
            "results": [r.to_dict() for r in self.results],
        }


async def run_agent_loop(
    agent: Agent,
    on_loop_iteration: Optional[Callable[[dict[str, Any]], None]] = None,
) -> None:
    """
    Run the agent loop indefinitely.

    Args:
        agent: Agent instance to run.
        on_loop_iteration: Optional callback after each iteration.
    """
    while True:
        try:
            logger.info("Starting agent loop iteration")
            await agent.execute_skills()
            summary = agent.get_result_summary()

            if on_loop_iteration:
                on_loop_iteration(summary)

            await asyncio.sleep(agent.settings.check_interval_minutes * 60)
        except KeyboardInterrupt:
            logger.info("Agent loop interrupted")
            break
        except Exception as e:
            logger.exception(f"Error in agent loop: {e}")
            await asyncio.sleep(60)  # Wait before retrying
