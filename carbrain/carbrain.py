"""
carbrain.py — CarBrain main entry point.

Raspberry Pi 5 + 3.5" touchscreen (480×320).
Pure Python / tkinter.  No additional pip packages required for sim mode.

Run:
    python3 carbrain.py

For real OBD (ELM327 Bluetooth):
    pip install obd
    Then set USE_REAL_OBD = True below and set OBD_PORT to your serial device.
"""

import tkinter as tk

# ── Select OBD source here ─────────────────────────────────────────────────
USE_REAL_OBD = False
OBD_PORT     = None          # e.g. "/dev/rfcomm0"  – None = auto-detect

# ── Imports ────────────────────────────────────────────────────────────────
from modules.config  import W, H, NAV_H, TOP_H, THEMES, POLL_MS
from modules.db      import DB
from modules.draw    import make_fonts
from modules.trip    import TripController
from modules.widgets import TopBar, NavBar

from modules.screen_home    import HomeScreen
from modules.screen_history import HistoryScreen
from modules.screen_weekly  import WeeklyScreen
from modules.screen_monthly import MonthlyScreen
from modules.screen_errors  import ErrorsScreen

from modules.modals import NewTripModal, ConfirmModal, PriceAdjustModal


# ══════════════════════════════════════════════════════════════════════════════
class CarBrain(tk.Tk):

    CONTENT_Y  = TOP_H
    CONTENT_H  = H - TOP_H - NAV_H

    def __init__(self):
        super().__init__()
        self.title("CarBrain")
        self.geometry(f"{W}x{H}+0+0")
        self.resizable(False, False)
        # self.overrideredirect(True)   # ← uncomment for kiosk / Pi

        # ── Core services ─────────────────────────────────────────────────
        self.db = DB()

        if USE_REAL_OBD:
            from modules.obd_interface import OBDReal
            self.obd = OBDReal(port=OBD_PORT)
        else:
            from modules.obd_interface import OBDSim
            self.obd = OBDSim()

        # ── Theme ─────────────────────────────────────────────────────────
        self.theme_name = self.db.get("theme", "night")
        self.T  = THEMES[self.theme_name]
        self.F  = make_fonts()
        self.configure(bg=self.T["bg"])

        # ── Trip controller ───────────────────────────────────────────────
        self.trip = TripController(self.db, self.obd)
        self.trip.fuel_price = float(self.db.get("fuel_price", 1.80))

        # ── Active modal ref ──────────────────────────────────────────────
        self._modal = None
        self._history_cleared = False
        self._cur   = "home"

        # ── Build UI ──────────────────────────────────────────────────────
        self._build()
        self._show("home")
        self._tick()

    # ── Build all persistent UI elements ──────────────────────────────────
    def _build(self):
        # Topbar + navbar
        self._topbar = TopBar(self, self.T, self.F,
                              on_theme_toggle=self._toggle_theme)
        self._navbar = NavBar(self, self.T, self.F,
                              on_tab=self._on_nav)

        # Create content canvases
        def mk(name):
            cv = tk.Canvas(self, bg=self.T["bg"], highlightthickness=0)
            cv.place(x=0, y=self.CONTENT_Y,
                     width=W, height=self.CONTENT_H)
            return cv

        self._cv = {
            "home":    mk("home"),
            "history": mk("history"),
            "weekly":  mk("weekly"),
            "monthly": mk("monthly"),
            "errors":  mk("errors"),
        }

        # Screen controllers
        self._home    = HomeScreen(self._cv["home"],    self.T, self.F, on_price_adjust=self._open_price_modal)
        self._history = HistoryScreen(
            self._cv["history"], self.T, self.F,
            on_continue  = self._continue_trip,
            on_end_trip  = self._request_end_trip,
            on_delete    = self._request_delete_trip,
            on_clear     = self._clear_history,
        )
        self._weekly  = WeeklyScreen(self._cv["weekly"],   self.T, self.F)
        self._monthly = MonthlyScreen(
            self._cv["monthly"], self.T, self.F,
            on_archive=self._do_archive,
        )
        self._errors  = ErrorsScreen(
            self._cv["errors"], self.T, self.F,
            on_clear_codes=self._clear_fault_codes,
        )

        # Hide all except home
        for name, cv in self._cv.items():
            if name != "home":
                cv.place_forget()

    # ── Navigation ─────────────────────────────────────────────────────────
    def _on_nav(self, tab_id: str):
        if tab_id == "new":
            self._open_new_trip_modal()
            return
        self._show(tab_id)

    def _show(self, name: str):
        self._cur = name
        for n, cv in self._cv.items():
            if n == name:
                cv.place(x=0, y=self.CONTENT_Y,
                         width=W, height=self.CONTENT_H)
            else:
                cv.place_forget()
        self._navbar.draw(active_tab=name)
        self._redraw_screen(name)

    def _redraw_screen(self, name: str):
        if name == "home":
            self._home.draw(self.obd.data, self.trip.fuel_price)
        elif name == "history":
            trips = [] if self._history_cleared else self.db.trips(limit=8, show_hidden=False)
            rows  = []
            for t in trips:
                rows.append({
                    "id":   t["id"],
                    "lbl":  t["date"][5:],
                    "km":   t["km"],
                    "avg":  t["avg_l100"],
                    "cost": t["cost"],
                    "fuel": t["fuel"],
                    "seg":  bool(t["parent_id"]),
                })
            self._history.draw(rows, self.trip.active_row_for_history())
        elif name == "weekly":
            self._weekly.draw(self.db.weekly_summary())
        elif name == "monthly":
            self._monthly.draw(
                self.db.total_stats(),
                self.db.get_month_archive(),
            )
        elif name == "errors":
            if USE_REAL_OBD:
                try:
                    codes = [
                        (c, d, "error") for c, d in self.obd.get_fault_codes()
                    ]
                    self._errors.set_codes(codes, simulated=False)
                except Exception:
                    pass
            self._errors.draw()

    # ── Theme ──────────────────────────────────────────────────────────────
    def _toggle_theme(self):
        self.theme_name = "day" if self.theme_name == "night" else "night"
        self.T = THEMES[self.theme_name]
        self.db.put("theme", self.theme_name)
        self.configure(bg=self.T["bg"])
        # Update theme in all sub-components
        self._topbar.update_theme(self.T, self.F)
        self._navbar.update_theme(self.T, self.F)
        for sc in [self._home, self._history, self._weekly,
                   self._monthly, self._errors]:
            sc.update_theme(self.T, self.F)
        # Refresh all canvases background
        for cv in self._cv.values():
            cv.configure(bg=self.T["bg"])
        self._topbar.draw(
            trip_active=self.trip.active,
            theme_name=self.theme_name,
        )
        self._navbar.draw(active_tab=self._cur)
        self._redraw_screen(self._cur)

    # ── Modals ─────────────────────────────────────────────────────────────
    def _open_new_trip_modal(self):
        if self._modal:
            return
        last_trips = self.db.trips(limit=5, show_hidden=False)
        self._modal = NewTripModal(
            self, self.T, self.F,
            fuel_price  = self.trip.fuel_price,
            last_trips  = last_trips,
            on_start    = self._start_trip,
            on_continue = self._continue_from_modal,
            on_cancel   = self._close_modal,
        )

    def _open_price_modal(self):
        if self._modal:
            return
        self._modal = PriceAdjustModal(
            self, self.T, self.F,
            fuel_price = self.trip.fuel_price,
            on_save    = self._update_price,
            on_cancel  = self._close_modal,
        )

    def _close_modal(self):
        # Modal already destroyed itself before calling this — just clear ref
        self._modal = None

    def _request_end_trip(self):
        if not self.trip.active:
            return
        if self._modal:
            return
        self._modal = ConfirmModal(
            self, self.T, self.F,
            title="END TRIP",
            body="Save and end the current trip?",
            on_yes=self._end_trip_confirmed,
            on_no=self._close_modal,
            yes_label="END TRIP",
            style="danger",
        )

    def _request_delete_trip(self, trip_id: int):
        if self._modal:
            return
        self._modal = ConfirmModal(
            self, self.T, self.F,
            title="DELETE TRIP",
            body=f"Permanently delete trip #{trip_id}?",
            on_yes=lambda: self._delete_trip(trip_id),
            on_no=self._close_modal,
            yes_label="DELETE",
            style="danger",
        )

    # ── Trip actions ───────────────────────────────────────────────────────
    def _start_trip(self, fuel_price: float):
        self._modal = None
        self.trip.start(fuel_price)
        self._topbar.draw(trip_active=True, theme_name=self.theme_name)
        self._show("home")

    def _continue_from_modal(self, trip_id: int, fuel_price: float):
        """Called when user taps CONT inside the NewTripModal."""
        self._modal = None
        # Update price first (may differ from saved trip's price)
        self.trip.fuel_price = fuel_price
        ok = self.trip.continue_from(trip_id)
        if ok:
            self._topbar.draw(trip_active=True, theme_name=self.theme_name)
            self._show("home")

    def _continue_trip(self, trip_id: int):
        """Called directly from history screen CONT button."""
        ok = self.trip.continue_from(trip_id)
        if ok:
            self._topbar.draw(trip_active=True, theme_name=self.theme_name)
            self._show("home")

    def _end_trip_confirmed(self):
        self._modal = None
        self.trip.end()
        self._topbar.draw(trip_active=False, theme_name=self.theme_name)
        self._show("history")

    def _delete_trip(self, trip_id: int):
        self._modal = None
        self.db.delete_trip(trip_id)
        self._show("history")

    def _update_price(self, new_price: float):
        self._modal = None
        self.trip.fuel_price = new_price
        self.db.put("fuel_price", new_price)

    def _clear_history(self):
        self._history_cleared = not self._history_cleared
        self._redraw_screen("history")

    def _clear_fault_codes(self):
        if USE_REAL_OBD:
            try:
                self.obd.clear_fault_codes()
                self._errors.set_codes([], simulated=False)
            except Exception as ex:
                print(f"[WARN] Could not clear DTC: {ex}")
        else:
            self._errors.set_codes([], simulated=True)
        self._redraw_screen("errors")

    def _do_archive(self):
        self.db.archive_and_purge_old_months()
        self._redraw_screen("monthly")

    # ── Main tick ──────────────────────────────────────────────────────────
    def _tick(self):
        # Clock in topbar
        self._topbar.tick()

        # Telemetry
        self.trip.tick()

        # Live-update current screen
        if self._modal is None:
            if self._cur == "home":
                self._home.draw(self.obd.data, self.trip.fuel_price)

        self.after(POLL_MS, self._tick)

    def on_close(self):
        if self.trip.active:
            self.trip.end()
        try:
            self.obd.stop()
        except Exception:
            pass
        self.destroy()


# ══════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    app = CarBrain()
    app.protocol("WM_DELETE_WINDOW", app.on_close)
    app.mainloop()