import json
import math
import os
import random
import sys
import urllib.request

# ---------- shared canvas ----------
W, H = 1000, 600
BG = "#0d1117"
FONT = "'Courier New', monospace"

# ---------- card palette / text ----------
TEXT_PRIMARY = "#e6edf3"
TEXT_DIM = "#8b949e"

GRADIENT_PAIRS = [
    ("#1f8f0c", "#39ff14"),
    ("#0c5c8f", "#12b3ff"),
    ("#8f0c6e", "#ff12b3"),
    ("#8f6e0c", "#ffcf12"),
    ("#0c8f5c", "#12ffb3"),
]

LANG_COLOR = {
    "Python": "#3572A5", "C++": "#f34b7d", "Shell": "#89e051",
    "JavaScript": "#f1e05a", "HTML": "#e34c26", "N/A": "#484f58",
}

SAMPLE_REPOS = [
    {"name": "Muzasio", "language": "Python", "stars": 1},
    {"name": "Cachy-Os", "language": "N/A", "stars": 0},
    {"name": "gdl2pdf", "language": "Python", "stars": 0},
    {"name": "Android", "language": "Shell", "stars": 0},
    {"name": "Github-Repo-Uploader", "language": "Shell", "stars": 0},
    {"name": "KVM_Backup_Manager", "language": "Shell", "stars": 1},
    {"name": "Lab-System-Logs", "language": "N/A", "stars": 0},
    {"name": "Video-Caption-gen", "language": "Python", "stars": 1},
    {"name": "Per-App-Vpn-Linux", "language": "N/A", "stars": 0},
    {"name": "bash-log-inspector", "language": "Shell", "stars": 0},
    {"name": "video-batch-conv", "language": "Shell", "stars": 0},
]

# ---------- snake tuning ----------
ACCENT = "#39ff14"
ACCENT_DIM = "#155c0a"
ACCENT_MID = "#2bcf10"
EYE = "#0d1117"
SHADOW = "#000000"

N_SEGMENTS = 26
HEAD_R = 22
TAIL_R = 3.8
SEG_GAP_T = 0.028
LOOP_DUR = 9.0

UNDULATE_PERIOD = 0.9
UNDULATE_AMP = 3.4
UNDULATE_PHASE_STEP = 0.045

BLINK_PERIOD = 3.4


