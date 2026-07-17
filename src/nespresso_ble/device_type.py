"""Machine family detection for Nespresso BLE devices."""

from __future__ import annotations

from .const import SERVICE_UUID_TO_FAMILY
from .enums import MachineFamily


def family_from_service_uuids(
    service_uuids: list[str] | None,
) -> MachineFamily:
    """Determine the machine family from advertised service UUIDs."""
    if not service_uuids:
        return MachineFamily.UNKNOWN
    lowered = {uuid.lower() for uuid in service_uuids}
    for service_uuid, family in SERVICE_UUID_TO_FAMILY.items():
        if service_uuid in lowered:
            return family
    return MachineFamily.UNKNOWN


def is_supported(service_uuids: list[str] | None) -> bool:
    """Return True if the advertised service UUIDs map to a known family."""
    return family_from_service_uuids(service_uuids) is not MachineFamily.UNKNOWN
