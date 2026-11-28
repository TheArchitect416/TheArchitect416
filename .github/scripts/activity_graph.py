"""Render a line graph of daily GitHub contributions (last 31 days) as an SVG.

Usage: GITHUB_TOKEN=... python activity_graph.py <username> <output.svg>
"""
import datetime as dt
import json
import os
import sys
import urllib.request

DAYS = 31
W, H = 1000, 340
PAD_L, PAD_R, PAD_T, PAD_B = 60, 30, 60, 50

BG, TITLE, LINE, POINT, AXIS, GRID = "#1a1b27", "#70a5fd", "#bf91f3", "#38bdae", "#a9b1d6", "#2a2e42"


def fetch(user: str, token: str) -> list[tuple[dt.date, int]]:
    to = dt.datetime.now(dt.timezone.utc)
    frm = to - dt.timedelta(days=DAYS + 1)
    query = """query($u:String!,$f:DateTime!,$t:DateTime!){user(login:$u){
      contributionsCollection(from:$f,to:$t){contributionCalendar{weeks{contributionDays{date contributionCount}}}}}}"""
    body = json.dumps({"query": query, "variables": {"u": user, "f": frm.isoformat(), "t": to.isoformat()}}).encode()
    req = urllib.request.Request("https://api.github.com/graphql", data=body,
                                 headers={"Authorization": f"bearer {token}", "Content-Type": "application/json"})
    data = json.load(urllib.request.urlopen(req))
    weeks = data["data"]["user"]["contributionsCollection"]["contributionCalendar"]["weeks"]
    days = [(dt.date.fromisoformat(d["date"]), d["contributionCount"]) for w in weeks for d in w["contributionDays"]]
    return sorted(days)[-DAYS:]


def render(user: str, days: list[tuple[dt.date, int]]) -> str:
    peak = max([c for _, c in days] + [1])
    step = max(1, -(-peak // 5))  # ~5 gridlines
    top = step * -(-peak // step)
    pw, ph = W - PAD_L - PAD_R, H - PAD_T - PAD_B
    x = lambda i: PAD_L + pw * i / (len(days) - 1)
    y = lambda c: PAD_T + ph * (1 - c / top)

    pts = [(x(i), y(c)) for i, (_, c) in enumerate(days)]
    line = " ".join(f"{px:.1f},{py:.1f}" for px, py in pts)
    area = f"{PAD_L},{PAD_T + ph} {line} {PAD_L + pw},{PAD_T + ph}"

    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" font-family="Segoe UI, Ubuntu, sans-serif">',
           '<defs><linearGradient id="g" x1="0" y1="0" x2="0" y2="1">'
           f'<stop offset="0" stop-color="{LINE}" stop-opacity="0.45"/><stop offset="1" stop-color="{LINE}" stop-opacity="0"/></linearGradient></defs>',
           f'<rect width="{W}" height="{H}" rx="6" fill="{BG}"/>',
           f'<text x="{W / 2}" y="34" text-anchor="middle" fill="{TITLE}" font-size="20" font-weight="600">{user}\'s Contribution Graph</text>']
    for v in range(0, top + 1, step):
        gy = y(v)
        out.append(f'<line x1="{PAD_L}" y1="{gy:.1f}" x2="{PAD_L + pw}" y2="{gy:.1f}" stroke="{GRID}"/>')
        out.append(f'<text x="{PAD_L - 10}" y="{gy + 4:.1f}" text-anchor="end" fill="{AXIS}" font-size="12">{v}</text>')
    for i, (d, _) in enumerate(days):
        out.append(f'<text x="{x(i):.1f}" y="{PAD_T + ph + 20}" text-anchor="middle" fill="{AXIS}" font-size="11">{d.day}</text>')
    out.append(f'<text x="{W / 2}" y="{H - 8}" text-anchor="middle" fill="{AXIS}" font-size="12">Days (last {DAYS})</text>')
    out.append(f'<text x="16" y="{PAD_T + ph / 2}" text-anchor="middle" fill="{AXIS}" font-size="12" transform="rotate(-90 16 {PAD_T + ph / 2})">Contributions</text>')
    out.append(f'<polygon points="{area}" fill="url(#g)"/>')
    out.append(f'<polyline points="{line}" fill="none" stroke="{LINE}" stroke-width="2.5" stroke-linejoin="round"/>')
    for (px, py), (d, c) in zip(pts, days):
        out.append(f'<circle cx="{px:.1f}" cy="{py:.1f}" r="3.5" fill="{POINT}"><title>{d.isoformat()}: {c}</title></circle>')
    out.append("</svg>")
    return "\n".join(out)


if __name__ == "__main__":
    user, path = sys.argv[1], sys.argv[2]
    days = fetch(user, os.environ["GITHUB_TOKEN"])
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(render(user, days))
