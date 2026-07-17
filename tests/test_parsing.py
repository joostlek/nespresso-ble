"""Tests for the pure parsing helpers."""

from __future__ import annotations

import pytest

from nespresso_ble import MachineFamily, MachineStatus, WaterHardness, is_supported
from nespresso_ble.device_type import family_from_service_uuids
from nespresso_ble.enums import barista_status, vertuo_next_status, vmini_status
from nespresso_ble.parsing import (
    BaristaState,
    VertuoNextState,
    decode_ble_string,
    parse_mac,
    parse_shadow,
    parse_version_v2,
    parse_version_v3,
    vmini_status_from_shadow,
)

VMINI_UUID = "96600100-526e-4676-a11a-af1eb848165b"
VERTUO_UUID = "06aa1910-f22a-11e3-9daa-0002a5d5c51b"
BARISTA_UUID = "65241910-0253-11e7-93ae-92361f002671"


@pytest.mark.parametrize(
    ("uuids", "family"),
    [
        ([VMINI_UUID], MachineFamily.VMINI),
        ([VERTUO_UUID], MachineFamily.VERTUO_NEXT),
        ([BARISTA_UUID], MachineFamily.BARISTA),
        (["0000180a-0000-1000-8000-00805f9b34fb"], MachineFamily.UNKNOWN),
        ([], MachineFamily.UNKNOWN),
        (None, MachineFamily.UNKNOWN),
    ],
)
def test_family_detection(uuids: list[str] | None, family: MachineFamily) -> None:
    """Test that families are detected from advertised service UUIDs."""
    assert family_from_service_uuids(uuids) is family
    assert is_supported(uuids) is (family is not MachineFamily.UNKNOWN)


@pytest.mark.parametrize(
    ("value", "expected"),
    [(453, "4.53"), (100, "1.0"), (0, "0.0")],
)
def test_version_v2(value: int, expected: str) -> None:
    """Test the major.minor version formatter."""
    assert parse_version_v2(value) == expected


def test_version_v3() -> None:
    """Test the major.minor.patch version formatter."""
    assert parse_version_v3(31800) == "3.18.0"


def test_decode_ble_string() -> None:
    """Test null-padded UTF-8 decoding."""
    assert decode_ble_string(b"ABC123\x00\x00\x00") == "ABC123"


def test_parse_mac() -> None:
    """Test MAC formatting from raw bytes."""
    assert parse_mac(bytes.fromhex("80f1b2e14874")) == "80:f1:b2:e1:48:74"
    assert parse_mac(b"\x00") is None


@pytest.mark.parametrize(
    ("value", "status"),
    [
        (1, MachineStatus.READY),
        (2, MachineStatus.BREWING),
        (4, MachineStatus.ERROR),
        (99, MachineStatus.UNKNOWN),
    ],
)
def test_barista_status_map(value: int, status: MachineStatus) -> None:
    """Test Barista state mapping."""
    assert barista_status(value) is status


@pytest.mark.parametrize(
    ("value", "status"),
    [
        (2, MachineStatus.READY),
        (4, MachineStatus.BREWING),
        (6, MachineStatus.DESCALING),
        (99, MachineStatus.UNKNOWN),
    ],
)
def test_vertuo_next_status_map(value: int, status: MachineStatus) -> None:
    """Test Vertuo Next state mapping."""
    assert vertuo_next_status(value) is status


@pytest.mark.parametrize(
    ("token", "status"),
    [
        ("ready", MachineStatus.READY),
        ("BREWING", MachineStatus.BREWING),
        ("nonsense", MachineStatus.UNKNOWN),
    ],
)
def test_vmini_status_map(token: str, status: MachineStatus) -> None:
    """Test VMini token mapping."""
    assert vmini_status(token) is status


def test_barista_state_parsing() -> None:
    """Test parsing raw Barista status bytes."""
    state = BaristaState(bytes([0b0000_1000, 0b0000_0100]))
    assert state.status is MachineStatus.READY
    assert state.error_present is True


def test_barista_state_too_short() -> None:
    """Test Barista parsing rejects short input."""
    with pytest.raises(ValueError, match="requires >= 2 bytes"):
        BaristaState(b"\x00")


def test_vertuo_next_state_parsing() -> None:
    """Test parsing raw Vertuo Next status bytes."""
    state = VertuoNextState(bytes([0b0000_0100, 0x02, 0x00]))
    assert state.status is MachineStatus.READY
    assert state.descaling_needed is True


def test_vertuo_next_state_too_short() -> None:
    """Test Vertuo Next parsing rejects short input."""
    with pytest.raises(ValueError, match="requires >= 3 bytes"):
        VertuoNextState(b"\x00\x00")


SHADOW_SCHEMA = (
    b"machineStatus,str;descalingAlert,bool;lastCoffeeFamilyID,int;"
    b"volumeCustomization,str;waterHardness,int;errorCode,str"
)
SHADOW_VALUES = b"ready,0,255,25;40;80,4,no error"


def test_parse_shadow() -> None:
    """Test the VMini self-describing shadow parser."""
    shadow = parse_shadow(SHADOW_SCHEMA, SHADOW_VALUES)
    assert shadow["machineStatus"] == "ready"
    assert shadow["descalingAlert"] is False
    assert shadow["lastCoffeeFamilyID"] == 255
    assert shadow["volumeCustomization"] == "25;40;80"
    assert shadow["waterHardness"] == 4
    assert shadow["errorCode"] == "no error"


def test_parse_shadow_empty() -> None:
    """Test the shadow parser tolerates empty input."""
    assert not parse_shadow(b"", b"")


def test_vmini_status_from_shadow() -> None:
    """Test extracting the machine status from a parsed shadow."""
    shadow = parse_shadow(SHADOW_SCHEMA, SHADOW_VALUES)
    assert vmini_status_from_shadow(shadow) is MachineStatus.READY
    assert vmini_status_from_shadow({}) is MachineStatus.UNKNOWN


def test_water_hardness_enum() -> None:
    """Test the water hardness enum values."""
    assert WaterHardness(4) is WaterHardness.LEVEL_4
