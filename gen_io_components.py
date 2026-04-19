#!/usr/bin/env python3
"""
Phase 3 — Add IO components and expand board to 80×60mm.

New board: 80mm wide × 60mm tall (was 65×56mm).
The extra space accommodates the 2×20 GPIO header on the right side.

New components added:
  J_GPIO   (70.0,  4.0)  — 2×20 GPIO header (right side, vertical)
  J_HDMI   (15.0, 55.0)  — HDMI-A horizontal, bottom-left edge
  J_SDCARD (36.0, 36.0)  — microSD slot (Molex 104031-0811)
  J_USB1   (34.0, 46.5)  — USB-A horizontal (Molex 67643), bottom-center
  J_USB2   (52.0, 46.5)  — USB-A horizontal (Molex 67643), bottom-right
  SW_RST   (58.0, 38.0)  — Reset button (nRESET via RUN pin)
  SW_PWR   (64.0, 38.0)  — Power button (PWR_BTN)
"""

import uuid, re, math

LIB = '/usr/share/kicad/footprints'
PCB_PATH = '/mnt/storage/cm5-carrier/cm5-carrier.kicad_pcb'


def uid():
    return str(uuid.uuid4())


def extract_pads(raw):
    """Extract pad, fp_line, fp_arc, fp_circle, fp_rect, fp_poly blocks.
    Intentionally excludes fp_text (reference/value handled by embed_fp).
    """
    tags = ('pad', 'fp_line', 'fp_arc', 'fp_circle', 'fp_rect', 'fp_poly')
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


def embed_fp(fp_path, ref, value, x, y, rotation=0,
             ref_at=(0, -3), val_at=(0, 3), layer='F.Cu'):
    """Embed a .kicad_mod footprint at (x, y) with given rotation."""
    raw = open(fp_path).read().strip()
    m = re.match(r'\((?:footprint|module)\s+"?([^"\s)]+)"?', raw)
    fp_name = m.group(1) if m else 'UNKNOWN'
    inner = extract_pads(raw)
    rot_str = f' {rotation}' if rotation else ''
    return (
        f'\t(footprint "{fp_name}"\n'
        f'\t\t(layer "{layer}")\n'
        f'\t\t(uuid "{uid()}")\n'
        f'\t\t(at {x:.3f} {y:.3f}{rot_str})\n'
        f'\t\t(property "Reference" "{ref}"\n'
        f'\t\t\t(at {ref_at[0]} {ref_at[1]} 0)\n'
        f'\t\t\t(layer "F.SilkS")\n'
        f'\t\t\t(effects (font (size 0.8 0.8)))\n'
        f'\t\t\t(uuid "{uid()}")\n'
        f'\t\t)\n'
        f'\t\t(property "Value" "{value}"\n'
        f'\t\t\t(at {val_at[0]} {val_at[1]} 0)\n'
        f'\t\t\t(layer "F.Fab")\n'
        f'\t\t\t(effects (font (size 0.8 0.8)))\n'
        f'\t\t\t(uuid "{uid()}")\n'
        f'\t\t){inner}\n'
        f'\t)'
    )


# ─── New edge cuts (80×60mm, r=1mm rounded corners) ───────────────────────────
W, H, R = 80.0, 60.0, 1.0

def edge_line(x1, y1, x2, y2):
    return (
        f'\t(gr_line\n'
        f'\t\t(start {x1:.3f} {y1:.3f})\n'
        f'\t\t(end {x2:.3f} {y2:.3f})\n'
        f'\t\t(stroke\n'
        f'\t\t\t(width 0.05)\n'
        f'\t\t\t(type default)\n'
        f'\t\t)\n'
        f'\t\t(layer "Edge.Cuts")\n'
        f'\t\t(uuid "{uid()}")\n'
        f'\t)'
    )

def edge_arc(sx, sy, mx, my, ex, ey):
    return (
        f'\t(gr_arc\n'
        f'\t\t(start {sx:.3f} {sy:.3f})\n'
        f'\t\t(mid {mx:.3f} {my:.3f})\n'
        f'\t\t(end {ex:.3f} {ey:.3f})\n'
        f'\t\t(stroke\n'
        f'\t\t\t(width 0.05)\n'
        f'\t\t\t(type default)\n'
        f'\t\t)\n'
        f'\t\t(layer "Edge.Cuts")\n'
        f'\t\t(uuid "{uid()}")\n'
        f'\t)'
    )

