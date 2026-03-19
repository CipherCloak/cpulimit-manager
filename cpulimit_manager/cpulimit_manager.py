"""cpulimit process management module."""

import logging
import shutil
import subprocess
from typing import Dict, Optional

import psutil

log = logging.getLogger(__name__)


class CPULimitManager:
    """Manages cpulimit processes for limiting CPU usage."""

    def __init__(self) -> None:
        self._processes: Dict[int, subprocess.Popen] = {}  # pid -> cpulimit Popen
        self._limits: Dict[int, int] = {}  # pid -> limit percentage

    @staticmethod
    def is_available() -> bool:
        """Check if cpulimit is installed on the system."""
        return shutil.which("cpulimit") is not None

    def limit(
        self,
        pid: int,
        limit: int,
        sudo: bool = False,
        password: Optional[str] = None,
    ) -> bool:
        """Apply a CPU limit to a process. Returns True on success.

        Raises:
            ValueError: If pid or limit are out of valid range.
        """
        if pid <= 0:
            raise ValueError(f"Invalid PID: {pid}")
        if not (1 <= limit <= 800):
            raise ValueError(f"Limit must be between 1 and 800, got {limit}")

        # Verify the target process still exists before spawning cpulimit
        try:
            if not psutil.pid_exists(pid):
                log.debug("limit: pid=%d does not exist", pid)
                return False
        except Exception as exc:
            log.debug("limit: pid_exists check failed for pid=%d: %s", pid, exc)

        # Remove any existing limit first
        if pid in self._processes:
            self.unlimit(pid)

        cmd = ["cpulimit", "-p", str(pid), "-l", str(limit), "-z"]
        log.debug("limit: pid=%d limit=%d sudo=%s cmd=%s", pid, limit, sudo, cmd)

        if sudo and password:
            process = self._run_with_sudo(cmd, password)
        else:
            try:
                process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    stdin=subprocess.DEVNULL,
                    start_new_session=True,
                )
            except FileNotFoundError:
                log.debug("limit: cpulimit executable not found")
                return False
            except PermissionError as exc:
                log.debug("limit: permission denied launching cpulimit: %s", exc)
                return False
            except OSError as exc:
                log.debug("limit: OS error launching cpulimit for pid=%d: %s", pid, exc)
                return False

        if process is None:
            log.debug("limit: cpulimit process is None for pid=%d", pid)
            return False

        log.debug("limit: cpulimit started (subprocess pid=%d) for pid=%d", process.pid, pid)
        self._processes[pid] = process
        self._limits[pid] = limit
        return True

    def unlimit(self, pid: int) -> bool:
        """Remove CPU limit from a process. Returns True on success."""
        if pid not in self._processes:
            log.debug("unlimit: pid=%d not in active limits", pid)
            return False

        proc = self._processes.pop(pid)
        self._limits.pop(pid, None)

        try:
            proc.terminate()
            proc.wait(timeout=2)
            log.debug("unlimit: cpulimit terminated for pid=%d", pid)
        except subprocess.TimeoutExpired:
            log.debug("unlimit: terminate timed out for pid=%d, sending SIGKILL", pid)
            try:
                proc.kill()
                proc.wait(timeout=1)
            except OSError as exc:
                log.debug("unlimit: kill failed for pid=%d: %s", pid, exc)
        except OSError as exc:
            log.debug("unlimit: error stopping cpulimit for pid=%d: %s", pid, exc)
        return True

    def is_limited(self, pid: int) -> bool:
        """Check if a process has an active CPU limit."""
        if pid not in self._processes:
            return False
        try:
            proc = self._processes[pid]
            if proc.poll() is not None:
                # cpulimit exited (target process likely died)
                del self._processes[pid]
                self._limits.pop(pid, None)
                return False
        except OSError as exc:
            log.debug("is_limited: error polling cpulimit for pid=%d: %s", pid, exc)
            self._processes.pop(pid, None)
            self._limits.pop(pid, None)
            return False
        return True

    def get_limit(self, pid: int) -> Optional[int]:
        """Get the current CPU limit percentage for a process, or None if not limited."""
        if self.is_limited(pid):
            return self._limits.get(pid)
        return None

    def get_all_limits(self) -> Dict[int, int]:
        """Return dict of all active limits {pid: limit_percent}."""
        dead = []
        for pid, proc in list(self._processes.items()):
            try:
                if proc.poll() is not None:
                    dead.append(pid)
            except OSError as exc:
                log.debug("get_all_limits: poll error for pid=%d: %s", pid, exc)
                dead.append(pid)

        for pid in dead:
            self._processes.pop(pid, None)
            self._limits.pop(pid, None)

        return dict(self._limits)

    def cleanup(self) -> None:
        """Terminate all managed cpulimit processes on shutdown."""
        for pid in list(self._processes.keys()):
            try:
                self.unlimit(pid)
            except Exception as exc:
                log.debug("cleanup: error releasing pid=%d: %s", pid, exc)

    @staticmethod
    def _run_with_sudo(cmd: list, password: str) -> Optional[subprocess.Popen]:
        """Run a command with sudo, providing the password via stdin."""
        try:
            sudo_cmd = ["sudo", "-S"] + cmd
            log.debug("_run_with_sudo: cmd=%s", sudo_cmd)
            proc = subprocess.Popen(
                sudo_cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
            if proc.stdin:
                proc.stdin.write((password + "\n").encode())
                proc.stdin.flush()
                proc.stdin.close()
            log.debug("_run_with_sudo: subprocess pid=%d", proc.pid)
            return proc
        except FileNotFoundError:
            log.debug("_run_with_sudo: sudo executable not found")
            return None
        except OSError as exc:
            log.debug("_run_with_sudo: failed: %s", exc)
            return None
