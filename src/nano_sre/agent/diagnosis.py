"""AI-powered diagnosis module for analyzing skill failures."""

import logging
from typing import Any, Optional

from nano_sre.agent.core import SkillResult

logger = logging.getLogger(__name__)


async def diagnose(skill_result: SkillResult) -> dict[str, Any]:
    """
    Analyze a skill failure using LLM and return diagnostic information.

    Args:
        skill_result: The SkillResult object from a failed or warned skill

    Returns:
        Dictionary containing:
            - root_cause: String explaining the root cause
            - severity: P0/P1/P2/P3 priority level
            - recommended_fix: String with recommended remediation steps
            - shopify_docs_link: Optional URL to relevant Shopify docs
            - analyzed: Boolean indicating if LLM analysis was performed
    """
    from nano_sre.config.settings import get_settings

    settings = get_settings()

    # Fallback when no LLM is configured
    if not settings.llm_api_key and settings.llm_provider != "ollama":
        logger.warning("No LLM API key configured, returning fallback diagnosis")
        return _fallback_diagnosis(skill_result)

    # Try to perform LLM-based diagnosis
    try:
        return await _llm_diagnosis(skill_result, settings)
    except Exception as e:
        logger.exception(f"Error during LLM diagnosis: {e}")
        return _fallback_diagnosis(skill_result, error=str(e))


async def _llm_diagnosis(skill_result: SkillResult, settings: Any) -> dict[str, Any]:
    """
    Perform LLM-based diagnosis using litellm.

    Args:
        skill_result: The SkillResult to analyze
        settings: Application settings

    Returns:
        Diagnosis dictionary with LLM insights
    """
    import json

    try:
        import litellm
    except ImportError:
        logger.error("litellm not installed, falling back to basic diagnosis")
        return _fallback_diagnosis(skill_result, error="litellm not installed")

    # Prepare system prompt
    system_prompt = (
        "You are a Senior Shopify SRE with deep Shopify platform expertise. "
        "Analyze the provided skill failure and provide a structured diagnosis. "
        "Focus on Shopify-specific issues like checkout extensibility, app conflicts, "
        "API rate limits, theme issues, and pixel tracking problems. "
        "Return your response as JSON with the following structure:\n"
        "{\n"
        '  "root_cause": "brief explanation of the root cause",\n'
        '  "severity": "P0 or P1 or P2 or P3",\n'
        '  "recommended_fix": "step-by-step remediation guidance",\n'
        '  "shopify_docs_link": "URL to relevant Shopify documentation (optional)"\n'
        "}\n\n"
        "Severity levels:\n"
        "- P0: Critical - Store is down or checkout is broken\n"
        "- P1: High - Major feature broken, significant revenue impact\n"
        "- P2: Medium - Minor feature issue, limited impact\n"
        "- P3: Low - Cosmetic or non-critical issue"
    )

    # Prepare user message with skill result details
    user_message = _format_skill_result_for_llm(skill_result)

    # Build messages list
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message},
    ]

    # Add screenshots for vision models if available
    if skill_result.screenshots and _is_vision_model(settings.llm_model):
        messages = _add_screenshots_to_messages(messages, skill_result.screenshots)

    # Determine model identifier for litellm
    model = _get_litellm_model_identifier(settings.llm_provider, settings.llm_model)

    try:
        # Call LLM via litellm
        response = await litellm.acompletion(
            model=model,
            messages=messages,
            api_key=settings.llm_api_key if settings.llm_api_key else None,
            temperature=0.3,
            max_tokens=1000,
        )

        # Extract response content
        content = response.choices[0].message.content

        # Parse JSON response
        diagnosis_data: dict[str, Any] = json.loads(content)

        # Validate required fields
        required_fields = ["root_cause", "severity", "recommended_fix"]
        for field in required_fields:
            if field not in diagnosis_data:
                raise ValueError(f"LLM response missing required field: {field}")

        # Validate severity
        valid_severities = ["P0", "P1", "P2", "P3"]
        if diagnosis_data["severity"] not in valid_severities:
            logger.warning(f"Invalid severity {diagnosis_data['severity']}, defaulting to P2")
            diagnosis_data["severity"] = "P2"

        diagnosis_data["analyzed"] = True
        logger.info(
            f"LLM diagnosis completed: {diagnosis_data['severity']} - {diagnosis_data['root_cause'][:50]}"
        )
        return diagnosis_data

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse LLM response as JSON: {e}")
        return _fallback_diagnosis(skill_result, error="Invalid JSON response from LLM")
    except Exception as e:
        logger.exception(f"LLM call failed: {e}")
        raise


