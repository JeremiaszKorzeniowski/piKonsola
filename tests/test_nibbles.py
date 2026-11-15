from pikonsola.games.nibbles import Nibbles, Status
from pikonsola.input import InputFrame, Key


def press(key: Key) -> InputFrame:
    return InputFrame(pressed={key}, held={key})


def test_game_starts_with_a() -> None:
    game = Nibbles(seed=1)
    game.update(0, press(Key.A))
    assert game.status is Status.PLAYING


def test_snake_moves_one_cell() -> None:
    game = Nibbles(seed=1)
    game.update(0, press(Key.A))
    old_head = game.snake[0]
    game.update(0.14, InputFrame())
    assert game.snake[0] == (old_head[0] + 1, old_head[1])


def test_snake_cannot_reverse() -> None:
    game = Nibbles(seed=1)
    game.update(0, press(Key.A))
    game.update(0, press(Key.LEFT))
    game.update(0.14, InputFrame())
    assert game.direction == (1, 0)


def test_wall_causes_game_over() -> None:
    game = Nibbles(seed=1)
    game.update(0, press(Key.A))
    for _ in range(20):
        game.update(0.14, InputFrame())
    assert game.status is Status.GAME_OVER
