#!/usr/bin/env python3
"""
Phase 3: Assign nets to all PCB pads + remove duplicate footprints.
Uses bracket-counting for reliable pad block extraction.
"""

import re
import json

PCB = '/mnt/storage/cm5-carrier/cm5-carrier.kicad_pcb'

# ── CM5 pin→net from netlist ──────────────────────────────────────────
with open('/tmp/cm5_pin_nets.json') as f:
    cm5_raw = json.load(f)
CM5_NETS = {int(k): v for k, v in cm5_raw.items()}

# ── RPi GPIO 2×20 header pinout ────────────────────────────────────────
_C = '/CM5 Connector/'
GPIO_HEADER = {
    1:  '+3.3V',          2:  '+5V_CM5',
    3:  _C+'GPIO2',       4:  '+5V_CM5',
    5:  _C+'GPIO3',       6:  'GND',
    7:  _C+'GPIO4',       8:  _C+'GPIO14',
    9:  'GND',            10: _C+'GPIO15',
    11: _C+'GPIO17',      12: _C+'GPIO18',
    13: _C+'GPIO27',      14: 'GND',
    15: _C+'GPIO22',      16: _C+'GPIO23',
    17: '+3.3V',          18: _C+'GPIO24',
    19: _C+'GPIO10',      20: 'GND',
    21: _C+'GPIO9',       22: _C+'GPIO25',
    23: _C+'GPIO11',      24: _C+'GPIO8',
    25: 'GND',            26: _C+'GPIO7',
    27: _C+'ID_SD',       28: _C+'ID_SC',
    29: _C+'GPIO5',       30: 'GND',
    31: _C+'GPIO6',       32: _C+'GPIO12',
    33: _C+'GPIO13',      34: 'GND',
    35: _C+'GPIO19',      36: _C+'GPIO16',
    37: _C+'GPIO26',      38: _C+'GPIO20',
    39: 'GND',            40: _C+'GPIO21',
}

# ── HDMI-A connector (Amphenol 10029449) ──────────────────────────────
HDMI_A = {
    '1':  _C+'HDMI_PI.HDMI0_D2_P',
    '2':  'GND',
    '3':  _C+'HDMI_PI.HDMI0_D2_N',
    '4':  _C+'HDMI_PI.HDMI0_D1_P',
    '5':  'GND',
    '6':  _C+'HDMI_PI.HDMI0_D1_N',
    '7':  _C+'HDMI_PI.HDMI0_D0_P',
    '8':  'GND',
    '9':  _C+'HDMI_PI.HDMI0_D0_N',
    '10': _C+'HDMI_PI.HDMI0_CK_P',
    '11': 'GND',
    '12': _C+'HDMI_PI.HDMI0_CK_N',
    '13': _C+'HDMI_PI.HDMI0_CEC',
    '14': None,   # reserved
    '15': _C+'HDMI_PI.HDMI0_SCL',
    '16': _C+'HDMI_PI.HDMI0_SDA',
    '17': 'GND',
    '18': '+5V_CM5',
    '19': _C+'HDMI_PI.HDMI0_HOTPLUG',
    'SH': 'GND',
}

# ── microSD Molex 104031-0811 ─────────────────────────────────────────
SDCARD = {
    '1':  _C+'SD_DAT2',
    '2':  _C+'SD_DAT3',
    '3':  _C+'SD_CMD',
    '4':  '+3.3V',
    '5':  _C+'SD_CLK',
    '6':  'GND',
    '7':  _C+'SD_DAT0',
    '8':  _C+'SD_DAT1',
    '9':  'GND',
    '10': 'GND',
    '11': 'GND',
}

# ── USB-A Molex 67643 (4 + shield) ───────────────────────────────────
USB_A_1 = {
    '1': '+5V_CM5',
    '2': _C+'USB2P.D_N',
    '3': _C+'USB2P.D_P',
    '4': 'GND',
    '5': 'GND',
}
USB_A_2 = {
    '1': '+5V_CM5',
    '2': _C+'USB_PI.D_N',
    '3': _C+'USB_PI.D_P',
    '4': 'GND',
    '5': 'GND',
}

# ── Tactile buttons ────────────────────────────────────────────────────
SW_RST_MAP = {'1': _C+'GLOBAL_EN', '2': 'GND', '3': 'GND'}
SW_PWR_MAP = {'1': '/PWR_BUT_BTN',  '2': 'GND', '3': 'GND'}

