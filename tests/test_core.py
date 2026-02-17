"""Tests for the core agent module."""

from datetime import datetime, timezone
from typing import Any

import pytest

from nano_sre.agent.core import Agent, Skill, SkillResult


class MockSkill(Skill):
    """Mock skill for testing."""

    def __init__(self, name: str, status: str = "PASS", should_fail: bool = False):
        """Initialize mock skill."""
        self._name = name
        self._status = status
        self._should_fail = should_fail
        self.run_count = 0

    def name(self) -> str:
        """Return skill name."""
        return self._name

    async def run(self, context: dict[str, Any]) -> SkillResult:
        """Execute the skill."""
        self.run_count += 1

        if self._should_fail:
            raise RuntimeError(f"Mock skill {self._name} failed")

        return SkillResult(
            skill_name=self._name,
            status=self._status,
            summary=f"{self._name} completed with {self._status}",
            details={"context_data": context.get("test_key", "no_data")},
        )


@pytest.fixture
def mock_settings():
    """Create mock settings."""
    class MockSettings:
        check_interval_minutes = 5
        store_url = "https://test.myshopify.com"

    return MockSettings()


class TestSkillResult:
    """Test SkillResult dataclass."""

    def test_skill_result_creation(self):
        """Test creating a SkillResult."""
        result = SkillResult(
            skill_name="test_skill",
            status="PASS",
            summary="Test passed",
        )

        assert result.skill_name == "test_skill"
        assert result.status == "PASS"
        assert result.summary == "Test passed"
        assert result.details == {}
        assert result.screenshots == []
        assert result.error is None
        assert isinstance(result.timestamp, datetime)

    def test_skill_result_with_details(self):
        """Test SkillResult with details."""
        details = {"key": "value", "count": 42}
        result = SkillResult(
            skill_name="test_skill",
            status="PASS",
            summary="Test passed",
            details=details,
        )

        assert result.details == details

    def test_skill_result_with_screenshots(self):
        """Test SkillResult with screenshots."""
        screenshots = ["screenshot1.png", "screenshot2.png"]
        result = SkillResult(
            skill_name="test_skill",
            status="PASS",
            summary="Test passed",
            screenshots=screenshots,
        )

        assert result.screenshots == screenshots

    def test_skill_result_with_error(self):
        """Test SkillResult with error."""
        result = SkillResult(
            skill_name="test_skill",
            status="FAIL",
            summary="Test failed",
            error="Something went wrong",
        )

        assert result.error == "Something went wrong"

    def test_skill_result_to_dict(self):
        """Test converting SkillResult to dictionary."""
        timestamp = datetime(2026, 2, 17, 12, 0, 0, tzinfo=timezone.utc)
        result = SkillResult(
            skill_name="test_skill",
            status="PASS",
            summary="Test passed",
            details={"key": "value"},
            screenshots=["screenshot.png"],
            timestamp=timestamp,
            error=None,
        )

        result_dict = result.to_dict()

        assert result_dict["skill_name"] == "test_skill"
        assert result_dict["status"] == "PASS"
        assert result_dict["summary"] == "Test passed"
        assert result_dict["details"] == {"key": "value"}
        assert result_dict["screenshots"] == ["screenshot.png"]
        assert result_dict["timestamp"] == timestamp.isoformat()
        assert result_dict["error"] is None

    def test_skill_result_default_timestamp(self):
        """Test that timestamp defaults to current time."""
        result = SkillResult(
            skill_name="test_skill",
            status="PASS",
            summary="Test passed",
        )

        # Timestamp should be recent (within last minute)
        now = datetime.now(timezone.utc)
        time_diff = (now - result.timestamp).total_seconds()
        assert time_diff < 60  # Less than 1 minute


