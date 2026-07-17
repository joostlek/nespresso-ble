"""Typed data model for Nespresso BLE machines."""

from __future__ import annotations

from dataclasses import dataclass, field

from .enums import MachineFamily, MachineStatus, PairingStatus, WaterHardness


@dataclass(kw_only=True)
class NespressoDevice:
    """Fully parsed, typed state of a Nespresso machine."""

    # Identity
    address: str
    name: str
    family: MachineFamily
    serial: str | None = None
    manufacturer: str | None = None
    model_number: str | None = None
    firmware_version: str | None = None
    hardware_version: str | None = None

    # State
    status: MachineStatus = MachineStatus.UNKNOWN
    error: bool = False
    error_code: str | None = None
    water_hardness: WaterHardness | None = None

    # Maintenance / consumable flags (None when the family does not report them)
    descaling_needed: bool | None = None
    cleaning_needed: bool | None = None
    water_tank_empty: bool | None = None
    capsule_container_full: bool | None = None
    brewing_unit_closed: bool | None = None

    # VMini specifics
    pairing_status: PairingStatus | None = None
    wifi_mac: str | None = None
    iot_market: str | None = None

    # Original-line specifics
    capsule_count: int | None = None

    # Raw shadow / extra values keyed by the machine's own field names, for
    # advanced consumers. Typed fields above should be preferred.
    extra: dict[str, str | int | bool] = field(default_factory=dict)

    def friendly_name(self) -> str:
        """Return a friendly product name for the machine."""
        return {
            MachineFamily.VMINI: "Nespresso Vertuo Mini",
            MachineFamily.VERTUO_NEXT: "Nespresso Vertuo",
            MachineFamily.BARISTA: "Nespresso Barista",
        }.get(self.family, "Nespresso machine")
