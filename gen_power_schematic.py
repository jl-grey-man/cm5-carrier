#!/usr/bin/env python3
"""
Generate power.kicad_sch for CM5 carrier board.
Power circuit: USB-C → BQ25895RTW charger → LiPo (JST-PH)
               LiPo → TPS61089 boost → +5V_CM5
"""

import re, uuid

def uid():
    return str(uuid.uuid4())

def kicad9_to_kicad8_sym(block):
    """Convert KiCad 9 library format differences to KiCad 8 schematic inline format."""
    # (pin_numbers (hide yes)) → (pin_numbers hide)
    block = re.sub(
        r'\(pin_numbers\s*\(\s*hide\s+yes\s*\)\s*\)',
        '(pin_numbers hide)', block, flags=re.DOTALL)
    # (pin_names (offset N) (hide yes)) → (pin_names (offset N) hide)
    block = re.sub(
        r'\(pin_names\s*(\(offset\s+[\d.]+\))\s*\(\s*hide\s+yes\s*\)\s*\)',
        r'(pin_names \1 hide)', block, flags=re.DOTALL)
    # (pin_names (hide yes)) → (pin_names hide)
    block = re.sub(
        r'\(pin_names\s*\(\s*hide\s+yes\s*\)\s*\)',
        '(pin_names hide)', block, flags=re.DOTALL)
    return block


def extract_sym(lib_path, sym_name, lib_prefix):
    """Extract symbol from KiCad .kicad_sym and rename with lib prefix."""
    with open(lib_path) as f:
        content = f.read()
    marker = f'(symbol "{sym_name}"'
    start = content.find(marker)
    if start == -1:
        raise ValueError(f"{sym_name} not found in {lib_path}")
    depth = 0
    for j, c in enumerate(content[start:], start):
        if c == '(': depth += 1
        elif c == ')':
            depth -= 1
            if depth == 0:
                block = content[start:j+1]
                new_name = f"{lib_prefix}:{sym_name}"
                # Only rename the TOP-LEVEL symbol, NOT sub-symbols (_0_1, _1_1 etc.)
                # Sub-symbols must keep their original name (no lib prefix) per KiCad 8 format
                block = block.replace(f'(symbol "{sym_name}"\n', f'(symbol "{new_name}"\n', 1)
                # Remove KiCad 9-specific embedded_fonts attribute
                block = block.replace('\t\t(embedded_fonts no)\n', '')
                block = kicad9_to_kicad8_sym(block)
                return block
    raise ValueError("Unbalanced parens")

def placed_sym(lib_id, ref, value, x, y, rot=0, footprint="", datasheet=""):
    pwrref = f"#PWR{uid()[:4]}" if lib_id.startswith("power:") else ref
    hide_ref = "(hide yes)" if lib_id.startswith("power:") else ""
    return f"""	(symbol
		(lib_id "{lib_id}")
		(at {x:.2f} {y:.2f} {rot})
		(unit 1)
		(exclude_from_sim no)
		(in_bom yes)
		(on_board yes)
		(dnp no)
		(uuid "{uid()}")
		(property "Reference" "{pwrref}"
			(at {x+2.54:.2f} {y-2.54:.2f} 0)
			(effects (font (size 1.27 1.27)) {hide_ref})
		)
		(property "Value" "{value}"
			(at {x+2.54:.2f} {y+2.54:.2f} 0)
			(effects (font (size 1.27 1.27)))
		)
		(property "Footprint" "{footprint}"
			(at {x:.2f} {y:.2f} 0)
			(effects (font (size 1.27 1.27)) (hide yes))
		)
		(property "Datasheet" "{datasheet}"
			(at {x:.2f} {y:.2f} 0)
			(effects (font (size 1.27 1.27)) (hide yes))
		)
	)"""

def wire(x1, y1, x2, y2):
    return f"""	(wire
		(pts (xy {x1:.2f} {y1:.2f}) (xy {x2:.2f} {y2:.2f}))
		(stroke (width 0) (type default))
		(uuid "{uid()}")
	)"""

def label(name, x, y, angle=0):
    return f"""	(label "{name}"
		(at {x:.2f} {y:.2f} {angle})
		(fields_autoplaced yes)
		(effects (font (size 1.27 1.27)) (justify left bottom))
		(uuid "{uid()}")
	)"""

