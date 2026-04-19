#!/usr/bin/env python3
"""
Generate component footprints and add them to cm5-carrier.kicad_pcb.

Layout (all coordinates in mm, origin top-left):
  CM5:   (32.5, 8.0)   — 100-pin, 22mm wide
  D1:    (13.0, 13.0)  — status LED
  J_USB: (7.5,  20.0)  — USB-C input
  U1:    (18.0, 20.0)  — BQ25895RTW WQFN-24
  L1:    (27.0, 20.0)  — charger inductor 4.7µH (4×4mm 2-pad)
  C1-C4: x=20-26, y=26 — U1 decoupling
  R1-R4: x=28,  y=26-30.5 — BQ25895 feedback
  U2:    (18.0, 36.0)  — TPS61089 VSON-10
  L2:    (25.0, 36.0)  — boost inductor 2.2µH (3×3mm 2-pad)
  C5-C7: x=18-22, y=40 — U2 decoupling
  C8-C10: x=18-22, y=42 — extra VBAT caps
  R5-R8: x=29,  y=35-39.5 — TPS61089 feedback
  J_BAT: (7.0,  46.0)  — JST-PH battery

Component courtyard half-extents verified before placement:
  WQFN-24:    ±2.62mm
  VSON-10:    ±1.75mm × ±1.25mm
  USB-C HRO:  ±5.32mm × (-5.27 to +4.15mm)
  0402:       ±0.75mm × ±0.35mm
  L1 4-pad:   ±2.9mm  × ±1.5mm
  L2 3-pad:   ±2.2mm  × ±1.1mm
  JST-PH:     (-2.45 to +4.45mm) × (-1.85 to +6.75mm)
  LED 0603:   ±1.48mm × ±0.73mm
"""

import uuid, re

def uid():
    return str(uuid.uuid4())


# ─── Bracket-counted block extractor ──────────────────────────────────────────
def extract_blocks(raw, tags=('pad', 'fp_line', 'fp_arc', 'fp_circle', 'fp_rect', 'fp_poly')):
    """Extract complete S-expression blocks matching any of the given tags."""
    pattern = r'\n[\t ]+\((?:' + '|'.join(tags) + r')\b'
    result = ''
    for m in re.finditer(pattern, raw):
        start = m.start()
        depth = 0
        end = start
        for i, c in enumerate(raw[start:]):
            if c == '(':
                depth += 1
            elif c == ')':
                depth -= 1
                if depth == 0:
                    end = start + i + 1
                    break
        result += '\n' + raw[start:end]
    return result


# ─── Generic footprint loader from .kicad_mod ─────────────────────────────────
def embed_fp(path, ref, value, x, y, rotation=0, ref_at=(0, -3), val_at=(0, 3)):
    """Load a .kicad_mod and embed it in the PCB at (x, y)."""
    raw = open(path).read().strip()
    m = re.match(r'\((?:footprint|module)\s+"?([^"\s)]+)"?', raw)
    if not m:
        raise ValueError(f"Cannot parse footprint in {path}")
    fp_name = m.group(1)
    inner = extract_blocks(raw)
    rot_str = f' {rotation}' if rotation else ''
    return f"""\t(footprint "{fp_name}"
\t\t(layer "F.Cu")
\t\t(uuid "{uid()}")
\t\t(at {x:.3f} {y:.3f}{rot_str})
\t\t(property "Reference" "{ref}"
\t\t\t(at {ref_at[0]} {ref_at[1]} 0)
\t\t\t(layer "F.SilkS")
\t\t\t(effects (font (size 0.8 0.8)))
\t\t\t(uuid "{uid()}")
\t\t)
\t\t(property "Value" "{value}"
\t\t\t(at {val_at[0]} {val_at[1]} 0)
\t\t\t(layer "F.Fab")
\t\t\t(effects (font (size 0.8 0.8)))
\t\t\t(uuid "{uid()}")
\t\t){inner}
\t)"""


