# Creating a new LCD display

The system is built around small, self-contained **Display** classes.
Each display owns its own resources (audio streams, sockets, …) and is
activated / deactivated cleanly when the user switches screens.

## Minimal example

Create a new file under `lcd_display/displays/`, for example `clock.py`:

```python
from __future__ import annotations
from datetime import datetime

from ..display import Display
from ..lcd import LCD


class ClockDisplay(Display):
    name = "clock"                          # unique short id
    description = "Current time + date"
    update_interval = 1.0                   # seconds between update() calls

    def on_activate(self) -> None:
        """Called once when this display becomes active.
        Open streams, sockets, allocate buffers here."""
        pass

    def on_deactivate(self) -> None:
        """Called when switching away. Release everything you acquired."""
        pass

    def update(self, lcd: LCD) -> None:
        now = datetime.now()
        lcd.write_both(
            now.strftime("%H:%M:%S"),
            now.strftime("%Y-%m-%d"),
        )
```

Then register it in `lcd_display/displays/__init__.py`:

```python
from .clock import ClockDisplay

DISPLAYS: dict[str, type] = {
    # …
    ClockDisplay.name: ClockDisplay,
}
```

That’s it. The new display is immediately available:

```bash
python -m lcd_display --list
python -m lcd_display --display clock
```

## Lifecycle guarantees

| Method            | When it runs                          | Purpose                          |
|-------------------|---------------------------------------|----------------------------------|
| `on_activate()`   | Once, when the display is selected    | Start audio, open sockets, etc.  |
| `update(lcd)`     | Periodically while active             | Draw the current frame           |
| `on_deactivate()` | Once, when switching to another display or on shutdown | Clean up resources |

The manager always calls `on_deactivate()` before activating another display,
so you can safely hold exclusive resources (microphone stream, file locks, …).

## LCD helpers

```python
lcd.write_both("line 0 text", "line 1 text")   # most common
lcd.write_line("only first line", 0)
lcd.write_line("only second", 1)
lcd.write_raw(bytes([0x01, 0x02, 0x05, …]))    # bar glyphs / custom chars
lcd.clear()
```

Strings are automatically truncated / padded to 16 characters.
Non-ASCII is replaced.

## Switching displays at runtime

- **CLI**: `--display vu` / `--display niri`
- **Signal**: send `SIGUSR1` to the process to cycle to the next display  
  (handy for a Niri keybind: `niri msg action spawn -- kill -USR1 $(pidof lcd-display)`)
- **Programmatic**: if you embed the manager, call `manager.switch("niri")`

## Tips

- Keep `update()` fast (< 30 ms). Do heavy work in a background thread if needed.
- Always release exclusive resources in `on_deactivate()` so other displays can use them.
- Prefer `lcd.write_both()` – it already contains a short delay that keeps the
  D1 Mini + I2C bus happy.
- For debugging, the manager prints init / update exceptions to stderr and
  shows a short error message on the LCD itself.
