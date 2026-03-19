"""CPU MONITOR widget — fancy real-time per-core CPU usage visualization."""

from __future__ import annotations

import logging
from typing import Dict, List, Tuple

from rich.align import Align
from rich.console import Console, ConsoleOptions, RenderResult
from rich.table import Table
from rich.text import Text
from textual.widget import Widget

log = logging.getLogger(__name__)

# Bar characters
_FILLED = "▪"
_EMPTY  = "·"

# How many characters wide each core's usage bar is
_BAR_W = 12
# Width of the overall CPU bar (will be adjusted at render time)
_OVERALL_BAR_W = 28


def _usage_color(pct: float) -> str:
    """Map a CPU usage percentage to a Rich color string."""
    if pct >= 80:
        return "#ff4444"
    if pct >= 60:
        return "#ff8800"
    if pct >= 40:
        return "#ffdd00"
    return "#00e676"


def _temp_color(celsius: float) -> str:
    """Map a temperature value to a Rich color string."""
    if celsius >= 85:
        return "#ff4444"
    if celsius >= 75:
        return "#ff8800"
    if celsius >= 60:
        return "#ffdd00"
    return "#44cfcf"


def _make_bar(pct: float, width: int) -> Text:
    """Return a colored bar Text of exactly *width* characters."""
    filled = min(width, int(pct / 100 * width))
    t = Text(no_wrap=True, overflow="crop")
    t.append(_FILLED * filled, style=_usage_color(pct))
    t.append(_EMPTY * (width - filled), style="dim")
    return t


def _temp_str(celsius: float) -> Text:
    """Format a temperature value with its unit, colored by severity."""
    t = Text(no_wrap=True)
    t.append(f"{celsius:.0f}°C", style=_temp_color(celsius))
    return t


class _CPUContent:
    """Rich-protocol renderable that combines all CPU monitor sections."""

    def __init__(
        self,
        header:   Text,
        overall:  Text,
        grid:     Table,
        footer:   Text,
    ) -> None:
        self._header  = header
        self._overall = overall
        self._grid    = grid
        self._footer  = footer

    def __rich_console__(self, console: Console, options: ConsoleOptions) -> RenderResult:
        yield Align.center(self._header)
        yield self._overall
        yield self._grid
        yield Align.center(self._footer)


class CPUMonitorWidget(Widget):
    """Widget displaying real-time CPU usage per core in a bpytop-like style."""

    BORDER_TITLE = "CPU MONITOR"

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._cpu_percents:  List[float] = []
        self._cpu_overall:   float = 0.0
        self._cpu_name:      str = "CPU"
        self._freq_str:      str = ""
        self._load_avg:      Tuple[float, float, float] = (0.0, 0.0, 0.0)
        self._temps:         Dict[int, float] = {}

    def update_cpu(
        self,
        percents:    List[float],
        overall:     float,
        cpu_name:    str,
        freq_str:    str,
        load_avg:    Tuple[float, float, float],
        temps:       Dict[int, float] | None = None,
    ) -> None:
        """Push new CPU data and trigger a re-render."""
        self._cpu_percents = percents
        self._cpu_overall  = overall
        self._cpu_name     = cpu_name
        self._freq_str     = freq_str
        self._load_avg     = load_avg
        self._temps        = temps or {}
        self.refresh()

    # ------------------------------------------------------------------
    # Rendering
    # ------------------------------------------------------------------

    def render(self) -> _CPUContent:
        """Build and return the fancy CPU monitor renderable."""
        widget_w = max(40, self.size.width - 4)  # usable inner width

        # ── Header ────────────────────────────────────────────────────
        header = Text(no_wrap=True, overflow="crop")
        name = self._cpu_name
        # Shorten if needed (keep last 3–4 words)
        if len(name) > widget_w - 12:
            parts = name.split()
            name = " ".join(parts[-4:]) if len(parts) > 4 else name[: widget_w - 12]
        header.append(name, style="bold #00cfff")
        if self._freq_str:
            # Right-align frequency
            pad = widget_w - len(name) - len(self._freq_str) - 2
            header.append(" " * max(1, pad))
            header.append(self._freq_str, style="bold #00cfff")

        # ── Overall CPU bar ───────────────────────────────────────────
        overall_bar_w = max(10, widget_w - 22)
        pct_pkg = self._cpu_overall
        pkg_temp = self._temps.get(-1)

        overall_line = Text(no_wrap=True, overflow="crop")
        overall_line.append("CPU ", style="bold white")
        overall_line.append_text(_make_bar(pct_pkg, overall_bar_w))
        overall_line.append(f"  {pct_pkg:>3.0f}%", style=_usage_color(pct_pkg))
        if pkg_temp is not None:
            overall_line.append("  ")
            overall_line.append_text(_temp_str(pkg_temp))

        # ── Per-core four-column grid ─────────────────────────────────
        # 4 columns halves the number of rows (20 cores → 5 rows),
        # which lets CPU MONITOR use a fixed small height so LIMITED
        # PROCESS gets the remaining vertical space.
        num_cores = len(self._cpu_percents)
        num_cols  = 4
        rows      = (num_cores + num_cols - 1) // num_cols  # ceil division

        # Per-column width and bar width
        col_w = max(8, (widget_w - num_cols + 1) // num_cols)
        label_w = 4   # "C20 "
        pct_w   = 4   # "100%"
        bar_w   = max(2, col_w - label_w - pct_w - 2)

        grid = Table.grid(padding=(0, 0))
        for _ in range(num_cols):
            grid.add_column(min_width=col_w)

        def core_cell(idx: int) -> Text:
            if idx >= num_cores:
                return Text("")
            pct  = self._cpu_percents[idx]
            cell = Text(no_wrap=True, overflow="crop")
            cell.append(f"C{idx + 1:<3}", style="bold white")
            cell.append_text(_make_bar(pct, bar_w))
            cell.append(f" {pct:>3.0f}%", style=_usage_color(pct))
            return cell

        for row in range(rows):
            cells = [core_cell(row + col * rows) for col in range(num_cols)]
            grid.add_row(*cells)

        # ── Load average footer ───────────────────────────────────────
        la = self._load_avg
        footer = Text(justify="center", no_wrap=True, overflow="crop")
        footer.append("Load AVG:  ", style="dim white")
        for val in la:
            color = "#ff4444" if val > 8 else "#ffdd00" if val > 4 else "#00e676"
            footer.append(f"{val:.2f}  ", style=color)

        return _CPUContent(header, overall_line, grid, footer)