def global_label(name, x, y, angle=0, shape="output"):
    return f"""	(global_label "{name}"
		(shape {shape})
		(at {x:.2f} {y:.2f} {angle})
		(fields_autoplaced yes)
		(effects (font (size 1.27 1.27)) (justify left))
		(uuid "{uid()}")
		(property "Intersheet References" ""
			(at 0 0 0)
			(effects (font (size 1.27 1.27)) (hide yes))
		)
	)"""

def no_connect(x, y):
    return f'	(no_connect (at {x:.2f} {y:.2f}) (uuid "{uid()}"))'

def text(s, x, y, size=1.27, bold=False):
    bold_str = "(bold yes)" if bold else ""
    return f"""	(text "{s}"
		(at {x:.2f} {y:.2f} 0)
		(effects (font (size {size:.2f} {size:.2f}) {bold_str}))
		(uuid "{uid()}")
	)"""

# ─────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────

BATT_MGMT = "/usr/share/kicad/symbols/Battery_Management.kicad_sym"
REG_SW    = "/usr/share/kicad/symbols/Regulator_Switching.kicad_sym"
DEVICE    = "/usr/share/kicad/symbols/Device.kicad_sym"
CONN      = "/usr/share/kicad/symbols/Connector_Generic.kicad_sym"
POWER     = "/usr/share/kicad/symbols/power.kicad_sym"

# Extract symbols with correct library prefixes
syms = {
    "Battery_Management:BQ25895RTW": extract_sym(BATT_MGMT, "BQ25895RTW", "Battery_Management"),
    "Regulator_Switching:TPS61089":  extract_sym(REG_SW, "TPS61089", "Regulator_Switching"),
    "Device:R":                       extract_sym(DEVICE, "R", "Device"),
    "Device:C":                       extract_sym(DEVICE, "C", "Device"),
    "Device:L":                       extract_sym(DEVICE, "L", "Device"),
    "Device:LED":                     extract_sym(DEVICE, "LED", "Device"),
    "Connector_Generic:Conn_01x02":   extract_sym(CONN, "Conn_01x02", "Connector_Generic"),
    "power:GND":                      extract_sym(POWER, "GND", "power"),
    "power:+5V":                      extract_sym(POWER, "+5V", "power"),
    "power:+3.3V":                    extract_sym(POWER, "+3.3V", "power"),
}
lib_symbols_str = "\n\t".join(syms.values())

# ── Component instances ───────────────────────────────────────────────
R = "Resistor_SMD:R_0402_1005Metric"
C = "Capacitor_SMD:C_0402_1005Metric"
C1210 = "Capacitor_SMD:C_1210_3225Metric"
L_BOOST = "Inductor_SMD:L_Bourns_SRR4028"
LED_FP = "LED_SMD:LED_0603_1608Metric"
JST_FP = "Connector_JST:JST_PH_S2B-PH-K_1x02_P2.00mm_Horizontal"
USBC_FP = "Connector_USB:USB_C_Receptacle_GCT_USB4135_16P_Vertical_SMD"

parts = []
wires_list = []
labels_list = []
no_conn_list = []

# ═══════════════════════════════════════════════════════════════════════
# SECTION 1: USB-C Input (top-left)
# ═══════════════════════════════════════════════════════════════════════
parts.append(text("1. USB-C Input", 15, 20, size=1.5, bold=True))
parts.append(text("J1 uses full 16-pin USB-C footprint. CC1/CC2: 5.1kΩ to GND → 5V sink (no PD).", 15, 24))

# J1: USB-C (shown as simple 2-pin connector for schematic, assign real footprint)
parts.append(placed_sym("Connector_Generic:Conn_01x02", "J1", "USB-C_5V_Input",
                         25, 45, footprint=USBC_FP,
                         datasheet="https://www.usb.org/sites/default/files/documents/usb_type-c.zip"))
# Pin 1 = VBUS, Pin 2 = GND
labels_list.append(global_label("VBUS", 38, 42.5, angle=0, shape="output"))
wires_list.append(wire(30, 42.5, 38, 42.5))
parts.append(placed_sym("power:GND", "GND", "GND", 30, 52))
wires_list.append(wire(30, 47.5, 30, 52))

