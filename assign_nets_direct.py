#!/usr/bin/env python3
"""
Directly assign correct nets to PCB pads based on design intent.
Bypasses the broken schematic netlist (wires don't connect to pins).

Design: USB-C → BQ25895RTW charger → LiPo → TPS61089 boost → +5V_CM5
"""

import pcbnew
import sys

BOARD_PATH = '/mnt/storage/cm5-carrier/cm5-carrier.kicad_pcb'

# ─── Net assignment tables ───────────────────────────────────────────────────
# Format: {ref: {pad_number: net_name}}

PAD_NETS = {

    # ── U1: BQ25895RTW — USB charger / power path ──────────────────────────
    # Pinout: 24-pin WQFN + EP (pad 25)
    'U1': {
        '1':  'VBUS',           # VBUS input from USB-C
        '2':  'GND',            # D+  → GND (BC1.2 not used, was no_connect → keep as GND or NC)
        '3':  'GND',            # D-  → GND (BC1.2 not used)
        '4':  'STAT',           # Status output → LED
        '5':  'I2C0_SCL',       # I2C clock
        '6':  'I2C0_SDA',       # I2C data
        '7':  'GND',            # INT → leave NC or GPIO; tie to GND for now (pull-up needed)
        '8':  'GND',            # OTG → GND (disable OTG mode)
        '9':  'GND',            # /CE → GND (charge always enabled, active-low)
        '10': 'ILIM',           # Input current limit resistor
        '11': 'GND',            # TS → GND (no NTC thermistor)
        '12': '/PWR_BUT_BTN',   # /QON → power button
        '13': 'VBATT',          # BAT
        '14': 'VBATT',          # BAT (2nd pad)
        '15': 'VSYS',           # SYS output → TPS61089 VIN
        '16': 'VSYS',           # SYS (2nd pad)
        '17': 'GND',            # PGND
        '18': 'GND',            # PGND
        '19': 'SW_BQ',          # SW → inductor L1 → VBUS
        '20': 'SW_BQ',          # SW (2nd pad)
        '21': 'BTST',           # Bootstrap → C3 → SW_BQ
        '22': 'REGN',           # Internal LDO output → C4, C5
        '23': 'PMID',           # Internal node → C6
        '24': 'GND',            # DSEL → GND
        '25': 'GND',            # EP (thermal pad) → GND
        '':   'GND',            # Any unnamed EP pads
    },

    # ── U2: TPS61089 — boost converter 3.7V → 5.1V ─────────────────────────
    # Pinout: 14-pin VQFN (pads 1-11 + EP + PGND pads)
    'U2': {
        '1':  'FSW',            # Frequency set → resistor to GND
        '2':  'REGN_BOOST',     # VCC internal LDO → cap to GND
        '3':  'FB_BOOST',       # Feedback → resistor divider from +5V_CM5
        '4':  'COMP_BOOST',     # Compensation → cap to GND
        '5':  'GND',            # AGND
        '6':  '+5V_CM5',        # VOUT = 5.1V regulated output
        '7':  'VSYS',           # EN → tied to VSYS (always enabled)
        '8':  'ILIM_BOOST',     # Current limit → resistor to GND
        '9':  'VSYS',           # VIN from BQ25895 SYS
        '10': 'BOOT_BOOST',     # Bootstrap → cap from SW to BOOT
        '11': 'SW_BOOST',       # Switch node → inductor L2
        '12': 'GND',            # PGND
        '13': 'GND',            # PGND
        '14': 'GND',            # PGND (if exists)
        '':   'GND',            # EP
    },

    # ── L1: Charge inductor between VBUS and BQ25895 SW ─────────────────────
    # SRR4028 has pads 1 and 2
    'L1': {
        '1': 'VBUS',            # VBUS side
        '2': 'SW_BQ',           # SW side (to U1 SW pin)
    },

    # ── L2: Boost inductor between TPS61089 SW and output ───────────────────
    'L2': {
        '1': 'SW_BOOST',        # SW side (to U2 SW pin)
        '2': '+5V_CM5',         # Output side
    },

    # ── C1: VBUS bulk decoupling 10uF ────────────────────────────────────────
    'C1': {'1': 'VBUS', '2': 'GND'},

    # ── C2: VBUS bulk decoupling 100nF ───────────────────────────────────────
    'C2': {'1': 'VBUS', '2': 'GND'},

    # ── C3: BTST bypass cap (100nF between BTST and SW_BQ) ───────────────────
    'C3': {'1': 'BTST', '2': 'SW_BQ'},

    # ── C4: REGN bypass 10uF ─────────────────────────────────────────────────
    'C4': {'1': 'REGN', '2': 'GND'},

    # ── C5: REGN bypass 100nF ────────────────────────────────────────────────
    'C5': {'1': 'REGN', '2': 'GND'},

    # ── C6: PMID bypass 1uF ──────────────────────────────────────────────────
    'C6': {'1': 'PMID', '2': 'GND'},

    # ── C7: SYS decoupling 47uF ──────────────────────────────────────────────
    'C7': {'1': 'VSYS', '2': 'GND'},

    # ── C8: SYS decoupling 47uF ──────────────────────────────────────────────
    'C8': {'1': 'VSYS', '2': 'GND'},

    # ── C9: BAT decoupling 100uF ─────────────────────────────────────────────
    'C9': {'1': 'VBATT', '2': 'GND'},

    # ── C10: +5V_CM5 output cap (if present) ─────────────────────────────────
    'C10': {'1': '+5V_CM5', '2': 'GND'},

    # ── R1: CC1 pull-down 5.1k (VBUS sink identification) ────────────────────
    'R1': {'1': 'CC1', '2': 'GND'},

    # ── R2: CC2 pull-down 5.1k ───────────────────────────────────────────────
    'R2': {'1': 'CC2', '2': 'GND'},

    # ── R3: ILIM resistor 68k ────────────────────────────────────────────────
    'R3': {'1': 'ILIM', '2': 'GND'},

    # ── R4: /CE pull-down 10k ────────────────────────────────────────────────
    'R4': {'1': 'GND', '2': 'GND'},   # Both to GND (CE always enabled)

    # ── R5: /QON pull-up 100k to +3.3V ──────────────────────────────────────
    'R5': {'1': '+3.3V', '2': '/PWR_BUT_BTN'},

    # ── R6: STAT LED resistor 1k ─────────────────────────────────────────────
    'R6': {'1': 'STAT', '2': 'STAT_LED'},

    # ── R7: FB upper resistor (VOUT to FB) ───────────────────────────────────
    'R7': {'1': '+5V_CM5', '2': 'FB_BOOST'},

    # ── R8: FB lower resistor (FB to GND) ────────────────────────────────────
    'R8': {'1': 'FB_BOOST', '2': 'GND'},

    # ── D1: Status LED ───────────────────────────────────────────────────────
    'D1': {'1': 'GND', '2': 'STAT_LED'},   # K=GND, A=STAT_LED (through R6)

    # ── J_BAT / J2: JST-PH battery connector ─────────────────────────────────
    # Pin 1 = + (VBATT), Pin 2 = - (GND)
    'J_BAT': {'1': 'VBATT', '2': 'GND'},
    'J2':    {'1': 'VBATT', '2': 'GND'},

    # ── J_USB: USB-C power input connector ───────────────────────────────────
    # HRO TYPE-C-31-M-12 / USB-C standard pad mapping
    'J_USB': {
        'A1':  'GND',    # GND
        'A4':  'VBUS',   # VBUS
        'A5':  'CC1',    # CC1 → 5.1k to GND
        'A6':  'GND',    # D+ (not used, tie low)
        'A7':  'GND',    # D- (not used)
        'A8':  'GND',    # SBU1 (not used)
        'A9':  'VBUS',   # VBUS
        'A12': 'GND',    # GND
        'B1':  'GND',    # GND
        'B4':  'VBUS',   # VBUS
        'B5':  'CC2',    # CC2 → 5.1k to GND
        'B6':  'GND',    # D- (not used)
        'B7':  'GND',    # D+ (not used)
        'B8':  'GND',    # SBU2 (not used)
        'B9':  'VBUS',   # VBUS
        'B12': 'GND',    # GND
        'S1':  'GND',    # Shield/case GND (multiple S1 pads)
        '':    'GND',    # Any unlabeled pads (shield pins)
    },

    # ── J_USB1 / J_USB2: USB-A host ports (USB 2.0 from CM5) ─────────────────
    # Already have nets from CM5 connector sheet — skip

    # ── SW_RST: Reset button ──────────────────────────────────────────────────
    # Pads: pin 1/2 + NC pin for 4-pad button
    # Pin labeled '' is the NC tab pad
    'SW_RST': {'': 'GND'},  # NC pad → GND (connect tab to GND)

    # ── SW_PWR: Power button ──────────────────────────────────────────────────
    'SW_PWR': {'': 'GND'},  # NC pad → GND

    # ── Mounting holes → GND ─────────────────────────────────────────────────
    'H1':  {'': 'GND'},
    'MH2': {'': 'GND'},
    'MH3': {'': 'GND'},
    'MH4': {'': 'GND'},
}


