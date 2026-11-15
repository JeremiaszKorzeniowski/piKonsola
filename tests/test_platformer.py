import pygame

from pikonsola.games.platformer import Platformer, Status, load_levels
from pikonsola.input import InputFrame, Key


def press(key: Key) -> InputFrame:
    return InputFrame(pressed={key}, held={key})


def test_three_levels_are_loaded_from_separate_modules() -> None:
    levels = load_levels()
    assert [level.name for level in levels] == ["LAKA", "RUINY", "NOC"]
    assert all(level.width >= 3 * 128 for level in levels)


def test_player_moves_left_and_right_but_not_without_input() -> None:
    game = Platformer()
    game.update(0, press(Key.A))
    start_x = game.player_x
    game.update(0.1, InputFrame())
    assert game.player_x == start_x
    game.update(0.1, InputFrame(held={Key.RIGHT}))
    assert game.player_x > start_x
    moved_right = game.player_x
    game.update(0.1, InputFrame(held={Key.LEFT}))
    assert game.player_x < moved_right


def test_player_jumps_with_a() -> None:
    game = Platformer()
    game.update(0, press(Key.A))
    game.update(0, press(Key.A))
    assert game.velocity_y < 0


def test_key_opens_door_and_advances_level() -> None:
    game = Platformer()
    game.status = Status.PLAYING
    game.player_x, game.player_y = game.level.key
    game._resolve_entities()
    assert game.has_key
    game.player_x, game.player_y = game.level.door
    game._resolve_entities()
    assert game.status is Status.LEVEL_COMPLETE
    game.update(1.1, InputFrame())
    assert game.level_index == 1
    assert game.status is Status.PLAYING


def test_door_stays_closed_without_key() -> None:
    game = Platformer()
    game.status = Status.PLAYING
    game.player_x, game.player_y = game.level.door
    game._resolve_entities()
    assert game.status is Status.PLAYING
    assert game.player_rect.right <= game.door_rect.left


def test_enemy_collision_costs_one_of_three_lives() -> None:
    game = Platformer()
    game.status = Status.PLAYING
    enemy = game.enemies[0]
    game.player_x, game.player_y = enemy.x, enemy.y
    game._resolve_entities()
    assert game.lives == 2
    assert game.status is Status.PLAYING


def test_three_hits_end_game() -> None:
    game = Platformer()
    game.status = Status.PLAYING
    for expected in (2, 1, 0):
        game.invulnerable = 0
        enemy = game.enemies[0]
        game.player_x, game.player_y = enemy.x, enemy.y
        game._resolve_entities()
        assert game.lives == expected
    assert game.status is Status.GAME_OVER


def test_every_gap_is_shorter_than_same_height_jump_range() -> None:
    # Zasięg skoku to ok. 25 px. Mapy zachowują zapas na krawędzie postaci.
    for level in load_levels():
        # Niskie stopnie (do 12 px) również są częścią głównej trasy.
        ground = sorted(rect for rect in level.platforms if rect[1] >= 104)
        for left, right in zip(ground, ground[1:]):
            gap = right[0] - (left[0] + left[2])
            assert gap <= 18, f"{level.name}: luka {gap}px jest za szeroka"
        assert ground[0][0] <= level.spawn[0]
        assert ground[-1][0] + ground[-1][2] >= level.door[0]


def test_every_level_has_reachable_raised_platforms() -> None:
    for level in load_levels():
        raised = [rect for rect in level.platforms if rect[1] < 104]
        assert raised, level.name
        assert all(116 - rect[1] <= 22 for rect in raised), level.name
        assert any(
            rect[0] <= level.key[0] < rect[0] + rect[2]
            and level.key[1] + 8 <= rect[1]
            for rect in raised
        ), level.name


def test_first_key_platform_can_be_reached_from_the_ground() -> None:
    game = Platformer()
    game.status = Status.PLAYING
    game.enemies = []
    game.player_x = 106
    game.player_y = 106
    game.on_ground = True
    for frame in range(90):
        controls = InputFrame(held={Key.RIGHT})
        if frame == 0:
            controls.pressed.add(Key.A)
        game.update(1 / 60, controls)
        if game.has_key:
            break
    assert game.has_key


def test_every_level_can_be_finished_with_right_and_jump() -> None:
    """Prosty automat przechodzi mapy, używając ruchu w prawo i skoku."""
    for index, _ in enumerate(load_levels()):
        game = Platformer()
        game._load_level(index)
        # Przeciwnicy mają osobny test kolizji; tu sprawdzamy geometrię trasy.
        game.enemies = []
        game.status = Status.PLAYING
        starting_lives = game.lives
        hits = []

        for _frame in range(1800):
            jump = False
            if game.on_ground:
                player = game.player_rect
                nearby_obstacles = [rect[0] for rect in game.level.hazards]
                nearby_obstacles.extend(enemy.rect.left for enemy in game.enemies)
                jump = any(
                    0 <= threat - player.right <= 8
                    for threat in nearby_obstacles
                )

                supporting = [
                    rect for rect in game.level.platforms
                    if abs(player.bottom - rect[1]) <= 1
                    and rect[1] >= 104
                    and player.right > rect[0]
                    and player.left < rect[0] + rect[2]
                ]
                if supporting:
                    edge = max(rect[0] + rect[2] for rect in supporting)
                    next_surfaces = [rect for rect in game.level.platforms if rect[0] >= edge]
                    if next_surfaces and min(rect[0] for rect in next_surfaces) > edge:
                        jump = jump or 0 <= edge - player.right <= 2

                key_platforms = [
                    rect for rect in game.level.platforms
                    if rect[1] < 104
                    and rect[0] <= game.level.key[0] < rect[0] + rect[2]
                ]
                jump = jump or any(
                    0 <= rect[0] - player.right <= 12
                    for rect in key_platforms
                )

            before_lives = game.lives
            before_position = (round(game.player_x), round(game.player_y))
            controls = InputFrame(held={Key.RIGHT})
            if jump:
                controls.pressed.add(Key.A)
                controls.held.add(Key.A)
            game.update(1 / 60, controls)
            if game.lives < before_lives:
                hits.append(before_position)
            if game.status is Status.LEVEL_COMPLETE:
                break

        assert game.status is Status.LEVEL_COMPLETE, (
            game.level.name, hits, round(game.player_x), round(game.player_y), game.has_key
        )
        assert game.has_key, game.level.name
        assert game.lives == starting_lives, game.level.name


def test_game_draws_all_states() -> None:
    pygame.font.init()
    surface = pygame.Surface((128, 128))
    game = Platformer()
    for status in Status:
        game.status = status
        game.draw(surface)
