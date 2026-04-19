#!/usr/bin/env python3
"""
Generate cm5-carrier.kicad_pcb skeleton.
- Board outline: 65 × 56mm (matches timonsku Minimal CM4 carrier size)
- 4-layer stackup: F.Cu / In1.Cu / In2.Cu / B.Cu (JLCPCB JLC04161H-7628)
- Mounting holes: M2.5 at corners
- No components placed yet — layout step follows
"""

import uuid

def uid():
    return str(uuid.uuid4())

# Board dimensions (mm)
W = 65.0   # width
H = 56.0   # height
CORNER_R = 1.0   # corner radius
MH_OFFSET = 3.5  # mounting hole inset from corner
MH_DRILL  = 2.5  # M2.5 hole

def xy(x, y):
    """Bare coordinate pair (PCB format — no xy wrapper)."""
    return f"{x:.3f} {y:.3f}"

def stroke(w=0.05):
    return f"""\t\t(stroke
\t\t\t(width {w})
\t\t\t(type default)
\t\t)"""


# ─── Stackup (4-layer JLCPCB JLC04161H-7628) ─────────────────────────────────
stackup = """\t\t(stackup
\t\t\t(layer "F.SilkS"
\t\t\t\t(type "Top Silk Screen")
\t\t\t)
\t\t\t(layer "F.Paste"
\t\t\t\t(type "Top Solder Paste")
\t\t\t)
\t\t\t(layer "F.Mask"
\t\t\t\t(type "Top Solder Mask")
\t\t\t\t(thickness 0.01)
\t\t\t)
\t\t\t(layer "F.Cu"
\t\t\t\t(type "copper")
\t\t\t\t(thickness 0.035)
\t\t\t)
\t\t\t(layer "dielectric 1"
\t\t\t\t(type "core")
\t\t\t\t(thickness 0.2)
\t\t\t\t(material "FR4")
\t\t\t\t(epsilon_r 4.5)
\t\t\t\t(loss_tangent 0.02)
\t\t\t)
\t\t\t(layer "In1.Cu"
\t\t\t\t(type "copper")
\t\t\t\t(thickness 0.0175)
\t\t\t)
\t\t\t(layer "dielectric 2"
\t\t\t\t(type "prepreg")
\t\t\t\t(thickness 1.065)
\t\t\t\t(material "FR4")
\t\t\t\t(epsilon_r 4.5)
\t\t\t\t(loss_tangent 0.02)
\t\t\t)
\t\t\t(layer "In2.Cu"
\t\t\t\t(type "copper")
\t\t\t\t(thickness 0.0175)
\t\t\t)
\t\t\t(layer "dielectric 3"
\t\t\t\t(type "core")
\t\t\t\t(thickness 0.2)
\t\t\t\t(material "FR4")
\t\t\t\t(epsilon_r 4.5)
\t\t\t\t(loss_tangent 0.02)
\t\t\t)
\t\t\t(layer "B.Cu"
\t\t\t\t(type "copper")
\t\t\t\t(thickness 0.035)
\t\t\t)
\t\t\t(layer "B.Mask"
\t\t\t\t(type "Bottom Solder Mask")
\t\t\t\t(thickness 0.01)
\t\t\t)
\t\t\t(layer "B.Paste"
\t\t\t\t(type "Bottom Solder Paste")
\t\t\t)
\t\t\t(layer "B.SilkS"
\t\t\t\t(type "Bottom Silk Screen")
\t\t\t)
\t\t\t(copper_finish "ENIG")
\t\t\t(dielectric_constraints no)
\t\t)"""

