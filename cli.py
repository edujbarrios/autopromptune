"""
cli.py — AutoPromTune Command-Line Interface
============================================
Usage:
    python cli.py tune "Describe if there is a blue ball on the image"
    python cli.py tune --json "Check if the animal is near the thing"
    autopromptune tune "..."   (after: pip install -e .)

Part of MSc AI thesis research — Eduardo J. Barrios (@edujbarrios)
"""

import json as _json
import logging
import sys

import click
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box

load_dotenv()

from autopromptune import PromptTuner, __version__
from autopromptune.llm_client import LLMClient

console = Console()


@click.group()
@click.version_option(__version__, prog_name="autopromptune")
def main() -> None:
    """AutoPromTune — LLM-powered prompt disambiguation.

    Part of MSc AI thesis research by Eduardo J. Barrios (@edujbarrios).
    """


@main.command()
@click.argument("prompt")
@click.option(
    "--json",
    "output_json",
    is_flag=True,
    default=False,
    help="Output the full result as JSON (useful for scripting).",
)
@click.option("--api-key", default=None, envvar="LLM_API_KEY", help="llm7.io API key.")
@click.option(
    "--base-url",
    default=None,
    envvar="LLM_API_BASE_URL",
    help="API base URL (default: https://api.llm7.io/v1).",
)
@click.option("--model", default=None, envvar="LLM_MODEL", help="Model identifier.")
@click.option(
    "--verbose", "-v", is_flag=True, default=False, help="Show debug logs."
)
def tune(
    prompt: str,
    output_json: bool,
    api_key: str,
    base_url: str,
    model: str,
    verbose: bool,
) -> None:
    """Tune PROMPT by identifying and replacing vague terms.

    Example:

        python cli.py tune "Describe if there is a blue ball on the image"
    """
    if verbose:
        logging.basicConfig(level=logging.DEBUG)

    client_kwargs = {k: v for k, v in
                     [("api_key", api_key), ("base_url", base_url), ("model", model)]
                     if v is not None}

    client = LLMClient(**client_kwargs)
    tuner = PromptTuner(client=client)

    with console.status("[bold green]Running two-pass LLM analysis…[/bold green]"):
        try:
            result = tuner.tune(prompt)
        except Exception as exc:
            console.print(f"[bold red]Error:[/bold red] {exc}")
            sys.exit(1)

    # ------------------------------------------------------------------
    # JSON output mode
    # ------------------------------------------------------------------
    if output_json:
        payload = {
            "original_prompt": result.original_prompt,
            "tuned_prompt": result.tuned_prompt,
            "was_changed": result.was_changed,
            "vague_terms": [
                {"term": vt.term, "reason": vt.reason, "replacement": vt.replacement}
                for vt in result.vague_terms
            ],
        }
        console.print_json(_json.dumps(payload, ensure_ascii=False, indent=2))
        return

    # ------------------------------------------------------------------
    # Rich human-readable output
    # ------------------------------------------------------------------
    console.print()
    console.print(Panel(result.original_prompt, title="[dim]Original Prompt[/dim]", border_style="dim"))
    console.print(Panel(result.tuned_prompt, title="[bold green]✅ Tuned Prompt[/bold green]", border_style="green"))

    if result.vague_terms:
        table = Table(
            title=f"Vague Terms Identified ({len(result.vague_terms)})",
            box=box.ROUNDED,
            show_lines=True,
        )
        table.add_column("Term", style="red", no_wrap=True)
        table.add_column("Reason", style="yellow")
        table.add_column("Replacement", style="green")

        for vt in result.vague_terms:
            table.add_row(vt.term, vt.reason, vt.replacement)

        console.print()
        console.print(table)
    else:
        console.print("\n[dim]No vague terms found — prompt was already precise.[/dim]")

    console.print()


if __name__ == "__main__":
    main()
