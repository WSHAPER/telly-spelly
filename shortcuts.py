"""Global keyboard shortcuts using evdev for Wayland/Linux support."""
from __future__ import annotations
from typing import List, Set, Optional
from PyQt6.QtCore import QObject, QThread, pyqtSlot
from PyQt6.QtCore import pyqtSignal as Signal
import logging
import select

logger = logging.getLogger(__name__)

# Key codes from evdev - defined here to avoid import issues
KEY_LEFTCTRL = 29
KEY_RIGHTCTRL = 97
KEY_LEFTALT = 56
KEY_RIGHTALT = 100
KEY_LEFTSHIFT = 42
KEY_RIGHTSHIFT = 54
KEY_LEFTMETA = 125
KEY_RIGHTMETA = 126
EV_KEY = 1

# Letter key codes (A=30, B=48, etc.)
KEY_LETTERS = {
    'a': 30, 'b': 48, 'c': 46, 'd': 32, 'e': 18, 'f': 33, 'g': 34, 'h': 35,
    'i': 23, 'j': 36, 'k': 37, 'l': 38, 'm': 50, 'n': 49, 'o': 24, 'p': 25,
    'q': 16, 'r': 19, 's': 31, 't': 20, 'u': 22, 'v': 47, 'w': 17, 'x': 45,
    'y': 21, 'z': 44
}


class KeyboardListener(QThread):
    """Thread to listen for keyboard events using evdev."""
    
    key_combo_pressed: Signal = Signal(str)
    
    def __init__(self, start_combo: str, stop_combo: str) -> None:
        super().__init__()
        self.start_combo = start_combo
        self.stop_combo = stop_combo
        self._running = True
        self._pressed_keys: Set[int] = set()
        self.start_groups: List[Set[int]] = []
        self.stop_groups: List[Set[int]] = []
        
    def run(self) -> None:
        try:
            import evdev
            
            devices = [evdev.InputDevice(path) for path in evdev.list_devices()]
            keyboards = [d for d in devices if EV_KEY in d.capabilities()]
            
            if not keyboards:
                logger.error("No keyboard devices found")
                return
            
            logger.info(f"Monitoring {len(keyboards)} keyboard device(s)")
            
            # Parse combos into modifier groups
            self.start_groups = _parse_combo(self.start_combo)
            self.stop_groups = _parse_combo(self.stop_combo)
            
            logger.info(f"Start combo groups: {self.start_groups}")
            logger.info(f"Stop combo groups: {self.stop_groups}")
            
            while self._running:
                r, _, _ = select.select(keyboards, [], [], 0.1)
                for dev in r:
                    try:
                        for event in dev.read():
                            if event.type == EV_KEY:
                                self._handle_key_event(event.code, event.value)
                    except OSError:
                        # Device disconnected or read error
                        pass
                        
        except ImportError as err:
            logger.error(f"evdev not available: {err}")
        except PermissionError as err:
            logger.error(f"Permission denied accessing input devices: {err}")
        except OSError as err:
            logger.error(f"Keyboard listener error: {err}")
    
    def _handle_key_event(self, code: int, value: int) -> None:
        """Handle a key event (1=press, 0=release, 2=repeat)."""
        if value == 1:  # Press
            self._pressed_keys.add(code)
            self._check_combos()
        elif value == 0:  # Release
            self._pressed_keys.discard(code)
    
    def _check_combos(self) -> None:
        """Check if any combo is currently pressed."""
        if _combo_matches(self.start_groups, self._pressed_keys):
            logger.info("Start combo detected!")
            self.key_combo_pressed.emit("start")
        elif _combo_matches(self.stop_groups, self._pressed_keys):
            logger.info("Stop combo detected!")
            self.key_combo_pressed.emit("stop")
    
    def stop(self) -> None:
        """Stop the listener thread."""
        self._running = False


def _parse_combo(combo_str: str) -> List[Set[int]]:
    """Parse a combo string to a list of key code groups.
    
    Each group is a set of equivalent keys (e.g., left ctrl OR right ctrl).
    Returns a list of groups - all groups must have at least one key pressed.
    """
    groups: List[Set[int]] = []
    parts = combo_str.lower().replace(' ', '').split('+')
    
    for part in parts:
        if part in ('ctrl', 'control'):
            groups.append({KEY_LEFTCTRL, KEY_RIGHTCTRL})
        elif part == 'alt':
            groups.append({KEY_LEFTALT, KEY_RIGHTALT})
        elif part == 'shift':
            groups.append({KEY_LEFTSHIFT, KEY_RIGHTSHIFT})
        elif part in ('super', 'meta', 'win'):
            groups.append({KEY_LEFTMETA, KEY_RIGHTMETA})
        elif len(part) == 1 and part in KEY_LETTERS:
            groups.append({KEY_LETTERS[part]})
    
    return groups


def _combo_matches(groups: List[Set[int]], pressed_keys: Set[int]) -> bool:
    """Check if combo matches - need at least one key from each group pressed."""
    if not groups:
        return False
    for group in groups:
        if not any(code in pressed_keys for code in group):
            return False
    return True


class GlobalShortcuts(QObject):
    """Manager for global keyboard shortcuts."""
    
    start_recording_triggered: Signal = Signal()
    stop_recording_triggered: Signal = Signal()
    
    def __init__(self) -> None:
        super().__init__()
        self._listener: Optional[KeyboardListener] = None
        
    def setup_shortcuts(self, start_key: str = 'ctrl+alt+r', stop_key: str = 'ctrl+alt+s') -> bool:
        """Setup global keyboard shortcuts using evdev."""
        try:
            self.remove_shortcuts()
            
            self._listener = KeyboardListener(start_key, stop_key)
            self._listener.key_combo_pressed.connect(self._on_combo)
            self._listener.start()
            
            logger.info(f"Global shortcuts registered - Start: {start_key}, Stop: {stop_key}")
            return True
            
        except RuntimeError as err:
            logger.error(f"Failed to register global shortcuts: {err}")
            return False
    
    @pyqtSlot(str)
    def _on_combo(self, combo_name: str) -> None:
        """Handle combo press from listener thread."""
        if combo_name == "start":
            logger.info("Start recording shortcut triggered")
            self.start_recording_triggered.emit()
        elif combo_name == "stop":
            logger.info("Stop recording shortcut triggered")
            self.stop_recording_triggered.emit()
    
    def remove_shortcuts(self) -> None:
        """Remove existing shortcuts."""
        if self._listener:
            self._listener.stop()
            self._listener.wait(1000)
            self._listener = None
        
    def __del__(self) -> None:
        self.remove_shortcuts()
