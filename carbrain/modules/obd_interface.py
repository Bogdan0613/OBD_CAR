import time
import math
import random
import threading
import subprocess
import platform
import os

from modules.config import POLL_MS


# ══════════════════════════════════════════════════════════════════════════════
# SIMULATOR
# ══════════════════════════════════════════════════════════════════════════════
class OBDSim:
    """Realistic OBD simulator.  Thread-safe.  Starts background thread."""

    def __init__(self):
        self._rpm     = 1600.0
        self._cool    = 32.0        # starts cold, warms up
        self._inst    = 7.8
        self._load    = 42.0
        self._thr     = 18.0
        self._speed   = 62.0
        self._map     = 55.0        # manifold absolute pressure (kPa)
        self._intake  = 25.0        # intake air temperature (°C)
        self._voltage = 13.8        # battery voltage
        self._km      = 0.0
        self._fuel    = 0.0
        self._last    = time.time()
        self._lock    = threading.Lock()
        self._running = True
        threading.Thread(target=self._run, daemon=True).start()

    def _run(self):
        while self._running:
            now = time.time()
            dt_h = (now - self._last) / 3600.0
            self._last = now

            with self._lock:
                # Speed follows a gentle sine + noise pattern
                self._speed = max(
                    0,
                    min(140, 65 + 30 * math.sin(now / 60.0) + random.gauss(0, 8)),
                )
                self._rpm = max(
                    750,
                    min(5500, 800 + self._speed * 28 + random.gauss(0, 80)),
                )
                # Coolant warms to operating temp (87 °C) then hovers
                target_cool = 87.0 if self._cool > 60 else 90.0
                self._cool = min(
                    115,
                    self._cool
                    + (target_cool - self._cool) * 0.002
                    + random.uniform(0.0, 0.4),
                )
                self._inst = max(
                    3.2,
                    min(25.0, self._inst + random.gauss(0, 0.35)),
                )
                self._load = max(
                    8.0, min(98.0, self._load + random.gauss(0, 2.5))
                )
                self._thr = max(
                    4.0, min(92.0, self._thr + random.gauss(0, 2.0))
                )
                self._map = max(
                    20.0, min(105.0, self._map + random.gauss(0, 1.5))
                )
                self._intake = max(
                    15.0, min(60.0, self._intake + random.gauss(0, 0.3))
                )
                self._voltage = max(
                    12.0, min(14.8, self._voltage + random.gauss(0, 0.05))
                )
                dk = self._speed * dt_h
                self._km   += dk
                self._fuel += dk * self._inst / 100.0

            time.sleep(POLL_MS / 1000.0)

    @property
    def data(self):
        with self._lock:
            km   = self._km
            fuel = self._fuel
            avg  = (fuel / km * 100) if km > 0.001 else self._inst
            cool = self._cool
            state = (
                "COLD" if cool < 60
                else ("WARM" if cool < 90 else "HOT")
            )
            return {
                "rpm":     round(self._rpm),
                "cool":    round(cool, 1),
                "state":   state,
                "inst":    round(self._inst, 2),
                "avg":     round(avg, 2),
                "load":    round(self._load, 1),
                "throttle":round(self._thr, 1),
                "speed":   round(self._speed, 1),
                "map":     round(self._map, 1),
                "intake":  round(self._intake, 1),
                "voltage": round(self._voltage, 2),
                "km":      round(km, 3),
                "fuel":    round(fuel, 3),
            }

    def reset(self):
        with self._lock:
            self._km   = 0.0
            self._fuel = 0.0

    def stop(self):
        self._running = False


# ══════════════════════════════════════════════════════════════════════════════
# BYPASS MODE  (Testing without real OBD)
# ══════════════════════════════════════════════════════════════════════════════
class OBDBypass:
    """Testing mode that returns all zeros (no recordings)."""

    def __init__(self):
        self.is_connected = True

    @property
    def data(self):
        """Return all zeros for bypass mode."""
        return {
            "rpm": 0,
            "cool": 0,
            "state": "COLD",
            "inst": 0,
            "avg": 0,
            "load": 0,
            "throttle": 0,
            "speed": 0,
            "map": 0,
            "intake": 0,
            "voltage": 0,
            "km": 0,
            "fuel": 0,
        }

    def reset(self):
        pass

    def stop(self):
        pass

    def get_fault_codes(self):
        return []

    def clear_fault_codes(self):
        pass


