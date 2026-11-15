from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum, auto

import pygame

from ..config import COLORS, HEIGHT, WIDTH
from ..input import InputFrame, Key
from ..ui import text


PLAY_TOP = 19
PADDLE_Y = 118
PADDLE_WIDTH = 25
PADDLE_HEIGHT = 3
PADDLE_SPEED = 92.0
BALL_RADIUS = 2
BALL_SPEED = 58.0
BRICK_ROWS = 5
BRICK_COLUMNS = 7
BRICK_WIDTH = 16
BRICK_HEIGHT = 7
BRICK_GAP = 1
BRICK_LEFT = 5
BRICK_TOP = 26


class Status(Enum):
    READY = auto()
    PLAYING = auto()
    GAME_OVER = auto()


@dataclass
class Ball:
    x: float
    y: float
    vx: float = 0.0
    vy: float = 0.0

    @property
    def speed(self) -> float:
        return math.hypot(self.vx, self.vy)


@dataclass
class Brick:
    rect: pygame.Rect
    row: int


class Arkanoid:
    title = "ARKANOID"

    def __init__(self) -> None:
        self.best = 0
        self.reset()

    def reset(self) -> None:
        self.score = 0
        self.lives = 3
        self.level = 1
        self.paddle_x = (WIDTH - PADDLE_WIDTH) / 2
        self.bricks: list[Brick] = []
        self._build_wall()
        self.ball = Ball(0, 0)
        self.status = Status.READY
        self._attach_ball()

    def _build_wall(self) -> None:
        self.bricks = []
        for row in range(BRICK_ROWS):
            for column in range(BRICK_COLUMNS):
                x = BRICK_LEFT + column * (BRICK_WIDTH + BRICK_GAP)
                y = BRICK_TOP + row * (BRICK_HEIGHT + BRICK_GAP)
                self.bricks.append(Brick(pygame.Rect(x, y, BRICK_WIDTH, BRICK_HEIGHT), row))

    def update(self, dt: float, controls: InputFrame) -> None:
        if self.status is Status.GAME_OVER:
            if controls.just_pressed(Key.A) or controls.just_pressed(Key.START):
                self.reset()
            return

        dt = min(dt, 0.1)
        direction = int(controls.is_held(Key.RIGHT)) - int(controls.is_held(Key.LEFT))
        self.paddle_x += direction * PADDLE_SPEED * dt
        self.paddle_x = max(2.0, min(WIDTH - PADDLE_WIDTH - 2.0, self.paddle_x))

        if self.status is Status.READY:
            self._attach_ball()
            if controls.just_pressed(Key.A) or controls.just_pressed(Key.START):
                self._launch()
            return

        # Małe kroki zapobiegają przelatywaniu piłki przez cienkie klocki.
        steps = max(1, math.ceil(dt * max(self.ball.speed, BALL_SPEED) / 1.5))
        step_dt = dt / steps
        for _ in range(steps):
            if self.status is not Status.PLAYING:
                break
            self._step_ball(step_dt)

    def _attach_ball(self) -> None:
        self.ball.x = self.paddle_x + PADDLE_WIDTH / 2
        self.ball.y = PADDLE_Y - BALL_RADIUS - 1
        self.ball.vx = 0.0
        self.ball.vy = 0.0

    def _launch(self) -> None:
        speed = BALL_SPEED + min(14.0, (self.level - 1) * 3.0)
        self.ball.vx = speed * 0.48
        self.ball.vy = -math.sqrt(speed * speed - self.ball.vx * self.ball.vx)
        self.status = Status.PLAYING

    def _step_ball(self, dt: float) -> None:
        old_x, old_y = self.ball.x, self.ball.y
        self.ball.x += self.ball.vx * dt
        self.ball.y += self.ball.vy * dt

        if self.ball.x - BALL_RADIUS <= 1 and self.ball.vx < 0:
            self.ball.x = 1 + BALL_RADIUS
            self.ball.vx = abs(self.ball.vx)
        elif self.ball.x + BALL_RADIUS >= WIDTH - 1 and self.ball.vx > 0:
            self.ball.x = WIDTH - 1 - BALL_RADIUS
            self.ball.vx = -abs(self.ball.vx)
        if self.ball.y - BALL_RADIUS <= PLAY_TOP and self.ball.vy < 0:
            self.ball.y = PLAY_TOP + BALL_RADIUS
            self.ball.vy = abs(self.ball.vy)

        paddle = pygame.Rect(round(self.paddle_x), PADDLE_Y, PADDLE_WIDTH, PADDLE_HEIGHT)
        if self.ball.vy > 0 and self._touches(paddle):
            self.ball.y = paddle.top - BALL_RADIUS
            offset = (self.ball.x - paddle.centerx) / (PADDLE_WIDTH / 2)
            offset = max(-1.0, min(1.0, offset))
            speed = max(BALL_SPEED, self.ball.speed)
            self.ball.vx = speed * 0.78 * offset
            self.ball.vy = -math.sqrt(max(1.0, speed * speed - self.ball.vx * self.ball.vx))

        hit = next((brick for brick in self.bricks if self._touches(brick.rect)), None)
        if hit is not None:
            self._bounce_from_rect(hit.rect, old_x, old_y)
            self.bricks.remove(hit)
            self.score += (BRICK_ROWS - hit.row) * 10
            self.best = max(self.best, self.score)
            if not self.bricks:
                self.level += 1
                self._build_wall()
                self.status = Status.READY
                self._attach_ball()
                return

        if self.ball.y - BALL_RADIUS > HEIGHT:
            self.lives -= 1
            if self.lives <= 0:
                self.best = max(self.best, self.score)
                self.status = Status.GAME_OVER
            else:
                self.status = Status.READY
                self._attach_ball()

    def _touches(self, rect: pygame.Rect) -> bool:
        closest_x = max(rect.left, min(self.ball.x, rect.right))
        closest_y = max(rect.top, min(self.ball.y, rect.bottom))
        dx = self.ball.x - closest_x
        dy = self.ball.y - closest_y
        return dx * dx + dy * dy <= BALL_RADIUS * BALL_RADIUS

    def _bounce_from_rect(self, rect: pygame.Rect, old_x: float, old_y: float) -> None:
        if old_y + BALL_RADIUS <= rect.top:
            self.ball.y = rect.top - BALL_RADIUS
            self.ball.vy = -abs(self.ball.vy)
        elif old_y - BALL_RADIUS >= rect.bottom:
            self.ball.y = rect.bottom + BALL_RADIUS
            self.ball.vy = abs(self.ball.vy)
        elif old_x + BALL_RADIUS <= rect.left:
            self.ball.x = rect.left - BALL_RADIUS
            self.ball.vx = -abs(self.ball.vx)
        elif old_x - BALL_RADIUS >= rect.right:
            self.ball.x = rect.right + BALL_RADIUS
            self.ball.vx = abs(self.ball.vx)
        else:
            self.ball.vy = -self.ball.vy

    def draw(self, surface: pygame.Surface) -> None:
        surface.fill(COLORS.background)
        text(surface, f"S {self.score:04d}", 3, 3, color=COLORS.accent, size=7, bold=True)
        text(surface, f"L {self.level}", WIDTH // 2, 3, color=COLORS.muted, size=7, center=True)
        text(surface, f"X {self.lives}", 105, 3, color=COLORS.food, size=7, bold=True)
        pygame.draw.line(surface, COLORS.accent_dark, (2, PLAY_TOP - 1), (125, PLAY_TOP - 1))

        colors = (COLORS.danger, COLORS.food, COLORS.accent, (76, 154, 230), (166, 105, 220))
        for brick in self.bricks:
            color = colors[brick.row]
            pygame.draw.rect(surface, color, brick.rect)
            pygame.draw.line(surface, tuple(min(255, channel + 45) for channel in color), brick.rect.topleft, brick.rect.topright)
            pygame.draw.line(surface, tuple(max(0, channel - 55) for channel in color), brick.rect.bottomleft, brick.rect.bottomright)

        paddle = pygame.Rect(round(self.paddle_x), PADDLE_Y, PADDLE_WIDTH, PADDLE_HEIGHT)
        pygame.draw.rect(surface, COLORS.text, paddle)
        pygame.draw.rect(surface, COLORS.accent, (paddle.x + 5, paddle.y, paddle.width - 10, 1))
        pygame.draw.circle(surface, COLORS.food, (round(self.ball.x), round(self.ball.y)), BALL_RADIUS)

        if self.status is Status.READY:
            self._overlay(
                surface,
                "ARKANOID" if self.level == 1 and self.score == 0 else f"POZIOM {self.level}",
                "A: PILKA",
            )
        elif self.status is Status.GAME_OVER:
            self._overlay(surface, "KONIEC", "A: JESZCZE RAZ")

    @staticmethod
    def _overlay(surface: pygame.Surface, heading: str, hint: str) -> None:
        rect = pygame.Rect(11, 72, 106, 32)
        pygame.draw.rect(surface, COLORS.background, rect)
        pygame.draw.rect(surface, COLORS.accent_dark, rect, 1)
        text(surface, heading, WIDTH // 2, 76, color=COLORS.text, size=11, center=True, bold=True)
        text(surface, hint, WIDTH // 2, 91, color=COLORS.food, size=7, center=True)
