# Shopify Nano-SRE Architecture

This document provides a comprehensive overview of the Shopify Nano-SRE architecture, including system diagrams, decision logs, and extension points for building custom skills.

## Table of Contents

- [System Overview](#system-overview)
- [Architecture Diagrams](#architecture-diagrams)
  - [Agent Loop](#agent-loop)
  - [Skill Flow](#skill-flow)
  - [Data Store Schema](#data-store-schema)
- [Architectural Decisions](#architectural-decisions)
  - [Why Playwright](#why-playwright)
  - [Why SQLite](#why-sqlite)
  - [Why Async](#why-async)
- [Extension Points](#extension-points)
  - [Creating Custom Skills](#creating-custom-skills)
  - [Custom Triggers](#custom-triggers)
  - [Custom Alerters](#custom-alerters)

---

## System Overview

Shopify Nano-SRE is a lightweight, AI-powered Site Reliability Engineering tool that continuously monitors Shopify stores using synthetic monitoring and LLM-driven diagnostics. The system follows a modular, agent-based architecture with pluggable skills, flexible triggers, and configurable alerting.

**Core Components:**

1. **Agent Core** - Orchestrates skill execution and manages the monitoring lifecycle
2. **Skills** - Pluggable monitoring modules (e.g., PixelAuditor, HeadlessProbe)
3. **Data Store** - SQLite-based persistence for baselines, incidents, and check runs
4. **Diagnosis Module** - LLM-powered analysis of failures and warnings
5. **Alerter** - Multi-channel notification system (Discord, Slack, stdout)
6. **Trigger System** - Interval-based and webhook-based execution triggers

---

## Architecture Diagrams

### Agent Loop

The agent loop is the heart of Nano-SRE, orchestrating continuous monitoring and diagnosis.

```
┌─────────────────────────────────────────────────────────────────┐
│                         Agent Loop                               │
│                                                                   │
│  ┌──────────────┐                                                │
│  │   Trigger    │ ◄────── Interval Timer (e.g., every 30 min)   │
│  │   Manager    │ ◄────── Webhook Events (GitHub Deployments)   │
│  └──────┬───────┘                                                │
│         │                                                         │
│         ▼                                                         │
│  ┌──────────────┐                                                │
│  │ Skill        │  ┌─────────────────────────────────┐           │
│  │ Execution    │  │ Skills (run sequentially):      │           │
│  │              │  │  1. HeadlessProbe               │           │
│  │              │  │  2. PixelAuditor                │           │
│  │              │  │  3. VisualAuditor               │           │
│  │              │  │  4. ShopifyDoctor               │           │
│  └──────┬───────┘  └─────────────────────────────────┘           │
│         │                                                         │
│         ▼                                                         │
│  ┌──────────────┐                                                │
│  │  Collect     │ ◄── SkillResult objects (PASS/WARN/FAIL)      │
│  │  Results     │                                                │
│  └──────┬───────┘                                                │
│         │                                                         │
│         ▼                                                         │
│  ┌──────────────┐                                                │
│  │  Diagnose    │ ◄── LLM Analysis (for WARN/FAIL only)         │
│  │  Failures    │ ──► Root cause, severity, remediation         │
│  └──────┬───────┘                                                │
│         │                                                         │
│         ▼                                                         │
│  ┌──────────────┐                                                │
│  │   Record     │ ──► SQLite: check_runs, incidents             │
│  │   to Store   │ ──► Update baselines                          │
│  └──────┬───────┘                                                │
│         │                                                         │
│         ▼                                                         │
│  ┌──────────────┐                                                │
│  │   Send       │ ──► Discord / Slack / stdout                  │
│  │   Alerts     │ ──► Rate-limited (1 alert/hour default)       │
│  └──────┬───────┘                                                │
│         │                                                         │
│         ▼                                                         │
│  ┌──────────────┐                                                │
│  │   Wait for   │ ◄── Sleep until next interval                 │
│  │   Next       │ ◄── Or webhook event arrives                  │
│  │   Trigger    │                                                │
│  └──────────────┘                                                │
│         │                                                         │
│         └────────────────► (Loop back to Trigger)                │
└─────────────────────────────────────────────────────────────────┘
```

**Key Flow:**
1. Trigger fires (interval or webhook)
2. Agent executes all registered skills sequentially
3. Each skill returns a `SkillResult` (PASS/WARN/FAIL)
4. Failed/warned results are sent to the diagnosis module (LLM)
5. All results are persisted to SQLite
6. Alerts are sent via configured channels (with rate limiting)
7. Agent waits for next trigger

---

### Skill Flow

Skills are self-contained monitoring modules that execute checks and return structured results.

```
┌─────────────────────────────────────────────────────────────────┐
│                      Skill Execution Flow                        │
│                                                                   │
│  ┌──────────────┐                                                │
│  │   Agent      │                                                │
│  │   Context    │ ──► { "page": Playwright Page,                │
│  │              │      "settings": Settings,                     │
│  │              │      "store": Store }                          │
│  └──────┬───────┘                                                │
│         │                                                         │
│         ▼                                                         │
│  ┌──────────────────────────────────────────────────────┐        │
│  │              Skill.run(context)                      │        │
│  │                                                       │        │
│  │  ┌────────────────────────────────────────────────┐  │        │
│  │  │  1. Setup & Initialization                     │  │        │
│  │  │     - Reset tracking state                     │  │        │
│  │  │     - Inject hooks (e.g., analytics.js)        │  │        │
│  │  │     - Set up network interception              │  │        │
│  │  └────────────────────────────────────────────────┘  │        │
│  │                      │                                │        │
│  │                      ▼                                │        │
│  │  ┌────────────────────────────────────────────────┐  │        │
│  │  │  2. Execute Monitoring                         │  │        │
│  │  │     - Navigate to pages                        │  │        │
│  │  │     - Capture events/metrics                   │  │        │
│  │  │     - Take screenshots                         │  │        │
│  │  │     - Measure performance                      │  │        │
│  │  └────────────────────────────────────────────────┘  │        │
│  │                      │                                │        │
│  │                      ▼                                │        │
│  │  ┌────────────────────────────────────────────────┐  │        │
│  │  │  3. Validation & Analysis                      │  │        │
│  │  │     - Compare against baselines                │  │        │
│  │  │     - Validate event payloads                  │  │        │
│  │  │     - Check for required fields                │  │        │
│  │  └────────────────────────────────────────────────┘  │        │
│  │                      │                                │        │
│  │                      ▼                                │        │
│  │  ┌────────────────────────────────────────────────┐  │        │
│  │  │  4. Generate SkillResult                       │  │        │
│  │  │     - Determine status (PASS/WARN/FAIL)        │  │        │
│  │  │     - Create summary message                   │  │        │
│  │  │     - Attach details and screenshots           │  │        │
│  │  └────────────────────────────────────────────────┘  │        │
│  └──────────────────────────────────────────────────────┘        │
│                       │                                           │
│                       ▼                                           │
│  ┌──────────────────────────────────────────────────────┐        │
│  │  SkillResult                                         │        │
│  │  {                                                   │        │
│  │    "skill_name": "pixel_auditor",                    │        │
│  │    "status": "WARN",                                 │        │
│  │    "summary": "3 validation errors found",           │        │
│  │    "details": {                                      │        │
│  │      "total_events": 15,                             │        │
│  │      "validation_errors": [...],                     │        │
│  │      "pixel_hits": {...}                             │        │
│  │    },                                                │        │
│  │    "screenshots": ["path/to/screenshot.png"],        │        │
│  │    "timestamp": "2026-02-17T21:00:00Z",              │        │
│  │    "error": null                                     │        │
│  │  }                                                   │        │
│  └──────────────────────────────────────────────────────┘        │
└─────────────────────────────────────────────────────────────────┘
```

**Built-in Skills:**

1. **PixelAuditor** - Validates analytics pixels and tracking events
2. **HeadlessProbe** - Synthetic shopper journey (product → cart → checkout)
3. **VisualAuditor** - Layout drift detection using LLM vision
4. **ShopifyDoctor** - MCP-powered API error diagnosis
5. **MCPAdvisor** - Shopify Dev MCP query interface

---

### MCP Integration

Nano-SRE implements the **Model Context Protocol (MCP)** to bridge monitoring data with official documentation and expert knowledge.

#### Architecture

```
┌─────────────────┐       ┌─────────────────┐       ┌─────────────────┐
│                 │       │                 │       │                 │
│  Nano-SRE Agent │ <───> │   MCP Client    │ <───> │ Shopify Dev MCP │
│                 │       │    (Stdio)      │       │    (Server)     │
└─────────────────┘       └─────────────────┘       └─────────────────┘
         │                         ▲                         │
         │                         │                         │
         └──── Captured Errors ────┘        Query Shopify Docs
               (Console/API)                & API References
```

#### Implementation Details

- **Stdio Client**: The agent launches the MCP server as a subprocess (e.g., via `npx`).
- **Workflow**:
  1. The `mcp_advisor` skill identifies errors captured by other skills (like `shopify_doctor` or `headless_probe`).
  2. It initializes a "conversation" with the MCP server using the `learn_shopify_api` tool (Admin, Liquid, or Storefront).
  3. It searches for solutions using the `search_docs_chunks` tool.
  4. Diagnostics are surfaced in the final incident report.

---

### Data Store Schema

The SQLite database maintains state across monitoring runs.

```
┌─────────────────────────────────────────────────────────────────┐
│                     SQLite Database Schema                       │
│                        (nano_sre.db)                             │
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  TABLE: check_runs                                        │   │
│  │                                                            │   │
│  │  - id              INTEGER PRIMARY KEY                    │   │
│  │  - timestamp       TEXT (ISO 8601)                        │   │
│  │  - store_url       TEXT                                   │   │
│  │  - skill_name      TEXT                                   │   │
│  │  - status          TEXT (PASS/WARN/FAIL)                  │   │
│  │  - summary         TEXT                                   │   │
│  │  - details         TEXT (JSON)                            │   │
│  │  - screenshots     TEXT (JSON array)                      │   │
│  │  - error           TEXT (nullable)                        │   │
│  │                                                            │   │
│  │  INDEX: idx_check_runs (timestamp, store_url, skill_name) │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  TABLE: baselines                                         │   │
│  │                                                            │   │
│  │  - id              INTEGER PRIMARY KEY                    │   │
│  │  - skill_name      TEXT                                   │   │
│  │  - store_url       TEXT                                   │   │
│  │  - baseline_data   TEXT (JSON)                            │   │
│  │  - created_at      TEXT (ISO 8601)                        │   │
│  │  - updated_at      TEXT (ISO 8601)                        │   │
│  │                                                            │   │
│  │  INDEX: idx_baselines (skill_name, store_url) UNIQUE      │   │
│  │                                                            │   │
│  │  Purpose: Store performance baselines for comparison      │   │
│  │  Example: { "lcp_ms": 1200, "ttfb_ms": 350 }              │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  TABLE: incidents                                         │   │
│  │                                                            │   │
│  │  - id              INTEGER PRIMARY KEY                    │   │
│  │  - created_at      TEXT (ISO 8601)                        │   │
│  │  - resolved_at     TEXT (nullable, ISO 8601)              │   │
│  │  - store_url       TEXT                                   │   │
│  │  - skill_name      TEXT                                   │   │
│  │  - severity        TEXT (P0/P1/P2/P3)                     │   │
│  │  - title           TEXT                                   │   │
│  │  - details         TEXT (JSON)                            │   │
│  │  - status          TEXT (open/resolved)                   │   │
│  │                                                            │   │
│  │  INDEX: idx_incidents (store_url, status)                 │   │
│  │                                                            │   │
│  │  Purpose: Track ongoing and historical incidents          │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘

Relationships:
- check_runs ─┬─ N:1 ─► store_url
              └─ N:1 ─► skill_name

- baselines  ──── 1:1 ─► (skill_name, store_url) UNIQUE

- incidents  ─┬─ N:1 ─► store_url
              └─ N:1 ─► skill_name
```

**Data Flow:**

1. **check_runs**: Every skill execution creates a record
2. **baselines**: Updated when performance metrics are within acceptable ranges
3. **incidents**: Created when FAIL status occurs, resolved when checks pass

---

## Architectural Decisions

### Why Playwright

**Decision:** Use Playwright as the browser automation engine

**Context:**

Shopify stores are increasingly complex JavaScript applications with hydration, client-side routing, and dynamic pixel firing. Traditional HTTP-based monitoring (e.g., `requests`, `httpx`) cannot:

- Execute JavaScript to trigger analytics pixels
- Wait for React/Vue hydration to complete
- Capture real user-like performance metrics (LCP, TTFB)
- Detect layout shifts or visual regressions

**Alternatives Considered:**

1. **Selenium** - More mature but heavier, slower startup, less reliable
2. **Puppeteer** - Chrome-only, no Firefox/WebKit support
3. **HTTP client (requests/httpx)** - Cannot execute JavaScript

**Decision Rationale:**

✅ **Playwright Advantages:**

- **Fast & reliable**: Auto-waiting, retry logic built-in
- **Multi-browser**: Chromium, Firefox, WebKit for cross-browser testing
- **Modern web support**: Handles SPAs, hydration, service workers
- **Network interception**: Capture pixel hits without external proxies
- **Performance metrics**: Built-in Web Vitals (LCP, FID, CLS)
- **Mobile viewports**: iPhone 17 Pro emulation out-of-the-box
- **Screenshot API**: Visual regression testing support
- **Headless & headed modes**: Debug locally, run headless in CI/Docker

**Use Cases in Nano-SRE:**

- **HeadlessProbe**: Navigate product → cart → checkout flow
- **PixelAuditor**: Intercept network requests to validate pixel hits
- **VisualAuditor**: Capture screenshots for LLM-based layout analysis

**Trade-offs:**

❌ **Drawbacks:**

- Heavier resource usage than HTTP clients (~100MB RAM per browser)
- Requires browser binary installation (handled in Docker)
- Slower execution time vs. pure HTTP checks (acceptable for synthetic monitoring)

**Conclusion:** Playwright is the optimal choice for realistic, JavaScript-aware Shopify monitoring.

---

### Why SQLite

**Decision:** Use SQLite as the primary data store

**Context:**

Nano-SRE needs to store:

- Historical check runs for trend analysis
- Performance baselines for anomaly detection
- Incident tracking (open/resolved)
- Screenshot paths and metadata

**Alternatives Considered:**

1. **PostgreSQL** - Full-featured RDBMS, but overkill for single-store monitoring
2. **JSON files** - Simple but no indexing, poor query performance
3. **Redis** - In-memory, loses data on restart unless persistence configured
4. **Cloud DB (DynamoDB, Firestore)** - Requires external dependencies, not local-first

**Decision Rationale:**

✅ **SQLite Advantages:**

- **Local-first**: No external database server required
- **Zero configuration**: Single file (`nano_sre.db`), no setup needed
- **Serverless**: Embedded in Python process, no separate daemon
- **ACID compliant**: Reliable transaction support
- **Fast for reads**: Efficient for historical queries (last 100 runs)
- **Portable**: Copy/backup is just a file copy
- **Great Python support**: `sqlite3` stdlib, `sqlite-utils` for schema management
- **Low overhead**: <1MB memory, ~10KB disk per check run

**Use Cases in Nano-SRE:**

1. **Baselines**: Store `LCP`, `TTFB` per skill/store for regression detection
2. **Check runs**: Historical log for debugging and trend analysis
3. **Incidents**: Track when issues opened/resolved, duration, severity

**Schema Design:**

```python
# Example query: Get recent check runs
store.db.execute("""
    SELECT skill_name, status, timestamp
    FROM check_runs
    WHERE store_url = ? AND timestamp > datetime('now', '-7 days')
    ORDER BY timestamp DESC
""", [store_url])
```

**Trade-offs:**

❌ **Limitations:**

- **Single-writer**: Not suitable for multi-process workers (okay for agent model)
- **No built-in replication**: Manual backup required for disaster recovery
- **Size limits**: Degrades after ~10GB (years of data), mitigated by pruning

✅ **Mitigation:**

- Rotate old data after 90 days (configurable)
- For multi-store SaaS, use one DB per store or upgrade to PostgreSQL

**Conclusion:** SQLite is ideal for local-first, single-agent deployments with predictable data volume.

---

### Why Async

**Decision:** Use `asyncio` for the agent core and skill execution

**Context:**

Nano-SRE performs I/O-heavy operations:

- Browser automation (waiting for page loads)
- Network requests (webhooks, LLM API calls)
- Database writes (non-blocking preferred)

**Alternatives Considered:**

1. **Synchronous (blocking)** - Simple but wasteful during I/O wait
2. **Threading** - GIL contention, harder to reason about
3. **Multiprocessing** - Overkill for I/O-bound tasks, complex state sharing

**Decision Rationale:**

✅ **Async (asyncio) Advantages:**

- **Non-blocking I/O**: Agent can wait for page loads without blocking other skills
- **Playwright compatibility**: Native async API (`async_playwright()`)
- **LLM API efficiency**: Parallel LLM calls when diagnosing multiple failures
- **Event-driven**: Natural fit for webhook triggers and interval timers
- **Resource efficient**: Single-threaded, low memory overhead
- **Modern Python**: First-class support in 3.11+, excellent tooling

**Code Example:**

```python
# Async skill execution
async def execute_skills(self, skill_names):
    results = []
    for skill_name in skill_names:
        skill = self.skills[skill_name]
        result = await skill.run(self.context)  # Non-blocking
        results.append(result)
    return results

# Async LLM diagnosis
async def diagnose(skill_result):
    response = await litellm.acompletion(  # Non-blocking
        model="gpt-4",
        messages=[...]
    )
    return response
```

**Performance Benefits:**

| Operation               | Sync Time | Async Time | Speedup |
|------------------------|-----------|------------|---------|
| Page load (3s)         | 3s        | 3s         | 1x      |
| 3 LLM calls (2s each)  | 6s        | 2s         | 3x      |
| Total pipeline         | 9s        | 5s         | 1.8x    |

**Trade-offs:**

❌ **Complexity:**

- Steeper learning curve than sync code
- Requires `async`/`await` discipline across codebase
- Debugging async code can be harder

✅ **Mitigation:**

- Use clear abstractions (`Agent`, `Skill`, `Trigger`)
- Comprehensive type hints for IDE support
- Logging at key async boundaries

**Conclusion:** Async is essential for efficient I/O-bound operations and scales well for future parallel skill execution.

---

## Extension Points

Nano-SRE is designed to be extensible. Here are the primary extension points for building custom functionality.

### Creating Custom Skills

Skills are the core extension mechanism. A custom skill is a class that inherits from `Skill` and implements two methods:

#### Skill Interface

```python
from abc import ABC, abstractmethod
from typing import Any
from nano_sre.agent.core import Skill, SkillResult

class MyCustomSkill(Skill):
    """Custom skill for monitoring XYZ."""

    @abstractmethod
    def name(self) -> str:
        """Return the skill name (unique identifier)."""
        return "my_custom_skill"

    @abstractmethod
    async def run(self, context: dict[str, Any]) -> SkillResult:
        """
        Execute the skill and return results.

        Args:
            context: Agent context containing:
                - page: Playwright Page object
                - settings: Settings instance
                - store: Store instance (optional)

        Returns:
            SkillResult with status (PASS/WARN/FAIL)
        """
        # Your monitoring logic here
        pass
```

#### Example: Custom Checkout Validator

```python
from nano_sre.agent.core import Skill, SkillResult
from playwright.async_api import Page

class CheckoutValidator(Skill):
    """Validates checkout flow completes without errors."""

    def name(self) -> str:
        return "checkout_validator"

    async def run(self, context: dict[str, Any]) -> SkillResult:
        page: Page = context.get("page")

        try:
            # Navigate to checkout
            await page.goto("https://store.myshopify.com/checkout")

            # Fill in checkout form
            await page.fill('input[name="email"]', "test@example.com")
            await page.fill('input[name="firstName"]', "Test")
            # ... more form fields

            # Check for error messages
            error_selector = '.error-message'
            has_errors = await page.locator(error_selector).count() > 0

            if has_errors:
                error_text = await page.locator(error_selector).inner_text()
                return SkillResult(
                    skill_name=self.name(),
                    status="FAIL",
                    summary=f"Checkout error: {error_text}",
                    error=error_text,
                )

            # Success case
            return SkillResult(
                skill_name=self.name(),
                status="PASS",
                summary="Checkout completed successfully",
                details={"checkout_time_ms": 1200},
            )

        except Exception as e:
            return SkillResult(
                skill_name=self.name(),
                status="FAIL",
                summary=f"Checkout validation failed: {str(e)}",
                error=str(e),
            )
```

#### Registering Your Skill

```python
from nano_sre.agent.core import Agent
from nano_sre.config.settings import get_settings

# Create agent
settings = get_settings()
agent = Agent(settings)

# Register your custom skill
custom_skill = CheckoutValidator()
agent.register_skill(custom_skill)

# Execute all skills (including your custom one)
results = await agent.execute_skills()
```

#### Best Practices for Custom Skills

1. **Return structured data**: Use the `details` field for metrics and validation errors
2. **Use WARN for degraded state**: Reserve FAIL for complete failures
3. **Capture screenshots**: Add screenshot paths to `SkillResult.screenshots` for debugging
4. **Validate inputs**: Check that required context keys exist before use
5. **Handle exceptions gracefully**: Wrap in try/except and return FAIL status
6. **Add baselines**: Use `context["store"].update_baseline()` for performance metrics

---

### Custom Triggers

Extend the trigger system to fire checks on custom events.

#### Example: Custom CloudWatch Event Trigger

```python
from nano_sre.agent.trigger import IntervalTrigger
from typing import Callable, Any
import asyncio

class CloudWatchEventTrigger:
    """Trigger from AWS CloudWatch Events."""

    def __init__(self, queue_url: str):
        self.queue_url = queue_url
        self.events: list[dict] = []

    async def poll_sqs(self):
        """Poll SQS queue for CloudWatch events."""
        import boto3
        sqs = boto3.client('sqs')

        while True:
            response = sqs.receive_message(
                QueueUrl=self.queue_url,
                MaxNumberOfMessages=1,
                WaitTimeSeconds=20
            )

            if 'Messages' in response:
                for msg in response['Messages']:
                    self.events.append(msg)
                    sqs.delete_message(
                        QueueUrl=self.queue_url,
                        ReceiptHandle=msg['ReceiptHandle']
                    )

    def has_pending_events(self) -> bool:
        return len(self.events) > 0

    def pop_event(self) -> dict:
        return self.events.pop(0) if self.events else {}
```

---

### Custom Alerters

Build custom alerting channels beyond Discord/Slack.

#### Example: PagerDuty Alerter

```python
from nano_sre.agent.core import SkillResult
import httpx

class PagerDutyAlerter:
    """Send alerts to PagerDuty."""

    def __init__(self, integration_key: str):
        self.integration_key = integration_key
        self.url = "https://events.pagerduty.com/v2/enqueue"

    async def send_alert(self, skill_result: SkillResult):
        """Send PagerDuty event."""
        if skill_result.status != "FAIL":
            return  # Only alert on failures

        payload = {
            "routing_key": self.integration_key,
            "event_action": "trigger",
            "payload": {
                "summary": skill_result.summary,
                "severity": "error",
                "source": "shopify-nano-sre",
                "custom_details": skill_result.details,
            }
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(self.url, json=payload)
            return response.status_code == 202
```

#### Integration Example

```python
from nano_sre.agent.core import Agent

agent = Agent(settings)
pagerduty = PagerDutyAlerter(integration_key="xxx")

# Execute skills
results = await agent.execute_skills()

# Alert on failures
for result in results:
    if result.status == "FAIL":
        await pagerduty.send_alert(result)
```

---

## Contributing

We welcome contributions to Nano-SRE! Here are some areas where custom skills would be valuable:

1. **App-specific skills**: Klaviyo integration check, Recharge subscription validation
2. **Performance skills**: Core Web Vitals monitoring, Lighthouse score tracking
3. **Accessibility skills**: WCAG compliance checker
4. **SEO skills**: Meta tag validation, structured data verification
5. **Security skills**: CSP header validation, HTTPS enforcement check

**Contribution Guidelines:**

- Follow the skill interface pattern
- Include unit tests for your skill
- Add documentation with usage examples
- Submit PR with skill description and use case

For more details, see [CONTRIBUTING.md](../CONTRIBUTING.md) (placeholder).

---

## References

- [Playwright Documentation](https://playwright.dev/)
- [SQLite Documentation](https://www.sqlite.org/docs.html)
- [Python asyncio Guide](https://docs.python.org/3/library/asyncio.html)
- [Shopify Checkout Extensibility](https://shopify.dev/docs/apps/checkout)
- [LiteLLM Documentation](https://docs.litellm.ai/)

---

**Last Updated:** 2026-02-17  
**Version:** 1.0.0
