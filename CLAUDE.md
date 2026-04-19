# Rules

## Never break what works
- Run DRC before AND after every schematic/layout change
- Never modify footprints or symbols you weren't asked to touch
- Every design change must leave the project in a DRC-clean state

## Atomic changes only
- One logical change per commit (e.g. "add USB-C power circuit" is one commit)
- If a change touches schematic + layout, both go in one commit
- No "while I'm here" cleanups — note it in Checklist.md instead

## Documentation is not optional
- If you add/change a component or net, update CLAUDE.md in the same commit
- CLAUDE.md is source of truth — if the schematic contradicts it, the schematic is wrong
- New design decision? Document it in the Fragile or Gotchas section

## Don't guess, ask
- Unsure about CM5 pinout → check the official datasheet, not memory
- Ambiguous design requirement → ask before routing

## Task tracking belongs in Checklist.md
- Never put todos or phase status in CLAUDE.md

---

# Project

**Minimal CM5 Carrier Board** — inspired by [timonsku/Minimal-RPi-CM-4-Carrier](https://github.com/timonsku/Minimal-RPi-CM-4-Carrier), ported to Raspberry Pi Compute Module 5.

Goal: smallest possible functional carrier board. Just power, display, USB, and GPIO.

---

# Tools & Commands

```bash
# DRC check
kicad-cli pcb drc --output /tmp/drc.json --format json <file>.kicad_pcb

# Parse DRC results
python3 -c "
import json; d=json.load(open('/tmp/drc.json'))
v=d.get('violations',[])
by_type={}
for x in v: by_type[x['type']]=by_type.get(x['type'],0)+1
for t,c in sorted(by_type.items(),key=lambda x:-x[1]): print(f'{c:4d} {t}')
"

# Export Gerbers
kicad-cli pcb export gerbers --output fab/ \
  --layers "F.Cu,B.Cu,In1.Cu,In2.Cu,F.Silkscreen,B.Silkscreen,F.Mask,B.Mask,Edge.Cuts" \
  <file>.kicad_pcb

# Export drill files
kicad-cli pcb export drill --output fab/ --format excellon --excellon-units mm <file>.kicad_pcb

# Zip for JLCPCB
cd fab && zip cm5-carrier-gerbers.zip *.g* *.drl

# Clear all tracks/vias/zones from PCB file (MUST do before re-running routing scripts)
python3 -c "
with open('cm5-carrier.kicad_pcb') as f: content=f.read()
lines=content.split('\n'); out=[]; depth=0; skip=False
for line in lines:
    stripped=line.lstrip('\t'); tabs=len(line)-len(stripped)
    if tabs==1 and not skip:
        if stripped.startswith('(via') or stripped.startswith('(segment') or stripped.startswith('(zone'):
            skip=True; depth=stripped.count('(')-stripped.count(')'); continue
    if skip:
        depth+=stripped.count('(')-stripped.count(')')
        if depth<=0: skip=False
        continue
    out.append(line)
with open('cm5-carrier.kicad_pcb','w') as f: f.write('\n'.join(out))
"
```

Tool locations: `kicad-cli` at `/usr/local/bin/kicad-cli` (v9.0.2)

## Scripted routing workflow
1. Clear PCB (strip all segments/vias/zones using text manipulation above)
2. Run routing script: `python3 route_power.py`
3. Verify: `kicad-cli pcb drc ...` — check for `shorting_items` and `tracks_crossing`
4. If shorts: clear PCB, fix script, re-run. Do NOT run script twice on same file.

**Why text manipulation instead of pcbnew API for clearing:**
`board.Remove()` + `board.Save()` in pcbnew does not reliably persist to disk. Always clear
the file via S-expression text manipulation, then verify with grep before running routing scripts.

---

# CM5 Key Facts

## Connector
- Same physical 200-pin Hirose board-to-board as CM4 — **different pinout, NOT CM4-compatible**
- KiCad symbol/footprint: use official RPi CM5 library (not CM4)

## Power
- **5V / 5A minimum** (CM4 was 3A — this is a hard requirement)
- Recommended buck converter: min 8A saturation current inductor
- USB-C PD or barrel jack, targeting 5V/5A input

## Changed pins vs CM4
- Pin 16: now Fan_tacho (was Ethernet SYNC_IN)
- Pin 19: now Fan_pwm (was Ethernet LED)
- Pins 159, 163, 165, 169, 171: now USB 3.0 (was DSI0)
- Pins 128–142: now USB 3.0 (was CSI0/CAM0)

## What CM5 now handles internally (no external IC needed)
- RTC — no PCF85063A needed
- Fan controller — no EMC2301 needed
- Power button — dedicated pins on module

## USB
- CM5 has USB 3.0 (5 Gbps) — requires impedance-controlled differential pairs at 90Ω
- **Requires 4-layer PCB** for proper USB 3.0 routing (reference plane under high-speed traces)

---

# Board Spec

| Parameter | Value |
|-----------|-------|
| Layers | 4 |
| Stackup | F.Cu / In1.Cu (GND) / In2.Cu (PWR) / B.Cu |
| Dimensions | 80×60mm (2×20 GPIO header requires extra width) |
| Thickness | 1.6mm |
| Min trace | 0.1mm |
| Min via | 0.2mm drill |
| Surface finish | HASL or ENIG |
| Target fab | JLCPCB (EU-RO-1 ship to Sweden) |

---

# Target Feature Set (Minimal)

| Feature | Notes |
|---------|-------|
| CM5 connector | 200-pin Hirose |
| Power input | USB-C (5V/5A) — PD negotiation or dumb 5V |
| Battery | LiPo via JST-PH 2.0mm 2-pin — any capacity (5000mAh default) |
| Charger IC | BQ25895 — USB-C PD input, power path, up to 3A charge |
| Boost converter | TPS61089 — 3.7V LiPo → 5V/5A for CM5 |
| Power LED | Simple indicator |
| HDMI | Full-size or micro — single port |
| USB-A | ×2 USB 2.0 (or ×1 USB 3.0 if routing allows) |
| GPIO header | 2×20 pin (standard RPi pinout) |
| microSD | Slot for CM5 Lite variant |
| Reset button | Via CM5 RUN pin |
| Power button | Via CM5 dedicated power button pins |

**Explicitly NOT included** (keep it minimal):
- Ethernet (use USB adapter)
- Camera/display ribbon (CSI/DSI)
- Audio
- PCIe
- UART debug header (maybe add as unpopulated)

---

# Component Placement (power section)

| Ref | Position (mm) | Description |
|-----|--------------|-------------|
| U1 | (18, 20) | BQ25895RTW charger IC |
| U2 | (18, 36) | TPS61089 boost IC |
| L1 | (27, 20) | Boost inductor (BQ25895 SW) |
| L2 | (25, 36) | Boost inductor (TPS61089 SW) |
| J_USB | (7.5, 20) | USB-C input connector |
| J_BAT | (7, 40) | JST-PH battery connector |
| J_GPIO | (70, 4) | 2×20 GPIO header |
| J_HDMI | (17, 55) | HDMI-A connector |
| J_SDCARD | (36, 36) | microSD slot |
| J_USB1 | (34, 46.5) | USB-A port 1 |
| J_USB2 | (52, 46.5) | USB-A port 2 |
| SW_RST | (58, 38) | Reset button |
| SW_PWR | (64, 38) | Power button |

---

# Reference Designs

| Resource | Notes |
|----------|-------|
| RPi CM5 datasheet | https://datasheets.raspberrypi.com/cm5/cm5-datasheet.pdf |
| RPi CM5 KiCad reference design | Download from RPi design files page |
| timonsku CM4 minimal (Eagle) | https://github.com/timonsku/Minimal-RPi-CM-4-Carrier — inspiration, CM4 only |
| JLCPCB 4-layer stackup | JLC04161H-7628 (standard) |

---

# Fragile

- **CM5 vs CM4 pinout confusion** — always verify against CM5 datasheet, not CM4. The connector looks identical.
- **USB 3.0 impedance** — must be 90Ω differential. Measure trace width against JLCPCB 4-layer stackup specs before routing.
- **5V/5A power rail** — underspeccing the buck converter or inductor will cause instability under load. Don't reuse CM4 power designs.
- **Battery connector polarity** — JST-PH 2.0mm är inte polaritetsskyddad. Felvänd batteri = dött kort. Lägg till polaritetsmarkering på silkscreen och överväg en skyddsdiod.
- **LiPo boost current** — vid full CM5-last (5A @ 5V = 25W) drar boosten ~7.5A från batteriet (vid 3.7V + förluster). TPS61089 klarar detta men induktorn måste dimensioneras rätt (min 8A saturation).
- **eMMC vs Lite** — CM5 with eMMC doesn't need microSD. CM5 Lite does. Design for Lite (include SD slot).
- **TPS61089 pad numbering** — VQFN-11 custom footprint: pad numbers in PCB ≠ chip pin numbers. Verified order: 1=FSW, 2=VCC, 3=FB, 4=COMP, 5=GND, 6=VOUT, 7=EN(VSYS), 8=ILIM, 9=VIN(VSYS), 10=BOOT, 11=SW(center). pad11 is the exposed SW pad at package center.
- **TPS61089 boost topology** — inductor L2 is between VIN and SW node (pads: VSYS→SW). Bootstrap cap C13 connects BOOT↔SW. Do not confuse SW→VOUT topology.
- **Routing obstacle: C13 stub** — C13.pad2 (Net-U2-SW) at (24.4,43) cannot be reached by script: D2 at x=27.6 and J_SDCARD pad at x≈29.26 leave no gap. Route manually in KiCad GUI.
- **pcbnew API clearing** — `board.Remove()` + `board.Save()` does not reliably write to disk. Use S-expression text manipulation to clear segments/vias/zones before re-routing.
- **pcbnew KiCad 9 API changes** — `SetAssignedPriority()` (not `SetPriority()`), `ZONE_FILL_MODE_POLYGONS` (not `ZONE_FILL_MODE_SOLID`).
- **SW_RST/SW_PWR unnamed pad** — footprint has an `np_thru_hole` pad with empty pad number. This is a mechanical mounting hole — no net, not an electrical error.

---

# Manufacturing

- **Fab**: JLCPCB
- **Upload**: Zip all files in `fab/` and upload to jlcpcb.com
- **Order qty**: 5 boards minimum
- **Shipping**: DHL Express DDP (includes VAT, no customs surprises in Sweden)
- **Estimated cost**: ~$15-25 for 4-layer 5 boards + $30 shipping
