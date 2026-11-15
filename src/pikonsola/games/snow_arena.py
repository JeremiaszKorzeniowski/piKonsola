from __future__ import annotations

import importlib
import math
import pkgutil
import random
from dataclasses import dataclass
from enum import Enum, auto
from types import ModuleType
from typing import Mapping, Optional

import pygame

from ..config import COLORS, HEIGHT, WIDTH
from ..input import InputFrame, Key
from ..ui import text
from . import snow_arena_levels


FOV = math.pi / 3
MOVE_SPEED = 2.15
TURN_SPEED = 1.75
PLAYER_RADIUS = 0.20
OBJECT_RADIUS = {"snowman": 0.28, "igloo": 0.48, "sled": 0.38}
MAX_ACTIVE_ENEMIES = 2


class Status(Enum):
    READY = auto()
    PLAYING = auto()
    GAME_OVER = auto()


@dataclass(frozen=True)
class Arena:
    name: str
    tiles: tuple[str, ...]
    spawn: tuple[float, float, float]
    enemy_spawns: tuple[tuple[float, float], ...]
    objects: tuple[tuple[str, float, float], ...]

    @property
    def width(self) -> int:
        return len(self.tiles[0])

    @property
    def height(self) -> int:
        return len(self.tiles)


@dataclass
class Enemy:
    x: float
    y: float
    fire_timer: float
    phase: float


@dataclass
class Projectile:
    x: float
    y: float
    dx: float
    dy: float
    hostile: bool


def arena_from_module(module: ModuleType) -> Arena:
    data = getattr(module, "LEVEL", None)
    if not isinstance(data, Mapping):
        raise ValueError(f"{module.__name__} nie udostępnia słownika LEVEL")
    tiles = tuple(str(row) for row in data.get("map", ()))
    if not tiles or len({len(row) for row in tiles}) != 1:
        raise ValueError("Mapa areny musi być niepustym prostokątem")
    if any(char not in "#." for row in tiles for char in row):
        raise ValueError("Mapa areny zawiera nieznane pola")
    if any(char != "#" for char in tiles[0] + tiles[-1]):
        raise ValueError("Arena musi mieć zamkniętą górną i dolną ścianę")
    if any(row[0] != "#" or row[-1] != "#" for row in tiles):
        raise ValueError("Arena musi mieć zamknięte boczne ściany")

    spawn_raw = data.get("spawn", ())
    enemy_raw = data.get("enemy_spawns", ())
    object_raw = data.get("objects", ())
    if not isinstance(spawn_raw, (tuple, list)) or len(spawn_raw) != 3:
        raise ValueError("Spawn gracza musi zawierać x, y i kierunek")
    arena = Arena(
        name=str(data.get("name", module.__name__)).upper(),
        tiles=tiles,
        spawn=(float(spawn_raw[0]), float(spawn_raw[1]), float(spawn_raw[2])),
        enemy_spawns=tuple((float(item[0]), float(item[1])) for item in enemy_raw),
        objects=tuple((str(item[0]), float(item[1]), float(item[2])) for item in object_raw),
    )
    if len(arena.enemy_spawns) < MAX_ACTIVE_ENEMIES:
        raise ValueError("Arena wymaga co najmniej dwóch spawnów przeciwników")
    if any(kind not in OBJECT_RADIUS for kind, _, _ in arena.objects):
        raise ValueError("Nieznany rodzaj dekoracji")
    points = [(arena.spawn[0], arena.spawn[1]), *arena.enemy_spawns]
    points.extend((x, y) for _, x, y in arena.objects)
    if any(_wall_at(arena, x, y) for x, y in points):
        raise ValueError("Obiekt lub spawn znajduje się w ścianie")
    return arena


def load_arenas() -> tuple[Arena, ...]:
    names = sorted(
        info.name for info in pkgutil.iter_modules(snow_arena_levels.__path__)
        if info.name.startswith("arena_")
    )
    if not names:
        raise RuntimeError("Brak map w pakiecie snow_arena_levels")
    return tuple(
        arena_from_module(importlib.import_module(f"{snow_arena_levels.__name__}.{name}"))
        for name in names
    )


def _wall_at(arena: Arena, x: float, y: float) -> bool:
    ix, iy = int(x), int(y)
    return ix < 0 or iy < 0 or ix >= arena.width or iy >= arena.height or arena.tiles[iy][ix] == "#"


