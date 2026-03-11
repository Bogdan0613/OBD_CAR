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

        # Button regions for click detection
        self._scan_btn_rect = None
        self._bypass_btn_rect = None
        self._device_rects = {}  # device_idx -> (x1, y1, x2, y2)

        # Bind canvas click events
        self.cv.bind("<Button-1>", self._on_canvas_click)

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

    def _connect_device(self, mac, name=None):
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

    def _on_canvas_click(self, event):
        """Handle canvas clicks by checking coordinates."""
        x, y = event.x, event.y

        # Check scan button
        if self._scan_btn_rect:
            x1, y1, x2, y2 = self._scan_btn_rect
            if x1 <= x <= x2 and y1 <= y <= y2 and not self._scanning:
                self._scan_devices()
                return

        # Check device buttons
        for device_idx, (x1, y1, x2, y2) in self._device_rects.items():
            if x1 <= x <= x2 and y1 <= y <= y2:
                mac, name = self._devices[device_idx]
                self._connect_device(mac, name)
                return

        # Check bypass button
        if self._bypass_btn_rect:
            x1, y1, x2, y2 = self._bypass_btn_rect
            if x1 <= x <= x2 and y1 <= y <= y2:
                self._on_bypass()
                return

    def draw(self):
        cv = self.cv
        cv.delete("all")
        T = self.T
        cH = H - TOP_H - NAV_H

        # Reset button regions
        self._scan_btn_rect = None
        self._bypass_btn_rect = None
        self._device_rects = {}

        # Header
        cv.create_rectangle(0, 0, W, 25, fill=T["border"], outline="")
        cv.create_text(W // 2, 12, text="🔗 OBD",
                       font=self.F["hud_md"], fill=T["acc3"], anchor="center")

        # Connected state
        if self._connection_status == "connected":
            cv.create_text(W // 2, cH // 2 - 20,
                           text="✓ Connected", font=self.F["hud_lg"], fill=T["acc2"], anchor="center")
            cv.create_text(W // 2, cH // 2 + 10,
                           text="Loading...", font=self.F["ui_md"], fill=T["text3"], anchor="center")
            return

        # Connecting state
        if self._connection_status == "connecting":
            cv.create_text(W // 2, cH // 2,
                           text="⏳ Connecting...", font=self.F["hud_md"], fill=T["acc3"], anchor="center")
            return

        # Failed state
        if self._connection_status == "failed":
            cv.create_text(W // 2, cH // 2 - 15,
                           text="❌ Failed", font=self.F["hud_md"], fill=T["danger"], anchor="center")
            cv.create_text(W // 2, cH // 2 + 5,
                           text="Tap SCAN", font=self.F["ui_md"], fill=T["text3"], anchor="center")

        # Scan button
        y = 30
        scan_color = T["acc2_dim"] if self._scanning else T["acc_dim"]
        cv.create_rectangle(8, y, W - 8, y + 35,
                           fill=scan_color, outline=T["acc"], width=2)
        scan_text = "SCANNING" if self._scanning else "SCAN"
        cv.create_text(W // 2, y + 17, text=scan_text,
                       font=self.F["hud_md"], fill=T["acc"], anchor="center")
        self._scan_btn_rect = (8, y, W - 8, y + 35)

        # Device list
        y += 40
        device_idx = 0
        for mac, name in self._devices[:5]:  # Max 5 devices
            cv.create_rectangle(8, y, W - 8, y + 32,
                               fill=T["bg3"], outline=T["acc2"], width=1)
            cv.create_text(12, y + 7, text=name, font=self.F["hud_sm"], fill=T["text"],
                           anchor="nw")
            cv.create_text(12, y + 20, text=mac, font=self.F["ui_xs"], fill=T["text2"],
                           anchor="nw")
            self._device_rects[device_idx] = (8, y, W - 8, y + 32)
            y += 33
            device_idx += 1

        # Show how many more if needed
        if len(self._devices) > 5:
            cv.create_text(W // 2, y, text=f"+{len(self._devices) - 5} more",
                           font=self.F["ui_xs"], fill=T["text2"], anchor="center")
            y += 20

        # Bypass button at bottom
        bypass_y = cH - 32
        cv.create_rectangle(8, bypass_y, W - 8, cH - 2,
                           fill=T["danger_dim"], outline=T["danger"], width=2)
        cv.create_text(W // 2, bypass_y + 15, text="BYPASS",
                       font=self.F["hud_md"], fill=T["danger"], anchor="center")
        self._bypass_btn_rect = (8, bypass_y, W - 8, cH - 2)