from collections import deque

import pygame

from pikonsola.games.sokoban import Sokoban, Status, load_levels
from pikonsola.input import InputFrame, Key


def press(key: Key) -> InputFrame:
    return InputFrame(pressed={key}, held={key})


def test_three_levels_are_loaded_from_subdirectory() -> None:
    levels = load_levels()
    assert [level.name for level in levels] == ["MAGAZYN", "ZAKRET", "3 PACZKI"]
    assert all(len(level.crates) == len(level.goals) for level in levels)


def test_player_pushes_crate_but_not_two_crates_or_wall() -> None:
    game = Sokoban()
    game.status = Status.PLAYING
    game.player = (2, 4)
    assert game._move((0, -1))
    assert (2, 2) in game.crates

    game.restart_level()
    game.player = (4, 3)
    assert not game._move((-1, 0))
    assert game.player == (4, 3)


def test_b_restarts_current_level() -> None:
    game = Sokoban()
    game.status = Status.PLAYING
    game._move((0, 1))
    game.update(0, press(Key.B))
    assert game.player == game.level.player
    assert game.crates == set(game.level.crates)
    assert game.moves == 0


def test_completing_level_advances_and_last_level_wins() -> None:
    game = Sokoban()
    game.status = Status.PLAYING
    game.crates = set(game.level.goals)
    game.crates.remove((2, 2))
    game.crates.add((2, 3))
    game.player = (2, 4)
    assert game._move((0, -1))
    assert game.status is Status.LEVEL_COMPLETE
    game.update(0.8, InputFrame())
    assert game.level_index == 1
    assert game.status is Status.PLAYING

    game._load_level(len(game.levels) - 1)
    game.status = Status.LEVEL_COMPLETE
    game.transition_time = 0
    game.update(0, InputFrame())
    assert game.status is Status.WON


def _is_solvable(level) -> bool:
    start = (level.player, level.crates)
    queue = deque([start])
    visited = {start}
    while queue:
        player, frozen_crates = queue.popleft()
        crates = set(frozen_crates)
        if crates == set(level.goals):
            return True
        for dx, dy in ((0, -1), (0, 1), (-1, 0), (1, 0)):
            target = (player[0] + dx, player[1] + dy)
            if target in level.walls:
                continue
            moved_crates = crates
            if target in crates:
                beyond = (target[0] + dx, target[1] + dy)
                if beyond in level.walls or beyond in crates:
                    continue
                moved_crates = set(crates)
                moved_crates.remove(target)
                moved_crates.add(beyond)
            state = (target, frozenset(moved_crates))
            if state not in visited:
                visited.add(state)
                queue.append(state)
    return False


def test_every_level_is_solvable() -> None:
    for level in load_levels():
        assert _is_solvable(level), level.name


def test_game_draws_all_states() -> None:
    pygame.font.init()
    surface = pygame.Surface((128, 128))
    game = Sokoban()
    for status in Status:
        game.status = status
        game.draw(surface)
