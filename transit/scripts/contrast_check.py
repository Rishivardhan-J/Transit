"""WCAG 2.x contrast ratios for the Command Navy palette (PRD 11.2 requires AA = 4.5:1 for body text)."""


def lum(hex_: str) -> float:
    c = [int(hex_[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    c = [v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4 for v in c]
    return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]


def blend(fg: str, bg: str, a: float) -> str:
    f = [int(fg[i:i + 2], 16) for i in (1, 3, 5)]
    b = [int(bg[i:i + 2], 16) for i in (1, 3, 5)]
    return "#" + "".join(f"{round(x * a + y * (1 - a)):02X}" for x, y in zip(f, b))


def ratio(a: str, b: str) -> float:
    la, lb = sorted((lum(a), lum(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


DOM, SEC = "#0F172A", "#1E293B"
PAIRS = [
    ("text primary on dominant", "#F1F5F9", DOM), ("text primary on secondary", "#F1F5F9", SEC),
    ("text secondary on dominant", "#94A3B8", DOM), ("text secondary on secondary", "#94A3B8", SEC),
    ("text muted on dominant", "#64748B", DOM), ("text muted on secondary", "#64748B", SEC),
    ("accent on dominant", "#F59E0B", DOM), ("accent on secondary", "#F59E0B", SEC),
    ("dominant on accent (button)", DOM, "#F59E0B"),
    ("success badge", "#4ADE80", blend("#22C55E", SEC, 0.15)), ("warning badge", "#FCD34D", blend("#F59E0B", SEC, 0.18)),
    ("error badge", "#FCA5A5", blend("#EF4444", SEC, 0.15)),
]
if __name__ == "__main__":
    for name, fg, bg in PAIRS:
        r = ratio(fg, bg)
        print(f"{name:34s} {fg} on {bg}  {r:5.2f}:1  {'AA' if r >= 4.5 else 'below AA (large text / non-text only)' if r >= 3 else 'FAIL'}")
