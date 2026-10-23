"""VU-meter display using the default PipeWire / PulseAudio source."""

from __future__ import annotations

import time
from typing import Optional

import numpy as np
import sounddevice as sd

from ..display import Display
from ..lcd import LCD


class VUMeterDisplay(Display):
    name = "vu"
    description = "Microphone VU meter (dBFS + bar)"
    update_interval = 1/10 #Hz

    MIN_DB = -60.0
    MAX_DB = 0.0
    BAR_WIDTH = 16
    SEGMENTS = 5
    SAMPLE_RATE = 48000
    BLOCKSIZE = 1024
    CHANNELS = 1

    def __init__(self) -> None:
        self._stream: Optional[sd.InputStream] = None
        self._last_db: float = -100.0

    def on_activate(self) -> None:
        if self._stream is not None:
            return
        self._stream = sd.InputStream(
            samplerate=self.SAMPLE_RATE,
            blocksize=self.BLOCKSIZE,
            channels=self.CHANNELS,
            dtype="float32",
            latency="low",
        )
        self._stream.start()

    def on_deactivate(self) -> None:
        if self._stream is not None:
            try:
                self._stream.stop()
                self._stream.close()
            except Exception:
                pass
            self._stream = None

    def _read_db(self) -> float:
        if self._stream is None:
            return -100.0
        try:
            data, overflowed = self._stream.read(self.BLOCKSIZE)
            if overflowed:
                pass  # could log
            rms = np.sqrt(np.mean(data ** 2))
            db = 20.0 * np.log10(rms + 1e-12)
            # simple one-pole smoother
            self._last_db = 0.6 * self._last_db + 0.4 * db
            return self._last_db
        except Exception:
            return self._last_db

    @staticmethod
    def _db_to_bar(db: float) -> bytes:
        level = float(np.clip(db, VUMeterDisplay.MIN_DB, VUMeterDisplay.MAX_DB))
        total = int(round(
            (level - VUMeterDisplay.MIN_DB)
            / (VUMeterDisplay.MAX_DB - VUMeterDisplay.MIN_DB)
            * (VUMeterDisplay.BAR_WIDTH * VUMeterDisplay.SEGMENTS)
        ))
        bar = bytearray()
        for i in range(VUMeterDisplay.BAR_WIDTH):
            segs = max(0, min(VUMeterDisplay.SEGMENTS, total - i * VUMeterDisplay.SEGMENTS))
            bar.append(0x20 if segs == 0 else segs)
        return bytes(bar)

    @staticmethod
    def _format_line1(db: float) -> str:
        if db < -99.0:
            return "MIC  -inf dBFS"
        return f"MIC {db:5.1f} dBFS"

    def update(self, lcd: LCD) -> None:
        db = self._read_db()
        lcd.write_both(self._format_line1(db), self._db_to_bar(db))
