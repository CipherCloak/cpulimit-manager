#!/usr/bin/env python3
"""CLI entry point for cpulimit-manager."""

import argparse
import logging
import sys
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

DEBUG_LOG_FILE = "debug.log"


def _setup_logging(debug: bool) -> None:
    """Configure logging. When debug=True, write DEBUG-level records to debug.log."""
    if debug:
        logging.basicConfig(
            filename=DEBUG_LOG_FILE,
            filemode="w",
            level=logging.DEBUG,
            format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        logging.getLogger("cpulimit_manager").setLevel(logging.DEBUG)
    else:
        # Silence all loggers when debug mode is off
        logging.disable(logging.CRITICAL)

console = Console()

APP_NAME = "cpulimit-manager"
VERSION = "1.0.0"
DESCRIPTION = "TUI application to monitor and limit CPU usage of processes using cpulimit"
AUTHOR = "cpulimit-manager contributors"


def show_about() -> None:
    """Display formatted about information."""
    content = Text.assemble(
        ("cpulimit-manager", "bold cyan"),
        ("\n"),
        ("Version: ", "dim"),
        (VERSION + "\n", "green"),
        ("\n"),
        (DESCRIPTION + "\n", "white"),
        ("\n"),
        ("Dependencies: ", "dim"),
        ("textual, rich, psutil, cpulimit\n", "cyan"),
        ("Platforms: ", "dim"),
        ("Linux, macOS, FreeBSD\n", "cyan"),
        ("\n"),
        ("Shortcuts:\n", "bold yellow"),
        ("  l  ", "yellow"),
        ("Limit a process\n", "white"),
        ("  u  ", "yellow"),
        ("Unlimit a process\n", "white"),
        ("  r  ", "yellow"),
        ("Re-limit a process\n", "white"),
        ("  5  ", "yellow"),
        ("Limit top 5 processes\n", "white"),
        ("  x  ", "yellow"),
        ("Unlimit top 5 processes\n", "white"),
        ("  t  ", "yellow"),
        ("Toggle dark/light theme\n", "white"),
        ("  ?  ", "yellow"),
        ("Show about info\n", "white"),
        ("  q  ", "yellow"),
        ("Quit\n", "white"),
    )
    console.print(
        Panel(content, title="[bold]About cpulimit-manager[/bold]", border_style="cyan")
    )


def main() -> None:
    """Main entry point: parse CLI arguments or launch the TUI."""
    parser = argparse.ArgumentParser(
        prog=APP_NAME,
        description=DESCRIPTION,
        add_help=False,
    )
    parser.add_argument(
        "-h", "--help", action="store_true", help="Show this help message and exit"
    )
    parser.add_argument(
        "-v", "--version", action="store_true", help="Show version and exit"
    )
    parser.add_argument(
        "-a", "--about", action="store_true", help="Show about information and exit"
    )
    parser.add_argument(
        "-d", "--debug", action="store_true", help=f"Enable debug logging to {DEBUG_LOG_FILE}"
    )

    args = parser.parse_args()
    _setup_logging(args.debug)

    if args.help:
        help_text = Text.assemble(
            ("Usage: ", "bold"),
            (f"{APP_NAME} [OPTIONS]\n\n", "cyan"),
            (DESCRIPTION + "\n\n", "white"),
            ("Options:\n", "bold yellow"),
            ("  -h, --help     ", "yellow"),
            ("Show this help message\n", "white"),
            ("  -v, --version  ", "yellow"),
            ("Show version\n", "white"),
            ("  -a, --about    ", "yellow"),
            ("Show about information\n", "white"),
            ("  -d, --debug    ", "yellow"),
            (f"Enable debug logging to {DEBUG_LOG_FILE}\n", "white"),
            ("\n"),
            ("(no options)     ", "dim"),
            ("Launch the TUI\n", "white"),
        )
        console.print(
            Panel(
                help_text,
                title="[bold]cpulimit-manager help[/bold]",
                border_style="blue",
            )
        )
        sys.exit(0)

    if args.version:
        console.print(f"[cyan]{APP_NAME}[/cyan] [green]v{VERSION}[/green]")
        sys.exit(0)

    if args.about:
        show_about()
        sys.exit(0)

    # No flags — launch the TUI
    from cpulimit_manager.app import CPULimitApp

    app = CPULimitApp()
    app.run()


if __name__ == "__main__":
    main()
