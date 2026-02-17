"""MCP Advisor skill for querying Shopify Dev MCP."""

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
            # Check if MCP is configured
            mcp_available = await self._check_mcp_availability(context)

            if not mcp_available:
                return SkillResult(
                    skill_name=self.name(),
                    status="PASS",
                    summary="MCP not configured - skipping gracefully",
                    details={
                        "mcp_configured": False,
                        "note": "Install and configure Shopify Dev MCP for enhanced diagnostics",
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
                    details={"mcp_configured": True},
                )

            # Query MCP for recommendations
            recommendations = await self._query_mcp(
                console_errors=console_errors,
                api_errors=api_errors,
                context=context,
            )

            status = "WARN" if recommendations.get("issues_found") else "PASS"

            return SkillResult(
                skill_name=self.name(),
                status=status,
                summary=self._build_summary(recommendations),
                details={
                    "mcp_configured": True,
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
                        recommendations["deprecations"].append({
                            "feature": result.get("feature"),
                            "deprecation_date": result.get("deprecation_date"),
                            "replacement": result.get("replacement"),
                        })

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
                        recommendations["deprecations"].append({
                            "api_field": result.get("field"),
                            "deprecation_date": result.get("deprecation_date"),
                            "replacement": result.get("replacement"),
                            "migration_guide": result.get("migration_guide"),
                        })

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
        # Placeholder for actual MCP query implementation
        # This would use the MCP client's API to query Shopify Dev docs

        # Example structure of what would be returned:
        # return {
        #     "error": error_text,
        #     "explanation": "...",
        #     "recommended_fix": "...",
        #     "documentation_link": "https://shopify.dev/...",
        #     "is_deprecated": False,
        # }

        # For now, return None as placeholder
        logger.debug(f"MCP query for error: {error_text} (type: {error_type})")
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
        # Placeholder for actual MCP query implementation

        # Example query: "Explain the error 'Field sku doesn't exist' for API version 2025-01"
        # Example response structure:
        # return {
        #     "error_code": error_code,
        #     "error_message": error_message,
        #     "explanation": "...",
        #     "recommended_fix": "...",
        #     "documentation_link": "https://shopify.dev/api/admin-graphql/...",
        #     "is_deprecated": True,
        #     "field": "sku",
        #     "deprecation_date": "2024-10",
        #     "replacement": "Use variants.sku instead",
        #     "migration_guide": "https://shopify.dev/changelog/...",
        # }

        logger.debug(
            f"MCP query for API error: {error_message} "
            f"(code: {error_code}, version: {api_version})"
        )
        return None

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
