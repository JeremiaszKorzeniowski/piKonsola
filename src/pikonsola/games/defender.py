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


WORLD_WIDTH = 1024.0
RADAR_BOTTOM = 20
PLAY_TOP = 22
GROUND_Y = 114
SHIP_SPEED = 76.0
BULLET_SPEED = 180.0


class Status(Enum):
    READY = auto()
    PLAYING = auto()
    GAME_OVER = auto()


@dataclass
class Ship:
    x: float = WORLD_WIDTH / 2
    y: float = 66.0
    direction: int = 1


@dataclass
class Bullet:
    x: float
    y: float
    vx: float
    life: float = 0.72


@dataclass
class Human:
    x: float
    y: float
    alive: bool = True
    carrier: Optional["Enemy"] = None


@dataclass
class Enemy:
    x: float
    y: float
    kind: str = "lander"
    target: Optional[Human] = None
    carrying: Optional[Human] = None
    phase: float = 0.0


@dataclass
class Spark:
    x: float
    y: float
    vx: float
    vy: float
    life: float


class Defender:
    title = "DEFENDER"

    def __init__(self, seed: Optional[int] = None) -> None:
        self.rng = random.Random(seed)
        self.best = 0
        self.reset()

    def reset(self) -> None:
        self.ship = Ship()
        self.bullets: list[Bullet] = []
        self.enemies: list[Enemy] = []
        self.sparks: list[Spark] = []
        self.humans = [Human(75.0 + index * 145.0, 0.0) for index in range(7)]
        for human in self.humans:
            human.y = self._terrain_y(human.x) - 5
        self.score = 0
        self.lives = 3
        self.wave = 1
        self.fire_cooldown = 0.0
        self.invulnerable = 0.0
        self.status = Status.READY
        self._spawn_wave(4)

    def update(self, dt: float, controls: InputFrame) -> None:
        if self.status in {Status.READY, Status.GAME_OVER}:
            if controls.just_pressed(Key.A) or controls.just_pressed(Key.START):
                if self.status is Status.GAME_OVER:
                    self.reset()
                self.status = Status.PLAYING
                self.invulnerable = 1.5
            return

        dt = min(dt, 0.1)
        horizontal = int(controls.is_held(Key.RIGHT)) - int(controls.is_held(Key.LEFT))
        vertical = int(controls.is_held(Key.DOWN)) - int(controls.is_held(Key.UP))
        if horizontal:
            self.ship.direction = horizontal
            self.ship.x = (self.ship.x + horizontal * SHIP_SPEED * dt) % WORLD_WIDTH
        self.ship.y = max(PLAY_TOP + 8, min(GROUND_Y - 9, self.ship.y + vertical * SHIP_SPEED * 0.72 * dt))

        self.fire_cooldown = max(0.0, self.fire_cooldown - dt)
        if (controls.just_pressed(Key.A) or controls.just_pressed(Key.START)) and self.fire_cooldown == 0:
            self._fire()

        for bullet in self.bullets:
            bullet.x = (bullet.x + bullet.vx * dt) % WORLD_WIDTH
            bullet.life -= dt
        self.bullets = [bullet for bullet in self.bullets if bullet.life > 0]

        for enemy in list(self.enemies):
            self._move_enemy(enemy, dt)
        for spark in self.sparks:
            spark.x = (spark.x + spark.vx * dt) % WORLD_WIDTH
            spark.y += spark.vy * dt
            spark.life -= dt
        self.sparks = [spark for spark in self.sparks if spark.life > 0]

        self.invulnerable = max(0.0, self.invulnerable - dt)
        self._resolve_collisions()
        if self.status is Status.PLAYING and not self.enemies:
            self.wave += 1
            self.score += 250 * sum(human.alive for human in self.humans)
            self._spawn_wave(min(3 + self.wave * 2, 12))

    def _fire(self) -> None:
        self.bullets.append(
            Bullet(
                (self.ship.x + self.ship.direction * 7) % WORLD_WIDTH,
                self.ship.y,
                self.ship.direction * BULLET_SPEED,
            )
        )
        self.fire_cooldown = 0.16

    def _spawn_wave(self, count: int) -> None:
        for index in range(count):
            x = (self.ship.x + 120 + index * WORLD_WIDTH / count + self.rng.uniform(-35, 35)) % WORLD_WIDTH
            self.enemies.append(Enemy(x, self.rng.uniform(29, 55), phase=self.rng.uniform(0, math.tau)))

    def _move_enemy(self, enemy: Enemy, dt: float) -> None:
        if enemy.kind == "mutant":
            dx = self._world_delta(enemy.x, self.ship.x)
            enemy.x = (enemy.x + max(-1, min(1, dx)) * (35 + self.wave * 2) * dt) % WORLD_WIDTH
            enemy.y += max(-1, min(1, self.ship.y - enemy.y)) * 27 * dt
            return

        if enemy.carrying is not None:
            enemy.y -= (19 + self.wave) * dt
            enemy.carrying.x = enemy.x
            enemy.carrying.y = enemy.y + 5
            if enemy.y < PLAY_TOP + 4:
                enemy.carrying.alive = False
                enemy.carrying.carrier = None
                enemy.carrying = None
                enemy.kind = "mutant"
            return

        if enemy.target is None or not enemy.target.alive or enemy.target.carrier is not None:
            candidates = [human for human in self.humans if human.alive and human.carrier is None]
            enemy.target = min(candidates, key=lambda human: abs(self._world_delta(enemy.x, human.x)), default=None)

        if enemy.target is None:
            enemy.kind = "mutant"
            return

        dx = self._world_delta(enemy.x, enemy.target.x)
        enemy.x = (enemy.x + max(-1, min(1, dx)) * (17 + self.wave) * dt) % WORLD_WIDTH
        ground = self._terrain_y(enemy.x)
        if abs(dx) < 4:
            enemy.y = min(ground - 8, enemy.y + 18 * dt)
            if enemy.y >= ground - 9:
                enemy.carrying = enemy.target
                enemy.target.carrier = enemy
        else:
            enemy.phase += dt * 2.5
            enemy.y += math.sin(enemy.phase) * 7 * dt

    def _resolve_collisions(self) -> None:
        for bullet in list(self.bullets):
            enemy = next(
                (
                    target
                    for target in self.enemies
                    if abs(self._world_delta(bullet.x, target.x)) < 7 and abs(bullet.y - target.y) < 6
                ),
                None,
            )
            if enemy is not None:
                self.bullets.remove(bullet)
                self._destroy_enemy(enemy)

        if self.invulnerable > 0:
            return
        hit = next(
            (
                enemy
                for enemy in self.enemies
                if abs(self._world_delta(self.ship.x, enemy.x)) < 8 and abs(self.ship.y - enemy.y) < 6
            ),
            None,
        )
        if hit is not None:
            self._burst(self.ship.x, self.ship.y, 12)
            self.lives -= 1
            if self.lives <= 0:
                self.best = max(self.best, self.score)
                self.status = Status.GAME_OVER
            else:
                self.ship.y = 66
                self.invulnerable = 2.0

    def _destroy_enemy(self, enemy: Enemy) -> None:
        self.enemies.remove(enemy)
        self.score += 150 if enemy.kind == "mutant" else 100
        self.best = max(self.best, self.score)
        if enemy.carrying is not None:
            human = enemy.carrying
            human.carrier = None
            human.x = enemy.x
            human.y = self._terrain_y(human.x) - 5
            self.score += 250
        self._burst(enemy.x, enemy.y, 7)

    def _burst(self, x: float, y: float, count: int) -> None:
        for _ in range(count):
            angle = self.rng.uniform(0, math.tau)
            speed = self.rng.uniform(12, 38)
            self.sparks.append(Spark(x, y, math.cos(angle) * speed, math.sin(angle) * speed, 0.45))

    @staticmethod
    def _world_delta(source: float, target: float) -> float:
        return (target - source + WORLD_WIDTH / 2) % WORLD_WIDTH - WORLD_WIDTH / 2

    @staticmethod
    def _terrain_y(world_x: float) -> float:
        return 112 + math.sin(world_x * 0.031) * 3 + math.sin(world_x * 0.011) * 2

    def _screen_x(self, world_x: float) -> float:
        return WIDTH / 2 + self._world_delta(self.ship.x, world_x)

    def draw(self, surface: pygame.Surface) -> None:
        surface.fill(COLORS.background)
        text(surface, f"{self.score:05d}", 2, 2, color=COLORS.accent, size=7, bold=True)
        text(surface, f"W{self.wave}", 55, 2, color=COLORS.muted, size=7)
        text(surface, f"L{self.lives}", 106, 2, color=COLORS.food, size=7, bold=True)
        self._draw_radar(surface)
        self._draw_terrain(surface)

        for human in self.humans:
            if human.alive:
                x = self._screen_x(human.x)
                if -3 <= x <= WIDTH + 3:
                    self._draw_human(surface, round(x), round(human.y))
        for enemy in self.enemies:
            x = self._screen_x(enemy.x)
            if -8 <= x <= WIDTH + 8:
                self._draw_enemy(surface, round(x), round(enemy.y), enemy.kind)
        for bullet in self.bullets:
            x = self._screen_x(bullet.x)
            if 0 <= x < WIDTH:
                pygame.draw.line(surface, COLORS.food, (round(x), round(bullet.y)), (round(x - bullet.vx / 45), round(bullet.y)))
        for spark in self.sparks:
            x = self._screen_x(spark.x)
            if 0 <= x < WIDTH and PLAY_TOP <= spark.y < HEIGHT:
                surface.set_at((round(x), round(spark.y)), COLORS.danger)

        if self.status is Status.PLAYING and (self.invulnerable == 0 or int(self.invulnerable * 8) % 2 == 0):
            self._draw_ship(surface)
        if self.status is Status.READY:
            self._overlay(surface, "DEFENDER", "A: START")
        elif self.status is Status.GAME_OVER:
            self._overlay(surface, "KONIEC", "A: JESZCZE RAZ")

    def _draw_radar(self, surface: pygame.Surface) -> None:
        pygame.draw.rect(surface, COLORS.panel, (1, 10, 126, 9))
        pygame.draw.rect(surface, COLORS.accent_dark, (1, 10, 126, 9), 1)
        for human in self.humans:
            if human.alive:
                x = 2 + int(human.x / WORLD_WIDTH * 124)
                surface.set_at((x, 17), COLORS.accent)
        for enemy in self.enemies:
            x = 2 + int(enemy.x / WORLD_WIDTH * 124)
            surface.set_at((x, 12), COLORS.danger)
        ship_x = 2 + int(self.ship.x / WORLD_WIDTH * 124)
        pygame.draw.line(surface, COLORS.food, (ship_x, 13), (ship_x, 16))

    def _draw_terrain(self, surface: pygame.Surface) -> None:
        points = []
        for screen_x in range(0, WIDTH + 4, 4):
            world_x = (self.ship.x + screen_x - WIDTH / 2) % WORLD_WIDTH
            points.append((screen_x, round(self._terrain_y(world_x))))
        points.extend(((WIDTH, HEIGHT), (0, HEIGHT)))
        pygame.draw.polygon(surface, COLORS.panel, points)
        pygame.draw.lines(surface, COLORS.accent_dark, False, points[:-2], 1)

    def _draw_ship(self, surface: pygame.Surface) -> None:
        x, y, direction = WIDTH // 2, round(self.ship.y), self.ship.direction
        points = ((x + 7 * direction, y), (x - 4 * direction, y - 4), (x - 2 * direction, y), (x - 4 * direction, y + 4))
        pygame.draw.lines(surface, COLORS.accent, True, points, 1)
        pygame.draw.line(surface, COLORS.food, (x - 3 * direction, y), (x - 7 * direction, y))

    @staticmethod
    def _draw_enemy(surface: pygame.Surface, x: int, y: int, kind: str) -> None:
        color = COLORS.danger if kind == "mutant" else COLORS.text
        if kind == "mutant":
            pygame.draw.lines(surface, color, True, ((x, y - 4), (x + 5, y), (x, y + 4), (x - 5, y)), 1)
        else:
            pygame.draw.line(surface, color, (x - 5, y), (x + 5, y))
            pygame.draw.line(surface, color, (x - 3, y - 2), (x + 3, y - 2))
            pygame.draw.line(surface, color, (x - 2, y + 1), (x, y + 4))
            pygame.draw.line(surface, color, (x + 2, y + 1), (x, y + 4))

    @staticmethod
    def _draw_human(surface: pygame.Surface, x: int, y: int) -> None:
        pygame.draw.circle(surface, COLORS.food, (x, y - 3), 1)
        pygame.draw.line(surface, COLORS.food, (x, y - 2), (x, y + 2))
        pygame.draw.line(surface, COLORS.food, (x - 2, y), (x + 2, y))

    @staticmethod
    def _overlay(surface: pygame.Surface, heading: str, hint: str) -> None:
        rect = pygame.Rect(11, 51, 106, 34)
        pygame.draw.rect(surface, COLORS.background, rect)
        pygame.draw.rect(surface, COLORS.accent_dark, rect, 1)
        text(surface, heading, WIDTH // 2, 55, color=COLORS.text, size=11, center=True, bold=True)
        text(surface, hint, WIDTH // 2, 71, color=COLORS.food, size=7, center=True)
