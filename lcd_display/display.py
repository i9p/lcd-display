"""Base class for all LCD displays."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .lcd import LCD


class Display(ABC):
    """
    Abstract base for a "screen" that can be shown on the 16x2 LCD.

    Lifecycle:
      - on_activate()   called when this display becomes current
      - update(lcd)     called periodically while active
      - on_deactivate() called when switching away
    """

    # Unique short name used on the CLI and for switching
    name: str = "base"

    # Human-readable description
    description: str = ""

    # How often update() should be called (seconds)
    update_interval: float = 0.5

    def on_activate(self) -> None:
        """Allocate resources (audio streams, sockets, etc.)."""
        pass

    def on_deactivate(self) -> None:
        """Release resources acquired in on_activate()."""
        pass

    @abstractmethod
    def update(self, lcd: "LCD") -> None:
        """Draw the current state onto the LCD. Must be reasonably fast."""
        ...

    def __repr__(self) -> str:
        return f"<Display {self.name}>"