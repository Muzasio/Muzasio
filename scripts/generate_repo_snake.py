import math
import random

W, H = 900, 420
BG = "#0d1117"
ACCENT = "#39ff14"
ACCENT_DIM = "#155c0a"
ACCENT_MID = "#2bcf10"
EYE = "#0d1117"
SHADOW = "#000000"

N_SEGMENTS = 26
HEAD_R = 20
TAIL_R = 3.5
SEG_GAP_T = 0.028
LOOP_DUR = 8.0

UNDULATE_PERIOD = 0.9
UNDULATE_AMP = 3.2
UNDULATE_PHASE_STEP = 0.045

BLINK_PERIOD = 3.4


def shape_wide_roam(cx, cy, rnd):
    n = 11
    pts = []
    for i in range(n):
        angle = (2 * math.pi * i / n) + rnd.uniform(-0.15, 0.15)
        r = 170 * (1 + rnd.uniform(-0.4, 0.4))
        x = cx + r * math.cos(angle) * 1.35
        y = cy + r * math.sin(angle)
        pts.append((x, y))
    return pts


def shape_tight_coil(cx, cy, rnd):
    n = 13
    pts = []
    for i in range(n):
        angle = (2 * math.pi * i / n) + rnd.uniform(-0.2, 0.2)
        r = 95 * (1 + rnd.uniform(-0.3, 0.3))
        x = cx + r * math.cos(angle)
        y = cy + r * math.sin(angle) * 0.85
        pts.append((x, y))
    return pts


def shape_elongated(cx, cy, rnd):
    n = 9
    pts = []
    for i in range(n):
        angle = (2 * math.pi * i / n) + rnd.uniform(-0.12, 0.12)
        r = 150 * (1 + rnd.uniform(-0.35, 0.35))
        x = cx + r * math.cos(angle) * 1.8
        y = cy + r * math.sin(angle) * 0.6
        pts.append((x, y))
    return pts


SHAPES = [shape_wide_roam, shape_tight_coil, shape_elongated]


def closed_catmull_rom_bezier(points):
    n = len(points)
    d = f"M {points[0][0]:.2f},{points[0][1]:.2f} "
    for i in range(n):
        p0 = points[(i - 1) % n]
        p1 = points[i]
        p2 = points[(i + 1) % n]
        p3 = points[(i + 2) % n]
        c1x = p1[0] + (p2[0] - p0[0]) / 6
        c1y = p1[1] + (p2[1] - p0[1]) / 6
        c2x = p2[0] - (p3[0] - p1[0]) / 6
        c2y = p2[1] - (p3[1] - p1[1]) / 6
        d += f"C {c1x:.2f},{c1y:.2f} {c2x:.2f},{c2y:.2f} {p2[0]:.2f},{p2[1]:.2f} "
    d += "Z"
    return d


def lerp_color(c1, c2, t):
    c1 = c1.lstrip("#")
    c2 = c2.lstrip("#")
    r1, g1, b1 = int(c1[0:2], 16), int(c1[2:4], 16), int(c1[4:6], 16)
    r2, g2, b2 = int(c2[0:2], 16), int(c2[2:4], 16), int(c2[4:6], 16)
    r = round(r1 + (r2 - r1) * t)
    g = round(g1 + (g2 - g1) * t)
    b = round(b1 + (b2 - b1) * t)
    return f"#{r:02x}{g:02x}{b:02x}"


