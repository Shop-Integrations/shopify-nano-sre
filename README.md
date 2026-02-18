# Shopify Nano-SRE

> The open-source AI engineer that monitors your Shopify store 24/7.

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Playwright](https://img.shields.io/badge/powered%20by-Playwright-green.svg)](https://playwright.dev/)
[![MIT License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![CI Status](https://github.com/Shop-Integrations/shopify-nano-sre/actions/workflows/ci.yml/badge.svg)](https://github.com/Shop-Integrations/shopify-nano-sre/actions)
[![Coverage](https://img.shields.io/badge/coverage-85%25-green.svg)](https://github.com/Shop-Integrations/shopify-nano-sre/actions)

## Monitoring Comparison

| Feature                    | Pingdom | Datadog            | Shopify Nano-SRE |
| -------------------------- | ------- | ------------------ | ---------------- |
| HTTP Uptime                | ✅      | ✅                 | ✅               |
| Synthetic User Journey     | ❌      | ⚠️ (manual)        | ✅               |
| Shopify Awareness          | ❌      | ⚠️                 | ✅               |
| Checkout Audit             | ❌      | ⚠️ (manual)        | ✅               |
| Analytics Pixel Validation | ❌      | ❌                 | ✅               |
| LLM-Powered Diagnosis      | ❌      | ❌                 | ✅               |
| Mobile-First Monitoring    | ⚠️      | ⚠️                 | ✅               |
| Open Source                | ❌      | ❌                 | ✅               |
| Self-Hosted                | ❌      | ❌                 | ✅               |
| Setup Time                 | 5 min   | Days or weeks      | 5 min            |
| Cost per month             | $10-50  | $500+ (enterprise) | Free (+ LLM API) |

## Features

- 🤖 **Agentic Diagnostics**: LLMs analyze failures and propose next steps
- 🎭 **Synthetic Shopper**: Real user journeys through product, cart, checkout
- 🧪 **Pixel Auditor**: Verifies checkout events and conversion tracking
- 🧿 **Visual Layout Sentinel**: Detects layout drift after app/theme changes
- 🩺 **Shopify Doctor**: Uses the Shopify Dev MCP to explain API errors
- 📊 **SQLite Baselines**: Tracks performance metrics locally
- 🔒 **Local-First + BYOK**: Run on your machine, bring your own LLM key
- 📱 **Mobile-First**: iPhone 17 Pro viewport included by default
- 🐳 **Docker Ready**: Containerized deployment supported

## About

Nano-SRE is a lightweight, AI-powered Site Reliability Engineering (SRE) tool designed specifically for Shopify stores. It continuously monitors your storefront, product pages, add-to-cart flows, and checkout using synthetic monitoring with Playwright, then employs LLM-driven diagnostics to detect and alert you to issues before customers see them.

## Demo

Here's a sample report from a baseline check against a Shopify development store:

| Skill           | Status  | Summary                                                  |
| --------------- | ------- | -------------------------------------------------------- |
| shopify_shopper | ✅ PASS | Shopper journey completed successfully (Product -> Cart) |
| pixel_auditor   | ⚠️ WARN | Pixel Health: No analytics events detected               |
| visual_auditor  | ✅ PASS | No significant visual changes detected across 3 pages    |
| shopify_doctor  | ⚠️ WARN | Found 3 warning(s)                                       |
| headless_probe  | ⚠️ WARN | Console warnings detected: 2                             |
| mcp_advisor     | ⚠️ WARN | Found 3 issue(s)                                         |

**Total Skills:** 6 | **Passed:** 2 | **Warnings:** 4 | **Failed:** 0

The full report includes detailed findings, AI-powered diagnosis, and recommended actions for each warning. See [docs/demo/baseline_report.md](docs/demo/baseline_report.md) for the complete example.

### The Reliability Gaps We Target

- **Silent Failures**: App embed conflicts that break add-to-cart without server errors
- **Checkout Extensibility Migrations**: Pixels and conversion events that stop firing
- **Headless Fragility**: API rate limits, hydration mismatches, stale data
- **Manual QA Limits**: Continuous synthetic shoppers instead of human click-throughs

### Why Nano-SRE?

As Shopify transitions to [Checkout Extensibility](https://shopify.dev/docs/custom-storefronts/checkout/checkout-extensibility), store operations become more complex. Custom checkout flows, third-party payment processors, and pixel-heavy analytics stacks introduce new failure modes that traditional uptime monitoring cannot catch. Nano-SRE fills that gap by:

- **Synthetic Shopper**: Walks through your product and checkout flow autonomously
- **Pixel Auditor**: Validates critical analytics pixels (Facebook, GA, TikTok) are firing
- **Smart Diagnosis**: Uses LLMs to analyze failures and suggest remediation
- **Mobile-First**: Tests on iPhone 17 Pro viewport by default
- **Local-First**: Runs locally with BYOK, keeping store data private

## Quick Start

### Installation

```bash
pip install shopify-nano-sre
```

Or clone and install in development mode:

```bash
git clone https://github.com/Shop-Integrations/shopify-nano-sre.git
cd shopify-nano-sre
pip install -e ".[dev]"
```

### Configuration

1. Copy `.env.example` to `.env`
2. Fill in required fields:
   - `STORE_URL`: Your Shopify store URL (e.g., `https://mystore.myshopify.com`)
   - `STORE_PASSWORD`: (Optional) Your store password if it's protected
   - `LLM_API_KEY`: OpenAI or Anthropic API key
   - `LLM_MODEL`: Model to use (e.g., `gpt-4`, `claude-3-sonnet`)
   - `MCP_COMMAND`: `npx` (for Shopify Dev MCP)
   - `MCP_ARGS`: `'["-y", "@shopify/dev-mcp@latest"]'`

### Run Your First Check

```bash
nano-sre watch --interval 30
```

Or trigger a manual check:

```bash
nano-sre check
```

Or run a one-off audit:

```bash
nano-sre audit --url https://mystore.myshopify.com
```

## How It Works

```
┌──────────┐
│ Trigger  │  (Interval or Webhook)
└────┬─────┘
     │
     ▼
┌──────────────┐
│  Observe     │  Skill 1: Synthetic Shopper
├──────────────┤  Skill 2: Pixel Auditor
┌──────────────┐  ... (more skills)
│  Diagnose    │  LLM: Analyze failures + suggest actions
├──────────────┤
│  Act         │  Send alert, record incident, update baseline
└──────────────┘
```

### Technology Stack

| Component         | Choice                                        | Notes                           |
| ----------------- | --------------------------------------------- | ------------------------------- |
| Agent Core        | Nanobot-inspired Python                       | Lightweight and auditable       |
| Browser Engine    | [Playwright](https://playwright.dev/)         | Handles hydration and pixels    |
| Intelligence      | [LiteLLM](https://github.com/BerriAI/litellm) | OpenAI, Anthropic, local models |
| Knowledge Base    | Shopify Dev MCP                               | Live API docs and errors        |
| State             | [SQLite](https://www.sqlite.org/)             | Local baselines and incidents   |
| UI/CLI            | [Rich](https://github.com/Textualize/rich)    | Beautiful terminal output       |
| Schema/Validation | [Pydantic](https://docs.pydantic.dev/)        | Data integrity and settings     |
| CLI Framework     | [Click](https://click.palletsprojects.com/)   | Command-line interface          |

This project is built on the shoulders of giants. We leverage major open-source tools including **Playwright** for browser automation, **LiteLLM** for model-agnostic AI integration, **Rich** for terminal formatting, and **Pydantic** for robust data validation.

### Skill: Synthetic Shopper

Automatically:

1. Navigate to your store
2. Click first product link
3. Add to cart
4. Proceed to checkout
5. Capture performance metrics (LCP, load time)
6. Report PASS/WARN/FAIL

### Skill: Pixel Auditor

Tracks pixel firing:

- **Facebook Pixel**: `facebook.com/tr`
- **Google Analytics**: `google-analytics.com/collect`
- **TikTok Pixel**: `analytics.tiktok.com/v1/track`

### Skill: Visual Layout Sentinel

- Captures baseline screenshots for key templates
- Uses LLM vision to detect layout drift after app/theme changes

### Skill: Shopify Doctor

- Queries the Shopify Dev MCP for API and deprecation guidance
- Turns GraphQL errors into actionable fixes

## Deployment Options

- **Local CLI**: Run checks from your terminal or CI
- **GitHub Action**: Block deployments when critical checks fail
- **Self-Hosted Worker**: Run scheduled checks for multiple stores

## Roadmap

- [x] Phase 1 (current): Core skills, local monitoring
- [ ] Phase 2: Cloud sync, dashboard, advanced LLM features
- [ ] Phase 3: Community marketplace, advanced integrations
- [ ] Phase 4: Advanced Shopify integration modules

### Future: Deep Shopify Integration Modules

Building on research into Shopify app reliability patterns, we're developing specialized modules:

- **Webhook Sentinel** - HMAC validation middleware, subscription watchdog (prevents silent webhook removal), circuit breaker monitoring
- **Quota Guardian** - Real-time API rate limit visualization, GraphQL cost prediction, AIMD throttling strategy
- **Drift Detective** - Synthetic reconciliation between Shopify and ERPs, inventory sampling, cache staleness detection
- **AI Remediation Agent** - LLM-powered error analysis, automated fix suggestions with human-in-the-loop approval

See [docs/roadmap.md](docs/roadmap.md) and [docs/architecture.md](docs/architecture.md) for detailed specifications.

## Development

### Setup

```bash
pip install -e ".[dev]"
pre-commit install
```

### Run Tests

```bash
pytest tests/ -v
```

### Code Quality

```bash
ruff check src/
mypy src/ --config-file=mypy.ini
```

## API Reference

_(Placeholder: Full API documentation coming soon)_

## Deployment

### Docker

```bash
docker build -t shopify-nano-sre .
docker run -e STORE_URL=... -e LLM_API_KEY=... shopify-nano-sre watch
```

### Kubernetes

A Helm chart is planned for future releases.

## Support & Contributing

- **Issue Tracker**: [GitHub Issues](https://github.com/Shop-Integrations/shopify-nano-sre/issues)
- **Discussions**: [GitHub Discussions](https://github.com/Shop-Integrations/shopify-nano-sre/discussions)
- **Contributing**: See [CONTRIBUTING.md](CONTRIBUTING.md) (placeholder)

## License

This project is licensed under the MIT License - see [LICENSE](LICENSE) for details.

## Security

Found a security vulnerability? Please report it via [.github/SECURITY.md](.github/SECURITY.md).

---

**Learn more** at [shopintegrations.com](https://shopintegrations.com)
