#!/usr/bin/env python3
"""Generate SVG concept drawings for the Eira HDPE panel armchair."""

from pathlib import Path
from math import tan, radians


ROOT = Path(__file__).resolve().parents[1]
DRAWINGS = ROOT / "drawings"


COLORS = {
    "board25": "#4b5563",
    "board20": "#8b5e3c",
    "line": "#111827",
    "dim": "#2563eb",
    "muted": "#6b7280",
    "bg": "#f8fafc",
    "sheet": "#eef2f7",
    "cut": "#cbd5e1",
    "accent": "#0f766e",
    "hardware": "#334155",
}


def tag(name, attrs=None, content=""):
    attrs = attrs or {}
    attr = " ".join(f'{k}="{v}"' for k, v in attrs.items() if v is not None)
    if content:
        return f"<{name} {attr}>{content}</{name}>"
    return f"<{name} {attr}/>"


def svg_doc(width, height, title, body):
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
  <title>{title}</title>
  <rect width="100%" height="100%" fill="{COLORS['bg']}"/>
  <style>
    .title {{ font: 700 24px Arial, sans-serif; fill: #111827; }}
    .label {{ font: 600 13px Arial, sans-serif; fill: #111827; }}
    .small {{ font: 12px Arial, sans-serif; fill: #374151; }}
    .dim {{ font: 12px Arial, sans-serif; fill: {COLORS['dim']}; }}
    .part {{ font: 11px Arial, sans-serif; fill: #111827; }}
  </style>
{body}
</svg>
"""


def text(x, y, value, cls="small", anchor="start", rotate=None):
    transform = f"rotate({rotate} {x} {y})" if rotate else None
    return tag("text", {"x": x, "y": y, "class": cls, "text-anchor": anchor, "transform": transform}, value)


def line(x1, y1, x2, y2, stroke=None, width=1.5, dash=None):
    return tag(
        "line",
        {
            "x1": x1,
            "y1": y1,
            "x2": x2,
            "y2": y2,
            "stroke": stroke or COLORS["line"],
            "stroke-width": width,
            "stroke-dasharray": dash,
            "stroke-linecap": "round",
        },
    )


def rect(x, y, w, h, fill, stroke=None, rx=3, opacity=None):
    return tag(
        "rect",
        {
            "x": x,
            "y": y,
            "width": w,
            "height": h,
            "rx": rx,
            "fill": fill,
            "stroke": stroke or COLORS["line"],
            "stroke-width": 1.5,
            "opacity": opacity,
        },
    )


def polygon(points, fill, stroke=None, opacity=None):
    pts = " ".join(f"{x},{y}" for x, y in points)
    return tag(
        "polygon",
        {
            "points": pts,
            "fill": fill,
            "stroke": stroke or COLORS["line"],
            "stroke-width": 1.5,
            "opacity": opacity,
        },
    )


def dim_h(x1, x2, y, label):
    mid = (x1 + x2) / 2
    return "\n".join(
        [
            line(x1, y, x2, y, COLORS["dim"], 1.2),
            line(x1, y - 6, x1, y + 6, COLORS["dim"], 1.2),
            line(x2, y - 6, x2, y + 6, COLORS["dim"], 1.2),
            text(mid, y - 10, label, "dim", "middle"),
        ]
    )


def dim_v(x, y1, y2, label):
    mid = (y1 + y2) / 2
    return "\n".join(
        [
            line(x, y1, x, y2, COLORS["dim"], 1.2),
            line(x - 6, y1, x + 6, y1, COLORS["dim"], 1.2),
            line(x - 6, y2, x + 6, y2, COLORS["dim"], 1.2),
            text(x + 14, mid, label, "dim", "start", rotate=-90),
        ]
    )


def screw(x, y, r=5):
    return "\n".join(
        [
            tag("circle", {"cx": x, "cy": y, "r": r, "fill": COLORS["hardware"], "stroke": "#020617", "stroke-width": 1}),
            line(x - r * 0.55, y, x + r * 0.55, y, "#cbd5e1", 1),
        ]
    )


def front_view():
    s = 0.72
    x0, y0 = 150, 80
    width, height = 660 * s, 820 * s
    ground = y0 + height
    inner_x = x0 + 25 * s
    inner_w = 610 * s
    out = [
        text(40, 42, "Eira HDPE Panel Armchair - Front View", "title"),
        text(40, 66, "Visible board/slat construction, no monobloc shell, no wicker, no Adirondack profile", "small"),
        line(80, ground, 800, ground, "#94a3b8", 1, "6 6"),
    ]

    # Side frames and rear posts
    out += [
        rect(x0, ground - 640 * s, 25 * s, 640 * s, COLORS["board25"]),
        rect(x0 + width - 25 * s, ground - 820 * s, 25 * s, 820 * s, COLORS["board25"]),
        rect(x0 + width - 25 * s, ground - 640 * s, 25 * s, 640 * s, COLORS["board25"]),
        rect(x0, ground - 820 * s, 25 * s, 820 * s, COLORS["board25"], opacity=0.22),
    ]

    # Arm caps
    out += [
        rect(x0 - 10 * s, ground - 640 * s, 115 * s, 25 * s, COLORS["board25"]),
        rect(x0 + width - 105 * s, ground - 640 * s, 115 * s, 25 * s, COLORS["board25"]),
    ]

    # Seat and front rail
    out.append(rect(inner_x, ground - 440 * s, inner_w, 90 * s, COLORS["board25"]))
    for i in range(6):
        y = ground - (425 - i * 13) * s
        out.append(rect(inner_x + 8 * s, y, inner_w - 16 * s, 6 * s, COLORS["board20"], rx=2))

    # Back assembly
    out.append(rect(inner_x, ground - 790 * s, inner_w, 68 * s, COLORS["board25"]))
    out.append(rect(inner_x, ground - 515 * s, inner_w, 60 * s, COLORS["board25"]))
    slat_w = 64 * s
    gap = (inner_w - 5 * slat_w) / 6
    for i in range(5):
        x = inner_x + gap + i * (slat_w + gap)
        out.append(rect(x, ground - 720 * s, slat_w, 220 * s, COLORS["board20"], rx=5))

    # Hardware dots
    for x in [x0 + 12 * s, x0 + width - 12 * s]:
        for y_mm in [110, 385, 615, 760]:
            out.append(screw(x, ground - y_mm * s, 4))
    for x in [inner_x + 70 * s, inner_x + inner_w - 70 * s]:
        out.append(screw(x, ground - 472 * s, 4))
        out.append(screw(x, ground - 760 * s, 4))

    out += [
        dim_h(x0, x0 + width, ground + 42, "overall width 660 mm"),
        dim_v(x0 + width + 55, ground - height, ground, "overall height 820 mm"),
    ]
    return svg_doc(900, 760, "Eira front view", "\n".join(out))


def side_view():
    s = 0.75
    x0, ground = 110, 700
    to_xy = lambda x, y: (x0 + x * s, ground - y * s)

    out = [
        text(40, 42, "Eira HDPE Panel Armchair - Side View", "title"),
        text(40, 66, "Upright garden lounge posture: shallow seat rake and 10 degree back angle", "small"),
        line(70, ground, 820, ground, "#94a3b8", 1, "6 6"),
    ]

    # Side frame as manufacturable plate frame pieces shown in side elevation
    def rxy(x, y, w, h, fill):
        xx, yy = to_xy(x, y + h)
        return rect(xx, yy, w * s, h * s, fill)

    out += [
        rxy(0, 0, 75, 640, COLORS["board25"]),
        rxy(560, 0, 80, 820, COLORS["board25"]),
        rxy(55, 390, 520, 65, COLORS["board25"]),
        rxy(35, 70, 560, 62, COLORS["board25"]),
    ]

    # Sloped arm cap
    p = [to_xy(12, 640), to_xy(600, 625), to_xy(598, 665), to_xy(10, 680)]
    out.append(polygon(p, COLORS["board25"]))

    # Seat slats, front high rear low
    seat_front = to_xy(70, 440)
    seat_rear = to_xy(555, 420)
    out.append(line(seat_front[0], seat_front[1], seat_rear[0], seat_rear[1], COLORS["board20"], 18))
    for i in range(6):
        x = 85 + i * 78
        p1 = to_xy(x, 442 - i * 3.2)
        p2 = to_xy(x + 58, 439 - i * 3.2)
        out.append(line(p1[0], p1[1], p2[0], p2[1], "#a16207", 5))

    # Back plane
    back_bottom_x, back_bottom_y = 500, 440
    back_h = 360
    back_top_x = back_bottom_x + tan(radians(10)) * back_h
    p_back = [
        to_xy(back_bottom_x - 18, back_bottom_y),
        to_xy(back_bottom_x + 12, back_bottom_y),
        to_xy(back_top_x + 12, back_bottom_y + back_h),
        to_xy(back_top_x - 18, back_bottom_y + back_h),
    ]
    out.append(polygon(p_back, COLORS["board20"]))
    top_rail = [to_xy(back_top_x - 50, 790), to_xy(back_top_x + 28, 790), to_xy(back_top_x + 28, 830), to_xy(back_top_x - 50, 830)]
    out.append(polygon(top_rail, COLORS["board25"]))

    # Hardware dots
    for x, y in [(37, 105), (37, 410), (37, 620), (600, 100), (600, 430), (600, 625), (600, 770)]:
        xx, yy = to_xy(x, y)
        out.append(screw(xx, yy, 4))

    # Dimensions and callouts
    out += [
        dim_h(x0, x0 + 650 * s, ground + 42, "overall depth 650 mm"),
        dim_v(x0 + 650 * s + 50, ground - 820 * s, ground, "height 820 mm"),
        dim_v(x0 - 34, ground - 440 * s, ground, "front seat 440 mm"),
        text(535, 140, "10 deg back", "dim"),
        text(510, 170, "Back is relaxed, not Adirondack-deep", "small"),
        rect(42, 96, 280, 92, "#ffffff", "#cbd5e1", rx=8, opacity=0.88),
        text(60, 126, "One-piece mirrored side frame", "label"),
        text(60, 150, "CNC cut windows", "small"),
        text(60, 174, "Separate replaceable arm cap", "small"),
    ]
    return svg_doc(900, 780, "Eira side view", "\n".join(out))


def side_profile_symbol(x, y, s, label):
    parts = [
        rect(x, y + 180 * s, 75 * s, 460 * s, COLORS["board25"], rx=2),
        rect(x + 560 * s, y, 80 * s, 640 * s, COLORS["board25"], rx=2),
        rect(x + 55 * s, y + 365 * s, 520 * s, 65 * s, COLORS["board25"], rx=2),
        rect(x + 35 * s, y + 560 * s, 560 * s, 62 * s, COLORS["board25"], rx=2),
        text(x + 320 * s, y + 665 * s, label, "part", "middle"),
    ]
    return "\n".join(parts)


def cut_sheet_25():
    s = 0.34
    board_w, board_h = 2440 * s, 1220 * s
    x0, y0 = 40, 90
    out = [
        text(40, 42, "25 mm Sheet - CNC Cut Layout Concept", "title"),
        text(40, 66, "Board reference: 2440 x 1220 mm. Layout is schematic, not final nesting.", "small"),
        rect(x0, y0, board_w, board_h, COLORS["sheet"], COLORS["cut"], rx=6),
        text(x0 + board_w - 12, y0 + board_h - 12, "2440 x 1220", "dim", "end"),
    ]

    out.append(side_profile_symbol(x0 + 35, y0 + 25, 0.28, "S01-L side frame"))
    out.append(side_profile_symbol(x0 + 260, y0 + 25, 0.28, "S01-R side frame"))

    # Rails and arms
    x = x0 + 510
    y = y0 + 35
    rails = [
        ("A01 arm cap", 590, 82),
        ("A01 arm cap", 590, 82),
        ("C01 front rail", 610, 90),
        ("C02 rear rail", 610, 85),
        ("B01 back top rail", 610, 90),
        ("B02 back bottom rail", 610, 80),
        ("C03/C04 lower stretchers", 610, 70),
    ]
    for name, w, h in rails:
        out.append(rect(x, y, w * 0.34, h * 0.34, "#64748b", rx=3))
        out.append(text(x + 6, y + h * 0.17 + 3, name, "part"))
        y += h * 0.34 + 14

    # Gussets
    gx, gy = x0 + 510, y0 + 320
    for i in range(4):
        px = gx + (i % 2) * 70
        py = gy + (i // 2) * 70
        out.append(polygon([(px, py + 44), (px + 44, py + 44), (px, py)], "#64748b"))
    out.append(text(gx, gy + 150, "G01 triangular corner gussets x4", "part"))

    out += [
        text(40, 545, "25 mm parts: side frames, arm caps, cross rails, back rails, corner gussets, spacer blocks.", "label"),
        text(40, 568, "Keep high-load holes at least 62 mm from vulnerable free edges where possible.", "small"),
    ]
    return svg_doc(930, 610, "25 mm cut sheet", "\n".join(out))


def cut_sheet_20():
    s = 0.5
    x0, y0 = 50, 95
    board_w, board_h = 1220 * s, 900 * s
    out = [
        text(40, 42, "20 mm Sheet - Seat and Back Slats", "title"),
        text(40, 66, "Slats are repeat parts with rounded ends and slotted screw holes for thermal movement.", "small"),
        rect(x0, y0, board_w, board_h, COLORS["sheet"], COLORS["cut"], rx=6),
    ]

    # Seat slats
    for i in range(6):
        x = x0 + 35
        y = y0 + 35 + i * 50
        out.append(rect(x, y, 610 * s, 70 * s, COLORS["board20"], rx=8))
        out.append(text(x + 12, y + 24, f"SE01 seat slat {i + 1} - 610 x 70", "part"))
        for hx in [55, 555]:
            out.append(tag("ellipse", {"cx": x + hx * s, "cy": y + 35 * s, "rx": 10, "ry": 4, "fill": "#f8fafc", "stroke": COLORS["line"], "stroke-width": 1}))

    # Back slats
    bx = x0 + 385
    for i in range(5):
        x = bx + i * 45
        y = y0 + 35
        out.append(rect(x, y, 64 * s, 520 * s, "#9a6a43", rx=8))
        out.append(text(x + 16, y + 245, f"BA01 {i + 1}", "part", "middle", rotate=-90))
        for hy in [45, 475]:
            out.append(tag("ellipse", {"cx": x + 32 * s, "cy": y + hy * s, "rx": 4, "ry": 10, "fill": "#f8fafc", "stroke": COLORS["line"], "stroke-width": 1}))

    out += [
        text(40, 590, "20 mm parts: 6 seat slats and 5 vertical back slats.", "label"),
        text(40, 612, "Slot direction follows slat length. Do not clamp slats so tightly that expansion is locked.", "small"),
    ]
    return svg_doc(760, 650, "20 mm cut sheet", "\n".join(out))


def flat_pack_layout():
    out = [
        text(40, 42, "Flat-Pack Layout", "title"),
        text(40, 66, "All structural parts are flat CNC panels; no molded shell, no woven panels, no folding frame.", "small"),
    ]
    x0, y0 = 90, 120
    # Carton
    out.append(rect(x0, y0, 720, 420, "#e2e8f0", "#64748b", rx=12))
    out.append(text(x0 + 360, y0 - 18, "Suggested carton inside: 870 x 700 x 140 mm", "dim", "middle"))
    # Stacked parts
    layers = [
        ("Side frames x2, 25 mm", 650, 820, "#4b5563"),
        ("Rails and arms, 25 mm", 650, 160, "#64748b"),
        ("Seat slats x6, 20 mm", 650, 110, "#8b5e3c"),
        ("Back slats x5, 20 mm", 560, 130, "#9a6a43"),
        ("Hardware pouch + guide", 220, 90, "#334155"),
    ]
    sx, sy = x0 + 65, y0 + 60
    for i, (name, w, h, color) in enumerate(layers):
        draw_w = w * 0.62
        draw_h = max(28, h * 0.07)
        out.append(rect(sx + i * 25, sy + i * 52, draw_w, draw_h, color, rx=5, opacity=0.92))
        out.append(text(sx + i * 25 + draw_w + 18, sy + i * 52 + 20, name, "label"))
    out += [
        text(95, 590, "Packing order: protect arm surfaces; keep hardware isolated; add cardboard between boards.", "label"),
        text(95, 614, "Longest part remains the side frame; all other pieces stack inside the same footprint.", "small"),
    ]
    return svg_doc(1050, 660, "Flat pack layout", "\n".join(out))


def main():
    DRAWINGS.mkdir(exist_ok=True)
    files = {
        "assembly_front.svg": front_view(),
        "assembly_side.svg": side_view(),
        "cut_sheet_25mm.svg": cut_sheet_25(),
        "cut_sheet_20mm.svg": cut_sheet_20(),
        "flat_pack_layout.svg": flat_pack_layout(),
    }
    for name, content in files.items():
        (DRAWINGS / name).write_text(content, encoding="utf-8")
        print(f"wrote drawings/{name}")


if __name__ == "__main__":
    main()
