"""Tests for the diagnosis module."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from nano_sre.agent.core import SkillResult
from nano_sre.agent.diagnosis import (
    _fallback_diagnosis,
    _format_skill_result_for_llm,
    diagnose,
)
from nano_sre.utils.llm import get_litellm_model_identifier as _get_litellm_model_identifier
from nano_sre.utils.llm import is_vision_model as _is_vision_model


@pytest.fixture
def failed_skill_result():
    """Create a failed skill result for testing."""
    return SkillResult(
        skill_name="pixel_auditor",
        status="FAIL",
        summary="Pixel validation failed",
        error="Missing required fields: transaction_id",
        details={"events": 5, "errors": 2},
        screenshots=["screenshot1.png"],
        timestamp=datetime(2026, 2, 17, 12, 0, 0),
    )


@pytest.fixture
def warn_skill_result():
    """Create a warning skill result for testing."""
    return SkillResult(
        skill_name="checkout_monitor",
        status="WARN",
        summary="Checkout load time degraded",
        details={"load_time_ms": 3500, "threshold_ms": 3000},
        screenshots=[],
        timestamp=datetime(2026, 2, 17, 12, 0, 0),
    )


@pytest.fixture
def mock_settings():
    """Create mock settings."""
    settings = MagicMock()
    settings.llm_provider = "openai"
    settings.llm_api_key = "test-api-key"
    settings.llm_model = "gpt-4"
    return settings


@pytest.fixture
def mock_settings_no_key():
    """Create mock settings without API key."""
    settings = MagicMock()
    settings.llm_provider = "openai"
    settings.llm_api_key = None
    settings.llm_model = "gpt-4"
    return settings


@pytest.fixture
def mock_settings_ollama():
    """Create mock settings for Ollama."""
    settings = MagicMock()
    settings.llm_provider = "ollama"
    settings.llm_api_key = None
    settings.llm_model = "mistral"
    return settings


class TestFallbackDiagnosis:
    """Test fallback diagnosis functionality."""

    def test_fallback_diagnosis_fail_status(self, failed_skill_result):
        """Test fallback diagnosis for FAIL status."""
        result = _fallback_diagnosis(failed_skill_result)

        assert result["severity"] == "P1"
        assert "pixel_auditor" in result["root_cause"]
        assert "FAIL" in result["root_cause"]
        assert result["analyzed"] is False
        assert "recommended_fix" in result
        assert "shopify_docs_link" in result

    def test_fallback_diagnosis_warn_status(self, warn_skill_result):
        """Test fallback diagnosis for WARN status."""
        result = _fallback_diagnosis(warn_skill_result)

        assert result["severity"] == "P2"
        assert "checkout_monitor" in result["root_cause"]
        assert result["analyzed"] is False

    def test_fallback_diagnosis_with_error(self, failed_skill_result):
        """Test fallback diagnosis with error message."""
        result = _fallback_diagnosis(failed_skill_result, error="LLM unavailable")

        assert "error" in result
        assert result["error"] == "LLM unavailable"

    def test_fallback_diagnosis_pixel_skill(self, failed_skill_result):
        """Test pixel-specific recommendations."""
        result = _fallback_diagnosis(failed_skill_result)

        assert "pixel" in result["recommended_fix"].lower()
        assert "pixels" in result["shopify_docs_link"]

    def test_fallback_diagnosis_checkout_skill(self, warn_skill_result):
        """Test checkout-specific recommendations."""
        result = _fallback_diagnosis(warn_skill_result)

        assert "checkout" in result["recommended_fix"].lower()
        assert "checkout" in result["shopify_docs_link"]


class TestUtilityFunctions:
    """Test utility functions."""

    def test_format_skill_result_for_llm(self, failed_skill_result):
        """Test formatting skill result for LLM."""
        formatted = _format_skill_result_for_llm(failed_skill_result)

        assert "pixel_auditor" in formatted
        assert "FAIL" in formatted
        assert "Pixel validation failed" in formatted
        assert "Missing required fields" in formatted
        assert "Please analyze" in formatted

    def test_format_skill_result_without_error(self, warn_skill_result):
        """Test formatting skill result without error."""
        formatted = _format_skill_result_for_llm(warn_skill_result)

        assert "checkout_monitor" in formatted
        assert "WARN" in formatted
        assert "Error:" not in formatted

    def test_is_vision_model_gpt4_turbo(self):
        """Test vision model detection for GPT-4 Turbo."""
        assert _is_vision_model("gpt-4-turbo") is True
        assert _is_vision_model("gpt-4o") is True

    def test_is_vision_model_claude3(self):
        """Test vision model detection for Claude 3."""
        assert _is_vision_model("claude-3-opus") is True
        assert _is_vision_model("claude-3-sonnet") is True

    def test_is_vision_model_non_vision(self):
        """Test vision model detection for non-vision models."""
        assert _is_vision_model("gpt-3.5-turbo") is False
        assert _is_vision_model("gpt-4") is False
        assert _is_vision_model("claude-2") is False

    def test_get_litellm_model_identifier_openai(self):
        """Test model identifier for OpenAI."""
        identifier = _get_litellm_model_identifier("openai", "gpt-4")
        assert identifier == "gpt-4"

    def test_get_litellm_model_identifier_anthropic(self):
        """Test model identifier for Anthropic."""
        identifier = _get_litellm_model_identifier("anthropic", "claude-3-opus")
        assert identifier == "claude-3-opus"

        # Test auto-prefixing
        identifier = _get_litellm_model_identifier("anthropic", "3-opus")
        assert identifier == "claude-3-opus"

    def test_get_litellm_model_identifier_ollama(self):
        """Test model identifier for Ollama."""
        identifier = _get_litellm_model_identifier("ollama", "mistral")
        assert identifier == "ollama/mistral"


class TestDiagnoseFunction:
    """Test main diagnose function."""

    @pytest.mark.asyncio
    async def test_diagnose_no_api_key_fallback(self, failed_skill_result, mock_settings_no_key):
        """Test diagnose falls back when no API key is configured."""
        with patch("nano_sre.config.settings.get_settings", return_value=mock_settings_no_key):
            result = await diagnose(failed_skill_result)

            assert result["analyzed"] is False
            assert result["severity"] in ["P0", "P1", "P2", "P3"]
            assert "root_cause" in result
            assert "recommended_fix" in result

    @pytest.mark.asyncio
    async def test_diagnose_ollama_no_key_ok(self, failed_skill_result, mock_settings_ollama):
        """Test diagnose works with Ollama without API key."""
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(
                message=MagicMock(
                    content='{"root_cause": "Test cause", "severity": "P1", "recommended_fix": "Test fix"}'
                )
            )
        ]

        with patch("nano_sre.config.settings.get_settings", return_value=mock_settings_ollama):
            with patch("litellm.acompletion", new_callable=AsyncMock) as mock_completion:
                mock_completion.return_value = mock_response

                result = await diagnose(failed_skill_result)

                assert result["analyzed"] is True
                assert result["root_cause"] == "Test cause"
                assert result["severity"] == "P1"

    @pytest.mark.asyncio
    async def test_diagnose_with_llm_success(self, failed_skill_result, mock_settings):
        """Test successful LLM diagnosis."""
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(
                message=MagicMock(
                    content='{"root_cause": "Pixel configuration issue", "severity": "P1", "recommended_fix": "Update pixel settings", "shopify_docs_link": "https://shopify.dev/docs"}'
                )
            )
        ]

        with patch("nano_sre.config.settings.get_settings", return_value=mock_settings):
            with patch("litellm.acompletion", new_callable=AsyncMock) as mock_completion:
                mock_completion.return_value = mock_response

                result = await diagnose(failed_skill_result)

                assert result["analyzed"] is True
                assert result["root_cause"] == "Pixel configuration issue"
                assert result["severity"] == "P1"
                assert result["recommended_fix"] == "Update pixel settings"
                assert "shopify_docs_link" in result

                # Verify litellm was called correctly
                mock_completion.assert_called_once()
                call_args = mock_completion.call_args
                assert call_args.kwargs["model"] == "gpt-4"
                assert call_args.kwargs["api_key"] == "test-api-key"
                assert len(call_args.kwargs["messages"]) == 2
                assert call_args.kwargs["messages"][0]["role"] == "system"
                assert "Senior Shopify SRE" in call_args.kwargs["messages"][0]["content"]

    @pytest.mark.asyncio
    async def test_diagnose_with_invalid_severity(self, failed_skill_result, mock_settings):
        """Test diagnosis with invalid severity defaults to P2."""
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(
                message=MagicMock(
                    content='{"root_cause": "Test", "severity": "INVALID", "recommended_fix": "Fix"}'
                )
            )
        ]

        with patch("nano_sre.config.settings.get_settings", return_value=mock_settings):
            with patch("litellm.acompletion", new_callable=AsyncMock) as mock_completion:
                mock_completion.return_value = mock_response

                result = await diagnose(failed_skill_result)

                assert result["severity"] == "P2"

    @pytest.mark.asyncio
    async def test_diagnose_with_json_parse_error(self, failed_skill_result, mock_settings):
        """Test diagnosis handles JSON parse errors."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="Invalid JSON response"))]

        with patch("nano_sre.config.settings.get_settings", return_value=mock_settings):
            with patch("litellm.acompletion", new_callable=AsyncMock) as mock_completion:
                mock_completion.return_value = mock_response

                result = await diagnose(failed_skill_result)

                assert result["analyzed"] is False
                assert "error" in result
                assert "JSON" in result["error"]

    @pytest.mark.asyncio
    async def test_diagnose_with_missing_fields(self, failed_skill_result, mock_settings):
        """Test diagnosis handles missing required fields."""
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(
                message=MagicMock(content='{"root_cause": "Test"}')  # Missing severity and fix
            )
        ]

        with patch("nano_sre.config.settings.get_settings", return_value=mock_settings):
            with patch("litellm.acompletion", new_callable=AsyncMock) as mock_completion:
                mock_completion.return_value = mock_response

                result = await diagnose(failed_skill_result)

                # Should fall back due to missing fields
                assert result["analyzed"] is False

    @pytest.mark.asyncio
    async def test_diagnose_with_llm_exception(self, failed_skill_result, mock_settings):
        """Test diagnosis handles LLM exceptions."""
        with patch("nano_sre.config.settings.get_settings", return_value=mock_settings):
            with patch("litellm.acompletion", new_callable=AsyncMock) as mock_completion:
                mock_completion.side_effect = Exception("LLM service error")

                result = await diagnose(failed_skill_result)

                assert result["analyzed"] is False
                assert result["severity"] in ["P0", "P1", "P2", "P3"]

    @pytest.mark.asyncio
    async def test_diagnose_with_screenshots_vision_model(self, failed_skill_result):
        """Test diagnosis includes screenshots for vision models."""
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(
                message=MagicMock(
                    content='{"root_cause": "Visual issue", "severity": "P2", "recommended_fix": "Fix layout"}'
                )
            )
        ]

        vision_settings = MagicMock()
        vision_settings.llm_provider = "openai"
        vision_settings.llm_api_key = "test-key"
        vision_settings.llm_model = "gpt-4o"

        with patch("nano_sre.config.settings.get_settings", return_value=vision_settings):
            with patch("litellm.acompletion", new_callable=AsyncMock) as mock_completion:
                mock_completion.return_value = mock_response

                await diagnose(failed_skill_result)

                # Verify screenshots mention was added
                call_args = mock_completion.call_args
                user_message = call_args.kwargs["messages"][1]["content"]
                assert "screenshot" in user_message.lower()

    @pytest.mark.asyncio
    async def test_diagnose_litellm_not_installed(self, failed_skill_result, mock_settings):
        """Test diagnosis handles missing litellm gracefully."""
        with patch("nano_sre.config.settings.get_settings", return_value=mock_settings):
            with patch.dict("sys.modules", {"litellm": None}):
                # Mock import to fail
                with patch("nano_sre.agent.diagnosis._llm_diagnosis") as mock_llm_diag:
                    mock_llm_diag.return_value = _fallback_diagnosis(
                        failed_skill_result, error="litellm not installed"
                    )
                    result = await diagnose(failed_skill_result)

                    assert result["analyzed"] is False
