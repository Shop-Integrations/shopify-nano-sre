"""CLI entry point for Shopify Nano-SRE."""

import asyncio
import logging

import click
from rich.console import Console
from rich.table import Table

from nano_sre.agent.core import Agent
from nano_sre.config.settings import Settings
from nano_sre.skills import PixelAuditor

console = Console()
logger = logging.getLogger(__name__)


@click.group()
def main():
    """Shopify Nano-SRE: The open-source AI engineer that monitors your Shopify store."""
    pass


@main.command()
@click.option(
    "--url",
    required=True,
    help="URL of the Shopify store to audit (e.g., https://your-store.myshopify.com)",
)
def audit(url: str):
    """Run an audit on the specified Shopify store URL."""
    asyncio.run(_run_audit(url))


async def _run_audit(url: str):
    """Execute the audit asynchronously."""
    from playwright.async_api import async_playwright

    console.print(f"[bold blue]Starting audit for:[/bold blue] {url}")

    try:
        # Create settings with the provided URL
        settings = Settings(
            store_url=url,
            llm_provider="openai",
            llm_api_key="",
            llm_model="gpt-4",
        )

        # Create agent
        agent = Agent(settings)

        # Register PixelAuditor skill
        pixel_auditor = PixelAuditor(mock_mode=False)
        agent.register_skill(pixel_auditor)

        # Launch Playwright
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()

            try:
                # Navigate to the URL
                await page.goto(url, wait_until="networkidle")

                # Execute skills with page in context
                context = {"page": page}
                results = await agent.execute_skills(context=context)

                # Display results
                _display_results(results)

            finally:
                await browser.close()

    except Exception as e:
        console.print(f"[bold red]Error during audit:[/bold red] {str(e)}")
        logger.exception("Audit failed")
        raise click.Abort()


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


if __name__ == "__main__":
    main()
