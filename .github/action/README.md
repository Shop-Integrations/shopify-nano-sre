# Shopify Nano-SRE Action

A GitHub Action for AI-powered monitoring of your Shopify store. Runs synthetic checks and validates analytics pixels before deployment.

## Features

- 🤖 **Automated Store Audits**: Runs comprehensive checks on your Shopify store
- 🎭 **Synthetic Shopping**: Tests real user journeys through product pages, cart, and checkout
- 🧪 **Pixel Validation**: Verifies analytics pixels are firing correctly
- 📊 **Detailed Reports**: Generates JSON reports uploaded as artifacts
- ✅ **Build Protection**: Fails CI/CD pipeline if critical issues are detected

## Usage

### Basic Usage

```yaml
name: Store Audit
on: [push, pull_request]

jobs:
  audit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Audit Shopify Store
        uses: shopintegrations/nano-sre-action@v1
        with:
          store_url: 'https://your-store.myshopify.com'
```

### With Optional Parameters

```yaml
- name: Audit Shopify Store
  uses: shopintegrations/nano-sre-action@v1
  with:
    store_url: 'https://your-store.myshopify.com'
    llm_api_key: ${{ secrets.OPENAI_API_KEY }}
    alert_webhook: ${{ secrets.SLACK_WEBHOOK_URL }}
```

### With Report Analysis

```yaml
- name: Audit Shopify Store
  id: audit
  uses: shopintegrations/nano-sre-action@v1
  with:
    store_url: ${{ vars.STORE_URL }}
    llm_api_key: ${{ secrets.LLM_API_KEY }}

- name: Check audit status
  if: steps.audit.outputs.status == 'FAIL'
  run: |
    echo "Store audit failed!"
    exit 1

- name: Download report
  uses: actions/download-artifact@v4
  with:
    name: nano-sre-report
    path: ./reports
```

## Inputs

| Input | Description | Required | Default |
|-------|-------------|----------|---------|
| `store_url` | Shopify store URL to audit (e.g., `https://your-store.myshopify.com`) | ✅ Yes | - |
| `llm_api_key` | API key for LLM provider (OpenAI, Anthropic). Required for AI-powered diagnostics. | ❌ No | - |
| `alert_webhook` | Webhook URL for sending alerts (Discord, Slack) | ❌ No | - |

## Outputs

| Output | Description |
|--------|-------------|
| `status` | Overall health status (`PASS`, `WARN`, `FAIL`) |
| `report_path` | Path to the generated report artifact |

## Artifacts

The action uploads a `nano-sre-report` artifact containing:
- `report.json` - Detailed audit results in JSON format
- Screenshots (if any issues are detected)

Artifacts are retained for 30 days.

## Environment Variables

The action sets the following environment variables for the audit:

- `STORE_URL` - The store URL to audit
- `LLM_API_KEY` - LLM API key (if provided)
- `ALERT_WEBHOOK_URL` - Alert webhook URL (if provided)

## Example Workflows

### Pre-Deployment Gate

Block deployments if store health check fails:

```yaml
name: Pre-Deploy Audit
on:
  push:
    branches: [main]

jobs:
  audit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Audit Store Health
        uses: shopintegrations/nano-sre-action@v1
        with:
          store_url: ${{ vars.PRODUCTION_STORE_URL }}
          llm_api_key: ${{ secrets.OPENAI_API_KEY }}
      
      # Only deploy if audit passes
      - name: Deploy
        if: success()
        run: ./deploy.sh
```

### Scheduled Monitoring

Run regular health checks:

```yaml
name: Scheduled Store Audit
on:
  schedule:
    - cron: '0 */6 * * *'  # Every 6 hours

jobs:
  monitor:
    runs-on: ubuntu-latest
    steps:
      - uses: shopintegrations/nano-sre-action@v1
        with:
          store_url: ${{ vars.STORE_URL }}
          llm_api_key: ${{ secrets.OPENAI_API_KEY }}
          alert_webhook: ${{ secrets.SLACK_WEBHOOK }}
```

## What Gets Checked

The action runs comprehensive checks including:

1. **Synthetic Shopper**: Navigates through product pages, add-to-cart, and checkout
2. **Pixel Auditor**: Validates analytics pixels (Facebook, GA4, TikTok)
3. **Visual Layout Sentinel**: Detects UI/layout changes
4. **Performance Metrics**: Monitors page load times and Core Web Vitals

## Failure Conditions

The action will fail the workflow if:

- Any skill returns a `FAIL` status
- The store is unreachable
- Critical checkout flows are broken
- Required analytics pixels are missing

## Troubleshooting

### Action fails immediately

Check that:
- Your `store_url` is correct and accessible
- The store is not password-protected (or auth is configured)

### Playwright installation fails

The action automatically installs Playwright with `--with-deps`. If this fails on your runner, you may need to use a different base image or manually install dependencies.

### No report generated

If the report artifact is missing:
- Check the action logs for errors
- Ensure the `nano-sre` CLI completed successfully
- Verify the output directory is writable

## License

MIT License - see the [main repository](https://github.com/Shop-Integrations/shopify-nano-sre) for details.

## Support

- 📚 [Documentation](https://github.com/Shop-Integrations/shopify-nano-sre)
- 🐛 [Report Issues](https://github.com/Shop-Integrations/shopify-nano-sre/issues)
- 💬 [Discussions](https://github.com/Shop-Integrations/shopify-nano-sre/discussions)
