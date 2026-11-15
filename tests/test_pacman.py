from collections import deque

from pikonsola.games.pacman import FLOOR, MAZE, Pacman, Status
from pikonsola.input import InputFrame, Key


def press(key: Key) -> InputFrame:
    return InputFrame(pressed={key}, held={key})


def test_maze_is_small_and_all_floor_is_connected() -> None:
    assert len(MAZE) == 13
    assert all(len(row) == 15 for row in MAZE)
    seen = {next(iter(FLOOR))}
    queue = deque(seen)
    while queue:
        x, y = queue.popleft()
        for neighbor in (((x - 1) % 15, y), ((x + 1) % 15, y), (x, y - 1), (x, y + 1)):
            if neighbor in FLOOR and neighbor not in seen:
                seen.add(neighbor)
                queue.append(neighbor)
    assert seen == FLOOR


def test_game_starts_and_player_eats_pellet() -> None:
    game = Pacman(seed=1)
    game.update(0, press(Key.A))
    game.player = (1, 1)
    game.direction = (1, 0)
    game.next_direction = (1, 0)
    assert (2, 1) in game.pellets
    game.update(0.14, InputFrame())
    assert game.player == (2, 1)
    assert game.score == 10


def test_ghosts_move_slower_than_player() -> None:
    game = Pacman(seed=1)
    game.update(0, press(Key.A))
    game.player = (1, 1)
    game.direction = (1, 0)
    game.next_direction = (1, 0)
    ghosts = [ghost.position for ghost in game.ghosts]
    game.update(0.14, InputFrame())
    assert game.player == (2, 1)
    assert [ghost.position for ghost in game.ghosts] == ghosts


def test_losing_all_lives_ends_game() -> None:
    game = Pacman(seed=1)
    game.update(0, press(Key.A))
    game.lives = 1
    game.ghosts[0].position = game.player
    game._resolve_collisions()
    assert game.status is Status.GAME_OVER
