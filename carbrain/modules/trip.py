import time
from datetime import datetime, date

from modules.config import LOG_S


class TripController:
    """
    Manages the lifecycle of a single driving trip segment.

    State transitions:
        idle  ──start()──►  active  ──end()──►  idle
                  ▲                   │
                  └──continue(tid)────┘  (new segment linked to parent)
    """

    def __init__(self, db, obd):
        self._db  = db
        self._obd = obd

        self.active    = False
        self._start_ts = None
        self._parent   = None      # parent trip id (for CONT segments)
        self._db_id    = None      # interim DB row id
        self._last_log = 0.0
        self.fuel_price = 1.80

    # ── public API ─────────────────────────────────────────────────────────
    def start(self, fuel_price: float, parent_id=None):
        """Begin a new trip (or new segment from CONT)."""
        self.fuel_price = fuel_price
        self._db.put("fuel_price", fuel_price)
        self.active    = True
        self._start_ts = datetime.now().isoformat()
        self._parent   = parent_id
        self._db_id    = None
        self._last_log = 0.0
        self._obd.reset()

    def continue_from(self, trip_id: int):
        """Resume a saved trip as a linked child segment."""
        t = self._db.trip_by_id(trip_id)
        if not t:
            return False
        self.start(float(t["price"]), parent_id=trip_id)
        return True

    def end(self):
        """Finish the active trip, persist to DB. Returns saved trip dict or None."""
        if not self.active:
            return None

        d    = self._obd.data
        km   = d["km"]
        fuel = d["fuel"]
        avg  = (fuel / km * 100) if km > 0.001 else 0
        cost = fuel * self.fuel_price
        now  = datetime.now().isoformat()

        saved = None
        if km > 0.01:
            t_data = {
                "date":     date.today().isoformat(),
                "start_ts": self._start_ts,
                "end_ts":   now,
                "km":       km,
                "fuel":     fuel,
                "price":    self.fuel_price,
                "avg":      avg,
                "cost":     cost,
            }
            if self._db_id:
                t_data["id"] = self._db_id
            new_id = self._db.save_trip(t_data, parent_id=self._parent)
            saved  = self._db.trip_by_id(new_id)

        self.active    = False
        self._start_ts = None
        self._parent   = None
        self._db_id    = None
        self._obd.reset()
        return saved

    def tick(self):
        """
        Called every POLL_MS by the main loop.
        Logs telemetry snapshot every LOG_S seconds.
        """
        if not self.active:
            return
        now = time.time()
        if now - self._last_log < LOG_S:
            return
        self._last_log = now

        d = self._obd.data
        if d["km"] < 0.05:
            return   # not moving yet

        # Ensure DB row exists
        if self._db_id is None:
            avg = (d["fuel"] / d["km"] * 100) if d["km"] > 0.001 else 0
            self._db_id = self._db.save_trip(
                {
                    "date":     date.today().isoformat(),
                    "start_ts": self._start_ts,
                    "end_ts":   datetime.now().isoformat(),
                    "km":       d.get("km", 0),
                    "fuel":     d.get("fuel", 0),
                    "price":    self.fuel_price,
                    "avg":      avg,
                    "cost":     d.get("fuel", 0) * self.fuel_price,
                },
                parent_id=self._parent,
            )
        else:
            # Keep end_ts and running stats updated
            avg  = (d["fuel"] / d["km"] * 100) if d["km"] > 0.001 else 0
            cost = d["fuel"] * self.fuel_price
            self._db.save_trip(
                {
                    "id":     self._db_id,
                    "end_ts": datetime.now().isoformat(),
                    "km":     d.get("km", 0),
                    "fuel":   d.get("fuel", 0),
                    "price":  self.fuel_price,
                    "avg":    avg,
                    "cost":   d.get("fuel", 0) * self.fuel_price,
                }
            )

        # Compact snapshot
        self._db.log_snapshot(
            self._db_id,
            {
                "r": d["rpm"],
                "c": round(d["cool"], 0),
                "i": d["inst"],
                "l": d["load"],
                "s": d.get("speed", 0),
                "k": d["km"],
                "f": d["fuel"],
            },
        )

    def active_row_for_history(self) -> dict | None:
        """Return a display row dict for the history screen, or None."""
        if not self.active:
            return None
        d    = self._obd.data
        km   = d["km"]
        fuel = d["fuel"]
        avg  = (fuel / km * 100) if km > 0.001 else 0
        return {
            "id":     None,
            "lbl":    "NOW ●",
            "km":     km,
            "avg":    avg,
            "cost":   fuel * self.fuel_price,
            "fuel":   fuel,
            "active": True,
        }