# ── USB-C Input (J_USB) ────────────────────────────────────────────────
USBC_MAP = {
    'A1': 'GND', 'B1': 'GND',
    'A4': 'VBUS', 'B4': 'VBUS',
    'A9': 'VBUS', 'B9': 'VBUS',
    'A12': 'GND', 'B12': 'GND',
    'A5': 'VBUS',   # CC1 (via R1 5.1k pulls to GND on board)
    'B5': 'VBUS',   # CC2
    'SH': 'GND',
    '1': 'GND', '2': 'GND', '3': 'VBUS', '4': 'VBUS',
    '5': 'VBUS', '6': 'VBUS', '13': 'GND', '14': 'GND',
}

# ── JST-PH Battery (J_BAT) ────────────────────────────────────────────
JBAT_MAP = {'1': 'VBATT', '2': 'GND'}

# ── Passive components ─────────────────────────────────────────────────
# L1: BQ25895 switching inductor — SW side → output side (VSYS)
L1_NETS = {'1': 'Net-U1-SW', '2': 'VSYS'}
# L2: TPS61089 boost inductor — VIN side (VSYS) → SW node
# Boost topology: VIN → L → SW; internal high-side FET → VOUT
L2_NETS = {'1': 'VSYS', '2': 'Net-U2-SW'}
# D1: VBUS protection diode (anode=VBUS_IN, cathode=VBUS)
D1_NETS = {'1': 'VBUS', '2': 'VBUS'}
# Bypass caps near U1 (C1–C4): VSYS bypass
C1_C4  = {'1': 'VSYS', '2': 'GND'}
# Bypass caps near U2 input (C5–C7): VSYS input bypass
C5_C7  = {'1': 'VSYS', '2': 'GND'}
# Bypass caps near U2 output (C8–C10): +5V_CM5 output bypass
C8_C10 = {'1': '+5V_CM5', '2': 'GND'}
# R1–R4: ILIM/feedback resistors for BQ25895
R1_NETS = {'1': 'Net-U2-ILIM', '2': 'GND'}
R2_NETS = {'1': 'Net-U2-FB',   '2': 'GND'}
R3_NETS = {'1': 'Net-U2-COMP', '2': 'GND'}
R4_NETS = {'1': 'Net-U1-SW',   '2': 'GND'}
# R5–R8: I2C pull-up resistors (+3.3V → I2C lines)
R5_NETS = {'1': '+3.3V', '2': 'I2C0_SDA'}
R6_NETS = {'1': '+3.3V', '2': 'I2C0_SCL'}
R7_NETS = {'1': '+3.3V', '2': '/PWR_BUT_BTN'}
R8_NETS = {'1': '+3.3V', '2': 'GND'}

# ── TPS61089 (U2) VQFN-11 + EP ────────────────────────────────────────
# Pin mapping from KiCad Regulator_Switching:TPS61089 symbol:
# 1=FSW, 2=VCC, 3=FB, 4=COMP, 5=GND, 6=VOUT, 7=EN, 8=ILIM, 9=VIN, 10=BOOT, 11=SW, EP=GND
TPS_NETS = {
    '1':  'Net-U2-FSW',    # FSW: frequency-setting resistor to GND
    '2':  '+5V_CM5',       # VCC: internal bias, tied to VOUT
    '3':  'Net-U2-FB',     # FB: feedback voltage (1V ref)
    '4':  'Net-U2-COMP',   # COMP: error-amp compensation
    '5':  'GND',           # GND
    '6':  '+5V_CM5',       # VOUT: output voltage
    '7':  'VSYS',          # EN: enable — tied to VIN (always on)
    '8':  'Net-U2-ILIM',   # ILIM: current limit setting
    '9':  'VSYS',          # VIN: input from VSYS (BQ25895 SYS)
    '10': 'Net-U2-BOOT',   # BOOT: bootstrap capacitor node
    '11': 'Net-U2-SW',     # SW: switch node (inductor connects here)
    # Note: footprint is VQFN-11 (no separate EP pad in PCB)
}

# ── BQ25895RTW (U1) WQFN-24+EP ────────────────────────────────────────
BQ_NETS = {
    '1':  'VBUS',
    '5':  'I2C0_SCL',
    '6':  'I2C0_SDA',
    '13': 'VBATT',
    '14': 'GND',
    '15': 'VSYS',
    '16': 'GND',
    '17': 'GND',
    '18': 'Net-U1-SW',
    '19': 'Net-U1-SW',
    '20': 'Net-U1-SW',
    '21': 'Net-U1-SW',
    **{str(n): 'GND' for n in range(22, 40)},  # thermal pads
}

