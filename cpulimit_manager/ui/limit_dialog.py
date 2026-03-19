"""Dialog for entering a CPU limit percentage."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label, Static


class LimitDialog(ModalScreen[int | None]):
    """Modal dialog that prompts the user to enter a CPU limit percentage."""

    CSS = """
    LimitDialog {
        align: center middle;
    }
    LimitDialog > Vertical {
        width: 52;
        height: auto;
        border: solid $accent;
        background: $surface;
        padding: 1 2;
    }
    LimitDialog Label {
        margin-bottom: 1;
    }
    LimitDialog Input {
        margin-bottom: 1;
    }
    LimitDialog Input.error {
        border: tall $error;
    }
    LimitDialog Horizontal {
        height: auto;
        align: center middle;
    }
    LimitDialog Button {
        margin: 0 1;
        border: none;
        padding: 0 2;
    }
    """

    def __init__(
        self,
        pid: int | None = None,
        current_limit: int | None = None,
        title_text: str = "",
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self._pid = pid
        self._current = current_limit
        self._title_text = title_text

    def compose(self) -> ComposeResult:
        hint = f"(current: {self._current}%)" if self._current else "(1–800)"
        if self._title_text:
            title = f"[bold]{self._title_text}[/bold]"
        elif self._pid is not None:
            title = f"[bold]Set CPU limit for PID {self._pid}[/bold]"
        else:
            title = "[bold]Set CPU limit[/bold]"
        with Vertical():
            yield Label(title)
            yield Label(f"Enter limit percentage {hint}:")
            yield Input(
                placeholder="e.g. 50",
                value=str(self._current) if self._current else "",
                id="limit-input",
            )
            yield Static(
                "[dim]100 = 100% of one core. Max 800 (8 cores × 100%)[/dim]",
                id="limit-hint",
            )
            with Horizontal():
                yield Button("Apply", variant="primary", id="apply")
                yield Button("Cancel", variant="default", id="cancel")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle Apply / Cancel button presses."""
        if event.button.id == "cancel":
            self.dismiss(None)
        elif event.button.id == "apply":
            self._apply()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Allow pressing Enter in the input field to apply."""
        self._apply()

    def _apply(self) -> None:
        """Validate the input and dismiss with the chosen limit, or show an error."""
        inp = self.query_one("#limit-input", Input)
        hint = self.query_one("#limit-hint", Static)
        raw = inp.value.strip()

        if not raw:
            inp.add_class("error")
            hint.update("[red]Please enter a value[/red]")
            return

        try:
            value = int(raw)
        except ValueError:
            inp.add_class("error")
            hint.update("[red]Must be a whole number (e.g. 50)[/red]")
            return

        if not (1 <= value <= 800):
            inp.add_class("error")
            hint.update("[red]Value must be between 1 and 800[/red]")
            return

        self.dismiss(value)
