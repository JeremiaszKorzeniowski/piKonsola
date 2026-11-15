from __future__ import annotations

import math
import random
from dataclasses import dataclass
from enum import Enum, auto
from typing import Optional

import pygame

from ..config import COLORS, WIDTH
from ..input import InputFrame, Key
from ..ui import text


GROUND_Y = 105
DINO_X = 17
DINO_WIDTH = 14
DINO_HEIGHT = 18
RUN_SPEED = 52.0
MAX_SPEED = 88.0
JUMP_SPEED = 112.0
GRAVITY = 270.0


class Status(Enum):
    READY = auto()
    PLAYING = auto()
    GAME_OVER = auto()


@dataclass
class Obstacle:
    x: float
    width: int
    height: int

    @property
    def rect(self) -> pygame.Rect:
        return pygame.Rect(round(self.x), GROUND_Y - self.height, self.width, self.height)


class Dino:
    title = "DINO"

    def __init__(self, seed: Optional[int] = None) -> None:
        self.rng = random.Random(seed)
        self.best = 0
        self.reset()

    def reset(self) -> None:
        self.status = Status.READY
        self.dino_y = float(GROUND_Y - DINO_HEIGHT)
        self.velocity_y = 0.0
        self.obstacles: list[Obstacle] = []
        self.distance = 0.0
        self.score = 0
        self.speed = RUN_SPEED
        self.spawn_distance = 76.0
        self.run_frame = 0.0

    @property
    def on_ground(self) -> bool:
        return self.dino_y >= GROUND_Y - DINO_HEIGHT - 0.01

    @property
    def dino_rect(self) -> pygame.Rect:
        # Węższy hitbox wybacza kontakt pojedynczych pikseli ogona i pyska.
        return pygame.Rect(DINO_X + 2, round(self.dino_y) + 2, DINO_WIDTH - 4, DINO_HEIGHT - 2)

    def update(self, dt: float, controls: InputFrame) -> None:
        jump_pressed = any(
            controls.just_pressed(key) for key in (Key.A, Key.UP, Key.START)
        )

        if self.status is Status.READY:
            if jump_pressed:
                self.status = Status.PLAYING
                self._jump()
            return

        if self.status is Status.GAME_OVER:
            if jump_pressed:
                self.reset()
                self.status = Status.PLAYING
                self._jump()
            return

        if jump_pressed and self.on_ground:
            self._jump()

        # Krótkie kroki utrzymują pewne kolizje również po chwilowym spadku FPS.
        dt = min(dt, 0.1)
        steps = max(1, math.ceil(dt / 0.015))
        step_dt = dt / steps
        for _ in range(steps):
            if self.status is not Status.PLAYING:
                break
            self._step(step_dt)

    def _jump(self) -> None:
        self.velocity_y = -JUMP_SPEED

    def _step(self, dt: float) -> None:
        self.distance += self.speed * dt
        self.score = int(self.distance / 5.0)
        self.speed = min(MAX_SPEED, RUN_SPEED + self.score * 0.18)
        self.run_frame += dt * self.speed / 9.0

        self.velocity_y += GRAVITY * dt
        self.dino_y += self.velocity_y * dt
        floor = GROUND_Y - DINO_HEIGHT
        if self.dino_y >= floor:
            self.dino_y = float(floor)
            self.velocity_y = 0.0

        travelled = self.speed * dt
        self.spawn_distance -= travelled
        for obstacle in self.obstacles:
            obstacle.x -= travelled

        if self.spawn_distance <= 0:
            self._spawn_obstacle()
        self.obstacles = [obstacle for obstacle in self.obstacles if obstacle.x + obstacle.width >= 0]

        if any(self.dino_rect.colliderect(obstacle.rect) for obstacle in self.obstacles):
            self.status = Status.GAME_OVER
            self.best = max(self.best, self.score)

    def _spawn_obstacle(self) -> None:
        height = self.rng.choice((12, 15, 18, 21))
        width = self.rng.choice((5, 6, 8))
        self.obstacles.append(Obstacle(float(WIDTH + 3), width, height))
        # Odstęp rośnie lekko wraz z prędkością, więc zawsze da się przeskoczyć.
        self.spawn_distance += self.rng.uniform(55.0, 83.0) + self.speed * 0.18

    def draw(self, surface: pygame.Surface) -> None:
        surface.fill(COLORS.background)
        text(surface, "DINO", 4, 3, color=COLORS.accent, size=8, bold=True)
        text(surface, f"{self.score:05d}", 73, 3, color=COLORS.text, size=8, bold=True)
        text(surface, f"HI {self.best:05d}", 73, 13, color=COLORS.muted, size=6)

        self._draw_cloud(surface, 82 - int(self.distance * 0.08) % 145, 31)
        self._draw_cloud(surface, 31 - int(self.distance * 0.04) % 154, 49)

        pygame.draw.line(surface, COLORS.muted, (0, GROUND_Y), (WIDTH - 1, GROUND_Y))
        offset = -int(self.distance) % 13
        for x in range(offset, WIDTH, 13):
            pygame.draw.line(surface, COLORS.accent_dark, (x, GROUND_Y + 5), (x + 5, GROUND_Y + 5))

        for obstacle in self.obstacles:
            self._draw_cactus(surface, obstacle)
        self._draw_dino(surface)

        if self.status is Status.READY:
            self._overlay(surface, "DINO", "A / GORA: SKOK")
        elif self.status is Status.GAME_OVER:
            self._overlay(surface, "KONIEC", "A: JESZCZE RAZ")

    @staticmethod
    def _draw_cloud(surface: pygame.Surface, x: int, y: int) -> None:
        color = COLORS.panel
        pygame.draw.rect(surface, color, (x, y + 3, 18, 3))
        pygame.draw.rect(surface, color, (x + 4, y, 7, 5))
        pygame.draw.rect(surface, color, (x + 11, y + 2, 5, 4))

    @staticmethod
    def _draw_cactus(surface: pygame.Surface, obstacle: Obstacle) -> None:
        rect = obstacle.rect
        color = COLORS.accent
        stem_x = rect.centerx - 1
        pygame.draw.rect(surface, color, (stem_x, rect.top, 3, rect.height))
        if rect.height >= 15:
            pygame.draw.rect(surface, color, (rect.left, rect.top + 6, 3, 3))
            pygame.draw.rect(surface, color, (rect.left, rect.top + 3, 2, 6))
        if rect.width >= 6:
            pygame.draw.rect(surface, color, (rect.right - 3, rect.top + 9, 3, 3))
            pygame.draw.rect(surface, color, (rect.right - 2, rect.top + 6, 2, 6))

    def _draw_dino(self, surface: pygame.Surface) -> None:
        x, y = DINO_X, round(self.dino_y)
        color = COLORS.text if self.status is not Status.GAME_OVER else COLORS.danger
        # Sylwetka w stylu pikselowym: ogon, tułów, głowa i pysk.
        pygame.draw.rect(surface, color, (x + 4, y + 7, 7, 8))
        pygame.draw.rect(surface, color, (x + 8, y, 6, 9))
        pygame.draw.rect(surface, color, (x + 12, y + 4, 3, 4))
        pygame.draw.polygon(surface, color, ((x + 4, y + 9), (x - 2, y + 6), (x + 2, y + 13)))
        pygame.draw.rect(surface, COLORS.background, (x + 11, y + 2, 1, 1))

        if not self.on_ground:
            pygame.draw.rect(surface, color, (x + 5, y + 14, 2, 4))
            pygame.draw.rect(surface, color, (x + 10, y + 14, 2, 4))
        elif int(self.run_frame) % 2:
            pygame.draw.rect(surface, color, (x + 4, y + 14, 2, 4))
            pygame.draw.rect(surface, color, (x + 10, y + 14, 4, 2))
        else:
            pygame.draw.rect(surface, color, (x + 4, y + 14, 4, 2))
            pygame.draw.rect(surface, color, (x + 11, y + 14, 2, 4))

    @staticmethod
    def _overlay(surface: pygame.Surface, heading: str, hint: str) -> None:
        rect = pygame.Rect(10, 45, 108, 34)
        pygame.draw.rect(surface, COLORS.background, rect)
        pygame.draw.rect(surface, COLORS.accent_dark, rect, 1)
        text(surface, heading, WIDTH // 2, 50, color=COLORS.text, size=11, center=True, bold=True)
        text(surface, hint, WIDTH // 2, 65, color=COLORS.food, size=7, center=True)
