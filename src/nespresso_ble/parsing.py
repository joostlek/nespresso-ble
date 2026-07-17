"""Pure byte/text parsing for Nespresso BLE characteristics.

Bytes in, structured values out. No I/O. Layouts verified against the
decompiled Nespresso Smart app.
"""

from __future__ import annotations

from .enums import (
    MachineStatus,
    WaterHardness,
    barista_status,
    vertuo_next_status,
    vmini_status,
)


def _bit(value: int, pos: int) -> bool:
    return bool(value & (1 << pos))


def _u16_msb(data: bytes, offset: int) -> int:
    return ((data[offset] & 0xFF) << 8) | (data[offset + 1] & 0xFF)


def parse_version_v2(value: int) -> str:
    """Format ``major.minor`` from a 16-bit value (Utils.getVersionV2)."""
    return f"{value // 100}.{value % 100}"


def parse_version_v3(value: int) -> str:
    """Format ``major.minor.patch`` from a 16-bit value (Utils.getVersionV3)."""
    major = value // 10000
    remainder = value % 10000
    return f"{major}.{remainder // 100}.{remainder % 100}"


def decode_ble_string(raw: bytes) -> str:
    """Decode a (possibly null-padded) UTF-8 BLE string."""
    return bytes(raw).split(b"\x00", 1)[0].decode("utf-8", errors="replace").strip()


def parse_serial_number(data: bytes) -> str:
    """Decode the null-terminated UTF-8 serial number."""
    return decode_ble_string(data)


def parse_mac(data: bytes) -> str | None:
    """Format 6 raw bytes as a MAC address."""
    if len(data) != 6:
        return None
    return ":".join(f"{b:02x}" for b in data)


class BaristaState:  # pylint: disable=too-few-public-methods
    """Parsed Barista (Original line) machine status."""

    def __init__(self, data: bytes) -> None:
        """Parse the raw Barista status bytes."""
        if len(data) < 2:
            msg = f"Barista status requires >= 2 bytes, got {len(data)}"
            raise ValueError(msg)
        b0, b1 = data[0], data[1]
        self.status: MachineStatus = barista_status((b1 & 0xFC) >> 2)
        self.error_present: bool = _bit(b0, 3)
        self.motor_running: bool = _bit(b0, 4)
        self.induction_heating: bool = _bit(b0, 5)


class VertuoNextState:  # pylint: disable=too-few-public-methods
    """Parsed Vertuo Next machine status."""

    def __init__(self, data: bytes) -> None:
        """Parse the raw Vertuo Next status bytes."""
        if len(data) < 3:
            msg = f"Vertuo Next status requires >= 3 bytes, got {len(data)}"
            raise ValueError(msg)
        b0, b1, b2 = data[0], data[1], data[2]
        self.status: MachineStatus = vertuo_next_status((b1 & 0x0F) + (b2 & 0xF0))
        self.water_tank_empty: bool = _bit(b0, 0)
        self.cleaning_needed: bool = _bit(b0, 1)
        self.descaling_needed: bool = _bit(b0, 2)
        self.error_present: bool = _bit(b0, 4)
        self.milk_frother_running: bool = _bit(b1, 4)
        self.capsule_container_full: bool = _bit(b1, 6)
        self.brewing_unit_closed: bool = _bit(b1, 7)


def parse_vertuo_machine_info(data: bytes) -> dict[str, str]:
    """Parse the Vertuo Next 16-byte machine info characteristic."""
    if len(data) < 10:
        msg = f"Machine info requires >= 10 bytes, got {len(data)}"
        raise ValueError(msg)
    return {
        "hardware_version": parse_version_v2(_u16_msb(data, 0)),
        "firmware_version": parse_version_v2(_u16_msb(data, 4)),
        "connectivity_fw_version": parse_version_v3(_u16_msb(data, 8)),
    }


def parse_barista_machine_info(data: bytes) -> dict[str, str]:
    """Parse the Barista 14-byte machine info characteristic."""
    if len(data) < 8:
        msg = f"Machine info requires >= 8 bytes, got {len(data)}"
        raise ValueError(msg)
    return {
        "hardware_version": parse_version_v2(_u16_msb(data, 0)),
        "firmware_version": parse_version_v2(_u16_msb(data, 4)),
    }


def parse_water_hardness(data: bytes) -> WaterHardness | None:
    """Parse the water hardness characteristic (byte index 2)."""
    if len(data) < 3:
        return None
    try:
        return WaterHardness(data[2])
    except ValueError:
        return None


def parse_capsule_count(data: bytes) -> int:
    """Parse the big-endian capsule counter."""
    return int.from_bytes(data, "big")


def parse_shadow(schema_raw: bytes, values_raw: bytes) -> dict[str, str | int | bool]:
    """Parse the VMini self-describing device shadow into typed fields.

    ``schema_raw`` is ``name,type`` pairs separated by ``;``; ``values_raw`` is
    the matching comma-separated values. Some string values contain ``;``, so
    values are aligned to the number of schema fields.
    """
    schema = decode_ble_string(schema_raw)
    values = decode_ble_string(values_raw)
    if not schema or not values:
        return {}

    fields: list[tuple[str, str]] = []
    for part in schema.split(";"):
        if "," in part:
            name, typ = part.rsplit(",", 1)
            fields.append((name, typ))

    raw_values = values.split(",")
    if len(raw_values) < len(fields):
        return {}
    if len(raw_values) > len(fields):
        head = raw_values[: len(fields) - 1]
        tail = ",".join(raw_values[len(fields) - 1 :])
        raw_values = [*head, tail]

    result: dict[str, str | int | bool] = {}
    for (name, typ), value in zip(fields, raw_values, strict=False):
        if typ == "bool":
            result[name] = value not in ("0", "", "false", "False")
        elif typ == "int":
            try:
                result[name] = int(value)
            except ValueError:
                result[name] = value
        else:
            result[name] = value
    return result


def vmini_status_from_shadow(shadow: dict[str, str | int | bool]) -> MachineStatus:
    """Map the VMini shadow ``machineStatus`` token to a typed status."""
    token = shadow.get("machineStatus")
    if isinstance(token, str):
        return vmini_status(token)
    return MachineStatus.UNKNOWN
