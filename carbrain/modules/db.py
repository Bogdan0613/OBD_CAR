import sqlite3
import threading
import json
from datetime import datetime, date, timedelta

from modules.config import DB_PATH


class DB:
    def __init__(self):
        self._lock = threading.Lock()
        self.cx = sqlite3.connect(DB_PATH, check_same_thread=False)
        self.cx.execute("PRAGMA journal_mode=WAL")
        self._migrate()

    # ── schema ─────────────────────────────────────────────────────────────
    def _migrate(self):
        self.cx.executescript("""
            CREATE TABLE IF NOT EXISTS trips(
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                date      TEXT NOT NULL,
                start_ts  TEXT NOT NULL,
                end_ts    TEXT NOT NULL,
                km        REAL NOT NULL DEFAULT 0,
                fuel      REAL NOT NULL DEFAULT 0,
                price     REAL NOT NULL DEFAULT 0,
                avg_l100  REAL NOT NULL DEFAULT 0,
                cost      REAL NOT NULL DEFAULT 0,
                parent_id INTEGER DEFAULT NULL,
                notes     TEXT DEFAULT NULL,
                hidden    INTEGER DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS telemetry(
                id       INTEGER PRIMARY KEY AUTOINCREMENT,
                trip_id  INTEGER NOT NULL,
                ts       TEXT NOT NULL,
                snapshot TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS month_archive(
                month TEXT PRIMARY KEY,
                data  TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS cfg(
                k TEXT PRIMARY KEY,
                v TEXT
            );
        """)
        # Add hidden column to existing trips table if it doesn't exist
        try:
            self.cx.execute("ALTER TABLE trips ADD COLUMN hidden INTEGER DEFAULT 0")
        except sqlite3.OperationalError:
            pass  # Column already exists
        self.cx.commit()

    # ── helpers ────────────────────────────────────────────────────────────
    def _row_to_dict(self, cursor, row):
        return dict(zip([d[0] for d in cursor.description], row))

    # ── cfg ────────────────────────────────────────────────────────────────
    def get(self, k, default=None):
        with self._lock:
            r = self.cx.execute("SELECT v FROM cfg WHERE k=?", (k,)).fetchone()
            return r[0] if r else default

    def put(self, k, v):
        with self._lock:
            self.cx.execute(
                "INSERT OR REPLACE INTO cfg(k,v) VALUES(?,?)", (k, str(v))
            )
            self.cx.commit()

    # ── trips ──────────────────────────────────────────────────────────────
    def save_trip(self, t, parent_id=None):
        """Insert or UPDATE a trip. Pass id in t to update existing row."""
        with self._lock:
            if t.get("id"):
                self.cx.execute(
                    """UPDATE trips
                       SET end_ts=?,km=?,fuel=?,price=?,avg_l100=?,cost=?,notes=?
                       WHERE id=?""",
                    (
                        t["end_ts"],
                        round(t.get("km", 0) or 0, 3),
                        round(t.get("fuel", 0) or 0, 3),
                        round(t.get("price", 0) or 0, 3),
                        round(t.get("avg", 0) or 0, 2),
                        round(t.get("cost", 0) or 0, 2),
                        t.get("notes"),
                        t["id"],
                    ),
                )
                self.cx.commit()
                return t["id"]
            else:
                c = self.cx.execute(
                    """INSERT INTO trips
                       (date,start_ts,end_ts,km,fuel,price,avg_l100,cost,parent_id,notes)
                       VALUES(?,?,?,?,?,?,?,?,?,?)""",
                    (
                        t["date"],
                        t["start_ts"],
                        t["end_ts"],
                        round(t.get("km", 0) or 0, 3),
                        round(t.get("fuel", 0) or 0, 3),
                        round(t.get("price", 0) or 0, 3),
                        round(t.get("avg", 0) or 0, 2),
                        round(t.get("cost", 0) or 0, 2),
                        parent_id,
                        t.get("notes"),
                    ),
                )
                self.cx.commit()
                return c.lastrowid

    def trip_by_id(self, tid):
        with self._lock:
            c = self.cx.execute("SELECT * FROM trips WHERE id=?", (tid,))
            row = c.fetchone()
            return self._row_to_dict(c, row) if row else None

    def hide_trip(self, trip_id: int):
        with self._lock:
            self.cx.execute("UPDATE trips SET hidden=1 WHERE id=?", (trip_id,))
            self.cx.commit()

    def show_trip(self, trip_id: int):
        with self._lock:
            self.cx.execute("UPDATE trips SET hidden=0 WHERE id=?", (trip_id,))
            self.cx.commit()

    def trips(self, limit=20, since_date=None, show_hidden=False):
        with self._lock:
            if since_date:
                if show_hidden:
                    query = "SELECT * FROM trips WHERE date>=?" + (" ORDER BY id DESC LIMIT ?" if limit else "")
                    params = (since_date, limit) if limit else (since_date,)
                else:
                    query = "SELECT * FROM trips WHERE date>=? AND hidden=0" + (" ORDER BY id DESC LIMIT ?" if limit else "")
                    params = (since_date, limit) if limit else (since_date,)
                c = self.cx.execute(query, params)
            else:
                if show_hidden:
                    query = "SELECT * FROM trips" + (" ORDER BY id DESC LIMIT ?" if limit else "")
                    params = (limit,) if limit else ()
                else:
                    query = "SELECT * FROM trips WHERE hidden=0" + (" ORDER BY id DESC LIMIT ?" if limit else "")
                    params = (limit,) if limit else ()
                c = self.cx.execute(query, params)
            rows = c.fetchall()
            return [self._row_to_dict(c, r) for r in rows]

    def monthly_summary(self, month_str=None):
        m = month_str or datetime.now().strftime("%Y-%m")
        with self._lock:
            r = self.cx.execute(
                "SELECT COUNT(*),SUM(km),SUM(fuel),SUM(cost),AVG(avg_l100)"
                " FROM trips WHERE date LIKE ? AND hidden=0",
                (f"{m}%",),
            ).fetchone()
        return {
            "n":       r[0] or 0,
            "km":      r[1] or 0.0,
            "fuel":    r[2] or 0.0,
            "cost":    r[3] or 0.0,
            "avg_l100":round(r[4] or 0.0, 2),
        }

    def weekly_summary(self):
        since = (date.today() - timedelta(days=6)).isoformat()
        with self._lock:
            r = self.cx.execute(
                "SELECT COUNT(*),SUM(km),SUM(fuel),SUM(cost)"
                " FROM trips WHERE date>=? AND hidden=0",
                (since,),
            ).fetchone()
            c = self.cx.execute(
                "SELECT * FROM trips WHERE date>=? AND hidden=0 ORDER BY id DESC LIMIT 20",
                (since,),
            )
            trip_rows = [self._row_to_dict(c, row) for row in c.fetchall()]
        return {
            "n":     r[0] or 0,
            "km":    r[1] or 0.0,
            "fuel":  r[2] or 0.0,
            "cost":  r[3] or 0.0,
            "trips": trip_rows,
        }

    def best_trip(self):
        """Return the trip with the lowest avg_l100 (most efficient)."""
        with self._lock:
            c = self.cx.execute(
                "SELECT * FROM trips WHERE km>1 AND hidden=0 ORDER BY avg_l100 ASC LIMIT 1"
            )
            row = c.fetchone()
            return self._row_to_dict(c, row) if row else None

    def total_stats(self):
        """Lifetime aggregates."""
        with self._lock:
            r = self.cx.execute(
                "SELECT COUNT(*),SUM(km),SUM(fuel),SUM(cost) FROM trips WHERE hidden=0"
            ).fetchone()
        return {
            "n":    r[0] or 0,
            "km":   r[1] or 0.0,
            "fuel": r[2] or 0.0,
            "cost": r[3] or 0.0,
        }

    # ── telemetry ──────────────────────────────────────────────────────────
    def log_snapshot(self, trip_id, snap):
        payload = json.dumps(snap, separators=(",", ":"))
        with self._lock:
            self.cx.execute(
                "INSERT INTO telemetry(trip_id,ts,snapshot) VALUES(?,?,?)",
                (trip_id, datetime.now().strftime("%H:%M"), payload),
            )
            self.cx.commit()

    def get_telemetry(self, trip_id):
        with self._lock:
            rows = self.cx.execute(
                "SELECT ts,snapshot FROM telemetry WHERE trip_id=? ORDER BY id",
                (trip_id,),
            ).fetchall()
        return [{"ts": r[0], **json.loads(r[1])} for r in rows]

    # ── archive & purge ────────────────────────────────────────────────────
    def archive_and_purge_old_months(self):
        """
        For each past month:
          1. Aggregate into month_archive (INSERT OR IGNORE — safe to re-run).
          2. Delete trips + telemetry for that month.
        Returns list of archived month strings.
        """
        current = datetime.now().strftime("%Y-%m")
        archived = []
        with self._lock:
            months = sorted(
                {
                    r[0][:7]
                    for r in self.cx.execute(
                        "SELECT date FROM trips"
                    ).fetchall()
                    if r[0][:7] < current
                }
            )
            for m in months:
                r = self.cx.execute(
                    """SELECT COUNT(*),SUM(km),SUM(fuel),SUM(cost),
                              MIN(date),MAX(date),AVG(avg_l100)
                       FROM trips WHERE date LIKE ?""",
                    (f"{m}%",),
                ).fetchone()
                summary = {
                    "month":    m,
                    "trips":    r[0] or 0,
                    "km":       round(r[1] or 0, 1),
                    "fuel":     round(r[2] or 0, 2),
                    "cost":     round(r[3] or 0, 2),
                    "first":    r[4] or m,
                    "last":     r[5] or m,
                    "avg_l100": round(r[6] or 0, 2),
                }
                self.cx.execute(
                    "INSERT OR IGNORE INTO month_archive(month,data) VALUES(?,?)",
                    (m, json.dumps(summary, separators=(",", ":"))),
                )
                ids = [
                    row[0]
                    for row in self.cx.execute(
                        "SELECT id FROM trips WHERE date LIKE ?", (f"{m}%",)
                    ).fetchall()
                ]
                if ids:
                    ph = ",".join("?" * len(ids))
                    self.cx.execute(
                        f"DELETE FROM telemetry WHERE trip_id IN ({ph})", ids
                    )
                    self.cx.execute(
                        f"DELETE FROM trips WHERE id IN ({ph})", ids
                    )
                archived.append(m)
            self.cx.commit()
        return archived

    def get_month_archive(self):
        with self._lock:
            rows = self.cx.execute(
                "SELECT month,data FROM month_archive ORDER BY month DESC"
            ).fetchall()
        return [{"month": r[0], **json.loads(r[1])} for r in rows]