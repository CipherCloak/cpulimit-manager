"""Dialog for sudo password entry."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label, Static


class PasswordDialog(ModalScreen[str | None]):
    """Modal dialog that prompts the user to enter a sudo password."""

    CSS = """
    PasswordDialog {
        align: center middle;
    }
    PasswordDialog > Vertical {
        width: 56;
        height: auto;
        border: solid $warning;
        background: $surface;
        padding: 1 2;
    }
    PasswordDialog Label {
        margin-bottom: 1;
    }
    PasswordDialog Input {
        margin-bottom: 1;
    }
    PasswordDialog Horizontal {
        height: auto;
        align: center middle;
    }
    PasswordDialog Button {
        margin: 0 1;
        border: none;
        padding: 0 2;
    }
    """

    def __init__(self, pid: int, program: str = "", message: str = "", **kwargs) -> None:
        super().__init__(**kwargs)
        self._pid = pid
        self._program = program
        self._message = message

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Label("[bold yellow]Privilege Required[/bold yellow]")
            yield Label("This process requires elevated privileges to limit.")
            yield Label(f"[dim]PID:[/dim]     [bold]{self._pid}[/bold]")
            yield Label(f"[dim]Program:[/dim] [bold]{self._program or 'unknown'}[/bold]")
            if self._message:
                yield Static(f"[red]{self._message}[/red]", id="error-msg")
            yield Label("Enter your sudo password:")
            yield Input(
                placeholder="password",
                password=True,
                id="password-input",
            )
            with Horizontal():
                yield Button("Confirm", variant="warning", id="confirm")
                yield Button("Cancel", variant="default", id="cancel")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle Confirm / Cancel button presses."""
        if event.button.id == "cancel":
            self.dismiss(None)
        elif event.button.id == "confirm":
            self._confirm()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Allow pressing Enter in the password field to confirm."""
        self._confirm()

    def _confirm(self) -> None:
        """Validate that a password was entered before dismissing."""
        inp = self.query_one("#password-input", Input)
        if not inp.value:
            inp.add_class("error")
            # Show or update the error message label
            try:
                self.query_one("#error-msg", Static).update(
                    "[red]Password cannot be empty[/red]"
                )
            except Exception:
                # error-msg widget only exists when a message was passed; mount one now
                inp.mount(Static("[red]Password cannot be empty[/red]", id="error-msg"))
            return
        self.dismiss(inp.value)
