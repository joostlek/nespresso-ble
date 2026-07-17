"""Nespresso BLE library."""

from __future__ import annotations

from .client import NespressoBluetoothDeviceData
from .const import ALL_SERVICE_UUIDS, SERVICE_UUID_TO_FAMILY
from .device_type import family_from_service_uuids, is_supported
from .enums import MachineFamily, MachineStatus, PairingStatus, WaterHardness
from .exceptions import (
    AuthError,
    DisconnectedError,
    NespressoError,
    NotOnboardedError,
    UnsupportedDeviceError,
)
from .models import NespressoDevice

__version__ = "0.3.0"

__all__ = [
    "ALL_SERVICE_UUIDS",
    "SERVICE_UUID_TO_FAMILY",
    "AuthError",
    "DisconnectedError",
    "MachineFamily",
    "MachineStatus",
    "NespressoBluetoothDeviceData",
    "NespressoDevice",
    "NespressoError",
    "NotOnboardedError",
    "PairingStatus",
    "UnsupportedDeviceError",
    "WaterHardness",
    "family_from_service_uuids",
    "is_supported",
]