def _format_skill_result_for_llm(skill_result: SkillResult) -> str:
    """
    Format SkillResult for LLM analysis.

    Args:
        skill_result: The SkillResult to format

    Returns:
        Formatted string for LLM
    """
    message_parts = [
        f"Skill Name: {skill_result.skill_name}",
        f"Status: {skill_result.status}",
        f"Summary: {skill_result.summary}",
    ]

    if skill_result.error:
        message_parts.append(f"Error: {skill_result.error}")

    if skill_result.details:
        message_parts.append(f"Details: {skill_result.details}")

    message_parts.append("\nPlease analyze this failure and provide a structured diagnosis.")

    return "\n".join(message_parts)


def _is_vision_model(model_name: str) -> bool:
    """
    Check if the model supports vision/image inputs.

    Args:
        model_name: Name of the LLM model

    Returns:
        True if vision model, False otherwise
    """
    vision_keywords = ["vision", "gpt-4-turbo", "gpt-4o", "claude-3"]
    return any(keyword in model_name.lower() for keyword in vision_keywords)


def _add_screenshots_to_messages(
    messages: list[dict[str, Any]], screenshots: list[str]
) -> list[dict[str, Any]]:
    """
    Add screenshots to messages for vision models.

    Args:
        messages: List of message dictionaries
        screenshots: List of screenshot paths or base64 data

    Returns:
        Updated messages with image content
    """
    # For now, we'll just note that screenshots are available
    # Full implementation would encode images as base64 and add to content
    if messages:
        last_message = messages[-1]
        if "content" in last_message:
            last_message["content"] += (
                f"\n\nNote: {len(screenshots)} screenshot(s) available for analysis."
            )
    return messages


def _get_litellm_model_identifier(provider: str, model: str) -> str:
    """
    Get the correct model identifier for litellm.

    Args:
        provider: LLM provider (openai, anthropic, ollama)
        model: Model name

    Returns:
        Formatted model identifier for litellm
    """
    # litellm uses provider-specific prefixes
    if provider == "anthropic":
        if not model.startswith("claude"):
            return f"claude-{model}"
        return model
    elif provider == "ollama":
        return f"ollama/{model}"
    else:  # openai and others
        return model


def _fallback_diagnosis(skill_result: SkillResult, error: Optional[str] = None) -> dict[str, Any]:
    """
    Provide a basic diagnosis when LLM is not available.

    Args:
        skill_result: The SkillResult to analyze
        error: Optional error message explaining why LLM wasn't used

    Returns:
        Basic diagnosis dictionary
    """
    # Determine severity based on status
    severity_map = {
        "FAIL": "P1",  # Failed skills are high priority
        "WARN": "P2",  # Warnings are medium priority
        "PASS": "P3",  # Pass shouldn't need diagnosis, but just in case
    }
    severity = severity_map.get(skill_result.status, "P2")

    # Provide basic recommendations based on skill name and status
    root_cause = f"{skill_result.skill_name} reported {skill_result.status}"
    if skill_result.error:
        root_cause += f": {skill_result.error}"

    recommended_fix = (
        "1. Review the skill execution logs and error details\n"
        "2. Check Shopify Admin for any recent changes\n"
        "3. Verify store configuration and app settings\n"
        "4. Consider rolling back recent theme or app changes"
    )

    # Add skill-specific recommendations
    if "pixel" in skill_result.skill_name.lower():
        recommended_fix += (
            "\n5. Verify pixel IDs are correct in app/theme settings\n"
            "6. Check browser console for JavaScript errors\n"
            "7. Review checkout extensibility pixel configuration"
        )
        shopify_docs_link = "https://shopify.dev/docs/apps/marketing/pixels"
    elif "checkout" in skill_result.skill_name.lower():
        recommended_fix += (
            "\n5. Test checkout flow manually\n"
            "6. Review payment gateway settings\n"
            "7. Check for checkout.liquid customizations"
        )
        shopify_docs_link = "https://shopify.dev/docs/apps/checkout"
    else:
        shopify_docs_link = "https://shopify.dev/docs"

    diagnosis = {
        "root_cause": root_cause,
        "severity": severity,
        "recommended_fix": recommended_fix,
        "shopify_docs_link": shopify_docs_link,
        "analyzed": False,
    }

    if error:
        diagnosis["error"] = error

    logger.info(f"Fallback diagnosis: {severity} - {root_cause}")
    return diagnosis
