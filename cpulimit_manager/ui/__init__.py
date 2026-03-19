"""UI widgets and dialogs for cpulimit-manager."""

from cpulimit_manager.ui.cpu_monitor import CPUMonitorWidget
from cpulimit_manager.ui.help_dialog import HelpDialog
from cpulimit_manager.ui.limit_dialog import LimitDialog
from cpulimit_manager.ui.limited_list import LimitedListWidget
from cpulimit_manager.ui.password_dialog import PasswordDialog
from cpulimit_manager.ui.process_list import ProcessListWidget
from cpulimit_manager.ui.quit_dialog import QuitDialog
from cpulimit_manager.ui.refresh_rate_dialog import RefreshRateDialog
from cpulimit_manager.ui.theme_dialog import ThemeDialog

__all__ = [
    "ProcessListWidget",
    "LimitedListWidget",
    "CPUMonitorWidget",
    "HelpDialog",
    "LimitDialog",
    "PasswordDialog",
    "QuitDialog",
    "RefreshRateDialog",
    "ThemeDialog",
]
