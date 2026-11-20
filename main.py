#!/usr/bin/env python3
"""DICTAR (basat en SFlow) - dicta amb la veu i el text apareix on tens el cursor."""

import os
import sys
import signal
import subprocess
import threading
import webbrowser
from PyQt6.QtWidgets import (
    QApplication, QSystemTrayIcon, QMenu,
    QDialog, QVBoxLayout, QLabel, QLineEdit, QPushButton, QMessageBox,
)
from PyQt6.QtCore import Qt, QObject, pyqtSignal, pyqtSlot, QLockFile
from PyQt6.QtGui import QIcon, QPixmap, QAction, QActionGroup, QCursor

from ui.pill_widget import PillWidget
from core.recorder import AudioRecorder
from core.transcriber import Transcriber
from core.hotkey import HotkeyListener
from core.clipboard import paste_text, save_frontmost_app
from core.postprocessor import TextPostprocessor
from core.corrector import corregeix
from core import idioma
from core import silenci
from db.database import TranscriptionDB
from web.server import start_web_server
from config import LOGO_PATH, APP_DATA_DIR, GROQ_API_KEY, IS_WINDOWS, IS_MAC


def _ensure_accessibility() -> bool:
    """Prompt macOS to grant Accessibility if not trusted. No-op on Windows."""
    if IS_WINDOWS:
        return True
    try:
        from ApplicationServices import AXIsProcessTrustedWithOptions
        return AXIsProcessTrustedWithOptions({"AXTrustedCheckOptionPrompt": True})
    except Exception:
        return True


# LaunchAgent constants
_LAUNCH_AGENT_LABEL = "so.saasfactory.sflow"
_PLIST_PATH = os.path.expanduser(f"~/Library/LaunchAgents/{_LAUNCH_AGENT_LABEL}.plist")


# ---------------------------------------------------------------------------
# First-run dialog
# ---------------------------------------------------------------------------
class FirstRunDialog(QDialog):
    """Shown when GROQ_API_KEY is missing on first launch."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("DICTAR - Primera vegada")
        self.setFixedWidth(460)

        layout = QVBoxLayout()
        benvinguda = QLabel(
            "<b>Benvingut a DICTAR!</b><br><br>"
            "Enganxa aquí la teva clau de Groq (comença per <b>gsk_</b>).<br>"
            "Només cal fer-ho aquesta primera vegada.")
        benvinguda.setWordWrap(True)
        layout.addWidget(benvinguda)

        link = QLabel('<a href="https://console.groq.com/keys">No en tens? Crea-la gratis aquí: console.groq.com/keys</a>')
        link.setOpenExternalLinks(True)
        layout.addWidget(link)

        self.key_input = QLineEdit()
        self.key_input.setPlaceholderText("gsk_...")
        self.key_input.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(self.key_input)

        save_btn = QPushButton("Desa i comença")
        save_btn.clicked.connect(self._save_key)
        layout.addWidget(save_btn)

        self.setLayout(layout)

    def _save_key(self):
        key = self.key_input.text().strip()
        if not key.startswith("gsk_") or len(key) < 20:
            QMessageBox.warning(self, "Revisa la clau",
                                "La clau ha de començar per gsk_ i ser llarga.\n"
                                "Torna-la a copiar i enganxar sencera.")
            return

        env_path = os.path.join(APP_DATA_DIR, ".env")
        os.makedirs(APP_DATA_DIR, exist_ok=True)
        with open(env_path, "w", encoding="utf-8") as f:
            f.write(f"GROQ_API_KEY={key}\n")

        # Set in current process so Transcriber picks it up
        os.environ["GROQ_API_KEY"] = key
        self.accept()


# ---------------------------------------------------------------------------
# Launch at Login
# ---------------------------------------------------------------------------
_RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"


def _exe_path() -> str:
    if getattr(sys, "frozen", False):
        return sys.executable
    return os.path.abspath(sys.argv[0])


def _is_launch_at_login() -> bool:
    if IS_WINDOWS:
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _RUN_KEY) as k:
                winreg.QueryValueEx(k, "DICTAR")
            return True
        except OSError:
            return False
    return os.path.exists(_PLIST_PATH)


def _set_launch_at_login(enabled: bool):
    if IS_WINDOWS:
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _RUN_KEY, 0,
                                winreg.KEY_SET_VALUE) as k:
                if enabled:
                    winreg.SetValueEx(k, "DICTAR", 0, winreg.REG_SZ, f'"{_exe_path()}"')
                else:
                    try:
                        winreg.DeleteValue(k, "DICTAR")
                    except OSError:
                        pass
        except OSError:
            pass
        return
    if enabled:
        if getattr(sys, "frozen", False):
            # In .app bundle: executable is Contents/MacOS/SFlow
            exe = sys.executable
        else:
            exe = os.path.abspath(sys.argv[0])

        plist = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>{_LAUNCH_AGENT_LABEL}</string>
    <key>ProgramArguments</key>
    <array>
        <string>{exe}</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <false/>
</dict>
</plist>"""
        os.makedirs(os.path.dirname(_PLIST_PATH), exist_ok=True)
        with open(_PLIST_PATH, "w") as f:
            f.write(plist)
        subprocess.run(["launchctl", "load", _PLIST_PATH], capture_output=True)
    else:
        if os.path.exists(_PLIST_PATH):
            subprocess.run(["launchctl", "unload", _PLIST_PATH], capture_output=True)
            os.remove(_PLIST_PATH)


