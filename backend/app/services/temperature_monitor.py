"""CPU/GPU temperature monitoring for queue throttling."""

import logging
import subprocess

logger = logging.getLogger(__name__)

CPU_THROTTLE_THRESHOLD = 90.0    # °C
GPU_THROTTLE_THRESHOLD = 95.0   # °C
RESUME_MARGIN = 5.0             # °C below threshold to resume


class TemperatureMonitor:
    """Monitors CPU (via WMI) and GPU (via nvidia-smi) temperatures.

    All methods return ``None`` when the monitoring source is unavailable.
    """

    def get_cpu_temp(self) -> float | None:
        """Return CPU temperature in °C, or ``None`` if unavailable."""
        try:
            import wmi

            c = wmi.WMI(namespace="root\\WMI")
            temps = c.MSAcpi_ThermalZoneTemperature()
            if not temps:
                return None
            temp_c = (temps[0].CurrentTemperature / 10.0) - 273.15
            return round(temp_c, 2)
        except ImportError:
            logger.debug("wmi module not available, skipping CPU temperature")
            return None
        except Exception:
            logger.debug("Failed to query CPU temperature via WMI", exc_info=True)
            return None

    def get_gpu_temp(self) -> float | None:
        """Return GPU temperature in °C, or ``None`` if unavailable."""
        try:
            result = subprocess.run(
                ["nvidia-smi", "--query-gpu=temperature.gpu", "--format=csv,noheader"],
                capture_output=True, text=True, timeout=5,
            )
            if result.returncode != 0:
                return None
            return float(result.stdout.strip())
        except FileNotFoundError:
            logger.debug("nvidia-smi not found, skipping GPU temperature")
            return None
        except Exception:
            logger.debug("Failed to query GPU temperature via nvidia-smi", exc_info=True)
            return None

    def should_throttle(self) -> bool:
        """Return ``True`` if CPU ≥ 90°C or GPU ≥ 95°C."""
        cpu = self.get_cpu_temp()
        gpu = self.get_gpu_temp()
        if cpu is not None and cpu >= CPU_THROTTLE_THRESHOLD:
            return True
        if gpu is not None and gpu >= GPU_THROTTLE_THRESHOLD:
            return True
        return False

    def should_resume(self) -> bool:
        """Return ``True`` only if both temps are below (threshold - margin)."""
        cpu = self.get_cpu_temp()
        gpu = self.get_gpu_temp()
        cpu_ok = cpu is None or cpu < CPU_THROTTLE_THRESHOLD - RESUME_MARGIN
        gpu_ok = gpu is None or gpu < GPU_THROTTLE_THRESHOLD - RESUME_MARGIN
        return cpu_ok and gpu_ok
