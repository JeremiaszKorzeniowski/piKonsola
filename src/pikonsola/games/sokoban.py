from __future__ import annotations

import importlib
import pkgutil
from dataclasses import dataclass
from enum import Enum, auto
from types import ModuleType
from typing import Iterable, Mapping

import pygame

from ..config import COLORS, HEIGHT, WIDTH
from ..input import InputFrame, Key
from ..ui import text
from . import sokoban_levels


Position = tuple[int, int]


class Status(Enum):
    READY = auto()
    PLAYING = auto()
    LEVEL_COMPLETE = auto()
    WON = auto()


@dataclass(frozen=True)
class Level:
    name: str
    width: int
    height: int
    walls: frozenset[Position]
    goals: frozenset[Position]
    crates: frozenset[Position]
    player: Position


def level_from_module(module: ModuleType) -> Level:
    data = getattr(module, "LEVEL", None)
    if not isinstance(data, Mapping):
        raise ValueError(f"{module.__name__} nie udostępnia słownika LEVEL")
    raw_map = data.get("map")
    if not isinstance(raw_map, (tuple, list)) or not raw_map:
        raise ValueError("Pole 'map' musi być niepustą listą wierszy")
    rows = tuple(str(row) for row in raw_map)
    width = len(rows[0])
    if width < 3 or any(len(row) != width for row in rows):
        raise ValueError("Wszystkie wiersze mapy muszą mieć tę samą długość")
    if len(rows) < 3 or width > 11 or len(rows) > 9:
        raise ValueError("Mapa Sokobana musi mieścić się na ekranie")

    allowed = set("# .@$*+")
    if any(character not in allowed for row in rows for character in row):
        raise ValueError("Mapa zawiera nieznany znak")
    if any(cell != "#" for cell in rows[0] + rows[-1]):
        raise ValueError("Mapa musi być otoczona ścianami")
    if any(row[0] != "#" or row[-1] != "#" for row in rows):
        raise ValueError("Mapa musi być otoczona ścianami")

    walls: set[Position] = set()
    goals: set[Position] = set()
    crates: set[Position] = set()
    players: list[Position] = []
    for y, row in enumerate(rows):
        for x, cell in enumerate(row):
            position = (x, y)
            if cell == "#":
                walls.add(position)
            if cell in ".*+":
                goals.add(position)
            if cell in "$*":
                crates.add(position)
            if cell in "@+":
                players.append(position)
    if len(players) != 1:
        raise ValueError("Mapa musi mieć dokładnie jednego gracza")
    if not crates or len(crates) != len(goals):
        raise ValueError("Mapa musi mieć tyle samo skrzyń co celów")
    return Level(
        name=str(data.get("name", module.__name__)).upper(),
        width=width,
        height=len(rows),
        walls=frozenset(walls),
        goals=frozenset(goals),
        crates=frozenset(crates),
        player=players[0],
    )


def load_levels() -> tuple[Level, ...]:
    module_names = sorted(
        info.name
        for info in pkgutil.iter_modules(sokoban_levels.__path__)
        if info.name.startswith("level_")
    )
    if not module_names:
        raise RuntimeError("Brak poziomów w pakiecie sokoban_levels")
    return tuple(
        level_from_module(importlib.import_module(f"{sokoban_levels.__name__}.{name}"))
        for name in module_names
    )