# ---------------------------------------------------------------------------
# System tray
# ---------------------------------------------------------------------------
def _setup_tray(app: QApplication, port: int) -> QSystemTrayIcon:
    pixmap = QPixmap(LOGO_PATH)
    if pixmap.isNull():
        # Fallback: empty icon (shouldn't happen but don't crash)
        icon = QIcon()
    else:
        icon = QIcon(pixmap.scaled(22, 22, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))

    tray = QSystemTrayIcon(icon, app)

    menu = QMenu()

    status = QAction("DICTAR - en marxa", menu)
    status.setEnabled(False)
    menu.addAction(status)
    menu.addSeparator()

    # --- Idioma del dictat (es recorda en reiniciar) ---
    grup_idioma = QActionGroup(menu)
    grup_idioma.setExclusive(True)
    for codi, nom in (("ca", "Dicto en català"), ("es", "Dicto en castellano")):
        accio = QAction(nom, menu)
        accio.setCheckable(True)
        accio.setChecked(idioma.actual() == codi)
        accio.triggered.connect(lambda _=False, c=codi: (idioma.canvia(c), _actualitza_tooltip(tray)))
        grup_idioma.addAction(accio)
        menu.addAction(accio)
    menu.addSeparator()

    dashboard = QAction("Veure l'historial de dictats", menu)
    dashboard.triggered.connect(lambda: webbrowser.open(f"http://localhost:{port}"))
    menu.addAction(dashboard)
    menu.addSeparator()

    clau_action = QAction("Canvia la clau de Groq", menu)
    clau_action.triggered.connect(_canvia_clau)
    menu.addAction(clau_action)

    login_action = QAction("Engega DICTAR en obrir l'ordinador", menu)
    login_action.setCheckable(True)
    login_action.setChecked(_is_launch_at_login())
    login_action.toggled.connect(_set_launch_at_login)
    menu.addAction(login_action)
    menu.addSeparator()

    quit_action = QAction("Tanca DICTAR", menu)
    quit_action.triggered.connect(app.quit)
    menu.addAction(quit_action)

    tray.setContextMenu(menu)
    if IS_WINDOWS:
        # Al PC, també amb el clic normal (esquerre) s'obre el menú
        tray.activated.connect(
            lambda reason: menu.popup(QCursor.pos())
            if reason == QSystemTrayIcon.ActivationReason.Trigger else None)
    _actualitza_tooltip(tray)
    tray.show()
    tray._grup_idioma = grup_idioma  # cal mantenir-lo viu
    return tray


_app_dictar = None  # el controlador, per poder reiniciar la connexió amb Groq


def _canvia_clau():
    dialog = FirstRunDialog()
    if dialog.exec() == QDialog.DialogCode.Accepted and _app_dictar is not None:
        _app_dictar.transcriber._client = None  # farà servir la clau nova


