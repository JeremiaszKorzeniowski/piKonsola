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
from . import platformer_levels


PLAYER_WIDTH = 8
PLAYER_HEIGHT = 10
MOVE_SPEED = 42.0
JUMP_SPEED = 105.0
GRAVITY = 220.0
ENEMY_SPEED = 6.0
HUD_HEIGHT = 16


class Status(Enum):
    READY = auto()
    PLAYING = auto()
    LEVEL_COMPLETE = auto()
    GAME_OVER = auto()
    WON = auto()


@dataclass(frozen=True)
class Level:
    name: str
    width: int
    spawn: tuple[int, int]
    platforms: tuple[tuple[int, int, int, int], ...]
    hazards: tuple[tuple[int, int, int, int], ...]
    enemies: tuple[tuple[int, int, int, int], ...]
    key: tuple[int, int]
    door: tuple[int, int]


@dataclass
class Enemy:
    x: float
    y: float
    left: float
    right: float
    direction: int = 1

    @property
    def rect(self) -> pygame.Rect:
        return pygame.Rect(round(self.x), round(self.y), 8, 8)


def _tuple_field(data: Mapping[str, object], name: str, size: int) -> tuple[tuple[int, ...], ...]:
    value = data.get(name)
    if not isinstance(value, (tuple, list)):
        raise ValueError(f"Pole {name!r} musi być listą lub krotką")
    result = tuple(tuple(int(number) for number in item) for item in value)
    if any(len(item) != size for item in result):
        raise ValueError(f"Każdy element pola {name!r} musi mieć {size} wartości")
    return result


def _point_field(data: Mapping[str, object], name: str) -> tuple[int, int]:
    value = data.get(name)
    if not isinstance(value, (tuple, list)) or len(value) != 2:
        raise ValueError(f"Pole {name!r} musi być parą współrzędnych")
    return int(value[0]), int(value[1])


def level_from_module(module: ModuleType) -> Level:
    data = getattr(module, "LEVEL", None)
    if not isinstance(data, Mapping):
        raise ValueError(f"{module.__name__} nie udostępnia słownika LEVEL")
    level = Level(
        name=str(data.get("name", module.__name__)).upper(),
        width=int(data.get("width", 0)),
        spawn=_point_field(data, "spawn"),
        platforms=_tuple_field(data, "platforms", 4),
        hazards=_tuple_field(data, "hazards", 4),
        enemies=_tuple_field(data, "enemies", 4),
        key=_point_field(data, "key"),
        door=_point_field(data, "door"),
    )
    if level.width < WIDTH or not level.platforms:
        raise ValueError(f"Nieprawidłowy rozmiar poziomu {level.name}")
    if not 0 <= level.spawn[0] < level.width or not 0 <= level.door[0] < level.width:
        raise ValueError(f"Start lub drzwi poziomu {level.name} są poza mapą")
    return level


def load_levels() -> tuple[Level, ...]:
    """Wczytaj wszystkie pliki level_*.py w kolejności ich nazw."""
    module_names = sorted(
        info.name
        for info in pkgutil.iter_modules(platformer_levels.__path__)
        if info.name.startswith("level_")
    )
    if not module_names:
        raise RuntimeError("Brak poziomów w pakiecie platformer_levels")
    modules = (
        importlib.import_module(f"{platformer_levels.__name__}.{name}")
        for name in module_names
    )
    return tuple(level_from_module(module) for module in modules)


