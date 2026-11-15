from __future__ import annotations

import random
from collections import deque
from enum import Enum, auto
from typing import Optional

import pygame

from ..config import COLORS, HEIGHT, WIDTH
from ..input import InputFrame, Key
from ..ui import text


CELL = 6
COLS = 19
ROWS = 16
ORIGIN_X = 7
ORIGIN_Y = 25
STEP_SECONDS = 0.13


class Status(Enum):
    READY = auto()
    PLAYING = auto()
    GAME_OVER = auto()


DIRECTIONS = {
    Key.UP: (0, -1),
    Key.DOWN: (0, 1),
    Key.LEFT: (-1, 0),
    Key.RIGHT: (1, 0),
}


class Nibbles:
    title = "NIBBLES"

    def __init__(self, seed: Optional[int] = None) -> None:
        self.rng = random.Random(seed)
        self.best = 0
        self.reset()

    def reset(self) -> None:
        cx, cy = COLS // 2, ROWS // 2
        self.snake = deque([(cx, cy), (cx - 1, cy), (cx - 2, cy)])
        self.direction = (1, 0)
        self.next_direction = self.direction
        self.food = self._new_food()
        self.score = 0
        self.elapsed = 0.0
        self.status = Status.READY

    def _new_food(self) -> tuple[int, int]:
        free = [
            (x, y)
            for y in range(ROWS)
            for x in range(COLS)
            if (x, y) not in self.snake
        ]
        return self.rng.choice(free)

    def update(self, dt: float, controls: InputFrame) -> None:
        if self.status in {Status.READY, Status.GAME_OVER}:
            if controls.just_pressed(Key.START) or controls.just_pressed(Key.A):
                if self.status is Status.GAME_OVER:
                    self.reset()
                self.status = Status.PLAYING
            return

        for key, candidate in DIRECTIONS.items():
            if controls.just_pressed(key):
                if candidate != (-self.direction[0], -self.direction[1]):
                    self.next_direction = candidate
                break

        self.elapsed += dt
        interval = max(0.065, STEP_SECONDS - self.score * 0.002)
        while self.elapsed >= interval and self.status is Status.PLAYING:
            self.elapsed -= interval
            self._step()

    def _step(self) -> None:
        self.direction = self.next_direction
        hx, hy = self.snake[0]
        dx, dy = self.direction
        new_head = (hx + dx, hy + dy)
        eating = new_head == self.food
        occupied = set(self.snake if eating else list(self.snake)[:-1])
        if (
            new_head[0] < 0
            or new_head[0] >= COLS
            or new_head[1] < 0
            or new_head[1] >= ROWS
            or new_head in occupied
        ):
            self.status = Status.GAME_OVER
            self.best = max(self.best, self.score)
            return

        self.snake.appendleft(new_head)
        if eating:
            self.score += 1
            self.food = self._new_food()
        else:
            self.snake.pop()

    def draw(self, surface: pygame.Surface) -> None:
        surface.fill(COLORS.background)
        text(surface, f"NIBBLES {self.score:03d}", 5, 4, color=COLORS.accent, size=9, bold=True)
        text(surface, f"HI {self.best:03d}", 88, 4, color=COLORS.muted, size=8)

        board = pygame.Rect(ORIGIN_X - 2, ORIGIN_Y - 2, COLS * CELL + 3, ROWS * CELL + 3)
        pygame.draw.rect(surface, COLORS.panel, board)
        pygame.draw.rect(surface, COLORS.accent_dark, board, 1)

        fx, fy = self.food
        food_rect = pygame.Rect(ORIGIN_X + fx * CELL + 1, ORIGIN_Y + fy * CELL + 1, 4, 4)
        pygame.draw.rect(surface, COLORS.food, food_rect)

        for index, (x, y) in enumerate(self.snake):
            color = COLORS.accent if index == 0 else (55, 188, 126)
            pygame.draw.rect(
                surface,
                color,
                (ORIGIN_X + x * CELL, ORIGIN_Y + y * CELL, CELL - 1, CELL - 1),
            )

        if self.status is Status.READY:
            self._overlay(surface, "NIBBLES", "A / START")
        elif self.status is Status.GAME_OVER:
            self._overlay(surface, "KONIEC", "A: JESZCZE RAZ")

    @staticmethod
    def _overlay(surface: pygame.Surface, heading: str, hint: str) -> None:
        rect = pygame.Rect(14, 49, 100, 34)
        pygame.draw.rect(surface, COLORS.background, rect)
        pygame.draw.rect(surface, COLORS.accent_dark, rect, 1)
        text(surface, heading, WIDTH // 2, 54, color=COLORS.text, size=11, center=True, bold=True)
        text(surface, hint, WIDTH // 2, 69, color=COLORS.food, size=7, center=True)

