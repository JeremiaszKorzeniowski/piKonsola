from pikonsola.games.river import Bullet, River, RiverObject, Status
from pikonsola.input import InputFrame, Key


def press(key: Key) -> InputFrame:
    return InputFrame(pressed={key}, held={key})


def test_game_starts_with_a() -> None:
    game = River(seed=1)
    game.update(0, press(Key.A))
    assert game.status is Status.PLAYING


def test_player_moves_but_stays_inside_river() -> None:
    game = River(seed=1)
    game.update(0, press(Key.A))
    start = game.player_x
    game.update(0.1, InputFrame(held={Key.RIGHT}))
    assert game.player_x > start
    game.update(10, InputFrame(held={Key.RIGHT, Key.DOWN}))
    assert game.player_x <= 97
    assert game.player_y <= 115


def test_player_can_shoot() -> None:
    game = River(seed=1)
    game.update(0, press(Key.A))
    game.update(0, press(Key.A))
    assert len(game.bullets) == 1


def test_bullet_destroys_boat_and_scores() -> None:
    game = River(seed=1)
    game.update(0, press(Key.A))
    target = RiverObject(50, 50, "boat")
    game.objects = [target]
    game.bullets = [Bullet(53, 53)]
    game._resolve_collisions()
    assert target not in game.objects
    assert game.score == 20


def test_fuel_is_collected_without_losing_life() -> None:
    game = River(seed=1)
    game.update(0, press(Key.A))
    game.objects = [RiverObject(game.player_x + 2, game.player_y, "fuel")]
    game._resolve_collisions()
    assert game.objects == []
    assert game.score == 25
    assert game.lives == 3


def test_three_crashes_end_game() -> None:
    game = River(seed=1)
    game.update(0, press(Key.A))
    for expected_lives in (2, 1, 0):
        game.invulnerable = 0
        game.objects = [RiverObject(game.player_x, game.player_y, "rock")]
        game._resolve_collisions()
        assert game.lives == expected_lives
    assert game.status is Status.GAME_OVER
