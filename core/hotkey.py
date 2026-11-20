"""Tecles per dictar.

Dues maneres:
1. Mantenir premudes Ctrl + Alt de l'ESQUERRA: grava mentre les tens premudes.
2. Doble toc a Ctrl: mode mans lliures (un altre toc a Ctrl ho atura).

Al PC, la tecla AltGr (per escriure @, #, €...) envia per dins un Ctrl
«fantasma» + AltGr. Aquí s'ignora del tot perquè escriure una arrova no
engegui mai el dictat.
"""

import time
import threading
from pynput import keyboard
from PyQt6.QtCore import QObject, pyqtSignal
from config import DOUBLE_TAP_INTERVAL, IS_WINDOWS

_CTRL = (keyboard.Key.ctrl_l, keyboard.Key.ctrl_r)
if IS_WINDOWS:
    # Al PC només l'Alt de l'esquerra; AltGr / Alt dret NO compten.
    _ALT = (keyboard.Key.alt_l,)
    _ALTGR = (keyboard.Key.alt_gr, keyboard.Key.alt_r)
else:
    _ALT = (keyboard.Key.alt, keyboard.Key.alt_l, keyboard.Key.alt_r,
            keyboard.Key.alt_gr)
    _ALTGR = ()

# Mentre el programa mateix enganxa el text (Ctrl+V simulat), no s'ha
# d'interpretar com si l'usuari toqués Ctrl.
_ignora_fins = 0.0


def ignora_tecles(segons: float) -> None:
    global _ignora_fins
    _ignora_fins = time.time() + segons


class HotkeyListener(QObject):
    pressed = pyqtSignal()
    released = pyqtSignal()

    def __init__(self):
        super().__init__()
        self._lock = threading.Lock()
        self._ctrl_held = False
        self._alt_held = False
        self._recording = False
        self._hands_free = False
        self._listener: keyboard.Listener | None = None

        # Un «toc net» de Ctrl: prémer i deixar anar Ctrl sol, de pressa,
        # sense cap altra tecla pel mig (així Ctrl+Z, Ctrl+C... no compten).
        self._ctrl_down_at = 0.0
        self._net = False
        self._last_tap = 0.0

    def start(self):
        self._listener = keyboard.Listener(
            on_press=self._on_press,
            on_release=self._on_release,
        )
        self._listener.daemon = True
        self._listener.start()

    def stop(self):
        if self._listener:
            self._listener.stop()
            self._listener = None

    # ------------------------------------------------------------------
    def _toc_net(self):
        now = time.time()
        # Mans lliures en marxa: un toc ho atura
        if self._hands_free and self._recording:
            self._hands_free = False
            self._recording = False
            self._last_tap = 0.0
            self.released.emit()
            return
        if now - self._last_tap < DOUBLE_TAP_INTERVAL and not self._recording:
            self._last_tap = 0.0
            self._hands_free = True
            self._recording = True
            self.pressed.emit()
            return
        self._last_tap = now

    def _on_press(self, key):
        if time.time() < _ignora_fins:
            return
        with self._lock:
            if key in _CTRL:
                if not self._ctrl_held:          # no és una repetició
                    self._ctrl_held = True
                    self._ctrl_down_at = time.time()
                    self._net = True
            else:
                # Qualsevol altra tecla (AltGr inclosa) espatlla el toc net
                self._net = False
                if key in _ALTGR:
                    self._ctrl_held = False      # era el Ctrl fantasma d'AltGr
                    return
                if key in _ALT:
                    self._alt_held = True

            # Mode mantenir: Ctrl + Alt (esquerres) alhora
            if self._ctrl_held and self._alt_held and not self._recording:
                self._recording = True
                self._hands_free = False
                self.pressed.emit()

    def _on_release(self, key):
        if time.time() < _ignora_fins:
            return
        with self._lock:
            if key in _CTRL:
                if (self._ctrl_held and self._net
                        and time.time() - self._ctrl_down_at < DOUBLE_TAP_INTERVAL):
                    self._toc_net()
                self._ctrl_held = False
                self._net = False
            elif key in _ALT:
                self._alt_held = False

            # Mode mantenir: s'atura en deixar anar qualsevol de les dues
            if self._recording and not self._hands_free:
                if not (self._ctrl_held and self._alt_held):
                    self._recording = False
                    self.released.emit()
