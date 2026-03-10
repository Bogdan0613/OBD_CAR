import time
import math
import random
import threading

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
# REAL OBD  (ELM327 / python-obd)
# ══════════════════════════════════════════════════════════════════════════════
class OBDReal:
    """
    Live ELM327 connector.  Requires:  pip install obd

    Usage:
        from modules.obd_interface import OBDReal
        obd_source = OBDReal(port="/dev/rfcomm0")   # or leave port=None for auto
    """

    def __init__(self, port=None):
        try:
            import obd
            self._obd = obd.OBD(port)
        except ImportError:
            raise RuntimeError(
                "python-obd not installed.  Run: pip install obd"
            )

        self._km    = 0.0
        self._fuel  = 0.0
        self._last  = time.time()
        self._lock  = threading.Lock()
        self._cache = {}
        self._running = True
        threading.Thread(target=self._poll, daemon=True).start()

    def _q(self, cmd_name):
        import obd
        cmd = getattr(obd.commands, cmd_name, None)
        if cmd is None:
            return None
        r = self._obd.query(cmd)
        return r.value if not r.is_null() else None

    def _poll(self):
        import obd
        while self._running:
            now  = time.time()
            dt_h = (now - self._last) / 3600.0
            self._last = now

            rpm     = self._q("RPM")
            cool    = self._q("COOLANT_TEMP")
            load    = self._q("ENGINE_LOAD")
            thr     = self._q("THROTTLE_POS")
            speed   = self._q("SPEED")
            maf     = self._q("MAF")      # g/s
            map_    = self._q("INTAKE_PRESSURE")
            intake  = self._q("INTAKE_TEMP")
            voltage = self._q("CONTROL_MODULE_VOLTAGE")

            # Fuel consumption from MAF (stoich 14.7:1, density 0.755 kg/L)
            inst = 0.0
            if maf and speed and speed.magnitude > 2:
                maf_gs = maf.magnitude          # g/s
                fc_lh  = (maf_gs * 3600) / (14.7 * 755)   # L/h
                spd_kmh= speed.magnitude
                inst   = (fc_lh / spd_kmh) * 100           # L/100km
            elif maf:
                maf_gs = maf.magnitude
                inst   = (maf_gs * 3.6) / (14.7 * 0.755)  # rough L/h

            spd_val = speed.magnitude if speed else 0
            dk      = spd_val * dt_h
            df      = dk * inst / 100.0

            with self._lock:
                self._km   += dk
                self._fuel += df
                self._cache = {
                    "rpm":     int(rpm.magnitude)    if rpm     else 0,
                    "cool":    round(cool.magnitude, 1) if cool else 0.0,
                    "load":    round(load.magnitude, 1) if load else 0.0,
                    "throttle":round(thr.magnitude,  1) if thr  else 0.0,
                    "speed":   round(spd_val, 1),
                    "inst":    round(inst, 2),
                    "map":     round(map_.magnitude,  1) if map_   else 0.0,
                    "intake":  round(intake.magnitude,1) if intake else 0.0,
                    "voltage": round(voltage.magnitude,2) if voltage else 0.0,
                }

            time.sleep(POLL_MS / 1000.0)

    @property
    def data(self):
        with self._lock:
            km   = self._km
            fuel = self._fuel
            avg  = (fuel / km * 100) if km > 0.001 else self._cache.get("inst", 0)
            cool = self._cache.get("cool", 0)
            state = (
                "COLD" if cool < 60
                else ("WARM" if cool < 90 else "HOT")
            )
            return {
                **self._cache,
                "avg":   round(avg, 2),
                "state": state,
                "km":    round(km, 3),
                "fuel":  round(fuel, 3),
            }

    def reset(self):
        with self._lock:
            self._km   = 0.0
            self._fuel = 0.0

    def stop(self):
        self._running = False

    def get_fault_codes(self):
        """Return list of (code, description) tuples."""
        import obd
        r = self._obd.query(obd.commands.GET_DTC)
        if r.is_null():
            return []
        return [(str(c[0]), str(c[1])) for c in r.value]

    def clear_fault_codes(self):
        import obd
        self._obd.query(obd.commands.CLEAR_DTC)