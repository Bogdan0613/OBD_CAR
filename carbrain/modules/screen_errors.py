import tkinter as tk

from modules.config import W, H, NAV_H, TOP_H, MOCK_ERRORS
from modules.draw import rrect, shadowed


class ErrorsScreen:
    def __init__(self, parent_canvas: tk.Canvas, T: dict, F: dict,
                 on_clear_codes):
        self.cv              = parent_canvas
        self.T               = T
        self.F               = F
        self._on_clear_codes = on_clear_codes
        self._codes: list    = []
        self._sim            = True

    def update_theme(self, T, F):
        self.T = T
        self.F = F

    def set_codes(self, codes: list, simulated: bool = True):
        """
        codes = list of (code_str, description, severity)
        severity one of: "error" | "warn" | "info"
        """
        self._codes = codes
        self._sim   = simulated

    def draw(self):
        cv = self.cv
        cv.delete("all")
        T  = self.T
        cH = H - TOP_H - NAV_H

        codes = self._codes or MOCK_ERRORS

        # ── Header ──────────────────────────────────────────────────────
        rrect(cv, 4, 4, W - 4, 24, 3,
              fill=T["danger_dim"], outline=T["danger"])
        sim_txt = " (simulated)" if self._sim else ""
        cv.create_text(10, 14,
                       text=f"⚠  FAULT CODES{sim_txt}",
                       font=self.F["lbl"], fill=T["danger"], anchor="w")

        # Clear DTC button
        rrect(cv, W - 100, 6, W - 6, 22, 3,
              fill=T["acc_dim"], outline=T["acc"], tags="clr_btn")
        cv.create_text(W - 53, 14, text="CLEAR DTC",
                       font=self.F["ui_xs"], fill=T["acc"],
                       anchor="center", tags="clr_btn")
        cv.tag_bind("clr_btn", "<Button-1>", lambda e: self._on_clear_codes())

        # ── Code cards ──────────────────────────────────────────────────
        CARD_H = (cH - 30) // max(len(codes), 1)
        CARD_H = min(CARD_H, 58)

        for i, entry in enumerate(codes[:4]):
            if len(entry) == 2:
                code, desc = entry
                sev = "warn"
            else:
                code, desc, sev = entry

            col = T["danger"] if sev == "error" else (
                  T["acc"]   if sev == "warn"  else T["acc3"])

            ry = 30 + i * (CARD_H + 3)
            rrect(cv, 6, ry, W - 6, ry + CARD_H, 4,
                  fill=T["bg2"], outline=col)
            # Left severity bar
            cv.create_rectangle(6, ry, 12, ry + CARD_H,
                                 fill=col, outline="")

            # Code + desc
            shadowed(cv, 20, ry + 10, code, self.F["hud_md"],
                     col, T["bg"])
            cv.create_text(20, ry + CARD_H - 18,
                           text=desc, font=self.F["ui_sm"],
                           fill=T["text2"], anchor="w", width=W - 40)

            # Severity badge
            badge_txt = sev.upper()
            rrect(cv, W - 54, ry + 6, W - 10, ry + 20, 3,
                  fill=col if sev == "error" else T["bg3"],
                  outline=col)
            cv.create_text(W - 32, ry + 13,
                           text=badge_txt, font=self.F["ui_xs"],
                           fill=T["text"] if sev == "error" else col,
                           anchor="center")

        if not codes:
            cv.create_oval(W // 2 - 20, cH // 2 - 20,
                           W // 2 + 20, cH // 2 + 20,
                           fill=T["acc2_dim"], outline=T["acc2"], width=2)
            cv.create_text(W // 2, cH // 2, text="✓",
                           font=self.F["hud_lg"], fill=T["acc2"],
                           anchor="center")
            cv.create_text(W // 2, cH // 2 + 30,
                           text="No fault codes",
                           font=self.F["hud_sm"], fill=T["acc2"],
                           anchor="center")

        cv.create_text(W // 2, cH - 6,
                       text="Connect OBD-II Bluetooth for real diagnostics",
                       font=self.F["ui_xs"], fill=T["text3"], anchor="center")