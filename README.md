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