# CC1 / CC2 pull-downs (5.1k each)
parts.append(placed_sym("Device:R", "R1", "5.1k", 50, 38, footprint=R))
parts.append(placed_sym("Device:R", "R2", "5.1k", 60, 38, footprint=R))
labels_list.append(label("CC1", 50, 33))
labels_list.append(label("CC2", 60, 33))
parts.append(placed_sym("power:GND", "GND", "GND", 50, 48))
parts.append(placed_sym("power:GND", "GND", "GND", 60, 48))

# VBUS bulk decoupling (10uF + 100nF)
parts.append(placed_sym("Device:C", "C1", "10uF/10V", 38, 55, footprint=C1210))
parts.append(placed_sym("Device:C", "C2", "100nF/10V", 46, 55, footprint=C))
parts.append(placed_sym("power:GND", "GND", "GND", 38, 65))
parts.append(placed_sym("power:GND", "GND", "GND", 46, 65))

# ═══════════════════════════════════════════════════════════════════════
# SECTION 2: BQ25895RTW Charger (center)
# ═══════════════════════════════════════════════════════════════════════
parts.append(text("2. BQ25895RTW — USB Charger + Power Path Manager", 70, 20, size=1.5, bold=True))
parts.append(text("Charges LiPo from USB-C. SYS output powers TPS61089. I2C control via CM5.", 70, 24))

parts.append(placed_sym("Battery_Management:BQ25895RTW", "U1", "BQ25895RTW",
                          110, 75,
                          footprint="Package_DFN_QFN:Texas_WQFN-24-1EP_4x4mm_P0.5mm_EP2.7x2.7mm",
                          datasheet="https://www.ti.com/lit/ds/symlink/bq25895.pdf"))

# VBUS in
labels_list.append(global_label("VBUS", 75, 63, angle=0, shape="input"))

# Charge inductor L1 between SW and VBUS (2.2uH, 8A sat)
parts.append(placed_sym("Device:L", "L1", "2.2uH/8A", 88, 63,
                          footprint=L_BOOST,
                          datasheet="https://www.bourns.com/docs/Product-Datasheets/SRR4028.pdf"))
wires_list.append(wire(75, 63, 85, 63))   # VBUS → L1
wires_list.append(wire(92, 63, 110, 63))  # L1 → SW pin of U1

# BTST cap (100nF)
parts.append(placed_sym("Device:C", "C3", "100nF/10V", 125, 52, footprint=C))
parts.append(placed_sym("power:GND", "GND", "GND", 125, 62))

# REGN bypass (10uF + 100nF)
parts.append(placed_sym("Device:C", "C4", "10uF/10V", 138, 52, footprint=C))
parts.append(placed_sym("Device:C", "C5", "100nF/10V", 146, 52, footprint=C))
parts.append(placed_sym("power:GND", "GND", "GND", 138, 62))
parts.append(placed_sym("power:GND", "GND", "GND", 146, 62))

# PMID bypass (1uF)
parts.append(placed_sym("Device:C", "C6", "1uF/10V", 155, 52, footprint=C))
parts.append(placed_sym("power:GND", "GND", "GND", 155, 62))

# ILIM resistor (68k → ~1A limit, adjustable)
parts.append(placed_sym("Device:R", "R3", "68k", 125, 85, footprint=R))
parts.append(placed_sym("power:GND", "GND", "GND", 125, 95))

# CE (charge enable) — pulled low via 10k resistor to always enable
parts.append(placed_sym("Device:R", "R4", "10k", 75, 85, footprint=R))
parts.append(placed_sym("power:GND", "GND", "GND", 80, 95))

# QON (ship mode) — pulled high via 100k (normal operation)
parts.append(placed_sym("Device:R", "R5", "100k", 75, 100, footprint=R))
parts.append(placed_sym("power:+3.3V", "+3.3V", "+3.3V", 80, 95))

# STAT LED (charge status indicator)
parts.append(placed_sym("Device:R", "R6", "1k", 75, 110, footprint=R))
parts.append(placed_sym("Device:LED", "D1", "LED_STAT", 68, 110,
                          footprint=LED_FP))
parts.append(placed_sym("power:GND", "GND", "GND", 63, 118))