class Sokoban:
    title = "SOKOBAN"
    DIRECTIONS = (
        (Key.UP, (0, -1)),
        (Key.DOWN, (0, 1)),
        (Key.LEFT, (-1, 0)),
        (Key.RIGHT, (1, 0)),
    )

    def __init__(self, levels: Iterable[Level] | None = None) -> None:
        self.levels = tuple(levels) if levels is not None else load_levels()
        if not self.levels:
            raise ValueError("Gra wymaga co najmniej jednego poziomu")
        self.reset()

    def reset(self) -> None:
        self.level_index = 0
        self.status = Status.READY
        self._load_level(0)

    def _load_level(self, index: int) -> None:
        self.level_index = index
        self.level = self.levels[index]
        self.player = self.level.player
        self.crates = set(self.level.crates)
        self.moves = 0
        self.pushes = 0
        self.transition_time = 0.0

    def restart_level(self) -> None:
        self._load_level(self.level_index)
        self.status = Status.PLAYING

    def update(self, dt: float, controls: InputFrame) -> None:
        if self.status in {Status.READY, Status.WON}:
            if controls.just_pressed(Key.A) or controls.just_pressed(Key.START):
                if self.status is Status.WON:
                    self.reset()
                self.status = Status.PLAYING
            return
        if self.status is Status.LEVEL_COMPLETE:
            self.transition_time -= dt
            if self.transition_time <= 0:
                next_index = self.level_index + 1
                if next_index == len(self.levels):
                    self.status = Status.WON
                else:
                    self._load_level(next_index)
                    self.status = Status.PLAYING
            return
        if controls.just_pressed(Key.B):
            self.restart_level()
            return
        for key, direction in self.DIRECTIONS:
            if controls.just_pressed(key):
                self._move(direction)
                break

    def _move(self, direction: Position) -> bool:
        dx, dy = direction
        target = (self.player[0] + dx, self.player[1] + dy)
        if target in self.level.walls:
            return False
        if target in self.crates:
            beyond = (target[0] + dx, target[1] + dy)
            if beyond in self.level.walls or beyond in self.crates:
                return False
            self.crates.remove(target)
            self.crates.add(beyond)
            self.pushes += 1
        self.player = target
        self.moves += 1
        if self.crates == set(self.level.goals):
            self.status = Status.LEVEL_COMPLETE
            self.transition_time = 0.7
        return True

    def draw(self, surface: pygame.Surface) -> None:
        surface.fill(COLORS.background)
        text(
            surface,
            f"SOKOBAN {self.level_index + 1}/{len(self.levels)}",
            WIDTH // 2,
            3,
            color=COLORS.accent,
            size=9,
            center=True,
            bold=True,
        )
        tile = min(12, 112 // self.level.width, 91 // self.level.height)
        board_width = self.level.width * tile
        board_height = self.level.height * tile
        left = (WIDTH - board_width) // 2
        top = 17 + (91 - board_height) // 2

        for y in range(self.level.height):
            for x in range(self.level.width):
                position = (x, y)
                rect = pygame.Rect(left + x * tile, top + y * tile, tile, tile)
                if position in self.level.walls:
                    pygame.draw.rect(surface, COLORS.accent_dark, rect)
                    pygame.draw.rect(surface, COLORS.accent, rect, 1)
                else:
                    pygame.draw.rect(surface, COLORS.panel, rect)
                    if position in self.level.goals:
                        pygame.draw.circle(surface, COLORS.food, rect.center, max(2, tile // 4))
                if position in self.crates:
                    color = COLORS.accent if position in self.level.goals else (174, 112, 54)
                    box = rect.inflate(-2, -2)
                    pygame.draw.rect(surface, color, box)
                    pygame.draw.line(surface, COLORS.background, box.topleft, box.bottomright, 1)
                    pygame.draw.line(surface, COLORS.background, box.topright, box.bottomleft, 1)

        player_rect = pygame.Rect(
            left + self.player[0] * tile + 2,
            top + self.player[1] * tile + 2,
            tile - 4,
            tile - 4,
        )
        pygame.draw.circle(surface, COLORS.text, player_rect.center, max(2, player_rect.width // 2))
        pygame.draw.circle(surface, COLORS.background, (player_rect.centerx - 2, player_rect.centery - 1), 1)
        pygame.draw.circle(surface, COLORS.background, (player_rect.centerx + 2, player_rect.centery - 1), 1)

        if self.status is Status.READY:
            self._message(surface, "A: START", COLORS.food)
        elif self.status is Status.LEVEL_COMPLETE:
            self._message(surface, "GOTOWE!", COLORS.accent)
        elif self.status is Status.WON:
            self._message(surface, "BRAWO! A: OD NOWA", COLORS.food)
        else:
            text(surface, f"RUCHY {self.moves}  B: RESET", WIDTH // 2, 114, color=COLORS.muted, size=7, center=True)

    @staticmethod
    def _message(surface: pygame.Surface, value: str, color: tuple[int, int, int]) -> None:
        width = min(122, max(66, len(value) * 7))
        pygame.draw.rect(surface, COLORS.background, ((WIDTH - width) // 2, 106, width, 17))
        pygame.draw.rect(surface, color, ((WIDTH - width) // 2, 106, width, 17), 1)
        text(surface, value, WIDTH // 2, 109, color=color, size=8, center=True, bold=True)
