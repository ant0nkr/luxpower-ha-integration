# Changelog

All notable releases of this project are documented in this file. Full release notes are also available on [GitHub Releases](https://github.com/ant0nkr/luxpower-ha-integration/releases).

## [1.1.2] - 2026-11-11

### Added
* Added `Inverter Time` sensor from hold registers `12–14` (disabled by default) (#182).
* Added AFCI diagnostics and dongle recovery documentation (#186).
* Added diagnostic `Data Read At` sensors for input and battery registers (#181).
* Added local brand assets (`icon.png`, `icon@2x.png`) (#179).

### Fixed
* Kept the settings pass active when a connection fails (#188).
* Preserved poll cadence after writes (#185).
* Fixed parsing of protocol 1 byte-count responses (#184).

## [1.1.1] - 2026-10-14

### Added
* Added `AC CT Direction` switch (#159) and `Grid CT Connection` switch (#160).

### Fixed
* Allowed `On-Grid Cut-Off SOC` of `0` and corrected `Quick Charge Time` range (#176).
* Fixed replies landing one request late when the dongle pushes frames (#175).
* Confirmed writes on the write connection instead of triggering a full poll (#155).
* Removed empty sub-devices left behind by renamed device groups (#153).

## [1.1.0-beta.1] - 2026-08-06

### Added
* Added `Grid Export` switch.

### Changed
* Stopped re-reading settings and empty battery blocks on every poll (#151).

### Fixed
* Improved write rejection handling and register `22` behavior (#152).

## [1.0.0] - 2026-08-06

### Added
* Major architecture overhaul and code refactoring (#113).
* Added **Battery BMS monitoring** (register range `5000+`) with `none`, `auto`, and explicit serial number modes (#114).
* Added `Grid Connected` binary sensor (#121, #125) and PV combined / per-string current sensors (#118).
* Added AC couple power register `153` (#130).

### Changed
* Aligned switch entity names and device groups with the LuxPower app (#124).

### Fixed
* Preserved unsigned 16-bit values when writing hold registers (#135).
* Fixed `Reboot Inverter` button lambda (#127), `Charge First SOC Limit` byte order (#123), battery register reading (#126), and HA compatibility / write path (#150).

## [0.2.4] - 2025-12-29

### Added
* Added `Grid Flow` sensor (#100) and suggested display precision on sensor types (#96).

### Changed
* Removed the `Settings & Schedules` device group for cleaner entity organization.
* Flipped `Battery Flow` sign convention (#99).

## [0.2.3] - 2025-12-06

### Added
* Added `Standby` state to `SENSOR_TYPES`.

### Changed
* Moved `Battery Flow` to the `Battery` device group.

### Fixed
* Fixed `Load Percentage` calculation when the inverter is in Standby mode.

## [0.2.2] - 2025-12-01

### Added
* Added `Energy Flow` sensor (#93) and cell difference / battery calibration entities (#89, #90).

### Changed
* Allowed `On-Grid Cut-Off SOC` control up to 100% on non-primary inverters (#92).

## [0.2.1] - 2025-11-26

### Added
* Added working mode select for standby mode (#79) and forced discharge schedule times (#77).
* Added signed value `extract` and `compose` handling in `ModbusBridgeNumber` (#82).

### Fixed
* Improved message decoding, write checks, and quick charge time handling (#67, #72, #73, #75).

## [0.2.0] - 2025-10-02

### Added
* Introduced **Device Grouping** to organize entities into logical sub-devices (`PV`, `Grid`, `EPS`, `Generator`, `Battery`).
* Added split-phase information for US/BR inverters (#55) and updated battery status / BMS data decoding (#54).

### Fixed
* Fixed `EPS Energy Total L2N` extract formula.

## [0.1.10] - 2025-09-26

### Changed
* Updated register references and documentation.

## [0.1.9] - 2025-09-25

### Fixed
* Fixed Function 4 / Function 5 handling and register definitions (#48).
* Fixed maximum percentage value in `NUMBER_TYPES` to `100`.
* Reduced redundant logging for input/hold poll failures and sanity checks.

## [0.1.8] - 2025-08-31

### Added
* Added **Connection Retry Attempts** configuration option with `1–10` validation and reconnection logic (#44).
* Added `AC Charge End SOC` register (#43) and additional missing sensors.

### Fixed
* Standardized unit casing for reactive power and `AC Charge End SOC`.

## [0.1.7] - 2025-08-23

### Added
* Added **Register Block Size** configuration option (`125` / `40`) (#39) and missing sensors.

## [0.1.6] - 2025-08-16

### Changed
* Changed protocol version to `1` and increased default polling interval to `60` seconds.
* Added automated `pytest` CI workflow.

### Fixed
* Fixed CRC calculation, active warning code handling, and `modbus_client` issues.

## [0.1.6-beta] - 2025-08-02

### Fixed
* Handled inverters returning less data than expected and fixed `get_highest_set_bit` for non-integer or zero inputs (#30).

## [0.1.5] - 2025-07-31

### Added
* Added **Read-Only Mode** (#23).
* Added `master_only` flag and disabled slave inverter controls by default (#25, #26).

### Fixed
* Fixed warning/error code extraction with `get_highest_set_bit` (#27).

## [0.1.4] - 2025-07-28

### Added
* Added `Force Charge to Target SOC` automation blueprint.
* Added missing sensors and `state_class` definitions (#18).

## [0.1.3] - 2025-07-28

### Added
* Added new input and hold registers, including `Generator` start/end time schedules (#13, #15).
* Added composed phase logic (#12) and optimized Modbus register reads (#14).
* Restored AC Charge Start/End times after running the force-charge script blueprint (#17).

## [0.1.2] - 2025-07-19

### Fixed
* Updated `manifest.json` version to match the latest release.

## [0.1.1] - 2025-07-19

### Added
* Initial Home Assistant custom component implementation with `Force Charge for a Specific Duration` blueprint (#3), Total PV Power (#4), HACS (`hacs.json`, `validate.yml`), and `hassfest` support.