def _actualitza_tooltip(tray: QSystemTrayIcon) -> None:
    nom = "català" if idioma.actual() == "ca" else "castellano"
    tray.setToolTip(f"DICTAR - dictat en {nom}")


# ---------------------------------------------------------------------------
# Main app controller
# ---------------------------------------------------------------------------
class SFlowApp(QObject):
    """Main application controller. Wires hotkey -> recorder -> transcriber -> clipboard."""

    transcription_done = pyqtSignal(str, float)
    transcription_error = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.recorder = AudioRecorder()
        self.transcriber = Transcriber()
        self.postprocessor = TextPostprocessor()
        self.db = TranscriptionDB()
        self.hotkey = HotkeyListener()
        self.pill = PillWidget()

        # Connect visualizer to recorder's audio queue
        self.pill.visualizer.set_audio_queue(self.recorder.audio_queue)

        # MUST use QueuedConnection: pynput emits from its own thread
        self.hotkey.pressed.connect(self._on_hotkey_pressed, Qt.ConnectionType.QueuedConnection)
        self.hotkey.released.connect(self._on_hotkey_released, Qt.ConnectionType.QueuedConnection)
        self.transcription_done.connect(self._on_transcription_done, Qt.ConnectionType.QueuedConnection)
        self.transcription_error.connect(self._on_transcription_error, Qt.ConnectionType.QueuedConnection)

    def start(self):
        self.hotkey.start()
        self.pill.show()
        self.pill.set_state(PillWidget.STATE_IDLE)

    def avisa(self, titol: str, text: str):
        """Missatge petit al costat del rellotge (si la icona ja existeix)."""
        tray = getattr(self, "tray", None)
        if tray is not None:
            tray.showMessage(titol, text, QSystemTrayIcon.MessageIcon.Warning, 10000)

    def _desfes_estat_tecles(self):
        self.hotkey._recording = False
        self.hotkey._hands_free = False

    @pyqtSlot()
    def _on_hotkey_pressed(self):
        save_frontmost_app()
        silenci.silencia()  # la música continua, però muda
        try:
            self.recorder.start()
        except Exception as e:
            print(f"Error del micròfon: {e}")
            silenci.restaura()
            self._desfes_estat_tecles()
            self.pill.set_state(PillWidget.STATE_ERROR)
            self.avisa("DICTAR no troba el micròfon",
                       "Comprova que el micròfon està connectat i que Windows "
                       "deixa fer-lo servir (Configuració > Privadesa > Micròfon).")
            return
        self.pill.set_state(PillWidget.STATE_RECORDING)

    @pyqtSlot()
    def _on_hotkey_released(self):
        if not self.recorder.is_recording:
            return
        duration = self.recorder.stop()
        silenci.restaura()  # torna el so tal com estava
        self.pill.set_state(PillWidget.STATE_PROCESSING)

        if duration < 0.3:
            self.pill.set_state(PillWidget.STATE_IDLE)
            return

        wav_buffer = self.recorder.get_wav_buffer()
        recording_duration = self.recorder.get_duration()
        thread = threading.Thread(
            target=self._transcribe_worker,
            args=(wav_buffer, recording_duration),
            daemon=True,
        )
        thread.start()

    def _transcribe_worker(self, wav_buffer, duration):
        try:
            text = self.transcriber.transcribe(wav_buffer)
            if text:
                # Neteja (crosses) i corrector de Softcatalà, fora del fil de la
                # interfície perquè la consulta per internet no la bloquegi.
                text = corregeix(self.postprocessor.process(text, idioma.actual()))
                self.transcription_done.emit(text, duration)
            else:
                self.transcription_error.emit("No speech detected")
        except Exception as e:
            self.transcription_error.emit(str(e))

    @pyqtSlot(str, float)
    def _on_transcription_done(self, text: str, duration: float):
        cleaned_text = text  # ja ve netejat i corregit del _transcribe_worker
        paste_text(cleaned_text)
        self.db.insert(text=cleaned_text, duration_seconds=duration)
        self.pill.set_state(PillWidget.STATE_DONE)

    @pyqtSlot(str)
    def _on_transcription_error(self, error: str):
        self.pill.set_state(PillWidget.STATE_ERROR)
        if error == "No speech detected":
            return
        print(f"Error en transcriure: {error}")
        e = error.lower()
        if "401" in e or "invalid_api_key" in e or "api key" in e or "not configured" in e:
            self.avisa("La clau de Groq no funciona",
                       "Clica la icona de DICTAR i tria «Canvia la clau de Groq».")
        elif "429" in e or "rate limit" in e:
            self.avisa("Massa dictats seguits",
                       "El servei gratuït de Groq demana una pausa. Torna-ho a provar d'aquí a un minut.")
        else:
            self.avisa("No s'ha pogut dictar",
                       "Comprova que tens internet i torna-ho a provar.")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def _prepara_registre():
    """Al programa instal·lat no hi ha finestra de text: els missatges
    tècnics van a «registre.txt» (útil si cal investigar un problema)."""
    if getattr(sys, "frozen", False):
        try:
            os.makedirs(APP_DATA_DIR, exist_ok=True)
            f = open(os.path.join(APP_DATA_DIR, "registre.txt"), "a",
                     encoding="utf-8", buffering=1)
            sys.stdout = f
            sys.stderr = f
        except OSError:
            pass