# ─── Generic 2-pad SMD (caps, resistors, inductors) ───────────────────────────
def smd_2pad(ref, value, x, y, pw, ph, pitch):
    """2-pad SMD component. Courtyard: x=±(pitch/2+pw/2+0.1), y=±(ph/2+0.1)."""
    cx = pitch / 2 + pw / 2 + 0.1
    cy = ph / 2 + 0.1
    ref_y = -(cy + 0.5)
    val_y = cy + 0.5
    return f"""\t(footprint "SMD_{ref}_GENERATED"
\t\t(layer "F.Cu")
\t\t(uuid "{uid()}")
\t\t(at {x:.3f} {y:.3f})
\t\t(property "Reference" "{ref}"
\t\t\t(at 0 {ref_y:.2f} 0) (layer "F.SilkS")
\t\t\t(effects (font (size 0.6 0.6)))
\t\t\t(uuid "{uid()}")
\t\t)
\t\t(property "Value" "{value}"
\t\t\t(at 0 {val_y:.2f} 0) (layer "F.Fab")
\t\t\t(effects (font (size 0.6 0.6)))
\t\t\t(uuid "{uid()}")
\t\t)
\t\t(pad "1" smd rect
\t\t\t(at {-pitch/2:.3f} 0)
\t\t\t(size {pw} {ph})
\t\t\t(layers "F.Cu" "F.Paste" "F.Mask")
\t\t\t(uuid "{uid()}")
\t\t)
\t\t(pad "2" smd rect
\t\t\t(at {pitch/2:.3f} 0)
\t\t\t(size {pw} {ph})
\t\t\t(layers "F.Cu" "F.Paste" "F.Mask")
\t\t\t(uuid "{uid()}")
\t\t)
\t\t(fp_rect
\t\t\t(start {-cx:.3f} {-cy:.3f})
\t\t\t(end {cx:.3f} {cy:.3f})
\t\t\t(stroke (width 0.05) (type default))
\t\t\t(layer "F.CrtYd")
\t\t\t(uuid "{uid()}")
\t\t)
\t)"""


# ─── CM5 connector — Hirose DF40HC(3.0)-100DS-0.4V ────────────────────────────
def gen_cm5_connector(x, y):
    PAD_W = 0.25
    PAD_H = 1.6
    PITCH = 0.4
    ROW_SPACING = 2.8
    N_PINS = 50
    BODY_W = N_PINS * PITCH + 2.0  # 22mm
    BODY_H = ROW_SPACING + 2.0     # 4.8mm
    cyd_x = BODY_W / 2 + 0.25
    cyd_y = BODY_H / 2 + 0.25

    pads = []
    for i in range(N_PINS):
        px = (i - (N_PINS - 1) / 2.0) * PITCH
        pads.append(f"""\t\t(pad "{i+1}" smd rect
\t\t\t(at {px:.4f} {ROW_SPACING/2:.4f})
\t\t\t(size {PAD_W} {PAD_H})
\t\t\t(layers "F.Cu" "F.Paste" "F.Mask")
\t\t\t(uuid "{uid()}")
\t\t)""")
        pads.append(f"""\t\t(pad "{51+i}" smd rect
\t\t\t(at {px:.4f} {-ROW_SPACING/2:.4f})
\t\t\t(size {PAD_W} {PAD_H})
\t\t\t(layers "F.Cu" "F.Paste" "F.Mask")
\t\t\t(uuid "{uid()}")
\t\t)""")

    graphics = f"""\t\t(fp_rect
\t\t\t(start {-cyd_x:.3f} {-cyd_y:.3f})
\t\t\t(end {cyd_x:.3f} {cyd_y:.3f})
\t\t\t(stroke (width 0.05) (type default))
\t\t\t(layer "F.CrtYd")
\t\t\t(uuid "{uid()}")
\t\t)
\t\t(fp_rect
\t\t\t(start {-BODY_W/2:.3f} {-BODY_H/2:.3f})
\t\t\t(end {BODY_W/2:.3f} {BODY_H/2:.3f})
\t\t\t(stroke (width 0.1) (type default))
\t\t\t(layer "F.Fab")
\t\t\t(uuid "{uid()}")
\t\t)"""

    return f"""\t(footprint "Hirose_DF40HC-100DS-0.4V_GENERATED"
\t\t(layer "F.Cu")
\t\t(uuid "{uid()}")
\t\t(at {x:.3f} {y:.3f})
\t\t(descr "Hirose DF40HC(3.0)-100DS-0.4V — VERIFY DIMS AGAINST DATASHEET")
\t\t(property "Reference" "J_CM5"
\t\t\t(at 0 -5 0)
\t\t\t(layer "F.SilkS")
\t\t\t(effects (font (size 1 1)))
\t\t\t(uuid "{uid()}")
\t\t)
\t\t(property "Value" "DF40HC(3.0)-100DS-0.4V"
\t\t\t(at 0 5 0)
\t\t\t(layer "F.Fab")
\t\t\t(effects (font (size 1 1)))
\t\t\t(uuid "{uid()}")
\t\t)
{chr(10).join(pads)}
{graphics}
\t)"""


