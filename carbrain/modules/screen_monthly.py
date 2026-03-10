import tkinter as tk
from datetime import datetime

from modules.config import W, H, NAV_H, TOP_H
from modules.draw import rrect, segbar


class MonthlyScreen:
    def __init__(self, parent_canvas: tk.Canvas, T: dict, F: dict,
                 on_archive):
        self.cv          = parent_canvas
        self.T           = T
        self.F           = F
        self._on_archive = on_archive

    def update_theme(self, T, F):
        self.T = T
        self.F = F

    def draw(self, monthly: dict, archives: list):
        cv = self.cv
        cv.delete("all")
        T  = self.T
        cH = H - TOP_H - NAV_H

        # ── Header ──────────────────────────────────────────────────────
        rrect(cv, 4, 4, W - 4, 24, 3, fill=T["bg3"], outline=T["border"])
        cv.create_text(
            10, 14,
            text=f"TOTAL STATS",
            font=self.F["lbl"], fill=T["acc"], anchor="w",
        )
        rrect(cv, W - 126, 6, W - 6, 22, 3,
              fill=T["acc_dim"], outline=T["acc"], tags="arch_btn")
        cv.create_text(W - 66, 14, text="ARCHIVE OLD ▶",
                       font=self.F["ui_xs"], fill=T["acc"],
                       anchor="center", tags="arch_btn")
        cv.tag_bind("arch_btn", "<Button-1>", lambda e: self._on_archive())

        # ── KPI 2×3 grid ─────────────────────────────────────────────────
        s  = monthly
        n  = max(s["n"], 1)
        CW = W // 2 - 6
        CC = (cH - 36) // 3

        cells = [
            (s["n"],                  "",    "TRIPS",      T["acc"],   0, 0),
            (f"{s['km']:.1f}",       "km",  "DISTANCE",   T["text"],  1, 0),
            (f"{s['fuel']:.2f}",     "L",   "FUEL USED",  T["text"],  0, 1),
            (f"{s['cost']:.2f}",     "€",   "TOTAL COST", T["acc2"],  1, 1),
            (f"{s['cost']/n:.2f}",   "€",   "AVG/TRIP",   T["text2"], 0, 2),
            (f"{s['km']/n:.1f}",     "km",  "AVG KM",     T["text2"], 1, 2),
        ]
        for val, unit, lbl, col, ci, ri in cells:
            x1 = 4  + ci * (CW + 4)
            y1 = 30 + ri * (CC + 3)
            x2 = x1 + CW
            y2 = y1 + CC
            rrect(cv, x1, y1, x2, y2, 4, fill=T["bg2"], outline=T["border"])
            xc = (x1 + x2) // 2
            yc = (y1 + y2) // 2
            cv.create_text(xc, yc - 10, text=str(val),
                           font=self.F["hud_lg"], fill=col, anchor="center")
            cv.create_text(xc, yc + 12,
                           text=f"{unit}  ·  {lbl}",
                           font=self.F["ui_xs"], fill=T["text3"],
                           anchor="center")

        # ── Efficiency bar ───────────────────────────────────────────────
        avg_l100 = s.get("avg_l100", 0)
        if avg_l100 > 0:
            bar_y = cH - 36
            rrect(cv, 4, bar_y, W - 4, bar_y + 20, 3,
                  fill=T["bg2"], outline=T["border"])
            cv.create_text(10, bar_y + 10,
                           text=f"AVG EFFICIENCY: {avg_l100:.1f} L/100km",
                           font=self.F["lbl"], fill=T["acc3"], anchor="w")
            segbar(cv, 260, bar_y + 6, W - 16, 8,
                   avg_l100, 4, 20, T["acc3"], T["bg3"], segs=12)

        # ── Archive list ─────────────────────────────────────────────────
        if archives:
            ay = cH - 14
            parts = []
            for a in archives[:6]:
                parts.append(f"{a['month']}  {a['km']:.0f}km  {a['cost']:.0f}€")
            cv.create_text(10, ay,
                           text="ARCHIVED: " + "   ".join(
                               a["month"] for a in archives[:5]
                           ),
                           font=self.F["ui_xs"], fill=T["text3"], anchor="w")