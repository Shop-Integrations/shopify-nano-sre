# Shopify Nano-SRE — Copilot Task Checklist

> Assign tasks to agents and track status per item.
> Status key: [ ] TODO [-] IN-PROGRESS [x] DONE

---

## Group 1 — Project Scaffolding (parallel)

- [ ] Task 1.1: Initialize Python Project
  - [ ] Set up `pyproject.toml` (or `setup.cfg`) with name `shopify-nano-sre`, version `0.1.0`, Python >=3.11
  - [ ] Create directory layout:
    - [ ] `shopify-nano-sre/src/nano_sre/__init__.py`
    - [ ] `shopify-nano-sre/src/nano_sre/cli.py`
    - [ ] `shopify-nano-sre/src/nano_sre/agent/`
    - [ ] `shopify-nano-sre/src/nano_sre/skills/`
    - [ ] `shopify-nano-sre/src/nano_sre/db/`
    - [ ] `shopify-nano-sre/src/nano_sre/config/`
    - [ ] `shopify-nano-sre/tests/`
    - [ ] `shopify-nano-sre/pyproject.toml`
    - [ ] `shopify-nano-sre/.env.example`
    - [ ] `shopify-nano-sre/README.md`
  - [ ] Add dependencies: `playwright`, `litellm`, `rich`, `sqlite-utils`, `pydantic`, `pydantic-settings`, `click`, `httpx`, `pytest-asyncio`, `pytest-playwright`

- [ ] Task 1.2: Create README.md with Positioning
  - [ ] Hero tagline: "The open-source AI engineer that monitors your Shopify store 24/7."
  - [ ] Feature badges (Python, Playwright, MIT License, etc.)
  - [ ] Monitoring comparison table (Pingdom vs Datadog vs Nano-SRE)
  - [ ] Quick-start install section (placeholder commands)
  - [ ] "How it Works" diagram (Mermaid or ASCII)
  - [ ] "Why Nano-SRE?" section highlighting Checkout Extensibility migration
  - [ ] CTA to `shopintegrations.com` in footer

- [ ] Task 1.3: Set Up Dev Tooling & CI
  - [ ] `.github/workflows/ci.yml` (pytest, ruff, mypy)
  - [ ] `.github/workflows/release.yml` (PyPI on tags)
  - [ ] `ruff.toml`
  - [ ] `mypy.ini`
  - [ ] `.pre-commit-config.yaml` (ruff + mypy)
  - [ ] `Dockerfile` (minimal Python image)

- [ ] Task 1.4: Add License & Security Policy
  - [ ] `LICENSE` (MIT)
  - [ ] `SECURITY.md` (disclosure policy + contact)

---

## Group 2 — Core Agent Engine (parallel)

- [ ] Task 2.1: Build the Configuration System
  - [ ] Create `src/nano_sre/config/settings.py`
  - [ ] Use `pydantic-settings` to load `.env` and CLI
  - [ ] Fields: `store_url`, `shopify_admin_api_key` (optional), `llm_provider` (openai/anthropic/ollama), `llm_api_key`, `llm_model`, `alert_webhook_url`, `check_interval_minutes`, `sqlite_db_path`
  - [ ] Validate URLs, sensible defaults
  - [ ] `.env.example` with all fields documented

- [ ] Task 2.2: Build the Agent Core Loop
  - [ ] Create `src/nano_sre/agent/core.py`
  - [ ] Agent loop: Trigger -> Observe -> Diagnose -> Act
  - [ ] `Skill` base class with `name()` and `run(context) -> SkillResult`
  - [ ] `SkillResult` dataclass: `status`, `summary`, `details`, `screenshots`
  - [ ] Load skills, execute sequentially, collect results, diagnose, dispatch alerts
  - [ ] Use `asyncio` throughout

- [ ] Task 2.3: Set Up SQLite State Management
  - [ ] Create `src/nano_sre/db/store.py` using `sqlite-utils`
  - [ ] Tables: `check_runs`, `baselines`, `incidents`
  - [ ] Helpers: `record_check()`, `get_latest_baseline()`, `update_baseline()`, `create_incident()`, `resolve_incident()`

