from __future__ import annotations

from enum import Enum, auto

import pygame

from ..config import COLORS, WIDTH
from ..input import InputFrame, Key
from ..ui import text


BOARD_SIZE = 8
CELL = 12
ORIGIN_X = 16
ORIGIN_Y = 20

KNIGHT_JUMPS = (
    (-2, -1),
    (-2, 1),
    (-1, -2),
    (-1, 2),
    (1, -2),
    (1, 2),
    (2, -1),
    (2, 1),
)


class Status(Enum):
    PLAYING = auto()
    LOST = auto()
    WON = auto()


class KnightTour:
    """Interaktywna wersja problemu wędrówki skoczka."""

    title = "SKOCZEK"

    def __init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        self.position = (0, 0)  # a1
        self.path = [self.position]
        self.visited = {self.position}
        self.status = Status.PLAYING
        self.selection = 0

    @property
    def destinations(self) -> list[tuple[int, int]]:
        x, y = self.position
        return sorted(
            (
                (x + dx, y + dy)
                for dx, dy in KNIGHT_JUMPS
                if 0 <= x + dx < BOARD_SIZE and 0 <= y + dy < BOARD_SIZE
            ),
            key=lambda square: (square[1], square[0]),
        )

    @property
    def selected_destination(self) -> tuple[int, int]:
        return self.destinations[self.selection % len(self.destinations)]

    @property
    def square_name(self) -> str:
        return f"{chr(ord('A') + self.position[0])}{self.position[1] + 1}"

    def update(self, _dt: float, controls: InputFrame) -> None:
        if self.status is not Status.PLAYING:
            if controls.just_pressed(Key.A) or controls.just_pressed(Key.START):
                self.reset()
            return

        destinations = self.destinations
        if controls.just_pressed(Key.LEFT) or controls.just_pressed(Key.UP):
            self.selection = (self.selection - 1) % len(destinations)
        elif controls.just_pressed(Key.RIGHT) or controls.just_pressed(Key.DOWN):
            self.selection = (self.selection + 1) % len(destinations)
        elif controls.just_pressed(Key.A) or controls.just_pressed(Key.START):
            self._land(self.selected_destination)
        elif controls.just_pressed(Key.B):
            self.reset()

    def _land(self, destination: tuple[int, int]) -> None:
        self.position = destination
        self.path.append(destination)
        if destination in self.visited:
            self.status = Status.LOST
            return

        self.visited.add(destination)
        if len(self.visited) == BOARD_SIZE * BOARD_SIZE:
            self.status = Status.WON
            return
        self.selection = 0

    @staticmethod
    def _screen_rect(square: tuple[int, int]) -> pygame.Rect:
        x, rank = square
        row = BOARD_SIZE - 1 - rank
        return pygame.Rect(ORIGIN_X + x * CELL, ORIGIN_Y + row * CELL, CELL, CELL)

    def draw(self, surface: pygame.Surface) -> None:
        surface.fill(COLORS.background)
        text(surface, "SKOCZEK", 4, 3, color=COLORS.accent, size=9, bold=True)
        text(surface, self.square_name, 72, 4, color=COLORS.muted, size=8, bold=True)
        text(surface, f"{len(self.visited):02d}/64", 92, 4, color=COLORS.food, size=8, bold=True)

        light = (188, 199, 196)
        dark = (80, 94, 98)
        visited_light = (224, 174, 54)
        visited_dark = (174, 124, 30)
        for rank in range(BOARD_SIZE):
            for file_index in range(BOARD_SIZE):
                square = (file_index, rank)
                is_light = (file_index + rank) % 2 == 1
                if square in self.visited:
                    color = visited_light if is_light else visited_dark
                else:
                    color = light if is_light else dark
                pygame.draw.rect(surface, color, self._screen_rect(square))

        if self.status is Status.PLAYING:
            selected = self.selected_destination
            for destination in self.destinations:
                rect = self._screen_rect(destination)
                center = rect.center
                if destination == selected:
                    pygame.draw.rect(surface, COLORS.food, rect.inflate(-2, -2), 2)
                    pygame.draw.circle(surface, COLORS.food, center, 2)
                else:
                    pygame.draw.circle(surface, COLORS.accent, center, 2)

        knight_rect = self._screen_rect(self.position)
        knight_color = COLORS.danger if self.status is Status.LOST else COLORS.text
        x, y = knight_rect.x, knight_rect.y
        pygame.draw.polygon(
            surface,
            knight_color,
            (
                (x + 2, y + 10),
                (x + 10, y + 10),
                (x + 9, y + 8),
                (x + 7, y + 6),
                (x + 8, y + 4),
                (x + 6, y + 2),
                (x + 3, y + 1),
                (x + 4, y + 4),
                (x + 2, y + 7),
            ),
        )
        pygame.draw.rect(surface, COLORS.background, (x + 5, y + 3, 1, 1))

        if self.status is Status.LOST:
            self._overlay(surface, "POWTORKA!", f"WYNIK {len(self.visited)}/64")
        elif self.status is Status.WON:
            self._overlay(surface, "SUKCES!", "64 POLA")
        else:
            text(surface, "PAD: WYBOR  A: SKOK", WIDTH // 2, 118, color=COLORS.muted, size=6, center=True)

    @staticmethod
    def _overlay(surface: pygame.Surface, heading: str, result: str) -> None:
        rect = pygame.Rect(23, 51, 82, 42)
        pygame.draw.rect(surface, COLORS.background, rect)
        pygame.draw.rect(surface, COLORS.food, rect, 1)
        text(surface, heading, WIDTH // 2, 57, color=COLORS.text, size=11, center=True, bold=True)
        text(surface, result, WIDTH // 2, 72, color=COLORS.food, size=7, center=True)
        text(surface, "A: OD NOWA", WIDTH // 2, 82, color=COLORS.muted, size=6, center=True)
