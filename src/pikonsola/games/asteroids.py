from __future__ import annotations

import math
import random
from dataclasses import dataclass
from enum import Enum, auto
from typing import Optional

import pygame

from ..config import COLORS, HEIGHT, WIDTH
from ..input import InputFrame, Key
from ..ui import text


PLAY_TOP = 18
TURN_SPEED = 210.0
THRUST = 62.0
MAX_SPEED = 58.0
BULLET_SPEED = 92.0


class Status(Enum):
    READY = auto()
    PLAYING = auto()
    GAME_OVER = auto()


@dataclass
class Ship:
    x: float
    y: float
    vx: float = 0.0
    vy: float = 0.0
    angle: float = 0.0


@dataclass
class Bullet:
    x: float
    y: float
    vx: float
    vy: float
    life: float = 1.15


@dataclass
class Asteroid:
    x: float
    y: float
    vx: float
    vy: float
    size: int
    angle: float = 0.0
    spin: float = 0.0
    shape: tuple[float, ...] = (1.0, 0.78, 0.92, 0.7, 1.0, 0.76, 0.9, 0.72)

    @property
    def radius(self) -> float:
        return (3.5, 6.0, 10.0)[self.size - 1]


@dataclass
class Spark:
    x: float
    y: float
    vx: float
    vy: float
    life: float


