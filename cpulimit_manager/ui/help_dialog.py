"""Help dialog — keyboard shortcuts, navigation, and author info."""

from __future__ import annotations

from rich.table import Table
from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Horizontal, VerticalScroll, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Rule, Static

from cpulimit_manager import __app_name__, __author__, __description__, __version__

# ── Color palette (fixed; readable on both light and dark themes) ────────────
_KEY_BG    = "#1e3a5f"   # key badge background
_KEY_FG    = "#7ecfff"   # key badge text
_SEC_FG    = "#ffcc44"   # section header
_DESC_FG   = "#c8d0d8"   # description text
_DIM_FG    = "#6a737d"   # dimmed / separator
_ACCENT    = "#00cfff"   # title / accent


def _key(label: str) -> Text:
    """Render a keyboard key badge."""
    t = Text(no_wrap=True)
    t.append(f" {label} ", style=f"bold {_KEY_FG} on {_KEY_BG}")
    return t


def _shortcut_table(rows: list[tuple[str | list[str], str]]) -> Table:
    """Build a Rich grid table: [key(s)] → description."""
    tbl = Table.grid(padding=(0, 1))
    tbl.add_column(min_width=14, no_wrap=True)   # key column
    tbl.add_column()                              # description

    for keys, desc in rows:
        if isinstance(keys, str):
            keys = [keys]
        key_cell = Text(no_wrap=True)
        for i, k in enumerate(keys):
            if i:
                key_cell.append(" ", style="")
            key_cell.append_text(_key(k))

        tbl.add_row(key_cell, Text(desc, style=_DESC_FG))
    return tbl


def _section_header(title: str) -> Text:
    t = Text(no_wrap=True)
    t.append(f"  {title}", style=f"bold {_SEC_FG}")
    return t



class HelpDialog(ModalScreen[None]):
    """Full help popup: shortcuts, navigation, and about."""

    BINDINGS = [
        ("escape", "dismiss_dialog", "Close"),
        ("question_mark", "dismiss_dialog", "Close"),
    ]

    CSS = """
    HelpDialog {
        align: center middle;
    }
    HelpDialog > Vertical {
        width: 66;
        height: auto;
        max-height: 92vh;
        border: solid $accent;
        background: $surface;
        padding: 0;
    }
    HelpDialog VerticalScroll {
        height: auto;
        max-height: 80vh;
        padding: 0 2;
        border: none;
    }
    HelpDialog Rule {
        margin: 1 0;
        color: $panel;
    }
    HelpDialog .help-title {
        text-align: center;
        padding: 1 2 0 2;
    }
    HelpDialog .help-sep {
        padding: 0 2;
    }
    HelpDialog .help-section {
        margin-top: 1;
    }
    HelpDialog .help-footer {
        text-align: center;
        padding: 1 2;
    }
    HelpDialog .help-close {
        height: auto;
        align: center middle;
        padding: 0 0 1 0;
    }
    HelpDialog Button {
        border: none;
        padding: 0 3;
    }
    """

    def compose(self) -> ComposeResult:
        with Vertical():
            # ── Title ──────────────────────────────────────────────────
            title = Text(justify="center", no_wrap=True)
            title.append(f" {__app_name__} ", style=f"bold {_ACCENT}")
            title.append(f"v{__version__}", style=f"dim {_ACCENT}")
            yield Static(title, classes="help-title")

            sep = Text("═" * 60, style=_ACCENT, no_wrap=True, overflow="crop")
            yield Static(sep, classes="help-sep")

            with VerticalScroll():
                # ── Process management ─────────────────────────────────
                yield Static(_section_header("PROCESS MANAGEMENT"), classes="help-section")
                yield Static(_shortcut_table([
                    ("l",   "Limit the selected process"),
                    ("u",   "Unlimit the selected process"),
                    ("c",   "Change the limit of the selected process"),
                ]))

                yield Static(_section_header("TOP 5 SHORTCUTS"), classes="help-section")
                yield Static(_shortcut_table([
                    ("t",   "Limit Top 5  ·  current user only"),
                    ("T",   "Limit Top 5  ·  all users"),
                    ("x",   "Unlimit Top 5  ·  current user only"),
                    ("X",   "Unlimit Top 5  ·  all users"),
                ]))

                yield Static(_section_header("CONFIGURATION"), classes="help-section")
                yield Static(_shortcut_table([
                    ("p",   "Set the default CPU limit percentage"),
                    ("r",   "Set the data refresh rate (seconds)"),
                    ("F5",  "Force an immediate data refresh"),
                    ("q",   "Quit the application"),
                ]))

                yield Rule()

                # ── Navigation ─────────────────────────────────────────
                yield Static(_section_header("NAVIGATION"), classes="help-section")
                yield Static(_shortcut_table([
                    (["↑", "↓"],     "Move row selection"),
                    (["PgUp", "PgDn"], "Scroll page"),
                    ("Tab",          "Switch focus between panels"),
                    ("Enter",        "Confirm / select in dialogs"),
                    ("Esc",          "Cancel / close dialog"),
                ]))

                yield Rule()

                # ── About ──────────────────────────────────────────────
                footer = Text(justify="center", no_wrap=True)
                footer.append(__description__ + "\n", style=f"dim {_DESC_FG}")
                footer.append(f"Author: {__author__}", style=f"dim {_DIM_FG}")
                yield Static(footer, classes="help-footer")

            # ── Close button ───────────────────────────────────────────
            with Horizontal(classes="help-close"):
                yield Button("Close  [Esc]", variant="primary", id="close")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "close":
            self.dismiss(None)

    def action_dismiss_dialog(self) -> None:
        self.dismiss(None)
