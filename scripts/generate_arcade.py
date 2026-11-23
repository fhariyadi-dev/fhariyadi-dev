#!/usr/bin/env python3
"""
Generates an original, copyright-free animated SVG display:
"YUNA-BOT // COMMIT DEFENDER" — combining a floating cyber-robot mascot
with the user's REAL 53-week x 7-day GitHub contribution calendar.

Data source priority:
1. --html <path> (local saved https://github.com/users/<user>/contributions HTML)
2. Live public fetch from https://github.com/users/<user>/contributions (no token required!)
3. GitHub GraphQL API if GITHUB_TOKEN is provided
"""

import argparse
import datetime as dt
import json
import os
import re
import urllib.request
from pathlib import Path

USERNAME = os.environ.get("GITHUB_USERNAME", "fhariyadi-dev")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")

LEVEL_COLORS = {
    0: "#161B22",
    1: "#0E4429",
    2: "#006D32",
    3: "#26A641",
    4: "#39D353",
}


def parse_contributions_html(html: str) -> list[tuple[str, int]]:
    matches = re.findall(r'data-date="(\d{4}-\d{2}-\d{2})"[^>]*data-level="(\d)"', html)
    if not matches:
        rev = re.findall(r'data-level="(\d)"[^>]*data-date="(\d{4}-\d{2}-\d{2})"', html)
        matches = [(d, l) for l, d in rev]
    dedup = {d: int(l) for d, l in matches}
    return sorted(dedup.items())


def fetch_public_contributions(username: str) -> list[tuple[str, int]]:
    url = f"https://github.com/users/{username}/contributions"
    req = urllib.request.Request(url, headers={"User-Agent": "yuna-arcade-generator/2.0"})
    with urllib.request.urlopen(req, timeout=20) as resp:
        html = resp.read().decode("utf-8")
    days = parse_contributions_html(html)
    if not days:
        raise RuntimeError("No contribution cells found in public HTML")
    return days


def fetch_graphql_contributions(username: str, token: str) -> list[tuple[str, int]]:
    query = """
    query($login: String!) {
      user(login: $login) {
        contributionsCollection {
          contributionCalendar {
            weeks {
              contributionDays {
                date
                contributionCount
              }
            }
          }
        }
      }
    }
    """
    payload = json.dumps({"query": query, "variables": {"login": username}}).encode("utf-8")
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=payload,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": "yuna-arcade-generator/2.0",
        },
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    weeks = data["data"]["user"]["contributionsCollection"]["contributionCalendar"]["weeks"]
    days: list[tuple[str, int]] = []
    for week in weeks:
        for day in week["contributionDays"]:
            c = day["contributionCount"]
            lvl = 0 if c == 0 else (1 if c <= 1 else (2 if c <= 3 else (3 if c <= 6 else 4)))
            days.append((day["date"], lvl))
    days.sort()
    return days


