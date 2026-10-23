"""Display manager – owns the LCD and the currently active display."""

from __future__ import annotations

import signal
import time
from typing import Optional

from .display import Display
from .lcd import LCD
from .displays import DISPLAYS


class DisplayManager:
    def __init__(
        self,
        port: str = "/dev/ttyUSB0",
        baud: int = 115200,
        initial: str = "vu",
    ):
        self.lcd = LCD(port=port, baud=baud)
        self._current: Optional[Display] = None
        self._running = False
        self._switch_to: Optional[str] = None

        if initial not in DISPLAYS:
            raise ValueError(f"Unknown display '{initial}'. Available: {list(DISPLAYS)}")
        self._initial_name = initial

    @property
    def current_name(self) -> str:
        return self._current.name if self._current else ""

    def list_displays(self) -> dict[str, str]:
        return {name: cls.description for name, cls in DISPLAYS.items()}

    def switch(self, name: str) -> None:
        """Request a switch (thread-safe-ish; applied on next loop iteration)."""
        if name not in DISPLAYS:
            raise ValueError(f"Unknown display '{name}'")
        self._switch_to = name

    def _do_switch(self, name: str) -> None:
        if self._current is not None:
            try:
                self._current.on_deactivate()
            except Exception as e:
                print(f"[manager] deinit error: {e}")
            self._current = None

        cls = DISPLAYS[name]
        disp = cls()
        try:
            disp.on_activate()
        except Exception as e:
            print(f"[manager] init error for {name}: {e}")
            # still set it so the user sees the error on screen
        self._current = disp
        self._switch_to = None
        print(f"[manager] switched to '{name}'")

    def _cycle(self) -> None:
        names = list(DISPLAYS.keys())
        if not names:
            return
        try:
            idx = names.index(self.current_name)
            next_name = names[(idx + 1) % len(names)]
        except ValueError:
            next_name = names[0]
        self.switch(next_name)

    def run(self) -> None:
        self.lcd.open()
        self._do_switch(self._initial_name)
        self._running = True

        # SIGUSR1 cycles displays – convenient for keybinds / systemd
        def _sigusr1_handler(signum, frame):
            self._cycle()

        signal.signal(signal.SIGUSR1, _sigusr1_handler)

        try:
            while self._running:
                if self._switch_to is not None:
                    self._do_switch(self._switch_to)

                if self._current is not None:
                    try:
                        self._current.update(self.lcd)
                    except Exception as e:
                        print(f"[manager] update error: {e}")
                        self.lcd.write_both("Display error", str(e)[:16])

                    interval = getattr(self._current, "update_interval", 0.5)
                else:
                    interval = 1.0

                time.sleep(interval)
        except KeyboardInterrupt:
            print("\n[manager] shutting down")
        finally:
            if self._current is not None:
                try:
                    self._current.on_deactivate()
                except Exception:
                    pass
            self.lcd.close()
            self._running = False

    def stop(self) -> None:
        self._running = False