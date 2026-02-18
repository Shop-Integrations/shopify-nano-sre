# Product Roadmap

This roadmap is directional and may shift based on user feedback and Shopify platform changes.

## Phase 1 (current): Core skills, local monitoring

- [x] Core agent loop and local state management
- [x] Local-first configuration with BYOK
- [x] Alerting and reporting (local-first)
- [x] Core skills: pixel auditor, visual sentinel, Shopify doctor, headless probe, MCP advisor
- [x] Synthetic shopper flow
- [x] CLI workflows: audit, watch, baseline update, report show
- [x] GitHub Action for CI audits

## Phase 2: Cloud sync, dashboard, advanced LLM features

- [ ] Optional cloud sync for incidents and baselines
- [ ] Multi-store dashboard with team roles
- [ ] Advanced LLM diagnosis and structured runbooks
- [ ] Scheduled reports and escalation policies

## Phase 3: Community marketplace, advanced integrations

- [ ] Skill marketplace and community-contributed checks
- [ ] Deeper Shopify platform integrations and partner apps
- [ ] CI/CD templates and managed actions
- [ ] Enterprise controls (SSO, audit logs, retention policies)

## Phase 4: Advanced Shopify Integration Modules

### 4.1 Module 1: The Webhook Sentinel (Integrity Layer)

Webhook reliability is the Achilles' heel of Shopify apps. This module ensures webhook infrastructure remains healthy and prevents silent failures.

**Feature Specification:**

- [ ] **HMAC Validation Middleware**: Robust, reusable function that validates the `X-Shopify-Hmac-Sha256` header
  - Insight: Many developers fail by parsing the body before validation, which alters the buffer and causes validation to fail
  - Implementation: Provide "safe" middleware that captures the raw buffer for validation
  - Zero-copy validation to prevent body mutation issues

- [ ] **Subscription Watchdog**: Cron job that queries the `webhookSubscriptions` endpoint every hour
  - Logic: Shopify silently removes webhooks that fail consecutively for 48 hours
  - Validation: Check if critical topics (e.g., `orders/create`, `customers/update`) are missing
  - Alerting: Immediate notification when subscriptions are removed
  - Value: Prevents "Silent Death" scenario where stores stop syncing orders for days unnoticed

- [ ] **Circuit Breaker Monitoring**: Monitor Circuit Breaker headers that Shopify sends when an app is under load
  - Track `X-Shopify-Shop-Api-Call-Limit` headers
  - Detect patterns indicating impending webhook suspension
  - Proactive alerting before complete failure

### 4.2 Module 2: The Quota Guardian (Capacity Layer)

Shopify's API rate limits ("Leaky Bucket") are complex, especially with differences between REST (requests/sec) and GraphQL (cost/sec).

**Feature Specification:**

- [ ] **Real-Time Bucket Visualization**: Implementation of Token Bucket algorithm that mirrors Shopify's server-side logic locally
  - Track REST API bucket fill level in real-time
  - Monitor GraphQL cost accumulation
  - Dashboard showing current capacity and headroom

- [ ] **Cost Prediction**: Heuristic that analyzes GraphQL queries before sending to estimate cost
  - Insight: Developers often over-fetch data (e.g., requesting `edges { node {...} }` 10 levels deep)
  - Static analysis: Lint queries for "Cost Violations" before execution
  - Warning system: Alert when query cost exceeds safe thresholds
  - Optimization suggestions: Recommend pagination and field reduction

- [ ] **Throttling Strategy**: Implementation of "Smoothed Rate Limiting" using AIMD (Additive Increase, Multiplicative Decrease) algorithm
  - Ensures app backs off before hitting 429 errors
  - Maintains smooth throughput without disruption
  - Adaptive rate adjustment based on response headers
  - Prevention: Avoid rate limit errors entirely through predictive throttling

### 4.3 Module 3: The Drift Detective (Consistency Layer)

Agency-style feature solving complex business problems beyond pure technical monitoring.

**Feature Specification:**

- [ ] **Synthetic Reconciliation**: Job that runs every 24 hours
  - Action: Fetch last 50 orders from Shopify and last 50 from ERP (via plugin adapter)
  - Comparison: Compare critical fields: `total_price`, `tax_lines`, `line_items`, `fulfillment_status`
  - Alerting: Flag "Revenue Drift" when discrepancies exceed threshold (e.g., >$0.05)
  - Reporting: Daily reconciliation report with detailed discrepancy analysis
  - Value: Catch data sync issues before they compound into revenue loss

- [ ] **Inventory Sampling**: Random spot-checks of product availability
  - Frontend check: Verify product page displays correct stock status
  - Backend validation: Query API for actual inventory levels
  - Cache detection: Catch stale Cloudflare or Hydrogen caching layers
  - Action: Alert when frontend says "In Stock" but backend shows 0 inventory
  - Value: Prevent overselling and customer disappointment

- [ ] **Price Consistency Validation**: Monitor price sync across channels
  - Compare Shopify admin prices vs. storefront display
  - Detect currency conversion errors
  - Identify variant-level pricing discrepancies

### 4.4 Module 4: The AI Remediation Agent (The Future)

True AI-powered remediation aligning with modern AI agent capabilities.

**Feature Specification:**

- [ ] **Log Analysis**: Automatic error capture and analysis
  - Capture: When SRE Agent catches exceptions (e.g., Liquid Render Error), capture full stack trace
  - Context gathering: Extract relevant code snippets and configuration
  - Historical patterns: Identify similar past incidents

- [ ] **Contextual Prompting**: LLM-powered error diagnosis
  - Send error + relevant code snippet to LLM (OpenAI/Anthropic API)
  - Prompt: "You are a Shopify Expert. This Liquid code failed with error X. Explain why and provide a diff to fix it."
  - Context enrichment: Include Shopify documentation and best practices
  - Solution generation: Generate step-by-step remediation instructions

- [ ] **Human-in-the-Loop**: Collaborative remediation workflow
  - Post explanation and suggested code fix to Slack/Discord channel
  - Developer review and approval workflow
  - One-click fix application (with rollback capability)
  - Learning: Track fix acceptance rate to improve future suggestions

- [ ] **Automated Fix Library**: Build knowledge base of successful remediations
  - Common error patterns and proven fixes
  - Auto-apply approved fixes for known issues
  - Continuous learning from developer feedback
