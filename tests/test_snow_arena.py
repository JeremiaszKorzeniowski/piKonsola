import math

import pygame

from pikonsola.games.snow_arena import MAX_ACTIVE_ENEMIES, Projectile, SnowArena, Status, load_arenas
from pikonsola.input import InputFrame, Key


def press(key: Key) -> InputFrame:
    return InputFrame(pressed={key}, held={key})


def test_arena_is_loaded_from_subpackage_and_closed() -> None:
    arena = load_arenas()[0]
    assert arena.name == "LODOWIEC"
    assert all(char == "#" for char in arena.tiles[0] + arena.tiles[-1])
    assert all(row[0] == "#" and row[-1] == "#" for row in arena.tiles)
    assert {kind for kind, _, _ in arena.objects} == {"snowman", "igloo", "sled"}


def test_game_starts_with_two_moving_enemies() -> None:
    game = SnowArena(seed=1)
    assert len(game.enemies) == MAX_ACTIVE_ENEMIES
    before = [(enemy.x, enemy.y) for enemy in game.enemies]
    game.update(0, press(Key.A))
    game.update(0.5, InputFrame())
    assert [(enemy.x, enemy.y) for enemy in game.enemies] != before


def test_player_moves_and_turns_in_first_person() -> None:
    game = SnowArena(seed=1)
    game.update(0, press(Key.A))
    start = (game.player_x, game.player_y, game.angle)
    game.update(0.1, InputFrame(held={Key.UP, Key.RIGHT}))
    assert (game.player_x, game.player_y) != start[:2]
    assert game.angle != start[2]


def test_decorations_block_player() -> None:
    game = SnowArena(seed=1)
    _, object_x, object_y = game.arena.objects[0]
    game.player_x, game.player_y = object_x - 0.55, object_y
    before = game.player_x
    game._move_player(0.35, 0)
    assert game.player_x == before


def test_hit_enemy_scores_and_immediately_respawns_replacement() -> None:
    game = SnowArena(seed=2)
    game.status = Status.PLAYING
    target = game.enemies[0]
    old_ids = {id(enemy) for enemy in game.enemies}
    game.projectiles = [Projectile(target.x, target.y, 0, 0, False)]
    game._resolve_hits()
    assert game.score == 1
    assert len(game.enemies) == MAX_ACTIVE_ENEMIES
    assert any(id(enemy) not in old_ids for enemy in game.enemies)


def test_five_enemy_hits_freeze_player_and_end_game() -> None:
    game = SnowArena(seed=3)
    game.status = Status.PLAYING
    for remaining in range(4, -1, -1):
        game.projectiles = [Projectile(game.player_x, game.player_y, 0, 0, True)]
        game._resolve_hits()
        assert game.health == remaining
    assert game.status is Status.GAME_OVER


def test_throw_uses_view_direction() -> None:
    game = SnowArena(seed=4)
    game.update(0, press(Key.A))
    game.angle = math.pi / 2
    game.update(0, press(Key.A))
    own = next(ball for ball in game.projectiles if not ball.hostile)
    assert abs(own.dx) < 0.01
    assert own.dy > 0


def test_game_draws_every_state() -> None:
    pygame.font.init()
    surface = pygame.Surface((128, 128))
    game = SnowArena(seed=5)
    for status in Status:
        game.status = status
        game.draw(surface)
