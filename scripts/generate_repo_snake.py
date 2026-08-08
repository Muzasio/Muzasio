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
PER_CELL = 0.9
SEG_SIZE = 16
SEG_COUNT = 6
SEG_GAP_T = 0.07
FONT = "'Courier New', monospace"

BG = "#0d1117"
CARD_FILL = "#161b22"
ACCENT = "#39ff14"
ACCENT_DIM = "#1f8f0c"
ACCENT_FLASH = "#baffb0"
TEXT_PRIMARY = "#e6edf3"
TEXT_DIM = "#8b949e"
BORDER_DIM = "#30363d"

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
    """Boustrophedon (serpentine) order: last cell of each row lines up
    vertically with the first cell of the next row, so connecting centers
    with straight lines is already an orthogonal, right-angle-only path."""
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


def straight_path(points):
    d = f"M {points[0][0]:.2f},{points[0][1]:.2f} "
    for x, y in points[1:]:
        d += f"L {x:.2f},{y:.2f} "
    return d.strip()


def cumulative_key_points(points):
    """keyPoints (0-1 along total path length) at each vertex, paired with
    uniform keyTimes (0-1 by index), so the head arrives at every card at
    exactly idx * PER_CELL regardless of uneven segment lengths."""
    dists = [0.0]
    for i in range(1, len(points)):
        (x0, y0), (x1, y1) = points[i - 1], points[i]
        dists.append(dists[-1] + math.hypot(x1 - x0, y1 - y0))
    total = dists[-1] if dists[-1] > 0 else 1.0
    key_points = [d / total for d in dists]
    n = len(points)
    key_times = [i / (n - 1) for i in range(n)]
    return key_points, key_times


def generate(repos, out_path):
    n = len(repos)
    centers, rows = grid_centers(n, COLS)
    width = PAD * 2 + COLS * CARD_W + (COLS - 1) * GAP
    height = PAD * 2 + rows * CARD_H + (rows - 1) * GAP
    total_dur = (n - 1) * PER_CELL if n > 1 else PER_CELL

    path_d = straight_path(centers)
    key_points, key_times = cumulative_key_points(centers)
    kp_str = ";".join(f"{k:.5f}" for k in key_points)
    kt_str = ";".join(f"{k:.5f}" for k in key_times)

    svg = []
    svg.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
        f'width="{width}" height="{height}">'
    )
    svg.append(f'<rect x="0" y="0" width="{width}" height="{height}" fill="{BG}" rx="10"/>')

    # cards: start dim, get "eaten" (lit up, one hard flash then settle bright)
    # exactly when the snake head reaches their center
    for idx, (cx0, cy0) in enumerate(centers):
        r = repos[idx]
        cx, cy = cx0 - CARD_W / 2, cy0 - CARD_H / 2
        eat_t = idx * PER_CELL
        settle_t = min(eat_t + 0.22, total_dur)
        rf_eat = eat_t / total_dur if total_dur else 0
        rf_settle = settle_t / total_dur if total_dur else 0
        lang_color = LANG_COLOR.get(r["language"], TEXT_DIM)

        svg.append(f'<g transform-origin="{cx0:.1f}px {cy0:.1f}px">')
        svg.append(
            '<animateTransform attributeName="transform" type="scale" additive="sum" '
            'dur="{:.3f}s" repeatCount="indefinite" calcMode="discrete" '
            'keyTimes="0;{:.5f};{:.5f};1" values="1;1;1.12;1"/>'.format(
                total_dur, rf_eat, rf_eat + 0.0001
            )
        )
        svg.append(
            f'<rect x="{cx:.1f}" y="{cy:.1f}" width="{CARD_W}" height="{CARD_H}" rx="8" '
            f'fill="{CARD_FILL}" stroke="{BORDER_DIM}" stroke-width="1.5">'
        )
        svg.append(
            '<animate attributeName="stroke" dur="{:.3f}s" repeatCount="indefinite" '
            'calcMode="discrete" keyTimes="0;{:.5f};{:.5f};1" values="{};{};{};{}"/>'.format(
                total_dur, rf_eat, rf_settle, BORDER_DIM, ACCENT_FLASH, ACCENT_FLASH, ACCENT_DIM
            )
        )
        svg.append("</rect>")
        svg.append(
            f'<text x="{cx+10:.1f}" y="{cy+24:.1f}" font-family="{FONT}" font-size="13" '
            f'font-weight="bold" fill="{TEXT_DIM}">'
        )
        svg.append(
            '<animate attributeName="fill" dur="{:.3f}s" repeatCount="indefinite" '
            'calcMode="discrete" keyTimes="0;{:.5f};1" values="{};{}"/>'.format(
                total_dur, rf_eat, TEXT_DIM, TEXT_PRIMARY
            )
        )
        svg.append(f'{esc(r["name"][:16])}</text>')
        svg.append(f'<circle cx="{cx+16:.1f}" cy="{cy+42:.1f}" r="4" fill="{BORDER_DIM}">')
        svg.append(
            '<animate attributeName="fill" dur="{:.3f}s" repeatCount="indefinite" '
            'calcMode="discrete" keyTimes="0;{:.5f};1" values="{};{}"/>'.format(
                total_dur, rf_eat, BORDER_DIM, lang_color
            )
        )
        svg.append("</circle>")
        svg.append(
            f'<text x="{cx+26:.1f}" y="{cy+46:.1f}" font-family="{FONT}" font-size="11" '
            f'fill="{TEXT_DIM}">{esc(r["language"][:14])}</text>'
        )
        svg.append(f'<text x="{cx+10:.1f}" y="{cy+64:.1f}" font-family="{FONT}" font-size="11" fill="{BORDER_DIM}">')
        svg.append(
            '<animate attributeName="fill" dur="{:.3f}s" repeatCount="indefinite" '
            'calcMode="discrete" keyTimes="0;{:.5f};1" values="{};{}"/>'.format(
                total_dur, rf_eat, BORDER_DIM, ACCENT
            )
        )
        svg.append(f'&#9733; {r["stars"]}</text>')
        svg.append("</g>")

    # snake: head + trailing body segments, all locked to the same straight
    # orthogonal path via identical keyPoints/keyTimes, offset only by begin=
    for seg in range(SEG_COUNT):
        fill = ACCENT if seg == 0 else ACCENT_DIM
        size = SEG_SIZE if seg == 0 else SEG_SIZE - 2
        delay = seg * SEG_GAP_T
        svg.append(f'<rect x="{-size/2:.1f}" y="{-size/2:.1f}" width="{size}" height="{size}" rx="3" fill="{fill}">')
        svg.append(
            f'<animateMotion dur="{total_dur:.3f}s" repeatCount="indefinite" '
            f'begin="-{delay:.3f}s" calcMode="linear" '
            f'keyPoints="{kp_str}" keyTimes="{kt_str}" path="{path_d}"/>'
        )
        svg.append("</rect>")

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
