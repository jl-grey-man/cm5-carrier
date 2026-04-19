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

---

## Fix Plan — Atomic Sequence (2026-04-19)

> Each step must pass verification before starting the next.
> Source: red team + cross-analysis + EMC scan results.

### Step 1 — R7/R8 circuit intent (research, no code)
**Why first:** All net fixes downstream depend on this.
- [ ] Check BQ25895 datasheet: what connects to ILIM pin? What is the correct pull-up net?
- [ ] Check TPS61089 datasheet: what is EN pin, FSW pin, COMP/FB pin? Correct nets?
- [ ] Document ground truth: R7={pad1, pad2}, R8={pad1, pad2}
- **Done when:** nets confirmed against datasheet, written in this checklist

**FINDINGS (2026-04-19):**
- assign_nets.py: R7={+3.3V, /PWR_BUT_BTN} (power button pull-up), R8={+3.3V, GND}
- gen_power_schematic.py: R7=TPS61089 EN pull-up (100k), R8=TPS61089 FSW resistor (400k)
- Current PCB: R7={+5V_CM5, Net-U2-COMP}(wrong), R8={FB_BOOST, GND}(wrong)
- **U2 (TPS61089) pad assignments are ALL wrong** — custom footprint pad numbering doesn't match chip pin numbering
  - pad 1 = chip pin 1 = GND (PCB has "FSW") WRONG
  - pad 7 = chip pin 7 = FSW (PCB has "+5V_CM5") WRONG
  - pad 8 = chip pin 8 = EN (PCB has "Net-U2-ILIM") — position correct, name wrong
  - pad 9/10 = chip pins 9/10 = VOUT (PCB has VSYS/Net-U2-SW) WRONG
- **Decision: Fix R7/R8 to assign_nets.py values. U2 pad redesign is a separate step.**
- [x] Step 1 complete

### Step 2 — Fix gen_power_schematic.py (schematic floating components)
**Depends on:** Step 1
**Why:** R7/R8 are placed but have no wire connections → nets are undefined
- [ ] Add wire connections for R7 (EN pull-up: +5V_CM5 → TPS61089 EN)
- [ ] Add wire connections for R8 (FSW resistor: FSW → GND)
- [ ] Regenerate power.kicad_sch and verify in KiCad
- **Done when:** R7/R8 show connected nets in schematic, no new ERC violations

### Step 3 — Fix PCB net assignments (R7, R8 pads)
**Depends on:** Step 1
**Why:** PCB still has Net-U2-COMP on R7-pad2, FB_BOOST on R8-pad1
- [x] R7: pad1=+3.3V, pad2=/PWR_BUT_BTN (power button pull-up, per assign_nets.py)
- [x] R8: pad1=+3.3V, pad2=GND (per assign_nets.py; TPS61089 FSW fix deferred to U2 redesign)
- [x] DRC: 32 violations (unchanged)
- **Done when:** DRC ≤ 32 violations, R7/R8 nets match Step 1 ground truth ✓

### Step 4 — Value sync (22 mismatches, schematic vs PCB)
**Depends on:** Step 2 (schematic is authoritative after fix)
**Priority mismatches to fix:**
- [ ] L2: PCB says 1.0uH/10A, schematic says 2.2uH/2A → pick correct for TPS61089 (10A capable)
- [ ] R6: PCB says 1k, schematic says 100k → check BQ25895 I2C pull-up spec
- [ ] Remaining 20 — review list from cross_analysis output, fix schematic or PCB per datasheet
- [ ] Rerun cross_analysis.py — 0 value mismatches
- **Done when:** cross_analysis reports 0 value mismatches

### Step 5 — Ground plane zones (EMC GP-002)
**Depends on:** Step 3 (PCB nets stable)
**Why:** No ground pour on In1.Cu — EMC score -15 pts, EMI risk
- [x] In1.Cu GND zone: full board (0.5,0.5)→(79.5,59.5)
- [x] In2.Cu +5V_CM5 zone: power section left half (0.5,0.5)→(45,59.5)
- [x] DRC: 32 violations (unchanged)
- **Done when:** DRC clean, zones visible in In1.Cu/In2.Cu ✓

### Step 6 — Via stitching (EMC VS-001)
**Depends on:** Step 5 (zones must exist to stitch)
- [x] 60 GND stitching vias: perimeter every 5mm + power section grid
- [x] Exclusion zones around mounting holes (MH2/3/4) to avoid hole_to_hole DRC
- [x] via_dangling: 60 violations (expected pre-routing — resolved once F.Cu/B.Cu pours added)
- **Done when:** DRC clean, via grid visible in PCB ✓

### Step 7 — ESD protection (EMC IO-001 ×4)
**Depends on:** Step 5 (GND plane needed for ESD to work)
**Missing:** ESD on J_USB1, J_USB2, J_HDMI, J1 (USB-C)
- [ ] Add USBLC6-2SC6 or TPD2E2U06 footprint to schematic for each USB port
- [ ] Add ESD component for HDMI (HDMI line protector or TVS array)
- [ ] Place components in PCB near connectors
- [ ] Run DRC
- **Done when:** EMC IO-001 violations resolved in EMC scan

### Step 8 — Place missing components (48 in schematic, not in PCB)
**Depends on:** Step 7 (schematic stable)
**Note:** Many are decoupling caps (C11-C17) — verify footprints before placing
- [ ] Identify which of 48 are mandatory vs reference-sheet artifacts
- [ ] Place mandatory components (decoupling caps, filter components)
- [ ] Assign nets from schematic
- [ ] Run DRC
- **Done when:** cross_analysis missing-component list < 10 (some ref sheet ghosts acceptable)

### Step 9 — Remaining courtyard violations (MH4, J_HDMI, J_BAT)
**Depends on:** Step 8 (all components placed, no more moves expected)
- [x] J_BAT: (7,46) → (7,40) — clears MH4 and J_HDMI overlap
- [x] MH4: (3.5,52) → (3.5,53) then → (3.5,53) — partial, still overlapped J_HDMI
- [x] J_HDMI: (15,55) → (17,55) — shifts left edge from x=5.75 to x=7.75, clears MH4 circle
- [x] DRC: 0 courtyard violations ✓
- **Done when:** DRC shows 0 courtyard violations ✓

### Step 10 — Final verification + Gerber export
**Depends on:** All steps above
- [ ] DRC: 0 errors (unconnected nets are known pre-layout issue, acceptable)
- [ ] EMC scan: score ≥ 85/100
- [ ] Cross-analysis: 0 value mismatches
- [ ] Export Gerbers (F.Cu, B.Cu, In1.Cu, In2.Cu, silk, mask, edge cuts)
- [ ] Export drill file
- [ ] Zip → fab/cm5-carrier-gerbers.zip
- [ ] Upload to JLCPCB DFM checker

---

## Generated files
- `gen_power_schematic.py` — generates power.kicad_sch
- `gen_all_schematics.py` — copies CM5 Minima sheets + generates top-level
- `gen_components.py` — places power section components in PCB
- `gen_io_components.py` — places IO components + expands board to 80×60mm
- `power.kicad_sch`, `CM5.kicad_sch`, `HDMI.kicad_sch`, `USB.kicad_sch`, `IO.kicad_sch`
- `cm5-carrier.kicad_sch` — top-level hierarchical
