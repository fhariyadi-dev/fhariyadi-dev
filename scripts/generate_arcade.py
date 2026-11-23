#!/usr/bin/env python3
"""
Generates an original, copyright-free animated SVG display:
"YUNA-BOT // COMMIT DEFENDER" — combining a floating cyber-robot mascot
with a GitHub contribution-grid arcade mini-game.

When run inside GitHub Actions with GITHUB_TOKEN, it fetches the user's real
contribution heatmap via GraphQL. Offline, it renders a clean emerald matrix.
"""

import json
import os
import urllib.request
from pathlib import Path

USERNAME = os.environ.get("GITHUB_USERNAME", "fhariyadi-dev")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")

LEVEL_COLORS = {
    0: "#151D2B",
    1: "#0E4429",
    2: "#006D32",
    3: "#26A641",
    4: "#39D353",
}

# Fallback contribution heatmap (28 weeks x 6 rows) inspired by active sprint cadence
FALLBACK_GRID = [
    [0, 1, 0, 0, 1, 0, 2, 1, 0, 1, 2, 0, 1, 3, 2, 1, 0, 2, 1, 0, 0, 1, 2, 1, 0, 2, 3, 4],
    [1, 0, 0, 1, 2, 0, 1, 0, 1, 2, 3, 1, 0, 2, 1, 0, 1, 3, 2, 1, 0, 1, 0, 2, 1, 3, 4, 3],
    [0, 0, 1, 2, 1, 0, 0, 1, 2, 1, 0, 2, 1, 4, 3, 2, 1, 0, 2, 1, 1, 0, 2, 3, 2, 1, 3, 4],
    [0, 1, 0, 1, 0, 1, 2, 0, 1, 3, 2, 1, 0, 2, 4, 1, 0, 1, 3, 2, 0, 1, 1, 2, 3, 2, 4, 3],
    [1, 0, 1, 0, 2, 1, 0, 1, 0, 2, 1, 0, 2, 1, 2, 3, 1, 2, 0, 1, 2, 1, 0, 2, 4, 3, 2, 4],
    [0, 0, 0, 1, 1, 0, 1, 0, 2, 1, 0, 1, 1, 0, 2, 1, 2, 1, 1, 0, 1, 2, 1, 0, 2, 3, 4, 3],
]