def _prova_rapida() -> int:
    """«DICTAR.exe --prova»: comprova que tot el programa es pot carregar.
    La fem servir en fabricar l'instal·lador, abans de donar-lo per bo."""
    import sounddevice, numpy, groq, flask, pynput  # noqa: F401
    from core import corrector, postprocessor  # noqa: F401
    assert os.path.exists(LOGO_PATH), "falta el logotip"
    if IS_WINDOWS:
        import win32clipboard, win32gui, win32api  # noqa: F401
    # Les finestres també s'han de poder crear
    app = QApplication(sys.argv)  # noqa: F841
    PillWidget()
    FirstRunDialog()
    HotkeyListener()
    print("PROVA OK")
    return 0


def main():
    _prepara_registre()
    if "--prova" in sys.argv:
        sys.exit(_prova_rapida())

    app = QApplication(sys.argv)

    # Un sol DICTAR alhora (si no, el text s'enganxaria dues vegades)
    os.makedirs(APP_DATA_DIR, exist_ok=True)
    bloqueig = QLockFile(os.path.join(APP_DATA_DIR, "dictar.lock"))
    bloqueig.setStaleLockTime(0)
    if not bloqueig.tryLock(100):
        QMessageBox.information(None, "DICTAR",
                                "DICTAR ja està en marxa.\n\n"
                                "Per dictar, prem dues vegades la tecla Ctrl.\n"
                                "El menú és a la icona de DICTAR, al costat del rellotge.")
        sys.exit(0)
    app.setApplicationName("DICTAR")
    app.setQuitOnLastWindowClosed(False)

    # Allow Ctrl+C to kill the app
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    # First-run: ask for API key if missing (BEFORE hiding from Dock so dialog is visible)
    api_key = os.getenv("GROQ_API_KEY", "")
    if not api_key:
        dialog = FirstRunDialog()
        if dialog.exec() != QDialog.DialogCode.Accepted:
            sys.exit(0)

    # Hide from Dock AFTER first-run dialog — menu bar only (macOS only)
    if IS_MAC:
        try:
            import AppKit
            AppKit.NSApp.setActivationPolicy_(AppKit.NSApplicationActivationPolicyAccessory)
        except Exception:
            pass

    # Start web dashboard
    port = start_web_server()

    # Request Accessibility permission (shows macOS prompt if not granted)
    _ensure_accessibility()

    # Start the app
    global _app_dictar
    sflow = SFlowApp()
    _app_dictar = sflow
    sflow.start()

    # System tray icon
    tray = _setup_tray(app, port)  # noqa: F841 — must keep reference alive
    sflow.tray = tray
    tray.showMessage("DICTAR està en marxa",
                     "Prem dues vegades Ctrl per dictar, i un cop més per acabar.",
                     QSystemTrayIcon.MessageIcon.Information, 8000)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
