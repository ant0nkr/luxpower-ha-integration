# Contributing

Thank you for contributing to the **LuxPower Modbus** integration for Home Assistant!

## Development Setup

1. Clone the repository and create a branch for your changes:
   ```bash
   git clone https://github.com/ant0nkr/luxpower-ha-integration.git
   cd luxpower-ha-integration
   git checkout -b my-feature-or-fix
   ```
2. Set up a Python 3.13 virtual environment and install dependencies:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   pip install -r requirements-dev.txt
   ```

## Running Tests

Run the full test suite from the repository root:

```bash
PYTHONPATH=. pytest -v
```

`pytest.ini` is configured with `testpaths = tests` and `asyncio_mode = auto`.

## Register & Entity Guidelines

* **Verify register definitions first:** Read [docs/protocol-registers.md](docs/protocol-registers.md) before modifying register ranges, multipliers, units, or signedness.
* **Tests enforce register invariants:** `tests/test_register_ranges.py` and `tests/test_observed_registers.py` pin verified register ranges and signedness rules (for example, any signed hold register must declare a negative minimum).
* **Do not guess unresolved registers:** Registers flagged as unresolved in [docs/protocol-registers.md](docs/protocol-registers.md) should only be changed with evidence from a protocol document or a real-hardware register dump.
* **Keep documentation in sync:** If you add or modify entity descriptions in `custom_components/lxp_modbus/entity_descriptions/` or configuration options in `const.py` / `config_flow.py`, update [ENTITIES.md](ENTITIES.md) and [README.md](README.md) accordingly.

## Pull Request Checks

Before opening a pull request, ensure:

* `PYTHONPATH=. pytest -v` passes locally.
* Home Assistant `hassfest` and HACS validation workflows pass (run automatically via `.github/workflows/`).
* Any new user-facing features or bug fixes are noted under `[Unreleased]` in [CHANGELOG.md](CHANGELOG.md).
