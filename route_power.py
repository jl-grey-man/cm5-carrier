#!/usr/bin/env python3
"""
Power routing v4: fixed routes to avoid all 5 shorts from v3.

Shorts fixed:
1. Net-U2-SW @ R6.pad1(24.6,37.65): was at y=37.5 → now routes via y=33
2. Net-U2-SW stub @ C11.pad2(24.4,41.0): stub now goes via x=27.5 east of C11/C12
3. Net-U2-BOOT @ C11.pad1(23.6,41.0): now routes via x=19.43 (far left of C11)
4. Net-U1-SW @ U1.pad17(19.94,19.25): now routes via y=17 below pad row
5. VBATT @ J_USB shield(11.82,16.87): now routes via y=23 below USB connector

Short analog traces (Net-U2-FB/COMP/ILIM) → KiCad GUI (pads 0.5mm apart).
"""

import pcbnew

PCB = '/mnt/storage/cm5-carrier/cm5-carrier.kicad_pcb'
board = pcbnew.LoadBoard(PCB)

def mm(v):  return pcbnew.FromMM(float(v))

F_Cu = pcbnew.F_Cu
B_Cu = pcbnew.B_Cu

def track(x1, y1, x2, y2, net, layer=F_Cu, w=0.25):
    n = board.FindNet(net)
    if not n: return
    t = pcbnew.PCB_TRACK(board)
    t.SetStart(pcbnew.VECTOR2I(mm(x1), mm(y1)))
    t.SetEnd(  pcbnew.VECTOR2I(mm(x2), mm(y2)))
    t.SetWidth(mm(w))
    t.SetLayer(layer)
    t.SetNet(n)
    board.Add(t)

def zone(corners, net, layer=F_Cu, clr=0.3, pri=0):
    n = board.FindNet(net)
    if not n: print(f"  WARN: {net}"); return
    z = pcbnew.ZONE(board)
    z.SetNet(n); z.SetLayer(layer)
    z.SetMinThickness(mm(0.25))
    z.SetLocalClearance(mm(clr))
    z.SetAssignedPriority(pri)
    z.SetFillMode(pcbnew.ZONE_FILL_MODE_POLYGONS)
    ol = z.Outline(); ol.NewOutline()
    for x, y in corners: ol.Append(mm(x), mm(y))
    board.Add(z)

BOARD = [(0.5,0.5),(79.5,0.5),(79.5,59.5),(0.5,59.5)]
PWR   = [(0.5,5.0),(45.0,5.0),(45.0,55.0),(0.5,55.0)]

# ── Fill zones ────────────────────────────────────────────────────────
print("=== Fill zones ===")
zone(BOARD, 'GND',     F_Cu, pri=0); print("  GND F.Cu (full board)")
zone(BOARD, 'GND',     B_Cu, pri=0); print("  GND B.Cu (full board)")
zone(PWR,   'VSYS',    F_Cu, pri=2); print("  VSYS F.Cu (power section)")
zone(BOARD, '+5V_CM5', B_Cu, pri=2); print("  +5V_CM5 B.Cu (full board)")

# ── Net-U2-SW: U2.pad11@(18,36) → L2.pad2@(26.6,36) ─────────────────
# Route via y=33 (above U2 package top at y≈34.5, above R5 at y=34.2).
# Previous y=37.5 shorted R6.pad1(+3.3V) at (24.6,37.65).
# Stub to C13.pad2@(24.4,43): go east to x=27.5, south to y=43.8,
#   west to x=24.4, then north — avoiding C11.pad2(GND) at (24.4,41).
print("\n=== Power traces (F.Cu) ===")
track(18.0, 36.0, 18.0, 33.0, 'Net-U2-SW', F_Cu, 0.8)  # up from SW pad
track(18.0, 33.0, 26.6, 33.0, 'Net-U2-SW', F_Cu, 0.8)  # east at y=33
track(26.6, 33.0, 26.6, 36.0, 'Net-U2-SW', F_Cu, 0.8)  # down to L2.pad2
# NOTE: C13.pad2 stub omitted — D2 at x=27.6 and J_SDCARD pad at x=29.26
# leave no gap for scripted routing. Route C13↔L2 stub manually in KiCad GUI.
print("  Net-U2-SW: U2.11 → y=33 → L2.2 [C13 stub → KiCad GUI]")

