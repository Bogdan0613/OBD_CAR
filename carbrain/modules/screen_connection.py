import tkinter as tk
import threading
import subprocess
import time

from modules.config import W, H, NAV_H, TOP_H
from modules.draw import rrect, shadowed


class ConnectionScreen:
    def __init__(self, parent_canvas: tk.Canvas, T: dict, F: dict,
                 on_connect, on_bypass):
        self.cv = parent_canvas
        self.T = T
        self.F = F
        self._on_connect = on_connect
        self._on_bypass = on_bypass
        self._devices = []
        self._connected = False
        self._scanning = False

    def update_theme(self, T, F):
        self.T = T
        self.F = F

    def set_connected(self, connected: bool):
        self._connected = connected

    def _scan_devices(self):
        """Scan for Bluetooth devices"""
        if self._scanning:
            return
        self._scanning = True
        self._devices = []

        def scan():
            try:
                # Run hcitool scan
                result = subprocess.run(["hcitool", "scan"], capture_output=True, text=True, timeout=10)
                lines = result.stdout.strip().split('\n')[1:]  # Skip header
                for line in lines:
                    parts = line.strip().split('\t')
                    if len(parts) >= 2:
                        mac = parts[0].strip()
                        name = parts[1].strip() if len(parts) > 1 else "Unknown"
                        if mac and name:
                            self._devices.append((mac, name))
            except Exception as ex:
                print(f"[WARN] Bluetooth scan failed: {ex}")
            finally:
                self._scanning = False
                # Redraw after scan
                self.cv.after(0, self.draw)

        threading.Thread(target=scan, daemon=True).start()

    def _connect_device(self, mac):
        """Connect to selected device"""
        self._on_connect(mac)

    def draw(self):
        cv = self.cv
        cv.delete("all")
        T = self.T
        cH = H - TOP_H - NAV_H

        # Header
        rrect(cv, 4, 4, W - 4, 24, 3,
              fill=T["danger_dim"], outline=T["danger"])
        cv.create_text(10, 14,
                       text="🔗 OBD CONNECTION",
                       font=self.F["lbl"], fill=T["danger"], anchor="w")

        if self._connected:
            # Connected status
            cv.create_oval(W // 2 - 30, cH // 2 - 30,
                           W // 2 + 30, cH // 2 + 30,
                           fill=T["acc2_dim"], outline=T["acc2"], width=3)
            cv.create_text(W // 2, cH // 2, text="✓",
                           font=self.F["hud_xl"], fill=T["acc2"], anchor="center")
            cv.create_text(W // 2, cH // 2 + 40,
                           text="OBD Connected",
                           font=self.F["hud_md"], fill=T["acc2"], anchor="center")
            return

        # Auto-connect button
        rrect(cv, 20, 40, W - 20, 80, 5,
              fill=T["acc_dim"], outline=T["acc"], tags="auto_connect")
        cv.create_text(W // 2, 60, text="🔄 Auto-Connect OBD",
                       font=self.F["ui_lg"], fill=T["acc"], anchor="center", tags="auto_connect")
        cv.tag_bind("auto_connect", "<Button-1>", lambda e: self._on_connect())

        # Scan devices button
        rrect(cv, 20, 90, W - 20, 130, 5,
               fill=T["bg2"], outline=T["acc"], tags="scan_btn")
        scan_text = "🔍 Scanning..." if self._scanning else "🔍 Scan Bluetooth Devices"
        cv.create_text(W // 2, 110, text=scan_text,
                       font=self.F["ui_lg"], fill=T["acc"], anchor="center", tags="scan_btn")
        if not self._scanning:
            cv.tag_bind("scan_btn", "<Button-1>", lambda e: self._scan_devices())

        # Device list
        y_start = 140
        if self._devices:
            cv.create_text(20, y_start, text="Available Devices:",
                           font=self.F["ui_md"], fill=T["text"], anchor="w")
            for i, (mac, name) in enumerate(self._devices[:5]):  # Show up to 5
                y = y_start + 20 + i * 35
                rrect(cv, 20, y, W - 20, y + 30, 3,
                      fill=T["bg3"], outline=T["acc2"], tags=f"dev_{i}")
                cv.create_text(30, y + 15, text=f"{name}\n{mac}",
                               font=self.F["ui_sm"], fill=T["text"], anchor="w", tags=f"dev_{i}")
                cv.tag_bind(f"dev_{i}", "<Button-1>", lambda e, m=mac: self._connect_device(m))

        # Bypass button (for testing)
        rrect(cv, 20, cH - 50, W - 20, cH - 10, 5,
              fill=T["warn_dim"], outline=T["warn"], tags="bypass_btn")
        cv.create_text(W // 2, cH - 30, text="⚠ Bypass OBD (Testing)",
                       font=self.F["ui_md"], fill=T["warn"], anchor="center", tags="bypass_btn")
        cv.tag_bind("bypass_btn", "<Button-1>", lambda e: self._on_bypass())

        # Instructions
        cv.create_text(W // 2, cH - 70,
                       text="Connect ELM327 Bluetooth adapter and select device",
                       font=self.F["ui_xs"], fill=T["text3"], anchor="center")