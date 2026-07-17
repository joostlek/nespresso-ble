"""Tests for family detection and push support."""

from __future__ import annotations

import logging

from nespresso_ble import NespressoBluetoothDeviceData
from nespresso_ble.const import (
    BARISTA_BASIC_SERVICE,
    VERTUO_BASIC_SERVICE,
    VMINI_BASIC_SERVICE,
)

DEVICE_INFO_SERVICE = "0000180a-0000-1000-8000-00805f9b34fb"


def _make_client() -> NespressoBluetoothDeviceData:
    return NespressoBluetoothDeviceData(logging.getLogger("test"))


def test_supports_push_for_known_families() -> None:
    """All supported families advertise push support."""
    client = _make_client()
    assert client.supports_push([VMINI_BASIC_SERVICE]) is True
    assert client.supports_push([VERTUO_BASIC_SERVICE]) is True
    assert client.supports_push([BARISTA_BASIC_SERVICE]) is True


def test_supports_push_for_unknown() -> None:
    """Unknown or empty service UUIDs do not advertise push support."""
    client = _make_client()
    assert client.supports_push([DEVICE_INFO_SERVICE]) is False
    assert client.supports_push([]) is False
