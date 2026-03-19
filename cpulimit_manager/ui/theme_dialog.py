"""Theme selection dialog."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Label, OptionList
from textual.widgets.option_list import Option


class ThemeDialog(ModalScreen[str | None]):
    """Modal dialog that lets the user pick a Textual built-in theme."""

    CSS = """
    ThemeDialog {
        align: center middle;
    }
    ThemeDialog > Vertical {
        width: 40;
        height: auto;
        max-height: 80%;
        border: thick $accent;
        background: $surface;
        padding: 1 2;
    }
    ThemeDialog Label {
        margin-bottom: 1;
    }
    ThemeDialog OptionList {
        height: auto;
        max-height: 20;
        margin-bottom: 1;
        border: solid $accent;
    }
    ThemeDialog Button {
        width: 100%;
    }
    """

    def __init__(self, themes: list[str], current: str, **kwargs) -> None:
        super().__init__(**kwargs)
        self._themes = themes
        self._current = current

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Label("[bold]Select Theme[/bold]")
            options = [
                Option(
                    f"{'▶ ' if t == self._current else '  '}{t}",
                    id=t,
                )
                for t in self._themes
            ]
            yield OptionList(*options, id="theme-list")
            yield Button("Cancel", variant="default", id="cancel")

    def on_mount(self) -> None:
        """Highlight the currently active theme."""
        ol = self.query_one("#theme-list", OptionList)
        try:
            idx = self._themes.index(self._current)
            ol.highlighted = idx
        except ValueError:
            pass

    def on_option_list_option_selected(
        self, event: OptionList.OptionSelected
    ) -> None:
        """Dismiss with the selected theme id."""
        self.dismiss(str(event.option.id))

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel":
            self.dismiss(None)