def get_or_create_net(board, netname):
    ni = board.GetNetInfo()
    nets = ni.NetsByName()
    if nets.has_key(netname):
        return nets[netname]
    net = pcbnew.NETINFO_ITEM(board, netname)
    board.Add(net)
    return board.GetNetInfo().NetsByName()[netname]


def assign_nets(board):
    fp_map = {fp.GetReference(): fp for fp in board.GetFootprints()}
    assigned = 0
    skipped = 0

    for ref, pad_map in PAD_NETS.items():
        fp = fp_map.get(ref)
        if fp is None:
            # Silently skip — component not in PCB
            continue

        for pad in fp.Pads():
            pad_num = pad.GetNumber()
            # Look up exact pad number first, then fallback to '' for unnamed
            if pad_num in pad_map:
                netname = pad_map[pad_num]
            elif '' in pad_map:
                netname = pad_map['']
            else:
                skipped += 1
                continue

            net = get_or_create_net(board, netname)
            pad.SetNet(net)
            assigned += 1

    return assigned, skipped


def main():
    print("Loading board...")
    board = pcbnew.LoadBoard(BOARD_PATH)
    fps = board.GetFootprints()
    print(f"  {len(fps)} footprints")

    print("Assigning nets...")
    assigned, skipped = assign_nets(board)
    print(f"  Assigned: {assigned}")
    print(f"  Skipped:  {skipped}")

    print("Saving...")
    board.Save(BOARD_PATH)

    # Verify
    board2 = pcbnew.LoadBoard(BOARD_PATH)
    total = sum(len(list(fp.Pads())) for fp in board2.GetFootprints())
    netted = sum(
        1 for fp in board2.GetFootprints()
        for pad in fp.Pads()
        if pad.GetNet() and pad.GetNet().GetNetname()
    )
    print(f"\nResult: {netted}/{total} pads have nets")

    # Show remaining unnetted
    print("\nComponents with unnetted pads:")
    for fp in board2.GetFootprints():
        pads = list(fp.Pads())
        unnetted = [p.GetNumber() for p in pads
                    if not p.GetNet() or not p.GetNet().GetNetname()]
        if unnetted:
            print(f"  {fp.GetReference():12s}: pads {unnetted}")


if __name__ == '__main__':
    main()
