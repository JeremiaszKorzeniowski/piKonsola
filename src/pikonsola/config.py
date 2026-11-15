from __future__ import annotations

import os
from dataclasses import dataclass


WIDTH = 128
HEIGHT = 128
FPS = 30


@dataclass
class Palette:
    background: tuple[int, int, int] = (9, 12, 18)
    panel: tuple[int, int, int] = (21, 28, 39)
    text: tuple[int, int, int] = (224, 239, 234)
    muted: tuple[int, int, int] = (110, 130, 140)
    accent: tuple[int, int, int] = (86, 232, 154)
    accent_dark: tuple[int, int, int] = (28, 112, 80)
    danger: tuple[int, int, int] = (244, 92, 92)
    food: tuple[int, int, int] = (255, 196, 74)


NIGHT_PALETTE = Palette()
DAY_PALETTE = Palette(
    background=(232, 239, 234),
    panel=(207, 220, 213),
    text=(18, 29, 27),
    muted=(76, 98, 91),
    accent=(0, 112, 72),
    accent_dark=(137, 190, 162),
    danger=(178, 42, 42),
    food=(166, 104, 0),
)
COLORS = Palette()


def set_color_mode(mode: str) -> None:
    """Change the shared palette without invalidating imports in game modules."""
    source = DAY_PALETTE if mode == "day" else NIGHT_PALETTE
    for name in Palette.__dataclass_fields__:
        setattr(COLORS, name, getattr(source, name))


def window_scale() -> int:
    try:
        return max(1, min(8, int(os.getenv("PIKONSOLA_SCALE", "4"))))
    except ValueError:
        return 4

