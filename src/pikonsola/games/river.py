from __future__ import annotations

import random
from dataclasses import dataclass
from enum import Enum, auto
from typing import Optional

import pygame

from ..config import COLORS, HEIGHT, WIDTH
from ..input import InputFrame, Key
from ..ui import text


RIVER_LEFT = 17
RIVER_RIGHT = 111
PLAYER_WIDTH = 11
PLAYER_HEIGHT = 9
PLAYER_SPEED = 46.0
SCROLL_SPEED = 24.0
BULLET_SPEED = 72.0


class Status(Enum):
    READY = auto()
    PLAYING = auto()
    GAME_OVER = auto()


@dataclass
class RiverObject:
    x: float
    y: float
    kind: str

    @property
    def rect(self) -> pygame.Rect:
        sizes = {"rock": (9, 7), "boat": (9, 11), "fuel": (7, 9)}
        width, height = sizes[self.kind]
        return pygame.Rect(round(self.x), round(self.y), width, height)


@dataclass
class Bullet:
    x: float
    y: float

    @property
    def rect(self) -> pygame.Rect:
        return pygame.Rect(round(self.x), round(self.y), 2, 5)


class River:
    title = "RIVER"

    def __init__(self, seed: Optional[int] = None) -> None:
        self.rng = random.Random(seed)
        self.best = 0
        self.reset()

    def reset(self) -> None:
        self.player_x = float((WIDTH - PLAYER_WIDTH) // 2)
        self.player_y = 105.0
        self.objects: list[RiverObject] = []
        self.bullets: list[Bullet] = []
        self.score = 0
        self.lives = 3
        self.distance = 0.0
        self.spawn_timer = 0.65
        self.fire_cooldown = 0.0
        self.invulnerable = 0.0
        self.status = Status.READY

    def update(self, dt: float, controls: InputFrame) -> None:
        if self.status in {Status.READY, Status.GAME_OVER}:
            if controls.just_pressed(Key.A) or controls.just_pressed(Key.START):
                if self.status is Status.GAME_OVER:
                    self.reset()
                self.status = Status.PLAYING
            return

        horizontal = int(controls.is_held(Key.RIGHT)) - int(controls.is_held(Key.LEFT))
        vertical = int(controls.is_held(Key.DOWN)) - int(controls.is_held(Key.UP))
        self.player_x += horizontal * PLAYER_SPEED * dt
        self.player_y += vertical * PLAYER_SPEED * dt
        self.player_x = max(RIVER_LEFT + 3.0, min(RIVER_RIGHT - PLAYER_WIDTH - 3.0, self.player_x))
        self.player_y = max(42.0, min(HEIGHT - PLAYER_HEIGHT - 4.0, self.player_y))

        self.fire_cooldown = max(0.0, self.fire_cooldown - dt)
        self.invulnerable = max(0.0, self.invulnerable - dt)
        if (controls.just_pressed(Key.A) or controls.just_pressed(Key.START)) and self.fire_cooldown == 0.0:
            self.bullets.append(Bullet(self.player_x + 4.5, self.player_y - 5))
            self.fire_cooldown = 0.38

        self.distance += SCROLL_SPEED * dt
        self._move_objects(dt)
        self._spawn_objects(dt)
        self._resolve_collisions()

    def _move_objects(self, dt: float) -> None:
        for obj in self.objects:
            obj.y += SCROLL_SPEED * dt
        for bullet in self.bullets:
            bullet.y -= BULLET_SPEED * dt
        self.objects = [obj for obj in self.objects if obj.y < HEIGHT + 12]
        self.bullets = [bullet for bullet in self.bullets if bullet.y > 17]

    def _spawn_objects(self, dt: float) -> None:
        self.spawn_timer -= dt
        if self.spawn_timer > 0:
            return
        kind = self.rng.choices(("rock", "boat", "fuel"), weights=(4, 4, 1), k=1)[0]
        width = {"rock": 9, "boat": 9, "fuel": 7}[kind]
        x = self.rng.randint(RIVER_LEFT + 8, RIVER_RIGHT - width - 8)
        self.objects.append(RiverObject(float(x), 19.0, kind))
        self.spawn_timer = self.rng.uniform(1.15, 1.65)

    def _resolve_collisions(self) -> None:
        for bullet in list(self.bullets):
            target = next(
                (obj for obj in self.objects if obj.kind != "fuel" and bullet.rect.colliderect(obj.rect)),
                None,
            )
            if target is not None:
                self.objects.remove(target)
                self.bullets.remove(bullet)
                self.score += 10 if target.kind == "rock" else 20

        player_rect = pygame.Rect(round(self.player_x), round(self.player_y), PLAYER_WIDTH, PLAYER_HEIGHT)
        fuel = next(
            (obj for obj in self.objects if obj.kind == "fuel" and obj.rect.colliderect(player_rect)),
            None,
        )
        if fuel is not None:
            self.objects.remove(fuel)
            self.score += 25

        obstacle = next(
            (obj for obj in self.objects if obj.kind != "fuel" and obj.rect.colliderect(player_rect)),
            None,
        )
        if obstacle is not None and self.invulnerable == 0.0:
            self.objects.remove(obstacle)
            self.lives -= 1
            self.invulnerable = 1.0
            if self.lives <= 0:
                self.best = max(self.best, self.score)
                self.status = Status.GAME_OVER

    def draw(self, surface: pygame.Surface) -> None:
        bank = (45, 91, 55)
        water = (21, 78, 112)
        foam = (72, 144, 166)
        surface.fill(bank)
        pygame.draw.rect(surface, water, (RIVER_LEFT, 18, RIVER_RIGHT - RIVER_LEFT, HEIGHT - 18))
        pygame.draw.line(surface, (99, 145, 76), (RIVER_LEFT, 18), (RIVER_LEFT, HEIGHT - 1), 2)
        pygame.draw.line(surface, (99, 145, 76), (RIVER_RIGHT - 1, 18), (RIVER_RIGHT - 1, HEIGHT - 1), 2)

        stripe_offset = int(self.distance) % 24
        for y in range(24 - stripe_offset, HEIGHT, 24):
            pygame.draw.line(surface, foam, (30, y), (30, y + 6))
            pygame.draw.line(surface, foam, (96, y + 8), (96, y + 14))

        pygame.draw.rect(surface, COLORS.background, (0, 0, WIDTH, 18))
        text(surface, f"S {self.score:03d}", 3, 3, color=COLORS.accent, size=8, bold=True)
        text(surface, f"HI {self.best:03d}", WIDTH // 2, 3, color=COLORS.muted, size=7, center=True)
        text(surface, f"L {self.lives}", 103, 3, color=COLORS.food, size=8, bold=True)

        for obj in self.objects:
            self._draw_object(surface, obj)
        for bullet in self.bullets:
            pygame.draw.rect(surface, COLORS.food, bullet.rect)
        if self.invulnerable == 0.0 or int(self.invulnerable * 10) % 2 == 0:
            self._draw_player(surface)

        if self.status is Status.READY:
            self._overlay(surface, "RIVER", "A / START")
        elif self.status is Status.GAME_OVER:
            self._overlay(surface, "KONIEC", "A: JESZCZE RAZ")

    def _draw_player(self, surface: pygame.Surface) -> None:
        x, y = round(self.player_x), round(self.player_y)
        pygame.draw.rect(surface, COLORS.food, (x + 4, y, 3, 9))
        pygame.draw.rect(surface, COLORS.food, (x, y + 4, PLAYER_WIDTH, 3))
        pygame.draw.rect(surface, COLORS.text, (x + 4, y + 1, 3, 2))

    @staticmethod
    def _draw_object(surface: pygame.Surface, obj: RiverObject) -> None:
        x, y = round(obj.x), round(obj.y)
        if obj.kind == "rock":
            pygame.draw.polygon(surface, (116, 121, 121), [(x + 1, y + 6), (x + 2, y + 1), (x + 6, y), (x + 9, y + 5), (x + 7, y + 7)])
        elif obj.kind == "boat":
            pygame.draw.rect(surface, COLORS.danger, (x + 2, y, 5, 8))
            pygame.draw.polygon(surface, (173, 53, 53), [(x, y + 7), (x + 9, y + 7), (x + 7, y + 11), (x + 2, y + 11)])
            pygame.draw.rect(surface, COLORS.text, (x + 3, y + 2, 3, 2))
        else:
            pygame.draw.rect(surface, COLORS.accent, (x, y, 7, 9))
            pygame.draw.rect(surface, COLORS.background, (x + 2, y + 2, 3, 5))
            pygame.draw.rect(surface, COLORS.accent, (x + 3, y + 3, 1, 3))

    @staticmethod
    def _overlay(surface: pygame.Surface, heading: str, hint: str) -> None:
        rect = pygame.Rect(11, 49, 106, 36)
        pygame.draw.rect(surface, COLORS.background, rect)
        pygame.draw.rect(surface, COLORS.accent_dark, rect, 1)
        text(surface, heading, WIDTH // 2, 54, color=COLORS.text, size=12, center=True, bold=True)
        text(surface, hint, WIDTH // 2, 71, color=COLORS.food, size=7, center=True)