# ─── Net classes ──────────────────────────────────────────────────────────────
net_classes = """\t(net_class "Default" "All nets"
\t\t(clearance 0.15)
\t\t(trace_width 0.25)
\t\t(diff_pair_gap 0.15)
\t\t(diff_pair_width 0.15)
\t\t(via_drill 0.4)
\t\t(via_dia 0.8)
\t\t(uvia_drill 0.1)
\t\t(uvia_dia 0.3)
\t)
\t(net_class "Power" "5V/3.3V power nets"
\t\t(clearance 0.3)
\t\t(trace_width 0.5)
\t\t(diff_pair_gap 0.2)
\t\t(diff_pair_width 0.5)
\t\t(via_drill 0.4)
\t\t(via_dia 0.8)
\t\t(add_net "+5V_CM5")
\t\t(add_net "GND")
\t\t(add_net "VSYS")
\t\t(add_net "VBATT")
\t\t(add_net "VBUS")
\t)
\t(net_class "USB3" "USB 3.0 differential pairs (90 ohm)"
\t\t(clearance 0.15)
\t\t(trace_width 0.15)
\t\t(diff_pair_gap 0.15)
\t\t(diff_pair_width 0.15)
\t\t(via_drill 0.4)
\t\t(via_dia 0.8)
\t)
\t(net_class "HDMI" "HDMI differential pairs (100 ohm)"
\t\t(clearance 0.15)
\t\t(trace_width 0.18)
\t\t(diff_pair_gap 0.18)
\t\t(diff_pair_width 0.18)
\t\t(via_drill 0.4)
\t\t(via_dia 0.8)
\t)"""


# ─── Board outline (Edge.Cuts) ────────────────────────────────────────────────
def outline_lines():
    lines = []
    r = CORNER_R
    # Straight edges
    for sx, sy, ex, ey in [
        (r, 0, W-r, 0),
        (W, r, W, H-r),
        (W-r, H, r, H),
        (0, H-r, 0, r),
    ]:
        lines.append(f"""\t(gr_line
\t\t(start {sx:.3f} {sy:.3f})
\t\t(end {ex:.3f} {ey:.3f})
\t\t(stroke
\t\t\t(width 0.05)
\t\t\t(type default)
\t\t)
\t\t(layer "Edge.Cuts")
\t\t(uuid "{uid()}")
\t)""")

    # Corner arcs — start/mid/end
    # TL: start=(r,0), mid=(0.293r, 0.293r), end=(0,r)
    # TR: start=(W,r), mid=(W-0.293r, 0.293r), end=(W-r,0)  [wait, need CCW]
    # Actually using the standard rounded-rect arc: for KiCad arc, (start, mid, end) defines the arc.
    # TL corner: arc from (r, 0) through (0.293, 0.293) to (0, r) — 90° CCW
    # TR corner: arc from (W-r, 0) through (W-0.293, 0.293) to (W, r) — 90° CW
    # BR corner: arc from (W, H-r) through (W-0.293, H-0.293) to (W-r, H) — 90° CCW
    # BL corner: arc from (r, H) through (0.293, H-0.293) to (0, H-r) — 90° CW
    q = r * (1 - 0.707)  # offset from corner to arc midpoint ≈ 0.293*r
    arcs = [
        # TL: center (r,r)
        (r,   0,   q,   q,   0,   r),
        # TR: center (W-r,r)
        (W-r, 0,   W-q, q,   W,   r),
        # BR: center (W-r,H-r)
        (W,   H-r, W-q, H-q, W-r, H),
        # BL: center (r,H-r)
        (r,   H,   q,   H-q, 0,   H-r),
    ]
    for sx, sy, mx, my, ex, ey in arcs:
        lines.append(f"""\t(gr_arc
\t\t(start {sx:.3f} {sy:.3f})
\t\t(mid {mx:.3f} {my:.3f})
\t\t(end {ex:.3f} {ey:.3f})
\t\t(stroke
\t\t\t(width 0.05)
\t\t\t(type default)
\t\t)
\t\t(layer "Edge.Cuts")
\t\t(uuid "{uid()}")
\t)""")
    return "\n".join(lines)