# ── All component → pad→net mappings ─────────────────────────────────
COMP_NETS = {
    'J_GPIO':   {str(p): v for p, v in GPIO_HEADER.items()},
    'J_HDMI':   HDMI_A,
    'J_SDCARD': SDCARD,
    'J_USB1':   USB_A_1,
    'J_USB2':   USB_A_2,
    'SW_RST':   SW_RST_MAP,
    'SW_PWR':   SW_PWR_MAP,
    'J_USB':    USBC_MAP,
    'J_BAT':    JBAT_MAP,
    'U1':       BQ_NETS,
    'U2':       TPS_NETS,
    'L1':       L1_NETS,
    'L2':       L2_NETS,
    'D1':       D1_NETS,
    'C1':       C1_C4,  'C2': C1_C4, 'C3': C1_C4, 'C4': C1_C4,
    'C5':       C5_C7,  'C6': C5_C7, 'C7': C5_C7,
    'C8':       C8_C10, 'C9': C8_C10, 'C10': C8_C10,
    # C11-C12: VSYS decoupling (placed near U2 input); C13: BOOT cap (BOOT→SW)
    # C14-C17: +5V_CM5 output decoupling
    'C11': C5_C7,  'C12': C5_C7,
    'C13': {'1': 'Net-U2-BOOT', '2': 'Net-U2-SW'},  # bootstrap cap 100nF
    'C14': C8_C10, 'C15': C8_C10, 'C16': C8_C10, 'C17': C8_C10,
    # ESD TVS diodes (added in Step 7)
    'D2': {'1': '+5V_CM5', '2': 'GND'},  # USB1 ESD
    'D3': {'1': '+5V_CM5', '2': 'GND'},  # USB2 ESD
    'D4': {'1': '+5V_CM5', '2': 'GND'},  # HDMI ESD
    'D5': {'1': 'VBUS',    '2': 'GND'},  # USB-C ESD
    'R1':       R1_NETS, 'R2': R2_NETS, 'R3': R3_NETS, 'R4': R4_NETS,
    'R5':       R5_NETS, 'R6': R6_NETS, 'R7': R7_NETS, 'R8': R8_NETS,
}

# ═══════════════════════════════════════════════════════════════════════
def find_block_end(text, start):
    """Return position just after the closing ) of block starting at start."""
    depth = 0
    for i, c in enumerate(text[start:]):
        if c == '(': depth += 1
        elif c == ')':
            depth -= 1
            if depth == 0:
                return start + i + 1
    return -1

# ═══════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════

with open(PCB) as f:
    pcb = f.read()

# ── Step 1: Remove duplicate footprints ────────────────────────────────
print('=== Step 1: Deduplication ===')
seen_refs = set()
dup_count = 0

fp_starts = [m.start() for m in re.finditer(r'[\n)]\t\(footprint "', pcb)]
fp_starts.append(len(pcb))  # sentinel

result = pcb[:fp_starts[0]+1] if fp_starts else pcb

for i, start in enumerate(fp_starts[:-1]):
    block_start = start + 1
    end = fp_starts[i+1]
    chunk = pcb[block_start:block_start+400]
    ref_m = re.search(r'"Reference" "([^"]+)"', chunk)
    ref = ref_m.group(1) if ref_m else '?'

    # If next match starts with ')' that char is this footprint's own closing paren
    end_inc = end + 1 if end < len(pcb) and pcb[end] == ')' else end

    if ref in seen_refs:
        dup_count += 1
        print(f'  Removing duplicate: {ref}')
    else:
        seen_refs.add(ref)
        result += pcb[block_start:end_inc]

# Restore the final \n) of the file
if not result.rstrip().endswith(')'):
    result = result.rstrip() + '\n)'

print(f'  Removed {dup_count} duplicates')
pcb = result

# ── Step 2: Build net table ────────────────────────────────────────────
print('\n=== Step 2: Net table ===')
existing_nets = re.findall(r'\(net (\d+) "([^"]+)"\)', pcb[:15000])
net_map = {name: int(num) for num, name in existing_nets}
next_id = max(int(n) for n, _ in existing_nets) + 1 if existing_nets else 1

def get_or_add_net(name):
    global next_id
    if not name:
        return None
    if name not in net_map:
        net_map[name] = next_id
        next_id += 1
    return net_map[name]

