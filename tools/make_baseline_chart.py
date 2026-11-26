"""Draw docs/baselines.svg: how the rule-based baseline holds up from simple (v1) to realistic (v2) letters.

Dumbbell chart, one hue in two shades (validated with the dataviz palette checker, ordinal mode).
Usage:  python tools/make_baseline_chart.py
"""
from pathlib import Path

ROWS = [  # label, v1 %, v2 %   (from docs/results.md)
    ("Rejection reason identified", 79.6, 47.6),
    ("All 11 fields, mean", 64.5, 76.9),
    ("Exact reason sentence found", 7.7, 8.0),
]
TARGET = 90  # model target for the exact reason sentence
LIGHT, DARK = "#84b9f3", "#1757ac"          # blue steps 250 / 600
INK, INK2, GRID, AXIS = "#191919", "#666666", "#e7e7e7", "#c2c2c2"
W, H = 880, 330
X0, X1 = 250, 840                              # plot area
Y0, ROW = 128, 58


def x(v):
    return X0 + (X1 - X0) * v / 100


def text(xp, yp, s, size=13, fill=INK, anchor="start", weight=400):
    return (f'<text x="{xp:.1f}" y="{yp:.1f}" font-size="{size}" fill="{fill}" text-anchor="{anchor}" '
            f'font-weight="{weight}">{s}</text>')


def main():
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" '
           f'font-family="IBM Plex Sans, Inter, Arial, sans-serif" role="img" '
           f'aria-label="Rules find the rejection reason in 80% of simple letters but 48% of realistic ones">',
           f'<rect width="{W}" height="{H}" fill="#ffffff"/>',
           text(24, 34, "Rules break on realistic letters: the reason is found in 80% of simple letters, 48% of realistic ones",
                size=15, weight=600),
           text(24, 56, "Rule-based baseline, no model. v1: 401 simple synthetic letters. v2: 958 realistic ones. Target is for the fine-tuned model.",
                size=12, fill=INK2)]
    # legend
    out += [f'<circle cx="30" cy="82" r="6" fill="{LIGHT}"/>', text(42, 86, "v1 letters (simple)", 12, INK2),
            f'<circle cx="182" cy="82" r="6" fill="{DARK}"/>', text(194, 86, "v2 letters (realistic)", 12, INK2)]
    bottom = Y0 + ROW * (len(ROWS) - 1) + 28
    for t in (0, 25, 50, 75, 100):  # recessive grid
        out.append(f'<line x1="{x(t):.1f}" x2="{x(t):.1f}" y1="{Y0 - 24}" y2="{bottom}" stroke="{GRID}" stroke-width="1"/>')
        out.append(text(x(t), bottom + 18, f"{t}%", 11.5, INK2, "middle"))
    out.append(f'<line x1="{X0}" x2="{X1}" y1="{bottom}" y2="{bottom}" stroke="{AXIS}" stroke-width="1"/>')
    # target
    out.append(f'<line x1="{x(TARGET):.1f}" x2="{x(TARGET):.1f}" y1="{Y0 - 24}" y2="{bottom}" stroke="{INK2}" '
               f'stroke-width="1.5" stroke-dasharray="4 4"/>')
    out.append(text(x(TARGET) - 6, Y0 + ROW * 2 - 14, "model target 90%", 11.5, INK2, "end"))
    for i, (label, a, b) in enumerate(ROWS):
        y = Y0 + ROW * i
        out.append(text(24, y + 4.5, label, 13))
        out.append(f'<line x1="{x(a):.1f}" x2="{x(b):.1f}" y1="{y}" y2="{y}" stroke="{AXIS}" stroke-width="2"/>')
        for v, c in ((a, LIGHT), (b, DARK)):  # dots with a 2px surface ring
            out.append(f'<circle cx="{x(v):.1f}" cy="{y}" r="7" fill="{c}" stroke="#ffffff" stroke-width="2"/>')
        if abs(a - b) < 6:  # too close for two labels: one combined label
            out.append(text(max(x(a), x(b)) + 14, y + 4.5, f"{a:.1f}% → {b:.1f}%", 12, INK))
        else:
            lo, hi = sorted((a, b))
            out.append(text(x(lo) - 13, y + 4.5, f"{lo:.1f}%", 12, INK, "end"))
            out.append(text(x(hi) + 13, y + 4.5, f"{hi:.1f}%", 12, INK))
    out.append("</svg>")
    path = Path(__file__).resolve().parent.parent / "docs" / "baselines.svg"
    path.write_text("\n".join(out), encoding="utf-8")
    print(f"Wrote {path}")


if __name__ == "__main__":
    main()
