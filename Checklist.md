# CM5 Carrier Board — Checklist

## Phase 1: Setup & Reference
- [x] Download official RPi CM5 KiCad reference design (CM5 Minima cloned)
- [x] Download CM5 KiCad symbol + footprint library (CM5IO.pretty)
- [x] Verify CM5 pinout against datasheet
- [x] Create KiCad project in `/mnt/storage/pcb/cm5-carrier/`

## Phase 2: Schematic
- [x] CM5 connector + decoupling caps (CM5.kicad_sch — copied from CM5 Minima)
- [x] Power circuit: USB-C → BQ25895RTW charger → LiPo (JST-PH) → TPS61089 boost → 5V/5A
- [x] HDMI output circuit (HDMI.kicad_sch)
- [x] USB-A ports ×2 (USB.kicad_sch)
- [x] GPIO 2×20 header + microSD + buttons (IO.kicad_sch)
- [x] Power LED (IO sheet)
- [x] Reset + power buttons (IO sheet — nRESET, PWR_BUT)
- [x] Top-level hierarchical schematic (cm5-carrier.kicad_sch)
- [ ] ERC clean — currently 379 violations (mostly unconnected pins in ref sheets, acceptable)

## Phase 3: Layout
- [x] Define board outline — 80×60mm (expanded from 65×56 to fit GPIO header)
- [x] Set 4-layer stackup (JLCPCB JLC04161H-7628)
- [x] Place CM5 connector (custom Hirose DF40HC footprint, top center)
- [x] Place power components (BQ25895RTW, TPS61089, passives — left side)
- [x] Place IO components:
  - J_GPIO (70, 4) — 2×20 GPIO header, right side vertical
  - J_HDMI (15, 55) — HDMI-A horizontal, bottom-left edge
  - J_SDCARD (36, 36) — microSD, center
  - J_USB1/2 (34/52, 46.5) — USB-A ×2 horizontal, bottom
  - SW_RST/PWR (58/64, 38) — tactile buttons
- [ ] Assign nets to IO component pads (needs KiCad GUI: Update PCB from Schematic)
  - NOTE: schematics have ref/footprint scrambling from CM5 Minima import — needs cleanup
  - Power section pads have nets (GND, +5V_CM5, VBUS, VSYS, VBATT, I2C0_SDA/SCL)
- [ ] Route USB 3.0 differential pairs (90Ω, ref plane underneath)
- [ ] Route HDMI differential pairs (100Ω)
- [ ] Route remaining signals
- [ ] Ground pour all layers
- [ ] Run DRC — 0 errors

## Phase 4: Fabrication
- [ ] Export Gerbers (4 copper layers + silk + mask + edge cuts)
- [ ] Export drill file
- [ ] Zip and upload to JLCPCB for DFM check
- [ ] Order 5 boards (~$10–15 + shipping)

## Phase 5: Assembly & Test
- [ ] Solder CM5 connector (reflow recommended)
- [ ] Solder BQ25895RTW + TPS61089 + passives
- [ ] Power-on test (check 5V rail before inserting CM5)
- [ ] Insert CM5, boot test
- [ ] Test HDMI, USB, GPIO

## Generated files
- `gen_power_schematic.py` — generates power.kicad_sch
- `gen_all_schematics.py` — copies CM5 Minima sheets + generates top-level
- `gen_components.py` — places power section components in PCB
- `gen_io_components.py` — places IO components + expands board to 80×60mm
- `power.kicad_sch`, `CM5.kicad_sch`, `HDMI.kicad_sch`, `USB.kicad_sch`, `IO.kicad_sch`
- `cm5-carrier.kicad_sch` — top-level hierarchical
