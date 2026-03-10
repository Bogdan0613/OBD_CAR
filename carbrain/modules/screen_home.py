import math
import tkinter as tk

from modules.config import W, H, NAV_H, TOP_H
from modules.draw import (
    rrect, arc_gauge, segbar, shadowed, lerp_hex, sparkline
)


class HomeScreen:
    """
    Owns a single tk.Canvas ('home') and redraws it every tick.
    """

    def __init__(self, parent_canvas: tk.Canvas, T: dict, F: dict, on_price_adjust):
        self.cv = parent_canvas
        self.T  = T
        self.F  = F
        self._on_price_adjust = on_price_adjust
        # Rolling buffer for sparklines
        self._HIST = 40

    def update_theme(self, T, F):
        self.T = T
        self.F = F

    def draw(self, d: dict, fuel_price: float):
        cv = self.cv
        cv.delete("all")
        T  = self.T

        cH = H - TOP_H - NAV_H

        # Layout zones
        LX1, LX2 = 4, 158
        RX1, RX2 = 162, W - 4
        TY1 = 4
        TY2 = cH - 62
        BY1 = cH - 58
        BY2 = cH - 4
        RW  = RX2 - RX1
        TH  = TY2 - TY1

        # ── Left: RPM panel ────────────────────────────────────────────────
        rrect(cv, LX1, TY1, LX2, TY2, 5, fill=T["bg2"], outline=T["border"])
        cx, cy, r = (LX1 + LX2) // 2, TY1 + 86, 52
        arc_gauge(cv, cx, cy, r, 215, -250, d["rpm"], 0, 6000, T["acc"], T["bg3"], w=8)

        # RPM digit
        shadowed(
            cv, cx, cy - 12,
            f"{d['rpm']:,}", self.F["hud_md"], T["acc"], T["bg"],
            anchor="center",
        )
        cv.create_text(cx, cy + 10, text="RPM", font=self.F["ui_xs"],
                       fill=T["text3"], anchor="center")

        # RPM segbar
        sby = TY1 + 154
        segbar(cv, LX1 + 8, sby, LX2 - LX1 - 16, 4,
               d["rpm"], 0, 6000, T["acc"], T["bg3"], segs=10)

        # Speed (if available)
        spd = d.get("speed", 0)
        cv.create_text(cx, sby + 14, text=f"{spd:.0f} km/h",
                       font=self.F["ui_xs"], fill=T["text2"], anchor="center")

        cv.create_text(cx, sby + 24, text="ENGINE",
                       font=self.F["ui_xs"], fill=T["text3"], anchor="center")

        # ── Right column: KPI grid ─────────────────────────────────────────
        # Coolant strip at top
        CH   = 32
        CY1  = TY1 + 2
        CY2  = CY1 + CH
        # 2x2 KPI grid below coolant
        K1Y1 = CY2 + 3
        KROW = (TY2 - K1Y1 - 2) // 2
        K1Y2 = K1Y1 + KROW
        K2Y1 = K1Y2 + 1
        K2Y2 = TY2 - 2
        HALF = RW // 2
        MID  = RX1 + HALF

        # ── Coolant strip ─────────────────────────────────────────────────
        st  = d["state"]
        cc  = {"COLD": T["cold"], "WARM": T["warm"], "HOT": T["hot"]}[st]
        ci  = {"COLD": "❄", "WARM": "〰", "HOT": "🔥"}[st]
        rrect(cv, RX1, CY1, RX2, CY2, 5,
              fill=lerp_hex(T["bg2"], cc, 0.10), outline=cc, width=1)
        yc = (CY1 + CY2) // 2
        cv.create_text(RX1 + 20, yc, text=ci, font=self.F["hud_sm"],
                       fill=cc, anchor="center")
        shadowed(cv, RX1 + 42, yc, st, self.F["hud_sm"], cc, T["bg"], anchor="w")
        cv.create_text(MID + 10, yc, text=f"{d['cool']}°C",
                       font=self.F["hud_sm"], fill=cc, anchor="center")
        segbar(cv, MID + 50, yc - 3, RX2 - MID - 58, 6,
               d["cool"], 30, 110, cc, T["bg3"], segs=8)

        # ── KPI cells ─ 2x2 grid ──────────────────────────────────────────
        def kpi(x1, y1, x2, y2, lbl, val, unit, vc,
                bv=None, bmn=0, bmx=100, bc=None, hist=None):
            rrect(cv, x1, y1, x2, y2, 4, fill=T["bg2"], outline=T["border"])
            xc = (x1 + x2) // 2
            cv.create_text(xc, y1 + 8, text=lbl, font=self.F["ui_xs"],
                           fill=T["text3"], anchor="center")
            shadowed(cv, xc, y1 + 26, val, self.F["hud_lg"], vc, T["bg"],
                     anchor="center")
            cv.create_text(xc, y1 + 42, text=unit, font=self.F["ui_xs"],
                           fill=T["text2"], anchor="center")
            if bv is not None and bc:
                segbar(cv, x1 + 6, y2 - 8, x2 - x1 - 12, 3,
                       bv, bmn, bmx, bc, T["bg3"], segs=8)

        # Row 1: INSTANT | AVERAGE
        kpi(
            RX1, K1Y1, MID - 1, K1Y2,
            "INSTANT", f"{d['inst']:.1f}", "L/100km", T["acc"],
            bv=d["inst"], bmn=4, bmx=22, bc=T["acc"],
        )
        kpi(
            MID + 1, K1Y1, RX2, K1Y2,
            "AVERAGE", f"{d['avg']:.1f}", "L/100km", T["acc3"],
            bv=d["avg"], bmn=4, bmx=22, bc=T["acc3"],
        )

        # Row 2: ENG LOAD | THROTTLE
        engload = d.get("engload", 0)
        throttle = d.get("throttle", 0)
        kpi(
            RX1, K2Y1, MID - 1, K2Y2,
            "ENG LOAD", f"{engload:.0f}", "%", T["warm"],
            bv=engload, bmn=0, bmx=100, bc=T["warm"],
        )
        kpi(
            MID + 1, K2Y1, RX2, K2Y2,
            "THROTTLE", f"{throttle:.0f}", "%", T["acc2"],
            bv=throttle, bmn=0, bmx=100, bc=T["acc2"],
        )

        # ── Bottom stats strip ────────────────────────────────────────────
        rrect(cv, 4, BY1, W - 4, BY2, 5, fill=T["bg2"], outline=T["border"])
        km    = d["km"]
        fuel  = d["fuel"]
        cost  = fuel * fuel_price
        volt  = d.get("voltage", 0)

        for xc, val, unit, lbl, col in [
            (52,  f"{km:.2f}",          "km",   "TRIP KM",  T["text"]),
            (146, f"{fuel:.3f}",        "L",    "FUEL",     T["text"]),
            (240, f"{cost:.2f}",        "€",    "COST",     T["acc"]),
            (334, f"{fuel_price:.2f}",  "€/L",  "PRICE",    T["text2"]),
            (428, f"{volt:.1f}",        "V",    "BATTERY",  T["acc3"]),
        ]:
            tags = "price" if lbl == "PRICE" else ""
            cv.create_text(xc, BY1 + 12, text=val,  font=self.F["hud_md"],
                           fill=col, anchor="center", tags=tags)
            cv.create_text(xc, BY1 + 26, text=unit, font=self.F["ui_xs"],
                           fill=T["text3"], anchor="center", tags=tags)
            cv.create_text(xc, BY1 + 38, text=lbl,  font=self.F["ui_xs"],
                           fill=T["text3"], anchor="center", tags=tags)
            if tags:
                cv.tag_bind(tags, "<Button-1>", lambda e: self._on_price_adjust())

        for sx in [98, 192, 286, 380]:
            cv.create_line(sx, BY1 + 4, sx, BY2 - 4, fill=T["border"])