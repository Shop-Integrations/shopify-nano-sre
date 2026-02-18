# Getting Started with Shopify Nano-SRE

Welcome to Shopify Nano-SRE! This guide will walk you through setting up and running your first monitoring checks on your Shopify store.

## What is Shopify Nano-SRE?

Shopify Nano-SRE is an AI-powered Site Reliability Engineering (SRE) tool that monitors your Shopify store 24/7. It uses synthetic monitoring to detect issues before your customers see them by:

- Running real user journeys through your store
- Auditing analytics pixels and conversion tracking
- Detecting visual layout changes
- Diagnosing issues with AI-powered insights

## Prerequisites

Before you begin, ensure you have:

- **Python 3.11 or higher** installed on your system
- A **Shopify store** to monitor (development or production)
- An **LLM API key** (OpenAI, Anthropic, or local Ollama setup)
- Basic familiarity with command-line tools

## Installation

### Option 1: Install from PyPI (Recommended)

```bash
pip install shopify-nano-sre
```

### Option 2: Install from Source

Clone the repository and install in development mode:

```bash
git clone https://github.com/Shop-Integrations/shopify-nano-sre.git
cd shopify-nano-sre
pip install -e ".[dev]"
```

### Install Playwright Browsers

After installation, you need to install the browser engines used for monitoring:

```bash
playwright install chromium
```

## Configuration

### Step 1: Create Your Environment File

Copy the example environment file to create your own configuration:

```bash
cp .env.example .env
```

### Step 2: Configure Required Settings

Open `.env` in your text editor and update the following required fields:

```bash
# Your Shopify store URL
STORE_URL=https://your-store.myshopify.com

# (Optional) Store password if it is password protected
STORE_PASSWORD=your-store-password

# LLM Provider (openai, anthropic, or ollama)
LLM_PROVIDER=openai

# Your LLM API key
LLM_API_KEY=sk-your-api-key-here

# Model to use
LLM_MODEL=gpt-4
```

### Password-Protected Stores

If your store is currently under development or maintenance and is password-protected, Shopify Nano-SRE can automatically bypass the password page. Simply provide the `STORE_PASSWORD` in your `.env` file or via the CLI.

The synthetic shopper will detect the password page, enter the password, and proceed with the audit.

### Configuring Shopify Admin API (Highly Recommended)

To enable advanced health checks (like Liquid error detection and product audits), you should provide a Shopify Admin API token.

1.  **Enable Custom App Development**:
    *   In Shopify Admin, go to **Settings** > **Apps and sales channels** > **Develop apps**.
    *   Click **Allow legacy custom app development** and confirm.
2.  **Create Private App**:
    *   Click **Create an app** and name it `Shopify Nano-SRE`.
3.  **Configure Scopes**:
    *   Click **Configure Admin API scopes**.
    *   Select `read_products` and `read_themes` (required for `shopify_doctor` skill).
    *   Click **Save**.
4.  **Install & Get Token**:
    *   Click **Install app** in the top right.
    *   Under **API credentials**, click **Reveal token once** to see your **Admin API access token** (starts with `shpat_`).
5.  **Update `.env`**:
    ```bash
    SHOPIFY_ADMIN_API_KEY=shpat_xxxxxxxxxxxxxxxxxxxx
    ```

### Configuring Shopify Dev MCP (Recommended)

Shopify Dev MCP (Model Context Protocol) allows Nano-SRE to query official Shopify documentation in real-time to explain API errors and propose fixes.

1.  **Ensure Node.js is installed** (npx is used to run the MCP server).
2.  **Update `.env`**:
    ```bash
    MCP_COMMAND=npx
    MCP_ARGS='["-y", "@shopify/dev-mcp@latest"]'
    MCP_ENABLED=true
    ```

This enables the `mcp_advisor` skill to provide authoritative diagnostics for storefront and Admin API errors.

### Step 3: Optional Configuration

You can also configure:

- **Alert Webhooks**: Get notifications in Discord or Slack
- **Check Intervals**: How often to run monitoring checks
- **Database Path**: Where to store monitoring data
- **Privacy Settings**: PII redaction and screenshot blurring

See `.env.example` for all available options.

## Running Your First Check

### Quick Audit

The fastest way to verify your setup is to run a one-time audit:

```bash
nano-sre audit --url https://your-store.myshopify.com
```

This will:
1. Launch a headless browser
2. Navigate to your store
3. Run all registered monitoring skills
4. Display results in your terminal

### Expected Output

You should see output similar to:

```
Starting audit for: https://your-store.myshopify.com

┏━━━━━━━━━━━━━━━━┳━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Skill          ┃ Status ┃ Summary                       ┃
┡━━━━━━━━━━━━━━━━╇━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ pixel_auditor  │ PASS   │ All tracking pixels detected  │
└────────────────┴────────┴───────────────────────────────┘

Summary: 1 passed, 0 warned, 0 failed
```

### Save Audit Report

To save the audit results as JSON:

```bash
nano-sre audit --url https://your-store.myshopify.com --output audit-report.json
```

## Understanding Skills

Nano-SRE uses "skills" to monitor different aspects of your store. Each skill focuses on a specific area:

### Available Skills

1. **pixel_auditor**: Verifies that analytics pixels (Facebook, Google Analytics, TikTok) are firing correctly
2. **headless_probe**: Tests your headless storefront's API endpoints and performance
3. **visual_auditor**: Captures screenshots and detects layout drift
4. **shopify_doctor**: Uses the Shopify Dev MCP to diagnose API errors
5. **mcp_advisor**: Provides AI-powered recommendations based on monitoring data
6. **shopify_shopper**: Real user journeys through product, cart, checkout flows

### Skill Results

Each skill returns one of three statuses:

- **PASS**: Everything is working as expected
- **WARN**: Minor issues detected that should be reviewed
- **FAIL**: Critical issues that need immediate attention

## Continuous Monitoring

For production environments, you'll want to run monitoring continuously.

### Watch Mode

```bash
nano-sre watch --interval 30
```

This will run checks every 30 minutes and alert you when issues are detected.

### Docker Deployment

For always-on monitoring, see the [CI/CD Integration Guide](./ci-cd-integration.md) for Docker deployment options.

## Troubleshooting

### Common Issues

#### "Browser not found"

If you see this error, install Playwright browsers:

```bash
playwright install chromium
```

#### "LLM API Error"

Check that your API key is correct and has sufficient credits/quota:

```bash
# Test with OpenAI
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer $LLM_API_KEY"
```

#### "Store not accessible"

Ensure your store URL is correct and accessible. For password-protected stores, you may need to:

1. Add a custom skill to handle authentication
2. Use a development store without password protection

### Enable Debug Logging

For more detailed output, set the log level in your `.env`:

```bash
LOG_LEVEL=DEBUG
```

## Next Steps

Now that you have Nano-SRE running, you can:

1. **Set up CI/CD Integration**: Automate monitoring in your deployment pipeline - see [CI/CD Integration Guide](./ci-cd-integration.md)
2. **Create Custom Skills**: Build skills specific to your store - see [Custom Skills Guide](./custom-skills.md)
3. **Configure Alerts**: Set up webhook notifications for Slack or Discord
4. **Review Documentation**: Explore the full documentation in the `docs/` folder

## Getting Help

- **GitHub Issues**: [Report bugs or request features](https://github.com/Shop-Integrations/shopify-nano-sre/issues)
- **Discussions**: [Ask questions and share ideas](https://github.com/Shop-Integrations/shopify-nano-sre/discussions)
- **Documentation**: [Browse all docs](https://github.com/Shop-Integrations/shopify-nano-sre/tree/main/docs)

## Example Use Cases

### E-commerce Agency

Monitor multiple client stores from a single installation:

```bash
# Store 1
nano-sre audit --url https://client1.myshopify.com --output reports/client1.json

# Store 2
nano-sre audit --url https://client2.myshopify.com --output reports/client2.json
```

### Pre-deployment Checks

Add to your deployment script to verify store health:

```bash
#!/bin/bash
nano-sre audit --url https://staging.myshopify.com
if [ $? -eq 0 ]; then
    echo "Store health check passed"
    # Proceed with deployment
else
    echo "Store health check failed"
    exit 1
fi
```

### Post-migration Validation

After migrating to Checkout Extensibility or making theme changes:

```bash
nano-sre audit --url https://your-store.myshopify.com --output post-migration-audit.json
```

Review the report to ensure all pixels and functionality still work correctly.

### Visual Baselines

Setting a visual baseline is critical for detecting layout drift. When you first set up Nano-SRE or after an intentional theme update, run:

```bash
nano-sre baseline update --url https://your-store.myshopify.com
```

This will save current screenshots as the "gold standard." Future audits will compare against these baselines and report any significant visual changes.

## Summary

You've learned how to:

- ✅ Install Shopify Nano-SRE
- ✅ Configure your environment
- ✅ Run your first audit
- ✅ Understand skill results
- ✅ Troubleshoot common issues

Continue to the [CI/CD Integration Guide](./ci-cd-integration.md) to set up automated monitoring!
