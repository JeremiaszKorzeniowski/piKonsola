import pygame

from pikonsola.games.defender import Bullet, Defender, Enemy, Status, WORLD_WIDTH
from pikonsola.input import InputFrame, Key


def press(key: Key) -> InputFrame:
    return InputFrame(pressed={key}, held={key})


def test_game_starts_with_people_and_landers() -> None:
    game = Defender(seed=1)
    assert len(game.humans) == 7
    assert len(game.enemies) == 4
    game.update(0, press(Key.A))
    assert game.status is Status.PLAYING


def test_ship_moves_in_four_directions_and_world_wraps() -> None:
    game = Defender(seed=1)
    game.update(0, press(Key.A))
    start_y = game.ship.y
    game.ship.x = WORLD_WIDTH - 1
    game.update(0.1, InputFrame(held={Key.RIGHT, Key.UP}))
    assert game.ship.x < 10
    assert game.ship.y < start_y
    assert game.ship.direction == 1


def test_ship_fires_in_facing_direction() -> None:
    game = Defender(seed=1)
    game.update(0, press(Key.A))
    game.ship.direction = -1
    game.update(0, press(Key.A))
    assert len(game.bullets) == 1
    assert game.bullets[0].vx < 0


def test_bullet_destroys_lander_and_scores() -> None:
    game = Defender(seed=1)
    enemy = Enemy(100, 50)
    game.enemies = [enemy]
    game.bullets = [Bullet(100, 50, 0)]
    game._resolve_collisions()
    assert not game.enemies
    assert game.score == 100


def test_shooting_abductor_rescues_human() -> None:
    game = Defender(seed=1)
    human = game.humans[0]
    enemy = Enemy(human.x, 45, carrying=human)
    human.carrier = enemy
    human.y = 50
    game.enemies = [enemy]
    game._destroy_enemy(enemy)
    assert human.alive
    assert human.carrier is None
    assert human.y == game._terrain_y(human.x) - 5
    assert game.score == 350


def test_completed_wave_spawns_more_enemies() -> None:
    game = Defender(seed=1)
    game.update(0, press(Key.A))
    game.enemies.clear()
    game.update(0, InputFrame())
    assert game.wave == 2
    assert len(game.enemies) == 7


def test_three_collisions_end_game() -> None:
    game = Defender(seed=1)
    game.status = Status.PLAYING
    for expected in (2, 1, 0):
        game.invulnerable = 0
        game.enemies = [Enemy(game.ship.x, game.ship.y)]
        game._resolve_collisions()
        assert game.lives == expected
    assert game.status is Status.GAME_OVER


def test_game_draws_ready_and_playing_frames() -> None:
    pygame.font.init()
    game = Defender(seed=1)
    surface = pygame.Surface((128, 128))
    game.draw(surface)
    game.update(0, press(Key.A))
    game.draw(surface)
    assert surface.get_size() == (128, 128)