def arrange_calendar_columns(days: list[tuple[str, int]]) -> tuple[list[list[int | None]], list[tuple[int, str]], int]:
    """
    Arrange real (YYYY-MM-DD, level) entries into GitHub's exact 7-row (Sun=0..Sat=6)
    weekly columns so every single green square matches GitHub's profile graph 1-to-1.
    """
    parsed = [(dt.date.fromisoformat(d), lvl) for d, lvl in days]
    first_date = parsed[0][0]
    # GitHub calendar starts each column on Sunday (Python weekday(): Mon=0..Sun=6 -> Sun=0..Sat=6)
    first_sun = first_date - dt.timedelta(days=(first_date.weekday() + 1) % 7)
    last_date = parsed[-1][0]
    num_weeks = ((last_date - first_sun).days // 7) + 1

    # Keep at most 53 most recent weeks
    if num_weeks > 53:
        shift = num_weeks - 53
        first_sun += dt.timedelta(days=shift * 7)
        num_weeks = 53

    # columns[col][row] where row 0=Sun..6=Sat
    columns: list[list[int | None]] = [[None] * 7 for _ in range(num_weeks)]
    active_days = 0
    for date_obj, lvl in parsed:
        delta = (date_obj - first_sun).days
        if delta < 0:
            continue
        col = delta // 7
        row = delta % 7
        if col < num_weeks:
            columns[col][row] = lvl
            if lvl > 0:
                active_days += 1

    # Month labels at the first week where a month starts
    month_labels: list[tuple[int, str]] = []
    seen_ym: set[tuple[int, int]] = set()
    for col in range(num_weeks):
        week_date = first_sun + dt.timedelta(days=col * 7)
        ym = (week_date.year, week_date.month)
        if ym not in seen_ym:
            seen_ym.add(ym)
            # Avoid crowding if too close to previous label
            if not month_labels or col - month_labels[-1][0] >= 3:
                month_labels.append((col, week_date.strftime("%b")))

    return columns, month_labels, active_days


def pick_empty_bug_cells(columns: list[list[int | None]]) -> list[tuple[int, int]]:
    """
    Choose 3 empty (level 0) cells in the top rows across the left/middle/right
    third of the calendar so pixel bugs NEVER obscure a real green contribution tile.
    """
    num_weeks = len(columns)
    targets = [int(num_weeks * 0.22), int(num_weeks * 0.50), int(num_weeks * 0.78)]
    chosen: list[tuple[int, int]] = []
    for target_col in targets:
        found = None
        for offset in range(0, 8):
            for c in (target_col + offset, target_col - offset):
                if 1 <= c < num_weeks - 1:
                    for r in (1, 0, 2):
                        if columns[c][r] == 0:
                            found = (r, c)
                            break
                if found:
                    break
            if found:
                break
        if found:
            chosen.append(found)
    return chosen


def build_svg(columns: list[list[int | None]], month_labels: list[tuple[int, str]], active_days: int) -> str:
    num_weeks = len(columns)
    tile = 9
    gap = 2
    step = tile + gap
    grid_w = num_weeks * step - gap
    start_x = int(252 + (626 - grid_w) / 2)
    start_y = 98

    bug_cells = pick_empty_bug_cells(columns)
    bug_set = set(bug_cells)

    # Month header labels
    months_svg = []
    for col, label in month_labels:
        mx = start_x + col * step
        months_svg.append(
            f'    <text x="{mx}" y="90" class="mono" font-size="8.5" fill="#64748B">{label}</text>'
        )

    # Exact real GitHub contribution tiles (53 weeks x 7 days)
    tiles_svg = []
    for c in range(num_weeks):
        for r in range(7):
            lvl = columns[c][r]
            if lvl is None:
                continue
            x = start_x + c * step
            y = start_y + r * step
            if (r, c) in bug_set:
                tiles_svg.append(
                    f'    <rect x="{x}" y="{y}" width="{tile}" height="{tile}" rx="2" fill="#161B22" stroke="#F59E0B" stroke-opacity="0.45" stroke-width="0.7"/>'
                )
            else:
                fill = LEVEL_COLORS.get(lvl, "#161B22")
                tiles_svg.append(
                    f'    <rect x="{x}" y="{y}" width="{tile}" height="{tile}" rx="2" fill="{fill}"/>'
                )

    # Compact pixel-bug sprites strictly on empty cells
    bugs_svg = []
    for idx, (r, c) in enumerate(bug_cells):
        cx = start_x + c * step + tile / 2
        cy = start_y + r * step + tile / 2
        delay = idx * 0.65
        bugs_svg.append(f"""    <g class="bug-target" style="animation-delay: {delay:.2f}s;">
      <rect x="{cx - 4.5:.1f}" y="{cy - 3:.1f}" width="9" height="6" rx="1.8" fill="#F59E0B"/>
      <rect x="{cx - 3:.1f}" y="{cy - 1.5:.1f}" width="1.8" height="1.8" rx="0.4" fill="#090D16"/>
      <rect x="{cx + 1.2:.1f}" y="{cy - 1.5:.1f}" width="1.8" height="1.8" rx="0.4" fill="#090D16"/>
      <line x1="{cx - 3:.1f}" y1="{cy - 3:.1f}" x2="{cx - 4.5:.1f}" y2="{cy - 5:.1f}" stroke="#FBBF24" stroke-width="1" stroke-linecap="round"/>
      <line x1="{cx + 3:.1f}" y1="{cy - 3:.1f}" x2="{cx + 4.5:.1f}" y2="{cy - 5:.1f}" stroke="#FBBF24" stroke-width="1" stroke-linecap="round"/>
    </g>""")

    months_str = "\n".join(months_svg)
    tiles_str = "\n".join(tiles_svg)
    bugs_str = "\n".join(bugs_svg)

    return f"""<svg width="900" height="284" viewBox="0 0 900 284" fill="none" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <linearGradient id="arenaBg" x1="0" y1="0" x2="900" y2="284" gradientUnits="userSpaceOnUse">
      <stop offset="0%" stop-color="#090D16"/>
      <stop offset="50%" stop-color="#0D1424"/>
      <stop offset="100%" stop-color="#091520"/>
    </linearGradient>

    <radialGradient id="podGlow" cx="0" cy="0" r="1" gradientUnits="userSpaceOnUse" gradientTransform="translate(129 212) scale(76 22)">
      <stop offset="0%" stop-color="#10B981" stop-opacity="0.45"/>
      <stop offset="100%" stop-color="#10B981" stop-opacity="0"/>
    </radialGradient>

    <radialGradient id="visorGlow" cx="0" cy="0" r="1" gradientUnits="userSpaceOnUse" gradientTransform="translate(129 124) scale(55 40)">
      <stop offset="0%" stop-color="#06B6D4" stop-opacity="0.22"/>
      <stop offset="100%" stop-color="#06B6D4" stop-opacity="0"/>
    </radialGradient>

    <linearGradient id="neonAccent" x1="0" y1="0" x2="900" y2="0" gradientUnits="userSpaceOnUse">
      <stop offset="0%" stop-color="#F59E0B"/>
      <stop offset="45%" stop-color="#10B981"/>
      <stop offset="100%" stop-color="#06B6D4"/>
    </linearGradient>

    <linearGradient id="laserGrad" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="#67E8F9"/>
      <stop offset="60%" stop-color="#10B981"/>
      <stop offset="100%" stop-color="#10B981" stop-opacity="0"/>
    </linearGradient>

    <pattern id="arcadeGrid" width="24" height="24" patternUnits="userSpaceOnUse">
      <path d="M 24 0 L 0 0 0 24" fill="none" stroke="#1E293B" stroke-width="0.6" opacity="0.4"/>
    </pattern>

    <clipPath id="outerClip">
      <rect x="1" y="1" width="898" height="282" rx="16"/>
    </clipPath>
  </defs>

  <style>
    .mono {{ font-family: 'JetBrains Mono', 'Fira Code', 'SFMono-Regular', Consolas, monospace; }}
    .sans {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; }}

    @keyframes botFloat {{
      0%, 100% {{ transform: translateY(0px); }}
      50% {{ transform: translateY(-7px); }}
    }}
    @keyframes eyeBlink {{
      0%, 44%, 48%, 100% {{ transform: scaleY(1); }}
      46% {{ transform: scaleY(0.12); }}
    }}
    @keyframes pulseCore {{
      0%, 100% {{ opacity: 1; }}
      50% {{ opacity: 0.45; }}
    }}
    @keyframes eqBar1 {{
      0%, 100% {{ height: 6px; y: 234px; }}
      50% {{ height: 14px; y: 226px; }}
    }}
    @keyframes eqBar2 {{
      0%, 100% {{ height: 13px; y: 227px; }}
      50% {{ height: 5px; y: 235px; }}
    }}
    @keyframes eqBar3 {{
      0%, 100% {{ height: 8px; y: 232px; }}
      50% {{ height: 15px; y: 225px; }}
    }}
    @keyframes dronePatrol {{
      0% {{ transform: translateX(0px); }}
      24% {{ transform: translateX(155px); }}
      52% {{ transform: translateX(315px); }}
      78% {{ transform: translateX(480px); }}
      100% {{ transform: translateX(0px); }}
    }}
    @keyframes laserPulse {{
      0% {{ transform: translateY(0px); opacity: 0; }}
      15% {{ opacity: 1; }}
      75% {{ transform: translateY(-88px); opacity: 0.95; }}
      100% {{ transform: translateY(-102px); opacity: 0; }}
    }}
    @keyframes bugHover {{
      0%, 100% {{ transform: translateY(0px); }}
      50% {{ transform: translateY(-2px); }}
    }}
    @keyframes ledBlink {{
      0%, 100% {{ opacity: 1; }}
      50% {{ opacity: 0.3; }}
    }}

    .yuna-bot {{ animation: botFloat 3.6s ease-in-out infinite; }}
    .bot-eyes {{ transform-box: fill-box; transform-origin: center; animation: eyeBlink 4.2s infinite; }}
    .core-glow {{ animation: pulseCore 2s ease-in-out infinite; }}
    .eq1 {{ animation: eqBar1 1.1s ease-in-out infinite; }}
    .eq2 {{ animation: eqBar2 0.85s ease-in-out infinite; }}
    .eq3 {{ animation: eqBar3 1.3s ease-in-out infinite; }}
    .drone-group {{ animation: dronePatrol 10s ease-in-out infinite; }}
    .laser-beam {{ animation: laserPulse 1.5s linear infinite; }}
    .bug-target {{ animation: bugHover 2s ease-in-out infinite; }}
    .led-blink {{ animation: ledBlink 1.8s ease-in-out infinite; }}
  </style>

  <g clip-path="url(#outerClip)">
    <!-- Background -->
    <rect width="900" height="284" fill="url(#arenaBg)"/>
    <rect width="900" height="284" fill="url(#arcadeGrid)"/>

    <!-- Top Bezel Header -->
    <rect x="0" y="0" width="900" height="36" fill="#0B1120" fill-opacity="0.92"/>
    <line x1="0" y1="36" x2="900" y2="36" stroke="#1E293B" stroke-width="1"/>
    <circle cx="22" cy="18" r="4.5" fill="#10B981" class="led-blink"/>
    <text x="36" y="22" class="mono" font-size="11.5" font-weight="700" fill="#E2E8F0" letter-spacing="0.6">ARCADE.SYS // YUNA-BOT COMMIT DEFENDER</text>

    <rect x="614" y="8" width="144" height="20" rx="6" fill="#111C33" stroke="#1E293B" stroke-width="1"/>
    <text x="686" y="21.5" text-anchor="middle" class="mono" font-size="10" fill="#38BDF8">LIVE SYNC · {active_days} ACTIVE DAYS</text>

    <rect x="766" y="8" width="114" height="20" rx="6" fill="#10B981" fill-opacity="0.12" stroke="#10B981" stroke-opacity="0.4" stroke-width="1"/>
    <text x="823" y="21.5" text-anchor="middle" class="mono" font-size="10" font-weight="700" fill="#6EE7B7">53W REAL GRID</text>

    <!-- LEFT HOLO-POD: ORIGINAL YUNA-BOT MASCOT -->
    <rect x="22" y="50" width="214" height="200" rx="12" fill="#0B1120" fill-opacity="0.88" stroke="#1E293B" stroke-width="1.2"/>
    <rect x="22" y="50" width="214" height="24" rx="12" fill="#111C33"/>
    <rect x="22" y="64" width="214" height="10" fill="#111C33"/>
    <line x1="22" y1="74" x2="236" y2="74" stroke="#1E293B" stroke-width="1"/>
    <text x="34" y="66" class="mono" font-size="10" font-weight="700" fill="#34D399">COMPANION // YUNA-BOT</text>
    <circle cx="222" cy="62" r="3" fill="#06B6D4"/>

    <!-- Holographic Base Pad -->
    <ellipse cx="129" cy="212" rx="62" ry="12" fill="url(#podGlow)"/>
    <ellipse cx="129" cy="212" rx="44" ry="6.5" fill="none" stroke="#10B981" stroke-opacity="0.55" stroke-width="1.2"/>
    <ellipse cx="129" cy="212" rx="24" ry="3.5" fill="#10B981" fill-opacity="0.22"/>

    <!-- Floating Cyber-Robot Character -->
    <g class="yuna-bot">
      <circle cx="129" cy="126" r="52" fill="url(#visorGlow)"/>
      <line x1="129" y1="96" x2="129" y2="84" stroke="#38BDF8" stroke-width="2.2" stroke-linecap="round"/>
      <circle cx="129" cy="82" r="4" fill="#10B981" class="core-glow"/>
      <circle cx="129" cy="82" r="7" fill="none" stroke="#10B981" stroke-opacity="0.35" stroke-width="1"/>

      <rect x="85" y="114" width="8" height="20" rx="4" fill="#1E293B" stroke="#38BDF8" stroke-width="1.2"/>
      <rect x="165" y="114" width="8" height="20" rx="4" fill="#1E293B" stroke="#38BDF8" stroke-width="1.2"/>

      <rect x="93" y="96" width="72" height="52" rx="18" fill="#111C33" stroke="#38BDF8" stroke-width="1.8"/>
      <rect x="101" y="106" width="56" height="32" rx="11" fill="#060B14" stroke="#1E293B" stroke-width="1"/>

      <g class="bot-eyes">
        <rect x="111" y="115" width="11" height="11" rx="3.5" fill="#10B981"/>
        <rect x="136" y="115" width="11" height="11" rx="3.5" fill="#10B981"/>
        <circle cx="114.5" cy="118.5" r="2" fill="#ECFDF5"/>
        <circle cx="139.5" cy="118.5" r="2" fill="#ECFDF5"/>
      </g>
      <path d="M 123 130 Q 129 134 135 130" stroke="#38BDF8" stroke-width="1.8" stroke-linecap="round" fill="none"/>

      <rect x="84" y="156" width="12" height="22" rx="6" fill="#0F172A" stroke="#10B981" stroke-width="1.4"/>
      <rect x="162" y="156" width="12" height="22" rx="6" fill="#0F172A" stroke="#10B981" stroke-width="1.4"/>

      <rect x="103" y="153" width="52" height="36" rx="12" fill="#111C33" stroke="#38BDF8" stroke-width="1.6"/>
      <polygon points="129,161 137,171 129,181 121,171" fill="#10B981" fill-opacity="0.25" stroke="#34D399" stroke-width="1.5" class="core-glow"/>
      <circle cx="129" cy="171" r="2.8" fill="#67E8F9"/>

      <path d="M 121 191 L 129 202 L 137 191 Z" fill="#06B6D4" fill-opacity="0.7" class="core-glow"/>
    </g>

    <!-- Mini Equalizer & Label -->
    <rect x="34" y="226" width="3.5" height="14" rx="1.5" fill="#10B981" class="eq1"/>
    <rect x="40" y="229" width="3.5" height="11" rx="1.5" fill="#06B6D4" class="eq2"/>
    <rect x="46" y="227" width="3.5" height="13" rx="1.5" fill="#818CF8" class="eq3"/>
    <text x="58" y="237" class="mono" font-size="10" fill="#94A3B8">AI CO-PILOT: ACTIVE</text>

    <!-- RIGHT ARENA: REAL 53-WEEK GITHUB CONTRIBUTION MATRIX -->
    <rect x="252" y="50" width="626" height="200" rx="12" fill="#0B1120" fill-opacity="0.88" stroke="#1E293B" stroke-width="1.2"/>
    <rect x="252" y="50" width="626" height="24" rx="12" fill="#111C33"/>
    <rect x="252" y="64" width="626" height="10" fill="#111C33"/>
    <line x1="252" y1="74" x2="878" y2="74" stroke="#1E293B" stroke-width="1"/>

    <text x="268" y="66" class="mono" font-size="10" font-weight="700" fill="#38BDF8">ARENA // REAL GITHUB CONTRIBUTIONS ({USERNAME})</text>
    <circle cx="716" cy="62" r="3" fill="#F59E0B"/>
    <text x="724" y="66" class="mono" font-size="9" fill="#CBD5E1">BUGS</text>
    <circle cx="766" cy="62" r="3" fill="#39D353"/>
    <text x="774" y="66" class="mono" font-size="9" fill="#CBD5E1">COMMITS</text>
    <circle cx="830" cy="62" r="3" fill="#38BDF8"/>
    <text x="838" y="66" class="mono" font-size="9" fill="#CBD5E1">DRONE</text>

    <!-- Month Labels -->
{months_str}

    <!-- Real Contribution Grid Tiles (53 Weeks x 7 Days) -->
{tiles_str}

    <!-- Animated Pixel Bug Targets (strictly on empty cells) -->
{bugs_str}

    <!-- Patrolling Mini Cyber-Drone + Laser Fire -->
    <g class="drone-group">
      <rect x="311" y="190" width="2.8" height="16" rx="1.4" fill="url(#laserGrad)" class="laser-beam"/>
      <polygon points="312.4,200 324,212 318.5,215 312.4,211 306.3,215 300.8,212" fill="#38BDF8"/>
      <polygon points="312.4,203 316.5,210 308.3,210" fill="#ECFDF5"/>
      <rect x="309.5" y="213" width="5.8" height="3.5" rx="1.7" fill="#10B981" class="core-glow"/>
    </g>

    <!-- Legend Bottom Right inside Arena -->
    <text x="748" y="238" class="mono" font-size="8.5" fill="#64748B">Less</text>
    <rect x="774" y="230" width="8" height="8" rx="1.8" fill="#161B22"/>
    <rect x="785" y="230" width="8" height="8" rx="1.8" fill="#0E4429"/>
    <rect x="796" y="230" width="8" height="8" rx="1.8" fill="#006D32"/>
    <rect x="807" y="230" width="8" height="8" rx="1.8" fill="#26A641"/>
    <rect x="818" y="230" width="8" height="8" rx="1.8" fill="#39D353"/>
    <text x="831" y="238" class="mono" font-size="8.5" fill="#64748B">More</text>

    <!-- Bottom Status Ticker -->
    <text x="26" y="271" class="mono" font-size="10.5" fill="#64748B">&gt; SYNCED FROM GITHUB.COM/{USERNAME.upper()} · ZAP BUGS · SHIP COMMITS</text>
    <text x="876" y="271" text-anchor="end" class="mono" font-size="10.5" font-weight="700" fill="#34D399">SHIELD ██████ 100%</text>

    <!-- Bottom Neon Bar -->
    <rect x="0" y="280" width="900" height="4" fill="url(#neonAccent)"/>
  </g>

  <rect x="1" y="1" width="898" height="282" rx="16" stroke="#1E293B" stroke-width="1.4"/>
</svg>
"""


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--html", type=str, default="", help="Optional path to saved GitHub contributions HTML")
    args = parser.parse_args()

    days: list[tuple[str, int]]
    if args.html:
        days = parse_contributions_html(Path(args.html).read_text(encoding="utf-8"))
    else:
        try:
            days = fetch_public_contributions(USERNAME)
        except Exception:
            if GITHUB_TOKEN:
                days = fetch_graphql_contributions(USERNAME, GITHUB_TOKEN)
            else:
                raise

    columns, month_labels, active_days = arrange_calendar_columns(days)
    svg = build_svg(columns, month_labels, active_days)

    repo_root = Path(__file__).resolve().parent.parent
    out_path = repo_root / "assets" / "yuna-arcade.svg"
    out_path.write_text(svg, encoding="utf-8")
    print(f"Generated {out_path} ({len(svg)} bytes, {len(columns)} weeks, {active_days} active days)")


if __name__ == "__main__":
    main()
