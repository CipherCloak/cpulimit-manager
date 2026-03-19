"""Dialog for setting the data refresh rate."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label, Static


class RefreshRateDialog(ModalScreen[float | None]):
    """Modal dialog that prompts the user to enter a refresh interval in seconds."""

    CSS = """
    RefreshRateDialog {
        align: center middle;
    }
    RefreshRateDialog > Vertical {
        width: 52;
        height: auto;
        border: solid $accent;
        background: $surface;
        padding: 1 2;
    }
    RefreshRateDialog Label {
        margin-bottom: 1;
    }
    RefreshRateDialog Input {
        margin-bottom: 1;
    }
    RefreshRateDialog Input.error {
        border: tall $error;
    }
    RefreshRateDialog Horizontal {
        height: auto;
        align: center middle;
    }
    RefreshRateDialog Button {
        margin: 0 1;
        border: none;
        padding: 0 2;
    }
    """

    def __init__(self, current: float = 2.0, **kwargs) -> None:
        super().__init__(**kwargs)
        self._current = current

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Label("[bold]Set Refresh Rate[/bold]")
            yield Label(f"Enter interval in seconds (current: {self._current:.1f}s):")
            yield Input(
                placeholder="e.g. 2",
                value=str(self._current),
                id="rate-input",
            )
            yield Static(
                "[dim]Minimum 0.5s — Maximum 60s[/dim]",
                id="rate-hint",
            )
            with Horizontal():
                yield Button("Apply", variant="primary", id="apply")
                yield Button("Cancel", variant="default", id="cancel")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel":
            self.dismiss(None)
        elif event.button.id == "apply":
            self._apply()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self._apply()

    def _apply(self) -> None:
        inp = self.query_one("#rate-input", Input)
        hint = self.query_one("#rate-hint", Static)
        raw = inp.value.strip()

        if not raw:
            inp.add_class("error")
            hint.update("[red]Please enter a value[/red]")
            return

        try:
            value = float(raw)
        except ValueError:
            inp.add_class("error")
            hint.update("[red]Must be a number (e.g. 2 or 0.5)[/red]")
            return

        if not (0.5 <= value <= 60):
            inp.add_class("error")
            hint.update("[red]Value must be between 0.5 and 60[/red]")
            return

        self.dismiss(value)