class TestAgent:
    """Test Agent class."""

    def test_agent_creation(self, mock_settings):
        """Test creating an agent."""
        agent = Agent(mock_settings)

        assert agent.settings == mock_settings
        assert agent.skills == {}
        assert agent.results == []
        assert agent.context == {}

    def test_register_skill(self, mock_settings):
        """Test registering a skill."""
        agent = Agent(mock_settings)
        skill = MockSkill("test_skill")

        agent.register_skill(skill)

        assert "test_skill" in agent.skills
        assert agent.skills["test_skill"] == skill

    def test_register_multiple_skills(self, mock_settings):
        """Test registering multiple skills."""
        agent = Agent(mock_settings)
        skill1 = MockSkill("skill1")
        skill2 = MockSkill("skill2")

        agent.register_skill(skill1)
        agent.register_skill(skill2)

        assert len(agent.skills) == 2
        assert "skill1" in agent.skills
        assert "skill2" in agent.skills

    def test_unregister_skill(self, mock_settings):
        """Test unregistering a skill."""
        agent = Agent(mock_settings)
        skill = MockSkill("test_skill")

        agent.register_skill(skill)
        assert "test_skill" in agent.skills

        agent.unregister_skill("test_skill")
        assert "test_skill" not in agent.skills

    def test_unregister_nonexistent_skill(self, mock_settings):
        """Test unregistering a skill that doesn't exist."""
        agent = Agent(mock_settings)

        # Should not raise an error
        agent.unregister_skill("nonexistent")
        assert len(agent.skills) == 0

    @pytest.mark.asyncio
    async def test_execute_skills_single(self, mock_settings):
        """Test executing a single skill."""
        agent = Agent(mock_settings)
        skill = MockSkill("test_skill", status="PASS")
        agent.register_skill(skill)

        results = await agent.execute_skills()

        assert len(results) == 1
        assert results[0].skill_name == "test_skill"
        assert results[0].status == "PASS"
        assert skill.run_count == 1

    @pytest.mark.asyncio
    async def test_execute_skills_multiple(self, mock_settings):
        """Test executing multiple skills."""
        agent = Agent(mock_settings)
        skill1 = MockSkill("skill1", status="PASS")
        skill2 = MockSkill("skill2", status="WARN")

        agent.register_skill(skill1)
        agent.register_skill(skill2)

        results = await agent.execute_skills()

        assert len(results) == 2
        skill_names = {r.skill_name for r in results}
        assert skill_names == {"skill1", "skill2"}

    @pytest.mark.asyncio
    async def test_execute_skills_with_context(self, mock_settings):
        """Test executing skills with context."""
        agent = Agent(mock_settings)
        skill = MockSkill("test_skill")
        agent.register_skill(skill)

        context = {"test_key": "test_value"}
        results = await agent.execute_skills(context=context)

        assert len(results) == 1
        assert results[0].details["context_data"] == "test_value"

    @pytest.mark.asyncio
    async def test_execute_specific_skills(self, mock_settings):
        """Test executing specific skills by name."""
        agent = Agent(mock_settings)
        skill1 = MockSkill("skill1")
        skill2 = MockSkill("skill2")
        skill3 = MockSkill("skill3")

        agent.register_skill(skill1)
        agent.register_skill(skill2)
        agent.register_skill(skill3)

        results = await agent.execute_skills(skill_names=["skill1", "skill3"])

        assert len(results) == 2
        skill_names = {r.skill_name for r in results}
        assert skill_names == {"skill1", "skill3"}
        assert skill1.run_count == 1
        assert skill2.run_count == 0
        assert skill3.run_count == 1

    @pytest.mark.asyncio
    async def test_execute_nonexistent_skill(self, mock_settings):
        """Test executing a skill that doesn't exist."""
        agent = Agent(mock_settings)
        skill = MockSkill("skill1")
        agent.register_skill(skill)

        results = await agent.execute_skills(skill_names=["skill1", "nonexistent"])

        # Should only execute skill1, skip nonexistent
        assert len(results) == 1
        assert results[0].skill_name == "skill1"

    @pytest.mark.asyncio
    async def test_execute_skill_with_exception(self, mock_settings):
        """Test executing a skill that raises an exception."""
        agent = Agent(mock_settings)
        skill = MockSkill("failing_skill", should_fail=True)
        agent.register_skill(skill)

        results = await agent.execute_skills()

        assert len(results) == 1
        assert results[0].skill_name == "failing_skill"
        assert results[0].status == "FAIL"
        assert "failed" in results[0].error.lower()

    @pytest.mark.asyncio
    async def test_execute_skills_clears_previous_results(self, mock_settings):
        """Test that executing skills clears previous results."""
        agent = Agent(mock_settings)
        skill = MockSkill("test_skill")
        agent.register_skill(skill)

        # First execution
        results1 = await agent.execute_skills()
        assert len(results1) == 1

        # Second execution should clear previous results
        results2 = await agent.execute_skills()
        assert len(results2) == 1
        assert len(agent.results) == 1

    def test_get_result_summary_empty(self, mock_settings):
        """Test getting result summary when no skills executed."""
        agent = Agent(mock_settings)

        summary = agent.get_result_summary()

        assert summary["total_skills"] == 0
        assert summary["passed"] == 0
        assert summary["warned"] == 0
        assert summary["failed"] == 0
        assert summary["results"] == []

    @pytest.mark.asyncio
    async def test_get_result_summary_with_results(self, mock_settings):
        """Test getting result summary after executing skills."""
        agent = Agent(mock_settings)
        agent.register_skill(MockSkill("skill1", status="PASS"))
        agent.register_skill(MockSkill("skill2", status="PASS"))
        agent.register_skill(MockSkill("skill3", status="WARN"))
        agent.register_skill(MockSkill("skill4", status="FAIL", should_fail=True))

        await agent.execute_skills()
        summary = agent.get_result_summary()

        assert summary["total_skills"] == 4
        assert summary["passed"] == 2
        assert summary["warned"] == 1
        assert summary["failed"] == 1
        assert len(summary["results"]) == 4

    @pytest.mark.asyncio
    async def test_get_result_summary_dict_format(self, mock_settings):
        """Test that result summary contains properly formatted dicts."""
        agent = Agent(mock_settings)
        agent.register_skill(MockSkill("test_skill", status="PASS"))

        await agent.execute_skills()
        summary = agent.get_result_summary()

        assert len(summary["results"]) == 1
        result_dict = summary["results"][0]

        # Should have all required fields
        assert "skill_name" in result_dict
        assert "status" in result_dict
        assert "summary" in result_dict
        assert "details" in result_dict
        assert "screenshots" in result_dict
        assert "timestamp" in result_dict
        assert "error" in result_dict


class TestMockSkill:
    """Test the MockSkill helper class."""

    @pytest.mark.asyncio
    async def test_mock_skill_name(self):
        """Test mock skill returns correct name."""
        skill = MockSkill("my_skill")
        assert skill.name() == "my_skill"

    @pytest.mark.asyncio
    async def test_mock_skill_run(self):
        """Test mock skill run method."""
        skill = MockSkill("test_skill", status="PASS")
        result = await skill.run({})

        assert result.skill_name == "test_skill"
        assert result.status == "PASS"

    @pytest.mark.asyncio
    async def test_mock_skill_run_count(self):
        """Test mock skill tracks run count."""
        skill = MockSkill("test_skill")

        assert skill.run_count == 0
        await skill.run({})
        assert skill.run_count == 1
        await skill.run({})
        assert skill.run_count == 2

    @pytest.mark.asyncio
    async def test_mock_skill_failure(self):
        """Test mock skill can simulate failure."""
        skill = MockSkill("failing_skill", should_fail=True)

        with pytest.raises(RuntimeError, match="Mock skill failing_skill failed"):
            await skill.run({})
