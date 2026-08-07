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
FONT = "'Courier New', monospace"

BG = "#0d1117"
CARD_FILL = "#161b22"
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


def grid_positions(n, cols):
    rows = math.ceil(n / cols)
    points = []
    for row in range(rows):
        row_cols = range(cols) if row % 2 == 0 else range(cols - 1, -1, -1)
        for col in row_cols:
            idx = row * cols + (col if row % 2 == 0 else cols - 1 - col)
            if idx >= n:
                continue
            x = PAD + col * (CARD_W + GAP)
            y = PAD + row * (CARD_H + GAP)
            points.append((x, y))
    return points, rows


def generate(repos, out_path):
    n = len(repos)
    positions, rows = grid_positions(n, COLS)
    width = PAD * 2 + COLS * CARD_W + (COLS - 1) * GAP
    height = PAD * 2 + rows * CARD_H + (rows - 1) * GAP
    total_dur = n * PER_CELL

    svg = []
    svg.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
        f'width="{width}" height="{height}">'
    )
    svg.append(f'<rect x="0" y="0" width="{width}" height="{height}" fill="{BG}" rx="10"/>')

    for idx, (cx, cy) in enumerate(positions):
        r = repos[idx]
        reveal_t = idx * PER_CELL
        flash_end_t = min(reveal_t + 0.30, total_dur)
        rf_reveal = reveal_t / total_dur
        rf_flash_end = flash_end_t / total_dur
        cx0, cy0 = cx + CARD_W / 2, cy + CARD_H / 2
        lang_color = LANG_COLOR.get(r["language"], TEXT_DIM)

        svg.append(f'<g transform-origin="{cx0:.1f}px {cy0:.1f}px" opacity="0">')
        svg.append(
            '<animate attributeName="opacity" dur="{:.3f}s" repeatCount="indefinite" '
            'calcMode="discrete" keyTimes="0;{:.4f};{:.4f};1" values="0;0;1;1"/>'.format(
                total_dur, rf_reveal, rf_reveal + 0.0001
            )
        )
        svg.append(
            '<animateTransform attributeName="transform" type="scale" additive="sum" '
            'dur="{:.3f}s" repeatCount="indefinite" calcMode="spline" '
            'keyTimes="0;{:.4f};{:.4f};1" values="0.85;0.85;1;1" '
            'keySplines="0.4 0 0.2 1;0.4 0 0.2 1;0 0 1 1"/>'.format(
                total_dur, rf_reveal, rf_reveal + 0.05
            )
        )
        svg.append(
            f'<rect x="{cx:.1f}" y="{cy:.1f}" width="{CARD_W}" height="{CARD_H}" rx="8" '
            f'fill="{CARD_FILL}" stroke="{ACCENT_DIM}" stroke-width="1.5">'
        )
        svg.append(
            '<animate attributeName="stroke" dur="{:.3f}s" repeatCount="indefinite" '
            'calcMode="discrete" keyTimes="0;{:.4f};{:.4f};1" values="{};{};{};{}"/>'.format(
                total_dur, rf_reveal, rf_flash_end, ACCENT_DIM, ACCENT_FLASH, ACCENT_FLASH, ACCENT_DIM
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