def fetch_github_contributions() -> list[list[int]] | None:
    if not GITHUB_TOKEN:
        return None
    query = """
    query($login: String!) {
      user(login: $login) {
        contributionsCollection {
          contributionCalendar {
            weeks {
              contributionDays {
                contributionCount
              }
            }
          }
        }
      }
    }
    """
    payload = json.dumps({"query": query, "variables": {"login": USERNAME}}).encode("utf-8")
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=payload,
        headers={
            "Authorization": f"Bearer {GITHUB_TOKEN}",
            "Content-Type": "application/json",
            "User-Agent": "yuna-arcade-generator",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        weeks = data["data"]["user"]["contributionsCollection"]["contributionCalendar"]["weeks"]
        recent = weeks[-28:]
        rows = [[0] * len(recent) for _ in range(6)]
        for col, week in enumerate(recent):
            days = week["contributionDays"][:6]
            for row, day in enumerate(days):
                c = day["contributionCount"]
                level = 0 if c == 0 else (1 if c <= 1 else (2 if c <= 3 else (3 if c <= 6 else 4)))
                rows[row][col] = level
        return rows
    except Exception:
        return None


def build_svg(grid: list[list[int]]) -> str:
    cols = len(grid[0])
    rows = len(grid)
    tile = 14
    gap = 5
    start_x = 294
    start_y = 88

    # Pixel bug positions inside grid (row, col)
    bug_cells = [(1, 6), (0, 14), (1, 22)]

    tiles_svg = []
    for r in range(rows):
        for c in range(cols):
            x = start_x + c * (tile + gap)
            y = start_y + r * (tile + gap)
            if (r, c) in bug_cells:
                # Render subtle dark backing cell behind animated bug sprite
                tiles_svg.append(
                    f'    <rect x="{x}" y="{y}" width="{tile}" height="{tile}" rx="3" fill="#151D2B" stroke="#F59E0B" stroke-opacity="0.35" stroke-width="0.8"/>'
                )
            else:
                lvl = grid[r][c]
                fill = LEVEL_COLORS.get(lvl, "#151D2B")
                extra = ' opacity="0.95"' if lvl >= 3 else ""
                tiles_svg.append(
                    f'    <rect x="{x}" y="{y}" width="{tile}" height="{tile}" rx="3" fill="{fill}"{extra}/>'
                )

    # Original geometric "pixel bug" sprites (3 targets hovering above/in grid)
    bugs_svg = []
    for idx, (r, c) in enumerate(bug_cells):
        cx = start_x + c * (tile + gap) + tile / 2
        cy = start_y + r * (tile + gap) + tile / 2
        delay = idx * 0.65
        bugs_svg.append(f"""    <g class="bug-target" style="animation-delay: {delay:.2f}s;">
      <rect x="{cx - 6:.1f}" y="{cy - 4:.1f}" width="12" height="8" rx="2.5" fill="#F59E0B"/>
      <rect x="{cx - 4:.1f}" y="{cy - 2:.1f}" width="2.5" height="2.5" rx="0.6" fill="#090D16"/>
      <rect x="{cx + 1.5:.1f}" y="{cy - 2:.1f}" width="2.5" height="2.5" rx="0.6" fill="#090D16"/>
      <line x1="{cx - 4:.1f}" y1="{cy - 4:.1f}" x2="{cx - 6:.1f}" y2="{cy - 7:.1f}" stroke="#FBBF24" stroke-width="1.3" stroke-linecap="round"/>
      <line x1="{cx + 4:.1f}" y1="{cy - 4:.1f}" x2="{cx + 6:.1f}" y2="{cy - 7:.1f}" stroke="#FBBF24" stroke-width="1.3" stroke-linecap="round"/>
      <line x1="{cx - 6:.1f}" y1="{cy + 2:.1f}" x2="{cx - 8.5:.1f}" y2="{cy + 4.5:.1f}" stroke="#F59E0B" stroke-width="1.2" stroke-linecap="round"/>
      <line x1="{cx + 6:.1f}" y1="{cy + 2:.1f}" x2="{cx + 8.5:.1f}" y2="{cy + 4.5:.1f}" stroke="#F59E0B" stroke-width="1.2" stroke-linecap="round"/>
    </g>""")

    tiles_str = "\n".join(tiles_svg)
    bugs_str = "\n".join(bugs_svg)

    return f"""<svg width="900" height="284" viewBox="0 0 900 284" fill="none" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <linearGradient id="arenaBg" x1="0" y1="0" x2="900" y2="284" gradientUnits="userSpaceOnUse">
      <stop offset="0%" stop-color="#090D16"/>
      <stop offset="50%" stop-color="#0D1424"/>
      <stop offset="100%" stop-color="#091520"/>
    </linearGradient>

    <radialGradient id="podGlow" cx="0" cy="0" r="1" gradientUnits="userSpaceOnUse" gradientTransform="translate(129 216) scale(76 22)">
      <stop offset="0%" stop-color="#10B981" stop-opacity="0.45"/>
      <stop offset="100%" stop-color="#10B981" stop-opacity="0"/>
    </radialGradient>

    <radialGradient id="visorGlow" cx="0" cy="0" r="1" gradientUnits="userSpaceOnUse" gradientTransform="translate(129 124) scale(55 40)">
      <stop offset="0%" stop-color="#06B6D4" stop-opacity="0.22"/>
      <stop offset="100%" stop-color="#06B6D4" stop-opacity="0"/>
    </radialGradient>

    <linearGradient id="neonAccent" x1="0" y1="0" x2="900" y2="0" gradientUnits="userSpaceOnUse">
      <stop offset="0%" stop-color="#10B981"/>
      <stop offset="50%" stop-color="#06B6D4"/>
      <stop offset="100%" stop-color="#6366F1"/>
    </linearGradient>

    <linearGradient id="laserGrad" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="#67E8F9"/>
      <stop offset="60%" stop-color="#10B981"/>
      <stop offset="100%" stop-color="#10B981" stop-opacity="0"/>
    </linearGradient>

    <pattern id="arcadeGrid" width="24" height="24" patternUnits="userSpaceOnUse">
      <path d="M 24 0 L 0 0 0 24" fill="none" stroke="#1E293B" stroke-width="0.6" opacity="0.45"/>
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
      22% {{ transform: translateX(132px); }}
      48% {{ transform: translateX(282px); }}
      74% {{ transform: translateX(416px); }}
      100% {{ transform: translateX(0px); }}
    }}
    @keyframes laserPulse {{
      0% {{ transform: translateY(0px); opacity: 0; }}
      15% {{ opacity: 1; }}
      75% {{ transform: translateY(-102px); opacity: 0.95; }}
      100% {{ transform: translateY(-120px); opacity: 0; }}
    }}
    @keyframes bugHover {{
      0%, 100% {{ transform: translateY(0px); }}
      50% {{ transform: translateY(-2.5px); }}
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
    .drone-group {{ animation: dronePatrol 9s ease-in-out infinite; }}
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

    <rect x="646" y="8" width="112" height="20" rx="6" fill="#111C33" stroke="#1E293B" stroke-width="1"/>
    <text x="702" y="21.5" text-anchor="middle" class="mono" font-size="10" fill="#38BDF8">PLAYER: FTHRXYZZ</text>

    <rect x="766" y="8" width="114" height="20" rx="6" fill="#10B981" fill-opacity="0.12" stroke="#10B981" stroke-opacity="0.4" stroke-width="1"/>
    <text x="823" y="21.5" text-anchor="middle" class="mono" font-size="10" font-weight="700" fill="#6EE7B7">MODE: AUTO-PLAY</text>

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

    <!-- Floating Cyber-Robot Character (100% Original Vector Design) -->
    <g class="yuna-bot">
      <circle cx="129" cy="126" r="52" fill="url(#visorGlow)"/>

      <!-- Antenna -->
      <line x1="129" y1="96" x2="129" y2="84" stroke="#38BDF8" stroke-width="2.2" stroke-linecap="round"/>
      <circle cx="129" cy="82" r="4" fill="#10B981" class="core-glow"/>
      <circle cx="129" cy="82" r="7" fill="none" stroke="#10B981" stroke-opacity="0.35" stroke-width="1"/>

      <!-- Ear Pods -->
      <rect x="85" y="114" width="8" height="20" rx="4" fill="#1E293B" stroke="#38BDF8" stroke-width="1.2"/>
      <rect x="165" y="114" width="8" height="20" rx="4" fill="#1E293B" stroke="#38BDF8" stroke-width="1.2"/>

      <!-- Head Shell -->
      <rect x="93" y="96" width="72" height="52" rx="18" fill="#111C33" stroke="#38BDF8" stroke-width="1.8"/>

      <!-- Dark Visor -->
      <rect x="101" y="106" width="56" height="32" rx="11" fill="#060B14" stroke="#1E293B" stroke-width="1"/>

      <!-- Expressive Cyber Eyes -->
      <g class="bot-eyes">
        <rect x="111" y="115" width="11" height="11" rx="3.5" fill="#10B981"/>
        <rect x="136" y="115" width="11" height="11" rx="3.5" fill="#10B981"/>
        <circle cx="114.5" cy="118.5" r="2" fill="#ECFDF5"/>
        <circle cx="139.5" cy="118.5" r="2" fill="#ECFDF5"/>
      </g>
      <!-- Subtle Friendly Smile -->
      <path d="M 123 130 Q 129 134 135 130" stroke="#38BDF8" stroke-width="1.8" stroke-linecap="round" fill="none"/>

      <!-- Floating Hover Arms -->
      <rect x="84" y="156" width="12" height="22" rx="6" fill="#0F172A" stroke="#10B981" stroke-width="1.4"/>
      <rect x="162" y="156" width="12" height="22" rx="6" fill="#0F172A" stroke="#10B981" stroke-width="1.4"/>

      <!-- Cyber Torso -->
      <rect x="103" y="153" width="52" height="36" rx="12" fill="#111C33" stroke="#38BDF8" stroke-width="1.6"/>
      <!-- Core Reactor -->
      <polygon points="129,161 137,171 129,181 121,171" fill="#10B981" fill-opacity="0.25" stroke="#34D399" stroke-width="1.5" class="core-glow"/>
      <circle cx="129" cy="171" r="2.8" fill="#67E8F9"/>

      <!-- Thruster Flame -->
      <path d="M 121 191 L 129 202 L 137 191 Z" fill="#06B6D4" fill-opacity="0.7" class="core-glow"/>
    </g>

    <!-- Mini Equalizer & Label -->
    <rect x="34" y="226" width="3.5" height="14" rx="1.5" fill="#10B981" class="eq1"/>
    <rect x="40" y="229" width="3.5" height="11" rx="1.5" fill="#06B6D4" class="eq2"/>
    <rect x="46" y="227" width="3.5" height="13" rx="1.5" fill="#818CF8" class="eq3"/>
    <text x="58" y="237" class="mono" font-size="10" fill="#94A3B8">AI CO-PILOT: ACTIVE</text>

    <!-- RIGHT ARENA: CONTRIBUTION GRID MINI-GAME -->
    <rect x="252" y="50" width="626" height="200" rx="12" fill="#0B1120" fill-opacity="0.88" stroke="#1E293B" stroke-width="1.2"/>
    <rect x="252" y="50" width="626" height="24" rx="12" fill="#111C33"/>
    <rect x="252" y="64" width="626" height="10" fill="#111C33"/>
    <line x1="252" y1="74" x2="878" y2="74" stroke="#1E293B" stroke-width="1"/>

    <text x="268" y="66" class="mono" font-size="10" font-weight="700" fill="#38BDF8">ARENA // CONTRIBUTION MATRIX</text>
    <circle cx="678" cy="62" r="3.5" fill="#F59E0B"/>
    <text x="687" y="66" class="mono" font-size="9.5" fill="#CBD5E1">BUGS</text>
    <circle cx="738" cy="62" r="3.5" fill="#39D353"/>
    <text x="747" y="66" class="mono" font-size="9.5" fill="#CBD5E1">COMMITS</text>
    <circle cx="816" cy="62" r="3.5" fill="#38BDF8"/>
    <text x="825" y="66" class="mono" font-size="9.5" fill="#CBD5E1">DRONE</text>

    <!-- Contribution Grid Tiles -->
{tiles_str}

    <!-- Animated Pixel Bug Targets -->
{bugs_str}

    <!-- Patrolling Mini Cyber-Drone + Laser Fire -->
    <g class="drone-group">
      <!-- Vertical Laser Pulse -->
      <rect x="331" y="198" width="3" height="18" rx="1.5" fill="url(#laserGrad)" class="laser-beam"/>

      <!-- Mini Cyber-Ship / Drone -->
      <polygon points="332.5,208 345,221 339,224 332.5,220 326,224 320,221" fill="#38BDF8"/>
      <polygon points="332.5,211 337,219 328,219" fill="#ECFDF5"/>
      <rect x="329.5" y="222" width="6" height="4" rx="2" fill="#10B981" class="core-glow"/>
    </g>

    <!-- Bottom Status Ticker -->
    <text x="26" y="271" class="mono" font-size="10.5" fill="#64748B">&gt; MISSION: ZAP BUGS · SHIP COMMITS · BUILD DAILY WITH @ASKYUNA.AI</text>
    <text x="876" y="271" text-anchor="end" class="mono" font-size="10.5" font-weight="700" fill="#34D399">SHIELD ██████ 100%</text>

    <!-- Bottom Neon Bar -->
    <rect x="0" y="280" width="900" height="4" fill="url(#neonAccent)"/>
  </g>

  <rect x="1" y="1" width="898" height="282" rx="16" stroke="#1E293B" stroke-width="1.4"/>
</svg>
"""


def main() -> None:
    repo_root = Path(__file__).resolve().parent.parent
    out_path = repo_root / "assets" / "yuna-arcade.svg"
    grid = fetch_github_contributions() or FALLBACK_GRID
    svg = build_svg(grid)
    out_path.write_text(svg, encoding="utf-8")
    print(f"Generated {out_path} ({len(svg)} bytes)")


if __name__ == "__main__":
    main()
