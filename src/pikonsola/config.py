from __future__ import annotations

import os
from dataclasses import dataclass


WIDTH = 128
HEIGHT = 128
FPS = 30


@dataclass(frozen=True)
class Palette:
    background: tuple[int, int, int] = (9, 12, 18)
    panel: tuple[int, int, int] = (21, 28, 39)
    text: tuple[int, int, int] = (224, 239, 234)
    muted: tuple[int, int, int] = (110, 130, 140)
    accent: tuple[int, int, int] = (86, 232, 154)
    accent_dark: tuple[int, int, int] = (28, 112, 80)
    danger: tuple[int, int, int] = (244, 92, 92)
    food: tuple[int, int, int] = (255, 196, 74)


COLORS = Palette()


def window_scale() -> int:
    try:
        return max(1, min(8, int(os.getenv("PIKONSOLA_SCALE", "4"))))
    except ValueError:
        return 4

