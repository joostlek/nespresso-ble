"""Exceptions for the Nespresso BLE library."""

from __future__ import annotations


class NespressoError(Exception):
    """Base error for the Nespresso BLE library."""


class UnsupportedDeviceError(NespressoError):
    """The BLE device is not a supported Nespresso machine."""


class DisconnectedError(NespressoError):
    """Disconnected from the device unexpectedly."""


class AuthError(NespressoError):
    """Authentication with the machine failed."""


class NotOnboardedError(NespressoError):
    """The machine has no stored auth key and no key was provided."""