# ─── TPS61089 VSON-10 ─────────────────────────────────────────────────────────
def gen_tps61089(x, y):
    PAD_W = 0.3
    PAD_H = 0.7
    BODY_W, BODY_H = 3.0, 2.0
    EP_W, EP_H = 2.2, 1.1
    cyd = 0.25

    pads = []
    ys = [1.0, 0.5, 0.0, -0.5, -1.0]
    for i, py in enumerate(ys):
        pads.append(f"""\t\t(pad "{i+1}" smd rect
\t\t\t(at -1.425 {py:.3f})
\t\t\t(size {PAD_W} {PAD_H})
\t\t\t(layers "F.Cu" "F.Paste" "F.Mask")
\t\t\t(uuid "{uid()}")
\t\t)""")
        pads.append(f"""\t\t(pad "{10-i}" smd rect
\t\t\t(at 1.425 {py:.3f})
\t\t\t(size {PAD_W} {PAD_H})
\t\t\t(layers "F.Cu" "F.Paste" "F.Mask")
\t\t\t(uuid "{uid()}")
\t\t)""")
    pads.append(f"""\t\t(pad "11" smd rect
\t\t\t(at 0 0)
\t\t\t(size {EP_W} {EP_H})
\t\t\t(layers "F.Cu" "F.Paste" "F.Mask")
\t\t\t(uuid "{uid()}")
\t\t)""")

    cx = BODY_W / 2 + cyd
    cy = BODY_H / 2 + cyd
    graphics = f"""\t\t(fp_rect
\t\t\t(start {-cx:.3f} {-cy:.3f})
\t\t\t(end {cx:.3f} {cy:.3f})
\t\t\t(stroke (width 0.05) (type default))
\t\t\t(layer "F.CrtYd")
\t\t\t(uuid "{uid()}")
\t\t)
\t\t(fp_rect
\t\t\t(start {-BODY_W/2:.3f} {-BODY_H/2:.3f})
\t\t\t(end {BODY_W/2:.3f} {BODY_H/2:.3f})
\t\t\t(stroke (width 0.1) (type default))
\t\t\t(layer "F.Fab")
\t\t\t(uuid "{uid()}")
\t\t)"""

    return f"""\t(footprint "TPS61089_VSON-10_3x2mm_GENERATED"
\t\t(layer "F.Cu")
\t\t(uuid "{uid()}")
\t\t(at {x:.3f} {y:.3f})
\t\t(property "Reference" "U2"
\t\t\t(at 0 -2 0)
\t\t\t(layer "F.SilkS")
\t\t\t(effects (font (size 0.8 0.8)))
\t\t\t(uuid "{uid()}")
\t\t)
\t\t(property "Value" "TPS61089"
\t\t\t(at 0 2 0)
\t\t\t(layer "F.Fab")
\t\t\t(effects (font (size 0.8 0.8)))
\t\t\t(uuid "{uid()}")
\t\t)
{chr(10).join(pads)}
{graphics}
\t)"""


