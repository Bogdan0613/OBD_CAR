import tkinter as tk
from datetime import date, timedelta
from collections import defaultdict

from modules.config import W, H, NAV_H, TOP_H
from modules.draw import rrect, segbar


class WeeklyScreen:
    def __init__(self, parent_canvas: tk.Canvas, T: dict, F: dict):
        self.cv = parent_canvas
        self.T  = T
        self.F  = F

    def update_theme(self, T, F):
        self.T = T
        self.F = F

    def draw(self, ws: dict):
        cv = self.cv
        cv.delete("all")
        T  = self.T
        cH = H - TOP_H - NAV_H

        since = (date.today() - timedelta(days=6)).strftime("%d %b")
        today = date.today().strftime("%d %b")

        rrect(cv, 4, 4, W - 4, 24, 3, fill=T["bg3"], outline=T["border"])
        cv.create_text(W // 2, 14,
                       text=f"LAST 7 DAYS  ·  {since} → {today}",
                       font=self.F["lbl"], fill=T["acc3"], anchor="center")

        # ── Summary strip ────────────────────────────────────────────────
        rrect(cv, 4, 28, W - 4, 62, 3, fill=T["bg2"], outline=T["border"])
        avg_l100 = (ws["fuel"] / ws["km"] * 100) if ws["km"] > 0.001 else 0
        for xc, val, lbl, col in [
            (55,  str(ws["n"]),          "TRIPS",  T["acc"]),
            (165, f"{ws['km']:.1f}",     "KM",     T["text"]),
            (275, f"{ws['fuel']:.2f}",   "LITRES", T["text"]),
            (375, f"{avg_l100:.1f}",     "L/100",  T["acc3"]),
            (455, f"{ws['cost']:.2f} €", "COST",   T["acc2"]),
        ]:
            cv.create_text(xc, 38, text=val,  font=self.F["hud_sm"],
                           fill=col, anchor="center")
            cv.create_text(xc, 53, text=lbl,  font=self.F["ui_xs"],
                           fill=T["text3"], anchor="center")
        for sx in [110, 220, 330, 420]:
            cv.create_line(sx, 32, sx, 58, fill=T["border"])

        # ── Trip rows ────────────────────────────────────────────────────
        row_y0 = 68
        for lbl, x in [
            ("DATE", 6), ("KM", 98), ("L/100", 158),
            ("COST", 220), ("FUEL", 280),
        ]:
            cv.create_text(x, row_y0, text=lbl, font=self.F["ui_xs"],
                           fill=T["text3"], anchor="w")
        cv.create_line(4, row_y0 + 10, W - 4, row_y0 + 10, fill=T["border"])

        RH = 22
        for i, t in enumerate(ws["trips"][:5]):
            ry = row_y0 + 12 + i * RH
            if ry + RH > cH:
                break
            rrect(cv, 4, ry, W - 4, ry + RH - 2, 2,
                  fill=T["bg2"] if i % 2 == 0 else T["bg"],
                  outline=T["border"])
            seg = " +" if t.get("parent_id") else ""
            cv.create_text(6,   ry + RH // 2,
                           text=t["date"][5:] + seg,
                           font=self.F["ui_sm"], fill=T["text2"], anchor="w")
            cv.create_text(128, ry + RH // 2,
                           text=f"{t['km']:.1f}",
                           font=self.F["ui_sm"], fill=T["text"], anchor="center")
            cv.create_text(188, ry + RH // 2,
                           text=f"{t['avg_l100']:.1f}",
                           font=self.F["ui_sm"], fill=T["text2"], anchor="center")
            cv.create_text(250, ry + RH // 2,
                           text=f"{t['cost']:.2f}",
                           font=self.F["ui_sm"], fill=T["acc"], anchor="center")
            cv.create_text(310, ry + RH // 2,
                           text=f"{t['fuel']:.2f}",
                           font=self.F["ui_sm"], fill=T["text2"], anchor="center")

        if not ws["trips"]:
            cv.create_text(W // 2, cH // 2,
                           text="No trips in the last 7 days.",
                           font=self.F["hud_sm"], fill=T["text3"],
                           anchor="center")