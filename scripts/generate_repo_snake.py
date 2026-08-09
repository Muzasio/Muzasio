import json
import math
import os
import random
import sys
import urllib.request

W, H = 1000, 600
BG = "#0d1117"
FONT = "'Courier New', monospace"

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

PER_CARD_T = 0.85

ACCENT = "#39ff14"
ACCENT_DIM = "#155c0a"
ACCENT_MID = "#2bcf10"
EYE = "#0d1117"
SHADOW = "#000000"

N_SEGMENTS = 26
HEAD_R = 20
TAIL_R = 3.5
SEG_GAP_T = 0.028

UNDULATE_PERIOD = 0.9
UNDULATE_AMP = 3.2
UNDULATE_PHASE_STEP = 0.045
BLINK_PERIOD = 3.4

GROWTH_START_SCALE = 0.72
GROWTH_END_SCALE = 1.45


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


def square_path(size, r):
    """Squircle-cornered square (iOS-icon style), centered at local origin."""
    x0 = y0 = -size / 2
    x1 = y1 = size / 2
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
    while len(pts) < n and attempts < 8000:
        attempts += 1
        x = rnd.uniform(margin, w - margin)
        y = rnd.uniform(margin, h - margin)
        if all(math.hypot(x - px, y - py) >= min_dist for px, py in pts):
            pts.append((x, y))
    return pts


def nearest_neighbor_tour(points, rnd):
    remaining = list(range(len(points)))
    start = rnd.choice(remaining)
    order = [start]
    remaining.remove(start)
    while remaining:
        last = points[order[-1]]
        nxt = min(remaining, key=lambda i: math.hypot(points[i][0] - last[0], points[i][1] - last[1]))
        order.append(nxt)
        remaining.remove(nxt)
    return order


def closed_catmull_rom_bezier(points):
    """Kept only for standalone-snake compatibility; the card-eating path
    below uses closed_catmull_rom_segments + arc_length_key_points instead."""
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


def closed_catmull_rom_segments(points):
    n = len(points)
    segments = []
    for i in range(n):
        p0 = points[(i - 1) % n]
        p1 = points[i]
        p2 = points[(i + 1) % n]
        p3 = points[(i + 2) % n]
        c1 = (p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6)
        c2 = (p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6)
        segments.append((p1, c1, c2, p2))
    return segments


def path_d_from_segments(segments):
    d = f"M {segments[0][0][0]:.2f},{segments[0][0][1]:.2f} "
    for p1, c1, c2, p2 in segments:
        d += f"C {c1[0]:.2f},{c1[1]:.2f} {c2[0]:.2f},{c2[1]:.2f} {p2[0]:.2f},{p2[1]:.2f} "
    d += "Z"
    return d


def sample_cubic(p1, c1, c2, p2, steps=28):
    pts = []
    for s in range(steps + 1):
        t = s / steps
        mt = 1 - t
        x = mt**3 * p1[0] + 3 * mt**2 * t * c1[0] + 3 * mt * t**2 * c2[0] + t**3 * p2[0]
        y = mt**3 * p1[1] + 3 * mt**2 * t * c1[1] + 3 * mt * t**2 * c2[1] + t**3 * p2[1]
        pts.append((x, y))
    return pts


def arc_length_key_points(segments):
    """True key points along the actual rendered bezier curve (not the
    straight-line chord distance between waypoints), so the head's arrival
    time at each card matches exactly where it visually is on the curve."""
    cum = [0.0]
    for seg in segments:
        pts = sample_cubic(*seg)
        length = 0.0
        for a, b in zip(pts, pts[1:]):
            length += math.hypot(b[0] - a[0], b[1] - a[1])
        cum.append(cum[-1] + length)
    total = cum[-1] if cum[-1] > 0 else 1.0
    return [c / total for c in cum]


def lerp_color(c1, c2, t):
    c1 = c1.lstrip("#")
    c2 = c2.lstrip("#")
    r1, g1, b1 = int(c1[0:2], 16), int(c1[2:4], 16), int(c1[4:6], 16)
    r2, g2, b2 = int(c2[0:2], 16), int(c2[2:4], 16), int(c2[4:6], 16)
    r = round(r1 + (r2 - r1) * t)
    g = round(g1 + (g2 - g1) * t)
    b = round(b1 + (b2 - b1) * t)
    return f"#{r:02x}{g:02x}{b:02x}"


