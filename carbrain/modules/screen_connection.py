import tkinter as tk
import threading
import subprocess
import time

from modules.config import W, H, NAV_H, TOP_H
from modules.draw import rrect, shadowed


class ConnectionScreen:
    def __init__(self, parent_canvas: tk.Canvas, T: dict, F: dict,
                 on_connect, on_bypass, db=None):
        self.cv = parent_canvas
        self.T = T
        self.F = F
        self._on_connect = on_connect
        self._on_bypass = on_bypass
        self.db = db
        self._devices = []
        self._connecting = False
        self._scanning = False
        self._connection_status = None  # "connecting", "connected", "failed"
        self._auto_connect_attempted = False

    def update_theme(self, T, F):
        self.T = T
        self.F = F

    def start_auto_connect(self):
        """Try to auto-connect to the last used device."""
        if self._auto_connect_attempted or self._connecting:
            return
        self._auto_connect_attempted = True
        self._connection_status = "connecting"
        # Try to auto-connect (will check DB for last device)
        self._on_connect(mac=None)
        self.draw()

    def _scan_devices(self):
        """Scan for Bluetooth devices"""
        if self._scanning:
            return
        self._scanning = True
        self._devices = []

        def scan():
            try:
                # Use OBDReal's static method for device discovery
                from modules.obd_interface import OBDReal
                discovered = OBDReal.discover_devices()
                # Update devices list (thread-safe because Python GIL)
                self._devices = discovered
            except Exception as ex:
                print(f"[WARN] Bluetooth scan failed: {ex}")
            finally:
                self._scanning = False
                # Use after() to safely update UI from main thread
                self.cv.after(0, self.draw)

        threading.Thread(target=scan, daemon=True).start()

    def _connect_device(self, mac):
        """Connect to selected device"""
        self._connecting = True
        self._connection_status = "connecting"
        self.draw()
        self._on_connect(mac)

    def set_connection_status(self, status: str):
        """Set connection status after connection attempt."""
        self._connection_status = status
        self._connecting = False
        self.draw()

    def draw(self):
        cv = self.cv
        cv.delete("all")
        T = self.T
        cH = H - TOP_H - NAV_H

        # Header
        cv.create_rectangle(0, 0, W, 30, fill=T["border"], outline="")
        cv.create_text(W // 2, 15,
                       text="🔗 OBD CONNECTION",
                       font=self.F["hud_md"], fill=T["acc3"], anchor="center")

        # If successfully connected, show checkmark
        if self._connection_status == "connected":
            cv.create_text(W // 2, cH // 2 - 20,
                           text="✓", font=self.F["hud_xl"], fill=T["acc2"], anchor="center")
            cv.create_text(W // 2, cH // 2 + 20,
                           text="OBD Connected",
                           font=self.F["hud_md"], fill=T["acc2"], anchor="center")
            return

        # If connecting, show spinner
        if self._connection_status == "connecting":
            cv.create_text(W // 2, cH // 2 - 15,
                           text="⏳ Connecting...",
                           font=self.F["hud_md"], fill=T["acc3"], anchor="center")
            cv.create_text(W // 2, cH // 2 + 15,
                           text="Please wait",
                           font=self.F["ui_md"], fill=T["text3"], anchor="center")
            return

        # If failed, show retry option
        if self._connection_status == "failed":
            cv.create_text(W // 2, cH // 2 - 20,
                           text="❌ Connection Failed",
                           font=self.F["hud_md"], fill=T["danger"], anchor="center")
            cv.create_text(W // 2, cH // 2 + 15,
                           text="Try again or scan for devices",
                           font=self.F["ui_sm"], fill=T["text3"], anchor="center")

        # Main content area
        content_top = 35
        content_height = cH - content_top - 55  # Leave room for bypass button

        # Scan button
        btn_h = 35
        cv.create_rectangle(10, content_top, W - 10, content_top + btn_h,
                           fill=T["acc_dim"], outline=T["acc"], width=2, tags="scan_btn")
        scan_text = "🔍 Scanning..." if self._scanning else "🔍 Scan Bluetooth Devices"
        cv.create_text(W // 2, content_top + btn_h // 2, text=scan_text,
                       font=self.F["ui_md"], fill=T["acc"], anchor="center", tags="scan_btn")
        if not self._scanning:
            cv.tag_bind("scan_btn", "<Button-1>", lambda e: self._scan_devices())

        # Device list area
        list_top = content_top + btn_h + 10
        list_height = content_height - btn_h - 10

        if self._devices:
            # Title
            cv.create_text(15, list_top, text="Available Devices:",
                           font=self.F["ui_md"], fill=T["text"], anchor="nw")

            # Device items
            y_pos = list_top + 25
            max_devices = 3
            for i, (mac, name) in enumerate(self._devices[:max_devices]):
                if y_pos + 40 > list_top + list_height:
                    break

                # Device button
                dev_height = 40
                cv.create_rectangle(10, y_pos, W - 10, y_pos + dev_height,
                                   fill=T["bg3"], outline=T["acc2"], width=2, tags=f"dev_{i}")

                # Device name and MAC
                cv.create_text(20, y_pos + 10, text=name,
                               font=self.F["ui_md"], fill=T["text"], anchor="nw", tags=f"dev_{i}")
                cv.create_text(20, y_pos + 25, text=mac,
                               font=self.F["ui_xs"], fill=T["text2"], anchor="nw", tags=f"dev_{i}")

                cv.tag_bind(f"dev_{i}", "<Button-1>", lambda e, m=mac: self._connect_device(m))
                y_pos += dev_height + 5

            # Show more indicator
            if len(self._devices) > max_devices:
                cv.create_text(W // 2, y_pos + 5,
                              text=f"... and {len(self._devices) - max_devices} more",
                              font=self.F["ui_xs"], fill=T["text3"], anchor="center")
        else:
            # No devices message
            if self._scanning:
                cv.create_text(W // 2, list_top + 30,
                              text="Scanning for devices...",
                              font=self.F["ui_md"], fill=T["text3"], anchor="center")
            else:
                cv.create_text(W // 2, list_top + 20,
                              text="No devices found",
                              font=self.F["ui_md"], fill=T["text3"], anchor="center")
                cv.create_text(W // 2, list_top + 45,
                              text="Tap 'Scan' to search for Bluetooth devices",
                              font=self.F["ui_xs"], fill=T["text3"], anchor="center")

        # Bypass button at bottom
        bypass_y = cH - 48
        cv.create_rectangle(10, bypass_y, W - 10, bypass_y + 40,
                           fill=T["danger_dim"], outline=T["danger"], width=2, tags="bypass_btn")
        cv.create_text(W // 2, bypass_y + 20, text="⚠ Bypass (Testing - No Recording)",
                       font=self.F["ui_md"], fill=T["danger"], anchor="center", tags="bypass_btn")
        cv.tag_bind("bypass_btn", "<Button-1>", lambda e: self._on_bypass())