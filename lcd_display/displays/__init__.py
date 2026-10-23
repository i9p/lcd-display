"""Built-in displays. Importing this package registers them."""

from .vu_meter import VUMeterDisplay
from .niri_window import NiriWindowDisplay

# Registry of all available displays (name → class)
DISPLAYS: dict[str, type] = {
    VUMeterDisplay.name: VUMeterDisplay,
    NiriWindowDisplay.name: NiriWindowDisplay,
}

__all__ = ["DISPLAYS", "VUMeterDisplay", "NiriWindowDisplay"]