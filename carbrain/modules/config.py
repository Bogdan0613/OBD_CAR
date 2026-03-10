import os

# ── Screen geometry ────────────────────────────────────────────────────────
W, H     = 480, 320
NAV_H    = 38
TOP_H    = 28

# ── Timing ─────────────────────────────────────────────────────────────────
POLL_MS  = 2000          # screen refresh interval (ms)
LOG_S    = 60            # telemetry snapshot interval (seconds)

# ── Paths ──────────────────────────────────────────────────────────────────
DB_PATH  = os.path.join(os.path.dirname(__file__), "..", "carbrain.db")

# ── Fonts ──────────────────────────────────────────────────────────────────
FONT_FAMILY = "Courier New"

# ── Themes ─────────────────────────────────────────────────────────────────
THEMES = {
    "night": {
        "bg":         "#08090C",
        "bg2":        "#0E1420",
        "bg3":        "#141E2E",
        "surface":    "#1A2840",
        "border":     "#1E3050",
        "border_hi":  "#2A4570",
        "acc":        "#E8A020",
        "acc_dim":    "#6B4800",
        "acc2":       "#2ECFAA",
        "acc2_dim":   "#0A4030",
        "acc3":       "#38B4FF",
        "acc3_dim":   "#083050",
        "danger":     "#FF4060",
        "danger_dim": "#500010",
        "text":       "#EDF2FF",
        "text2":      "#6A8AAA",
        "text3":      "#2A4060",
        "cold":       "#38B4FF",
        "warm":       "#2ECFAA",
        "hot":        "#FF4060",
        "nav_active": "#E8A020",
        "nav_bg":     "#0A1018",
    },
    "day": {
        "bg":         "#A0B0C0",
        "bg2":        "#8A9BB0",
        "bg3":        "#7A8BA0",
        "surface":    "#FFFFFF",
        "border":     "#6A7B90",
        "border_hi":  "#506080",
        "acc":        "#B06000",
        "acc_dim":    "#F0D090",
        "acc2":       "#007860",
        "acc2_dim":   "#B0E8D8",
        "acc3":       "#005090",
        "acc3_dim":   "#B0D0F0",
        "danger":     "#C00020",
        "danger_dim": "#F0C0C8",
        "text":       "#101828",
        "text2":      "#2A3A50",
        "text3":      "#4A5A70",
        "cold":       "#005090",
        "warm":       "#007860",
        "hot":        "#C00020",
        "nav_active": "#B06000",
        "nav_bg":     "#8A9BB0",
    },
}

# ── Mock OBD fault codes ───────────────────────────────────────────────────
MOCK_ERRORS = [
    ("P0171", "System Too Lean — Bank 1",                    "warn"),
    ("P0300", "Random / Multiple Cylinder Misfire Detected", "error"),
    ("P0420", "Catalyst System Efficiency Below Threshold",  "warn"),
    ("P0455", "Evaporative Emission System Leak (Large)",    "warn"),
    ("P0128", "Coolant Thermostat (Coolant Temp Below Reg)", "warn"),
]