"""
carbrain.py — CarBrain main entry point.

Raspberry Pi 5 + 3.5" touchscreen (480×320).
Pure Python / tkinter.  No additional pip packages required for sim mode.

Run:
    python3 carbrain.py

For real OBD (ELM327 Bluetooth):
    pip install obd
    Then connect through the UI connection screen.
"""

import tkinter as tk

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
from modules.screen_connection import ConnectionScreen

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
        self.overrideredirect(True)   # ← uncomment for kiosk / Pi

        # ── Core services ─────────────────────────────────────────────────
        self.db = DB()

        # ── Theme ─────────────────────────────────────────────────────────
        self.theme_name = self.db.get("theme", "night")
        self.T  = THEMES[self.theme_name]
        self.F  = make_fonts()
        self.configure(bg=self.T["bg"])

        # ── OBD will be initialized after connection ─────────────────────
        self.obd = None

        # ── Trip controller will be initialized after connection ─────────
        self.trip = None

        # ── Active modal ref ──────────────────────────────────────────────
        self._modal = None
        self._history_cleared = False
        self._cur   = "connection"
        self._main_ui_built = False

        # ── Connection screen ─────────────────────────────────────────────
        self._conn_canvas = tk.Canvas(self, bg=self.T["bg"], highlightthickness=0)
        self._conn_canvas.place(x=0, y=0, width=W, height=H)

        self._conn_screen = ConnectionScreen(
            self._conn_canvas, self.T, self.F,
            on_connect=self._on_connect_selected,
            on_bypass=self._on_bypass_selected,
        )
        self._conn_screen.draw()

        # Schedule auto-connect attempt
        print("[DEBUG] Scheduling auto-connect in 500ms...")
        self.after(500, self._conn_screen.start_auto_connect)

        print("[DEBUG] Starting main event loop...")
        self._tick()

    def _on_connect_selected(self, mac: str = None):
        """User selected to connect to a device or auto-connect."""
        try:
            if mac is None:
                # Try to auto-connect to last device
                last_mac = self.db.get("last_obd_device")
                if last_mac:
                    mac = last_mac
                else:
                    # No last device, show message and return
                    print("[INFO] No previously connected device found. User must select device.")
                    self._conn_screen.set_connection_status("failed")
                    return

            print(f"[INFO] Attempting to connect to OBD device: {mac}")

            # Create rfcomm binding (Linux/Raspberry Pi)
            import subprocess
            import platform
            port = "/dev/rfcomm0"

            if platform.system() == "Linux":
                try:
                    print(f"[DEBUG] Releasing rfcomm0...")
                    # Unbind first if already bound
                    subprocess.run(["rfcomm", "release", "0"], capture_output=True, timeout=5)
                    print(f"[DEBUG] Binding rfcomm0 to {mac}...")
                    # Create new binding
                    result = subprocess.run(["rfcomm", "bind", "0", mac], capture_output=True, text=True, timeout=10)
                    if result.returncode != 0:
                        print(f"[WARN] rfcomm bind failed: {result.stderr}")
                        self._conn_screen.set_connection_status("failed")
                        return
                    print(f"[INFO] rfcomm bound to {mac}")
                except FileNotFoundError:
                    print("[WARN] rfcomm command not found. Run: sudo apt-get install bluez")
                    self._conn_screen.set_connection_status("failed")
                    return
                except subprocess.TimeoutExpired:
                    print("[WARN] rfcomm command timed out")
                    self._conn_screen.set_connection_status("failed")
                    return
                except Exception as e:
                    print(f"[WARN] rfcomm bind error: {e}")
                    self._conn_screen.set_connection_status("failed")
                    return

            from modules.obd_interface import OBDReal
            self.obd = OBDReal()

            # Try to connect
            if self.obd.connect(port=port):
                # Connection successful
                self.db.put("last_obd_device", mac)
                print("[INFO] OBD connection established")
                self._conn_screen.set_connection_status("connected")
                # Small delay to show connected state before transitioning
                self.after(800, self._initialize_main_app)
            else:
                print("[WARN] OBD connection failed")
                self.obd = None
                self._conn_screen.set_connection_status("failed")
        except Exception as e:
            print(f"[ERROR] _on_connect_selected failed: {e}")
            import traceback
            traceback.print_exc()
            self._conn_screen.set_connection_status("failed")

    def _on_bypass_selected(self):
        """User selected bypass mode (testing without OBD)."""
        print("[INFO] Using bypass mode (testing without recordings)")
        from modules.obd_interface import OBDBypass
        self.obd = OBDBypass()
        self._conn_screen.set_connection_status("connected")
        # Small delay to show connected state before transitioning
        self.after(800, self._initialize_main_app)

    def _initialize_main_app(self):
        """Initialize the main app after OBD connection is established."""
        if self._main_ui_built:
            return

        # Initialize trip controller
        self.trip = TripController(self.db, self.obd)
        self.trip.fuel_price = float(self.db.get("fuel_price", 1.80))

        # Hide connection canvas
        self._conn_canvas.place_forget()

        # Build main UI
        self._build()
        self._show("home")
        self._main_ui_built = True
        self._cur = "home"

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
            if self.obd:
                self._home.draw(self.obd.data, self.trip.fuel_price)
            else:
                # Fallback if OBD not initialized
                self._home.draw({}, self.trip.fuel_price)
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
            # Only try to read real OBD codes if it's a real OBD connection
            from modules.obd_interface import OBDReal
            if isinstance(self.obd, OBDReal) and self.obd.is_connected:
                try:
                    codes = [
                        (c, d, "error") for c, d in self.obd.get_fault_codes()
                    ]
                    self._errors.set_codes(codes, simulated=False)
                except Exception as ex:
                    print(f"[WARN] Could not read fault codes: {ex}")
                    self._errors.set_codes([], simulated=False)
            else:
                self._errors.set_codes([], simulated=True)
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
        from modules.obd_interface import OBDReal
        if isinstance(self.obd, OBDReal) and self.obd.is_connected:
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
        if not self._main_ui_built:
            # Still on connection screen
            self.after(POLL_MS, self._tick)
            return

        # Clock in topbar
        self._topbar.tick()

        # Telemetry
        self.trip.tick()

        # Live-update current screen
        if self._modal is None and self._main_ui_built:
            if self._cur == "home" and self.obd and self.trip:
                self._home.draw(self.obd.data, self.trip.fuel_price)

        self.after(POLL_MS, self._tick)

    def on_close(self):
        if self.trip and self.trip.active:
            self.trip.end()
        if self.obd:
            try:
                self.obd.stop()
            except Exception:
                pass
        self.destroy()


# ══════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    print("[APP] Initializing CarBrain...")
    app = CarBrain()
    print("[APP] GUI created, running mainloop...")
    app.protocol("WM_DELETE_WINDOW", app.on_close)
    app.mainloop()