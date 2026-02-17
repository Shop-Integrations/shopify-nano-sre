"""CLI entry point for Shopify Nano-SRE."""

import click


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


if __name__ == "__main__":
    main()