- [ ] Task 2.4: Add Scheduler + Webhook Trigger
  - [ ] Create `src/nano_sre/agent/trigger.py`
  - [ ] CRON-like interval scheduling for `watch`
  - [ ] Optional webhook receiver for GitHub Deployment events
  - [ ] Normalize trigger metadata into context

- [ ] Task 2.5: Add Data Privacy + Redaction
  - [ ] Create `src/nano_sre/agent/privacy.py`
  - [ ] Redact secrets in logs/reports (API keys, tokens, emails)
  - [ ] Optional `--redact` flag to blur PII selectors in screenshots
  - [ ] Document data handling in README

---

## Group 3 — Skills Implementation (parallel)

- [ ] Task 3.1: Skill A — "Synthetic Shopper"
  - [ ] Use Playwright async API for shopping flow
  - [ ] Navigate to `store_url`
  - [ ] Click first product link using `get_by_role`
  - [ ] Click "Add to Cart"
  - [ ] Verify cart drawer/cart page
  - [ ] Navigate to checkout (no payment)
  - [ ] Handle popups/modals, capture screenshot on obstruction
  - [ ] Capture performance metrics (load time, LCP)
  - [ ] Return `SkillResult` with PASS/WARN/FAIL
  - [ ] Include mobile viewport (iPhone 14 Pro)

- [ ] Task 3.2: Skill B — "Pixel Auditor"
  - [ ] Use `page.route()` or `page.on("request")` to intercept requests
  - [ ] Track Facebook, GA, TikTok pixel hits
  - [ ] Inject script via `page.add_init_script()` to hook `Shopify.analytics` / `analytics.subscribe`
  - [ ] Verify events: `page_view`, `view_item`, `add_to_cart`, `begin_checkout`, `purchase`/`checkout_completed`
  - [ ] Validate payloads: `value`, `currency`, `transaction_id`
  - [ ] Return "Pixel Health Report" as `SkillResult`

- [ ] Task 3.3: Skill C — "Visual Layout Sentinel"
  - [ ] Capture full-page screenshots: Home, Product, Collection, Cart
  - [ ] Store baselines in `baselines/`
  - [ ] Pixel diff with `Pillow` threshold (e.g., >5%)
  - [ ] If threshold exceeded, send images to LLM (Vision) with comparison prompt
  - [ ] Return `SkillResult` with diff percentage and assessment
  - [ ] Support `--update-baseline` CLI flag

- [ ] Task 3.4: Skill D — "Shopify Doctor" (API Health Check)
  - [ ] If `shopify_admin_api_key` configured, query Admin GraphQL
  - [ ] Check: active theme has no Liquid errors (`shop.errors`)
  - [ ] Check: published products have images and prices
  - [ ] Check: no deprecated API version in use
  - [ ] If no API key, skip with note
  - [ ] Capture storefront console errors (`page.on("console")`)
  - [ ] Return `SkillResult`

- [ ] Task 3.5: Skill E — "Headless Health Probe"
  - [ ] Storefront API rate-limit probe (detect 429 + retry headers)
  - [ ] Hydration mismatch detection (React/Next.js warnings)
  - [ ] ISR staleness check (API price/inventory vs DOM)
  - [ ] Return `SkillResult` with PASS/WARN/FAIL

- [ ] Task 3.6: Skill F — "Shopify Dev MCP" Integration
  - [ ] Create `src/nano_sre/skills/mcp_advisor.py` (or integrate into `shopify_doctor`)
  - [ ] Query Shopify Dev MCP for console/API errors
  - [ ] Attach doc links and deprecation notes
  - [ ] Skip gracefully if MCP not configured

---

## Group 4 — Alerting & Reporting (parallel)

- [ ] Task 4.1: Build the Alert Dispatcher
  - [ ] Create `src/nano_sre/agent/alerter.py`
  - [ ] Channels: Discord webhook, Slack webhook, stdout
  - [ ] Format rich embeds (Discord) / Block Kit (Slack)
  - [ ] Include skill name, status (emoji), summary, timestamp, store URL
  - [ ] Attach screenshots when available
  - [ ] Rate limit duplicate alerts (default 1 hour)
  - [ ] CTA for FAIL results: "Need help fixing this? -> shopintegrations.com"

