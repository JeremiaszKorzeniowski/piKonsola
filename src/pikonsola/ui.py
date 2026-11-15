from __future__ import annotations

from functools import lru_cache

import pygame

from .config import COLORS, HEIGHT, WIDTH


@lru_cache(maxsize=16)
def pixel_font(size: int = 10, bold: bool = False) -> pygame.font.Font:
    return pygame.font.SysFont("dejavusansmono", size, bold=bold)


def text(
    surface: pygame.Surface,
    value: str,
    x: int,
    y: int,
    *,
    color: tuple[int, int, int] = COLORS.text,
    size: int = 10,
    center: bool = False,
    bold: bool = False,
) -> pygame.Rect:
    image = pixel_font(size, bold).render(value, False, color)
    rect = image.get_rect()
    if center:
        rect.midtop = (x, y)
    else:
        rect.topleft = (x, y)
    surface.blit(image, rect)
    return rect


def frame(surface: pygame.Surface, title: str) -> None:
    surface.fill(COLORS.background)
    pygame.draw.rect(surface, COLORS.panel, (3, 3, WIDTH - 6, HEIGHT - 6), 1)
    pygame.draw.line(surface, COLORS.accent_dark, (4, 18), (WIDTH - 5, 18))
    text(surface, title, WIDTH // 2, 5, color=COLORS.accent, size=9, center=True, bold=True)

