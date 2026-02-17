"""CLI entry point for Shopify Nano-SRE."""

import asyncio
import json
import logging
from pathlib import Path
from typing import Iterable, Optional

import click
from playwright.async_api import async_playwright
from rich.console import Console
from rich.table import Table

from nano_sre.agent.core import Agent, Skill
from nano_sre.agent.reporter import generate_report
from nano_sre.config.settings import Settings
from nano_sre.skills import (
    HeadlessProbeSkill,
    MCPAdvisor,
    PixelAuditor,
    ShopifyDoctorSkill,
    VisualAuditor,
)

console = Console()
logger = logging.getLogger(__name__)


@click.group()
@click.option(
    "--report-dir",
    default="reports",
    help="Directory to save incident reports",
    show_default=True,
)
@click.pass_context
def main(ctx, report_dir):
    """Shopify Nano-SRE: The open-source AI engineer that monitors your Shopify store."""
    # Ensure context object exists
    ctx.ensure_object(dict)
    # Store report_dir in context for subcommands
    ctx.obj["report_dir"] = report_dir


@main.command()
@click.option(
    "--url",
    required=True,
    help="URL of the Shopify store to audit (e.g., https://your-store.myshopify.com)",
)
@click.option(
    "--skill",
    "skill_names",
    multiple=True,
    help="Run only the specified skill(s) (repeatable)",
)
@click.option(
    "--update-baseline",
    is_flag=True,
    help="Update visual audit baselines instead of comparing",
)
@click.option(
    "--output",
    required=False,
    help="Path to save the audit report as JSON",
)
@click.pass_context
def audit(
    ctx,
    url: str,
    skill_names: Iterable[str],
    update_baseline: bool,
    output: Optional[str],
):
    """Run an audit on the specified Shopify store URL."""
    report_dir = ctx.obj.get("report_dir", "reports")
    asyncio.run(
        _run_audit(
            url,
            report_dir=report_dir,
            output=output,
            skill_names=list(skill_names),
            update_baseline=update_baseline,
        )
    )


@main.command()
@click.option(
    "--url",
    required=True,
    help="URL of the Shopify store to monitor (e.g., https://your-store.myshopify.com)",
)
@click.option(
    "--interval",
    default=60,
    show_default=True,
    help="Interval in minutes between checks",
)
@click.option(
    "--skill",
    "skill_names",
    multiple=True,
    help="Run only the specified skill(s) (repeatable)",
)
@click.pass_context
def watch(ctx, url: str, interval: int, skill_names: Iterable[str]):
    """Continuously monitor a Shopify store at a fixed interval."""
    report_dir = ctx.obj.get("report_dir", "reports")
    asyncio.run(
        _run_watch(
            url,
            interval_minutes=interval,
            report_dir=report_dir,
            skill_names=list(skill_names),
        )
    )


@main.group()
def baseline():
    """Baseline operations for visual audits."""


@baseline.command("update")
@click.option(
    "--url",
    required=True,
    help="URL of the Shopify store to baseline (e.g., https://your-store.myshopify.com)",
)
@click.option(
    "--skill",
    "skill_names",
    multiple=True,
    help="Baseline-capable skill(s) to run (default: visual_auditor)",
)
@click.pass_context
def baseline_update(ctx, url: str, skill_names: Iterable[str]):
    """Update visual audit baselines for a store."""
    report_dir = ctx.obj.get("report_dir", "reports")
    selected_skills = list(skill_names) if skill_names else ["visual_auditor"]
    normalized = {_normalize_skill_name(name) for name in selected_skills}
    if normalized != {"visual_auditor"}:
        raise click.BadParameter(
            "Baseline updates currently support only visual_auditor."
        )
    asyncio.run(
        _run_audit(
            url,
            report_dir=report_dir,
            skill_names=selected_skills,
            update_baseline=True,
        )
    )


@main.group()
def report():
    """Report operations."""


