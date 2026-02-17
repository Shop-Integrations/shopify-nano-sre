# Creating Custom Skills

This guide covers creating custom monitoring skills for Shopify Nano-SRE. Skills are modular components that perform specific monitoring tasks on your Shopify store.

## What are Skills?

Skills are Python classes that inherit from a base `Skill` interface and implement monitoring logic. Each skill:

- Performs a specific monitoring task (e.g., check pixel firing, test checkout flow)
- Returns structured results with PASS/WARN/FAIL status
- Can use Playwright for browser automation
- Can leverage LLM capabilities for intelligent diagnostics

## Built-in Skills

Nano-SRE comes with several built-in skills:

1. **PixelAuditor**: Monitors analytics pixel firing (Facebook, Google Analytics, TikTok)
2. **HeadlessProbe**: Tests headless storefront API endpoints
3. **VisualAuditor**: Detects visual layout changes with screenshots
4. **ShopifyDoctor**: Diagnoses Shopify API errors using MCP
5. **MCPAdvisor**: Provides AI-powered recommendations

## Skill Architecture

### Base Skill Interface

All skills implement this interface:

```python
from typing import Any, Dict
from dataclasses import dataclass

@dataclass
class SkillResult:
    """Result from executing a skill."""
    skill_name: str
    status: str  # "PASS", "WARN", or "FAIL"
    summary: str
    details: Dict[str, Any]

class Skill:
    """Base class for all monitoring skills."""
    
    async def execute(self, context: Dict[str, Any]) -> SkillResult:
        """Execute the skill and return results."""
        raise NotImplementedError
```

### Context Object

The `context` dictionary provides:

- `page`: Playwright Page object for browser automation
- `settings`: Application settings
- `db`: Database connection (if needed)
- Any custom data passed from the agent

## Creating Your First Skill

### Example: Cart Abandonment Monitor

Let's create a skill that monitors cart abandonment tracking:

```python
# src/nano_sre/skills/cart_monitor.py

from typing import Any, Dict
from dataclasses import dataclass, field
import logging
from playwright.async_api import Page

logger = logging.getLogger(__name__)

@dataclass
class SkillResult:
    skill_name: str
    status: str
    summary: str
    details: Dict[str, Any] = field(default_factory=dict)

class CartAbandonmentMonitor:
    """Monitors cart abandonment tracking and email triggers."""
    
    def __init__(self):
        self.name = "CartAbandonmentMonitor"
    
    async def execute(self, context: Dict[str, Any]) -> SkillResult:
        """Check if cart abandonment is working."""
        page: Page = context.get("page")
        
        if not page:
            return SkillResult(
                skill_name=self.name,
                status="FAIL",
                summary="No page context provided",
                details={}
            )
        
        try:
            # Navigate to a product
            await page.goto(context["settings"].store_url)
            
            # Find first product link
            product_link = page.locator('a[href*="/products/"]').first
            if await product_link.count() == 0:
                return SkillResult(
                    skill_name=self.name,
                    status="WARN",
                    summary="No products found on homepage",
                    details={"url": context["settings"].store_url}
                )
            
            await product_link.click()
            await page.wait_for_load_state("networkidle")
            
            # Add to cart
            add_to_cart = page.locator('button[name="add"]').first
            await add_to_cart.click()
            
            # Wait for cart to update
            await page.wait_for_timeout(2000)
            
            # Check for cart abandonment script
            cart_recovery_present = await page.evaluate("""
                () => {
                    // Check for common cart abandonment scripts
                    const scripts = document.querySelectorAll('script');
                    for (let script of scripts) {
                        if (script.src.includes('cart-abandonment') || 
                            script.src.includes('recovery') ||
                            script.textContent.includes('abandonedCart')) {
                            return true;
                        }
                    }
                    return false;
                }
            """)
            
            if cart_recovery_present:
                return SkillResult(
                    skill_name=self.name,
                    status="PASS",
                    summary="Cart abandonment tracking detected",
                    details={"cart_recovery_present": True}
                )
            else:
                return SkillResult(
                    skill_name=self.name,
                    status="WARN",
                    summary="Cart abandonment tracking not detected",
                    details={"cart_recovery_present": False}
                )
        
        except Exception as e:
            logger.exception(f"Error in {self.name}")
            return SkillResult(
                skill_name=self.name,
                status="FAIL",
                summary=f"Error during execution: {str(e)}",
                details={"error": str(e)}
            )
```

### Registering Your Skill

Add your skill to the agent:

```python
from nano_sre.agent.core import Agent
from nano_sre.skills.cart_monitor import CartAbandonmentMonitor

# Create agent
agent = Agent(settings)

# Register your custom skill
cart_monitor = CartAbandonmentMonitor()
agent.register_skill(cart_monitor)
```

## Advanced Skill Patterns

### Using LLM for Analysis

Skills can leverage LLMs for intelligent analysis:

