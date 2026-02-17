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


def test_cli_report_dir_flag():
    """Test CLI --report-dir flag."""
    runner = CliRunner()
    result = runner.invoke(main, ["--help"])

    assert result.exit_code == 0
    assert "--report-dir" in result.output
    assert "Directory to save incident reports" in result.output


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


def test_watch_command_help():
    """Test watch command help."""
    runner = CliRunner()
    result = runner.invoke(main, ["watch", "--help"])

    assert result.exit_code == 0
    assert "--interval" in result.output
    assert "--url" in result.output


def test_baseline_update_help():
    """Test baseline update help."""
    runner = CliRunner()
    result = runner.invoke(main, ["baseline", "update", "--help"])

    assert result.exit_code == 0
    assert "--skill" in result.output
    assert "--url" in result.output


def test_report_show_with_path(tmp_path):
    """Test report show command with a specific path."""
    report_file = tmp_path / "incident_report_20240217_120000.md"
    report_file.write_text("# Incident Report\n\nTest content\n", encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(main, ["report", "show", "--path", str(report_file)])

    assert result.exit_code == 0
    assert "Incident Report" in result.output
