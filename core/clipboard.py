"""Clipboard and paste operations — cross-platform (macOS + Windows)."""

import subprocess
import time
import sys
from config import IS_WINDOWS

_saved_app: str | None = None


def save_frontmost_app():
    """Save the currently focused application before recording starts."""
    global _saved_app
    if IS_WINDOWS:
        try:
            import win32gui
            hwnd = win32gui.GetForegroundWindow()
            if hwnd:
                _saved_app = str(hwnd)
        except Exception:
            pass
    else:
        try:
            result = subprocess.run(
                ["osascript", "-e",
                 'tell application "System Events" to get name of first process whose frontmost is true'],
                capture_output=True, text=True, timeout=2,
            )
            name = result.stdout.strip()
            if name and name != "SFlow":
                _saved_app = name
        except Exception:
            pass


def paste_text(text: str):
    """Copy text to clipboard and paste into the previously active app."""
    global _saved_app

    if IS_WINDOWS:
        _paste_windows(text)
    else:
        _paste_mac(text)

    _saved_app = None


def _paste_windows(text: str):
    """Windows: copy to clipboard and paste with Ctrl+V."""
    try:
        import win32clipboard
        win32clipboard.OpenClipboard()
        win32clipboard.EmptyClipboard()
        win32clipboard.SetClipboardText(text, win32clipboard.CF_UNICODETEXT)
        win32clipboard.CloseClipboard()
    except Exception:
        try:
            import pyperclip
            pyperclip.copy(text)
        except Exception:
            pass

    # Restore focus to saved window
    if _saved_app:
        try:
            import win32gui
            hwnd = int(_saved_app)
            win32gui.SetForegroundWindow(hwnd)
            time.sleep(0.12)
        except Exception:
            pass

    # Simulate Ctrl+V (el detector de tecles no l'ha de prendre per un toc)
    try:
        from core.hotkey import ignora_tecles
        ignora_tecles(0.5)
    except Exception:
        pass
    try:
        import win32api
        import win32con
        win32api.keybd_event(win32con.VK_CONTROL, 0, 0, 0)
        win32api.keybd_event(ord('V'), 0, 0, 0)
        time.sleep(0.05)
        win32api.keybd_event(ord('V'), 0, win32con.KEYEVENTF_KEYUP, 0)
        win32api.keybd_event(win32con.VK_CONTROL, 0, win32con.KEYEVENTF_KEYUP, 0)
    except Exception:
        try:
            import pyautogui
            pyautogui.hotkey('ctrl', 'v')
        except Exception:
            pass


def _paste_mac(text: str):
    """macOS: copy to clipboard and paste with Cmd+V."""
    try:
        from AppKit import NSPasteboard, NSPasteboardTypeString
        pb = NSPasteboard.generalPasteboard()
        pb.clearContents()
        pb.setString_forType_(text, NSPasteboardTypeString)
    except Exception:
        subprocess.run(["pbcopy"], input=text.encode("utf-8"), check=True)

    if _saved_app:
        try:
            subprocess.run(
                ["osascript", "-e", f'tell application "{_saved_app}" to activate'],
                check=True, timeout=2,
            )
            time.sleep(0.12)
        except Exception:
            pass

    subprocess.run(
        ["osascript", "-e", 'tell application "System Events" to keystroke "v" using command down'],
        check=True,
    )
