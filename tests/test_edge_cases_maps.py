"""Regression tests over the hand-crafted edge-case maps.

Each map in maps/edge_cases/ documents, in its header comment, exactly
which outcome it should produce. This test file locks that contract in
so a future change can't silently break edge-case handling.
"""

from fly_in.engine import Scheduler, SimulationError
from fly_in.parser import MapParser, ParseError

# filename -> expected outcome:
#   "parse_error"      -> MapParser().parse() must raise ParseError
#   "simulation_error" -> parses fine, Scheduler().solve() must raise
#   <int>               -> parses fine and must solve in exactly N turns
EXPECTATIONS: dict[str, str | int] = {
    "01_start_equals_end_name.txt": "parse_error",
    "02_start_end_adjacent.txt": 2,
    "03_zero_drones.txt": "parse_error",
    "04_negative_drones.txt": "parse_error",
    "05_no_connections_at_all.txt": "simulation_error",
    "06_disconnected_end.txt": "simulation_error",
    "07_self_loop_connection.txt": "parse_error",
    "08_duplicate_zone_name.txt": "parse_error",
    "09_unknown_zone_in_connection.txt": "parse_error",
    "10_malformed_metadata_brackets.txt": "parse_error",
    "11_invalid_zone_type.txt": "parse_error",
    "12_duplicate_connection_reversed.txt": "parse_error",
    "13_nb_drones_declared_late.txt": "parse_error",
    "14_negative_coordinates.txt": 2,
    "15_zero_and_negative_capacity.txt": "parse_error",
    "16_back_to_back_restricted.txt": 5,
    "17_single_capacity_bottleneck_many_drones.txt": 11,
    "18_high_capacity_no_bottleneck.txt": 2,
    "19_forced_long_detour_around_blocked.txt": 6,
    "20_unreachable_due_to_full_blockade.txt": "simulation_error",
}

EDGE_CASES_DIR = "maps/edge_cases"


def test_all_edge_case_files_are_covered() -> None:
    """Every file on disk has an expectation, and vice versa."""
    import os
    on_disk = set(os.listdir(EDGE_CASES_DIR))
    assert on_disk == set(EXPECTATIONS)


def test_edge_cases_match_expected_outcome() -> None:
    """Each edge-case map behaves exactly as its header documents."""
    for filename, expected in EXPECTATIONS.items():
        path = f"{EDGE_CASES_DIR}/{filename}"

        if expected == "parse_error":
            try:
                MapParser().parse(path)
            except ParseError:
                continue
            raise AssertionError(f"{filename}: expected ParseError")

        graph, drones = MapParser().parse(path)

        if expected == "simulation_error":
            try:
                Scheduler(graph, max_turn_count=200).solve(drones)
            except SimulationError:
                continue
            raise AssertionError(f"{filename}: expected SimulationError")

        assert isinstance(expected, int)
        total = Scheduler(graph, max_turn_count=200).solve(drones)
        assert total == expected, (
            f"{filename}: expected {expected} turns, got {total}")
