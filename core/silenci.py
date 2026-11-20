"""Silencia els altaveus mentre es dicta (Mac i PC).

La música de YouTube o Spotify CONTINUA sonant, però muda: així el micròfon
no la capta. En deixar de dictar, el so torna tal com estava.
"""

import atexit
import subprocess
import threading

from config import IS_MAC, IS_WINDOWS

_lock = threading.Lock()
_hem_silenciat = False


# --- Mac -----------------------------------------------------------------
def _osa(script: str) -> str:
    try:
        r = subprocess.run(["osascript", "-e", script],
                           capture_output=True, text=True, timeout=3)
        return r.stdout.strip()
    except Exception:
        return ""


# --- PC ------------------------------------------------------------------
# La tecla multimèdia «silenci» de Windows: un toc silencia, un altre ho
# torna. Com que la premem exactament dues vegades (en començar i en acabar),
# el so sempre queda com estava.
_VK_VOLUME_MUTE = 0xAD


def _tecla_silenci_windows() -> bool:
    try:
        import ctypes
        user32 = ctypes.windll.user32
        user32.keybd_event(_VK_VOLUME_MUTE, 0, 0, 0)
        user32.keybd_event(_VK_VOLUME_MUTE, 0, 2, 0)  # 2 = tecla amunt
        return True
    except Exception:
        return False


# -------------------------------------------------------------------------
def _silencia():
    global _hem_silenciat
    with _lock:
        if _hem_silenciat:
            return
        if IS_MAC:
            if _osa("output muted of (get volume settings)") == "false":
                _osa("set volume with output muted")
                _hem_silenciat = True
        elif IS_WINDOWS:
            _hem_silenciat = _tecla_silenci_windows()


def _restaura():
    global _hem_silenciat
    with _lock:
        if not _hem_silenciat:
            return
        if IS_MAC:
            _osa("set volume without output muted")
        elif IS_WINDOWS:
            _tecla_silenci_windows()
        _hem_silenciat = False


def silencia():
    """En començar a dictar. Va en segon pla perquè no es perdi cap paraula."""
    threading.Thread(target=_silencia, daemon=True).start()


def restaura():
    """En acabar de dictar."""
    threading.Thread(target=_restaura, daemon=True).start()


# Si el programa es tanca enmig d'un dictat, que el so no quedi apagat.
atexit.register(_restaura)
