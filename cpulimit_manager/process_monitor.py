"""Process monitoring module using psutil."""

import logging
import subprocess
from dataclasses import dataclass
from typing import List, Tuple

import psutil

log = logging.getLogger(__name__)


@dataclass
class ProcessInfo:
    """Holds information about a single running process."""

    pid: int
    name: str
    cmdline: str
    username: str
    cpu_percent: float


class ProcessMonitor:
    """Monitors system processes and CPU usage."""

    def get_processes(self) -> List[ProcessInfo]:
        """Return list of running processes sorted by CPU usage descending.

        Returns an empty list if the process iterator itself fails.
        """
        processes: List[ProcessInfo] = []
        try:
            iter_ = psutil.process_iter(
                ["pid", "name", "cmdline", "username", "cpu_percent"]
            )
        except Exception as exc:
            log.debug("get_processes: process_iter failed: %s", exc)
            return processes

        for proc in iter_:
            try:
                info = proc.info
                # cmdline may be None or an empty list for kernel threads
                cmdline = (
                    " ".join(info["cmdline"])
                    if info["cmdline"]
                    else info["name"] or ""
                )
                processes.append(
                    ProcessInfo(
                        pid=info["pid"],
                        name=info["name"] or "",
                        cmdline=cmdline,
                        username=info["username"] or "",
                        cpu_percent=info["cpu_percent"] or 0.0,
                    )
                )
            except (
                psutil.NoSuchProcess,
                psutil.AccessDenied,
                psutil.ZombieProcess,
            ):
                # Process disappeared or is inaccessible between iterations
                continue
            except (KeyError, TypeError, ValueError) as exc:
                # Unexpected structure in proc.info
                log.debug("get_processes: skipping malformed proc entry: %s", exc)
                continue

        processes.sort(key=lambda p: p.cpu_percent, reverse=True)
        log.debug("get_processes: %d processes collected", len(processes))
        return processes

    def get_cpu_per_core(self) -> List[float]:
        """Return CPU usage percentage per core.

        Returns an empty list on failure.
        """
        try:
            result = psutil.cpu_percent(percpu=True)
            return result  # type: ignore[return-value]
        except Exception as exc:
            log.debug("get_cpu_per_core: failed: %s", exc)
            return []

    def get_cpu_overall_percent(self) -> float:
        """Return total CPU usage across all cores (0–100 * num_cores scale).

        Returns 0.0 on failure.
        """
        try:
            return psutil.cpu_percent(percpu=False)
        except Exception as exc:
            log.debug("get_cpu_overall_percent: failed: %s", exc)
            return 0.0

    def get_cpu_temps(self) -> dict:
        """Return CPU core temperatures as {core_index: celsius}.

        Tries coretemp (Intel/generic Linux), then k10temp (AMD), then
        cpu_thermal (ARM). Returns an empty dict if unavailable.
        """
        result: dict = {}
        try:
            sensors = psutil.sensors_temperatures()
        except (AttributeError, Exception) as exc:
            log.debug("get_cpu_temps: sensors unavailable: %s", exc)
            return result

        # Intel / generic coretemp
        if "coretemp" in sensors:
            for entry in sensors["coretemp"]:
                label = entry.label
                if label.startswith("Core "):
                    try:
                        idx = int(label.split()[1])
                        result[idx] = entry.current
                    except (IndexError, ValueError):
                        pass
            # Overall package temperature stored at key -1
            for entry in sensors["coretemp"]:
                if "Package" in entry.label:
                    result[-1] = entry.current
                    break

        # AMD k10temp
        elif "k10temp" in sensors:
            for entry in sensors["k10temp"]:
                if entry.label in ("Tctl", "Tccd1"):
                    result[-1] = entry.current
                    break

        # ARM / generic
        elif "cpu_thermal" in sensors:
            for i, entry in enumerate(sensors["cpu_thermal"]):
                result[i] = entry.current

        # Fallback: thinkpad / acpitz package temp
        if -1 not in result:
            for key in ("thinkpad", "acpitz"):
                if key in sensors:
                    for entry in sensors[key]:
                        if entry.label in ("CPU", "") and entry.current > 0:
                            result[-1] = entry.current
                            break
                if -1 in result:
                    break

        return result

    def get_cpu_freq(self) -> Tuple[str, str]:
        """Return (cpu_model_name, frequency_ghz_string).

        Falls back to safe defaults on any read error.
        """
        freq_str = "N/A"
        try:
            freq = psutil.cpu_freq()
            if freq and freq.current > 0:
                freq_str = f"{freq.current / 1000:.1f} GHz"
        except Exception as exc:
            log.debug("get_cpu_freq: psutil.cpu_freq failed: %s", exc)

        cpu_name = "CPU"
        try:
            with open("/proc/cpuinfo", "r") as f:
                for line in f:
                    if "model name" in line and ":" in line:
                        cpu_name = line.split(":", 1)[1].strip()
                        break
        except OSError as exc:
            log.debug("get_cpu_freq: /proc/cpuinfo unavailable: %s", exc)
            # Fallback for macOS / FreeBSD
            try:
                result = subprocess.run(
                    ["sysctl", "-n", "machdep.cpu.brand_string"],
                    capture_output=True,
                    text=True,
                    timeout=2,
                )
                if result.returncode == 0 and result.stdout.strip():
                    cpu_name = result.stdout.strip()
            except (OSError, subprocess.TimeoutExpired) as sub_exc:
                log.debug("get_cpu_freq: sysctl fallback failed: %s", sub_exc)

        return cpu_name, freq_str

    def get_load_avg(self) -> Tuple[float, float, float]:
        """Return system load average (1, 5, 15 minutes).

        Returns (0.0, 0.0, 0.0) on unsupported platforms or errors.
        """
        try:
            return psutil.getloadavg()  # type: ignore[return-value]
        except (AttributeError, OSError) as exc:
            log.debug("get_load_avg: not available: %s", exc)
            return (0.0, 0.0, 0.0)
