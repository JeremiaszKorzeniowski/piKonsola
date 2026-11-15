import math

import pygame

from pikonsola.games.asteroids import Asteroid, Asteroids, Bullet, Status
from pikonsola.input import InputFrame, Key


def press(key: Key) -> InputFrame:
    return InputFrame(pressed={key}, held={key})


def test_game_starts_with_a_and_four_large_asteroids() -> None:
    game = Asteroids(seed=1)
    assert len(game.asteroids) == 4
    assert all(asteroid.size == 3 for asteroid in game.asteroids)
    game.update(0, press(Key.A))
    assert game.status is Status.PLAYING


def test_ship_turns_thrusts_and_wraps_around_screen() -> None:
    game = Asteroids(seed=1)
    game.update(0, press(Key.A))
    game.update(0.1, InputFrame(held={Key.RIGHT, Key.UP}))
    assert game.ship.angle > 0
    assert math.hypot(game.ship.vx, game.ship.vy) > 0
    game.ship.x = 129
    game.ship.y = 129
    game.update(0, InputFrame())
    assert 0 <= game.ship.x < 128
    assert 18 <= game.ship.y < 128


def test_ship_can_fire_in_facing_direction() -> None:
    game = Asteroids(seed=1)
    game.update(0, press(Key.A))
    game.invulnerable = 0
    game.update(0, press(Key.A))
    assert len(game.bullets) == 1
    assert game.bullets[0].vy < 0


def test_large_asteroid_splits_and_scores() -> None:
    game = Asteroids(seed=1)
    target = Asteroid(30, 40, 10, 0, 3)
    game.asteroids = [target]
    game.bullets = [Bullet(30, 40, 0, 0)]
    game._resolve_collisions()
    assert game.score == 20
    assert len(game.asteroids) == 2
    assert all(asteroid.size == 2 for asteroid in game.asteroids)


def test_small_asteroid_is_destroyed_without_splitting() -> None:
    game = Asteroids(seed=1)
    game.asteroids = [Asteroid(30, 40, 0, 0, 1)]
    game.bullets = [Bullet(30, 40, 0, 0)]
    game._resolve_collisions()
    assert game.score == 100
    assert not game.asteroids


def test_ship_collision_costs_a_life_and_grants_invulnerability() -> None:
    game = Asteroids(seed=1)
    game.status = Status.PLAYING
    game.invulnerable = 0
    game.asteroids = [Asteroid(game.ship.x, game.ship.y, 0, 0, 3)]
    game._resolve_collisions()
    assert game.lives == 2
    assert game.invulnerable == 2.0


def test_empty_field_starts_a_harder_wave() -> None:
    game = Asteroids(seed=1)
    game.update(0, press(Key.A))
    game.asteroids.clear()
    game.update(0, InputFrame())
    assert game.wave == 2
    assert len(game.asteroids) == 5


def test_game_draws_ready_and_playing_frames() -> None:
    pygame.font.init()
    game = Asteroids(seed=1)
    surface = pygame.Surface((128, 128))
    game.draw(surface)
    game.update(0, press(Key.A))
    game.draw(surface)
    assert surface.get_size() == (128, 128)
