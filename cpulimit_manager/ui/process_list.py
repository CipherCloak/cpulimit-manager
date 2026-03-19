"""ALL PROCESS widget — real-time process list sorted by CPU usage."""

from __future__ import annotations

from typing import TYPE_CHECKING

from rich.text import Text
from textual.coordinate import Coordinate
from textual.widgets import DataTable

if TYPE_CHECKING:
    from cpulimit_manager.process_monitor import ProcessInfo


def row_color(username: str) -> str:
    """Return a Rich color string based on the process owner."""
    return "#ff0000" if username == "root" else "#47ab92"


class ProcessListWidget(DataTable):
    """Widget displaying all running processes sorted by CPU usage."""

    BORDER_TITLE = "ALL PROCESS"

    def on_mount(self) -> None:
        """Initialize table columns and cursor style."""
        self.cursor_type = "row"
        self.add_columns("CPU%", "PID", "Program", "User", "Command")
        self.zebra_stripes = False

    def update_processes(
        self, processes: list[ProcessInfo], limited_pids: set[int]
    ) -> None:
        """Refresh the process table with updated process data."""
        cursor_row = self.cursor_row

        self.clear()
        for proc in processes:
            if proc.pid in limited_pids:
                continue
            color = row_color(proc.username)
            cpu_text = Text(f"{proc.cpu_percent:5.1f}%", style=color)
            pid_text = Text(str(proc.pid), style=color)
            name_text = Text(proc.name[:20], style=color)
            user_text = Text(proc.username[:15], style=color)
            cmd = proc.cmdline[:60] if proc.cmdline else proc.name
            cmd_text = Text(cmd, style=color)
            self.add_row(cpu_text, pid_text, name_text, user_text, cmd_text)

        # Restore cursor position if still valid
        if self.row_count > 0:
            row = min(cursor_row, self.row_count - 1)
            self.move_cursor(row=row)

    def get_selected_pid(self) -> int | None:
        """Return the PID of the currently selected row, or None."""
        if self.row_count == 0 or self.cursor_row >= self.row_count:
            return None
        try:
            cell = self.get_cell_at(Coordinate(self.cursor_row, 1))
            return int(str(cell))
        except Exception:
            return None
