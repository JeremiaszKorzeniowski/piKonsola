import pygame

from pikonsola.games.tetris import BOARD_HEIGHT, BOARD_WIDTH, Piece, Status, Tetris
from pikonsola.input import InputFrame, Key


def press(key: Key) -> InputFrame:
    return InputFrame(pressed={key}, held={key})


def test_game_starts_with_a() -> None:
    game = Tetris(seed=1)
    game.update(0, press(Key.A))
    assert game.status is Status.PLAYING


def test_board_has_classic_dimensions() -> None:
    game = Tetris(seed=1)
    assert len(game.board) == BOARD_HEIGHT
    assert all(len(row) == BOARD_WIDTH for row in game.board)


def test_piece_moves_left() -> None:
    game = Tetris(seed=1)
    game.update(0, press(Key.A))
    start_x = game.active.x
    game.update(0, press(Key.LEFT))
    assert game.active.x == start_x - 1


def test_piece_rotates_with_up() -> None:
    game = Tetris(seed=3)
    game.update(0, press(Key.A))
    game.active = Piece("T", x=3, y=2)
    game.update(0, press(Key.UP))
    assert game.active.rotation == 1


def test_hard_drop_locks_piece_and_spawns_next() -> None:
    game = Tetris(seed=2)
    game.update(0, press(Key.A))
    first_kind = game.active.kind
    expected_next = game.next_kind
    game.update(0, press(Key.B))
    assert game.active.kind == expected_next
    assert any(first_kind in row for row in game.board)


def test_full_line_is_cleared_and_scored() -> None:
    game = Tetris(seed=1)
    game.status = Status.PLAYING
    game.board[-1] = ["J"] * BOARD_WIDTH
    game.board[-1][4:6] = [None, None]
    game.active = Piece("O", x=3, y=18)
    game._lock_piece()
    assert game.lines == 1
    assert game.score == 100
    assert all(cell is None for cell in game.board[0])


def test_locking_above_board_ends_game() -> None:
    game = Tetris(seed=1)
    game.status = Status.PLAYING
    game.active = Piece("O", x=3, y=-1)
    game._lock_piece()
    assert game.status is Status.GAME_OVER


def test_game_draws_at_console_resolution() -> None:
    pygame.font.init()
    game = Tetris(seed=1)
    surface = pygame.Surface((128, 128))
    game.draw(surface)
    assert surface.get_size() == (128, 128)