def fetch_repos(user, token=None, limit=24):
    req = urllib.request.Request(
        f"https://api.github.com/users/{user}/repos?sort=updated&per_page=100&type=owner"
    )
    req.add_header("Accept", "application/vnd.github+json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.load(resp)
    repos = [r for r in data if not r.get("fork") and not r.get("private")][:limit]
    return [
        {"name": r["name"], "language": r.get("language") or "N/A", "stars": r.get("stargazers_count", 0)}
        for r in repos
    ]


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def truncate(s, n):
    return s if len(s) <= n else s[: n - 1].rstrip() + "\u2026"


# ---------- card shape/layout ----------

def squircle_path(w, h, r):
    x0, y0 = -w / 2, -h / 2
    x1, y1 = w / 2, h / 2
    k = 0.62
    return (
        f"M {x0+r:.2f},{y0:.2f} "
        f"L {x1-r:.2f},{y0:.2f} "
        f"C {x1-r+r*k:.2f},{y0:.2f} {x1:.2f},{y0+r-r*k:.2f} {x1:.2f},{y0+r:.2f} "
        f"L {x1:.2f},{y1-r:.2f} "
        f"C {x1:.2f},{y1-r+r*k:.2f} {x1-r+r*k:.2f},{y1:.2f} {x1-r:.2f},{y1:.2f} "
        f"L {x0+r:.2f},{y1:.2f} "
        f"C {x0+r-r*k:.2f},{y1:.2f} {x0:.2f},{y1-r+r*k:.2f} {x0:.2f},{y1-r:.2f} "
        f"L {x0:.2f},{y0+r:.2f} "
        f"C {x0:.2f},{y0+r-r*k:.2f} {x0+r-r*k:.2f},{y0:.2f} {x0+r:.2f},{y0:.2f} Z"
    )


def poisson_scatter(n, w, h, min_dist, margin, rnd):
    pts = []
    attempts = 0
    while len(pts) < n and attempts < 6000:
        attempts += 1
        x = rnd.uniform(margin, w - margin)
        y = rnd.uniform(margin, h - margin)
        if all(math.hypot(x - px, y - py) >= min_dist for px, py in pts):
            pts.append((x, y))
    return pts


def render_cards(svg, defs, repos, rnd):
    n = len(repos)
    pts = poisson_scatter(n, W, H, min_dist=108, margin=100, rnd=rnd)
    while len(pts) < n:
        pts.append((rnd.uniform(100, W - 100), rnd.uniform(100, H - 100)))

    defs.append(
        '<filter id="cardShadow" x="-40%" y="-40%" width="180%" height="180%">'
        '<feDropShadow dx="0" dy="4" stdDeviation="6" flood-color="#000000" flood-opacity="0.45"/>'
        "</filter>"
    )
    defs.append(
        '<filter id="glowBlur" x="-100%" y="-100%" width="300%" height="300%">'
        '<feGaussianBlur stdDeviation="14"/>'
        "</filter>"
    )
    card_gradients = []
    for i in range(n):
        c1, c2 = rnd.choice(GRADIENT_PAIRS)
        card_gradients.append((c1, c2))
        angle = rnd.uniform(0, 360)
        defs.append(
            f'<linearGradient id="grad{i}" gradientTransform="rotate({angle:.0f})">'
            f'<stop offset="0%" stop-color="{c1}"/>'
            f'<stop offset="100%" stop-color="{c2}"/>'
            "</linearGradient>"
        )

    card_w, card_h = 148, 88
    layout = []
    for i, r in enumerate(repos):
        cx, cy = pts[i]
        rot = rnd.uniform(-8, 8)
        scale = rnd.uniform(0.85, 1.22)
        corner = rnd.choice(["tl", "tr", "bl", "br"])
        layout.append((i, r, cx, cy, rot, scale, corner))
    layout.sort(key=lambda item: item[5])

    for i, r, cx, cy, rot, scale, corner in layout:
        w = card_w * scale
        h = card_h * scale
        corner_r = 22 * scale
        lang_color = LANG_COLOR.get(r["language"], TEXT_DIM)
        c1, c2 = card_gradients[i]

        cox = {"tl": -w / 2, "tr": w / 2, "bl": -w / 2, "br": w / 2}[corner]
        coy = {"tl": -h / 2, "tr": -h / 2, "bl": h / 2, "br": h / 2}[corner]

        svg.append(f'<g transform="translate({cx:.1f},{cy:.1f}) rotate({rot:.1f})">')
        svg.append(f'<circle cx="{cox:.1f}" cy="{coy:.1f}" r="{w*0.42:.1f}" fill="{c2}" opacity="0.30" filter="url(#glowBlur)"/>')
        svg.append('<g filter="url(#cardShadow)">')
        svg.append(f'<path d="{squircle_path(w, h, corner_r)}" fill="#161b22"/>')
        svg.append(f'<path d="{squircle_path(w, h, corner_r)}" fill="none" stroke="url(#grad{i})" stroke-width="1.8"/>')
        svg.append("</g>")
        svg.append(
            f'<path d="M {-w/2+corner_r*0.3:.1f},{-h/2+corner_r*1.1:.1f} '
            f'Q {-w/2:.1f},{-h/2:.1f} {-w/2+corner_r*1.1:.1f},{-h/2:.1f} '
            f'L {w/2-corner_r*1.1:.1f},{-h/2:.1f}" '
            f'fill="none" stroke="#ffffff" stroke-width="1" opacity="0.10" stroke-linecap="round"/>'
        )

        tx, ty = -w / 2 + 14, -h / 2 + 24
        svg.append(
            f'<text x="{tx:.1f}" y="{ty:.1f}" font-family="{FONT}" font-size="{12*scale:.1f}" '
            f'font-weight="bold" fill="{TEXT_PRIMARY}">{esc(truncate(r["name"], 16))}</text>'
        )
        svg.append(f'<circle cx="{tx+6:.1f}" cy="{ty+20*scale:.1f}" r="{3.5*scale:.1f}" fill="{lang_color}"/>')
        svg.append(
            f'<text x="{tx+15:.1f}" y="{ty+24*scale:.1f}" font-family="{FONT}" font-size="{10*scale:.1f}" '
            f'fill="{TEXT_DIM}">{esc(truncate(r["language"], 14))}</text>'
        )
        svg.append(
            f'<text x="{tx:.1f}" y="{ty+42*scale:.1f}" font-family="{FONT}" font-size="{10*scale:.1f}" '
            f'fill="{c2}">&#9733; {r["stars"]}</text>'
        )
        svg.append("</g>")


# ---------- snake shape/path/motion ----------

def shape_wide_roam(cx, cy, rnd):
    n = 11
    pts = []
    for i in range(n):
        angle = (2 * math.pi * i / n) + rnd.uniform(-0.15, 0.15)
        r = 230 * (1 + rnd.uniform(-0.4, 0.4))
        x = cx + r * math.cos(angle) * 1.35
        y = cy + r * math.sin(angle)
        pts.append((x, y))
    return pts


def shape_tight_coil(cx, cy, rnd):
    n = 13
    pts = []
    for i in range(n):
        angle = (2 * math.pi * i / n) + rnd.uniform(-0.2, 0.2)
        r = 130 * (1 + rnd.uniform(-0.3, 0.3))
        x = cx + r * math.cos(angle)
        y = cy + r * math.sin(angle) * 0.85
        pts.append((x, y))
    return pts


def shape_elongated(cx, cy, rnd):
    n = 9
    pts = []
    for i in range(n):
        angle = (2 * math.pi * i / n) + rnd.uniform(-0.12, 0.12)
        r = 200 * (1 + rnd.uniform(-0.35, 0.35))
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


def render_snake(svg, defs, rnd):
    shape_fn = rnd.choice(SHAPES)
    pts = shape_fn(W / 2, H / 2, rnd)
    path_d = closed_catmull_rom_bezier(pts)

    defs.append(
        '<filter id="glow" x="-60%" y="-60%" width="220%" height="220%">'
        '<feGaussianBlur stdDeviation="4" result="blur"/>'
        '<feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>'
        "</filter>"
    )
    defs.append(
        '<filter id="shadowBlur" x="-80%" y="-80%" width="260%" height="260%">'
        '<feGaussianBlur stdDeviation="3.5"/>'
        "</filter>"
    )

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

    for i in range(N_SEGMENTS - 1, -1, -1):
        t = i / (N_SEGMENTS - 1)
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


# ---------- top-level assembly ----------

def generate(out_path, repos, seed=None):
    rnd = random.Random(seed)

    defs = []
    svg = []
    svg.append(f'<rect x="0" y="0" width="{W}" height="{H}" fill="{BG}" rx="14"/>')
    for gy in range(0, H, 24):
        for gx in range(0, W, 24):
            svg.append(f'<circle cx="{gx}" cy="{gy}" r="1" fill="#1c2530"/>')

    render_cards(svg, defs, repos, rnd)
    render_snake(svg, defs, rnd)

    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">']
    out.append("<defs>")
    out.extend(defs)
    out.append("</defs>")
    out.extend(svg)
    out.append("</svg>")

    with open(out_path, "w") as f:
        f.write("\n".join(out))


if __name__ == "__main__":
    user = os.environ.get("GITHUB_USER", "Muzasio")
    token = os.environ.get("GITHUB_TOKEN")
    out = sys.argv[1] if len(sys.argv) > 1 else "dist/repo-snake.svg"
    seed = int(sys.argv[2]) if len(sys.argv) > 2 else None
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)

    if os.environ.get("USE_SAMPLE") == "1":
        repos = SAMPLE_REPOS
    else:
        try:
            repos = fetch_repos(user, token)
            if not repos:
                repos = SAMPLE_REPOS
        except Exception as e:
            print(f"API fetch failed ({e}), falling back to sample data", file=sys.stderr)
            repos = SAMPLE_REPOS

    generate(out, repos, seed=seed)
    print(f"wrote {out}: {W}x{H}px, {len(repos)} repos")
