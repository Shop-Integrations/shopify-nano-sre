"""Shopify Shopper Skill - Simulates a real user journey through the store."""

import asyncio
import logging
from typing import Any

from nano_sre.agent.core import Skill, SkillResult

logger = logging.getLogger(__name__)


class ShopifyShopper(Skill):
    """
    Simulates a synthetic shopper journey:
    1. Home Page
    2. Product Page
    3. Add to Cart
    4. View Cart
    """

    def name(self) -> str:
        return "shopify_shopper"

    async def run(self, context: dict[str, Any]) -> SkillResult:
        page = context.get("page")
        base_url: str = context.get("base_url", "")

        if not page or not base_url:
            return SkillResult(
                skill_name=self.name(),
                status="FAIL",
                summary="Missing page or base_url in context",
            )

        steps = []
        try:
            # 1. Home Page
            logger.info(f"Shopper starting at Home: {base_url}")
            await page.goto(base_url, wait_until="networkidle")
            steps.append("Visited Home Page")

            # 2. Find a product and click it
            # Look for product links that are likely to be real products
            product_link = page.locator('a[href*="/products/"]').first

            # Specifically look for the liquid snowboard if it's there (since we baselined it)
            liquid_link = page.locator('a[href*="/products/the-collection-snowboard-liquid"]').first
            if await liquid_link.count() > 0:
                product_link = liquid_link

            if await product_link.count() > 0:
                product_url = await product_link.get_attribute("href")
                if product_url:
                    if not product_url.startswith("http"):
                        product_url = base_url.rstrip("/") + product_url

                    logger.info(f"Navigating to product: {product_url}")
                    await page.goto(product_url, wait_until="networkidle")
                    steps.append(f"Visited Product Page: {product_url}")
            else:
                return SkillResult(
                    skill_name=self.name(),
                    status="FAIL",
                    summary="Could not find any product link on Home Page",
                )

            # 3. Add to Cart
            # Look for Add to Cart button
            atc_button = page.locator(
                'button[name="add"], button:has-text("Add to cart"), [data-testid="add-to-cart"]'
            )
            if await atc_button.count() > 0:
                logger.info("Clicking Add to Cart")
                await atc_button.first.click()
                await asyncio.sleep(2)  # Wait for animation/ajax
                steps.append("Clicked Add to Cart")
            else:
                return SkillResult(
                    skill_name=self.name(),
                    status="WARN",
                    summary="Could not find Add to Cart button on product page",
                    details={"steps": steps},
                )

            # 4. View Cart
            # Navigate to /cart directly as it's more reliable than finding the cart icon
            logger.info("Navigating to Cart")
            await page.goto(f"{base_url.rstrip('/')}/cart", wait_until="networkidle")
            steps.append("Visited Cart Page")

            # Check if cart is not empty
            cart_item = page.locator('.cart-item, .cart__item, [data-testid="cart-item"]')
            if await cart_item.count() > 0:
                status = "PASS"
                summary = "Shopper journey completed successfully (Product -> Cart)"
            else:
                status = "WARN"
                summary = "Shopper journey completed but cart appears empty"

            return SkillResult(
                skill_name=self.name(), status=status, summary=summary, details={"steps": steps}
            )

        except Exception as e:
            logger.exception("Shopper journey failed")
            return SkillResult(
                skill_name=self.name(),
                status="FAIL",
                summary=f"Shopper journey failed: {str(e)}",
                error=str(e),
                details={"steps": steps},
            )
