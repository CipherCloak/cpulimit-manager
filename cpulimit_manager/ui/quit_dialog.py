"""Confirmation dialog shown before quitting the application."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Label, Static


class QuitDialog(ModalScreen[bool]):
    """Modal dialog that asks the user to confirm quitting.

    Shows a list of currently limited processes (if any) that will be
    released on exit.
    """

    CSS = """
    QuitDialog {
        align: center middle;
    }
    QuitDialog > Vertical {
        width: 56;
        height: auto;
        border: solid $error;
        background: $surface;
        padding: 1 2;
    }
    QuitDialog Label {
        margin-bottom: 1;
    }
    QuitDialog #process-list {
        margin-bottom: 1;
        color: $text-muted;
    }
    QuitDialog Horizontal {
        height: auto;
        align: center middle;
        margin-top: 1;
    }
    QuitDialog Button {
        margin: 0 1;
        border: none;
        padding: 0 2;
    }
    """

    def __init__(
        self,
        limited: list[tuple[str, str]],
        **kwargs,
    ) -> None:
        """
        Args:
            limited: List of (program, user) tuples for currently limited processes.
        """
        super().__init__(**kwargs)
        self._limited = limited

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Label("[bold red]Quit cpulimit-manager?[/bold red]")

            if self._limited:
                yield Label(
                    f"[yellow]The following {len(self._limited)} limited "
                    f"process(es) will be released:[/yellow]"
                )
                rows = "\n".join(
                    f"  [bold]{prog}[/bold]  [dim]{user}[/dim]"
                    for prog, user in self._limited
                )
                yield Static(rows, id="process-list")
            else:
                yield Label("[dim]No processes are currently limited.[/dim]")

            with Horizontal():
                yield Button("Quit", variant="error", id="confirm")
                yield Button("Cancel", variant="default", id="cancel")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(event.button.id == "confirm")