def generate(out_path, repos, seed=None):
    rnd = random.Random(seed)
    n = len(repos)

    card_size = 108
    pts = poisson_scatter(n, W, H, min_dist=card_size * 1.25, margin=90, rnd=rnd)
    while len(pts) < n:
        pts.append((rnd.uniform(90, W - 90), rnd.uniform(90, H - 90)))

    order = nearest_neighbor_tour(pts, rnd)
    ordered_pts = [pts[i] for i in order]
    ordered_repos = [repos[i] for i in order]

    segments = closed_catmull_rom_segments(ordered_pts)
    path_d = path_d_from_segments(segments)
    key_points = arc_length_key_points(segments)

    # randomized per-card time gaps instead of a uniform i/n split -- a fixed
    # interval between every eat is what reads as a robotic metronome, so
    # each gap is drawn independently and the cumulative times define both
    # key_times (when the head visits each vertex) and total_dur
    gaps = [rnd.uniform(0.45, 1.55) for _ in range(n)]
    cumulative = [0.0]
    for g in gaps:
        cumulative.append(cumulative[-1] + g)
    total_dur = cumulative[-1]
    key_times = [c / total_dur for c in cumulative]

    kp_str = ";".join(f"{k:.5f}" for k in key_points)
    kt_str = ";".join(f"{k:.5f}" for k in key_times)
    # the head (body segment i=0) is given the LARGEST begin-delay so it
    # leads the pack (see render_snake). That means, for a fixed vertex, the
    # head physically arrives HEAD_DELAY seconds before the reference
    # (zero-delay) timing that key_points/key_times were built against.
    # Card eat-timing must be shifted by that same amount or the trigger
    # fires when the zero-delay tail segment arrives instead of the head.
    HEAD_DELAY = (N_SEGMENTS - 1) * SEG_GAP_T

    defs = []
    body = []

    body.append(f'<rect x="0" y="0" width="{W}" height="{H}" fill="{BG}" rx="14"/>')
    for gy in range(0, H, 24):
        for gx in range(0, W, 24):
            body.append(f'<circle cx="{gx}" cy="{gy}" r="1" fill="#1c2530"/>')

    # ---- cards: plain axis-aligned squares, no rotation. Each vanishes the
    # instant the snake head's timing (idx * PER_CARD_T) reaches it, and
    # reappears when the loop restarts.
    defs.append(
        '<filter id="cardShadow" x="-30%" y="-30%" width="160%" height="160%">'
        '<feDropShadow dx="0" dy="2" stdDeviation="3" flood-color="#000000" flood-opacity="0.35"/>'
        "</filter>"
    )
    defs.append(
        '<filter id="glowBlur" x="-60%" y="-60%" width="220%" height="220%">'
        '<feGaussianBlur stdDeviation="7"/>'
        "</filter>"
    )
    for i, r in enumerate(ordered_repos):
        c1, c2 = rnd.choice(GRADIENT_PAIRS)
        angle = rnd.uniform(0, 360)
        defs.append(
            f'<linearGradient id="grad{i}" gradientTransform="rotate({angle:.0f})">'
            f'<stop offset="0%" stop-color="{c1}"/>'
            f'<stop offset="100%" stop-color="{c2}"/>'
            "</linearGradient>"
        )
        cx, cy = ordered_pts[i]
        lang_color = LANG_COLOR.get(r["language"], TEXT_DIM)
        eat_t = (cumulative[i] - HEAD_DELAY) % total_dur
        pop_t = min(eat_t + 0.05, total_dur)
        vanish_end = min(eat_t + 0.13, total_dur)
        rf_eat = eat_t / total_dur
        rf_pop = pop_t / total_dur
        rf_vanish = vanish_end / total_dur

        body.append(f'<g transform="translate({cx:.1f},{cy:.1f})">')

        # card: idle -> quick pop -> shrink to nothing, timed tight to the
        # head's actual arrival so it reacts the instant contact happens
        body.append(f'<g>')
        body.append(
            '<animateTransform attributeName="transform" type="scale" additive="sum" '
            f'dur="{total_dur:.3f}s" repeatCount="indefinite" calcMode="spline" '
            f'keyTimes="0;{rf_eat:.5f};{rf_pop:.5f};{rf_vanish:.5f};1" values="1;1;1.22;0.05;0.05" '
            'keySplines="0.4 0 0.2 1;0.3 0 0.4 1;0.2 0 0.8 1;0 0 1 1"/>'
        )
        body.append(
            '<animate attributeName="opacity" '
            f'dur="{total_dur:.3f}s" repeatCount="indefinite" calcMode="discrete" '
            f'keyTimes="0;{rf_eat:.5f};{rf_vanish:.5f};1" values="1;1;0;0"/>'
        )
        body.append(f'<circle cx="{card_size*0.3:.1f}" cy="{-card_size*0.3:.1f}" r="{card_size*0.26:.1f}" fill="{c2}" opacity="0.22" filter="url(#glowBlur)"/>')
        body.append('<g filter="url(#cardShadow)">')
        body.append(f'<path d="{square_path(card_size, 20)}" fill="#161b22"/>')
        body.append(f'<path d="{square_path(card_size, 20)}" fill="none" stroke="url(#grad{i})" stroke-width="1.8"/>')
        body.append("</g>")

        tx, ty = -card_size / 2 + 12, -card_size / 2 + 22
        body.append(
            f'<text x="{tx:.1f}" y="{ty:.1f}" font-family="{FONT}" font-size="11.5" '
            f'font-weight="bold" fill="{TEXT_PRIMARY}">{esc(truncate(r["name"], 14))}</text>'
        )
        body.append(f'<circle cx="{tx+5:.1f}" cy="{ty+18:.1f}" r="3.2" fill="{lang_color}"/>')
        body.append(
            f'<text x="{tx+13:.1f}" y="{ty+22:.1f}" font-family="{FONT}" font-size="9.5" '
            f'fill="{TEXT_DIM}">{esc(truncate(r["language"], 12))}</text>'
        )
        body.append(
            f'<text x="{tx:.1f}" y="{ty+38:.1f}" font-family="{FONT}" font-size="9.5" '
            f'fill="{c2}">&#9733; {r["stars"]}</text>'
        )
        body.append("</g>")

        # particle burst: fires the instant the head arrives, flies outward
        # from the card center and fades, independent of the card's own pop
        n_particles = 7
        burst_start = rf_eat
        burst_end = min(eat_t + 0.34, total_dur) / total_dur
        # opacity must stay flat at 0 for the whole idle period and only pop
        # to 1 right at burst_start -- a duplicate near-zero pre-keyframe
        # pins that, otherwise linear calcMode ramps 0->1 across the ENTIRE
        # idle interval and the particle sits visible at the card center
        # the whole time (that's the stray "dot" bug)
        pre_burst_t = max(0.0, eat_t - 0.02)
        rf_pre = pre_burst_t / total_dur
        use_pre_frame = rf_pre < rf_eat
        for p in range(n_particles):
            angle = rnd.uniform(0, 2 * math.pi)
            dist = rnd.uniform(34, 68)
            dx, dy = math.cos(angle) * dist, math.sin(angle) * dist
            psize = rnd.uniform(2.2, 4.5)
            pcolor = c2 if p % 2 == 0 else c1
            body.append("<g>")
            body.append(
                '<animateTransform attributeName="transform" type="translate" '
                f'dur="{total_dur:.3f}s" repeatCount="indefinite" calcMode="linear" '
                f'keyTimes="0;{burst_start:.5f};{burst_end:.5f};1" '
                f'values="0,0;0,0;{dx:.1f},{dy:.1f};{dx:.1f},{dy:.1f}"/>'
            )
            body.append("<g>")
            body.append(
                '<animateTransform attributeName="transform" type="scale" '
                f'dur="{total_dur:.3f}s" repeatCount="indefinite" calcMode="linear" '
                f'keyTimes="0;{burst_start:.5f};{burst_end:.5f};1" values="1;1;0.15;0.15"/>'
            )
            body.append(
                f'<circle r="{psize:.1f}" fill="{pcolor}">'
                '<animate attributeName="opacity" '
                f'dur="{total_dur:.3f}s" repeatCount="indefinite" calcMode="linear" '
                + (
                    f'keyTimes="0;{rf_pre:.5f};{burst_start:.5f};{burst_end:.5f};1" values="0;0;1;0;0"/>'
                    if use_pre_frame else
                    f'keyTimes="0;{burst_start:.5f};{burst_end:.5f};1" values="1;1;0;0"/>'
                )
                + "</circle>"
            )
            body.append("</g>")
            body.append("</g>")

        body.append("</g>")

    # ---- snake: same path, growing in scale across the lap as it eats
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

    body.append('<g transform-origin="{}px {}px">'.format(W / 2, H / 2))
    body.append(
        '<animateTransform attributeName="transform" type="scale" additive="sum" '
        f'dur="{total_dur:.3f}s" repeatCount="indefinite" calcMode="linear" '
        f'values="{GROWTH_START_SCALE};{GROWTH_END_SCALE}"/>'
    )

    for i in range(N_SEGMENTS - 1, -1, -1):
        t = i / (N_SEGMENTS - 1)
        r = HEAD_R + (TAIL_R - HEAD_R) * (t ** 1.4)
        delay = (N_SEGMENTS - 1 - i) * SEG_GAP_T
        body.append('<g filter="url(#shadowBlur)">')
        body.append(
            f'<animateMotion dur="{total_dur:.3f}s" repeatCount="indefinite" '
            f'begin="-{delay:.3f}s" calcMode="linear" keyPoints="{kp_str}" keyTimes="{kt_str}">'
            f'<mpath href="#loopPath"/></animateMotion>'
        )
        body.append(
            f'<ellipse cx="0" cy="{r*0.7:.1f}" rx="{r*0.9:.1f}" ry="{r*0.42:.1f}" '
            f'fill="{SHADOW}" opacity="0.5"/>'
        )
        body.append("</g>")

    for i in range(N_SEGMENTS - 1, -1, -1):
        t = i / (N_SEGMENTS - 1)
        r = HEAD_R + (TAIL_R - HEAD_R) * (t ** 1.4)
        delay = (N_SEGMENTS - 1 - i) * SEG_GAP_T
        undulate_delay = (N_SEGMENTS - 1 - i) * UNDULATE_PHASE_STEP
        color = lerp_color(ACCENT, ACCENT_DIM, t)
        is_head = i == 0

        body.append("<g>")
        body.append(
            f'<animateMotion dur="{total_dur:.3f}s" repeatCount="indefinite" '
            f'begin="-{delay:.3f}s" rotate="auto" calcMode="linear" keyPoints="{kp_str}" keyTimes="{kt_str}">'
            f'<mpath href="#loopPath"/></animateMotion>'
        )
        body.append("<g>")
        body.append(
            '<animateTransform attributeName="transform" type="translate" '
            f'dur="{UNDULATE_PERIOD:.3f}s" repeatCount="indefinite" '
            f'begin="-{undulate_delay:.3f}s" calcMode="spline" '
            'keyTimes="0;0.25;0.5;0.75;1" '
            f'values="0,0;0,{UNDULATE_AMP:.1f};0,0;0,{-UNDULATE_AMP:.1f};0,0" '
            'keySplines="0.4 0 0.6 1;0.4 0 0.6 1;0.4 0 0.6 1;0.4 0 0.6 1"/>'
        )
        rx = r
        ry = r * 0.72
        body.append(f'<ellipse rx="{rx:.1f}" ry="{ry:.1f}" fill="{color}"' + (' filter="url(#glow)"' if is_head else "") + "/>")
        if not is_head:
            body.append(f'<ellipse rx="{rx*0.5:.1f}" ry="{ry*0.35:.1f}" fill="{ACCENT_MID}" opacity="0.25"/>')
        if is_head:
            blink_delay = rnd.uniform(0, BLINK_PERIOD)
            body.append(f'<g transform-origin="{rx*0.4:.1f}px {-ry*0.42:.1f}px">')
            body.append(
                '<animateTransform attributeName="transform" type="scale" '
                f'dur="{BLINK_PERIOD:.3f}s" repeatCount="indefinite" '
                f'begin="-{blink_delay:.3f}s" calcMode="discrete" '
                'keyTimes="0;0.92;0.95;0.98;1" values="1,1;1,1;1,0.1;1,1;1,1"/>'
            )
            body.append(f'<ellipse cx="{rx*0.4:.1f}" cy="{-ry*0.42:.1f}" rx="3.2" ry="3.6" fill="{EYE}"/>')
            body.append("</g>")
            body.append(f'<g transform-origin="{rx*0.4:.1f}px {ry*0.42:.1f}px">')
            body.append(
                '<animateTransform attributeName="transform" type="scale" '
                f'dur="{BLINK_PERIOD:.3f}s" repeatCount="indefinite" '
                f'begin="-{blink_delay:.3f}s" calcMode="discrete" '
                'keyTimes="0;0.92;0.95;0.98;1" values="1,1;1,1;1,0.1;1,1;1,1"/>'
            )
            body.append(f'<ellipse cx="{rx*0.4:.1f}" cy="{ry*0.42:.1f}" rx="3.2" ry="3.6" fill="{EYE}"/>')
            body.append("</g>")
            tongue_base_x = rx - 2
            body.append(f'<g transform-origin="{tongue_base_x:.1f}px 0px">')
            body.append(
                '<animateTransform attributeName="transform" type="scale" '
                'dur="1.4s" repeatCount="indefinite" calcMode="linear" '
                'keyTimes="0;0.58;0.66;0.8;0.88;1" '
                'values="0,1;0,1;1,1;1,1;0,1;0,1"/>'
            )
            body.append(
                f'<path d="M {tongue_base_x:.1f},0 L {tongue_base_x+4:.1f},0" stroke="#ff5555" '
                f'stroke-width="0.9" stroke-linecap="round"/>'
            )
            body.append(
                f'<path d="M {tongue_base_x+3:.1f},0 L {tongue_base_x+4.5:.1f},-0.9 '
                f'M {tongue_base_x+3:.1f},0 L {tongue_base_x+4.5:.1f},0.9" '
                f'stroke="#ff5555" stroke-width="0.8" stroke-linecap="round"/>'
            )
            body.append("</g>")
        body.append("</g>")
        body.append("</g>")

    body.append("</g>")  # close growth wrapper
    body.append(f'<path id="loopPath" d="{path_d}" fill="none" stroke="none"/>')

    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">']
    out.append("<defs>")
    out.extend(defs)
    out.append("</defs>")
    out.extend(body)
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
