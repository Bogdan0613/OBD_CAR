import tkinter as tk
from datetime import datetime

from modules.config import W, H, NAV_H, TOP_H
from modules.draw import rrect


class TopBar:
    """
    Fixed status bar at top of screen.
    Shows app name, active trip indicator, clock, theme toggle.
    """

    def __init__(self, parent: tk.Misc, T: dict, F: dict,
                 on_theme_toggle):
        self._on_toggle = on_theme_toggle
        self.T = T
        self.F = F
        self.cv = tk.Canvas(parent, width=W, height=TOP_H,
                            bg=T["bg2"], highlightthickness=0)
        self.cv.place(x=0, y=0)
        self._clk_id = None
        self.draw(trip_active=False, theme_name="night")

    def update_theme(self, T, F):
        self.T = T
        self.F = F
        self.cv.configure(bg=T["bg2"])

    def draw(self, trip_active: bool, theme_name: str):
        cv = self.cv
        cv.delete("all")
        T  = self.T

        cv.create_line(0, TOP_H - 1, W, TOP_H - 1, fill=T["border"])
        cv.create_text(10, 14, text="CARBRAIN",
                       font=self.F["hud_sm"], fill=T["acc"], anchor="w")

        if trip_active:
            rrect(cv, 90, 6, 156, 22, 4,
                  fill=T["acc2_dim"], outline=T["acc2"], width=1)
            cv.create_text(123, 14, text="● TRIP",
                           font=self.F["ui_xs"], fill=T["acc2"],
                           anchor="center")

        lbl = "☀ DAY" if theme_name == "night" else "🌙 NIGHT"
        rrect(cv, W - 80, 5, W - 5, 23, 3,
              fill=T["bg3"], outline=T["border_hi"], width=1, tags="thm")
        cv.create_text(W - 43, 14, text=lbl,
                       font=self.F["ui_xs"], fill=T["text2"],
                       anchor="center", tags="thm")
        cv.tag_bind("thm", "<Button-1>", lambda e: self._on_toggle())

        self._clk_id = cv.create_text(W // 2, 14, text="",
                                       font=self.F["ui_sm"],
                                       fill=T["text2"], anchor="center")
        self._update_clock()

    def _update_clock(self):
        try:
            if self._clk_id:
                self.cv.itemconfig(
                    self._clk_id,
                    text=datetime.now().strftime("%a %d %b   %H:%M:%S"),
                    fill=self.T["text2"],
                )
        except Exception:
            pass

    def tick(self):
        """Call every second / every POLL_MS to refresh clock."""
        self._update_clock()


class NavBar:
    """
    Bottom navigation bar with tab buttons.
    """

    TABS = [
        ("HOME",    "home"),
        ("NEW",     "new"),
        ("HISTORY", "history"),
        ("WEEKLY",  "weekly"),
        ("MONTHLY", "monthly"),
        ("ERR",     "errors"),
    ]

    def __init__(self, parent: tk.Misc, T: dict, F: dict,
                 on_tab):          # callback(tab_id: str)
        self.T      = T
        self.F      = F
        self._on_tab = on_tab
        self.cv = tk.Canvas(parent, width=W, height=NAV_H,
                            bg=T["nav_bg"], highlightthickness=0)
        self.cv.place(x=0, y=H - NAV_H)
        self.draw(active_tab="home")

    def update_theme(self, T, F):
        self.T = T
        self.F = F
        self.cv.configure(bg=T["nav_bg"])

    def draw(self, active_tab: str = "home"):
        cv = self.cv
        cv.delete("all")
        T  = self.T
        n  = len(self.TABS)
        bw = W // n

        cv.create_line(0, 0, W, 0, fill=T["border"])

        for i, (lbl, tid) in enumerate(self.TABS):
            x1, x2 = i * bw, (i + 1) * bw
            xc = (x1 + x2) // 2
            ia = (tid == active_tab)
            ie = (tid == "errors")

            if ia:
                cv.create_rectangle(
                    x1 + 1, 1, x2 - 1, NAV_H - 1,
                    fill=T["danger_dim"] if ie else T["acc_dim"],
                    outline="",
                )
                cv.create_line(
                    x1 + 4, 2, x2 - 4, 2,
                    width=2,
                    fill=T["danger"] if ie else T["nav_active"],
                )

            fg = (
                T["danger"]     if ie else
                T["nav_active"] if ia else
                T["text2"]
            )
            cv.create_text(xc, NAV_H // 2 + 1,
                           text=lbl, font=self.F["ui_xs"],
                           fill=fg, anchor="center")

            if i > 0:
                cv.create_line(x1, 6, x1, NAV_H - 6, fill=T["border"])

            tag = f"nav_{tid}"
            cv.create_rectangle(x1, 0, x2, NAV_H,
                                 fill="", outline="", tags=tag)
            cv.tag_bind(tag, "<Button-1>",
                        lambda e, t=tid: self._on_tab(t))