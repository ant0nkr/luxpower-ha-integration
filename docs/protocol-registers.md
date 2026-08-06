# Register documentation status

Entity ranges, units and multipliers in `entity_descriptions/` are only as good as
the source they came from. This file records which registers are backed by a
published protocol document, which are not, and what is still unresolved, so nobody
has to re-derive it.

## Primary source

`EG4-18KPV-12LV-Modbus-Protocol.pdf` — mirrored at
<https://www.dth.net/solar/luxpower/modbus/>

It covers **hold registers up to 198**. Registers above that (including everything
in the "unresolved" section below) are not in it. LuxPower and EG4 share the
protocol, but this document is for one model family, so a range that contradicts
observed hardware is not automatically wrong — record the evidence either way.

## Verified against the document

These are pinned by `tests/test_register_ranges.py`. Changing one fails the suite.

| Reg | Name | Unit | Range (raw) |
|-----|------|------|-------------|
| 160 | ACChgStartSOC | % | 0–90 |
| 161 | ACChgEndSOC | % | 20–100 |
| 162 | BatLowVoltage | 0.1 V | 400–500 |
| 163 | BatLowBackVoltage | 0.1 V | 420–520 |
| 164 | BatLowSOC | % | 0–90 |
| 165 | BatLowBackSOC | % | 20–100 |
| 166 | BatLowtoUtilityVoltage | 0.1 V | 444–514 |
| 167 | BatLowtoUtilitySOC | % | 0–100 |
| 168 | ACChargeBatCurrent | A | 0–140 |
| 169 | OngridEOD_Voltage | 0.1 V | 400–560 |
| 171 | SOCCurve_BatVolt1 | 0.1 V | 400–600 |
| 172 | SOCCurve_BatVolt2 | 0.1 V | 400–600 |

Also relevant: **register 121 `BusVoltHighEE`, unit 0.1 V, range 4500–5500.** This
is the document's bus-voltage-high setting, and it is the main evidence bearing on
register 260 below.

### Known divergences

Both are listed in `KNOWN_DIVERGENCES` in the test:

- **161 `AC Charge End SOC`** — description allows 0, document says 20. Pre-existing;
  not confirmed against hardware.
- **165 `Battery Low SOC Recovery`** — floor lowered to 0 because hardware reports 0
  when the feature is not configured, so the reported value could not be written
  back. The document says 20–100.

## Verified against a live register dump

A full poll from a real inverter (hold 0–374 and 500–624, decoded from the debug
frames) settled three things. Pinned by `tests/test_observed_registers.py`.

| Reg | Finding |
|-----|---------|
| 106 | `Lead-Acid Discharge Temp Low Limit` reads raw **65336**. The declared minimum is −40 °C, so the register is signed: 65336 → −200 → **−20.0 °C**. It had no signed conversion and displayed **6533.6 °C**. Fixed. |
| 201 | `Charge First End Voltage` reads raw **595** (59.5 V), above the documented 590 ceiling. Maximum raised to 59.5 so the value the hardware holds can be written back. |
| 75 | `Charge First SOC Limit` reads **101**, above the documented 100. Maximum raised to 101. |

The dump also showed **`0xFFFF` only in input registers 629 and 631 — never in a
hold register.** That matters for the unimplemented-register check in `number.py`:
it only ever applies to unsigned hold registers, so excluding signed ones costs
nothing while avoiding a real error. Two hold entities are signed (119 `External CT
Power Offset`, 117 `Start Charge P_import Threshold`, both min −32768), where
`0xFFFF` is an ordinary −1.

`test_signed_registers_declare_a_negative_minimum` enforces the invariant this
relies on: any description converting to signed must declare a negative minimum.

## Reading 0 is not an error

Many of these settings read `0` on real hardware when the feature is not configured,
even where the documented minimum is well above 0. Values are therefore reported
as-is; only the unimplemented-register sentinel (`0xFFFF`, which produced readings
like 6553.5 V) is hidden. See `UNIMPLEMENTED_REGISTER_VALUE` and `number.py`.

A consequence worth knowing: a register reading 0 with a documented floor of 42.0
displays 0 but cannot be written back as 0, because the floor is real. That is
correct behaviour, not a bug.

## Unresolved

Not covered by the document. Each has a description that contradicts its own
register comment. **Do not change these on inference alone** — they are alarm and
cut-off settings, and a wrong scale writes a wrong safety threshold. What is needed
is either a protocol document covering registers above 198, or a reading from a
device where the setting is actually configured.

### 252 `NEC 120% Bus Bar Limit` — unit and range disagree

```
hold_registers.py:  # NEC 120% Bus Bar Limit (Unit: W, Range: 0-65535)
number_types.py:    "unit": "A", "min": 5, "max": 80
```

Watts vs amps, and 0–65535 vs 5–80. To settle: read the value the inverter shows
for this setting in the LuxPower app or LCD and compare with the raw register.

### 260 `BUS Overvoltage Alarm Point` — probable 10× scale error

```
hold_registers.py:  # Bus voltage high limit setting (Unit: 0.1V, Range: 0-8000)
number_types.py:    "multiplier": 1, "min": 550, "max": 595
```

The register comment says 0.1 V, and the document's equivalent (register 121) is
0.1 V with a raw range of 4500–5500. That suggests `multiplier` should be 10 and the
range should come from the comment. But the declared 550–595 with multiplier 1 looks
like a battery voltage range (55.0–59.5 V) pasted into a DC bus setting, so which
half is wrong is not clear.

To settle: read raw register 260 on a device where the alarm point is configured. A
raw value near 5000 confirms 0.1 V; near 580 confirms whole volts.

### 261 `Discharge Recovery` — one of two entities may not exist

```
hold_registers.py:  # Discharge recovery setting (Unit: %, Range: 0-100)
```

The repository exposes two entities from this register: `Discharge Recovery SOC
Threshold` (low byte) and `Discharge Recovery Volt Threshold` (high byte, whose own
description admits `"max": 20.0, # Assuming a reasonable max`). If the register is a
single 0–100 % value, the high-byte entity is meaningless.

It is *not* dangerous: both compose functions preserve the other byte
(`orig & 0xFF00` / `orig & 0x00FF`), so the two entities cannot corrupt each other.
The risk is a misleading control, not data loss.

To settle: set the discharge recovery value in the app and read whether the change
lands in the low byte, the high byte, or the whole register.
