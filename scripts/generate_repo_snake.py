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
PER_CELL = 0.45
SNAKE_SEGMENTS = 5
FONT = "'Courier New', monospace"

BG = "#0d1117"
CARD_FILL = "#161b22"
CARD_BORDER = "#30363d"
ACCENT = "#39ff14"
ACCENT_DIM = "#1f8f0c"
TEXT_PRIMARY = "#e6edf3"
TEXT_DIM = "#8b949e"

LANG_COLOR = {
    "Python": "#3572A5", "C++": "#f34b7d", "Shell": "#89e051",
    "JavaScript": "#f1e05a", "HTML": "#e34c26", "CSS": "#563d7c",
    "C": "#555555", "TypeScript": "#3178c6", "Jupyter Notebook": "#DA5B0B",
}


def fetch_repos(user, token=None, limit=24):
    req = urllib.request.Request(
        f"https://api.github.com/users/{user}/repos?sort=updated&per_page=100&type=owner"
    )
    req.add_header("Accept", "application/vnd.github+json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.load(resp)
    repos = [r for r in data if not r.get("fork") and not r.get("private")]
    repos = repos[:limit]
    return [
        {
            "name": r["name"],
            "language": r.get("language") or "N/A",
            "stars": r.get("stargazers_count", 0),
        }
        for r in repos
    ]


SAMPLE_REPOS = [
    {"name": "Cybersecurity-Resources", "language": "Shell", "stars": 3},
    {"name": "System_Utils", "language": "Shell", "stars": 1},
]


def build_path(n, cols):
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
            points.append((cx, cy, row, col, idx))
    return points, rows


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def generate(repos, out_path):
    n = len(repos)
    points, rows = build_path(n, COLS)
    width = PAD * 2 + COLS * CARD_W + (COLS - 1) * GAP
    height = PAD * 2 + rows * CARD_H + (rows - 1) * GAP

    total_cells = len(points)
    total_dur = total_cells * PER_CELL + SNAKE_SEGMENTS * PER_CELL
    path_d = "M " + " L ".join(f"{x:.1f},{y:.1f}" for x, y, *_ in points)

    svg = []
    svg.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
        f'width="{width}" height="{height}">'
    )
    svg.append(f'<rect x="0" y="0" width="{width}" height="{height}" fill="{BG}" rx="10"/>')

    for x, y, row, col, idx in points:
        r = repos[idx]
        cx = x - CARD_W / 2
        cy = y - CARD_H / 2
        reveal_time = (idx + SNAKE_SEGMENTS) * PER_CELL
        rf = min(reveal_time / total_dur, 0.97)
        rf2 = min(rf + 0.02, 0.99)
        lang_color = LANG_COLOR.get(r["language"], TEXT_DIM)

        svg.append(f'<g opacity="0">')
        svg.append(
            f'<animate attributeName="opacity" dur="{total_dur:.2f}s" '
            f'repeatCount="indefinite" calcMode="linear" '
            f'keyTimes="0;{rf:.4f};{rf2:.4f};1" values="0;0;1;1"/>'
        )
        svg.append(
            f'<rect x="{cx:.1f}" y="{cy:.1f}" width="{CARD_W}" height="{CARD_H}" rx="8" '
            f'fill="{CARD_FILL}" stroke="{ACCENT_DIM}" stroke-width="1.5"/>'
        )
        svg.append(
            f'<text x="{cx+10:.1f}" y="{cy+24:.1f}" font-family="{FONT}" font-size="13" '
            f'font-weight="bold" fill="{TEXT_PRIMARY}">{esc(r["name"][:16])}</text>'
        )
        svg.append(
            f'<circle cx="{cx+16:.1f}" cy="{cy+42:.1f}" r="4" fill="{lang_color}"/>'
        )
        svg.append(
            f'<text x="{cx+26:.1f}" y="{cy+46:.1f}" font-family="{FONT}" font-size="11" '
            f'fill="{TEXT_DIM}">{esc(r["language"][:14])}</text>'
        )
        svg.append(
            f'<text x="{cx+10:.1f}" y="{cy+64:.1f}" font-family="{FONT}" font-size="11" '
            f'fill="{ACCENT}">&#9733; {r["stars"]}</text>'
        )
        svg.append("</g>")

    for seg in range(SNAKE_SEGMENTS):
        begin = seg * PER_CELL
        radius = 9 if seg == 0 else max(7 - seg * 0.6, 3)
        fill = ACCENT if seg == 0 else BG
        stroke = ACCENT if seg > 0 else "none"
        group = ['<g opacity="0">']
        group.append(
            f'<animate attributeName="opacity" begin="0s" dur="0.01s" fill="freeze" values="1"/>'
        )
        inner = f'<circle cx="0" cy="0" r="{radius:.1f}" fill="{fill}" stroke="{stroke}" stroke-width="2"/>'
        if seg == 0:
            inner += (
                f'<circle cx="-3.5" cy="-2.5" r="1.4" fill="{BG}"/>'
                f'<circle cx="3.5" cy="-2.5" r="1.4" fill="{BG}"/>'
            )
        group.append(inner)
        group.append(
            f'<animateMotion dur="{total_dur:.2f}s" begin="{begin:.2f}s" '
            f'repeatCount="indefinite" rotate="auto" path="{path_d}"/>'
        )
        group.append("</g>")
        svg.append("".join(group))

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
