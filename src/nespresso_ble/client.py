"""Connection manager and family-dispatching client for Nespresso machines."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
import contextlib
from functools import partial
from typing import TYPE_CHECKING

from async_interrupt import interrupt
from bleak import BleakClient, BleakError
from bleak_retry_connector import BleakClientWithServiceCache, establish_connection

from . import parsing
from .const import (
    BARISTA_CHAR_INFO,
    BARISTA_CHAR_SERIAL,
    BARISTA_CHAR_STATE,
    CHAR_FIRMWARE_REV,
    CHAR_MANUFACTURER,
    CHAR_MODEL_NUMBER,
    DEFAULT_MAX_UPDATE_ATTEMPTS,
    UPDATE_TIMEOUT,
    VERTUO_CHAR_INFO,
    VERTUO_CHAR_NBCAPS,
    VERTUO_CHAR_SERIAL,
    VERTUO_CHAR_STATE,
    VERTUO_CHAR_WATER_HARDNESS,
    VMINI_CHAR_ASSET_VERSIONS,
    VMINI_CHAR_IOT_MARKET,
    VMINI_CHAR_MACHINE_TOKEN,
    VMINI_CHAR_PAIRING,
    VMINI_CHAR_SERIAL,
    VMINI_CHAR_SHADOW_HEADER,
    VMINI_CHAR_SHADOW_UPDATE,
    VMINI_CHAR_WIFI_MAC,
    VMINI_TOKEN_LENGTH,
)
from .device_type import family_from_service_uuids
from .enums import MachineFamily, WaterHardness, pairing_status
from .exceptions import AuthError, DisconnectedError, UnsupportedDeviceError
from .models import NespressoDevice
from .parsing import vmini_status_from_shadow

if TYPE_CHECKING:
    from logging import Logger

    from bleak.backends.device import BLEDevice

UpdateCallback = Callable[[NespressoDevice], None]


class NespressoBluetoothDeviceData:
    """Connects to any supported Nespresso machine and returns typed data."""

    def __init__(
        self,
        logger: Logger,
        auth_key: str | None = None,
        max_attempts: int = DEFAULT_MAX_UPDATE_ATTEMPTS,
        client_class: type[BleakClient] = BleakClientWithServiceCache,
    ) -> None:
        """Initialize.

        ``auth_key`` is reused across connections. ``client_class`` may be set to
        ``habluetooth.HaBleakClientWrapper`` to route through an ESPHome proxy.
        """
        self.logger = logger
        self.auth_key = auth_key
        self.max_attempts = max_attempts
        self.client_class = client_class

    async def update_device(self, ble_device: BLEDevice) -> NespressoDevice:
        """Connect, read the machine's state once, and disconnect."""
        for attempt in range(self.max_attempts):
            is_final = attempt == self.max_attempts - 1
            try:
                return await self._update_device(ble_device)
            except DisconnectedError:
                if is_final:
                    raise
                self.logger.debug("Disconnected from %s", ble_device.address)
            except BleakError as err:
                if is_final:
                    raise
                self.logger.debug("Bleak error: %s", err)
        msg = "unreachable"
        raise RuntimeError(msg)

    async def stream(
        self,
        ble_device: BLEDevice,
        callback: UpdateCallback,
        stop_event: asyncio.Event | None = None,
    ) -> None:
        """Keep a connection open and push typed state on every change.

        Subscribes to the machine's state-notify characteristic and invokes
        ``callback`` with a full :class:`NespressoDevice` on each update. Falls
        back to nothing if the family does not support notifications; callers
        should keep polling in that case. Runs until ``stop_event`` is set or the
        machine disconnects.

        Note: the machine allows a single BLE client, so while streaming the
        Nespresso mobile app cannot connect.
        """
        stop_event = stop_event or asyncio.Event()
        loop = asyncio.get_running_loop()
        disconnect_future: asyncio.Future[bool] = loop.create_future()
        client = await self._connect(ble_device, disconnect_future)
        try:
            family = self._resolve_family(client)
            if self.auth_key:
                await self._authenticate(client, family)
            device = await self._read(client, ble_device, family)
            callback(device)
            unsubscribe = await self._subscribe(client, family, callback, device)
            async with interrupt(
                disconnect_future,
                DisconnectedError,
                f"Disconnected from {client.address}",
            ):
                await stop_event.wait()
            if unsubscribe is not None:
                await unsubscribe()
        finally:
            await client.disconnect()

    def supports_push(self, service_uuids: list[str]) -> bool:
        """Return True if the machine can push state via notifications.

        ``service_uuids`` are the advertised service UUIDs known to the caller
        (e.g. from Bluetooth discovery). All supported families support
        notifications.
        """
        return family_from_service_uuids(service_uuids) in (
            MachineFamily.VMINI,
            MachineFamily.VERTUO_NEXT,
            MachineFamily.BARISTA,
        )

    # -- internal --------------------------------------------------------

    def _on_disconnect(
        self, disconnect_future: asyncio.Future[bool], _client: BleakClient
    ) -> None:
        if not disconnect_future.done():
            disconnect_future.set_result(True)

    async def _connect(
        self, ble_device: BLEDevice, disconnect_future: asyncio.Future[bool]
    ) -> BleakClient:
        """Establish a connection, clearing a stale bond if one blocks it."""
        try:
            return await establish_connection(
                self.client_class,
                ble_device,
                ble_device.address,
                disconnected_callback=partial(self._on_disconnect, disconnect_future),
            )
        except BleakError as err:
            if not _is_auth_error(err):
                raise
            # A stale/half BlueZ bond from a previous attempt blocks the
            # connection. Remove it and retry once.
            self.logger.warning(
                "Connection authentication failed for %s; clearing stale bond",
                ble_device.address,
            )
            await self._unpair(ble_device)
            return await establish_connection(
                self.client_class,
                ble_device,
                ble_device.address,
                disconnected_callback=partial(self._on_disconnect, disconnect_future),
            )

    async def _unpair(self, ble_device: BLEDevice) -> None:
        """Remove any existing bond for the device."""
        try:
            await self.client_class(ble_device).unpair()
        except Exception as err:  # noqa: BLE001  # pylint: disable=broad-exception-caught
            self.logger.debug("Unpair failed for %s: %s", ble_device.address, err)

    async def _update_device(self, ble_device: BLEDevice) -> NespressoDevice:
        loop = asyncio.get_running_loop()
        disconnect_future: asyncio.Future[bool] = loop.create_future()
        client = await self._connect(ble_device, disconnect_future)
        try:
            async with (
                interrupt(
                    disconnect_future,
                    DisconnectedError,
                    f"Disconnected from {client.address}",
                ),
                asyncio.timeout(UPDATE_TIMEOUT),
            ):
                family = self._resolve_family(client)
                if self.auth_key:
                    await self._authenticate(client, family)
                return await self._read(client, ble_device, family)
        finally:
            await client.disconnect()

    def _resolve_family(self, client: BleakClient) -> MachineFamily:
        """Determine the family from the connected GATT services.

        Connected services are authoritative: unlike the advertisement, they are
        always available once connected and survive routing through a proxy.
        """
        service_uuids = [service.uuid for service in client.services]
        family = family_from_service_uuids(service_uuids)
        self.logger.debug(
            "Resolved family %s from connected services: %s", family, service_uuids
        )
        return family

    async def _authenticate(self, client: BleakClient, family: MachineFamily) -> None:
        if self.auth_key is None:
            self.logger.debug("No auth key set; skipping authentication")
            return
        if family is MachineFamily.VMINI:
            token = self.auth_key.encode("utf-8").ljust(VMINI_TOKEN_LENGTH, b"\x00")
            # The token characteristic is protected; the write triggers the
            # backend to encrypt the link on demand. If the link cannot be
            # encrypted the write raises an authentication error, which the
            # connection layer recovers from by clearing any stale bond.
            try:
                await client.write_gatt_char(
                    VMINI_CHAR_MACHINE_TOKEN, token, response=True
                )
            except BleakError as err:
                msg = f"VMini authentication failed: {err}"
                raise AuthError(msg) from err
            self.logger.debug("Wrote VMini machine token (%d bytes)", len(token))

    async def _read(
        self, client: BleakClient, ble_device: BLEDevice, family: MachineFamily
    ) -> NespressoDevice:
        if family is MachineFamily.VMINI:
            device = await self._read_vmini(client, ble_device)
        elif family is MachineFamily.VERTUO_NEXT:
            device = await self._read_vertuo_next(client, ble_device)
        elif family is MachineFamily.BARISTA:
            device = await self._read_barista(client, ble_device)
        else:
            msg = f"Unsupported machine family: {family}"
            raise UnsupportedDeviceError(msg)
        self.logger.debug("Parsed device: %s", device)
        return device

    async def _read_char(self, client: BleakClient, uuid: str) -> bytes | None:
        try:
            data = bytes(await client.read_gatt_char(uuid))
        except BleakError as err:
            self.logger.debug("Could not read %s: %s", uuid, err)
            return None
        self.logger.debug("Read %s -> %s", uuid, data.hex())
        return data

    async def _read_vmini(
        self, client: BleakClient, ble_device: BLEDevice
    ) -> NespressoDevice:
        device = NespressoDevice(
            address=ble_device.address,
            name=ble_device.name or "",
            family=MachineFamily.VMINI,
        )
        if (serial := await self._read_char(client, VMINI_CHAR_SERIAL)) is not None:
            device.serial = parsing.decode_ble_string(serial)
        pairing = await self._read_char(client, VMINI_CHAR_PAIRING)
        if pairing:
            device.pairing_status = pairing_status(pairing[0])
        if (wifi := await self._read_char(client, VMINI_CHAR_WIFI_MAC)) is not None:
            device.wifi_mac = parsing.parse_mac(wifi) or parsing.decode_ble_string(wifi)
        if (iot := await self._read_char(client, VMINI_CHAR_IOT_MARKET)) is not None:
            device.iot_market = parsing.decode_ble_string(iot)
        assets = await self._read_char(client, VMINI_CHAR_ASSET_VERSIONS)
        if assets is not None:
            device.firmware_version = _firmware_from_assets(
                parsing.decode_ble_string(assets)
            )
        schema = await self._read_char(client, VMINI_CHAR_SHADOW_HEADER)
        values = await self._read_char(client, VMINI_CHAR_SHADOW_UPDATE)
        if schema is not None and values is not None:
            shadow = parsing.parse_shadow(schema, values)
            self.logger.debug(
                "VMini shadow schema=%r values=%r parsed=%s",
                parsing.decode_ble_string(schema),
                parsing.decode_ble_string(values),
                shadow,
            )
            _apply_vmini_shadow(device, shadow)
        else:
            self.logger.debug(
                "VMini shadow unavailable (schema=%s, values=%s)",
                schema is not None,
                values is not None,
            )
        return device

    async def _read_vertuo_next(
        self, client: BleakClient, ble_device: BLEDevice
    ) -> NespressoDevice:
        device = NespressoDevice(
            address=ble_device.address,
            name=ble_device.name or "",
            family=MachineFamily.VERTUO_NEXT,
        )
        await self._read_device_info(client, device)
        if (serial := await self._read_char(client, VERTUO_CHAR_SERIAL)) is not None:
            device.serial = parsing.decode_ble_string(serial)
        if (info := await self._read_char(client, VERTUO_CHAR_INFO)) is not None:
            parsed = parsing.parse_vertuo_machine_info(info)
            device.hardware_version = parsed["hardware_version"]
            device.firmware_version = parsed["firmware_version"]
        if (state := await self._read_char(client, VERTUO_CHAR_STATE)) is not None:
            vn = parsing.VertuoNextState(state)
            device.status = vn.status
            device.error = vn.error_present
            device.descaling_needed = vn.descaling_needed
            device.cleaning_needed = vn.cleaning_needed
            device.water_tank_empty = vn.water_tank_empty
            device.capsule_container_full = vn.capsule_container_full
            device.brewing_unit_closed = vn.brewing_unit_closed
        wh = await self._read_char(client, VERTUO_CHAR_WATER_HARDNESS)
        if wh is not None:
            device.water_hardness = parsing.parse_water_hardness(wh)
        if (caps := await self._read_char(client, VERTUO_CHAR_NBCAPS)) is not None:
            device.capsule_count = parsing.parse_capsule_count(caps)
        return device

    async def _read_barista(
        self, client: BleakClient, ble_device: BLEDevice
    ) -> NespressoDevice:
        device = NespressoDevice(
            address=ble_device.address,
            name=ble_device.name or "",
            family=MachineFamily.BARISTA,
        )
        await self._read_device_info(client, device)
        if (serial := await self._read_char(client, BARISTA_CHAR_SERIAL)) is not None:
            device.serial = parsing.decode_ble_string(serial)
        if (info := await self._read_char(client, BARISTA_CHAR_INFO)) is not None:
            parsed = parsing.parse_barista_machine_info(info)
            device.hardware_version = parsed["hardware_version"]
            device.firmware_version = parsed["firmware_version"]
        if (state := await self._read_char(client, BARISTA_CHAR_STATE)) is not None:
            b = parsing.BaristaState(state)
            device.status = b.status
            device.error = b.error_present
        return device

    async def _read_device_info(
        self, client: BleakClient, device: NespressoDevice
    ) -> None:
        if (mfr := await self._read_char(client, CHAR_MANUFACTURER)) is not None:
            device.manufacturer = parsing.decode_ble_string(mfr)
        if (model := await self._read_char(client, CHAR_MODEL_NUMBER)) is not None:
            device.model_number = parsing.decode_ble_string(model)
        if (fw := await self._read_char(client, CHAR_FIRMWARE_REV)) is not None:
            fw_str = parsing.decode_ble_string(fw)
            if fw_str:
                device.firmware_version = fw_str

    async def _subscribe(
        self,
        client: BleakClient,
        family: MachineFamily,
        callback: UpdateCallback,
        device: NespressoDevice,
    ) -> Callable[[], Awaitable[None]] | None:
        """Subscribe to the state-notify characteristic. Returns unsubscribe."""
        if family is MachineFamily.VMINI:
            schema = await self._read_char(client, VMINI_CHAR_SHADOW_HEADER)
            if schema is None:
                return None

            def _handle(_c: object, data: bytearray) -> None:
                shadow = parsing.parse_shadow(schema, bytes(data))
                if shadow:
                    _apply_vmini_shadow(device, shadow)
                    callback(device)

            await client.start_notify(VMINI_CHAR_SHADOW_UPDATE, _handle)

            async def _unsub() -> None:
                with contextlib.suppress(BleakError):
                    await client.stop_notify(VMINI_CHAR_SHADOW_UPDATE)

            return _unsub

        state_uuid = {
            MachineFamily.VERTUO_NEXT: VERTUO_CHAR_STATE,
            MachineFamily.BARISTA: BARISTA_CHAR_STATE,
        }.get(family)
        if state_uuid is None:
            return None

        def _handle_state(_c: object, data: bytearray) -> None:
            if family is MachineFamily.VERTUO_NEXT:
                vn = parsing.VertuoNextState(bytes(data))
                device.status = vn.status
                device.error = vn.error_present
                device.descaling_needed = vn.descaling_needed
                device.cleaning_needed = vn.cleaning_needed
                device.water_tank_empty = vn.water_tank_empty
                device.capsule_container_full = vn.capsule_container_full
                device.brewing_unit_closed = vn.brewing_unit_closed
            else:
                b = parsing.BaristaState(bytes(data))
                device.status = b.status
                device.error = b.error_present
            callback(device)

        await client.start_notify(state_uuid, _handle_state)

        async def _unsub_state() -> None:
            with contextlib.suppress(BleakError):
                await client.stop_notify(state_uuid)

        return _unsub_state


_AUTH_ERROR_MARKERS = (
    "authentication",
    "not paired",
    "encryption",
)


def _is_auth_error(err: BaseException) -> bool:
    """Return True if the error indicates a bonding/encryption problem."""
    text = str(err).lower()
    return any(marker in text for marker in _AUTH_ERROR_MARKERS)


def _firmware_from_assets(assets: str) -> str | None:
    for entry in assets.split(";"):
        parts = entry.split(",")
        if parts and parts[0] == "fmw-main" and len(parts) >= 2:
            return parts[1]
    return None


def _apply_vmini_shadow(
    device: NespressoDevice, shadow: dict[str, str | int | bool]
) -> None:
    device.extra.update(shadow)
    device.status = vmini_status_from_shadow(shadow)
    if isinstance((err := shadow.get("errorCode")), str):
        device.error_code = err
        device.error = err.strip().lower() != "no error"
    if isinstance((desc := shadow.get("descalingAlert")), bool):
        device.descaling_needed = desc
    if isinstance((wh := shadow.get("waterHardness")), int):
        try:
            device.water_hardness = WaterHardness(wh)
        except ValueError:
            device.water_hardness = None