```python
class SmartCheckoutAnalyzer:
    """Uses LLM to analyze checkout flow issues."""
    
    def __init__(self, llm_client):
        self.llm_client = llm_client
        self.name = "SmartCheckoutAnalyzer"
    
    async def execute(self, context: Dict[str, Any]) -> SkillResult:
        page = context["page"]
        
        # Capture checkout flow
        await page.goto(f"{context['settings'].store_url}/cart")
        screenshot = await page.screenshot()
        
        # Use LLM to analyze
        prompt = """
        Analyze this Shopify checkout page screenshot.
        Check for:
        1. Visible payment options
        2. Trust badges
        3. Clear call-to-action buttons
        4. Any layout issues
        
        Return PASS if everything looks good, WARN if minor issues, FAIL if critical issues.
        """
        
        analysis = await self.llm_client.analyze_image(screenshot, prompt)
        
        return SkillResult(
            skill_name=self.name,
            status=analysis["status"],
            summary=analysis["summary"],
            details={"llm_analysis": analysis}
        )
```

### Network Request Monitoring

Monitor specific API calls:

```python
class APIMonitor:
    """Monitors API requests during page load."""
    
    def __init__(self, api_patterns: list[str]):
        self.api_patterns = api_patterns
        self.name = "APIMonitor"
        self.requests = []
    
    async def execute(self, context: Dict[str, Any]) -> SkillResult:
        page = context["page"]
        
        # Set up request listener
        page.on("request", lambda request: self.requests.append({
            "url": request.url,
            "method": request.method,
            "headers": request.headers
        }))
        
        # Navigate and wait
        await page.goto(context["settings"].store_url)
        await page.wait_for_load_state("networkidle")
        
        # Check if expected APIs were called
        matched_requests = [
            req for req in self.requests
            if any(pattern in req["url"] for pattern in self.api_patterns)
        ]
        
        if matched_requests:
            return SkillResult(
                skill_name=self.name,
                status="PASS",
                summary=f"Found {len(matched_requests)} API calls",
                details={"requests": matched_requests}
            )
        else:
            return SkillResult(
                skill_name=self.name,
                status="FAIL",
                summary="Expected API calls not found",
                details={"expected_patterns": self.api_patterns}
            )
```

### Performance Monitoring

Capture Core Web Vitals:

```python
class WebVitalsMonitor:
    """Monitors Core Web Vitals (LCP, FID, CLS)."""
    
    def __init__(self, thresholds: Dict[str, float] = None):
        self.name = "WebVitalsMonitor"
        self.thresholds = thresholds or {
            "lcp": 2500,  # ms
            "fid": 100,   # ms
            "cls": 0.1    # score
        }
    
    async def execute(self, context: Dict[str, Any]) -> SkillResult:
        page = context["page"]
        
        # Navigate to page
        await page.goto(context["settings"].store_url)
        
        # Capture Web Vitals using JavaScript
        metrics = await page.evaluate("""
            () => {
                return new Promise((resolve) => {
                    new PerformanceObserver((list) => {
                        const entries = list.getEntries();
                        const lcp = entries[entries.length - 1];
                        resolve({
                            lcp: lcp.renderTime || lcp.loadTime
                        });
                    }).observe({ entryTypes: ['largest-contentful-paint'] });
                    
                    // Set timeout in case LCP doesn't fire
                    setTimeout(() => resolve({ lcp: null }), 5000);
                });
            }
        """)
        
        # Evaluate against thresholds
        issues = []
        if metrics.get("lcp") and metrics["lcp"] > self.thresholds["lcp"]:
            issues.append(f"LCP too slow: {metrics['lcp']}ms")
        
        if issues:
            return SkillResult(
                skill_name=self.name,
                status="WARN",
                summary=f"Performance issues detected: {', '.join(issues)}",
                details={"metrics": metrics, "thresholds": self.thresholds}
            )
        else:
            return SkillResult(
                skill_name=self.name,
                status="PASS",
                summary="Core Web Vitals within thresholds",
                details={"metrics": metrics}
            )
```

## Testing Your Skill

Create tests for your custom skill:

```python
# tests/test_cart_monitor.py

import pytest
from unittest.mock import AsyncMock, MagicMock
from nano_sre.skills.cart_monitor import CartAbandonmentMonitor

@pytest.mark.asyncio
async def test_cart_monitor_success():
    """Test cart monitor with successful cart abandonment detection."""
    skill = CartAbandonmentMonitor()
    
    # Mock page
    mock_page = AsyncMock()
    mock_page.goto = AsyncMock()
    mock_page.locator = MagicMock(return_value=AsyncMock(count=AsyncMock(return_value=1)))
    mock_page.evaluate = AsyncMock(return_value=True)
    
    # Mock context
    context = {
        "page": mock_page,
        "settings": MagicMock(store_url="https://test.myshopify.com")
    }
    
    # Execute skill
    result = await skill.execute(context)
    
    # Assertions
    assert result.status == "PASS"
    assert "tracking detected" in result.summary.lower()

@pytest.mark.asyncio
async def test_cart_monitor_no_recovery():
    """Test cart monitor when cart abandonment not detected."""
    skill = CartAbandonmentMonitor()
    
    mock_page = AsyncMock()
    mock_page.evaluate = AsyncMock(return_value=False)
    
    context = {
        "page": mock_page,
        "settings": MagicMock(store_url="https://test.myshopify.com")
    }
    
    result = await skill.execute(context)
    
    assert result.status == "WARN"
```