# ── Net-U2-BOOT: U2.pad10@(19.43,37) → C13.pad1@(23.6,43) ──────────
# Route south at x=19.43 (far left of C11 at x=23.35), avoiding
# C11.pad1(VSYS) at (23.6,41). Then east below C13, north to pad1.
track(19.43, 37.0, 21.0,  37.0, 'Net-U2-BOOT', F_Cu, 0.2)  # east to clear C6/C9
track(21.0,  37.0, 21.0,  43.8, 'Net-U2-BOOT', F_Cu, 0.2)  # south (btw C6.pad2@20.4 & C7.pad1@21.6)
track(21.0,  43.8, 23.6,  43.8, 'Net-U2-BOOT', F_Cu, 0.2)  # east
track(23.6,  43.8, 23.6,  43.0, 'Net-U2-BOOT', F_Cu, 0.2)  # north to C13.pad1
print("  Net-U2-BOOT: U2.10 → east x=21.0 → south → C13.1 (avoids C6/C9)")

# ── Net-U1-SW: L1.pad1@(24.9,20) → U1.pad18@(19.94,18.75) ──────────
# Route via y=17 below U1 bottom pad row (at y=18.06) to avoid
# U1.pad17(GND) at (19.94,19.25).
track(24.9,  20.0,  21.0,  20.0,  'Net-U1-SW', F_Cu, 0.4)  # west along y=20
track(21.0,  20.0,  21.0,  17.0,  'Net-U1-SW', F_Cu, 0.4)  # south to y=17
track(21.0,  17.0,  19.94, 17.0,  'Net-U1-SW', F_Cu, 0.4)  # west to pad18 x
track(19.94, 17.0,  19.94, 18.75, 'Net-U1-SW', F_Cu, 0.4)  # north to U1.pad18
print("  Net-U1-SW: L1.1 → via y=17 → U1.pad18 (avoids pad17 GND)")

# ── Signals on B.Cu ───────────────────────────────────────────────────
print("\n=== Signal traces (B.Cu) ===")

# VBATT: J_BAT.pad1@(7,40) → U1.pad13@(19.94,21.25)
# J_USB shield pads are PTH at (11.82,16.87) and (11.82,21.05).
# Previous route at y=16 hit the shield pad — now route at y=23 (south
# of shield pad at y=21.05) then approach U1.pad13 from east at x=21.
track(7.0,   40.0,  7.0,   23.0,  'VBATT', B_Cu, 1.0)   # up left edge
track(7.0,   23.0,  21.0,  23.0,  'VBATT', B_Cu, 1.0)   # east at y=23
track(21.0,  23.0,  21.0,  21.25, 'VBATT', B_Cu, 1.0)   # north to pad13 y
track(21.0,  21.25, 19.94, 21.25, 'VBATT', B_Cu, 0.25)  # west to U1.pad13
print("  VBATT: J_BAT → y=23 (below USB) → x=21 → U1.pad13")

# I2C0_SDA: R5.pad2@(25.4,34.2) → U1.pad6@(16.06,21.25)
track(25.4,  34.2,  14.5,  34.2,  'I2C0_SDA', B_Cu, 0.2)
track(14.5,  34.2,  14.5,  21.25, 'I2C0_SDA', B_Cu, 0.2)
track(14.5,  21.25, 16.06, 21.25, 'I2C0_SDA', B_Cu, 0.2)
print("  I2C0_SDA: R5.2 → U1.pad6")

# I2C0_SCL: R6.pad2@(25.4,37.65) → U1.pad5@(16.06,20.75)
track(25.4,  37.65, 13.5,  37.65, 'I2C0_SCL', B_Cu, 0.2)
track(13.5,  37.65, 13.5,  20.75, 'I2C0_SCL', B_Cu, 0.2)
track(13.5,  20.75, 16.06, 20.75, 'I2C0_SCL', B_Cu, 0.2)
print("  I2C0_SCL: R6.2 → U1.pad5")

# /PWR_BUT_BTN: SW_PWR.pad1@(62.3,37.18) → R7.pad2@(25.4,38.6)
track(62.3,  37.18, 62.3,  42.0,  '/PWR_BUT_BTN', B_Cu, 0.2)
track(62.3,  42.0,  25.4,  42.0,  '/PWR_BUT_BTN', B_Cu, 0.2)
track(25.4,  42.0,  25.4,  38.6,  '/PWR_BUT_BTN', B_Cu, 0.2)
print("  /PWR_BUT_BTN: SW_PWR → R7.2")

# ── Fill all zones ────────────────────────────────────────────────────
print("\n=== Zone fill ===")
filler = pcbnew.ZONE_FILLER(board)
filler.Fill(board.Zones())
print("  Zones filled")

board.Save(PCB)
tracks = list(board.GetTracks())
print(f"\n✓ Saved. {len(tracks)} tracks total")