# ─── Component list ────────────────────────────────────────────────────────────
FP = '/mnt/storage/pcb/cm5-carrier/footprints'
components = []

# CM5 connector — top center
components.append(gen_cm5_connector(32.5, 8.0))

# Status LED — above USB-C
components.append(embed_fp(f'{FP}/LED_0603_1608Metric.kicad_mod',
    'D1', 'LED_PWR', 13.0, 13.0, ref_at=(0, -1.5), val_at=(0, 1.5)))

# USB-C input — left power region
usbc_raw = open(f'{FP}/USB_C.kicad_mod').read()
components.append(f"""\t(footprint "Connector_USB:USB_C_Receptacle_HRO_TYPE-C-31-M-12"
\t\t(layer "F.Cu")
\t\t(uuid "{uid()}")
\t\t(at 7.500 20.000)
\t\t(property "Reference" "J_USB"
\t\t\t(at 0 -6 0) (layer "F.SilkS")
\t\t\t(effects (font (size 0.8 0.8)))
\t\t\t(uuid "{uid()}")
\t\t)
\t\t(property "Value" "USB-C 5V Input"
\t\t\t(at 0 5 0) (layer "F.Fab")
\t\t\t(effects (font (size 0.8 0.8)))
\t\t\t(uuid "{uid()}")
\t\t){extract_blocks(usbc_raw)}
\t)""")

# BQ25895RTW — WQFN-24  (courtyard ±2.62mm)
wqfn_raw = open(f'{FP}/WQFN24.kicad_mod').read()
components.append(f"""\t(footprint "Package_DFN_QFN:WQFN-24-1EP_4x4mm_P0.5mm"
\t\t(layer "F.Cu")
\t\t(uuid "{uid()}")
\t\t(at 18.000 20.000)
\t\t(property "Reference" "U1"
\t\t\t(at 0 -3.5 0) (layer "F.SilkS")
\t\t\t(effects (font (size 0.8 0.8)))
\t\t\t(uuid "{uid()}")
\t\t)
\t\t(property "Value" "BQ25895RTW"
\t\t\t(at 0 3.5 0) (layer "F.Fab")
\t\t\t(effects (font (size 0.8 0.8)))
\t\t\t(uuid "{uid()}")
\t\t){extract_blocks(wqfn_raw)}
\t)""")

# Charger inductor L1 — 4×4mm 2-pad, right of U1
# Courtyard: x=±2.9mm, y=±1.5mm — verified no overlap
components.append(smd_2pad('L1', '4.7uH/3A', 27.0, 20.0, pw=1.4, ph=2.8, pitch=4.2))

# TPS61089 boost converter — VSON-10  (courtyard ±1.75×1.25mm)
components.append(gen_tps61089(18.0, 36.0))

# Boost inductor L2 — 3×3mm 2-pad, right of U2
# Courtyard: x=±2.2mm, y=±1.1mm
components.append(smd_2pad('L2', '2.2uH/2A', 25.0, 36.0, pw=1.0, ph=2.0, pitch=3.2))

# Decoupling caps for U1 — row below L1 (y=26, safe gap from U1/L1)
for ref, val, cx, cy in [
    ('C1', '100nF', 20.0, 26.0),
    ('C2', '100nF', 22.0, 26.0),
    ('C3', '10uF',  24.0, 26.0),
    ('C4', '4.7uF', 26.0, 26.0),
]:
    components.append(smd_2pad(ref, val, cx, cy, pw=0.5, ph=0.5, pitch=0.8))

# Feedback resistors for BQ25895 — vertical column right of caps
for ref, val, rx, ry in [
    ('R1', '100k', 28.0, 26.0),
    ('R2', '10k',  28.0, 27.5),
    ('R3', '10k',  28.0, 29.0),
    ('R4', '4.7k', 28.0, 30.5),
]:
    components.append(smd_2pad(ref, val, rx, ry, pw=0.5, ph=0.5, pitch=0.8))

