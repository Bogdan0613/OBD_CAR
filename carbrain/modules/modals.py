import tkinter as tk
from modules.config import W, H
from modules.draw import rrect


# ── internal helpers (don't need F passed in everywhere) ──────────────────

def _overlay(cv, T, title, sub, F):
    """Dim the screen and draw the modal card."""
    # Solid dark overlay (stipple = visual dimming without transparency)
    cv.create_rectangle(0, 0, W, H, fill=T["bg"], stipple="gray50", outline="")
    # Card
    rrect(cv, 16, 24, W - 16, H - 24, 8, fill=T["bg2"],
          outline=T["border_hi"], width=2)
    # Card header strip
    rrect(cv, 16, 24, W - 16, 70, 8, fill=T["bg3"],
          outline=T["border_hi"], width=1)
    cv.create_line(16, 70, W - 16, 70, fill=T["border_hi"])
    cv.create_text(32, 47, text=title, font=F["hud_lg"],
                   fill=T["acc"], anchor="w")
    cv.create_text(32, 63, text=sub, font=F["ui_xs"],
                   fill=T["text3"], anchor="w")


def _btn(cv, T, F, x1, y1, x2, y2, txt, style, tag):
    """Draw a touchable button. style: ghost | accent | green | danger."""
    colours = {
        "ghost":  (T["bg3"],        T["border_hi"], T["text2"]),
        "accent": (T["acc_dim"],    T["acc"],       T["acc"]),
        "green":  (T["acc2_dim"],   T["acc2"],      T["acc2"]),
        "danger": (T["danger_dim"], T["danger"],    T["danger"]),
    }
    bg, brd, fg = colours.get(style, colours["ghost"])
    rrect(cv, x1, y1, x2, y2, 6, fill=bg, outline=brd, width=1, tags=tag)
    cv.create_text((x1 + x2) // 2, (y1 + y2) // 2,
                   text=txt, font=F["hud_sm"], fill=fg,
                   anchor="center", tags=tag)


# ══════════════════════════════════════════════════════════════════════════════
class NewTripModal:
    """
    Full-screen modal for starting a new trip.

    Layout
    ──────
    Header  : NEW TRIP / subtitle
    Section : recent trips list with CONTINUE buttons (last 5)
    Section : fuel price ±0.01 adjuster
    Footer  : CANCEL  |  START NEW TRIP
    """

    def __init__(self, parent, T, F, fuel_price, last_trips,
                 on_start,      # callback(price: float)
                 on_continue,   # callback(trip_id: int, price: float)
                 on_cancel):    # callback()
        self.T  = T
        self.F  = F
        self._fp        = fuel_price
        self._trips     = last_trips          # list of trip dicts (max 5)
        self._on_start  = on_start
        self._on_cont   = on_continue
        self._on_cancel = on_cancel
        self._alive     = True

        # Use real bg colour — critical on Pi (no compositor)
        self.cv = tk.Canvas(parent, width=W, height=H,
                            bg=T["bg"], highlightthickness=0)
        self.cv.place(x=0, y=0, width=W, height=H)
        self._draw()

    # ── draw ──────────────────────────────────────────────────────────────
    def _draw(self):
        cv = self.cv
        cv.delete("all")
        T, F = self.T, self.F

        _overlay(cv, T, "NEW TRIP", "Adjust fuel price · or continue a saved trip", F)

        # ── Fuel price row ─────────────────────────────────────────────
        # Large − button (left third)
        _btn(cv, T, F, 18, 76, 118, 136, "−", "danger", "bd")
        # Price display (centre)
        rrect(cv, 122, 76, W - 122, 136, 5,
              fill=T["bg3"], outline=T["acc"], width=2)
        cv.create_text(W // 2, 100,
                       text=f"{self._fp:.2f}",
                       font=F["hud_xl"], fill=T["acc"],
                       anchor="center", tags="pd")
        cv.create_text(W // 2, 122,
                       text="€ / litre", font=F["ui_xs"],
                       fill=T["text3"], anchor="center")
        # Large + button (right third)
        _btn(cv, T, F, W - 118, 76, W - 18, 136, "+", "green", "bi")

        cv.tag_bind("bd", "<Button-1>", lambda e: self._adj(-0.01))
        cv.tag_bind("bi", "<Button-1>", lambda e: self._adj(+0.01))

        # ── Recent trips — CONTINUE ────────────────────────────────────
        if self._trips:
            cv.create_text(20, 146, text="CONTINUE A PREVIOUS TRIP:",
                           font=F["lbl"], fill=T["text3"], anchor="w")
            ROW_H = 30
            for i, t in enumerate(self._trips[:4]):
                ry = 158 + i * ROW_H
                seg = " +" if t.get("parent_id") else ""
                label = f"{t['date'][5:]}{seg}  {t['km']:.1f}km  {t['avg_l100']:.1f}L/100"
                # row background
                rrect(cv, 18, ry, W - 18, ry + ROW_H - 3, 4,
                      fill=T["bg3"], outline=T["border"])
                cv.create_text(26, ry + (ROW_H - 3) // 2,
                               text=label, font=F["ui_sm"],
                               fill=T["text2"], anchor="w")
                tag = f"ct{t['id']}"
                # CONT button on right
                _btn(cv, T, F, W - 86, ry + 2, W - 20, ry + ROW_H - 5,
                     "CONT ▶", "accent", tag)
                cv.tag_bind(tag, "<Button-1>",
                            lambda e, tid=t["id"]: self._continue(tid))

        # ── Footer buttons ─────────────────────────────────────────────
        _btn(cv, T, F, 18,    H - 54, 150,    H - 20, "✕  CANCEL",     "ghost", "bc")
        _btn(cv, T, F, 156,   H - 54, W - 18, H - 20, "▶  START NEW",  "green", "bs")

        cv.tag_bind("bc", "<Button-1>", lambda e: self._cancel())
        cv.tag_bind("bs", "<Button-1>", lambda e: self._start())

    # ── price adjuster ────────────────────────────────────────────────────
    def _adj(self, delta):
        if not self._alive:
            return
        self._fp = max(0.30, min(9.99, round(self._fp + delta, 2)))
        try:
            self.cv.itemconfig("pd", text=f"{self._fp:.2f}")
        except Exception:
            pass

    # ── actions ───────────────────────────────────────────────────────────
    def _start(self):
        if not self._alive:
            return
        fp = self._fp
        self._destroy_safe()
        self._on_start(fp)

    def _continue(self, trip_id):
        if not self._alive:
            return
        fp = self._fp
        self._destroy_safe()
        self._on_cont(trip_id, fp)

    def _cancel(self):
        if not self._alive:
            return
        self._destroy_safe()
        self._on_cancel()

    def _destroy_safe(self):
        self._alive = False
        try:
            self.cv.destroy()
        except Exception:
            pass

    # public alias so carbrain.py can call modal.destroy()
    def destroy(self):
        self._destroy_safe()


