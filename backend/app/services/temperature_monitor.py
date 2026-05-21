"""CPU/GPU temperature monitoring for queue throttling."""

import logging
import os
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
        # Try WMI first (works for Intel)
        try:
            import wmi

            c = wmi.WMI(namespace="root\\WMI")
            temps = c.MSAcpi_ThermalZoneTemperature()
            if temps:
                temps_c = [
                    (t.CurrentTemperature / 10.0) - 273.15
                    for t in temps
                    if t.CurrentTemperature is not None and t.CurrentTemperature > 0
                ]
                if temps_c:
                    return round(max(temps_c), 2)
        except ImportError:
            logger.debug("wmi module not available, skipping WMI CPU temp")
        except Exception:
            logger.debug("Failed to query CPU temperature via WMI", exc_info=True)

        # Fallback to LibreHardwareMonitorLib (works for AMD)
        return self._get_cpu_temp_lhm()

    def _get_cpu_temp_lhm(self) -> float | None:
        """Read CPU temperature via LibreHardwareMonitorLib (AMD fallback)."""
        dll_path = os.path.join(os.path.dirname(__file__), "sensors", "LibreHardwareMonitorLib.dll")
        if not os.path.isfile(dll_path):
            logger.debug("LibreHardwareMonitorLib.dll not found")
            return None
        try:
            import clr

            clr.AddReference(dll_path)
            from LibreHardwareMonitor.Hardware import Computer, SensorType

            computer = Computer()
            computer.IsCpuEnabled = True
            computer.Open()
            try:
                for hardware in computer.Hardware:
                    hardware.Update()
                    for sensor in hardware.Sensors:
                        if sensor.SensorType == SensorType.Temperature and "CPU" in sensor.Name:
                            return round(float(sensor.Value), 2)
            finally:
                computer.Close()
        except Exception:
            logger.debug("Failed to query CPU temperature via LHM", exc_info=True)
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
