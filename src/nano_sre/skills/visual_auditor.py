"""Visual auditor skill for detecting UI changes via screenshot comparison."""

import base64
import logging
from pathlib import Path
from typing import Any

from PIL import Image, ImageChops
from playwright.async_api import Page

from nano_sre.agent.core import Skill, SkillResult

logger = logging.getLogger(__name__)


class VisualAuditor(Skill):
    """
    Visual regression testing skill.

    Captures full-page screenshots of key pages, compares against baselines,
    and uses LLM vision models to assess significant visual differences.
    """

    BASELINE_DIR = Path("db/baselines")
    DIFF_THRESHOLD = 0.05  # 5% pixel difference threshold

    # Pages to monitor
    MONITORED_PAGES = [
        "/",  # index
        "/products/example-product",  # products (example)
        "/cart",
        "/checkout",
    ]

    def __init__(self, llm_client: Any = None, update_baseline: bool = False):
        """
        Initialize visual auditor.

        Args:
            llm_client: LiteLLM client for vision analysis (optional)
            update_baseline: If True, update baseline images instead of comparing
        """
        self.llm_client = llm_client
        self.update_baseline = update_baseline
        self.BASELINE_DIR.mkdir(parents=True, exist_ok=True)

    def name(self) -> str:
        """Return skill name."""
        return "visual_auditor"

    async def run(self, context: dict[str, Any]) -> SkillResult:
        """
        Execute visual audit by capturing and comparing screenshots.

        Args:
            context: Must contain 'page' (Playwright Page) and 'base_url'

        Returns:
            SkillResult with comparison results and LLM assessment
        """
        page = context.get("page")
        base_url: str = context.get("base_url", "")

        if not page:
            return SkillResult(
                skill_name=self.name(),
                status="FAIL",
                summary="No Playwright page instance in context",
                error="Missing 'page' in context",
            )

        results = {}
        screenshots_taken = []
        max_diff_percent = 0.0
        differences_found = []

        for page_path in self.MONITORED_PAGES:
            try:
                logger.info(f"Auditing page: {page_path}")
                diff_result = await self._audit_page(page, base_url, page_path)

                results[page_path] = diff_result
                screenshots_taken.append(diff_result.get("screenshot_path", ""))

                if diff_result.get("diff_percent", 0) > max_diff_percent:
                    max_diff_percent = diff_result["diff_percent"]

                if diff_result.get("has_significant_diff"):
                    differences_found.append(
                        {
                            "page": page_path,
                            "diff_percent": diff_result["diff_percent"],
                            "llm_assessment": diff_result.get("llm_assessment"),
                        }
                    )

            except Exception as e:
                logger.exception(f"Error auditing {page_path}: {e}")
                results[page_path] = {"error": str(e)}

        # Determine status
        if self.update_baseline:
            status = "PASS"
            summary = f"Updated baselines for {len(results)} pages"
        elif differences_found:
            status = "WARN"
            summary = f"Visual differences detected on {len(differences_found)} page(s), max diff: {max_diff_percent:.2f}%"
        else:
            status = "PASS"
            summary = f"No significant visual changes detected across {len(results)} pages"

        return SkillResult(
            skill_name=self.name(),
            status=status,
            summary=summary,
            details={
                "max_diff_percent": max_diff_percent,
                "pages_audited": len(results),
                "differences_found": differences_found,
                "results": results,
            },
            screenshots=screenshots_taken,
        )

    async def _audit_page(self, page: Page, base_url: str, page_path: str) -> dict[str, Any]:
        """
        Audit a single page by capturing screenshot and comparing to baseline.

        Args:
            page: Playwright page instance
            base_url: Base URL of the store
            page_path: Path to audit (e.g., "/cart")

        Returns:
            Dict with diff results and assessment
        """
        # Navigate to page
        url = f"{base_url.rstrip('/')}{page_path}"
        await page.goto(url, wait_until="networkidle")

        # Generate filename from path
        filename = page_path.strip("/").replace("/", "_") or "index"
        current_path = Path(f"db/screenshots/{filename}_current.png")
        baseline_path = self.BASELINE_DIR / f"{filename}.png"

        # Ensure screenshot directory exists
        current_path.parent.mkdir(parents=True, exist_ok=True)

        # Capture full-page screenshot
        await page.screenshot(path=str(current_path), full_page=True)
        logger.info(f"Captured screenshot: {current_path}")

        result: dict[str, Any] = {
            "screenshot_path": str(current_path),
            "baseline_path": str(baseline_path),
        }

        # If updating baseline, copy current to baseline
        if self.update_baseline:
            import shutil

            shutil.copy(current_path, baseline_path)
            logger.info(f"Updated baseline: {baseline_path}")
            result["baseline_updated"] = True
            result["diff_percent"] = 0.0
            return result

        # Compare with baseline if it exists
        if not baseline_path.exists():
            logger.warning(f"No baseline found for {page_path}, skipping comparison")
            result["diff_percent"] = 0.0
            result["has_significant_diff"] = False
            result["message"] = "No baseline available"
            return result

        # Perform pixel comparison
        diff_percent = self._calculate_pixel_diff(baseline_path, current_path)
        result["diff_percent"] = diff_percent

        # Check if difference exceeds threshold
        if diff_percent > self.DIFF_THRESHOLD:
            result["has_significant_diff"] = True
            logger.info(f"Significant diff detected on {page_path}: {diff_percent:.2%}")

            # Send to LLM for analysis if client available
            if self.llm_client:
                assessment = await self._get_llm_assessment(baseline_path, current_path, page_path)
                result["llm_assessment"] = assessment
            else:
                result["llm_assessment"] = "LLM analysis not available (no client configured)"
        else:
            result["has_significant_diff"] = False
            logger.info(f"No significant diff on {page_path}: {diff_percent:.2%}")

        return result

    def _calculate_pixel_diff(self, baseline_path: Path, current_path: Path) -> float:
        """
        Calculate pixel difference percentage between two images.

        Args:
            baseline_path: Path to baseline image
            current_path: Path to current screenshot

        Returns:
            Percentage of different pixels (0.0 to 1.0)
        """
        try:
            baseline = Image.open(baseline_path)
            current = Image.open(current_path)

            # Resize images to match if dimensions differ
            if baseline.size != current.size:
                logger.warning(
                    f"Image size mismatch: baseline={baseline.size}, current={current.size}"
                )
                # Resize current to match baseline
                current = current.resize(baseline.size, Image.LANCZOS)

            # Convert to RGB if needed
            if baseline.mode != "RGB":
                baseline = baseline.convert("RGB")
            if current.mode != "RGB":
                current = current.convert("RGB")

            # Calculate pixel differences
            diff = ImageChops.difference(baseline, current)

            # Count non-zero pixels (differences)
            diff_pixels = sum(1 for pixel in diff.getdata() if pixel != (0, 0, 0))
            total_pixels = baseline.size[0] * baseline.size[1]

            diff_percent = diff_pixels / total_pixels if total_pixels > 0 else 0.0

            return diff_percent

        except Exception as e:
            logger.exception(f"Error calculating pixel diff: {e}")
            return 0.0

    async def _get_llm_assessment(
        self, baseline_path: Path, current_path: Path, page_path: str
    ) -> str:
        """
        Get LLM vision model assessment of visual differences.

        Args:
            baseline_path: Path to baseline image
            current_path: Path to current screenshot
            page_path: Page being analyzed

        Returns:
            LLM's text assessment of the differences
        """
        try:
            # Read images as base64
            with open(baseline_path, "rb") as f:
                baseline_b64 = base64.b64encode(f.read()).decode("utf-8")

            with open(current_path, "rb") as f:
                current_b64 = base64.b64encode(f.read()).decode("utf-8")

            # Prepare messages for vision model
            messages = [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": (
                                f"Analyze these before/after screenshots of {page_path} and identify visual differences. "
                                "Focus on meaningful changes like layout shifts, missing elements, broken images, "
                                "or styling issues. Ignore minor anti-aliasing or rendering differences."
                            ),
                        },
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/png;base64,{baseline_b64}"},
                        },
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/png;base64,{current_b64}"},
                        },
                    ],
                }
            ]

            # Call LLM vision API (using litellm)
            import litellm

            response = await litellm.acompletion(
                model=self.llm_client.get("model", "gpt-4-vision-preview"),
                messages=messages,
                max_tokens=500,
            )

            assessment = response.choices[0].message.content or ""
            logger.info(f"LLM assessment for {page_path}: {assessment}")

            return assessment

        except Exception as e:
            logger.exception(f"Error getting LLM assessment: {e}")
            return f"LLM assessment failed: {str(e)}"
