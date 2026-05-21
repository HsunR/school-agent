"""Tests for TemperatureMonitor."""

import sys
from unittest.mock import MagicMock

import pytest

from app.services.temperature_monitor import TemperatureMonitor


@pytest.fixture
def monitor():
    return TemperatureMonitor()


def _mock_wmi_module(mock_wmi_cls):
    """Create a fake ``wmi`` module for monkeypatching ``sys.modules``."""
    mod = MagicMock()
    mod.WMI = mock_wmi_cls
    return mod


class TestCpuTemperature:
    def test_cpu_temp_returns_float_when_wmi_available(self, monkeypatch):
        mock_wmi_cls = MagicMock()
        mock_tz = MagicMock()
        mock_tz.CurrentTemperature = 3050
        mock_wmi_cls.return_value.MSAcpi_ThermalZoneTemperature.return_value = [mock_tz]
        monkeypatch.setitem(sys.modules, "wmi", _mock_wmi_module(mock_wmi_cls))
        monitor = TemperatureMonitor()
        temp = monitor.get_cpu_temp()
        assert temp is not None
        assert abs(temp - 31.85) < 0.01

    def test_cpu_temp_returns_none_when_wmi_unavailable(self, monkeypatch):
        import builtins
        original_import = builtins.__import__
        def mock_import(name, *args, **kwargs):
            if name == "wmi":
                raise ImportError("No module named wmi")
            return original_import(name, *args, **kwargs)
        monkeypatch.setattr(builtins, "__import__", mock_import)
        monitor = TemperatureMonitor()
        monkeypatch.setattr(monitor, "_get_cpu_temp_lhm", lambda: None)
        monkeypatch.setattr(monitor, "_get_cpu_temp_powershell", lambda: None)
        assert monitor.get_cpu_temp() is None

    def test_cpu_temp_returns_none_wmi_query_fails(self, monkeypatch):
        mock_wmi_cls = MagicMock()
        mock_wmi_cls.return_value.MSAcpi_ThermalZoneTemperature.side_effect = Exception("WMI query failed")
        monkeypatch.setitem(sys.modules, "wmi", _mock_wmi_module(mock_wmi_cls))
        monitor = TemperatureMonitor()
        monkeypatch.setattr(monitor, "_get_cpu_temp_lhm", lambda: None)
        monkeypatch.setattr(monitor, "_get_cpu_temp_powershell", lambda: None)
        assert monitor.get_cpu_temp() is None

    def test_cpu_temp_falls_back_to_lhm_when_wmi_returns_none(self, monkeypatch):
        mock_wmi_cls = MagicMock()
        mock_wmi_cls.return_value.MSAcpi_ThermalZoneTemperature.return_value = []
        monkeypatch.setitem(sys.modules, "wmi", _mock_wmi_module(mock_wmi_cls))
        monitor = TemperatureMonitor()
        monkeypatch.setattr(monitor, "_get_cpu_temp_lhm", lambda: 68.5)
        assert monitor.get_cpu_temp() == 68.5

    def test_cpu_temp_returns_none_when_both_wmi_and_lhm_fail(self, monkeypatch):
        mock_wmi_cls = MagicMock()
        mock_wmi_cls.return_value.MSAcpi_ThermalZoneTemperature.return_value = []
        monkeypatch.setitem(sys.modules, "wmi", _mock_wmi_module(mock_wmi_cls))
        monitor = TemperatureMonitor()
        monkeypatch.setattr(monitor, "_get_cpu_temp_lhm", lambda: None)
        monkeypatch.setattr(monitor, "_get_cpu_temp_powershell", lambda: None)
        assert monitor.get_cpu_temp() is None

    def test_cpu_temp_falls_back_to_powershell_when_wmi_and_lhm_fail(self, monkeypatch):
        mock_wmi_cls = MagicMock()
        mock_wmi_cls.return_value.MSAcpi_ThermalZoneTemperature.return_value = []
        monkeypatch.setitem(sys.modules, "wmi", _mock_wmi_module(mock_wmi_cls))
        monitor = TemperatureMonitor()
        monkeypatch.setattr(monitor, "_get_cpu_temp_lhm", lambda: None)
        monkeypatch.setattr(monitor, "_get_cpu_temp_powershell", lambda: 75.3)
        assert monitor.get_cpu_temp() == 75.3


