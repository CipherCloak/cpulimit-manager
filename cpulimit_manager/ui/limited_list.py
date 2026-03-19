"""LIMITED PROCESS widget — shows processes with active CPU limits."""

from __future__ import annotations

from typing import TYPE_CHECKING

from rich.text import Text
from textual.coordinate import Coordinate
from textual.widgets import DataTable

from cpulimit_manager.ui.process_list import row_color

if TYPE_CHECKING:
    from cpulimit_manager.process_monitor import ProcessInfo


class LimitedListWidget(DataTable):
    """Widget displaying processes that have active CPU limits applied."""

    BORDER_TITLE = "LIMITED PROCESS"

    def on_mount(self) -> None:
        """Initialize table columns and cursor style."""
        self.cursor_type = "row"
        self.add_columns("Limit", "CPU%", "PID", "Program", "User", "Command")
        self.zebra_stripes = False

    def update_limited(
        self, processes: list[ProcessInfo], limits: dict[int, int]
    ) -> None:
        """Refresh the limited process list."""
        cursor_row = self.cursor_row
        self.clear()

        limited = [p for p in processes if p.pid in limits]
        for proc in limited:
            limit_val = limits[proc.pid]
            color = row_color(proc.username)
            self.add_row(
                Text(f"{limit_val}%", style="bright_yellow"),
                Text(f"{proc.cpu_percent:5.1f}%", style=color),
                Text(str(proc.pid), style=color),
                Text(proc.name[:20], style=color),
                Text(proc.username[:15], style=color),
                Text((proc.cmdline or proc.name)[:50], style=color),
            )

        if self.row_count > 0:
            row = min(cursor_row, self.row_count - 1)
            self.move_cursor(row=row)

    def get_selected_pid(self) -> int | None:
        """Return PID of the currently selected row, or None."""
        if self.row_count == 0 or self.cursor_row >= self.row_count:
            return None
        try:
            cell = self.get_cell_at(Coordinate(self.cursor_row, 2))
            return int(str(cell))
        except Exception:
            return None
