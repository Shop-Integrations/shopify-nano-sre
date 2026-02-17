"""Tests for the CLI module."""

from click.testing import CliRunner

from nano_sre.cli import main


def test_cli_help():
    """Test CLI help command."""
    runner = CliRunner()
    result = runner.invoke(main, ["--help"])

    assert result.exit_code == 0
    assert "Usage:" in result.output
    assert "Shopify Nano-SRE" in result.output


def test_cli_invocation():
    """Test CLI can be invoked without arguments."""
    runner = CliRunner()
    result = runner.invoke(main, [])

    # Should not raise an error
    assert result.exit_code in (0, 2)  # 2 is for missing subcommand


def test_audit_command_help():
    """Test audit command help."""
    runner = CliRunner()
    result = runner.invoke(main, ["audit", "--help"])

    assert result.exit_code == 0
    assert "audit" in result.output.lower()
    assert "--url" in result.output


def test_audit_command_requires_url():
    """Test audit command requires --url option."""
    runner = CliRunner()
    result = runner.invoke(main, ["audit"])

    assert result.exit_code != 0
    assert "Missing option" in result.output or "required" in result.output.lower()