# ══════════════════════════════════════════════════════════════════════════════
class ConfirmModal:
    """Generic yes/no confirmation overlay."""

    def __init__(self, parent, T, F, title, body,
                 on_yes, on_no,
                 yes_label="CONFIRM", no_label="CANCEL",
                 style="danger"):
        self.T       = T
        self.F       = F
        self._on_yes = on_yes
        self._on_no  = on_no
        self._alive  = True

        self.cv = tk.Canvas(parent, width=W, height=H,
                            bg=T["bg"], highlightthickness=0)
        self.cv.place(x=0, y=0, width=W, height=H)

        _overlay(self.cv, T, title, body, F)
        _btn(self.cv, T, F, 18,   H - 54, 150,    H - 20,
             f"✕  {no_label}", "ghost", "cn")
        _btn(self.cv, T, F, 156,  H - 54, W - 18, H - 20,
             f"✓  {yes_label}", style, "cy")

        self.cv.tag_bind("cn", "<Button-1>", lambda e: self._no())
        self.cv.tag_bind("cy", "<Button-1>", lambda e: self._yes())

    def _yes(self):
        if not self._alive: return
        self._destroy_safe(); self._on_yes()

    def _no(self):
        if not self._alive: return
        self._destroy_safe(); self._on_no()

    def _destroy_safe(self):
        self._alive = False
        try: self.cv.destroy()
        except Exception: pass

    def destroy(self):
        self._destroy_safe()


# ══════════════════════════════════════════════════════════════════════════════
class PriceAdjustModal:
    """Adjust fuel price mid-trip without resetting odometer."""

    def __init__(self, parent, T, F, fuel_price, on_save, on_cancel):
        self.T          = T
        self.F          = F
        self._fp        = fuel_price
        self._on_save   = on_save
        self._on_cancel = on_cancel
        self._alive     = True

        self.cv = tk.Canvas(parent, width=W, height=H,
                            bg=T["bg"], highlightthickness=0)
        self.cv.place(x=0, y=0, width=W, height=H)
        self._draw()

    def _draw(self):
        cv = self.cv
        cv.delete("all")
        T, F = self.T, self.F

        _overlay(cv, T, "FUEL PRICE", "Adjust mid-trip — odometer not reset", F)

        _btn(cv, T, F, 18,     84, 118, 144, "−", "danger", "bd")
        rrect(cv, 122, 84, W - 122, 144, 5,
              fill=T["bg3"], outline=T["acc"], width=2)
        cv.create_text(W // 2, 108, text=f"{self._fp:.2f}",
                       font=F["hud_xl"], fill=T["acc"],
                       anchor="center", tags="pd")
        cv.create_text(W // 2, 130, text="€ / litre",
                       font=F["ui_xs"], fill=T["text3"], anchor="center")
        _btn(cv, T, F, W - 118, 84, W - 18, 144, "+", "green", "bi")

        _btn(cv, T, F, 18,  H - 54, 150,    H - 20, "✕  CANCEL", "ghost",  "bc")
        _btn(cv, T, F, 156, H - 54, W - 18, H - 20, "💾  SAVE",  "accent", "bs")

        cv.tag_bind("bd", "<Button-1>", lambda e: self._adj(-0.01))
        cv.tag_bind("bi", "<Button-1>", lambda e: self._adj(+0.01))
        cv.tag_bind("bc", "<Button-1>", lambda e: self._cancel())
        cv.tag_bind("bs", "<Button-1>", lambda e: self._save())

    def _adj(self, delta):
        if not self._alive: return
        self._fp = max(0.30, min(9.99, round(self._fp + delta, 2)))
        try: self.cv.itemconfig("pd", text=f"{self._fp:.2f}")
        except Exception: pass

    def _save(self):
        if not self._alive: return
        fp = self._fp
        self._destroy_safe(); self._on_save(fp)

    def _cancel(self):
        if not self._alive: return
        self._destroy_safe(); self._on_cancel()

    def _destroy_safe(self):
        self._alive = False
        try: self.cv.destroy()
        except Exception: pass

    def destroy(self):
        self._destroy_safe()