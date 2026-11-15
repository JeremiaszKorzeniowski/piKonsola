from pikonsola.games.tanks import Bullet, Status, Tanks
from pikonsola.input import InputFrame, Key


def press(key: Key) -> InputFrame:
    return InputFrame(pressed={key}, held={key})


def test_game_starts_with_a() -> None:
    game = Tanks(seed=1)
    game.update(0, press(Key.A))
    assert game.status is Status.PLAYING


def test_player_moves_and_turns() -> None:
    game = Tanks(seed=1)
    game.update(0, press(Key.A))
    start_y = game.player.y
    game.update(0.1, InputFrame(held={Key.UP}))
    assert game.player.y < start_y
    assert game.player.direction == "up"


def test_player_can_shoot_in_facing_direction() -> None:
    game = Tanks(seed=1)
    game.update(0, press(Key.A))
    game.player.direction = "left"
    game.update(0, press(Key.A))
    assert len(game.bullets) == 1
    assert game.bullets[0].friendly
    assert game.bullets[0].dx == -1


def test_bullet_destroys_breakable_wall() -> None:
    game = Tanks(seed=1)
    wall = next(wall for wall in game.walls if wall.breakable)
    game.bullets = [Bullet(float(wall.x), float(wall.y), 1, 0, True)]
    game._resolve_bullets()
    assert wall not in game.walls
    assert not game.bullets


def test_player_bullet_destroys_enemy_and_scores() -> None:
    game = Tanks(seed=1)
    enemy = game.enemies[0]
    game.bullets = [Bullet(enemy.x + 3, enemy.y + 3, 0, -1, True)]
    game._resolve_bullets()
    assert enemy not in game.enemies
    assert game.score == 100


def test_destroying_all_enemies_wins() -> None:
    game = Tanks(seed=1)
    game.update(0, press(Key.A))
    game.enemies.clear()
    game.update(0, InputFrame())
    assert game.status is Status.WON


def test_enemy_bullet_can_destroy_base() -> None:
    game = Tanks(seed=1)
    game.update(0, press(Key.A))
    game.bullets = [Bullet(float(game.base_rect.x), float(game.base_rect.y), 0, 1, False)]
    game._resolve_bullets()
    assert game.status is Status.GAME_OVER
