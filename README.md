# nespresso-ble

Asynchronous Python client for controlling and reading Nespresso coffee
machines over Bluetooth Low Energy.

Supports the three Nespresso Bluetooth hardware families:

- **Barista** (Original line)
- **Vertuo Next** (Venus line)
- **Vertuo Mini** (VMini)

The machine family is detected automatically from the advertised BLE service
UUID. State is exposed through a fully typed `NespressoDevice` model.

## Installation

```bash
pip install nespresso-ble
```

## Usage

```python
import asyncio
import logging

from bleak import BleakScanner

from nespresso_ble import NespressoBluetoothDeviceData, is_supported


async def main() -> None:
    device = await BleakScanner.find_device_by_filter(
        lambda d, adv: is_supported(adv.service_uuids)
    )
    if device is None:
        return

    client = NespressoBluetoothDeviceData(logging.getLogger())

    # One-shot poll.
    machine = await client.update_device(device)
    print(machine.status, machine.water_hardness)

    # Or subscribe to live push updates.
    await client.stream(device, lambda m: print(m.status))


asyncio.run(main())
```

## Development

This project uses [uv](https://docs.astral.sh/uv/).

```bash
uv sync --all-groups
uv run pytest
uv run prek run --all-files
```

## Attribution

This library builds on the reverse engineering work of several projects. Huge
thanks to their authors:

- [renaudallard/homeassistant_nespresso_smart](https://github.com/renaudallard/homeassistant_nespresso_smart)
  — reverse engineered the Nespresso Smart Android app, documenting the VMini
  (Vertuo Mini), Vertuo Next and Barista GATT services, characteristics, state
  encodings and authentication. Its protocol documentation is the basis for the
  parsing in this library.
- [bulldog5046/ha_nespresso_integration](https://github.com/bulldog5046/ha_nespresso_integration)
  — reverse engineered the Original line (Expert/Prodigio) protocol, auth/
  onboarding flow and brew commands via BLE captures.
- [tikismoke/home-assistant-nespressoble](https://github.com/tikismoke/home-assistant-nespressoble)
  and everyone before them who helped decode the Nespresso BLE protocols.