# I2C to CM5 (global labels for cross-sheet connection)
labels_list.append(global_label("I2C0_SDA", 75, 118, angle=0, shape="bidirectional"))
labels_list.append(global_label("I2C0_SCL", 75, 125, angle=0, shape="bidirectional"))

# SYS output decoupling (2x 47uF)
parts.append(placed_sym("Device:C", "C7", "47uF/10V", 138, 82, footprint=C1210))
parts.append(placed_sym("Device:C", "C8", "47uF/10V", 148, 82, footprint=C1210))
parts.append(placed_sym("power:GND", "GND", "GND", 138, 92))
parts.append(placed_sym("power:GND", "GND", "GND", 148, 92))

# SYS → boost stage
labels_list.append(global_label("VSYS", 160, 75, angle=0, shape="output"))

# BAT pins ← JST connector
labels_list.append(global_label("VBATT", 75, 132, angle=0, shape="bidirectional"))
# BAT decoupling (100uF)
parts.append(placed_sym("Device:C", "C9", "100uF/6.3V", 138, 100, footprint=C1210))
parts.append(placed_sym("power:GND", "GND", "GND", 138, 110))

# D+ / D- no-connect (USB BC1.2 not used)
no_conn_list.append(no_connect(75, 140))
no_conn_list.append(no_connect(75, 145))

# DSEL no-connect
no_conn_list.append(no_connect(145, 80))

# ═══════════════════════════════════════════════════════════════════════
# SECTION 3: JST-PH Battery Connector (bottom-left)
# ═══════════════════════════════════════════════════════════════════════
parts.append(text("3. LiPo Battery — JST-PH 2.0mm 2-pin", 15, 150, size=1.5, bold=True))
parts.append(text("Any 3.7V LiPo (5000mAh default). Pin 1 = + (red), Pin 2 = - (black).", 15, 154))
parts.append(text("WARNING: Add B5819W Schottky diode in series for reverse-polarity protection!", 15, 158))

parts.append(placed_sym("Connector_Generic:Conn_01x02", "J2", "BATT_JST-PH_3.7V",
                          35, 170, footprint=JST_FP,
                          datasheet="https://www.jst-mfg.com/product/detail_e.php?series=199"))
labels_list.append(global_label("VBATT", 55, 167.5, angle=0, shape="output"))
wires_list.append(wire(42, 167.5, 55, 167.5))
parts.append(placed_sym("power:GND", "GND", "GND", 42, 178))
wires_list.append(wire(42, 172.5, 42, 178))

# ═══════════════════════════════════════════════════════════════════════
# SECTION 4: TPS61089 Boost Converter (right)
# ═══════════════════════════════════════════════════════════════════════
parts.append(text("4. TPS61089 — 3.7V→5.1V Boost (5A continuous)", 190, 20, size=1.5, bold=True))
parts.append(text("VIN from VSYS (BQ25895 SYS output). VOUT=5.1V set by R_FB divider.", 190, 24))
parts.append(text("TPS61089 rated 10A switch current — adequate for CM5 5A draw.", 190, 28))

parts.append(placed_sym("Regulator_Switching:TPS61089", "U2", "TPS61089",
                          230, 75,
                          footprint="Package_DFN_QFN:Texas_VQFN-14-1EP_3.5x4.5mm_P0.65mm_EP2.7x3.1mm",
                          datasheet="https://www.ti.com/lit/ds/symlink/tps61089.pdf"))

# VIN from VSYS
labels_list.append(global_label("VSYS", 195, 68, angle=0, shape="input"))
wires_list.append(wire(200, 68, 230, 68))

# VIN decoupling (2x 47uF + 100nF)
parts.append(placed_sym("Device:C", "C10", "47uF/10V", 210, 55, footprint=C1210))
parts.append(placed_sym("Device:C", "C11", "47uF/10V", 220, 55, footprint=C1210))
parts.append(placed_sym("Device:C", "C12", "100nF/10V", 230, 55, footprint=C))
parts.append(placed_sym("power:GND", "GND", "GND", 210, 65))
parts.append(placed_sym("power:GND", "GND", "GND", 220, 65))
parts.append(placed_sym("power:GND", "GND", "GND", 230, 65))

