"""Low-level serial driver for the 16x2 character LCD protocol."""

from __future__ import annotations

import time
from typing import Optional

import serial


class LCD:
    """Talks the simple byte protocol expected by the D1 Mini firmware."""

    CMD_CLEAR = 0x11
    CMD_HOME = 0x12
    CMD_LINE2 = 0x13

    def __init__(self, port: str = "/dev/ttyUSB0", baud: int = 115200, timeout: float = 0.1):
        self.port = port
        self.baud = baud
        self._ser: Optional[serial.Serial] = None
        self._timeout = timeout

    def open(self) -> None:
        if self._ser is not None and self._ser.is_open:
            return
        self._ser = serial.Serial(self.port, self.baud, timeout=self._timeout)
        time.sleep(0.05)  # let the MCU settle

    def close(self) -> None:
        if self._ser is not None:
            try:
                self.clear()
                self.write_line("LCD offline", 0)
                self.write_line("", 1)
            except Exception:
                pass
            self._ser.close()
            self._ser = None

    def _write(self, data: bytes | bytearray | list[int]) -> None:
        if self._ser is None or not self._ser.is_open:
            raise RuntimeError("LCD serial port is not open")
        if isinstance(data, list):
            data = bytes(data)
        self._ser.write(data)
        self._ser.flush()

    def clear(self) -> None:
        self._write([self.CMD_CLEAR])
        time.sleep(0.002)

    def home(self) -> None:
        self._write([self.CMD_HOME])

    def line2(self) -> None:
        self._write([self.CMD_LINE2])

    def write_raw(self, data: bytes | bytearray) -> None:
        """Write raw bytes (characters or bar glyphs 0x01-0x05)."""
        self._write(data)

    def write_line(self, text: str, line: int = 0) -> None:
        """Write a string to line 0 or 1, truncated/padded to 16 chars."""
        text = (text or "")[:16].ljust(16)
        if line == 0:
            self.home()
        else:
            self.line2()
        self._write(text.encode("ascii", errors="replace"))

    def write_both(self, line0: str, line1: str | bytes) -> None:
        """Convenience: update both lines in one go."""
        self.write_line(line0, 0)
        if isinstance(line1, str):
            self.write_line(line1, 1)
        else:
            self.line2()
            self.write_raw(line1)
        time.sleep(0.012)  # give the MCU + I2C bus breathing room

    def __enter__(self) -> "LCD":
        self.open()
        return self

    def __exit__(self, *args) -> None:
        self.close()