c = R * (1 - 1/math.sqrt(2))  # ≈ 0.293mm (arc midpoint offset)

NEW_EDGES = [
    edge_line(R, 0, W-R, 0),
    edge_line(W, R, W, H-R),
    edge_line(W-R, H, R, H),
    edge_line(0, H-R, 0, R),
    edge_arc(R, 0, c, c, 0, R),
    edge_arc(W-R, 0, W-c, c, W, R),
    edge_arc(W, H-R, W-c, H-c, W-R, H),
    edge_arc(R, H, c, H-c, 0, H-R),
]


def mounting_hole(ref, x, y):
    return (
        f'\t(footprint "MountingHole:MountingHole_2.5mm_M2.5"\n'
        f'\t\t(layer "F.Cu")\n'
        f'\t\t(uuid "{uid()}")\n'
        f'\t\t(at {x:.3f} {y:.3f})\n'
        f'\t\t(property "Reference" "{ref}"\n'
        f'\t\t\t(at 0 -3.5 0) (layer "F.SilkS")\n'
        f'\t\t\t(effects (font (size 0.8 0.8)))\n'
        f'\t\t\t(uuid "{uid()}")\n'
        f'\t\t)\n'
        f'\t\t(property "Value" "M2.5"\n'
        f'\t\t\t(at 0 3.5 0) (layer "F.Fab")\n'
        f'\t\t\t(effects (font (size 0.8 0.8)))\n'
        f'\t\t\t(uuid "{uid()}")\n'
        f'\t\t)\n'
        f'\t\t(pad "" np_thru_hole circle\n'
        f'\t\t\t(at 0 0) (size 2.5 2.5) (drill 2.5)\n'
        f'\t\t\t(layers "*.Cu" "*.Mask")\n'
        f'\t\t\t(uuid "{uid()}")\n'
        f'\t\t)\n'
        f'\t\t(fp_circle\n'
        f'\t\t\t(center 0 0) (end 2.7 0)\n'
        f'\t\t\t(stroke (width 0.15) (type default))\n'
        f'\t\t\t(layer "F.CrtYd") (uuid "{uid()}")\n'
        f'\t\t)\n'
        f'\t)'
    )


# ─── IO Components ─────────────────────────────────────────────────────────────
components = [
    # GPIO 2×20 header — right side vertical
    # x=68.2..74.3, y=1.6..54.6 ✓
    embed_fp(
        f'{LIB}/Connector_PinHeader_2.54mm.pretty/PinHeader_2x20_P2.54mm_Vertical.kicad_mod',
        'J_GPIO', 'GPIO_2x20', 70.0, 4.0,
        ref_at=(-4, 0), val_at=(6, 0)
    ),
    # HDMI-A horizontal — bottom-left, opening at board edge y=60
    # x=5.8..24.2, y=48.5..60.0 ✓
    embed_fp(
        f'{LIB}/Connector_Video.pretty/HDMI_A_Amphenol_10029449-x01xLF_Horizontal.kicad_mod',
        'J_HDMI', 'HDMI-A', 15.0, 55.0,
        ref_at=(0, -8), val_at=(0, 7)
    ),
    # microSD — center-right above USB ports
    # x=29.2..42.8, y=26.3..42.5 ✓
    embed_fp(
        f'{LIB}/Connector_Card.pretty/microSD_HC_Molex_104031-0811.kicad_mod',
        'J_SDCARD', 'microSD', 36.0, 36.0,
        ref_at=(0, -11), val_at=(0, 8)
    ),
    # USB-A #1 horizontal — bottom center, opening at board edge y=60
    # x=29.8..45.2, y=43.7..60.0 ✓
    embed_fp(
        f'{LIB}/Connector_USB.pretty/USB_A_Molex_67643_Horizontal.kicad_mod',
        'J_USB1', 'USB-A', 34.0, 46.5,
        ref_at=(0, -4), val_at=(0, 15)
    ),
    # USB-A #2 horizontal — bottom right-center
    # x=47.8..63.2, y=43.7..60.0 ✓
    embed_fp(
        f'{LIB}/Connector_USB.pretty/USB_A_Molex_67643_Horizontal.kicad_mod',
        'J_USB2', 'USB-A', 52.0, 46.5,
        ref_at=(0, -4), val_at=(0, 15)
    ),
    # Reset button — via CM5 RUN/nRESET pin
    # x=55.6..60.4, y=34.8..39.6 ✓
    embed_fp(
        f'{LIB}/Button_Switch_SMD.pretty/SW_SPST_B3U-3100P-B.kicad_mod',
        'SW_RST', 'RESET', 58.0, 38.0,
        ref_at=(0, -4), val_at=(0, 3)
    ),
    # Power button — via CM5 PWR_BTN pin
    # x=61.6..66.4, y=34.8..39.6 ✓ (1.8mm clearance from GPIO)
    embed_fp(
        f'{LIB}/Button_Switch_SMD.pretty/SW_SPST_B3U-3100P-B.kicad_mod',
        'SW_PWR', 'POWER', 64.0, 38.0,
        ref_at=(0, -4), val_at=(0, 3)
    ),
]