def generate(out_path, seed=None):
    rnd = random.Random(seed)
    shape_fn = rnd.choice(SHAPES)
    pts = shape_fn(W / 2, H / 2 + 10, rnd)
    path_d = closed_catmull_rom_bezier(pts)

    svg = []
    svg.append(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">')
    svg.append("<defs>")
    svg.append(
        '<filter id="glow" x="-60%" y="-60%" width="220%" height="220%">'
        '<feGaussianBlur stdDeviation="4" result="blur"/>'
        '<feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>'
        "</filter>"
    )
    svg.append(
        '<filter id="shadowBlur" x="-80%" y="-80%" width="260%" height="260%">'
        '<feGaussianBlur stdDeviation="3.5"/>'
        "</filter>"
    )
    svg.append("</defs>")
    svg.append(f'<rect x="0" y="0" width="{W}" height="{H}" fill="{BG}" rx="12"/>')

    for gy in range(0, H, 22):
        for gx in range(0, W, 22):
            svg.append(f'<circle cx="{gx}" cy="{gy}" r="1" fill="#1c2530"/>')

    # ground shadow: same segments, position-only (no rotate, no undulation),
    # offset straight down in screen space so it reads as a fixed light source
    for i in range(N_SEGMENTS - 1, -1, -1):
        t = i / (N_SEGMENTS - 1)
        r = HEAD_R + (TAIL_R - HEAD_R) * (t ** 1.4)
        delay = (N_SEGMENTS - 1 - i) * SEG_GAP_T
        svg.append('<g filter="url(#shadowBlur)">')
        svg.append(
            f'<animateMotion dur="{LOOP_DUR:.3f}s" repeatCount="indefinite" '
            f'begin="-{delay:.3f}s" calcMode="linear">'
            f'<mpath href="#loopPath"/></animateMotion>'
        )
        svg.append(
            f'<ellipse cx="0" cy="{r*0.7:.1f}" rx="{r*0.9:.1f}" ry="{r*0.42:.1f}" '
            f'fill="{SHADOW}" opacity="0.5"/>'
        )
        svg.append("</g>")

    # body segments: tail -> head so head renders on top. Outer <g> rides the
    # path (position + heading via rotate=auto). Inner <g> adds a phase-shifted
    # perpendicular oscillation on top of that for a traveling-wave undulation.
    for i in range(N_SEGMENTS - 1, -1, -1):
        t = i / (N_SEGMENTS - 1)  # 0 = head, 1 = tail
        r = HEAD_R + (TAIL_R - HEAD_R) * (t ** 1.4)
        delay = (N_SEGMENTS - 1 - i) * SEG_GAP_T
        undulate_delay = (N_SEGMENTS - 1 - i) * UNDULATE_PHASE_STEP
        color = lerp_color(ACCENT, ACCENT_DIM, t)
        is_head = i == 0

        svg.append("<g>")
        svg.append(
            f'<animateMotion dur="{LOOP_DUR:.3f}s" repeatCount="indefinite" '
            f'begin="-{delay:.3f}s" rotate="auto" calcMode="linear">'
            f'<mpath href="#loopPath"/></animateMotion>'
        )
        svg.append("<g>")
        svg.append(
            '<animateTransform attributeName="transform" type="translate" '
            f'dur="{UNDULATE_PERIOD:.3f}s" repeatCount="indefinite" '
            f'begin="-{undulate_delay:.3f}s" calcMode="spline" '
            'keyTimes="0;0.25;0.5;0.75;1" '
            f'values="0,0;0,{UNDULATE_AMP:.1f};0,0;0,{-UNDULATE_AMP:.1f};0,0" '
            'keySplines="0.4 0 0.6 1;0.4 0 0.6 1;0.4 0 0.6 1;0.4 0 0.6 1"/>'
        )
        rx = r
        ry = r * 0.72
        svg.append(f'<ellipse rx="{rx:.1f}" ry="{ry:.1f}" fill="{color}"' + (' filter="url(#glow)"' if is_head else "") + "/>")
        if not is_head:
            svg.append(f'<ellipse rx="{rx*0.5:.1f}" ry="{ry*0.35:.1f}" fill="{ACCENT_MID}" opacity="0.25"/>')
        if is_head:
            blink_delay = rnd.uniform(0, BLINK_PERIOD)
            svg.append(f'<g transform-origin="{rx*0.4:.1f}px {-ry*0.42:.1f}px">')
            svg.append(
                '<animateTransform attributeName="transform" type="scale" '
                f'dur="{BLINK_PERIOD:.3f}s" repeatCount="indefinite" '
                f'begin="-{blink_delay:.3f}s" calcMode="discrete" '
                'keyTimes="0;0.92;0.95;0.98;1" values="1,1;1,1;1,0.1;1,1;1,1"/>'
            )
            svg.append(f'<ellipse cx="{rx*0.4:.1f}" cy="{-ry*0.42:.1f}" rx="3.2" ry="3.6" fill="{EYE}"/>')
            svg.append("</g>")
            svg.append(f'<g transform-origin="{rx*0.4:.1f}px {ry*0.42:.1f}px">')
            svg.append(
                '<animateTransform attributeName="transform" type="scale" '
                f'dur="{BLINK_PERIOD:.3f}s" repeatCount="indefinite" '
                f'begin="-{blink_delay:.3f}s" calcMode="discrete" '
                'keyTimes="0;0.92;0.95;0.98;1" values="1,1;1,1;1,0.1;1,1;1,1"/>'
            )
            svg.append(f'<ellipse cx="{rx*0.4:.1f}" cy="{ry*0.42:.1f}" rx="3.2" ry="3.6" fill="{EYE}"/>')
            svg.append("</g>")
            tongue_base_x = rx - 2
            svg.append(f'<g transform-origin="{tongue_base_x:.1f}px 0px">')
            svg.append(
                '<animateTransform attributeName="transform" type="scale" '
                'dur="1.4s" repeatCount="indefinite" calcMode="linear" '
                'keyTimes="0;0.58;0.66;0.8;0.88;1" '
                'values="0,1;0,1;1,1;1,1;0,1;0,1"/>'
            )
            svg.append(
                f'<path d="M {tongue_base_x:.1f},0 L {tongue_base_x+4:.1f},0" stroke="#ff5555" '
                f'stroke-width="0.9" stroke-linecap="round"/>'
            )
            svg.append(
                f'<path d="M {tongue_base_x+3:.1f},0 L {tongue_base_x+4.5:.1f},-0.9 '
                f'M {tongue_base_x+3:.1f},0 L {tongue_base_x+4.5:.1f},0.9" '
                f'stroke="#ff5555" stroke-width="0.8" stroke-linecap="round"/>'
            )
            svg.append("</g>")
        svg.append("</g>")
        svg.append("</g>")

    svg.append(f'<path id="loopPath" d="{path_d}" fill="none" stroke="none"/>')
    svg.append("</svg>")

    with open(out_path, "w") as f:
        f.write("\n".join(svg))


if __name__ == "__main__":
    import sys
    seed = int(sys.argv[2]) if len(sys.argv) > 2 else None
    generate(sys.argv[1] if len(sys.argv) > 1 else "snake.svg", seed=seed)
