#!/usr/bin/env python3
"""
Derive correct pad net assignments from existing track routing.
Finds each track endpoint → nearest pad → assigns track's net to that pad.
This eliminates shorts caused by mismatched pad/track nets.
"""

import pcbnew
import sys
from collections import defaultdict

BOARD_PATH = '/mnt/storage/cm5-carrier/cm5-carrier.kicad_pcb'
TOLERANCE = pcbnew.FromMM(0.15)   # tight: only true connections


def build_pad_index(board):
    """Return dict: (x, y) → pad object."""
    index = {}
    for fp in board.GetFootprints():
        for pad in fp.Pads():
            pos = pad.GetCenter()
            index[(pos.x, pos.y)] = pad
    return index


def get_or_create_net(board, netname):
    ni = board.GetNetInfo()
    nets = ni.NetsByName()
    if nets.has_key(netname):
        return nets[netname]
    net = pcbnew.NETINFO_ITEM(board, netname)
    board.Add(net)
    return board.GetNetInfo().NetsByName()[netname]


def fix_from_tracks(board):
    pad_index = build_pad_index(board)
    changed = 0
    conflicts = defaultdict(set)   # pad → set of track nets that want it

    for track in board.GetTracks():
        tnet = track.GetNet()
        if not tnet:
            continue
        tnetname = tnet.GetNetname()
        if not tnetname:
            continue

        for ep in [track.GetStart(), track.GetEnd()]:
            # Find pad within tolerance
            matched_pad = None
            best_dist = TOLERANCE + 1
            for (px, py), pad in pad_index.items():
                dx = abs(px - ep.x)
                dy = abs(py - ep.y)
                if dx <= TOLERANCE and dy <= TOLERANCE:
                    dist = dx + dy
                    if dist < best_dist:
                        best_dist = dist
                        matched_pad = pad

            if matched_pad is not None:
                pad_key = id(matched_pad)
                conflicts[pad_key].add(tnetname)

    # Apply nets — only assign if unambiguous (one track net per pad)
    for track in board.GetTracks():
        tnet = track.GetNet()
        if not tnet:
            continue
        tnetname = tnet.GetNetname()
        if not tnetname:
            continue

        for ep in [track.GetStart(), track.GetEnd()]:
            matched_pad = None
            best_dist = TOLERANCE + 1
            for (px, py), pad in pad_index.items():
                dx = abs(px - ep.x)
                dy = abs(py - ep.y)
                if dx <= TOLERANCE and dy <= TOLERANCE:
                    dist = dx + dy
                    if dist < best_dist:
                        best_dist = dist
                        matched_pad = pad

            if matched_pad is not None:
                pad_key = id(matched_pad)
                if len(conflicts[pad_key]) == 1:
                    # Unambiguous — assign
                    current = matched_pad.GetNet()
                    curr_name = current.GetNetname() if current else ''
                    if curr_name != tnetname:
                        net_obj = get_or_create_net(board, tnetname)
                        matched_pad.SetNet(net_obj)
                        changed += 1

    return changed, conflicts


def main():
    print("Loading board...")
    board = pcbnew.LoadBoard(BOARD_PATH)
    tracks = board.GetTracks()
    fps = board.GetFootprints()
    print(f"  {len(fps)} footprints, {len(tracks)} tracks")

    print("Fixing pad nets from track routing...")
    changed, conflicts = fix_from_tracks(board)
    print(f"  Changed: {changed} pads")

    ambiguous = {k: v for k, v in conflicts.items() if len(v) > 1}
    if ambiguous:
        print(f"  Ambiguous pads (multiple track nets): {len(ambiguous)}")

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

    print("\nComponents with unnetted pads:")
    for fp in board2.GetFootprints():
        pads = list(fp.Pads())
        unnetted = [p.GetNumber() for p in pads
                    if not p.GetNet() or not p.GetNet().GetNetname()]
        if unnetted:
            print(f"  {fp.GetReference():12s}: {unnetted}")


if __name__ == '__main__':
    main()
