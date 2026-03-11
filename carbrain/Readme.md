# 🚗 CarBrain — Modular OBD Dashboard for Raspberry Pi 5

Futuristic 480×320 touchscreen dashboard.
Tracks fuel usage, trip stats, monthly costs, fault codes.
Day & Night themes. Pure Python / tkinter — no extra pip packages in sim mode.

---

## File Structure

```
carbrain/
├── carbrain.py              ← Entry point — run this
└── modules/
    ├── __init__.py
    ├── config.py            ← Constants, screen size, theme colours
    ├── db.py                ← SQLite persistence (trips, telemetry, archive)
    ├── obd_interface.py     ← OBDSim (default) + OBDReal (ELM327)
    ├── draw.py              ← Canvas primitives (rrect, arc_gauge, segbar …)
    ├── trip.py              ← Trip lifecycle controller (start/end/continue)
    ├── widgets.py           ← TopBar, NavBar
    ├── modals.py            ← NewTripModal, ConfirmModal, PriceAdjustModal
    ├── screen_home.py       ← Live HUD (RPM, coolant, fuel, load…)
    ├── screen_history.py    ← Recent trips + CONT / DEL buttons
    ├── screen_weekly.py     ← 7-day summary + daily bar chart
    ├── screen_monthly.py    ← Monthly KPI grid + archive
    └── screen_errors.py     ← OBD fault codes display
```

---

## Install & Run

This is a pure‑Python/Tkinter app that runs out of the box on a
**Raspberry Pi 5** with a 3.5" (480×320) touchscreen. Just make sure
Python 3 and Tkinter are installed; no other dependencies are needed unless
you enable the real OBD interface.

```bash
# Tkinter (usually pre-installed on Pi OS)
sudo apt-get install python3-tk

# Run (simulator mode — no hardware needed)
cd carbrain
python3 carbrain.py
```

### Kiosk / autostart on Pi

Uncomment in `carbrain.py`:
```python
self.overrideredirect(True)   # hides title bar
```

Add to `/etc/xdg/lxsession/LXDE-pi/autostart`:
```
@python3 /home/pi/carbrain/carbrain.py
```

---

## Real OBD-II (ELM327 Bluetooth)

```bash
pip install obd
# Pair your scanner:
bluetoothctl
  > scan on
  > pair <MAC>
  > trust <MAC>
  > connect <MAC>
# Creates /dev/rfcomm0
```

In `carbrain.py`, set:
```python
USE_REAL_OBD = True
OBD_PORT     = "/dev/rfcomm0"   # or None for auto-detect
```

---

## Screens

| # | Screen   | Description |
|---|----------|-------------|
| 1 | Home     | Live RPM arc gauge, coolant state, instant/avg L/100km, load, throttle, speed, battery voltage |
| 2 | New Trip | Fuel price modal → starts trip with odometer reset |
| 3 | History  | Last 8 trips. **CONT** resumes any trip as a linked segment. **✕** deletes. |
| 4 | Weekly   | 7-day bar chart + aggregate stats + per-trip rows |
| 5 | Monthly  | 6-cell KPI grid (trips, km, fuel, cost, avg/trip, avg km). Archive old months. |
| 6 | Errors   | OBD fault codes with severity badges. CLEAR DTC button. |

---

## Extending

### Custom OBD PIDs
Edit `OBDReal._poll()` in `modules/obd_interface.py`.

### Add a new screen
1. Create `modules/screen_foo.py` with a class `FooScreen(canvas, T, F)`.
2. Add canvas + instantiate in `CarBrain._build()` in `carbrain.py`.
3. Add a tab entry to `NavBar.TABS` in `modules/widgets.py`.
4. Handle the tab id in `CarBrain._on_nav()` and `_redraw_screen()`.

### Change theme colours
Edit `THEMES` dict in `modules/config.py`.

---

## Database

SQLite at `~/carbrain.db`.

| Table          | Contents |
|----------------|----------|
| `trips`        | One row per completed (or interim) trip |
| `telemetry`    | Compact JSON snapshots every 60 s during active trips |
| `month_archive`| Aggregated summary per past calendar month |
| `cfg`          | Key/value settings (theme, fuel_price) |

k