class Platformer:
    title = "PLATFUS"

    def __init__(self, levels: Iterable[Level] | None = None) -> None:
        self.levels = tuple(levels) if levels is not None else load_levels()
        if not self.levels:
            raise ValueError("Gra wymaga co najmniej jednego poziomu")
        self.reset()

    def reset(self) -> None:
        self.lives = 3
        self.level_index = 0
        self.status = Status.READY
        self.transition_time = 0.0
        self._load_level(0)

    def _load_level(self, index: int) -> None:
        self.level_index = index
        self.level = self.levels[index]
        self.player_x = float(self.level.spawn[0])
        self.player_y = float(self.level.spawn[1])
        self.velocity_y = 0.0
        self.on_ground = True
        self.has_key = False
        self.camera_x = 0.0
        self.invulnerable = 0.0
        self.notice_time = 0.0
        self.enemies = [
            Enemy(float(x), float(y), float(left), float(right))
            for x, y, left, right in self.level.enemies
        ]

    @property
    def player_rect(self) -> pygame.Rect:
        return pygame.Rect(round(self.player_x), round(self.player_y), PLAYER_WIDTH, PLAYER_HEIGHT)

    @property
    def key_rect(self) -> pygame.Rect:
        return pygame.Rect(self.level.key[0], self.level.key[1], 6, 8)

    @property
    def door_rect(self) -> pygame.Rect:
        return pygame.Rect(self.level.door[0], self.level.door[1], 12, 20)

    def update(self, dt: float, controls: InputFrame) -> None:
        if self.status in {Status.READY, Status.GAME_OVER, Status.WON}:
            if controls.just_pressed(Key.A) or controls.just_pressed(Key.START):
                if self.status in {Status.GAME_OVER, Status.WON}:
                    self.reset()
                self.status = Status.PLAYING
            return

        if self.status is Status.LEVEL_COMPLETE:
            self.transition_time -= dt
            if self.transition_time <= 0:
                next_index = self.level_index + 1
                if next_index >= len(self.levels):
                    self.status = Status.WON
                else:
                    self._load_level(next_index)
                    self.status = Status.PLAYING
            return

        self.invulnerable = max(0.0, self.invulnerable - dt)
        self.notice_time = max(0.0, self.notice_time - dt)
        jump_pressed = any(controls.just_pressed(key) for key in (Key.A, Key.UP, Key.START))
        if jump_pressed and self.on_ground:
            self.velocity_y = -JUMP_SPEED
            self.on_ground = False

        direction = int(controls.is_held(Key.RIGHT)) - int(controls.is_held(Key.LEFT))
        self._move_enemies(dt)
        self._move_player(dt, direction)
        self._resolve_entities()
        target_camera = self.player_x - 38
        self.camera_x = max(0.0, min(self.level.width - WIDTH, target_camera))

    def _move_enemies(self, dt: float) -> None:
        for enemy in self.enemies:
            enemy.x += enemy.direction * ENEMY_SPEED * dt
            if enemy.x <= enemy.left:
                enemy.x = enemy.left
                enemy.direction = 1
            elif enemy.x >= enemy.right:
                enemy.x = enemy.right
                enemy.direction = -1

    def _move_player(self, dt: float, direction: int) -> None:
        horizontal_change = direction * MOVE_SPEED * dt
        self.player_x += horizontal_change
        self.player_x = max(0.0, min(self.level.width - PLAYER_WIDTH, self.player_x))
        rect = self.player_rect
        for platform in self._platform_rects():
            if rect.colliderect(platform):
                if horizontal_change > 0:
                    self.player_x = float(platform.left - PLAYER_WIDTH)
                elif horizontal_change < 0:
                    self.player_x = float(platform.right)
                rect = self.player_rect

        old_bottom = self.player_y + PLAYER_HEIGHT
        self.velocity_y += GRAVITY * dt
        self.player_y += self.velocity_y * dt
        rect = self.player_rect
        self.on_ground = False
        for platform in self._platform_rects():
            if not rect.colliderect(platform):
                continue
            if self.velocity_y >= 0 and old_bottom <= platform.top + 1:
                self.player_y = float(platform.top - PLAYER_HEIGHT)
                self.velocity_y = 0.0
                self.on_ground = True
                rect = self.player_rect
            elif self.velocity_y < 0:
                self.player_y = float(platform.bottom)
                self.velocity_y = 0.0
                rect = self.player_rect

        if self.player_y > HEIGHT + 12:
            self._hurt()

    def _platform_rects(self) -> tuple[pygame.Rect, ...]:
        return tuple(pygame.Rect(*values) for values in self.level.platforms)

    def _resolve_entities(self) -> None:
        player = self.player_rect
        if not self.has_key and player.colliderect(self.key_rect):
            self.has_key = True

        if self.invulnerable == 0.0:
            if any(player.colliderect(pygame.Rect(*values)) for values in self.level.hazards):
                self._hurt()
                return
            if any(player.colliderect(enemy.rect) for enemy in self.enemies):
                self._hurt()
                return

        if player.colliderect(self.door_rect):
            if self.has_key:
                self.status = Status.LEVEL_COMPLETE
                self.transition_time = 1.0
            else:
                self.player_x = float(self.door_rect.left - PLAYER_WIDTH)
                self.notice_time = 1.0

    def _hurt(self) -> None:
        if self.status is not Status.PLAYING:
            return
        self.lives -= 1
        if self.lives <= 0:
            self.status = Status.GAME_OVER
            return
        self.player_x = float(self.level.spawn[0])
        self.player_y = float(self.level.spawn[1])
        self.velocity_y = 0.0
        self.on_ground = True
        self.camera_x = 0.0
        self.invulnerable = 1.2

    def draw(self, surface: pygame.Surface) -> None:
        self._draw_background(surface)
        offset = round(self.camera_x)
        for platform in self._platform_rects():
            shown = platform.move(-offset, 0)
            pygame.draw.rect(surface, (75, 104, 83), shown)
            pygame.draw.line(surface, COLORS.accent, shown.topleft, shown.topright, 2)
        for values in self.level.hazards:
            hazard = pygame.Rect(*values).move(-offset, 0)
            pygame.draw.polygon(
                surface, COLORS.danger,
                (hazard.bottomleft, (hazard.centerx, hazard.top), hazard.bottomright),
            )
        for enemy in self.enemies:
            self._draw_enemy(surface, enemy.rect.move(-offset, 0))
        if not self.has_key:
            self._draw_key(surface, self.key_rect.move(-offset, 0))
        self._draw_door(surface, self.door_rect.move(-offset, 0))
        if self.invulnerable == 0.0 or int(self.invulnerable * 10) % 2 == 0:
            self._draw_player(surface, self.player_rect.move(-offset, 0))

        pygame.draw.rect(surface, COLORS.background, (0, 0, WIDTH, HUD_HEIGHT))
        text(surface, f"{self.level_index + 1}/{len(self.levels)} {self.level.name}", 3, 3, color=COLORS.text, size=7, bold=True)
        text(surface, f"ZYCIA {self.lives}", 89, 3, color=COLORS.food, size=7, bold=True)
        pygame.draw.rect(surface, COLORS.accent if self.has_key else COLORS.muted, (78, 5, 5, 5), 1 if not self.has_key else 0)

        if self.notice_time > 0:
            text(surface, "NAJPIERW KLUCZ!", WIDTH // 2, 23, color=COLORS.food, size=7, center=True, bold=True)
        if self.status is Status.READY:
            self._overlay(surface, "PLATFUS", "LEWO/PRAWO + A")
        elif self.status is Status.LEVEL_COMPLETE:
            self._overlay(surface, "POZIOM!", "DALEJ...")
        elif self.status is Status.GAME_OVER:
            self._overlay(surface, "KONIEC", "A: OD NOWA")
        elif self.status is Status.WON:
            self._overlay(surface, "WYGRANA!", "A: OD NOWA")

    def _draw_background(self, surface: pygame.Surface) -> None:
        sky = (16, 28, 46) if self.level_index == 2 else (28, 54, 72)
        surface.fill(sky)
        offset = round(self.camera_x * 0.25) % 55
        for x in range(-55, WIDTH + 55, 55):
            pygame.draw.polygon(
                surface, (35, 68, 72),
                ((x - offset, 116), (x + 25 - offset, 70), (x + 55 - offset, 116)),
            )
        star_offset = round(self.camera_x * 0.1) % 47
        for x in range(14 - star_offset, WIDTH, 47):
            pygame.draw.circle(surface, (210, 224, 188), (x, 31), 1)

    @staticmethod
    def _draw_player(surface: pygame.Surface, rect: pygame.Rect) -> None:
        pygame.draw.rect(surface, COLORS.food, rect)
        pygame.draw.rect(surface, COLORS.text, (rect.x + 2, rect.y + 2, 2, 2))
        pygame.draw.rect(surface, (163, 85, 47), (rect.x, rect.bottom - 2, rect.width, 2))

    @staticmethod
    def _draw_enemy(surface: pygame.Surface, rect: pygame.Rect) -> None:
        pygame.draw.rect(surface, COLORS.danger, rect)
        pygame.draw.rect(surface, COLORS.background, (rect.x + 1, rect.y + 2, 2, 2))
        pygame.draw.rect(surface, COLORS.background, (rect.right - 3, rect.y + 2, 2, 2))
        pygame.draw.line(surface, COLORS.background, (rect.x + 2, rect.bottom - 2), (rect.right - 2, rect.bottom - 2))

    @staticmethod
    def _draw_key(surface: pygame.Surface, rect: pygame.Rect) -> None:
        pygame.draw.circle(surface, COLORS.food, (rect.x + 2, rect.y + 2), 2, 1)
        pygame.draw.line(surface, COLORS.food, (rect.x + 3, rect.y + 4), (rect.right, rect.bottom - 1), 2)

    @staticmethod
    def _draw_door(surface: pygame.Surface, rect: pygame.Rect) -> None:
        pygame.draw.rect(surface, (116, 70, 47), rect)
        pygame.draw.rect(surface, (201, 151, 83), rect, 2)
        pygame.draw.rect(surface, COLORS.food, (rect.right - 4, rect.centery, 2, 2))

    @staticmethod
    def _overlay(surface: pygame.Surface, heading: str, hint: str) -> None:
        rect = pygame.Rect(12, 47, 104, 37)
        pygame.draw.rect(surface, COLORS.background, rect)
        pygame.draw.rect(surface, COLORS.accent_dark, rect, 1)
        text(surface, heading, WIDTH // 2, 52, color=COLORS.text, size=12, center=True, bold=True)
        text(surface, hint, WIDTH // 2, 70, color=COLORS.food, size=7, center=True)