class TestPowershellTemperature:
    def test_powershell_returns_temperature_in_celsius(self, monkeypatch):
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "353.0\n"
        monkeypatch.setattr("app.services.temperature_monitor.subprocess.run", lambda *a, **kw: mock_result)
        monitor = TemperatureMonitor()
        temp = monitor._get_cpu_temp_powershell()
        # 353K - 273.15 = 79.85°C
        assert temp is not None
        assert abs(temp - 79.85) < 0.01

    def test_powershell_returns_none_on_failure(self, monkeypatch):
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = ""
        monkeypatch.setattr("app.services.temperature_monitor.subprocess.run", lambda *a, **kw: mock_result)
        monitor = TemperatureMonitor()
        assert monitor._get_cpu_temp_powershell() is None


class TestGpuTemperature:
    def test_gpu_temp_returns_float_when_nvidia_smi_available(self, monkeypatch):
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "72\n"
        monkeypatch.setattr("app.services.temperature_monitor.subprocess.run", lambda *a, **kw: mock_result)
        monitor = TemperatureMonitor()
        temp = monitor.get_gpu_temp()
        assert temp == 72.0

    def test_gpu_temp_returns_none_when_nvidia_smi_fails(self, monkeypatch):
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = ""
        monkeypatch.setattr("app.services.temperature_monitor.subprocess.run", lambda *a, **kw: mock_result)
        monitor = TemperatureMonitor()
        assert monitor.get_gpu_temp() is None

    def test_gpu_temp_returns_none_when_command_not_found(self, monkeypatch):
        def mock_run(*args, **kwargs):
            raise FileNotFoundError("nvidia-smi not found")
        monkeypatch.setattr("app.services.temperature_monitor.subprocess.run", mock_run)
        monitor = TemperatureMonitor()
        assert monitor.get_gpu_temp() is None


class TestThrottleLogic:
    def test_should_throttle_true_when_cpu_over_90(self, monkeypatch):
        monitor = TemperatureMonitor()
        monkeypatch.setattr(monitor, "get_cpu_temp", lambda: 95.0)
        monkeypatch.setattr(monitor, "get_gpu_temp", lambda: 50.0)
        assert monitor.should_throttle() is True

    def test_should_throttle_true_when_gpu_over_95(self, monkeypatch):
        monitor = TemperatureMonitor()
        monkeypatch.setattr(monitor, "get_cpu_temp", lambda: 50.0)
        monkeypatch.setattr(monitor, "get_gpu_temp", lambda: 97.0)
        assert monitor.should_throttle() is True

    def test_should_throttle_false_when_below_threshold(self, monkeypatch):
        monitor = TemperatureMonitor()
        monkeypatch.setattr(monitor, "get_cpu_temp", lambda: 60.0)
        monkeypatch.setattr(monitor, "get_gpu_temp", lambda: 70.0)
        assert monitor.should_throttle() is False

    def test_should_throttle_false_when_unavailable(self, monkeypatch):
        monitor = TemperatureMonitor()
        monkeypatch.setattr(monitor, "get_cpu_temp", lambda: None)
        monkeypatch.setattr(monitor, "get_gpu_temp", lambda: None)
        assert monitor.should_throttle() is False

    def test_should_resume_true_when_cooled_down(self, monkeypatch):
        monitor = TemperatureMonitor()
        monkeypatch.setattr(monitor, "get_cpu_temp", lambda: 80.0)
        monkeypatch.setattr(monitor, "get_gpu_temp", lambda: 85.0)
        assert monitor.should_resume() is True

    def test_should_resume_false_when_still_hot(self, monkeypatch):
        monitor = TemperatureMonitor()
        monkeypatch.setattr(monitor, "get_cpu_temp", lambda: 88.0)
        monkeypatch.setattr(monitor, "get_gpu_temp", lambda: 92.0)
        assert monitor.should_resume() is False
