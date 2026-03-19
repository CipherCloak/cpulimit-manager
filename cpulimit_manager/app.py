"""Main TUI application for cpulimit-manager."""

from __future__ import annotations

import dataclasses
import logging
import os
from pathlib import Path
from typing import Optional

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.widgets import Footer, Header
from textual import work

log = logging.getLogger(__name__)

from cpulimit_manager.config import AppConfig
from cpulimit_manager.cpulimit_manager import CPULimitManager
from cpulimit_manager.privilege_manager import PrivilegeManager
from cpulimit_manager.process_monitor import ProcessInfo, ProcessMonitor
from cpulimit_manager.ui import (
    CPUMonitorWidget,
    HelpDialog,
    LimitDialog,
    LimitedListWidget,
    PasswordDialog,
    ProcessListWidget,
    QuitDialog,
    RefreshRateDialog,
    ThemeDialog,
)

THEMES_DIR = Path(__file__).parent / "themes"


class CPULimitApp(App):
    """TUI application for monitoring and limiting CPU usage of processes."""

    TITLE = "cpulimit-manager"
    SUB_TITLE = "CPU Process Limiter"

    CSS_PATH = THEMES_DIR / "app.tcss"

    BINDINGS = [
        Binding("l", "limit_process", "Limit", show=True),
        Binding("u", "unlimit_process", "Unlimit", show=True),
        Binding("c", "change_limit", "Change Limit", show=True),
        Binding("t", "limit_top5_user", "Limit Top5 (me)", show=True),
        Binding("T", "limit_top5_all", "Limit Top5 (all)", show=True),
        Binding("x", "unlimit_top5_user", "Unlimit Top5 (me)", show=True),
        Binding("X", "unlimit_top5_all", "Unlimit Top5 (all)", show=True),
        Binding("p", "set_default_limit", "Set Default %", show=True),
        Binding("r", "set_refresh_rate", "Refresh rate", show=True),
        Binding("f5", "refresh", "Refresh", show=True),
        Binding("question_mark", "help", "Help", show=True),
        Binding("q", "quit", "Quit", show=True),
    ]

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._config = AppConfig()
        self._monitor = ProcessMonitor()
        self._limiter = CPULimitManager()
        self._privilege = PrivilegeManager()
        self._processes: list[ProcessInfo] = []
        self._default_limit: int = self._config.limit_percentage
        self._refresh_timer = None

    # ------------------------------------------------------------------ #
    #  Layout                                                              #
    # ------------------------------------------------------------------ #

    def compose(self) -> ComposeResult:
        """Build the widget tree."""
        yield Header()
        with Horizontal(id="main-layout"):
            yield ProcessListWidget(id="all-process", classes="panel")
            with Vertical(id="right-panel"):
                yield LimitedListWidget(id="limited-process", classes="panel")
                yield CPUMonitorWidget(id="cpu-monitor", classes="panel")
        yield Footer()

    # ------------------------------------------------------------------ #
    #  Lifecycle                                                           #
    # ------------------------------------------------------------------ #

    def on_mount(self) -> None:
        """Start the periodic refresh timer once the app is mounted."""
        interval = self._config.refresh
        log.debug("App mounted, starting refresh timer (interval=%.1fs)", interval)
        self._refresh_default_limit_label()
        self._refresh_timer = self.set_interval(interval, self._update_data)
        # Restore last saved theme (if any)
        if self._config.theme:
            try:
                self.theme = self._config.theme
            except Exception as exc:
                log.debug("on_mount: could not restore theme '%s': %s", self._config.theme, exc)
        # Fire an immediate update so the UI is populated right away
        self.call_after_refresh(self._update_data)

    def _refresh_default_limit_label(self) -> None:
        """Update the 'p' binding description in the footer to show the current default."""
        try:
            key_map = self._bindings.key_to_bindings
            if "p" in key_map:
                old = key_map["p"][0]
                key_map["p"] = [
                    dataclasses.replace(old, description=f"Set % ({self._default_limit}%)")
                ]
                self.refresh_bindings()
        except Exception as exc:
            log.debug("_refresh_default_limit_label: failed: %s", exc)

    def on_unmount(self) -> None:
        """Cleanup: terminate all managed cpulimit child processes."""
        try:
            self._limiter.cleanup()
        except Exception as exc:
            log.debug("on_unmount: cleanup error: %s", exc)

    # ------------------------------------------------------------------ #
    #  Data refresh                                                        #
    # ------------------------------------------------------------------ #

    async def _update_data(self) -> None:
        """Fetch fresh data from the system and push it to all widgets."""
        try:
            processes = self._monitor.get_processes()
            self._processes = processes
        except Exception as exc:
            log.debug("_update_data: get_processes failed: %s", exc)
            processes = self._processes  # use last known state

        try:
            limits = self._limiter.get_all_limits()
        except Exception as exc:
            log.debug("_update_data: get_all_limits failed: %s", exc)
            limits = {}
        limited_pids = set(limits.keys())

        try:
            process_list = self.query_one("#all-process", ProcessListWidget)
            process_list.update_processes(processes, limited_pids)
        except Exception as exc:
            log.debug("_update_data: process list update failed: %s", exc)

        try:
            limited_list = self.query_one("#limited-process", LimitedListWidget)
            limited_list.update_limited(processes, limits)
        except Exception as exc:
            log.debug("_update_data: limited list update failed: %s", exc)

        try:
            cpu_monitor = self.query_one("#cpu-monitor", CPUMonitorWidget)
            percents = self._monitor.get_cpu_per_core()
            overall  = self._monitor.get_cpu_overall_percent()
            cpu_name, freq_str = self._monitor.get_cpu_freq()
            load_avg = self._monitor.get_load_avg()
            temps    = self._monitor.get_cpu_temps()
            cpu_monitor.update_cpu(percents, overall, cpu_name, freq_str, load_avg, temps)
        except Exception as exc:
            log.debug("_update_data: CPU monitor update failed: %s", exc)

    # ------------------------------------------------------------------ #
    #  Focus helpers                                                       #
    # ------------------------------------------------------------------ #

    def _get_focused_pid(self) -> Optional[int]:
        """Return the selected PID from whichever list panel currently has focus.

        Falls back to the ALL PROCESS panel if neither list is focused.
        """
        focused = self.focused
        if isinstance(focused, ProcessListWidget):
            return focused.get_selected_pid()
        if isinstance(focused, LimitedListWidget):
            return focused.get_selected_pid()
        # Default fallback
        return self.query_one("#all-process", ProcessListWidget).get_selected_pid()

    # ------------------------------------------------------------------ #
    #  Key actions                                                         #
    # ------------------------------------------------------------------ #

    @work
    async def action_limit_process(self) -> None:
        """Prompt the user for a CPU limit and apply it to the selected process."""
        pid = self._get_focused_pid()
        if pid is None:
            self.notify("No process selected.", severity="warning")
            return

        if pid == os.getpid():
            self.notify("Cannot limit the cpulimit-manager process itself.", severity="warning")
            return

        limit: int | None = await self.push_screen_wait(LimitDialog(pid))
        if limit is None:
            return

        await self._apply_limit(pid, limit)

    @work
    async def action_unlimit_process(self) -> None:
        """Remove the CPU limit from the currently selected process."""
        pid = self._get_focused_pid()
        if pid is None:
            self.notify("No process selected.", severity="warning")
            return

        if not self._limiter.is_limited(pid):
            self.notify(f"PID {pid} is not limited.", severity="warning")
            return

        self._limiter.unlimit(pid)
        self.notify(f"Removed CPU limit from PID {pid}.", severity="information")
        await self._update_data()

    @work
    async def action_change_limit(self) -> None:
        """Open the limit dialog pre-filled with the current limit for adjustment."""
        pid = self._get_focused_pid()
        if pid is None:
            self.notify("No process selected.", severity="warning")
            return

        current = self._limiter.get_limit(pid)
        limit: int | None = await self.push_screen_wait(
            LimitDialog(pid, current_limit=current)
        )
        if limit is None:
            return

        await self._apply_limit(pid, limit)
        self._config.limit_percentage = limit
        log.debug("action_change_limit: saved limit_percentage=%d to config", limit)

    @work
    async def action_limit_top5_user(self) -> None:
        """Apply the default CPU limit to the top 5 processes owned by the current user."""
        current_user = self._privilege.get_current_user()
        own_pid = os.getpid()
        child_pids = {proc.pid for proc in self._limiter._processes.values()}
        excluded = child_pids | {own_pid}
        log.debug("action_limit_top5_user: user=%s excluding pids=%s", current_user, excluded)

        top5 = [
            p for p in self._processes
            if not self._limiter.is_limited(p.pid)
            and p.pid not in excluded
            and p.username == current_user
        ][:5]
        if not top5:
            self.notify("No processes available to limit for current user.", severity="warning")
            return

        for proc in top5:
            await self._apply_limit(proc.pid, self._default_limit, silent=True)

        self.notify(
            f"Limited top {len(top5)} processes to {self._default_limit}%.",
            severity="information",
        )
        await self._update_data()

    @work
    async def action_limit_top5_all(self) -> None:
        """Apply the default CPU limit to the top 5 most CPU-intensive processes (all users)."""
        own_pid = os.getpid()
        child_pids = {proc.pid for proc in self._limiter._processes.values()}
        excluded = child_pids | {own_pid}
        log.debug("action_limit_top5_all: excluding pids=%s", excluded)

        top5 = [
            p for p in self._processes
            if not self._limiter.is_limited(p.pid) and p.pid not in excluded
        ][:5]
        if not top5:
            self.notify("No processes available to limit.", severity="warning")
            return

        for proc in top5:
            await self._apply_limit(proc.pid, self._default_limit, silent=True)

        self.notify(
            f"Limited top {len(top5)} processes to {self._default_limit}%.",
            severity="information",
        )
        await self._update_data()

    @work
    async def action_unlimit_top5_user(self) -> None:
        """Remove limits from up to 5 currently limited processes owned by the current user."""
        current_user = self._privilege.get_current_user()
        limits = self._limiter.get_all_limits()
        if not limits:
            self.notify("No limited processes.", severity="warning")
            return

        pid_to_info = {p.pid: p for p in self._processes}
        pids = [
            pid for pid in limits
            if pid in pid_to_info and pid_to_info[pid].username == current_user
        ][:5]
        if not pids:
            self.notify("No limited processes for current user.", severity="warning")
            return

        for pid in pids:
            self._limiter.unlimit(pid)

        self.notify(f"Released {len(pids)} process limit(s).", severity="information")
        await self._update_data()

    @work
    async def action_unlimit_top5_all(self) -> None:
        """Remove limits from up to 5 currently limited processes (all users)."""
        limits = self._limiter.get_all_limits()
        if not limits:
            self.notify("No limited processes.", severity="warning")
            return

        pids = list(limits.keys())[:5]
        for pid in pids:
            self._limiter.unlimit(pid)

        self.notify(f"Released {len(pids)} process limit(s).", severity="information")
        await self._update_data()

    @work
    async def action_set_refresh_rate(self) -> None:
        """Prompt the user to set the data refresh interval and persist it."""
        new_rate: float | None = await self.push_screen_wait(
            RefreshRateDialog(current=self._config.refresh)
        )
        if new_rate is None:
            return
        self._config.refresh = new_rate
        log.debug("action_set_refresh_rate: new interval=%.1fs", new_rate)
        # Restart the periodic timer with the new interval
        if self._refresh_timer is not None:
            self._refresh_timer.stop()
        self._refresh_timer = self.set_interval(new_rate, self._update_data)
        self.notify(
            f"Refresh rate set to [bold]{new_rate:.1f}s[/bold].",
            severity="information",
        )

    async def action_refresh(self) -> None:
        """Force an immediate data refresh."""
        log.debug("action_refresh: manual refresh triggered")
        await self._update_data()

    @work
    async def action_set_default_limit(self) -> None:
        """Prompt the user to set the default CPU limit used by the '5' shortcut."""
        new_limit: int | None = await self.push_screen_wait(
            LimitDialog(
                current_limit=self._default_limit,
                title_text="Set default CPU limit for this session",
            )
        )
        if new_limit is None:
            return
        old = self._default_limit
        self._default_limit = new_limit
        self._config.limit_percentage = new_limit
        log.debug("action_set_default_limit: %d%% -> %d%%", old, new_limit)
        self._refresh_default_limit_label()
        self.notify(f"Default limit set to [bold]{new_limit}%[/bold].", severity="information")

    @work
    async def action_select_theme(self) -> None:
        """Open the theme picker and apply the chosen built-in theme."""
        themes = sorted(self.available_themes.keys())
        selected: str | None = await self.push_screen_wait(
            ThemeDialog(themes, current=self.theme)
        )
        if selected is None:
            return
        try:
            self.theme = selected
            self._config.theme = selected
            log.debug("action_select_theme: theme set to '%s'", selected)
        except Exception as exc:
            log.debug("action_select_theme: failed to set theme '%s': %s", selected, exc)
            self.notify(f"Could not apply theme '{selected}'.", severity="error")

    @work
    async def action_help(self) -> None:
        """Display the help popup with shortcuts, navigation, and author info."""
        await self.push_screen_wait(HelpDialog())

    @work
    async def action_quit(self) -> None:
        """Ask for confirmation before quitting, listing any active limits."""
        limits = self._limiter.get_all_limits()
        pid_to_info = {p.pid: p for p in self._processes}

        limited_info = [
            (pid_to_info[pid].name if pid in pid_to_info else str(pid),
             pid_to_info[pid].username if pid in pid_to_info else "?")
            for pid in limits
        ]
        log.debug("action_quit: %d limited process(es)", len(limited_info))

        confirmed: bool = await self.push_screen_wait(QuitDialog(limited_info))
        if confirmed:
            self._limiter.cleanup()
            log.debug("action_quit: cleanup done, exiting")
            self.exit()

    # ------------------------------------------------------------------ #
    #  Limit application helpers                                           #
    # ------------------------------------------------------------------ #

    async def _apply_limit(
        self, pid: int, limit: int, silent: bool = False
    ) -> None:
        """Apply a CPU limit to a process, requesting sudo if required.

        Args:
            pid: Target process ID.
            limit: CPU percentage cap (1–800).
            silent: When True, suppresses the success notification.
        """
        requires_sudo = self._privilege.process_requires_sudo(pid)

        log.debug("_apply_limit: pid=%d limit=%d sudo_needed=%s", pid, limit, requires_sudo)

        try:
            if requires_sudo and not self._privilege.is_root():
                program = next((p.name for p in self._processes if p.pid == pid), "")
                password = await self._request_sudo_password(pid, program=program)
                if password is None:
                    log.debug("_apply_limit: sudo cancelled by user for pid=%d", pid)
                    return
                success = self._limiter.limit(pid, limit, sudo=True, password=password)
            else:
                success = self._limiter.limit(pid, limit)
        except ValueError as exc:
            log.debug("_apply_limit: invalid argument: %s", exc)
            self.notify(f"Invalid limit value: {exc}", severity="error")
            return
        except Exception as exc:
            log.debug("_apply_limit: unexpected error for pid=%d: %s", pid, exc)
            self.notify(f"Unexpected error limiting PID {pid}.", severity="error")
            return

        log.debug("_apply_limit: result=%s for pid=%d", success, pid)
        if success:
            if not silent:
                self.notify(
                    f"Limited PID {pid} to {limit}% CPU.",
                    severity="information",
                )
            await self._update_data()
        else:
            self.notify(
                f"Failed to limit PID {pid}. "
                "Ensure cpulimit is installed and the process still exists.",
                severity="error",
            )

    async def _request_sudo_password(
        self, pid: int, program: str = "", message: str = ""
    ) -> Optional[str]:
        """Show the password dialog in a loop until the password validates or is cancelled.

        Args:
            pid: The target process ID shown in the dialog.
            message: Optional error message to display (e.g. on a retry).

        Returns:
            The validated password string, or None if the user cancelled.
        """
        while True:
            password: str | None = await self.push_screen_wait(
                PasswordDialog(pid, program=program, message=message)
            )
            if password is None:
                return None
            if self._privilege.validate_password(password):
                return password
            message = "Incorrect password. Please try again."
            log.debug("_request_sudo_password: bad password for pid=%d, retrying", pid)
