import tkinter as tk
from modules.config import W, H, NAV_H, TOP_H
from modules.draw import rrect


class HistoryScreen:
    def __init__(self, parent_canvas: tk.Canvas, T: dict, F: dict,
                 on_continue, on_end_trip, on_delete, on_clear):
        self.cv           = parent_canvas
        self.T            = T
        self.F            = F
        self._on_continue = on_continue
        self._on_end_trip = on_end_trip
        self._on_delete   = on_delete
        self._on_clear    = on_clear

    def update_theme(self, T, F):
        self.T = T
        self.F = F

    def draw(self, trips: list, active_row: dict | None):
        cv = self.cv
        cv.delete("all")
        T  = self.T
        cH = H - TOP_H - NAV_H

        # ── Header ──────────────────────────────────────────────────────
        rrect(cv, 4, 4, W - 4, 24, 3, fill=T["bg3"], outline=T["border"])
        cv.create_text(10, 14,
                       text="HISTORY  ·  tap CONT to resume a trip",
                       font=self.F["lbl"], fill=T["acc3"], anchor="w")

        # End-trip button (only relevant when trip is active)
        rrect(cv, W - 102, 6, W - 6, 22, 3,
              fill=T["danger_dim"], outline=T["danger"], tags="end_btn")
        cv.create_text(W - 54, 14, text="END TRIP ✕",
                       font=self.F["ui_xs"], fill=T["danger"],
                       anchor="center", tags="end_btn")
        cv.tag_bind("end_btn", "<Button-1>",
                    lambda e: self._on_end_trip())

        # Clear history button
        rrect(cv, W - 152, 6, W - 106, 22, 3,
              fill=T["acc_dim"], outline=T["acc"], tags="clear_btn")
        cv.create_text(W - 129, 14, text="HIDE ALL",
                       font=self.F["ui_xs"], fill=T["acc"],
                       anchor="center", tags="clear_btn")
        cv.tag_bind("clear_btn", "<Button-1>",
                    lambda e: self._on_clear())

        # ── Column headers ──────────────────────────────────────────────
        for lbl, x in [
            ("DATE",  6), ("KM",  98), ("L/100", 158),
            ("COST", 220), ("FUEL", 280), ("",    360),
        ]:
            cv.create_text(x, 32, text=lbl, font=self.F["ui_xs"],
                           fill=T["text3"], anchor="w")
        cv.create_line(4, 42, W - 4, 42, fill=T["border"])

        # ── Build display rows ───────────────────────────────────────────
        rows = []
        if active_row:
            rows.append(active_row)
        rows.extend(trips)

        RH = 24
        for i, row in enumerate(rows[:8]):
            ry  = 46 + i * RH
            act = row.get("active", False)
            bg  = T["acc2_dim"] if act else (T["bg2"] if i % 2 == 0 else T["bg"])
            rrect(cv, 4, ry, W - 4, ry + RH - 2, 2,
                  fill=bg, outline=T["border"])
            vc  = T["acc3"] if act else T["text"]

            lbl_txt = row["lbl"]
            if not act and row.get("seg"):
                lbl_txt += " +"

            cv.create_text(6,   ry + RH // 2, text=lbl_txt,
                           font=self.F["ui_sm"], fill=T["text2"], anchor="w")
            cv.create_text(128, ry + RH // 2, text=f"{row['km']:.1f}",
                           font=self.F["ui_sm"], fill=vc, anchor="center")
            cv.create_text(188, ry + RH // 2, text=f"{row['avg']:.1f}",
                           font=self.F["ui_sm"], fill=T["text2"], anchor="center")
            cv.create_text(250, ry + RH // 2, text=f"{row['cost']:.2f}",
                           font=self.F["ui_sm"], fill=T["acc"], anchor="center")
            cv.create_text(310, ry + RH // 2, text=f"{row['fuel']:.2f}",
                           font=self.F["ui_sm"], fill=T["text2"], anchor="center")

            if not act and row.get("id"):
                # CONT button
                cont_tag = f"cont{row['id']}"
                rrect(cv, 352, ry + 2, 394, ry + RH - 4, 2,
                      fill=T["acc_dim"], outline=T["acc"], tags=cont_tag)
                cv.create_text(373, ry + RH // 2, text="CONT",
                               font=self.F["ui_xs"], fill=T["acc"],
                               anchor="center", tags=cont_tag)
                cv.tag_bind(cont_tag, "<Button-1>",
                            lambda e, tid=row["id"]: self._on_continue(tid))

                # DEL button
                del_tag = f"del{row['id']}"
                rrect(cv, 398, ry + 2, W - 6, ry + RH - 4, 2,
                      fill=T["danger_dim"], outline=T["danger"], tags=del_tag)
                cv.create_text(418, ry + RH // 2, text="✕",
                               font=self.F["ui_xs"], fill=T["danger"],
                               anchor="center", tags=del_tag)
                cv.tag_bind(del_tag, "<Button-1>",
                            lambda e, tid=row["id"]: self._on_delete(tid))

        if not rows:
            cv.create_text(W // 2, cH // 2,
                           text="No trips recorded yet.",
                           font=self.F["hud_sm"], fill=T["text3"],
                           anchor="center")