NEW_MH = [
    mounting_hole('MH2', 76.5, 3.5),
    mounting_hole('MH3', 76.5, 56.5),
    mounting_hole('MH4', 3.5, 56.5),
]


# ─── Patch PCB ─────────────────────────────────────────────────────────────────
pcb = open(PCB_PATH).read()


def remove_blocks_by_layer(text, layer_name):
    """Remove all gr_line/gr_arc blocks containing the given layer."""
    out = []
    i = 0
    while i < len(text):
        if re.match(r'[\t ]*\((gr_line|gr_arc)\b', text[i:]):
            depth = 0
            j = i
            for k, ch in enumerate(text[i:]):
                if ch == '(':
                    depth += 1
                elif ch == ')':
                    depth -= 1
                    if depth == 0:
                        j = i + k + 1
                        break
            block = text[i:j]
            if f'"{layer_name}"' in block:
                i = j
                # Skip trailing newline
                while i < len(text) and text[i] == '\n':
                    i += 1
                continue
        out.append(text[i])
        i += 1
    return ''.join(out)


def remove_footprints_at(text, positions):
    """Remove footprint blocks whose (at X Y) matches any of the given positions."""
    out = []
    i = 0
    while i < len(text):
        if re.match(r'[\t ]*\(footprint\b', text[i:]):
            depth = 0
            j = i
            for k, ch in enumerate(text[i:]):
                if ch == '(':
                    depth += 1
                elif ch == ')':
                    depth -= 1
                    if depth == 0:
                        j = i + k + 1
                        break
            block = text[i:j]
            am = re.search(r'\(at\s+([\d\.]+)\s+([\d\.]+)', block)
            if am:
                ax, ay = float(am.group(1)), float(am.group(2))
                if any(abs(ax - px) < 0.1 and abs(ay - py) < 0.1
                       for px, py in positions):
                    i = j
                    while i < len(text) and text[i] == '\n':
                        i += 1
                    continue
        out.append(text[i])
        i += 1
    return ''.join(out)


# Also strip any stale comments (semicolons from previous broken run)
pcb = re.sub(r'\t; ===.*?\n', '', pcb)

# 1. Remove old Edge.Cuts geometry
pcb = remove_blocks_by_layer(pcb, 'Edge.Cuts')

# 2. Remove old MH2 (61.5, 3.5), MH3 (61.5, 52.5), MH4 (3.5, 52.5)
pcb = remove_footprints_at(pcb, [(61.5, 3.5), (61.5, 52.5), (3.5, 52.5)])

# 3. Also remove any previously added IO components (by reference)
pcb = re.sub(
    r'\t\(footprint "[^"]*"\n(?:[^\n]*\n)*?\t\(property "Reference" "(?:J_GPIO|J_HDMI|J_SDCARD|J_USB1|J_USB2|SW_RST|SW_PWR)".*?(?=\n\t\(|\n\))',
    '', pcb, flags=re.DOTALL
)

# 4. Insert new geometry before closing )
insert_pos = pcb.rfind('\n)')
additions = '\n' + '\n'.join(NEW_EDGES) + '\n' + \
            '\n'.join(NEW_MH) + '\n' + \
            '\n'.join(components)

new_pcb = pcb[:insert_pos] + additions + '\n' + pcb[insert_pos:]

with open(PCB_PATH, 'w') as f:
    f.write(new_pcb)

print(f'Done. PCB size: {len(new_pcb):,} bytes')
print()
print('Board: 80x60mm')
print('Added:')
for c_str in components:
    ref = re.search(r'"Reference"\s+"([^"]+)"', c_str)
    at = re.search(r'\(at\s+([\d\.]+)\s+([\d\.]+)', c_str)
    if ref and at:
        print(f'  {ref.group(1):10s} ({at.group(1):5s}, {at.group(2):5s})')
