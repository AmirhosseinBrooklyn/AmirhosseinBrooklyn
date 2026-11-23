from datetime import date
from html import escape
import math

PALETTE = ("#a97bff", "#f1e05a", "#58a6ff", "#f78166", "#7b83c4", "#89929b")
THEMES = {
    "dark": ("#e6edf3", "#919ba8", "#30363d"),
    "light": ("#1f2328", "#59636e", "#d1d9e0"),
}


# Shared chart styling

def card(title, subtitle, description, theme, body):
    foreground, muted, border = THEMES[theme]
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="450" height="310" viewBox="0 0 450 310" role="img">
  <title>{escape(title)}</title>
  <desc>{escape(description)}</desc>
  <style>
    text {{ font-family: -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif; fill: {foreground}; }}
    .muted {{ fill: {muted}; }}
    .grid {{ stroke: {border}; fill: none; }}
    .enter {{ animation: fade .9s ease both; }}
    @keyframes fade {{ from {{ opacity: .65; }} to {{ opacity: 1; }} }}
    @media (prefers-reduced-motion: reduce) {{ .enter {{ animation: none; }} }}
  </style>
  <rect x=".5" y=".5" width="449" height="309" rx="10" class="grid"/>
  <text x="24" y="32" font-size="15" font-weight="600">{escape(title)}</text>
  <text x="24" y="53" class="muted" font-size="11">{escape(subtitle)}</text>
{body}
</svg>
"""


# Language footprint

def donut(language_bytes, updated, theme):
    languages = sorted(
        ((name, size) for name, size in language_bytes.items() if size > 0),
        key=lambda item: (-item[1], item[0]),
    )
    total = sum(size for _, size in languages)
    slices = languages[:5]
    if len(languages) > 5:
        slices.append(("Other", sum(size for _, size in languages[5:])))

    body = []
    circumference = math.tau * 68
    offset = 0.0
    description = []
    for index, ((name, size), color) in enumerate(zip(slices, PALETTE)):
        share = size / total
        length = share * circumference
        gap = min(3, length * .25) if len(slices) > 1 else 0
        y = 98 + index * 26
        body.extend((
            f'  <circle cx="116" cy="158" r="68" fill="none" stroke="{color}" stroke-width="23" '
            f'stroke-dasharray="{length - gap:.3f} {circumference:.3f}" stroke-dashoffset="{-offset:.3f}" '
            'transform="rotate(-90 116 158)" class="enter"/>',
            f'  <rect x="223" y="{y - 8}" width="8" height="8" rx="2" fill="{color}"/>',
            f'  <text x="241" y="{y}" font-size="13">{escape(name)}</text>',
            f'  <text x="417" y="{y}" text-anchor="end" font-size="13" class="muted">{share:.1%}</text>',
        ))
        description.append(f"{name}: {share:.1%}")
        offset += length
    if not languages:
        body.append('  <text x="225" y="158" text-anchor="middle" class="muted">No public language data</text>')
    else:
        body.extend((
            f'  <text x="116" y="156" text-anchor="middle" font-size="24" font-weight="600">{len(languages)}</text>',
            '  <text x="116" y="177" text-anchor="middle" class="muted" font-size="11">languages</text>',
        ))
    stamp = date.fromisoformat(updated).strftime("%d %b %Y")
    body.extend((
        '  <text x="24" y="274" class="muted" font-size="11">Forks excluded. Percentages are based on code size.</text>',
        f'  <text x="24" y="291" class="muted" font-size="10">Updated {stamp}</text>',
    ))
    return card("Language footprint", "Public original repositories · by code size",
                ". ".join(description) or "No public language data", theme, "\n".join(body))


# Collaboration radar

def radar(values, repository_count, theme):
    metrics = [*values.items(), ("Public repos", repository_count)]
    peak = max(value for _, value in metrics)
    maximum = max(100, 10 ** math.ceil(math.log10(max(1, peak))))
    center_x, center_y, radius = 225, 166, 65

    def point(index, level=1):
        angle = math.tau * index / len(metrics) - math.pi / 2
        return center_x + math.cos(angle) * radius * level, center_y + math.sin(angle) * radius * level

    def polygon(points):
        return " ".join(f"{x:.2f},{y:.2f}" for x, y in points)

    body = []
    for level in (.25, .5, .75, 1):
        outline = polygon(point(index, level) for index in range(len(metrics)))
        body.append(f'  <polygon points="{outline}" class="grid" stroke-dasharray="3 4"/>')

    vertices = []
    for index, (label, value) in enumerate(metrics):
        x, y = point(index)
        body.append(f'  <line x1="{center_x}" y1="{center_y}" x2="{x:.2f}" y2="{y:.2f}" class="grid"/>')
        x, y = point(index, 1.29)
        body.extend((
            f'  <text x="{x:.2f}" y="{y:.2f}" text-anchor="middle" font-size="12">{escape(label)}</text>',
            f'  <text x="{x:.2f}" y="{y + 15:.2f}" text-anchor="middle" font-weight="600" font-size="13">{value:,}</text>',
        ))
        vertices.append(point(index, math.log1p(value) / math.log1p(maximum)))

    body.append(f'  <polygon points="{polygon(vertices)}" fill="#3fb950" fill-opacity=".20" '
                'stroke="#3fb950" stroke-width="2" class="enter"/>')
    for x, y in vertices:
        body.append(f'  <circle cx="{x:.2f}" cy="{y:.2f}" r="3" fill="#3fb950"/>')
    body.extend((
        '  <text x="24" y="274" class="muted" font-size="10">Commits, issues, PRs and reviews cover the past 365 days.</text>',
        f'  <text x="24" y="291" class="muted" font-size="10">Log scale 0–{maximum:,}. Public repo count includes forks.</text>',
    ))
    description = ". ".join(f"{label}: {value:,}" for label, value in metrics)
    return card("Collaboration radar", "Public GitHub data · logarithmic scale",
                description, theme, "\n".join(body))


def write_charts(directory, data):
    for theme in THEMES:
        (directory / f"languages-{theme}.svg").write_text(
            donut(data["languages"], data["date"], theme), encoding="utf-8")
        (directory / f"radar-{theme}.svg").write_text(
            radar(data["contributions"], data["public_repos"], theme), encoding="utf-8")
