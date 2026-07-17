"""Tests for the typed device model helpers."""

from __future__ import annotations

from nespresso_ble import MachineFamily, MachineStatus, NespressoDevice, WaterHardness
from nespresso_ble.client import _apply_vmini_shadow, _firmware_from_assets


def test_friendly_name() -> None:
    """Test the per-family friendly name."""
    device = NespressoDevice(
        address="80:F1:B2:E1:48:76", name="VL-MD1", family=MachineFamily.VMINI
    )
    assert device.friendly_name() == "Nespresso Vertuo Mini"


def test_apply_vmini_shadow() -> None:
    """Test that a parsed shadow populates typed fields."""
    device = NespressoDevice(
        address="80:F1:B2:E1:48:76", name="VL-MD1", family=MachineFamily.VMINI
    )
    _apply_vmini_shadow(
        device,
        {
            "machineStatus": "brewing",
            "descalingAlert": True,
            "waterHardness": 4,
            "errorCode": "no error",
        },
    )
    assert device.status is MachineStatus.BREWING
    assert device.descaling_needed is True
    assert device.water_hardness is WaterHardness.LEVEL_4
    assert device.error is False
    assert device.error_code == "no error"


def test_apply_vmini_shadow_error() -> None:
    """Test that a non-'no error' code marks the machine in error."""
    device = NespressoDevice(
        address="80:F1:B2:E1:48:76", name="VL-MD1", family=MachineFamily.VMINI
    )
    _apply_vmini_shadow(device, {"errorCode": "water tank missing"})
    assert device.error is True


def test_firmware_from_assets() -> None:
    """Test extracting the main firmware version from the asset list."""
    assets = "fmw-main,4.5.3,1.1.0;recipe,4.5.0,1.1.0"
    assert _firmware_from_assets(assets) == "4.5.3"
    assert _firmware_from_assets("recipe,1.0.0,1.0.0") is None
