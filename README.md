# Python: Nespresso BLE

[![GitHub Release][releases-shield]][releases]
[![Python Versions][python-versions-shield]][pypi]
![Project Stage][project-stage-shield]
![Project Maintenance][maintenance-shield]
[![License][license-shield]](LICENSE.md)

[![Build Status][build-shield]][build]
[![Code Coverage][codecov-shield]][codecov]

Asynchronous Python client for controlling and reading Nespresso coffee
machines over Bluetooth Low Energy.

## About

This package allows you to control and read Nespresso coffee machines over
Bluetooth Low Energy.

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

## Changelog & Releases

This repository keeps a change log using [GitHub's releases][releases]
functionality. The format of the log is based on
[Keep a Changelog][keepchangelog].

Releases are based on [Semantic Versioning][semver], and use the format
of ``MAJOR.MINOR.PATCH``. In a nutshell, the version will be incremented
based on the following:

- ``MAJOR``: Incompatible or major changes.
- ``MINOR``: Backwards-compatible new features and enhancements.
- ``PATCH``: Backwards-compatible bugfixes and package updates.

## Contributing

This is an active open-source project. We are always open to people who want to
use the code or contribute to it.

We've set up a separate document for our
[contribution guidelines](.github/CONTRIBUTING.md).

Thank you for being involved! :heart_eyes:

## Setting up development environment

This Python project is fully managed using the [uv][uv] dependency manager. But also relies on the use of NodeJS for certain checks during development.

You need at least:

- Python 3.13+
- [uv][uv-install]
- NodeJS 12+ (including NPM)

To install all packages, including all development requirements:

```bash
npm install
uv sync --all-groups
```

As this repository uses the [prek][prek] framework, all changes
are linted and tested with each commit. You can run all checks and tests
manually, using the following command:

```bash
uv run prek run --all-files
```

To run just the Python tests:

```bash
uv run pytest
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

## Authors & contributors

The content is by [Joost Lekkerkerker][joostlek].

For a full list of all authors and contributors,
check [the contributor's page][contributors].

## License

MIT License

Copyright (c) 2026 Joost Lekkerkerker

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

[build-shield]: https://github.com/joostlek/nespresso-ble/actions/workflows/tests.yaml/badge.svg
[build]: https://github.com/joostlek/nespresso-ble/actions
[codecov-shield]: https://codecov.io/gh/joostlek/nespresso-ble/branch/master/graph/badge.svg
[codecov]: https://codecov.io/gh/joostlek/nespresso-ble
[commits-shield]: https://img.shields.io/github/commit-activity/y/joostlek/nespresso-ble.svg
[commits]: https://github.com/joostlek/nespresso-ble/commits/master
[contributors]: https://github.com/joostlek/nespresso-ble/graphs/contributors
[joostlek]: https://github.com/joostlek
[keepchangelog]: http://keepachangelog.com/en/1.0.0/
[license-shield]: https://img.shields.io/github/license/joostlek/nespresso-ble.svg
[maintenance-shield]: https://img.shields.io/maintenance/yes/2026.svg
[poetry-install]: https://python-poetry.org/docs/#installation
[poetry]: https://python-poetry.org
[prek]: https://prek.j178.dev/
[uv]: https://docs.astral.sh/uv/
[uv-install]: https://docs.astral.sh/uv/getting-started/installation/
[project-stage-shield]: https://img.shields.io/badge/project%20stage-stable-green.svg
[python-versions-shield]: https://img.shields.io/pypi/pyversions/nespresso-ble
[releases-shield]: https://img.shields.io/github/release/joostlek/nespresso-ble.svg
[releases]: https://github.com/joostlek/nespresso-ble/releases
[semver]: http://semver.org/spec/v2.0.0.html
[pypi]: https://pypi.org/project/nespresso-ble/
