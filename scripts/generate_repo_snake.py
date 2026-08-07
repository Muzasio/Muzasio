import json
import math
import os
import sys
import urllib.request

COLS = 6
CARD_W = 150
CARD_H = 80
GAP = 14
PAD = 24
PER_CELL = 0.55
BODY_FRACTION = 0.14
FONT = "'Courier New', monospace"

BG = "#0d1117"
CARD_FILL = "#161b22"
CARD_BORDER = "#30363d"
ACCENT = "#39ff14"
ACCENT_DIM = "#1f8f0c"
ACCENT_FLASH = "#baffb0"
TEXT_PRIMARY = "#e6edf3"
TEXT_DIM = "#8b949e"

LANG_COLOR = {
    "Python": "#3572A5", "C++": "#f34b7d", "Shell": "#89e051",
    "JavaScript": "#f1e05a", "HTML": "#e34c26", "CSS": "#563d7c",
    "C": "#555555", "TypeScript": "#3178c6", "Jupyter Notebook": "#DA5B0B",
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


def grid_centers(n, cols):
    rows = math.ceil(n / cols)
    points = []
    for row in range(rows):
        row_cols = range(cols) if row % 2 == 0 else range(cols - 1, -1, -1)
        for col in row_cols:
            idx = row * cols + (col if row % 2 == 0 else cols - 1 - col)
            if idx >= n:
                continue
            cx = PAD + col * (CARD_W + GAP) + CARD_W / 2
            cy = PAD + row * (CARD_H + GAP) + CARD_H / 2
            points.append((cx, cy))
    return points, rows


def catmull_rom_to_bezier(points):
    """Convert waypoints into a smooth cubic-bezier path string (rounded corners)."""
    pts = [points[0]] + points + [points[-1]]
    d = f"M {pts[1][0]:.2f},{pts[1][1]:.2f} "
    for i in range(1, len(pts) - 2):
        p0, p1, p2, p3 = pts[i - 1], pts[i], pts[i + 1], pts[i + 2]
        c1x = p1[0] + (p2[0] - p0[0]) / 6
        c1y = p1[1] + (p2[1] - p0[1]) / 6
        c2x = p2[0] - (p3[0] - p1[0]) / 6
        c2y = p2[1] - (p3[1] - p1[1]) / 6
        d += f"C {c1x:.2f},{c1y:.2f} {c2x:.2f},{c2y:.2f} {p2[0]:.2f},{p2[1]:.2f} "
    return d.strip()


def generate(repos, out_path):
    n = len(repos)
    centers, rows = grid_centers(n, COLS)
    width = PAD * 2 + COLS * CARD_W + (COLS - 1) * GAP
    height = PAD * 2 + rows * CARD_H + (rows - 1) * GAP

    path_d = catmull_rom_to_bezier(centers)
    total_dur = n * PER_CELL
    path_len_units = 1000
    body_len = path_len_units * BODY_FRACTION

    svg = []
    svg.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
        f'width="{width}" height="{height}">'
    )
    svg.append(f'<rect x="0" y="0" width="{width}" height="{height}" fill="{BG}" rx="10"/>')

    # --- cards, each pops when the snake head reaches it ---
    for idx, (cx0, cy0) in enumerate(centers):
        r = repos[idx]
        cx, cy = cx0 - CARD_W / 2, cy0 - CARD_H / 2
        eat_t = (idx + 0.5) * PER_CELL
        pre = max(eat_t - 0.12, 0)
        pop = eat_t
        settle = min(eat_t + 0.28, total_dur)
        rf_pre = pre / total_dur
        rf_pop = pop / total_dur
        rf_settle = settle / total_dur
        lang_color = LANG_COLOR.get(r["language"], TEXT_DIM)

        svg.append(f'<g transform-origin="{cx0:.1f}px {cy0:.1f}px" opacity="0">')
        svg.append(
            '<animate attributeName="opacity" dur="{:.3f}s" repeatCount="indefinite" '
            'calcMode="discrete" keyTimes="0;{:.4f};{:.4f};1" values="0;0;1;1"/>'.format(
                total_dur, rf_pre, rf_pre + 0.0001
            )
        )
        svg.append(
            '<animateTransform attributeName="transform" type="scale" additive="sum" '
            'dur="{:.3f}s" repeatCount="indefinite" calcMode="spline" '
            'keyTimes="0;{:.4f};{:.4f};{:.4f};1" values="1;1;1.18;1;1" '
            'keySplines="0.4 0 0.6 1;0.4 0 0.2 1;0.4 0 0.2 1;0 0 1 1"/>'.format(
                total_dur, rf_pre, rf_pop, rf_settle
            )
        )
        svg.append(
            f'<rect x="{cx:.1f}" y="{cy:.1f}" width="{CARD_W}" height="{CARD_H}" rx="8" '
            f'fill="{CARD_FILL}" stroke="{ACCENT_DIM}" stroke-width="1.5">'
        )
        svg.append(
            '<animate attributeName="stroke" dur="{:.3f}s" repeatCount="indefinite" '
            'calcMode="discrete" keyTimes="0;{:.4f};{:.4f};1" values="{};{};{};{}"/>'.format(
                total_dur, rf_pop, rf_settle, ACCENT_DIM, ACCENT_FLASH, ACCENT_FLASH, ACCENT_DIM
            )
        )
        svg.append("</rect>")
        svg.append(
            f'<text x="{cx+10:.1f}" y="{cy+24:.1f}" font-family="{FONT}" font-size="13" '
            f'font-weight="bold" fill="{TEXT_PRIMARY}">{esc(r["name"][:16])}</text>'
        )
        svg.append(f'<circle cx="{cx+16:.1f}" cy="{cy+42:.1f}" r="4" fill="{lang_color}"/>')
        svg.append(
            f'<text x="{cx+26:.1f}" y="{cy+46:.1f}" font-family="{FONT}" font-size="11" '
            f'fill="{TEXT_DIM}">{esc(r["language"][:14])}</text>'
        )
        svg.append(
            f'<text x="{cx+10:.1f}" y="{cy+64:.1f}" font-family="{FONT}" font-size="11" '
            f'fill="{ACCENT}">&#9733; {r["stars"]}</text>'
        )
        svg.append("</g>")

    # --- continuous snake body: a single stroke sliding along the smooth path ---
    svg.append(
        f'<path d="{path_d}" fill="none" stroke="{ACCENT_DIM}" stroke-width="12" '
        f'stroke-linecap="round" stroke-linejoin="round" opacity="0.35" pathLength="{path_len_units}"/>'
    )
    svg.append(
        f'<path d="{path_d}" fill="none" stroke="{ACCENT}" stroke-width="12" '
        f'stroke-linecap="round" stroke-linejoin="round" pathLength="{path_len_units}" '
        f'stroke-dasharray="{body_len:.1f} {path_len_units - body_len:.1f}">'
    )
    svg.append(
        '<animate attributeName="stroke-dashoffset" dur="{:.3f}s" repeatCount="indefinite" '
        'calcMode="linear" values="{};{}"/>'.format(
            total_dur, path_len_units + body_len, -body_len
        )
    )
    svg.append("</path>")

    # --- head marker, riding the front of the sliding body ---
    svg.append('<g>')
    svg.append('<circle r="9" fill="{}">'.format(ACCENT))
    svg.append(
        f'<animateMotion dur="{total_dur:.3f}s" repeatCount="indefinite" '
        f'rotate="auto" path="{path_d}"/>'
    )
    svg.append("</circle>")
    svg.append(f'<circle cx="-3.5" cy="-2.5" r="1.4" fill="{BG}">')
    svg.append(
        f'<animateMotion dur="{total_dur:.3f}s" repeatCount="indefinite" '
        f'rotate="auto" path="{path_d}"/>'
    )
    svg.append("</circle>")
    svg.append(f'<circle cx="3.5" cy="-2.5" r="1.4" fill="{BG}">')
    svg.append(
        f'<animateMotion dur="{total_dur:.3f}s" repeatCount="indefinite" '
        f'rotate="auto" path="{path_d}"/>'
    )
    svg.append("</circle>")
    svg.append("</g>")

    svg.append("</svg>")

    with open(out_path, "w") as f:
        f.write("\n".join(svg))
    return width, height, total_dur


if __name__ == "__main__":
    user = os.environ.get("GITHUB_USER", "Muzasio")
    token = os.environ.get("GITHUB_TOKEN")
    out = sys.argv[1] if len(sys.argv) > 1 else "dist/repo-snake.svg"
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

    w, h, dur = generate(repos, out)
    print(f"wrote {out}: {w}x{h}px, {len(repos)} repos, {dur:.1f}s loop")