# Boost inductor L2 (1.0uH, 10A sat) — between SW and VOUT
# Value matches PCB: 1.0uH/10A saturation (correct for TPS61089 at 5A output)
parts.append(placed_sym("Device:L", "L2", "1.0uH/10A", 248, 68,
                          footprint=L_BOOST))

# BOOT cap (100nF)
parts.append(placed_sym("Device:C", "C13", "100nF/10V", 260, 55, footprint=C))
parts.append(placed_sym("power:GND", "GND", "GND", 260, 65))

# R7: Power button pull-up (10k, +3.3V → /PWR_BUT_BTN)
# Pin 2 (top) = y-3.81 = 81.19, Pin 1 (bottom) = y+3.81 = 88.81
parts.append(placed_sym("Device:R", "R7", "10k", 215, 85, footprint=R))
parts.append(placed_sym("power:+3.3V", "+3.3V", "+3.3V", 215, 81.19))
labels_list.append(global_label("/PWR_BUT_BTN", 215, 88.81, angle=270, shape="bidirectional"))

# R8: +3.3V pull-down (10k, +3.3V → GND)
# Pin 2 (top) = y-3.81 = 91.19, Pin 1 (bottom) = y+3.81 = 98.81
parts.append(placed_sym("Device:R", "R8", "10k", 215, 95, footprint=R))
parts.append(placed_sym("power:+3.3V", "+3.3V", "+3.3V", 215, 91.19))
parts.append(placed_sym("power:GND", "GND", "GND", 215, 98.81))

# Feedback divider: Vout = 0.5 * (1 + R_top/R_bot)
# Vout=5.1V: R_top=1M, R_bot=110k
parts.append(placed_sym("Device:R", "R9", "1M",   268, 75, footprint=R))
parts.append(placed_sym("Device:R", "R10", "110k", 268, 90, footprint=R))
parts.append(placed_sym("power:GND", "GND", "GND", 268, 100))
labels_list.append(label("FB", 258, 82))

# VOUT decoupling (3x 47uF + 100nF)
parts.append(placed_sym("Device:C", "C14", "47uF/10V", 285, 55, footprint=C1210))
parts.append(placed_sym("Device:C", "C15", "47uF/10V", 295, 55, footprint=C1210))
parts.append(placed_sym("Device:C", "C16", "47uF/10V", 305, 55, footprint=C1210))
parts.append(placed_sym("Device:C", "C17", "100nF/10V", 315, 55, footprint=C))
parts.append(placed_sym("power:GND", "GND", "GND", 285, 65))
parts.append(placed_sym("power:GND", "GND", "GND", 295, 65))
parts.append(placed_sym("power:GND", "GND", "GND", 305, 65))
parts.append(placed_sym("power:GND", "GND", "GND", 315, 65))

# GND
parts.append(placed_sym("power:GND", "GND", "GND", 230, 115))

# VOUT → global label for CM5
labels_list.append(global_label("+5V_CM5", 330, 68, angle=0, shape="output"))
wires_list.append(wire(265, 68, 330, 68))

# ═══════════════════════════════════════════════════════════════════════
# ASSEMBLE
# ═══════════════════════════════════════════════════════════════════════
all_elements = "\n".join(parts + wires_list + labels_list + no_conn_list)

schematic = f"""(kicad_sch
	(version 20231120)
	(generator "eeschema")
	(generator_version "8.0")
	(uuid "{uid()}")
	(paper "A3")
	(title_block
		(title "CM5 Carrier — Power Management")
		(date "2026-04-18")
		(rev "1")
		(company "Jens Lennartsson")
		(comment 1 "USB-C 5V → BQ25895RTW charger → LiPo (JST-PH 2mm)")
		(comment 2 "LiPo 3.7V → TPS61089 boost → +5V_CM5 (5.1V/5A)")
		(comment 3 "I2C control of charger via CM5 GPIO (I2C0_SDA/SCL)")
	)
	(lib_symbols
		{lib_symbols_str}
	)
{all_elements}
	(sheet_instances
		(path "/" (page "1"))
	)
)
"""

out = "/mnt/storage/cm5-carrier/power.kicad_sch"
with open(out, "w") as f:
    f.write(schematic)
print(f"✓ Written {out} ({len(schematic):,} bytes, ~{len(parts)} components)")
