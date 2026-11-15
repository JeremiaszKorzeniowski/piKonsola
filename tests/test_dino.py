from pikonsola.games.dino import DINO_HEIGHT, DINO_X, GROUND_Y, Dino, Obstacle, Status
from pikonsola.input import InputFrame, Key


def press(key: Key) -> InputFrame:
    return InputFrame(pressed={key}, held={key})


def test_a_starts_game_with_a_jump() -> None:
    game = Dino(seed=1)
    game.update(0, press(Key.A))
    assert game.status is Status.PLAYING
    assert game.velocity_y < 0


def test_dino_lands_after_jump() -> None:
    game = Dino(seed=1)
    game.update(0, press(Key.UP))
    for _ in range(60):
        game.update(1 / 30, InputFrame())
    assert game.on_ground
    assert game.dino_y == GROUND_Y - DINO_HEIGHT


def test_world_moves_and_score_increases() -> None:
    game = Dino(seed=1)
    game.status = Status.PLAYING
    game.obstacles = [Obstacle(100.0, 6, 15)]
    game.spawn_distance = 999.0
    game.update(0.1, InputFrame())
    assert game.obstacles[0].x < 100.0
    assert game.score > 0


def test_cactus_collision_ends_game() -> None:
    game = Dino(seed=1)
    game.status = Status.PLAYING
    game.obstacles = [Obstacle(float(DINO_X + 2), 7, 18)]
    game.spawn_distance = 999.0
    game.update(0.01, InputFrame())
    assert game.status is Status.GAME_OVER


def test_restart_keeps_best_score() -> None:
    game = Dino(seed=1)
    game.score = 42
    game.best = 42
    game.status = Status.GAME_OVER
    game.update(0, press(Key.START))
    assert game.status is Status.PLAYING
    assert game.score == 0
    assert game.best == 42
