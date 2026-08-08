import math
import random

W, H = 900, 420
BG = "#0d1117"
ACCENT = "#39ff14"
ACCENT_DIM = "#155c0a"
ACCENT_MID = "#2bcf10"
EYE = "#0d1117"

N_SEGMENTS = 26
HEAD_R = 20
TAIL_R = 3.5
SEG_GAP_T = 0.028
LOOP_DUR = 8.0


def random_closed_path(cx, cy, base_r, n_points=11, jitter=0.35, seed=None):
    rnd = random.Random(seed)
    pts = []
    for i in range(n_points):
        angle = (2 * math.pi * i / n_points) + rnd.uniform(-0.15, 0.15)
        r = base_r * (1 + rnd.uniform(-jitter, jitter))
        x = cx + r * math.cos(angle) * 1.35
        y = cy + r * math.sin(angle)
        pts.append((x, y))
    return pts


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
    pts = random_closed_path(W / 2, H / 2 + 10, base_r=170, n_points=11, jitter=0.4, seed=seed)
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
    svg.append("</defs>")
    svg.append(f'<rect x="0" y="0" width="{W}" height="{H}" fill="{BG}" rx="12"/>')

    # faint dotted grid backdrop for texture
    for gy in range(0, H, 22):
        for gx in range(0, W, 22):
            svg.append(f'<circle cx="{gx}" cy="{gy}" r="1" fill="#1c2530"/>')

    # body segments: tail -> head so head renders on top, each riding the
    # same closed path via animateMotion, staggered by begin= so they trail
    for i in range(N_SEGMENTS - 1, -1, -1):
        t = i / (N_SEGMENTS - 1)  # 0 = head, 1 = tail
        r = HEAD_R + (TAIL_R - HEAD_R) * (t ** 1.4)
        delay = (N_SEGMENTS - 1 - i) * SEG_GAP_T
        color = lerp_color(ACCENT, ACCENT_DIM, t)
        is_head = i == 0

        svg.append("<g>")
        svg.append(
            f'<animateMotion dur="{LOOP_DUR:.3f}s" repeatCount="indefinite" '
            f'begin="-{delay:.3f}s" rotate="auto" calcMode="linear">'
            f'<mpath href="#loopPath"/></animateMotion>'
        )
        rx = r
        ry = r * 0.72
        svg.append(f'<ellipse rx="{rx:.1f}" ry="{ry:.1f}" fill="{color}"' + (' filter="url(#glow)"' if is_head else "") + "/>")
        if not is_head:
            # subtle belly highlight seam
            svg.append(f'<ellipse rx="{rx*0.5:.1f}" ry="{ry*0.35:.1f}" fill="{ACCENT_MID}" opacity="0.25"/>')
        if is_head:
            svg.append(f'<ellipse cx="{rx*0.4:.1f}" cy="{-ry*0.42:.1f}" rx="3.2" ry="3.6" fill="{EYE}"/>')
            svg.append(f'<ellipse cx="{rx*0.4:.1f}" cy="{ry*0.42:.1f}" rx="3.2" ry="3.6" fill="{EYE}"/>')
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

    svg.append(f'<path id="loopPath" d="{path_d}" fill="none" stroke="none"/>')
    svg.append("</svg>")

    with open(out_path, "w") as f:
        f.write("\n".join(svg))


if __name__ == "__main__":
    import sys
    seed = int(sys.argv[2]) if len(sys.argv) > 2 else None
    generate(sys.argv[1] if len(sys.argv) > 1 else "snake.svg", seed=seed)