def mounting_holes():
    holes = []
    positions = [
        (MH_OFFSET, MH_OFFSET),
        (W - MH_OFFSET, MH_OFFSET),
        (W - MH_OFFSET, H - MH_OFFSET),
        (MH_OFFSET, H - MH_OFFSET),
    ]
    for i, (x, y) in enumerate(positions, 1):
        holes.append(f"""\t(footprint "MountingHole:MountingHole_2.5mm_M2.5"
\t\t(layer "F.Cu")
\t\t(at {x:.3f} {y:.3f})
\t\t(uuid "{uid()}")
\t\t(property "Reference" "H{i}"
\t\t\t(at 0 -3.5 0)
\t\t\t(layer "F.SilkS")
\t\t\t(effects
\t\t\t\t(font
\t\t\t\t\t(size 1 1)
\t\t\t\t)
\t\t\t)
\t\t)
\t\t(property "Value" "M2.5"
\t\t\t(at 0 3.5 0)
\t\t\t(layer "F.Fab")
\t\t\t(effects
\t\t\t\t(font
\t\t\t\t\t(size 1 1)
\t\t\t\t)
\t\t\t)
\t\t)
\t\t(pad "" thru_hole circle
\t\t\t(at 0 0)
\t\t\t(size {MH_DRILL+0.5:.1f} {MH_DRILL+0.5:.1f})
\t\t\t(drill {MH_DRILL:.1f})
\t\t\t(layers "*.Cu" "*.Mask")
\t\t\t(uuid "{uid()}")
\t\t)
\t)""")
    return "\n".join(holes)


def gr_rect(x1, y1, x2, y2, layer, w=0.05):
    return f"""\t(gr_rect
\t\t(start {x1:.3f} {y1:.3f})
\t\t(end {x2:.3f} {y2:.3f})
\t\t(stroke
\t\t\t(width {w})
\t\t\t(type default)
\t\t)
\t\t(layer "{layer}")
\t\t(uuid "{uid()}")
\t)"""


def gr_text(text, x, y, layer, size=0.8):
    return f"""\t(gr_text "{text}"
\t\t(at {x:.3f} {y:.3f})
\t\t(layer "{layer}")
\t\t(effects
\t\t\t(font
\t\t\t\t(size {size} {size})
\t\t\t)
\t\t)
\t\t(uuid "{uid()}")
\t)"""


# ─── Courtyard / placement guides ─────────────────────────────────────────────
def placement_guides():
    guides = []
    cm5_x = (W - 40) / 2
    cm5_y = 3.0
    guides.append(gr_rect(cm5_x, cm5_y, cm5_x+40, cm5_y+5, "F.CrtYd"))
    guides.append(gr_text("CM5 Connector (Hirose DF40 100-pin)", W/2, cm5_y+2.5, "F.SilkS"))
    guides.append(gr_rect(2, 10, 28, 50, "F.Fab"))
    guides.append(gr_text("Power (BQ25895 + TPS61089)", 15, 12, "F.SilkS"))
    guides.append(gr_rect(32, 10, 63, 26, "F.Fab"))
    guides.append(gr_text("HDMI-A", 47.5, 13, "F.SilkS"))
    guides.append(gr_rect(32, 28, 63, 50, "F.Fab"))
    guides.append(gr_text("USB-A x2", 47.5, 31, "F.SilkS"))
    guides.append(gr_rect(2, 51, 16, 54, "F.Fab"))
    guides.append(gr_text("JST-PH LiPo", 9, 52.5, "F.SilkS"))
    return "\n".join(guides)