class Asteroids:
    title = "ASTEROIDS"

    def __init__(self, seed: Optional[int] = None) -> None:
        self.rng = random.Random(seed)
        self.best = 0
        self.stars = [(self.rng.randrange(WIDTH), self.rng.randrange(PLAY_TOP + 2, HEIGHT)) for _ in range(22)]
        self.reset()

    def reset(self) -> None:
        self.ship = Ship(WIDTH / 2, (PLAY_TOP + HEIGHT) / 2)
        self.bullets: list[Bullet] = []
        self.asteroids: list[Asteroid] = []
        self.sparks: list[Spark] = []
        self.score = 0
        self.lives = 3
        self.wave = 1
        self.fire_cooldown = 0.0
        self.invulnerable = 0.0
        self.status = Status.READY
        self._spawn_wave(4)

    def update(self, dt: float, controls: InputFrame) -> None:
        if self.status in {Status.READY, Status.GAME_OVER}:
            if controls.just_pressed(Key.START) or controls.just_pressed(Key.A):
                if self.status is Status.GAME_OVER:
                    self.reset()
                self.status = Status.PLAYING
                self.invulnerable = 1.5
            return

        dt = min(dt, 0.1)
        turn = int(controls.is_held(Key.RIGHT)) - int(controls.is_held(Key.LEFT))
        self.ship.angle = (self.ship.angle + turn * TURN_SPEED * dt) % 360

        if controls.is_held(Key.UP):
            dx, dy = self._direction(self.ship.angle)
            self.ship.vx += dx * THRUST * dt
            self.ship.vy += dy * THRUST * dt
        if controls.is_held(Key.DOWN):
            self.ship.vx *= max(0.0, 1.0 - 2.8 * dt)
            self.ship.vy *= max(0.0, 1.0 - 2.8 * dt)

        speed = math.hypot(self.ship.vx, self.ship.vy)
        if speed > MAX_SPEED:
            scale = MAX_SPEED / speed
            self.ship.vx *= scale
            self.ship.vy *= scale
        self.ship.x, self.ship.y = self._wrapped(
            self.ship.x + self.ship.vx * dt,
            self.ship.y + self.ship.vy * dt,
        )

        self.fire_cooldown = max(0.0, self.fire_cooldown - dt)
        if (controls.just_pressed(Key.A) or controls.just_pressed(Key.START)) and self.fire_cooldown == 0.0:
            self._fire()

        for bullet in self.bullets:
            bullet.x, bullet.y = self._wrapped(bullet.x + bullet.vx * dt, bullet.y + bullet.vy * dt)
            bullet.life -= dt
        self.bullets = [bullet for bullet in self.bullets if bullet.life > 0]

        for asteroid in self.asteroids:
            asteroid.x, asteroid.y = self._wrapped(asteroid.x + asteroid.vx * dt, asteroid.y + asteroid.vy * dt)
            asteroid.angle = (asteroid.angle + asteroid.spin * dt) % 360

        for spark in self.sparks:
            spark.x, spark.y = self._wrapped(spark.x + spark.vx * dt, spark.y + spark.vy * dt)
            spark.life -= dt
        self.sparks = [spark for spark in self.sparks if spark.life > 0]

        self.invulnerable = max(0.0, self.invulnerable - dt)
        self._resolve_collisions()
        if self.status is Status.PLAYING and not self.asteroids:
            self.wave += 1
            self.invulnerable = max(self.invulnerable, 1.0)
            self._spawn_wave(min(3 + self.wave, 7))

    def _fire(self) -> None:
        dx, dy = self._direction(self.ship.angle)
        self.bullets.append(
            Bullet(
                self.ship.x + dx * 7,
                self.ship.y + dy * 7,
                self.ship.vx + dx * BULLET_SPEED,
                self.ship.vy + dy * BULLET_SPEED,
            )
        )
        self.fire_cooldown = 0.2

    def _spawn_wave(self, count: int) -> None:
        for _ in range(count):
            for _attempt in range(30):
                x = self.rng.uniform(0, WIDTH)
                y = self.rng.uniform(PLAY_TOP, HEIGHT)
                if self._distance(x, y, self.ship.x, self.ship.y) > 28:
                    break
            angle = self.rng.uniform(0, math.tau)
            speed = self.rng.uniform(9.0, 17.0) + self.wave
            self.asteroids.append(self._make_asteroid(x, y, math.cos(angle) * speed, math.sin(angle) * speed, 3))

    def _make_asteroid(self, x: float, y: float, vx: float, vy: float, size: int) -> Asteroid:
        return Asteroid(
            x,
            y,
            vx,
            vy,
            size,
            self.rng.uniform(0, 360),
            self.rng.uniform(-35, 35),
            tuple(self.rng.uniform(0.68, 1.0) for _ in range(8)),
        )

    def _resolve_collisions(self) -> None:
        for bullet in list(self.bullets):
            target = next(
                (
                    asteroid
                    for asteroid in self.asteroids
                    if self._distance(bullet.x, bullet.y, asteroid.x, asteroid.y) <= asteroid.radius + 1
                ),
                None,
            )
            if target is not None:
                self.bullets.remove(bullet)
                self._destroy_asteroid(target)

        if self.invulnerable > 0:
            return
        hit = next(
            (
                asteroid
                for asteroid in self.asteroids
                if self._distance(self.ship.x, self.ship.y, asteroid.x, asteroid.y) <= asteroid.radius + 4
            ),
            None,
        )
        if hit is not None:
            self._burst(self.ship.x, self.ship.y, COLORS.danger, 10)
            self.lives -= 1
            if self.lives <= 0:
                self.best = max(self.best, self.score)
                self.status = Status.GAME_OVER
            else:
                self.ship = Ship(WIDTH / 2, (PLAY_TOP + HEIGHT) / 2)
                self.invulnerable = 2.0

    def _destroy_asteroid(self, asteroid: Asteroid) -> None:
        self.asteroids.remove(asteroid)
        self.score += {3: 20, 2: 50, 1: 100}[asteroid.size]
        self.best = max(self.best, self.score)
        self._burst(asteroid.x, asteroid.y, COLORS.food, 3 + asteroid.size * 2)
        if asteroid.size > 1:
            base = math.atan2(asteroid.vy, asteroid.vx)
            speed = math.hypot(asteroid.vx, asteroid.vy) * 1.3 + 5
            for offset in (-0.72, 0.72):
                angle = base + offset
                self.asteroids.append(
                    self._make_asteroid(
                        asteroid.x,
                        asteroid.y,
                        math.cos(angle) * speed,
                        math.sin(angle) * speed,
                        asteroid.size - 1,
                    )
                )

    def _burst(self, x: float, y: float, _color: tuple[int, int, int], count: int) -> None:
        for _ in range(count):
            angle = self.rng.uniform(0, math.tau)
            speed = self.rng.uniform(10, 35)
            self.sparks.append(Spark(x, y, math.cos(angle) * speed, math.sin(angle) * speed, self.rng.uniform(0.2, 0.6)))

    @staticmethod
    def _direction(angle: float) -> tuple[float, float]:
        radians = math.radians(angle)
        return math.sin(radians), -math.cos(radians)

    @staticmethod
    def _wrapped(x: float, y: float) -> tuple[float, float]:
        return x % WIDTH, PLAY_TOP + (y - PLAY_TOP) % (HEIGHT - PLAY_TOP)

    @staticmethod
    def _distance(x1: float, y1: float, x2: float, y2: float) -> float:
        dx = abs(x1 - x2)
        dy = abs(y1 - y2)
        dx = min(dx, WIDTH - dx)
        play_height = HEIGHT - PLAY_TOP
        dy = min(dy, play_height - dy)
        return math.hypot(dx, dy)

    def draw(self, surface: pygame.Surface) -> None:
        surface.fill(COLORS.background)
        text(surface, f"S {self.score:04d}", 3, 3, color=COLORS.accent, size=7, bold=True)
        text(surface, f"W {self.wave}", WIDTH // 2, 3, color=COLORS.muted, size=7, center=True)
        text(surface, f"L {self.lives}", 105, 3, color=COLORS.food, size=7, bold=True)
        pygame.draw.line(surface, COLORS.accent_dark, (2, PLAY_TOP - 1), (125, PLAY_TOP - 1))

        for x, y in self.stars:
            surface.set_at((x, y), (35, 47, 58))
        for asteroid in self.asteroids:
            self._draw_asteroid(surface, asteroid)
        for bullet in self.bullets:
            pygame.draw.circle(surface, COLORS.food, (round(bullet.x), round(bullet.y)), 1)
        for spark in self.sparks:
            color = COLORS.food if spark.life > 0.28 else COLORS.danger
            surface.set_at((round(spark.x) % WIDTH, round(spark.y) % HEIGHT), color)

        if self.status is Status.PLAYING and (self.invulnerable == 0 or int(self.invulnerable * 8) % 2 == 0):
            self._draw_ship(surface)
        if self.status is Status.READY:
            self._overlay(surface, "ASTEROIDS", "A: START")
        elif self.status is Status.GAME_OVER:
            self._overlay(surface, "KONIEC", "A: JESZCZE RAZ")

    def _draw_ship(self, surface: pygame.Surface) -> None:
        points = []
        for offset, radius in ((0, 7), (140, 5), (180, 2), (220, 5)):
            dx, dy = self._direction(self.ship.angle + offset)
            points.append((round(self.ship.x + dx * radius), round(self.ship.y + dy * radius)))
        pygame.draw.lines(surface, COLORS.accent, True, points, 1)
        if self.ship.vx or self.ship.vy:
            dx, dy = self._direction(self.ship.angle + 180)
            pygame.draw.line(
                surface,
                COLORS.food,
                (round(self.ship.x + dx * 3), round(self.ship.y + dy * 3)),
                (round(self.ship.x + dx * 7), round(self.ship.y + dy * 7)),
            )

    @staticmethod
    def _draw_asteroid(surface: pygame.Surface, asteroid: Asteroid) -> None:
        points = []
        for index, scale in enumerate(asteroid.shape):
            angle = math.radians(asteroid.angle + index * 45)
            radius = asteroid.radius * scale
            points.append((round(asteroid.x + math.cos(angle) * radius), round(asteroid.y + math.sin(angle) * radius)))
        color = COLORS.text if asteroid.size == 3 else COLORS.muted
        pygame.draw.lines(surface, color, True, points, 1)

    @staticmethod
    def _overlay(surface: pygame.Surface, heading: str, hint: str) -> None:
        rect = pygame.Rect(11, 51, 106, 34)
        pygame.draw.rect(surface, COLORS.background, rect)
        pygame.draw.rect(surface, COLORS.accent_dark, rect, 1)
        text(surface, heading, WIDTH // 2, 55, color=COLORS.text, size=11, center=True, bold=True)
        text(surface, hint, WIDTH // 2, 71, color=COLORS.food, size=7, center=True)
