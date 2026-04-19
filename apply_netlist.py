#!/usr/bin/env python3
"""Apply KiCad netlist to PCB — assigns nets to footprint pads."""

import re
import sys
import pcbnew

BOARD_PATH = '/mnt/storage/cm5-carrier/cm5-carrier.kicad_pcb'
NETLIST_PATH = '/tmp/cm5-netlist.net'

def parse_netlist(path):
    """Parse kicadsexpr netlist, return dict: {(ref, pin): netname}"""
    with open(path) as f:
        lines = f.readlines()

    pad_nets = {}  # (ref, pin) -> netname
    current_net = None

    name_re = re.compile(r'\(name\s+"([^"]*)"\)')
    ref_re = re.compile(r'\(ref\s+"([^"]*)"\)')
    pin_re = re.compile(r'\(pin\s+"([^"]*)"\)')

    for line in lines:
        # Detect net line: (net (code "N") (name "NETNAME") ...
        if '(net ' in line and '(name ' in line:
            m = name_re.search(line)
            if m:
                current_net = m.group(1)
        # Detect node line: (node (ref "R1") (pin "1") ...
        elif '(node ' in line and current_net is not None:
            ref_m = ref_re.search(line)
            pin_m = pin_re.search(line)
            if ref_m and pin_m:
                ref = ref_m.group(1)
                pin = pin_m.group(1)
                pad_nets[(ref, pin)] = current_net

    return pad_nets

def apply_netlist(board, pad_nets):
    """Assign nets from pad_nets dict to board footprint pads."""
    netinfo = board.GetNetInfo()
    assigned = 0
    skipped = 0
    missing_fp = set()
    missing_pad = set()

    # Build ref -> footprint lookup
    fp_map = {}
    for fp in board.GetFootprints():
        fp_map[fp.GetReference()] = fp

    for (ref, pin), netname in pad_nets.items():
        fp = fp_map.get(ref)
        if fp is None:
            missing_fp.add(ref)
            skipped += 1
            continue

        # Find pad by number
        target_pad = None
        for pad in fp.Pads():
            if pad.GetNumber() == pin:
                target_pad = pad
                break

        if target_pad is None:
            missing_pad.add(f"{ref}.{pin}")
            skipped += 1
            continue

        # Get or create net
        nets_by_name = netinfo.NetsByName()
        if nets_by_name.has_key(netname):
            net = nets_by_name[netname]
        else:
            net = pcbnew.NETINFO_ITEM(board, netname)
            board.Add(net)
            netinfo = board.GetNetInfo()
            nets_by_name = netinfo.NetsByName()
            net = nets_by_name[netname] if nets_by_name.has_key(netname) else None

        if net:
            target_pad.SetNet(net)
            assigned += 1

    return assigned, skipped, missing_fp, missing_pad

def main():
    print("Loading board...")
    board = pcbnew.LoadBoard(BOARD_PATH)
    if board is None:
        print("ERROR: Could not load board")
        sys.exit(1)

    fps = board.GetFootprints()
    print(f"  {len(fps)} footprints")

    print("Parsing netlist...")
    pad_nets = parse_netlist(NETLIST_PATH)
    print(f"  {len(pad_nets)} pad-net assignments")

    print("Applying nets...")
    assigned, skipped, missing_fp, missing_pad = apply_netlist(board, pad_nets)
    print(f"  Assigned: {assigned}")
    print(f"  Skipped:  {skipped}")

    if missing_fp:
        print(f"\nMissing footprints ({len(missing_fp)}): {sorted(missing_fp)[:10]}")
    if missing_pad and len(missing_pad) < 20:
        print(f"Missing pads: {sorted(missing_pad)[:10]}")

    print("\nSaving board...")
    board.Save(BOARD_PATH)
    print("Done.")

    # Verify
    board2 = pcbnew.LoadBoard(BOARD_PATH)
    total_pads = sum(len(list(fp.Pads())) for fp in board2.GetFootprints())
    netted_pads = sum(
        1 for fp in board2.GetFootprints()
        for pad in fp.Pads()
        if pad.GetNet() and pad.GetNet().GetNetname()
    )
    print(f"\nVerification: {netted_pads}/{total_pads} pads have nets")

if __name__ == '__main__':
    main()
