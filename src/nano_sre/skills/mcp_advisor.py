"""MCP Advisor skill for querying Shopify Dev MCP."""

import json
import logging
from typing import Any, Optional

from ..agent.core import Skill, SkillResult

logger = logging.getLogger(__name__)


class MCPAdvisor(Skill):
    """
    Query Shopify Dev MCP for console/API errors and deprecations.

    This skill attempts to connect to the Shopify Dev MCP server to:
    - Explain API errors and provide documentation links
    - Check for deprecation notices
    - Offer recommended fixes and best practices

    Gracefully skips if MCP is not configured or unavailable.
    """

    def name(self) -> str:
        """Return the skill name."""
        return "mcp_advisor"

    async def run(self, context: dict[str, Any]) -> SkillResult:
        """
        Execute MCP advisor and return recommendations.

        Args:
            context: Agent context containing console_errors, api_errors, etc.

        Returns:
            SkillResult with MCP recommendations or graceful skip.
        """
        try:
            # Check if MCP is configured or if we should use LLM fallback
            mcp_available = await self._check_mcp_availability(context)
            settings = context.get("settings")
            llm_available = settings and (settings.llm_api_key or settings.llm_provider == "ollama")

            if not mcp_available and not llm_available:
                return SkillResult(
                    skill_name=self.name(),
                    status="PASS",
                    summary="MCP not configured and no LLM available - skipping",
                    details={
                        "mcp_configured": False,
                        "llm_configured": False,
                        "note": "Install Shopify Dev MCP or configure LLM for enhanced diagnostics",
                    },
                )

            # Extract errors from context
            console_errors = context.get("console_errors", [])
            api_errors = context.get("api_errors", [])

            if not console_errors and not api_errors:
                return SkillResult(
                    skill_name=self.name(),
                    status="PASS",
                    summary="No errors to analyze",
                    details={
                        "mcp_configured": mcp_available,
                        "llm_configured": bool(llm_available),
                    },
                )

            # Query advisor for recommendations
            recommendations = await self._query_advisor(
                console_errors=console_errors,
                api_errors=api_errors,
                context=context,
                use_llm_fallback=bool(not mcp_available and llm_available),
            )

            status = "WARN" if recommendations.get("issues_found") else "PASS"

            return SkillResult(
                skill_name=self.name(),
                status=status,
                summary=self._build_summary(recommendations),
                details={
                    "mcp_configured": mcp_available,
                    "llm_used": bool(not mcp_available and llm_available),
                    "recommendations": recommendations.get("items", []),
                    "documentation_links": recommendations.get("docs", []),
                    "deprecations": recommendations.get("deprecations", []),
                },
            )

        except Exception as e:
            logger.exception(f"MCP advisor error: {e}")
            return SkillResult(
                skill_name=self.name(),
                status="FAIL",
                summary=f"MCP advisor failed: {str(e)}",
                error=str(e),
            )

    async def _query_advisor(
        self,
        console_errors: list[dict[str, Any]],
        api_errors: list[dict[str, Any]],
        context: dict[str, Any],
        use_llm_fallback: bool = False,
    ) -> dict[str, Any]:
        """Query for recommendations."""
        if use_llm_fallback:
            return await self._query_llm_advisor(console_errors, api_errors, context)
        return await self._query_mcp(console_errors, api_errors, context)

    async def _query_llm_advisor(
        self,
        console_errors: list[dict[str, Any]],
        api_errors: list[dict[str, Any]],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Use LLM to simulate the advisor when MCP is not available."""
        from nano_sre.agent.core import SkillResult
        from nano_sre.agent.diagnosis import diagnose

        # Create a dummy skill result to feed into the diagnosis module
        dummy_result = SkillResult(
            skill_name="mcp_advisor_internal",
            status="WARN",
            summary="Analyzing captured errors",
            details={"console_errors": console_errors, "api_errors": api_errors},
        )

        diagnosis = await diagnose(dummy_result)

        return {
            "items": [
                {
                    "error": "Multiple system errors",
                    "explanation": diagnosis.get("root_cause"),
                    "recommended_fix": diagnosis.get("recommended_fix"),
                    "documentation_link": diagnosis.get("shopify_docs_link"),
                }
            ],
            "docs": [diagnosis.get("shopify_docs_link")]
            if diagnosis.get("shopify_docs_link")
            else [],
            "deprecations": [],
            "issues_found": True,
        }

    async def _check_mcp_availability(self, context: dict[str, Any]) -> bool:
        """
        Check if MCP is configured and available.

        Args:
            context: Agent context that may contain MCP configuration.

        Returns:
            True if MCP is available, False otherwise.
        """
        # Check for MCP client in context
        mcp_client = context.get("mcp_client")
        if mcp_client is None:
            logger.info("MCP client not found in context - skipping")
            return False

        # Optionally ping MCP to verify connection
        try:
            # This would be replaced with actual MCP health check
            # For now, just check if client exists
            return True
        except Exception as e:
            logger.warning(f"MCP availability check failed: {e}")
            return False

    async def _query_mcp(
        self,
        console_errors: list[dict[str, Any]],
        api_errors: list[dict[str, Any]],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Query Shopify Dev MCP for error explanations and recommendations.

        Args:
            console_errors: List of console errors from browser.
            api_errors: List of API errors captured.
            context: Full agent context with MCP client.

        Returns:
            Dictionary with recommendations, docs, and deprecations.
        """
        mcp_client = context.get("mcp_client")
        recommendations: dict[str, Any] = {
            "items": [],
            "docs": [],
            "deprecations": [],
            "issues_found": False,
        }

        # Query for console errors
        for error in console_errors:
            error_text = error.get("text", "")
            error_type = error.get("type", "")

            try:
                # Query MCP for this error
                # This is a placeholder - actual MCP client interface would be used
                result = await self._mcp_explain_error(
                    mcp_client,
                    error_text=error_text,
                    error_type=error_type,
                )

                if result:
                    recommendations["items"].append(result)
                    recommendations["issues_found"] = True

                    if result.get("documentation_link"):
                        recommendations["docs"].append(result["documentation_link"])

                    if result.get("is_deprecated"):
                        recommendations["deprecations"].append(
                            {
                                "feature": result.get("feature"),
                                "deprecation_date": result.get("deprecation_date"),
                                "replacement": result.get("replacement"),
                            }
                        )

            except Exception as e:
                logger.warning(f"Failed to query MCP for console error: {e}")

        # Query for API errors
        for error in api_errors:
            error_code = error.get("code")
            error_message = error.get("message", "")
            api_version = error.get("api_version")

            try:
                result = await self._mcp_explain_api_error(
                    mcp_client,
                    error_code=error_code,
                    error_message=error_message,
                    api_version=api_version,
                )

                if result:
                    recommendations["items"].append(result)
                    recommendations["issues_found"] = True

                    if result.get("documentation_link"):
                        recommendations["docs"].append(result["documentation_link"])

                    if result.get("is_deprecated"):
                        recommendations["deprecations"].append(
                            {
                                "api_field": result.get("field"),
                                "deprecation_date": result.get("deprecation_date"),
                                "replacement": result.get("replacement"),
                                "migration_guide": result.get("migration_guide"),
                            }
                        )

            except Exception as e:
                logger.warning(f"Failed to query MCP for API error: {e}")

        return recommendations

    async def _mcp_explain_error(
        self,
        mcp_client: Any,
        error_text: str,
        error_type: str,
    ) -> Optional[dict[str, Any]]:
        """
        Query MCP to explain a console error.

        Args:
            mcp_client: MCP client instance.
            error_text: The error message text.
            error_type: The type of error (error, warning, etc.).

        Returns:
            Dictionary with explanation and recommendations, or None.
        """
        try:
            # Step 1: Initialize conversation for liquid/generic issues
            init_res = await mcp_client.call_tool("learn_shopify_api", arguments={"api": "liquid"})
            conversation_id = self._extract_conversation_id(init_res)

            if not conversation_id:
                return None

            # Step 2: Search for the error
            prompt = f"Explain this Shopify storefront error: {error_text}"
            search_res = await mcp_client.call_tool(
                "search_docs_chunks",
                arguments={"conversationId": conversation_id, "prompt": prompt},
            )

            content_text = self._extract_text_from_result(search_res)

            if content_text:
                processed_text = self._process_mcp_results(content_text)
                return {
                    "error": error_text,
                    "explanation": processed_text,
                    "recommended_fix": "See the search results above for guidance.",
                }
        except Exception as e:
            logger.warning(f"MCP workflow failed for console error: {e}")

        return None

    async def _mcp_explain_api_error(
        self,
        mcp_client: Any,
        error_code: Optional[str],
        error_message: str,
        api_version: Optional[str],
    ) -> Optional[dict[str, Any]]:
        """
        Query MCP to explain an API error.

        Args:
            mcp_client: MCP client instance.
            error_code: API error code if available.
            error_message: The error message.
            api_version: Shopify API version.

        Returns:
            Dictionary with explanation and recommendations, or None.
        """
        try:
            # Step 1: Initialize conversation for Admin API
            init_res = await mcp_client.call_tool("learn_shopify_api", arguments={"api": "admin"})
            conversation_id = self._extract_conversation_id(init_res)

            if not conversation_id:
                return None

            # Step 2: Search for the API error
            prompt = f"Explain Shopify Admin API error (code: {error_code}): {error_message}"
            if api_version:
                prompt += f" for API version {api_version}"

            search_res = await mcp_client.call_tool(
                "search_docs_chunks",
                arguments={"conversationId": conversation_id, "prompt": prompt},
            )

            content_text = self._extract_text_from_result(search_res)

            if content_text:
                processed_text = self._process_mcp_results(content_text)
                return {
                    "error_code": error_code,
                    "error_message": error_message,
                    "explanation": processed_text,
                }
        except Exception as e:
            logger.warning(f"MCP workflow failed for API error: {e}")

        return None

    def _process_mcp_results(self, content_text: str, limit: int = 5) -> Any:
        """Process and filter MCP results to limit size and remove bulky content."""
        try:
            data = json.loads(content_text)
            if isinstance(data, list):
                # Limit to 5-10 (default 5)
                limited_data = data[:limit]
                # Remove "content" field from each chunk to keep report slim
                for item in limited_data:
                    if isinstance(item, dict):
                        item.pop("content", None)
                return limited_data
        except (json.JSONDecodeError, TypeError):
            # Not JSON or not a list, return as is (might be plain text)
            pass
        return content_text

    def _extract_conversation_id(self, result: Any) -> Optional[str]:
        """Extract conversation UUID from tool result."""
        text = self._extract_text_from_result(result)
        if not text:
            return None

        # The result often says "Conversation started with ID: ..."
        # or we might need to parse the actual JSON if it returned one.
        # However, many MCP servers just return text.
        import re

        match = re.search(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", text)
        if match:
            return match.group(0)
        return None

    def _extract_text_from_result(self, result: Any) -> str:
        """Helper to extract text content from MCP result."""
        if not result or not hasattr(result, "content"):
            return ""

        texts = []
        for part in result.content:
            if hasattr(part, "text"):
                texts.append(part.text)
        return "\n".join(texts)

    def _build_summary(self, recommendations: dict[str, Any]) -> str:
        """
        Build a human-readable summary from recommendations.

        Args:
            recommendations: Dictionary with MCP recommendations.

        Returns:
            Summary string for SkillResult.
        """
        if not recommendations.get("issues_found"):
            return "MCP advisor found no issues to report"

        item_count = len(recommendations.get("items", []))
        deprecation_count = len(recommendations.get("deprecations", []))

        parts = [f"Found {item_count} issue(s)"]

        if deprecation_count > 0:
            parts.append(f"{deprecation_count} deprecation(s)")

        return ", ".join(parts)