class SnowArena:
    title = "SNIEZKA"

    def __init__(self, seed: Optional[int] = None, arenas: tuple[Arena, ...] | None = None) -> None:
        self.rng = random.Random(seed)
        self.arenas = arenas or load_arenas()
        self.best = 0
        self.reset()

    def reset(self) -> None:
        self.arena = self.arenas[0]
        self.player_x, self.player_y, self.angle = self.arena.spawn
        self.health = 5
        self.score = 0
        self.fire_cooldown = 0.0
        self.hit_flash = 0.0
        self.projectiles: list[Projectile] = []
        self.enemies: list[Enemy] = []
        self.status = Status.READY
        for _ in range(MAX_ACTIVE_ENEMIES):
            self._spawn_enemy()

    def update(self, dt: float, controls: InputFrame) -> None:
        if self.status in {Status.READY, Status.GAME_OVER}:
            if controls.just_pressed(Key.A) or controls.just_pressed(Key.START):
                if self.status is Status.GAME_OVER:
                    self.reset()
                self.status = Status.PLAYING
            return

        self.fire_cooldown = max(0.0, self.fire_cooldown - dt)
        self.hit_flash = max(0.0, self.hit_flash - dt)
        turn = int(controls.is_held(Key.RIGHT)) - int(controls.is_held(Key.LEFT))
        self.angle = (self.angle + turn * TURN_SPEED * dt) % (2 * math.pi)
        move = int(controls.is_held(Key.UP)) - int(controls.is_held(Key.DOWN))
        if move:
            self._move_player(
                math.cos(self.angle) * MOVE_SPEED * dt * move,
                math.sin(self.angle) * MOVE_SPEED * dt * move,
            )
        if (controls.just_pressed(Key.A) or controls.just_pressed(Key.START)) and self.fire_cooldown == 0:
            self.projectiles.append(Projectile(
                self.player_x, self.player_y,
                math.cos(self.angle) * 5.5, math.sin(self.angle) * 5.5, False,
            ))
            self.fire_cooldown = 0.34

        self._move_enemies(dt)
        self._move_projectiles(dt)
        self._resolve_hits()

    def _blocked(self, x: float, y: float, radius: float = PLAYER_RADIUS) -> bool:
        for ox in (-radius, radius):
            for oy in (-radius, radius):
                if _wall_at(self.arena, x + ox, y + oy):
                    return True
        return any(
            math.hypot(x - object_x, y - object_y) < radius + OBJECT_RADIUS[kind]
            for kind, object_x, object_y in self.arena.objects
        )

    def _move_player(self, dx: float, dy: float) -> None:
        if not self._blocked(self.player_x + dx, self.player_y):
            self.player_x += dx
        if not self._blocked(self.player_x, self.player_y + dy):
            self.player_y += dy

    def _spawn_enemy(self) -> None:
        choices = [
            point for point in self.arena.enemy_spawns
            if math.hypot(point[0] - self.player_x, point[1] - self.player_y) > 2.4
            and all(math.hypot(point[0] - enemy.x, point[1] - enemy.y) > 1.0 for enemy in self.enemies)
        ]
        x, y = self.rng.choice(choices or list(self.arena.enemy_spawns))
        self.enemies.append(Enemy(x, y, self.rng.uniform(0.8, 1.6), self.rng.random() * 6.0))

    def _move_enemies(self, dt: float) -> None:
        for enemy in self.enemies:
            dx, dy = self.player_x - enemy.x, self.player_y - enemy.y
            distance = max(0.01, math.hypot(dx, dy))
            # Przeciwnicy suną w stronę gracza, a z bliska krążą na boki.
            forward = 0.42 if distance > 2.2 else 0.0
            side = math.sin(enemy.phase) * 0.34
            enemy.phase += dt * 1.7
            step_x = (dx / distance * forward - dy / distance * side) * dt
            step_y = (dy / distance * forward + dx / distance * side) * dt
            if not self._enemy_blocked(enemy, enemy.x + step_x, enemy.y):
                enemy.x += step_x
            if not self._enemy_blocked(enemy, enemy.x, enemy.y + step_y):
                enemy.y += step_y
            enemy.fire_timer -= dt
            if enemy.fire_timer <= 0 and distance < 6.5 and self._line_clear(enemy.x, enemy.y, self.player_x, self.player_y):
                speed = 2.15
                self.projectiles.append(Projectile(enemy.x, enemy.y, dx / distance * speed, dy / distance * speed, True))
                enemy.fire_timer = self.rng.uniform(1.25, 2.1)

    def _enemy_blocked(self, current: Enemy, x: float, y: float) -> bool:
        return self._blocked(x, y, 0.22) or any(
            other is not current and math.hypot(x - other.x, y - other.y) < 0.48
            for other in self.enemies
        )

    def _line_clear(self, x1: float, y1: float, x2: float, y2: float) -> bool:
        distance = math.hypot(x2 - x1, y2 - y1)
        steps = max(1, int(distance / 0.12))
        return not any(
            _wall_at(self.arena, x1 + (x2 - x1) * i / steps, y1 + (y2 - y1) * i / steps)
            for i in range(1, steps)
        )

    def _move_projectiles(self, dt: float) -> None:
        alive: list[Projectile] = []
        for ball in self.projectiles:
            ball.x += ball.dx * dt
            ball.y += ball.dy * dt
            if not _wall_at(self.arena, ball.x, ball.y):
                alive.append(ball)
        self.projectiles = alive

    def _resolve_hits(self) -> None:
        for ball in list(self.projectiles):
            if ball.hostile:
                if math.hypot(ball.x - self.player_x, ball.y - self.player_y) < 0.27:
                    self.projectiles.remove(ball)
                    self.health -= 1
                    self.hit_flash = 0.18
                    if self.health <= 0:
                        self.best = max(self.best, self.score)
                        self.status = Status.GAME_OVER
                        return
            else:
                target = next((enemy for enemy in self.enemies if math.hypot(ball.x - enemy.x, ball.y - enemy.y) < 0.34), None)
                if target is not None:
                    self.projectiles.remove(ball)
                    self.enemies.remove(target)
                    self.score += 1
                    self.best = max(self.best, self.score)
                    self._spawn_enemy()

    def draw(self, surface: pygame.Surface) -> None:
        horizon = 65
        surface.fill((157, 207, 225))
        pygame.draw.rect(surface, (218, 235, 236), (0, horizon, WIDTH, HEIGHT - horizon))
        depths = self._draw_walls(surface, horizon)
        sprites = [(enemy.x, enemy.y, "enemy", enemy) for enemy in self.enemies]
        sprites.extend((x, y, kind, None) for kind, x, y in self.arena.objects)
        sprites.extend((ball.x, ball.y, "redball" if ball.hostile else "ball", None) for ball in self.projectiles)
        sprites.sort(key=lambda item: -math.hypot(item[0] - self.player_x, item[1] - self.player_y))
        for x, y, kind, _ in sprites:
            self._draw_sprite(surface, depths, x, y, kind, horizon)

        # Celownik, rękawica i HUD są zawsze na wierzchu świata.
        pygame.draw.line(surface, (24, 48, 57), (61, 64), (67, 64))
        pygame.draw.line(surface, (24, 48, 57), (64, 61), (64, 67))
        pygame.draw.circle(surface, (244, 247, 239), (68, 119), 11)
        pygame.draw.circle(surface, (88, 145, 180), (68, 119), 11, 2)
        pygame.draw.rect(surface, (7, 16, 24), (0, 0, WIDTH, 13))
        text(surface, f"S {self.score:02d}", 3, 2, color=COLORS.accent, size=7, bold=True)
        text(surface, f"HI {self.best:02d}", 45, 2, color=COLORS.muted, size=7)
        text(surface, "*" * self.health, 96, 2, color=(174, 224, 246), size=7, bold=True)
        if self.hit_flash > 0:
            pygame.draw.rect(surface, (210, 238, 247), (0, 13, WIDTH, HEIGHT - 13), 3)
        if self.status is Status.READY:
            self._overlay(surface, "SNIEZKA", "GORA: IDZ  A: RZUT")
        elif self.status is Status.GAME_OVER:
            self._overlay(surface, "SKUTY!", f"WYNIK {self.score}  A: GRAJ")

    def _draw_walls(self, surface: pygame.Surface, horizon: int) -> list[float]:
        depths = [99.0] * WIDTH
        for screen_x in range(0, WIDTH, 2):
            ray_angle = self.angle - FOV / 2 + (screen_x / (WIDTH - 1)) * FOV
            distance = 0.03
            while distance < 14:
                ray_x = self.player_x + math.cos(ray_angle) * distance
                ray_y = self.player_y + math.sin(ray_angle) * distance
                if _wall_at(self.arena, ray_x, ray_y):
                    break
                distance += 0.035
            corrected = max(0.12, distance * math.cos(ray_angle - self.angle))
            wall_height = min(104, int(82 / corrected))
            top = horizon - wall_height // 2
            shade = max(45, min(205, int(220 - corrected * 19)))
            color = (shade // 2, min(235, shade + 23), min(250, shade + 38))
            pygame.draw.rect(surface, color, (screen_x, top, 2, wall_height))
            if screen_x % 8 == 0:
                pygame.draw.line(surface, (color[0], max(0, color[1] - 22), max(0, color[2] - 18)), (screen_x, top), (screen_x, top + wall_height))
            depths[screen_x:min(WIDTH, screen_x + 2)] = [corrected] * min(2, WIDTH - screen_x)
        return depths

    def _draw_sprite(self, surface: pygame.Surface, depths: list[float], world_x: float, world_y: float, kind: str, horizon: int) -> None:
        dx, dy = world_x - self.player_x, world_y - self.player_y
        distance = math.hypot(dx, dy)
        relative = (math.atan2(dy, dx) - self.angle + math.pi) % (2 * math.pi) - math.pi
        if abs(relative) > FOV * 0.65 or distance < 0.08:
            return
        screen_x = int(WIDTH / 2 + math.tan(relative) / math.tan(FOV / 2) * WIDTH / 2)
        scale = min(64, max(2, int(48 / distance)))
        if kind in {"ball", "redball"}:
            scale = max(2, scale // 4)
        left, top = screen_x - scale // 2, horizon - scale // 2
        center_column = max(0, min(WIDTH - 1, screen_x))
        if distance >= depths[center_column] + 0.2:
            return
        rect = pygame.Rect(left, top, scale, scale)
        if kind == "enemy":
            pygame.draw.circle(surface, (236, 249, 250), (screen_x, top + scale // 2), scale // 3)
            pygame.draw.circle(surface, (43, 66, 74), (screen_x - scale // 9, top + scale // 2), max(1, scale // 18))
            pygame.draw.circle(surface, (43, 66, 74), (screen_x + scale // 9, top + scale // 2), max(1, scale // 18))
            pygame.draw.polygon(surface, (235, 111, 60), ((screen_x, top + scale // 2), (screen_x + scale // 4, top + scale * 3 // 5), (screen_x, top + scale * 2 // 3)))
            pygame.draw.rect(surface, (194, 51, 67), (left + scale // 5, top + scale // 6, scale * 3 // 5, max(2, scale // 7)))
        elif kind == "snowman":
            pygame.draw.circle(surface, (246, 250, 247), (screen_x, top + scale * 2 // 3), scale // 3)
            pygame.draw.circle(surface, (246, 250, 247), (screen_x, top + scale // 3), scale // 4)
            pygame.draw.rect(surface, (33, 48, 53), (left + scale // 4, top + scale // 10, scale // 2, max(2, scale // 9)))
        elif kind == "igloo":
            pygame.draw.ellipse(surface, (191, 225, 235), rect)
            pygame.draw.rect(surface, (91, 145, 164), (screen_x - scale // 7, top + scale * 2 // 3, scale // 3, scale // 3))
        elif kind == "sled":
            pygame.draw.line(surface, (113, 57, 35), (left, top + scale * 3 // 4), (left + scale, top + scale * 3 // 4), max(1, scale // 10))
            pygame.draw.line(surface, (207, 64, 50), (left + scale // 5, top + scale // 3), (left + scale * 4 // 5, top + scale * 2 // 3), max(2, scale // 6))
        else:
            color = (236, 249, 250) if kind == "ball" else (130, 210, 239)
            pygame.draw.circle(surface, color, rect.center, max(1, scale // 2))

    @staticmethod
    def _overlay(surface: pygame.Surface, heading: str, hint: str) -> None:
        rect = pygame.Rect(8, 42, 112, 38)
        pygame.draw.rect(surface, (7, 16, 24), rect)
        pygame.draw.rect(surface, (91, 169, 197), rect, 1)
        text(surface, heading, WIDTH // 2, 47, color=COLORS.text, size=12, center=True, bold=True)
        text(surface, hint, WIDTH // 2, 66, color=(174, 224, 246), size=7, center=True)