@report.command("show")
@click.option(
    "--latest/--no-latest",
    default=True,
    show_default=True,
    help="Show the most recent report",
)
@click.option(
    "--path",
    "report_path",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="Path to a specific report file",
)
@click.pass_context
def report_show(ctx, latest: bool, report_path: Optional[Path]):
    """Show the latest incident report."""
    if report_path:
        content = report_path.read_text(encoding="utf-8")
        console.print(content)
        return

    report_dir = Path(ctx.obj.get("report_dir", "reports"))
    if not report_dir.exists():
        console.print("[yellow]No reports directory found.[/yellow]")
        raise click.Abort()

    reports = sorted(
        report_dir.glob("incident_report_*.md"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )

    if not reports:
        console.print("[yellow]No reports found.[/yellow]")
        raise click.Abort()

    if latest:
        content = reports[0].read_text(encoding="utf-8")
        console.print(content)
        return

    console.print("[yellow]No report selected. Use --latest or --path.[/yellow]")
    raise click.Abort()


async def _run_audit(
    url: str,
    report_dir: str,
    output: Optional[str] = None,
    skill_names: Optional[list[str]] = None,
    update_baseline: bool = False,
):
    """Execute the audit asynchronously."""
    console.print(f"[bold blue]Starting audit for:[/bold blue] {url}")

    try:
        settings = Settings.model_validate({"store_url": url})
        settings.check_interval_minutes = max(settings.check_interval_minutes, 1)

        agent = Agent(settings)
        skills = _build_skills(update_baseline=update_baseline)
        for skill in skills.values():
            agent.register_skill(skill)

        selected_skills = _resolve_skill_names(skill_names, skills.keys())

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()

            try:
                await page.goto(url, wait_until="networkidle")

                context_data = {
                    "page": page,
                    "base_url": url,
                    "url": url,
                    "settings": settings,
                }

                results = await agent.execute_skills(
                    skill_names=selected_skills,
                    context=context_data,
                )

                _display_results(results)

                llm_configured = bool(settings.llm_api_key or settings.llm_provider == "ollama")
                report_path = await generate_report(
                    results=results,
                    store_url=url,
                    report_dir=report_dir,
                    llm_configured=llm_configured,
                    ai_diagnosis=None,
                )

                console.print(f"\n[green]Report saved to:[/green] {report_path}")

                if output:
                    output_path = Path(output)
                    output_path.parent.mkdir(parents=True, exist_ok=True)

                    report_data = {
                        "url": url,
                        "results": [
                            {
                                "skill_name": r.skill_name,
                                "status": r.status,
                                "summary": r.summary,
                                "details": r.details,
                            }
                            for r in results
                        ],
                    }

                    output_path.write_text(json.dumps(report_data, indent=2), encoding="utf-8")
                    console.print(f"[green]JSON output saved to:[/green] {output_path}")

            finally:
                await browser.close()

    except Exception as e:
        console.print(f"[bold red]Error during audit:[/bold red] {str(e)}")
        logger.exception("Audit failed")
        raise click.Abort()


async def _run_watch(
    url: str,
    interval_minutes: int,
    report_dir: str,
    skill_names: Optional[list[str]] = None,
):
    """Execute continuous monitoring at a fixed interval."""
    interval = max(interval_minutes, 1)

    try:
        while True:
            await _run_audit(
                url,
                report_dir=report_dir,
                skill_names=skill_names,
            )
            console.print(
                f"[dim]Next check in {interval} minute(s). Press Ctrl+C to stop.[/dim]"
            )
            await asyncio.sleep(interval * 60)
    except KeyboardInterrupt:
        console.print("[yellow]Monitoring stopped.[/yellow]")


def _display_results(results):
    """Display audit results in a formatted table."""
    if not results:
        console.print("[yellow]No results to display.[/yellow]")
        return

    # Create a table
    table = Table(title="Audit Results")
    table.add_column("Skill", style="cyan", no_wrap=True)
    table.add_column("Status", style="magenta")
    table.add_column("Summary", style="white")

    for result in results:
        # Color code status
        status_color = {
            "PASS": "[green]PASS[/green]",
            "WARN": "[yellow]WARN[/yellow]",
            "FAIL": "[red]FAIL[/red]",
        }.get(result.status, result.status)

        table.add_row(
            result.skill_name,
            status_color,
            result.summary,
        )

    console.print(table)

    # Print overall summary
    passed = sum(1 for r in results if r.status == "PASS")
    warned = sum(1 for r in results if r.status == "WARN")
    failed = sum(1 for r in results if r.status == "FAIL")

    console.print(f"\n[bold]Summary:[/bold] {passed} passed, {warned} warned, {failed} failed")


def _normalize_skill_name(name: str) -> str:
    """Normalize skill names for CLI matching."""
    return name.strip().lower().replace("-", "_")


def _build_skills(update_baseline: bool) -> dict[str, Skill]:
    """Build available skill instances keyed by their canonical names."""
    skill_instances = [
        PixelAuditor(mock_mode=False),
        VisualAuditor(update_baseline=update_baseline),
        ShopifyDoctorSkill(),
        HeadlessProbeSkill(),
        MCPAdvisor(),
    ]
    return {skill.name(): skill for skill in skill_instances}


def _resolve_skill_names(
    requested: Optional[list[str]],
    available: Iterable[str],
) -> Optional[list[str]]:
    """Resolve user-specified skill names to canonical names."""
    if not requested:
        return None

    available_set = {_normalize_skill_name(name) for name in available}
    resolved = []
    unknown = []

    for name in requested:
        normalized = _normalize_skill_name(name)
        if normalized in available_set:
            resolved.append(normalized)
        else:
            unknown.append(name)

    if unknown:
        available_list = ", ".join(sorted(available_set))
        raise click.BadParameter(
            f"Unknown skill(s): {', '.join(unknown)}. Available: {available_list}"
        )

    return resolved


if __name__ == "__main__":
    main()