## Packaging and Distribution

### As a Separate Package

Create a standalone package for your skill:

```
my-nano-sre-skills/
├── pyproject.toml
├── README.md
└── src/
    └── my_skills/
        ├── __init__.py
        └── cart_monitor.py
```

`pyproject.toml`:

```toml
[project]
name = "my-nano-sre-skills"
version = "0.1.0"
dependencies = [
    "shopify-nano-sre>=0.1.0",
]
```

Install and use:

```bash
pip install my-nano-sre-skills
```

```python
from my_skills import CartAbandonmentMonitor

agent.register_skill(CartAbandonmentMonitor())
```

### Contributing to Core

To contribute your skill to the core project:

1. Fork the repository
2. Add your skill to `src/nano_sre/skills/`
3. Add tests to `tests/`
4. Update documentation
5. Submit a pull request

## Best Practices

### Error Handling

Always handle errors gracefully:

```python
try:
    # Skill logic
    result = await self.do_monitoring(page)
except TimeoutError:
    return SkillResult(
        skill_name=self.name,
        status="WARN",
        summary="Timeout while monitoring",
        details={"error_type": "timeout"}
    )
except Exception as e:
    logger.exception(f"Unexpected error in {self.name}")
    return SkillResult(
        skill_name=self.name,
        status="FAIL",
        summary=f"Unexpected error: {str(e)}",
        details={"error": str(e), "error_type": type(e).__name__}
    )
```

### Status Guidelines

Use statuses consistently:

- **PASS**: Everything working as expected
- **WARN**: Minor issues or degraded performance
- **FAIL**: Critical failures or blocked functionality

### Performance

Optimize skill execution:

```python
# Bad: Sequential waits
await page.wait_for_selector("#element1")
await page.wait_for_selector("#element2")

# Good: Parallel waits
await asyncio.gather(
    page.wait_for_selector("#element1"),
    page.wait_for_selector("#element2")
)
```

### Configurability

Make skills configurable:

```python
class ConfigurableSkill:
    def __init__(
        self,
        timeout: int = 30000,
        retries: int = 3,
        custom_selectors: list[str] = None
    ):
        self.timeout = timeout
        self.retries = retries
        self.custom_selectors = custom_selectors or []
```

## Example Use Cases

### App-Specific Monitoring

Monitor a specific Shopify app:

```python
class ProductReviewsMonitor:
    """Monitors if product reviews app is loading."""
    
    async def execute(self, context):
        page = context["page"]
        
        # Navigate to product page
        await page.goto(f"{context['settings'].store_url}/products/sample")
        
        # Check for reviews widget
        reviews_widget = page.locator('[data-app="product-reviews"]')
        
        if await reviews_widget.count() > 0:
            return SkillResult(
                skill_name="ProductReviewsMonitor",
                status="PASS",
                summary="Reviews widget loaded successfully",
                details={}
            )
        else:
            return SkillResult(
                skill_name="ProductReviewsMonitor",
                status="FAIL",
                summary="Reviews widget not found",
                details={}
            )
```

### Multi-Currency Monitoring

```python
class CurrencyMonitor:
    """Monitors multi-currency functionality."""
    
    async def execute(self, context):
        page = context["page"]
        await page.goto(context["settings"].store_url)
        
        # Check for currency selector
        currency_selector = page.locator('[data-currency-selector]')
        
        if await currency_selector.count() == 0:
            return SkillResult(
                skill_name="CurrencyMonitor",
                status="FAIL",
                summary="Currency selector not found",
                details={}
            )
        
        # Try changing currency
        await currency_selector.click()
        await page.locator('[data-currency="EUR"]').click()
        await page.wait_for_timeout(2000)
        
        # Verify price changed
        # Implementation details...
        
        return SkillResult(
            skill_name="CurrencyMonitor",
            status="PASS",
            summary="Currency switching works",
            details={}
        )
```

## Resources

- **Playwright Documentation**: [playwright.dev](https://playwright.dev)
- **Shopify Development**: [shopify.dev](https://shopify.dev)
- **Example Skills**: Browse built-in skills in `src/nano_sre/skills/`

## Next Steps

Now that you can create custom skills:

1. Identify specific monitoring needs for your store
2. Create skills targeting those needs
3. Test thoroughly with various scenarios
4. Share useful skills with the community
5. Integrate into your CI/CD pipeline

Happy monitoring! 🚀
