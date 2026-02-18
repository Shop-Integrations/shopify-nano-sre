# Development Guide

This guide covers setting up your development environment and contributing to Shopify Nano-SRE.

## Prerequisites

- Python 3.11 or higher
- `pip` and `venv` for package management
- Git for version control

## Setting Up Development Environment

### 1. Create a Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate
```

### 2. Install Dependencies

```bash
pip install -e ".[dev]"
```

This installs the project in editable mode with all development dependencies including:
- `pytest` - Testing framework
- `ruff` - Linting and formatting
- `mypy` - Type checking
- `pre-commit` - Git hooks

## Code Quality

### Running Linting

Check code style with ruff:

```bash
ruff check src/ tests/
```

Auto-fix style issues:

```bash
ruff check src/ tests/ --fix
```

### Code Formatting

Format code with ruff:

```bash
ruff format src/ tests/
```

### Type Checking

Run type checker with mypy:

```bash
mypy src/nano_sre
```

### Pre-commit Hooks

Install pre-commit hooks to run checks automatically:

```bash
pre-commit install
pre-commit run --all-files
```

## Running Tests

Run all tests:

```bash
pytest
```

Run with verbose output:

```bash
pytest -v
```

Run specific test file:

```bash
pytest tests/test_specific.py
```

Run async tests:

```bash
pytest -m asyncio
```

## Project Structure

```
src/nano_sre/
├── agent/           # Core agent logic
├── config/          # Configuration management
├── db/              # Database operations
├── skills/          # Agent skills
└── cli.py           # Command-line interface

tests/               # Test files
docs/                # Documentation
```

## Configuration Files

- `pyproject.toml` - Project metadata and dependencies
- `mypy.ini` - Type checking configuration
- `.pre-commit-config.yaml` - Pre-commit hooks configuration
- `ruff.toml` - Ruff linting rules (removed - using pyproject.toml instead)

## Key Fixes Applied

### Ruff Configuration
- Fixed `ruff.toml` syntax issues (removed invalid configuration in favor of `pyproject.toml`)
- Configured linting rules for code quality

### Code Fixes
- Removed unused variable in agent loop (privacy.py)
- Applied auto-formatting to all files

## Contributing

1. Create a feature branch from `main`
2. Make your changes following the code quality guidelines
3. Run tests and linters to ensure quality
4. Commit with descriptive messages
5. Push and create a Pull Request

### Future Module Development Opportunities

We're actively developing advanced Shopify integration modules. These are great opportunities for contributors:

#### Module 1: Webhook Sentinel (Integrity Layer)
**Skills needed:** Python async, webhook security, Shopify Admin API  
**Focus areas:**
- HMAC validation middleware implementation
- Webhook subscription monitoring via GraphQL
- Circuit breaker pattern detection

#### Module 2: Quota Guardian (Capacity Layer)
**Skills needed:** Rate limiting algorithms, GraphQL cost analysis, async Python  
**Focus areas:**
- Token bucket algorithm implementation
- GraphQL query AST parsing for cost prediction
- AIMD throttling strategy

#### Module 3: Drift Detective (Consistency Layer)
**Skills needed:** Data reconciliation, async workflows, adapter patterns  
**Focus areas:**
- Synthetic reconciliation logic
- ERP adapter plugin system
- Inventory cache validation

#### Module 4: AI Remediation Agent (The Future)
**Skills needed:** LLM prompting, error analysis, human-in-the-loop workflows  
**Focus areas:**
- Error context extraction and enrichment
- LLM-powered fix generation
- Slack/Discord integration for approval workflows

See [docs/architecture.md](architecture.md) for detailed technical specifications of each module.

## Environment Variables

Create a `.env` file based on `.env.example`:

```bash
cp .env.example .env
```

Update with your configuration:
- `SHOPIFY_STORE_URL` - Your Shopify store URL
- `SHOPIFY_ADMIN_API_KEY` - Shopify admin API key
- `LLM_PROVIDER` - LLM provider (e.g., openai, gemini)
- `LLM_API_KEY` - LLM API key
- `LLM_MODEL` - Model name
- `ALERT_WEBHOOK_URL` - Webhook for alerts

## Troubleshooting

### Virtual Environment Issues
If experiencing package installation issues, try:
```bash
pip install --upgrade pip
rm -rf venv
python3 -m venv venv
source venv/bin/activate
pip install -e ".[dev]"
```

### Type Checking Errors
Some type checking errors may be expected in development. Configure mypy settings in `mypy.ini` as needed.

### Pre-commit Hook Failures
If pre-commit hooks fail:
```bash
pre-commit run --all-files
```

Fix the issues and commit again.