# ══════════════════════════════════════════════════════════════════════════════
# REAL OBD  (ELM327 / python-obd)
# ══════════════════════════════════════════════════════════════════════════════
class OBDReal:
    """
    Live ELM327 connector for Mazda 3 2008 1.6 BK.
    Requires: pip install obd

    Since Mazda 3 2008 doesn't provide odometer readings,
    kilometers are calculated from speed over time.

    Usage:
        obd = OBDReal()  # Deferred connection
        obd.connect(port="/dev/rfcomm0")  # OR auto-discover
    """

    def __init__(self):
        self._obd = None
        self._km = 0.0
        self._fuel = 0.0
        self._last = time.time()
        self._lock = threading.Lock()
        self._cache = {}
        self._running = False
        self._poll_thread = None
        self.is_connected = False

    def connect(self, port="/dev/rfcomm0"):
        """Attempt to connect to OBD device."""
        try:
            import obd
            self._obd = obd.OBD(port, baudrate=38400, timeout=30)
            print(f"OBD connection status: {self._obd.status()}")
            self.is_connected = True
            if not self._running:
                self._running = True
                self._poll_thread = threading.Thread(target=self._poll, daemon=True)
                self._poll_thread.start()
            return True
        except ImportError:
            raise RuntimeError("python-obd not installed. Run: pip install obd")
        except Exception as e:
            print(f"Failed to connect to OBD: {e}")
            self.is_connected = False
            return False


    def _q(self, cmd_name):
        """Query OBD command with error handling."""
        import obd
        try:
            cmd = getattr(obd.commands, cmd_name, None)
            if cmd is None:
                return None
            r = self._obd.query(cmd)
            if r.is_null():
                return None
            return r.value
        except Exception as e:
            print(f"OBD query error for {cmd_name}: {e}")
            return None

    def _poll(self):
        import obd
        while self._running:
            now = time.time()
            dt_s = (now - self._last)
            dt_h = dt_s / 3600.0
            self._last = now

            rpm = self._q("RPM")
            cool = self._q("COOLANT_TEMP")
            load = self._q("ENGINE_LOAD")
            thr = self._q("THROTTLE_POS")
            speed = self._q("SPEED")
            maf = self._q("MAF")
            map_ = self._q("INTAKE_PRESSURE")
            intake = self._q("INTAKE_TEMP")
            voltage = self._q("CONTROL_MODULE_VOLTAGE")

            inst = 0.0
            # if OBD provides a direct fuel economy value prefer it, otherwise calculate
            obd_avg = None
            for avg_cmd in ("FUEL_ECONOMY", "MPG", "FUEL_CONSUMPTION_RATE", "EFFICIENCY"):
                try:
                    v = self._q(avg_cmd)
                except Exception:
                    v = None
                if v is not None:
                    # some commands return L/100km, others mpg etc; we assume L/100km
                    try:
                        obd_avg = float(v.magnitude)
                        break
                    except Exception:
                        pass

            if maf:
                try:
                    maf_gs = maf.magnitude
                    if speed and hasattr(speed, "magnitude") and speed.magnitude > 1:
                        fc_lh = (maf_gs * 3600) / (14.7 * 755)
                        spd_kmh = speed.magnitude
                        inst = (fc_lh / spd_kmh) * 100
                    else:
                        inst = (maf_gs * 3.6) / (14.7 * 0.755)
                except (AttributeError, TypeError):
                    inst = 0.0
            else:
                if rpm and load:
                    try:
                        base_rate = (rpm.magnitude / 1000.0) * 0.5 * (load.magnitude / 100.0)
                        if speed and hasattr(speed, "magnitude") and speed.magnitude > 1:
                            inst = (base_rate / speed.magnitude) * 100
                        else:
                            inst = base_rate
                    except (AttributeError, TypeError):
                        inst = 0.0

            # if we got an obd average use it (override our computed value)
            if obd_avg is not None:
                inst = obd_avg

            spd_val = 0
            if speed and hasattr(speed, "magnitude"):
                try:
                    spd_val = speed.magnitude
                    if hasattr(speed, "units"):
                        try:
                            units_str = str(speed.units).lower()
                            if "meter" in units_str and "second" in units_str:
                                spd_val *= 3.6
                        except Exception:
                            pass
                except (AttributeError, TypeError):
                    spd_val = 0

            dk = spd_val * dt_h
            df = dk * inst / 100.0

            with self._lock:
                self._km += dk
                self._fuel += df
                self._cache = {
                    "rpm": int(rpm.magnitude) if rpm else 0,
                    "cool": round(cool.magnitude, 1) if cool else 0.0,
                    "load": round(load.magnitude, 1) if load else 0.0,
                    "throttle": round(thr.magnitude, 1) if thr else 0.0,
                    "speed": round(spd_val, 1),
                    "inst": round(max(inst, 0), 2),
                    "avg_obd": round(obd_avg, 2) if obd_avg is not None else None,
                    "map": round(map_.magnitude, 1) if map_ else 0.0,
                    "intake": round(intake.magnitude, 1) if intake else 0.0,
                    "voltage": round(voltage.magnitude, 2) if voltage else 0.0,
                }

            time.sleep(POLL_MS / 1000.0)

    @property
    def data(self):
        if not self.is_connected or self._obd is None:
            return {
                "rpm": 0, "cool": 0, "load": 0, "throttle": 0,
                "speed": 0, "inst": 0, "avg": 0, "state": "COLD",
                "map": 0, "intake": 0, "voltage": 0,
                "km": 0, "fuel": 0,
            }
        with self._lock:
            km = self._km
            fuel = self._fuel
            # prefer average coming from OBD if present
            avg = self._cache.get("avg_obd")
            if avg is None:
                avg = (fuel / km * 100) if km > 0.001 else self._cache.get("inst", 0)
            cool = self._cache.get("cool", 0)
            state = ("COLD" if cool < 60 else ("WARM" if cool < 90 else "HOT"))
            return {
                **self._cache,
                "avg": round(avg, 2) if avg is not None else None,
                "state": state,
                "km": round(km, 3),
                "fuel": round(fuel, 3),
            }

    @staticmethod
    def discover_devices():
        """Scan for Bluetooth devices (cross-platform: macOS and Linux)."""
        devices = []
        system = platform.system()

        try:
            if system == "Darwin":  # macOS
                devices.extend(OBDReal._scan_macos())
            elif system == "Linux":  # Linux/Raspberry Pi
                devices.extend(OBDReal._scan_linux())
            else:
                print(f"[WARN] Bluetooth scan not supported on {system}")
        except Exception as e:
            print(f"[WARN] Bluetooth scan failed: {e}")

        return devices

    @staticmethod
    def _scan_linux():
        """Scan using hcitool (Linux/Raspberry Pi)."""
        devices = []
        try:
            result = subprocess.run(["hcitool", "scan"], capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')[1:]  # Skip header
                for line in lines:
                    parts = line.strip().split('\t')
                    if len(parts) >= 2:
                        mac = parts[0].strip()
                        name = parts[1].strip() if len(parts) > 1 else "Unknown"
                        if mac and name:
                            devices.append((mac, name))
        except FileNotFoundError:
            print("[WARN] hcitool not found. Run: sudo apt-get install bluez")
        except subprocess.TimeoutExpired:
            print("[WARN] hcitool scan timeout")
        except Exception as e:
            print(f"[WARN] Linux scan error: {e}")
        return devices

    @staticmethod
    def _scan_macos():
        """Scan using macOS system_profiler."""
        devices = []
        try:
            result = subprocess.run(
                ["system_profiler", "SPBluetoothDataType"],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                lines = result.stdout.split('\n')
                current_device = None

                for line in lines:
                    stripped = line.strip()

                    # Device names end with ':' and have moderate indentation
                    if stripped.endswith(':') and 'Address' not in stripped and 'Bluetooth' not in stripped:
                        indent = len(line) - len(line.lstrip())
                        if 8 <= indent <= 16:
                            current_device = stripped.rstrip(':')

                    # Address line - starts with "Address:" after stripping
                    if stripped.startswith('Address:'):
                        try:
                            mac = line.split('Address:')[1].strip()
                            parts = mac.split(':')
                            if len(parts) == 6:
                                devices.append((mac, current_device or "Bluetooth Device"))
                                current_device = None
                        except Exception:
                            pass

        except FileNotFoundError:
            print("[WARN] system_profiler not found")
        except subprocess.TimeoutExpired:
            print("[WARN] system_profiler timeout")
        except Exception as e:
            print(f"[WARN] macOS scan error: {e}")

        return devices

    def reset(self):
        with self._lock:
            self._km = 0.0
            self._fuel = 0.0

    def stop(self):
        self._running = False

    def get_fault_codes(self):
        """Return list of (code, description) tuples."""
        if not self.is_connected or self._obd is None:
            return []
        import obd
        try:
            r = self._obd.query(obd.commands.GET_DTC)
            if r.is_null():
                return []
            return [(str(c[0]), str(c[1])) for c in r.value]
        except Exception as e:
            print(f"Error reading fault codes: {e}")
            return []

    def clear_fault_codes(self):
        """Clear diagnostic trouble codes."""
        if not self.is_connected or self._obd is None:
            return
        import obd
        try:
            self._obd.query(obd.commands.CLEAR_DTC)
            print("Fault codes cleared")
        except Exception as e:
            print(f"Error clearing fault codes: {e}")