# Decoupling caps for U2 — below U2 (y=40, 42)
for ref, val, cx, cy in [
    ('C5',  '100nF', 18.0, 40.0),
    ('C6',  '100nF', 20.0, 40.0),
    ('C7',  '47uF',  22.0, 40.0),
    ('C8',  '10uF',  18.0, 42.0),
    ('C9',  '100nF', 20.0, 42.0),
    ('C10', '100nF', 22.0, 42.0),
]:
    components.append(smd_2pad(ref, val, cx, cy, pw=0.5, ph=0.5, pitch=0.8))

# Feedback resistors for TPS61089 — right of L2 (x=29, clear of L2 courtyard at x=27.2)
for ref, val, rx, ry in [
    ('R5', '47k',  29.0, 35.0),
    ('R6', '100k', 29.0, 36.5),
    ('R7', '10k',  29.0, 38.0),
    ('R8', '10k',  29.0, 39.5),
]:
    components.append(smd_2pad(ref, val, rx, ry, pw=0.5, ph=0.5, pitch=0.8))

# JST-PH battery connector — bottom left
# CrtYd: (-2.45 to +4.45, -1.85 to +6.75) → at y=46: extends to y=52.75 ✓
jst_raw = open(f'{FP}/JST_PH_S2B-PH-K_1x02_P2.00mm_Horizontal.kicad_mod').read()
components.append(f"""\t(footprint "Connector_JST:JST_PH_S2B-PH-K_1x02_P2.00mm_Horizontal"
\t\t(layer "F.Cu")
\t\t(uuid "{uid()}")
\t\t(at 7.000 46.000)
\t\t(property "Reference" "J_BAT"
\t\t\t(at 0 -3 0) (layer "F.SilkS")
\t\t\t(effects (font (size 0.8 0.8)))
\t\t\t(uuid "{uid()}")
\t\t)
\t\t(property "Value" "LiPo JST-PH"
\t\t\t(at 0 3 0) (layer "F.Fab")
\t\t\t(effects (font (size 0.8 0.8)))
\t\t\t(uuid "{uid()}")
\t\t){extract_blocks(jst_raw)}
\t)""")


# ─── Write to PCB ─────────────────────────────────────────────────────────────
pcb_path = '/mnt/storage/pcb/cm5-carrier/cm5-carrier.kicad_pcb'
pcb = open(pcb_path).read()
insert_pos = pcb.rfind('\n)')
new_pcb = pcb[:insert_pos] + '\n\n' + '\n\n'.join(components) + '\n' + pcb[insert_pos:]

with open(pcb_path, 'w') as f:
    f.write(new_pcb)

print(f"Added {len(components)} components to {pcb_path}")
print(f"PCB size: {len(new_pcb):,} bytes")
print()
print("Placement summary:")
print("  J_CM5   (32.5,  8.0)  DF40HC 100-pin [VERIFY DIMS!]")
print("  D1      (13.0, 13.0)  LED 0603")
print("  J_USB   ( 7.5, 20.0)  USB-C HRO (courtyard x=2.18-12.82)")
print("  U1      (18.0, 20.0)  BQ25895RTW WQFN-24 (cyd ±2.62)")
print("  L1      (27.0, 20.0)  4.7µH inductor 4×4mm (cyd ±2.9×1.5)")
print("  C1-C4   y=26          U1 decoupling caps")
print("  R1-R4   x=28, y=26-30 BQ25895 feedback")
print("  U2      (18.0, 36.0)  TPS61089 VSON-10 (cyd ±1.75×1.25)")
print("  L2      (25.0, 36.0)  2.2µH inductor 3×3mm (cyd ±2.2×1.1)")
print("  C5-C10  y=40,42       U2 decoupling caps")
print("  R5-R8   x=29, y=35-39 TPS61089 feedback")
print("  J_BAT   ( 7.0, 46.0)  JST-PH (cyd x=4.55-11.45, y=44.15-52.75)")
