# Contributing to Shopify Nano-SRE

Thank you for your interest in contributing to Shopify Nano-SRE! This guide will help you get started with development, understand our code standards, and submit your contributions.

## Table of Contents

- [Development Setup](#development-setup)
- [Creating a New Skill](#creating-a-new-skill)
- [Code Style Guide](#code-style-guide)
- [Testing Requirements](#testing-requirements)
- [Pull Request Process](#pull-request-process)

## Development Setup

### Prerequisites

- **Python 3.11 or higher** - Required for modern type hints and features
- **pip** and **venv** - For package management
- **Git** - For version control
- **Playwright** - Will be installed via dependencies

### Initial Setup

1. **Clone the repository**

   ```bash
   git clone https://github.com/Shop-Integrations/shopify-nano-sre.git
   cd shopify-nano-sre
   ```

2. **Create a virtual environment**

   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install development dependencies**

   ```bash
   pip install -e ".[dev]"
   ```

   This installs the project in editable mode with all development dependencies:
   - `pytest` - Testing framework
   - `pytest-asyncio` - Async test support
   - `pytest-playwright` - Playwright integration for tests
   - `ruff` - Fast Python linter and formatter
   - `mypy` - Static type checker
   - `pre-commit` - Git hooks for code quality

4. **Install Playwright browsers**

   ```bash
   playwright install chromium
   ```

5. **Set up pre-commit hooks**

   ```bash
   pre-commit install
   ```

   This will automatically run linting and formatting checks before each commit.

6. **Configure environment variables**

   ```bash
   cp .env.example .env
   ```

   Edit `.env` and add your configuration:
   - `STORE_URL` - Your Shopify store URL for testing
   - `LLM_API_KEY` - OpenAI or Anthropic API key
   - `LLM_MODEL` - Model to use (e.g., `gpt-4`, `claude-3-sonnet`)

### Verify Installation

Run the test suite to verify everything is set up correctly:

```bash
pytest tests/ -v
```

## Creating a New Skill

Skills are the core monitoring capabilities of Nano-SRE. Each skill implements a specific check (e.g., pixel auditing, synthetic shopping, health checks).

### Skill Template

Here's a skeleton template for creating a new skill:

```python
"""Your Skill Description - Brief one-liner about what this skill does."""

import logging
from typing import Any

from playwright.async_api import Page

from nano_sre.agent.core import Skill, SkillResult

logger = logging.getLogger(__name__)


class YourSkillName(Skill):
    """
    Brief description of what this skill monitors or checks.

    This skill:
    - Key capability 1
    - Key capability 2
    - Key capability 3
    """

    def __init__(self, optional_param: bool = False):
        """
        Initialize the skill.

        Args:
            optional_param: Description of parameter if needed
        """
        self.optional_param = optional_param

    def name(self) -> str:
        """Return the skill name."""
        return "your_skill_name"

    async def run(self, context: dict[str, Any]) -> SkillResult:
        """
        Execute the skill and return results.

        Args:
            context: Agent context containing:
                - page: Playwright Page object
                - settings: Application settings
                - Any other context needed

        Returns:
            SkillResult with status, summary, and details
        """
        page: Page | None = context.get("page")
        settings = context.get("settings")

        # Validate required context
        if not page:
            return SkillResult(
                skill_name=self.name(),
                status="FAIL",
                summary="No Playwright page object in context",
                error="Missing required 'page' in context",
            )

        try:
            # Your skill implementation here
            # 1. Perform checks/monitoring
            # 2. Collect data
            # 3. Analyze results
            
            # Example: Navigate to a page
            # await page.goto("https://example.com")
            
            # Example: Collect some data
            data_collected = {}
            issues_found = []
            
            # Determine status based on your checks
            if issues_found:
                status = "FAIL"
                summary = f"Found {len(issues_found)} issue(s)"
            else:
                status = "PASS"
                summary = "All checks passed"

            return SkillResult(
                skill_name=self.name(),
                status=status,  # PASS, WARN, or FAIL
                summary=summary,
                details={
                    "data_collected": data_collected,
                    "issues": issues_found,
                },
            )

        except Exception as e:
            logger.exception(f"Error in {self.name()}: {e}")
            return SkillResult(
                skill_name=self.name(),
                status="FAIL",
                summary=f"Skill execution failed: {str(e)}",
                error=str(e),
            )
```

### Skill Development Checklist

When creating a new skill:

- [ ] Create skill file in `src/nano_sre/skills/your_skill_name.py`
- [ ] Inherit from `Skill` base class
- [ ] Implement `name()` method returning a unique skill identifier
- [ ] Implement `async run(context)` method with proper error handling
- [ ] Return `SkillResult` with appropriate status (PASS/WARN/FAIL)
- [ ] Add comprehensive docstrings
- [ ] Add type hints for all parameters and return values
- [ ] Export skill in `src/nano_sre/skills/__init__.py`
- [ ] Create corresponding test file in `tests/test_your_skill.py`
- [ ] Add unit tests covering success and failure scenarios
- [ ] Update documentation if the skill adds new configuration options

### Adding Your Skill to the Package

After creating your skill, export it in `src/nano_sre/skills/__init__.py`:

```python
from nano_sre.skills.your_skill_name import YourSkillName

__all__ = ["PixelAuditor", "YourSkillName"]  # Add to existing list
```

## Code Style Guide

We use automated tools to maintain consistent code quality across the project.

### Linting and Formatting with Ruff

**Ruff** is our primary tool for linting and code formatting. It's fast and comprehensive.

#### Check code style

```bash
ruff check src/ tests/
```

#### Auto-fix issues

```bash
ruff check src/ tests/ --fix
```

#### Format code

```bash
ruff format src/ tests/
```

### Ruff Configuration

Our Ruff settings are configured in `pyproject.toml`:

- **Line length**: 100 characters
- **Target version**: Python 3.11+
- **Enabled rules**: E (pycodestyle errors), F (pyflakes), W (pycodestyle warnings), I (isort)
- **Ignored**: E501 (line too long - handled by formatter)

### Type Checking with Mypy

**Mypy** ensures type safety across the codebase.

#### Run type checker

```bash
mypy src/nano_sre
```

Or with explicit config:

```bash
mypy src/nano_sre --config-file=mypy.ini
```

### Mypy Configuration

Type checking settings in `mypy.ini`:

- **Python version**: 3.11
- **Warnings enabled**: Return types, unused configs
- Partial type checking enabled (not strict mode for faster development)

### Code Quality Best Practices

1. **Type Hints**: Use type hints for function parameters and return values
   ```python
   async def process_data(input: dict[str, Any]) -> SkillResult:
       ...
   ```

2. **Docstrings**: Write clear docstrings for all public functions and classes
   ```python
   def calculate_score(data: dict) -> float:
       """
       Calculate health score from monitoring data.
       
       Args:
           data: Dictionary containing monitoring metrics
           
       Returns:
           Health score between 0.0 and 1.0
       """
   ```

3. **Error Handling**: Always include try/except blocks in skill `run()` methods
4. **Logging**: Use the logging module instead of print statements
5. **Async/Await**: Use async/await for I/O operations
6. **Constants**: Define constants at module level with UPPER_CASE names

### Pre-commit Hooks

Pre-commit hooks automatically run before each commit:

```bash
pre-commit run --all-files  # Run manually on all files
```

The hooks will:
1. Run `ruff check --fix` to auto-fix linting issues
2. Run `ruff format` to format code
3. Run `mypy` for type checking (excluding tests/)

If any hook fails, fix the issues and try committing again.

## Testing Requirements

We use **pytest** with async support for testing. All new code should include tests.

### Running Tests

#### Run all tests

```bash
pytest
```

#### Run with verbose output

```bash
pytest -v
```

#### Run specific test file

```bash
pytest tests/test_pixel_auditor.py
```

#### Run tests matching a pattern

```bash
pytest -k "test_skill"
```

#### Run with coverage report

```bash
pytest --cov=nano_sre --cov-report=html
```

### Writing Tests for Skills

Each skill should have a corresponding test file. Here's a template:

```python
"""Tests for YourSkillName."""

from typing import Any

import pytest

from nano_sre.agent.core import SkillResult
from nano_sre.skills.your_skill_name import YourSkillName


class MockSettings:
    """Mock settings for testing."""
    store_url_str = "https://test.myshopify.com"


@pytest.fixture
def skill():
    """Create skill instance for testing."""
    return YourSkillName()


@pytest.fixture
def mock_settings():
    """Create mock settings."""
    return MockSettings()


class TestYourSkillName:
    """Tests for YourSkillName skill."""

    def test_name(self, skill):
        """Test skill name is correct."""
        assert skill.name() == "your_skill_name"

    @pytest.mark.asyncio
    async def test_run_success(self, skill, mock_settings):
        """Test successful skill execution."""
        context = {
            "page": None,  # Use mock page object or real one
            "settings": mock_settings,
        }
        result = await skill.run(context)
        
        assert isinstance(result, SkillResult)
        assert result.skill_name == "your_skill_name"
        assert result.status in ["PASS", "WARN", "FAIL"]

    @pytest.mark.asyncio
    async def test_run_missing_page(self, skill):
        """Test skill handles missing page gracefully."""
        context = {}
        result = await skill.run(context)
        
        assert result.status == "FAIL"
        assert "page" in result.summary.lower() or result.error

    @pytest.mark.asyncio
    async def test_run_with_error(self, skill):
        """Test skill handles exceptions properly."""
        # Set up context that will cause an error
        context = {"page": "invalid"}
        result = await skill.run(context)
        
        assert result.status == "FAIL"
        assert result.error is not None
```

### Testing Best Practices

1. **Test Structure**: Use the Arrange-Act-Assert pattern
2. **Fixtures**: Use pytest fixtures for reusable test setup
3. **Async Tests**: Mark async tests with `@pytest.mark.asyncio`
4. **Mock Objects**: Use mocks for external dependencies (Playwright, API calls)
5. **Edge Cases**: Test error conditions, missing data, and edge cases
6. **Test Coverage**: Aim for >80% code coverage on new code
7. **Test Isolation**: Each test should be independent and not rely on others

### Integration Tests

For tests requiring Playwright:

```python
@pytest.mark.asyncio
async def test_with_browser(browser):
    """Test using Playwright browser."""
    page = await browser.new_page()
    # Your test code
    await page.close()
```

Mark integration tests:

```python
@pytest.mark.integration
async def test_full_flow():
    """Integration test."""
    ...
```

Run only integration tests:

```bash
pytest -m integration
```

## Pull Request Process

### Before Submitting a PR

1. **Create a feature branch**

   ```bash
   git checkout -b feature/your-feature-name
   ```

   Or for bug fixes:

   ```bash
   git checkout -b fix/bug-description
   ```

2. **Make your changes**
   - Follow the code style guide
   - Add tests for new functionality
   - Update documentation as needed

3. **Run all quality checks**

   ```bash
   # Format code
   ruff format src/ tests/
   
   # Check for linting issues
   ruff check src/ tests/
   
   # Run type checker
   mypy src/nano_sre
   
   # Run tests
   pytest -v
   ```

4. **Commit your changes**

   Write clear, descriptive commit messages:

   ```bash
   git add .
   git commit -m "Add pixel validation for TikTok events"
   ```

   Good commit message format:
   - Use present tense ("Add feature" not "Added feature")
   - First line: brief summary (50 chars or less)
   - Optionally, add detailed description after a blank line

5. **Push to your fork**

   ```bash
   git push origin feature/your-feature-name
   ```

### Submitting the PR

1. **Open a Pull Request** on GitHub
2. **Fill out the PR template** with:
   - Description of changes
   - Related issue number (if applicable)
   - Type of change (bug fix, new feature, breaking change)
   - Testing performed
3. **Ensure CI passes** - All automated checks must pass
4. **Request review** from maintainers

### PR Review Process

1. **Automated Checks**: CI will run linting, type checking, and tests
2. **Code Review**: Maintainers will review your code
3. **Feedback**: Address any requested changes
4. **Approval**: Once approved, your PR will be merged

### PR Requirements

Your PR must:

- [ ] Pass all automated CI checks (linting, type checking, tests)
- [ ] Include tests for new functionality
- [ ] Update documentation if adding new features
- [ ] Follow existing code style and patterns
- [ ] Have clear commit messages
- [ ] Not introduce breaking changes without discussion
- [ ] Include a clear description of what and why

### After Your PR is Merged

- Your contribution will be included in the next release
- You'll be added to the contributors list
- Delete your feature branch (optional)

## Additional Resources

- **Project Documentation**: [README.md](README.md)
- **Development Guide**: [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md)
- **Security Policy**: [SECURITY.md](SECURITY.md)
- **Issue Tracker**: [GitHub Issues](https://github.com/Shop-Integrations/shopify-nano-sre/issues)
- **Discussions**: [GitHub Discussions](https://github.com/Shop-Integrations/shopify-nano-sre/discussions)

## Getting Help

- **Questions?** Open a [discussion](https://github.com/Shop-Integrations/shopify-nano-sre/discussions)
- **Found a bug?** Open an [issue](https://github.com/Shop-Integrations/shopify-nano-sre/issues)
- **Want to propose a feature?** Start a discussion first

## Code of Conduct

Please be respectful and constructive in all interactions. We're here to build great software together.

---

Thank you for contributing to Shopify Nano-SRE! 🎉
