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
        self._device_scroll = 0  # Scroll offset for device list
        self._scan_start_time = None  # Track when scan started

        # Button regions for click detection
        self._scan_btn_rect = None
        self._bypass_btn_rect = None
        self._back_btn_rect = None
        self._device_rects = {}  # device_idx -> (x1, y1, x2, y2)

        # Bind canvas click events
        self.cv.bind("<Button-1>", self._on_canvas_click)
        self.cv.bind("<Button-4>", self._on_scroll_up)  # Mouse wheel up
        self.cv.bind("<Button-5>", self._on_scroll_down)  # Mouse wheel down

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
        self._device_scroll = 0
        self._scan_start_time = time.time()
        self.draw()  # Show scanning state immediately
        self._animate_scan()  # Start animation loop

        def scan():
            try:
                # Use OBDReal's static method for device discovery
                from modules.obd_interface import OBDReal
                print("[CONNECTION] Starting Bluetooth scan...")
                discovered = OBDReal.discover_devices()
                print(f"[CONNECTION] Scan complete. Found {len(discovered)} devices")
                # Prepend new devices (newest at top)
                self._devices = discovered + self._devices
            except Exception as ex:
                print(f"[WARN] Bluetooth scan failed: {ex}")
            finally:
                self._scanning = False
                self._scan_start_time = None
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

    def reset_to_device_list(self):
        """Reset connection state but keep device list (go back to device selection)."""
        self._connection_status = None
        self._connecting = False
        self.draw()

    def show_not_obd_message(self):
        """Show 'Not an OBD' message for 2 seconds, then return to device list."""
        self._connection_status = "not_obd"
        self.draw()
        self.cv.after(2000, self.reset_to_device_list)

    def _on_canvas_click(self, event):
        """Handle canvas clicks by checking coordinates."""
        x, y = event.x, event.y

        # Check scan button
        if self._scan_btn_rect:
            x1, y1, x2, y2 = self._scan_btn_rect
            if x1 <= x <= x2 and y1 <= y <= y2:
                if self._scanning:
                    # Cancel scan
                    print("[CONNECTION] Scan cancelled by user")
                    self._scanning = False
                    self._scan_start_time = None
                    self.draw()
                else:
                    # Start scan
                    self._scan_devices()
                return

        # Check device buttons
        for device_idx, (x1, y1, x2, y2) in self._device_rects.items():
            if x1 <= x <= x2 and y1 <= y <= y2:
                mac, name = self._devices[device_idx]
                self._connect_device(mac, name)
                return

        # Check back button
        if self._back_btn_rect:
            x1, y1, x2, y2 = self._back_btn_rect
            if x1 <= x <= x2 and y1 <= y <= y2:
                self._connection_status = None
                self._devices = []
                self._device_scroll = 0
                self._scanning = False
                self.draw()
                return

        # Check bypass button
        if self._bypass_btn_rect:
            x1, y1, x2, y2 = self._bypass_btn_rect
            if x1 <= x <= x2 and y1 <= y <= y2:
                self._on_bypass()
                return

    def _on_scroll_up(self, event):
        """Scroll device list up."""
        if self._device_scroll > 0:
            self._device_scroll -= 1
            self.draw()

    def _on_scroll_down(self, event):
        """Scroll device list down."""
        if self._device_scroll < len(self._devices) - 5:
            self._device_scroll += 1
            self.draw()

    def _animate_scan(self):
        """Animate scanning dots every 300ms."""
        if self._scanning:
            self.draw()
            self.cv.after(300, self._animate_scan)

    def draw(self):
        cv = self.cv
        cv.delete("all")
        T = self.T
        cH = H - TOP_H - NAV_H

        # Reset button regions
        self._scan_btn_rect = None
        self._bypass_btn_rect = None
        self._back_btn_rect = None
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

        # Not an OBD state
        if self._connection_status == "not_obd":
            cv.create_text(W // 2, cH // 2,
                           text="❌ Not an OBD", font=self.F["hud_md"], fill=T["danger"], anchor="center")
            return

        # Failed state
        if self._connection_status == "failed":
            cv.create_text(W // 2, cH // 2 - 15,
                           text="❌ Failed", font=self.F["hud_md"], fill=T["danger"], anchor="center")
            cv.create_text(W // 2, cH // 2 + 5,
                           text="Tap SCAN", font=self.F["ui_md"], fill=T["text3"], anchor="center")

        # Scan button - shows SCAN or CANCEL
        y = 30
        scan_color = T["acc2_dim"] if self._scanning else T["acc_dim"]
        cv.create_rectangle(8, y, W - 8, y + 35,
                           fill=scan_color, outline=T["acc"], width=2)
        scan_text = "CANCEL" if self._scanning else "SCAN"
        cv.create_text(W // 2, y + 17, text=scan_text,
                       font=self.F["hud_md"], fill=T["acc"], anchor="center")
        self._scan_btn_rect = (8, y, W - 8, y + 35)

        # Device list area
        y += 40
        list_start = y
        list_end = cH - 38  # Space for buttons at bottom

        # Draw device list with scroll offset (show 5 visible items max)
        visible_count = 0
        for i in range(self._device_scroll, len(self._devices)):
            if visible_count >= 5 or y > list_end:
                break

            mac, name = self._devices[i]
            cv.create_rectangle(8, y, W - 8, y + 32,
                               fill=T["bg3"], outline=T["acc2"], width=1)
            cv.create_text(12, y + 7, text=name, font=self.F["hud_sm"], fill=T["text"],
                           anchor="nw")
            cv.create_text(12, y + 20, text=mac, font=self.F["ui_xs"], fill=T["text2"],
                           anchor="nw")
            self._device_rects[i] = (8, y, W - 8, y + 32)  # Store actual device index
            y += 33
            visible_count += 1

        # Scroll indicators
        if self._device_scroll > 0:
            cv.create_text(W - 12, list_start + 5, text="↑",
                           font=self.F["hud_sm"], fill=T["acc2"], anchor="ne")
        if self._device_scroll + 5 < len(self._devices):
            cv.create_text(W - 12, list_end - 5, text="↓",
                           font=self.F["hud_sm"], fill=T["acc2"], anchor="se")

        # Show hint if list is empty and not scanning
        if not self._devices and not self._scanning:
            hint_y = (list_start + list_end) // 2
            cv.create_text(W // 2, hint_y,
                           text="Tap SCAN to search",
                           font=self.F["ui_md"], fill=T["text2"], anchor="center")

        # Show scanning with animated dots
        if self._scanning:
            hint_y = (list_start + list_end) // 2 - 20

            # Animated dots based on time
            if self._scan_start_time:
                elapsed = time.time() - self._scan_start_time
                dot_count = int(elapsed) % 4
                dots = "." * (dot_count + 1)
            else:
                dots = "..."

            cv.create_text(W // 2, hint_y,
                           text=f"Scanning{dots}",
                           font=self.F["hud_md"], fill=T["acc2"], anchor="center")

            # Show time elapsed
            if self._scan_start_time:
                elapsed = int(time.time() - self._scan_start_time)
                cv.create_text(W // 2, hint_y + 25,
                               text=f"{elapsed}s (max 20s)",
                               font=self.F["ui_xs"], fill=T["text2"], anchor="center")

        # Show device count if scanning
        if self._scanning and self._devices:
            cv.create_text(W - 12, list_start + 5, text=f"{len(self._devices)} found",
                           font=self.F["ui_xs"], fill=T["acc2"], anchor="ne")

        # Bottom buttons: BACK (left) and BYPASS (right)
        btn_y = cH - 32
        mid = W // 2

        # BACK button (left)
        cv.create_rectangle(8, btn_y, mid - 4, cH - 2,
                           fill=T["bg2"], outline=T["text2"], width=1)
        cv.create_text(mid // 2, btn_y + 15, text="BACK",
                       font=self.F["hud_sm"], fill=T["text"], anchor="center")
        self._back_btn_rect = (8, btn_y, mid - 4, cH - 2)

        # BYPASS button (right)
        cv.create_rectangle(mid + 4, btn_y, W - 8, cH - 2,
                           fill=T["danger_dim"], outline=T["danger"], width=1)
        cv.create_text(mid + (W - mid) // 2, btn_y + 15, text="BYPASS",
                       font=self.F["hud_sm"], fill=T["danger"], anchor="center")
        self._bypass_btn_rect = (mid + 4, btn_y, W - 8, cH - 2)