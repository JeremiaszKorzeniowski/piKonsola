import pygame

from pikonsola.games.arkanoid import (
    BALL_RADIUS,
    BRICK_COLUMNS,
    BRICK_ROWS,
    PADDLE_WIDTH,
    PADDLE_Y,
    Arkanoid,
    Status,
)
from pikonsola.input import InputFrame, Key


def press(key: Key) -> InputFrame:
    return InputFrame(pressed={key}, held={key})


def test_game_starts_with_a_full_wall_and_three_lives() -> None:
    game = Arkanoid()
    assert game.status is Status.READY
    assert len(game.bricks) == BRICK_ROWS * BRICK_COLUMNS
    assert game.lives == 3


def test_paddle_moves_and_ball_follows_before_launch() -> None:
    game = Arkanoid()
    old_x = game.paddle_x
    game.update(0.1, InputFrame(held={Key.RIGHT}))
    assert game.paddle_x > old_x
    assert game.ball.x == game.paddle_x + PADDLE_WIDTH / 2


def test_a_launches_ball_upward() -> None:
    game = Arkanoid()
    game.update(0, press(Key.A))
    assert game.status is Status.PLAYING
    assert game.ball.vy < 0


def test_ball_bounces_from_side_wall() -> None:
    game = Arkanoid()
    game.status = Status.PLAYING
    game.ball.x = BALL_RADIUS
    game.ball.y = 90
    game.ball.vx = -50
    game.ball.vy = -10
    game.update(0.02, InputFrame())
    assert game.ball.vx > 0


def test_paddle_changes_bounce_angle() -> None:
    game = Arkanoid()
    game.status = Status.PLAYING
    game.ball.x = game.paddle_x + PADDLE_WIDTH - 2
    game.ball.y = PADDLE_Y - BALL_RADIUS - 0.1
    game.ball.vx = 0
    game.ball.vy = 50
    game.update(0.01, InputFrame())
    assert game.ball.vy < 0
    assert game.ball.vx > 0


def test_brick_hit_removes_brick_and_scores_by_row() -> None:
    game = Arkanoid()
    brick = game.bricks[0]
    game.bricks = [brick, game.bricks[-1]]
    game.status = Status.PLAYING
    game.ball.x = brick.rect.centerx
    game.ball.y = brick.rect.bottom + BALL_RADIUS + 0.5
    game.ball.vx = 0
    game.ball.vy = -50
    game.update(0.02, InputFrame())
    assert brick not in game.bricks
    assert game.score == BRICK_ROWS * 10


def test_missing_three_balls_ends_game() -> None:
    game = Arkanoid()
    for expected_lives in (2, 1, 0):
        game.status = Status.PLAYING
        game.ball.y = 131
        game.ball.vy = 50
        game._step_ball(0)
        assert game.lives == expected_lives
    assert game.status is Status.GAME_OVER


def test_last_brick_starts_next_level() -> None:
    game = Arkanoid()
    brick = game.bricks[0]
    game.bricks = [brick]
    game.status = Status.PLAYING
    game.ball.x = brick.rect.centerx
    game.ball.y = brick.rect.bottom + BALL_RADIUS + 0.5
    game.ball.vx = 0
    game.ball.vy = -50
    game.update(0.02, InputFrame())
    assert game.level == 2
    assert game.status is Status.READY
    assert len(game.bricks) == BRICK_ROWS * BRICK_COLUMNS


def test_game_draws_all_states() -> None:
    pygame.font.init()
    surface = pygame.Surface((128, 128))
    game = Arkanoid()
    game.draw(surface)
    game.update(0, press(Key.A))
    game.draw(surface)
    game.status = Status.GAME_OVER
    game.draw(surface)
    assert surface.get_size() == (128, 128)