# ─── Assemble PCB ─────────────────────────────────────────────────────────────
pcb = f"""(kicad_pcb
\t(version 20241229)
\t(generator "pcbnew")
\t(generator_version "9.0")
\t(general
\t\t(thickness 1.6)
\t\t(legacy_teardrops no)
\t)
\t(paper "A4")
\t(title_block
\t\t(title "CM5 Carrier Board")
\t\t(date "2026-04-18")
\t\t(rev "1")
\t\t(company "Jens Lennartsson")
\t\t(comment 1 "65x56mm, 4-layer, M2.5 mounting holes")
\t\t(comment 2 "USB-C to BQ25895 charger to LiPo to TPS61089 to CM5")
\t)
\t(layers
\t\t(0 "F.Cu" signal)
\t\t(1 "In1.Cu" power)
\t\t(2 "In2.Cu" power)
\t\t(31 "B.Cu" signal)
\t\t(32 "B.Adhes" user "B.Adhesive")
\t\t(33 "F.Adhes" user "F.Adhesive")
\t\t(34 "B.Paste" user)
\t\t(35 "F.Paste" user)
\t\t(36 "B.SilkS" user "B.Silkscreen")
\t\t(37 "F.SilkS" user "F.Silkscreen")
\t\t(38 "B.Mask" user)
\t\t(39 "F.Mask" user)
\t\t(40 "Dwgs.User" user "User.Drawings")
\t\t(41 "Cmts.User" user "User.Comments")
\t\t(42 "Eco1.User" user "User.Eco1")
\t\t(43 "Eco2.User" user "User.Eco2")
\t\t(44 "Edge.Cuts" user)
\t\t(45 "Margin" user)
\t\t(46 "B.CrtYd" user "B.Courtyard")
\t\t(47 "F.CrtYd" user "F.Courtyard")
\t\t(48 "B.Fab" user "B.Fabrication")
\t\t(49 "F.Fab" user "F.Fabrication")
\t\t(50 "User.1" user)
\t\t(51 "User.2" user)
\t\t(52 "User.3" user)
\t\t(53 "User.4" user)
\t\t(54 "User.5" user)
\t\t(55 "User.6" user)
\t\t(56 "User.7" user)
\t\t(57 "User.8" user)
\t\t(58 "User.9" user)
\t)
\t(setup
{stackup}
\t\t(pad_to_mask_clearance 0)
\t\t(allow_soldermask_bridges_in_footprints no)
\t\t(pcbplotparams
\t\t\t(layerselection 0x00010fc_ffffffff)
\t\t\t(plot_on_all_layers_selection 0x0000000_00000000)
\t\t\t(disableapertmacros no)
\t\t\t(usegerberextensions no)
\t\t\t(usegerberattributes yes)
\t\t\t(usegerberadvancedattributes yes)
\t\t\t(creategerberjobfile yes)
\t\t\t(dashed_line_dash_ratio 12.000000)
\t\t\t(dashed_line_gap_ratio 3.000000)
\t\t\t(svgprecision 4)
\t\t\t(plotframeref no)
\t\t\t(viasonmask no)
\t\t\t(mode 1)
\t\t\t(useauxorigin no)
\t\t\t(hpglpennumber 1)
\t\t\t(hpglpenspeed 20)
\t\t\t(hpglpendiameter 15.000000)
\t\t\t(pdf_front_fp_property_popups yes)
\t\t\t(pdf_back_fp_property_popups yes)
\t\t\t(dxfpolygonmode yes)
\t\t\t(dxfimperialunits yes)
\t\t\t(dxfusepcbnewfont yes)
\t\t\t(psnegative no)
\t\t\t(psa4output no)
\t\t\t(plotreference yes)
\t\t\t(plotvalue yes)
\t\t\t(plotfptext yes)
\t\t\t(plotinvisibletext no)
\t\t\t(sketchpadsonfab no)
\t\t\t(subtractmaskfromsilk no)
\t\t\t(outputformat 1)
\t\t\t(mirror no)
\t\t\t(drillshape 0)
\t\t\t(scaleselection 1)
\t\t\t(outputdirectory "")
\t\t)
\t)
\t(net 0 "")
\t(net 1 "GND")
\t(net 2 "+5V_CM5")
\t(net 3 "VBUS")
\t(net 4 "VSYS")
\t(net 5 "VBATT")
\t(net 6 "I2C0_SDA")
\t(net 7 "I2C0_SCL")

{net_classes}

{outline_lines()}

{mounting_holes()}

{placement_guides()}

)
"""

out = "/mnt/storage/pcb/cm5-carrier/cm5-carrier.kicad_pcb"
with open(out, "w") as f:
    f.write(pcb)
print(f"Written {out} ({len(pcb):,} bytes)")
print(f"Board: {W}x{H}mm, 4-layer, {MH_DRILL}mm mounting holes")