# Pre-register all nets
for pin_nets in COMP_NETS.values():
    for net in pin_nets.values():
        if net: get_or_add_net(net)
for net in CM5_NETS.values():
    get_or_add_net(net)

print(f'  Total nets: {len(net_map)} ({len(net_map) - len(existing_nets)} new)')

# ── Step 3: Assign pads using bracket counting ─────────────────────────
print('\n=== Step 3: Pad assignment ===')
stats = {}

def assign_nets_to_footprint(fp_block, pad_map):
    """Given footprint block and pad_num→net_name map, return updated block."""
    count = 0
    result = fp_block

    # Find all pad blocks using bracket counting
    search_pos = 0
    while True:
        # Find next (pad "N"... or (pad N... (quoted or unquoted)
        m = re.search(r'\(pad "?([^"\s)]+)"?\s', result[search_pos:])
        if not m:
            break

        pad_start = search_pos + m.start()
        pad_num = m.group(1)

        # Find end of pad block via bracket counting
        pad_end = find_block_end(result, pad_start)
        if pad_end == -1:
            search_pos = pad_start + 1
            continue

        pad_block = result[pad_start:pad_end]
        net_name = pad_map.get(pad_num)

        if net_name:
            net_id = get_or_add_net(net_name)
            # Remove existing (net ...) from pad block
            pad_block = re.sub(r'\s*\(net \d+ "[^"]*"\)', '', pad_block)
            # Insert before closing ) of pad block
            pad_block = pad_block[:-1] + f'\n\t\t\t(net {net_id} "{net_name}")\n\t\t)'
            count += 1

        result = result[:pad_start] + pad_block + result[pad_end:]
        search_pos = pad_start + len(pad_block)

    return result, count

total_assigned = 0
new_pcb_parts = []
pos = 0

for m in re.finditer(r'[\n)]\t\(footprint "([^"]+)"', pcb):
    fp_start = m.start() + 1
    chunk = pcb[fp_start:fp_start+400]
    ref_m = re.search(r'"Reference" "([^"]+)"', chunk)
    ref = ref_m.group(1) if ref_m else '?'

    fp_end = find_block_end(pcb, fp_start)
    if fp_end == -1:
        new_pcb_parts.append(pcb[pos:fp_start+1])
        pos = fp_start + 1
        continue

    new_pcb_parts.append(pcb[pos:fp_start])

    if ref == 'J_CM5':
        pad_map = {str(p): n for p, n in CM5_NETS.items() if p <= 100}
    elif ref in COMP_NETS:
        pad_map = COMP_NETS[ref]
    else:
        new_pcb_parts.append(pcb[fp_start:fp_end])
        pos = fp_end
        continue

    fp_block = pcb[fp_start:fp_end]
    new_block, count = assign_nets_to_footprint(fp_block, pad_map)
    new_pcb_parts.append(new_block)
    if count:
        stats[ref] = count
        total_assigned += count
    pos = fp_end

new_pcb_parts.append(pcb[pos:])
pcb = ''.join(new_pcb_parts)

print(f'  Assigned {total_assigned} pad nets:')
for ref, count in sorted(stats.items()):
    print(f'    {ref}: {count} pads')

# ── Step 4: Update net declarations ──────────────────────────────────
print('\n=== Step 4: Update net declarations ===')

# Remove existing net declarations (top-level only, 1 tab)
pcb = re.sub(r'\n\t\(net \d+ "[^"]*"\)', '', pcb)

# Build sorted net declarations with net 0 first
net_decls = '\t(net 0 "")\n'
net_decls += '\n'.join(f'\t(net {nid} "{name}")'
                        for name, nid in sorted(net_map.items(), key=lambda x: x[1]))

# Insert before first footprint
insert_target = re.search(r'\n\t\(footprint ', pcb)
if insert_target:
    ins = insert_target.start()
    pcb = pcb[:ins] + '\n' + net_decls + pcb[ins:]

# ── Write ──────────────────────────────────────────────────────────────
# Verify paren balance before writing
opens = pcb.count('(')
closes = pcb.count(')')
if opens != closes:
    print(f'ABORT: Paren imbalance! {opens} opens vs {closes} closes — NOT writing')
    import sys; sys.exit(1)
else:
    print(f'Paren balance OK ({opens})')

with open(PCB, 'w') as f:
    f.write(pcb)

print(f'\nDone. {len(net_map)} nets, {total_assigned} pads assigned')
