import math
import tkinter as tk
from tkinter import font as tkfont

from modules.config import FONT_FAMILY


# ── Colour helpers ─────────────────────────────────────────────────────────
def hex_to_rgb(h):
    h = h.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def lerp_hex(c1, c2, t):
    r1, g1, b1 = hex_to_rgb(c1)
    r2, g2, b2 = hex_to_rgb(c2)
    return "#{:02x}{:02x}{:02x}".format(
        int(r1 + (r2 - r1) * t),
        int(g1 + (g2 - g1) * t),
        int(b1 + (b2 - b1) * t),
    )


def brightness(hex_col, factor):
    """Lighten (factor>1) or darken (factor<1) a hex colour."""
    r, g, b = hex_to_rgb(hex_col)
    return "#{:02x}{:02x}{:02x}".format(
        min(255, int(r * factor)),
        min(255, int(g * factor)),
        min(255, int(b * factor)),
    )


# ── Rounded rectangle ──────────────────────────────────────────────────────
def rrect(cv, x1, y1, x2, y2, r, fill, outline=None, width=1, tags=""):
    pts = [
        x1 + r, y1,   x2 - r, y1,
        x2,     y1,   x2,     y1 + r,
        x2,     y2 - r, x2,   y2,
        x2 - r, y2,   x1 + r, y2,
        x1,     y2,   x1,     y2 - r,
        x1,     y1 + r, x1,   y1,
        x1 + r, y1,
    ]
    cv.create_polygon(
        pts,
        smooth=True,
        fill=fill,
        outline=outline or fill,
        width=width,
        tags=tags,
    )


# ── Arc gauge ──────────────────────────────────────────────────────────────
def arc_gauge(cv, cx, cy, r, a0, sw, val, vmin, vmax, col, trk, w=7):
    """
    Draw a swept-arc gauge.
    a0 = start angle (degrees), sw = sweep extent (negative = clockwise).
    """
    t = max(0.0, min(1.0, (val - vmin) / (vmax - vmin)))
    # Track (background arc)
    cv.create_arc(
        cx - r, cy - r, cx + r, cy + r,
        start=a0, extent=sw,
        style="arc", outline=trk, width=w,
    )
    # Value arc
    if t > 0.005:
        cv.create_arc(
            cx - r, cy - r, cx + r, cy + r,
            start=a0, extent=sw * t,
            style="arc", outline=col, width=w,
        )
    # Needle dot
    angle = math.radians(a0 + sw * t)
    nx = cx + r * math.cos(angle)
    ny = cy - r * math.sin(angle)
    cv.create_oval(nx - 4, ny - 4, nx + 4, ny + 4, fill=col, outline="")


# ── Segmented bar ──────────────────────────────────────────────────────────
def segbar(cv, x, y, bw, bh, val, vmin, vmax, lit, dim, segs=10, gap=3):
    t = max(0.0, min(1.0, (val - vmin) / (vmax - vmin)))
    n = int(t * segs + 0.5)
    sw = (bw - gap * (segs - 1)) / segs
    for i in range(segs):
        bx = x + i * (sw + gap)
        cv.create_rectangle(
            bx, y, bx + sw, y + bh,
            fill=(lit if i < n else dim),
            outline="",
        )


# ── Shadowed text ──────────────────────────────────────────────────────────
def shadowed(cv, x, y, txt, font, fill, shad, anchor="nw", **kwargs):
    cv.create_text(x + 1, y + 1, text=txt, font=font, fill=shad, anchor=anchor, **kwargs)
    cv.create_text(x,     y,     text=txt, font=font, fill=fill,  anchor=anchor, **kwargs)


# ── Sparkline ──────────────────────────────────────────────────────────────
def sparkline(cv, x, y, w, h, values, col, bg, line_width=1):
    """Draw a mini line chart from a list of numeric values."""
    if len(values) < 2:
        return
    vmin = min(values)
    vmax = max(values)
    rng  = vmax - vmin or 1.0
    pts  = []
    for i, v in enumerate(values):
        px = x + i * w / (len(values) - 1)
        py = y + h - (v - vmin) / rng * h
        pts.extend([px, py])
    cv.create_line(pts, fill=col, width=line_width, smooth=True)


# ── Font registry ──────────────────────────────────────────────────────────
def make_fonts():
    return {
        "hud_xl": tkfont.Font(family=FONT_FAMILY, size=28, weight="bold"),
        "hud_lg": tkfont.Font(family=FONT_FAMILY, size=20, weight="bold"),
        "hud_md": tkfont.Font(family=FONT_FAMILY, size=15, weight="bold"),
        "hud_sm": tkfont.Font(family=FONT_FAMILY, size=12, weight="bold"),
        "ui_md":  tkfont.Font(family=FONT_FAMILY, size=12, weight="bold"),
        "ui_sm":  tkfont.Font(family=FONT_FAMILY, size=10, weight="bold"),
        "ui_xs":  tkfont.Font(family=FONT_FAMILY, size=9, weight="bold"),
        "lbl":    tkfont.Font(family=FONT_FAMILY, size=10, weight="bold"),
    }


# ── Modal scaffold helpers ─────────────────────────────────────────────────
def modal_overlay(cv, T, F, title, sub, W, H):
    """Dim background + card."""
    cv.create_rectangle(0, 0, W, H, fill="#000000", stipple="gray50", outline="")
    rrect(cv, 20, 30, W - 20, H - 30, 6, fill=T["bg2"], outline=T["border_hi"], width=2)
    rrect(cv, 20, 30, W - 20, 72,     6, fill=T["bg3"], outline=T["border_hi"], width=1)
    cv.create_line(20, 72, W - 20, 72, fill=T["border_hi"])
    cv.create_text(36, 51, text=title, font=F["hud_lg"], fill=T["acc"],   anchor="w")
    cv.create_text(36, 66, text=sub,   font=F["ui_xs"],  fill=T["text3"], anchor="w")


def modal_btn(cv, T, F, x1, y1, x2, y2, txt, style, tag):
    """Render a labelled button with one of four styles."""
    c = {
        "ghost":  (T["bg3"],        T["border_hi"], T["text2"]),
        "accent": (T["acc_dim"],    T["acc"],       T["acc"]),
        "green":  (T["acc2_dim"],   T["acc2"],      T["acc2"]),
        "danger": (T["danger_dim"], T["danger"],    T["danger"]),
    }
    bg, brd, fg = c.get(style, c["ghost"])
    rrect(cv, x1, y1, x2, y2, 4, fill=bg, outline=brd, width=1, tags=tag)
    cv.create_text(
        (x1 + x2) // 2, (y1 + y2) // 2,
        text=txt, font=F["hud_sm"], fill=fg,
        anchor="center", tags=tag,
    )