- [ ] Task 4.2: Build the Markdown Report Generator
  - [ ] Create `src/nano_sre/agent/reporter.py`
  - [ ] Generate `reports/incident_report_YYYYMMDD_HHMMSS.md`
  - [ ] Include timestamp, store URL, summary table, per-skill findings, screenshots, recommended actions
  - [ ] Optional "AI Diagnosis" section when LLM configured
  - [ ] Support `--report-dir` CLI flag

---

## Group 5 — CLI & Packaging (parallel)

- [ ] Task 5.1: Build the CLI Interface
  - [ ] Create `src/nano_sre/cli.py` using `click`
  - [ ] Commands:
    - [ ] `nano-sre audit --url <store_url>`
    - [ ] `nano-sre audit --url <store_url> --skill synthetic-shopper`
    - [ ] `nano-sre watch --url <store_url> --interval 60`
    - [ ] `nano-sre baseline update --url <store_url>`
    - [ ] `nano-sre report show --latest`
  - [ ] Rich terminal output (progress, colored tables)
  - [ ] Register entry point: `[project.scripts] nano-sre = "nano_sre.cli:main"`

- [ ] Task 5.2: Create the GitHub Action
  - [ ] Create `.github/action/action.yml` and wrapper script
  - [ ] Composite steps:
    - [ ] Setup Python
    - [ ] Install `shopify-nano-sre`
    - [ ] Install Playwright browsers
    - [ ] Run `nano-sre audit --url ${{ inputs.store_url }}`
    - [ ] Upload report as build artifact
    - [ ] Fail workflow if any skill returns FAIL
  - [ ] Inputs: `store_url` (required), `llm_api_key` (optional), `alert_webhook` (optional)
  - [ ] Marketplace-ready metadata: `shopintegrations/nano-sre-action`

---

## Group 6 — LLM Integration (sequential, after Groups 2-5)

- [ ] Task 6.1: Build the LLM Diagnosis Engine
  - [ ] Create `src/nano_sre/agent/diagnosis.py`
  - [ ] Use `litellm` for OpenAI/Anthropic/Ollama
  - [ ] System prompt: Senior Shopify SRE with Shopify-specific concepts
  - [ ] Include screenshots for vision models
  - [ ] Return `root_cause`, `severity` (P0-P3), `recommended_fix`, `shopify_docs_link`
  - [ ] Fallback when no LLM key

---

## Group 7 — Testing (parallel, after Groups 2-6)

- [ ] Task 7.1: Unit Tests for Core Components
  - [ ] `tests/test_config.py`
  - [ ] `tests/test_store.py` (in-memory DB)
  - [ ] `tests/test_alerter.py` (mock webhooks)
  - [ ] `tests/test_reporter.py` (markdown format)
  - [ ] Use `pytest` + `pytest-asyncio`

- [ ] Task 7.2: Integration Tests with Mock Store
  - [ ] `tests/integration/test_synthetic_shopper.py`
  - [ ] `tests/integration/test_pixel_auditor.py`
  - [ ] Fixtures: `tests/fixtures/mock_store/index.html`, `product.html`, `cart.html`
  - [ ] Use `pytest-playwright`

- [ ] Task 7.3: E2E Smoke Test
  - [ ] `tests/e2e/test_cli_smoke.py`
  - [ ] Run `nano-sre audit --url <fixture-url>`
  - [ ] Verify exit code, report file, terminal output sections
  - [ ] Ensure CI runs this test

---

## Group 8 — Documentation & Marketing Assets (parallel)

- [ ] Task 8.1: Write the Contributing Guide
  - [ ] `CONTRIBUTING.md` (setup, new skill template, style guide, tests, PR process)

- [ ] Task 8.2: Write Architecture Docs
  - [ ] `docs/architecture.md` with diagrams and decision log

- [ ] Task 8.3: Create Example Configs & Tutorials
  - [ ] `docs/tutorials/getting-started.md`
  - [ ] `docs/tutorials/ci-cd-integration.md`
  - [ ] `docs/tutorials/custom-skills.md`
  - [ ] `docs/tutorials/examples/` with sample `.env` files and `docker-compose.yml`

- [ ] Task 8.4: Add Product Roadmap
  - [ ] `docs/roadmap.md` with phased roadmap, local-first, BYOK
