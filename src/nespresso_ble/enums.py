"""Enumerations for Nespresso BLE machines."""

from __future__ import annotations

from enum import IntEnum, StrEnum


class MachineFamily(StrEnum):
    """Nespresso machine hardware families with distinct BLE protocols."""

    BARISTA = "barista"
    VERTUO_NEXT = "vertuo_next"
    VMINI = "vmini"
    UNKNOWN = "unknown"


class MachineStatus(StrEnum):
    """Unified machine operational status across families."""

    STANDBY = "standby"
    READY = "ready"
    BREWING = "brewing"
    HEATING = "heating"
    COOLDOWN = "cooldown"
    DESCALING = "descaling"
    DESCALING_READY = "descaling_ready"
    CLEANING = "cleaning"
    RINSING = "rinsing"
    EMPTYING = "emptying"
    POWER_SAVE = "power_save"
    UPDATING = "updating"
    CAPSULE_READING = "capsule_reading"
    TANK_EMPTY = "tank_empty"
    SERVICE_MODE = "service_mode"
    MAINTENANCE_MENU = "maintenance_menu"
    OVERHEATED = "overheated"
    PAUSED = "paused"
    SETUP = "setup"
    FACTORY_RESET = "factory_reset"
    INITIALIZING = "initializing"
    ERROR = "error"
    UNKNOWN = "unknown"


class PairingStatus(StrEnum):
    """VMini pairing state."""

    NOT_PAIRED = "not_paired"
    PAIRED = "paired"
    PAIRING_ONGOING = "pairing_ongoing"
    UNKNOWN = "unknown"


class WaterHardness(IntEnum):
    """Configured water hardness level."""

    LEVEL_0 = 0
    LEVEL_1 = 1
    LEVEL_2 = 2
    LEVEL_3 = 3
    LEVEL_4 = 4


# Raw state-value maps recovered from the decompiled Nespresso Smart app.
_BARISTA_STATES: dict[int, MachineStatus] = {
    0: MachineStatus.STANDBY,
    1: MachineStatus.READY,
    2: MachineStatus.BREWING,
    3: MachineStatus.MAINTENANCE_MENU,
    4: MachineStatus.ERROR,
    5: MachineStatus.OVERHEATED,
    6: MachineStatus.SETUP,
    7: MachineStatus.PAUSED,
}

_VERTUO_NEXT_STATES: dict[int, MachineStatus] = {
    0: MachineStatus.FACTORY_RESET,
    1: MachineStatus.HEATING,
    2: MachineStatus.READY,
    3: MachineStatus.DESCALING_READY,
    4: MachineStatus.BREWING,
    5: MachineStatus.CLEANING,
    6: MachineStatus.DESCALING,
    7: MachineStatus.EMPTYING,
    8: MachineStatus.ERROR,
    9: MachineStatus.POWER_SAVE,
    10: MachineStatus.COOLDOWN,
    11: MachineStatus.SERVICE_MODE,
    12: MachineStatus.STANDBY,
    13: MachineStatus.UPDATING,
    14: MachineStatus.RINSING,
    17: MachineStatus.CAPSULE_READING,
    19: MachineStatus.TANK_EMPTY,
    21: MachineStatus.INITIALIZING,
    23: MachineStatus.MAINTENANCE_MENU,
}

# VMini reports machineStatus as a text token in its device shadow.
_VMINI_STATES: dict[str, MachineStatus] = {
    "ready": MachineStatus.READY,
    "brewing": MachineStatus.BREWING,
    "heating": MachineStatus.HEATING,
    "heatup": MachineStatus.HEATING,
    "standby": MachineStatus.STANDBY,
    "descaling": MachineStatus.DESCALING,
    "cleaning": MachineStatus.CLEANING,
    "rinsing": MachineStatus.RINSING,
    "power_save": MachineStatus.POWER_SAVE,
    "powersave": MachineStatus.POWER_SAVE,
    "error": MachineStatus.ERROR,
    "updating": MachineStatus.UPDATING,
}


def barista_status(value: int) -> MachineStatus:
    """Map a raw Barista state value to a unified status."""
    return _BARISTA_STATES.get(value, MachineStatus.UNKNOWN)


def vertuo_next_status(value: int) -> MachineStatus:
    """Map a raw Vertuo Next state value to a unified status."""
    return _VERTUO_NEXT_STATES.get(value, MachineStatus.UNKNOWN)


def vmini_status(token: str) -> MachineStatus:
    """Map a VMini shadow status token to a unified status."""
    return _VMINI_STATES.get(token.strip().lower(), MachineStatus.UNKNOWN)


def pairing_status(value: int) -> PairingStatus:
    """Map a raw VMini pairing byte to a typed status."""
    return {
        0: PairingStatus.NOT_PAIRED,
        1: PairingStatus.PAIRED,
        2: PairingStatus.PAIRING_ONGOING,
    }.get(value, PairingStatus.UNKNOWN)
