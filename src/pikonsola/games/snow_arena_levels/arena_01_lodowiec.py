"""Prosta, zamknięta arena z kilkoma korytarzami."""

LEVEL = {
    "name": "LODOWIEC",
    "map": (
        "############",
        "#..........#",
        "#..##......#",
        "#..#.......#",
        "#..#..##...#",
        "#.....#....#",
        "#.....#....#",
        "#..##......#",
        "#..........#",
        "#......##..#",
        "#..........#",
        "############",
    ),
    "spawn": (1.6, 1.6, 0.0),
    "enemy_spawns": ((9.5, 2.0), (9.5, 8.5), (2.0, 9.5), (5.0, 5.5)),
    # Każda dekoracja jest jednocześnie stałą przeszkodą.
    "objects": (
        ("snowman", 5.3, 2.2),
        ("igloo", 8.3, 5.6),
        ("sled", 3.2, 8.7),
        ("snowman", 9.7, 9.6),
    ),
}
