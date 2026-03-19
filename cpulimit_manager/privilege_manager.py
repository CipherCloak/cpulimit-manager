"""Privilege elevation module for running commands with sudo."""

import logging
import os
import subprocess
from typing import Optional

import psutil

log = logging.getLogger(__name__)


class PrivilegeManager:
    """Manages privilege elevation for operations requiring root access."""

    @staticmethod
    def get_current_user() -> str:
        """Return the current username, falling back to the process owner."""
        user = os.environ.get("USER") or os.environ.get("LOGNAME", "")
        if not user:
            try:
                import pwd
                user = pwd.getpwuid(os.getuid()).pw_name
            except (ImportError, KeyError, OSError) as exc:
                log.debug("get_current_user: fallback lookup failed: %s", exc)
        return user

    @staticmethod
    def process_requires_sudo(pid: int) -> bool:
        """Check if limiting a process requires sudo (owned by a different user).

        Returns True (assume sudo needed) on any lookup failure.
        """
        try:
            proc = psutil.Process(pid)
            proc_user = proc.username()
            current_user = PrivilegeManager.get_current_user()
            return proc_user != current_user and current_user != "root"
        except psutil.NoSuchProcess:
            log.debug("process_requires_sudo: pid=%d no longer exists", pid)
            return False   # process gone — no point in limiting
        except psutil.AccessDenied:
            log.debug("process_requires_sudo: access denied for pid=%d, assuming sudo needed", pid)
            return True
        except Exception as exc:
            log.debug("process_requires_sudo: unexpected error for pid=%d: %s", pid, exc)
            return True

    @staticmethod
    def validate_password(password: str) -> bool:
        """Validate a sudo password by running a harmless sudo credential check.

        Returns False if sudo is not installed or the password is wrong.
        """
        if not password:
            return False
        try:
            result = subprocess.run(
                ["sudo", "-S", "-v"],
                input=(password + "\n").encode(),
                capture_output=True,
                timeout=5,
            )
            return result.returncode == 0
        except FileNotFoundError:
            log.debug("validate_password: sudo not found on this system")
            return False
        except subprocess.TimeoutExpired:
            log.debug("validate_password: sudo -v timed out")
            return False
        except OSError as exc:
            log.debug("validate_password: OS error: %s", exc)
            return False

    @staticmethod
    def is_root() -> bool:
        """Check if the current process is running as root."""
        try:
            return os.geteuid() == 0
        except AttributeError:
            # Windows fallback (not a target platform, but safe)
            return False
