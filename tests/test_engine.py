"""Tests for fly_in.engine.Scheduler."""

from pathlib import Path

import pytest

from fly_in.engine import Scheduler, SimulationError
from fly_in.parser import MapParser


def write_map(tmp_path: Path, content: str) -> str:
    """Write a map fixture to a temp file and return its path."""
    path = tmp_path / "map.txt"
    path.write_text(content)
    return str(path)


def test_linear_path_takes_exactly_the_path_length(tmp_path: Path) -> None:
    """A single drone on a 3-hop linear map needs exactly 3 turns."""
    content = """
    nb_drones: 1
    start_hub: a 0 0
    hub: b 1 0
    hub: c 2 0
    end_hub: d 3 0
    connection: a-b
    connection: b-c
    connection: c-d
    """
    graph, drones = MapParser().parse(write_map(tmp_path, content))
    total = Scheduler(graph).solve(drones)
    assert total == 3
    assert drones[0].movements == {1: "b", 2: "c", 3: "d"}


def test_restricted_zone_produces_two_events(tmp_path: Path) -> None:
    """Entering a restricted zone shows the connection, then the zone."""
    content = """
    nb_drones: 1
    start_hub: a 0 0
    hub: b 1 0 [zone=restricted]
    end_hub: c 2 0
    connection: a-b
    connection: b-c
    """
    graph, drones = MapParser().parse(write_map(tmp_path, content))
    Scheduler(graph).solve(drones)
    assert drones[0].movements[1] == "a-b"
    assert drones[0].movements[2] == "b"


def test_blocked_zone_is_never_used(tmp_path: Path) -> None:
    """A blocked zone must never appear in any drone's movements."""
    content = """
    nb_drones: 1
    start_hub: a 0 0
    hub: shortcut 1 0 [zone=blocked]
    hub: detour 1 1
    end_hub: c 2 0
    connection: a-shortcut
    connection: shortcut-c
    connection: a-detour
    connection: detour-c
    """
    graph, drones = MapParser().parse(write_map(tmp_path, content))
    Scheduler(graph).solve(drones)
    assert "shortcut" not in drones[0].movements.values()
    assert drones[0].movements == {1: "detour", 2: "c"}


def test_capacity_one_zone_serializes_two_drones(tmp_path: Path) -> None:
    """Two drones cannot occupy a max_drones=1 zone at the same tick."""
    content = """
    nb_drones: 2
    start_hub: start 0 0
    hub: bottleneck 1 0 [max_drones=1]
    end_hub: goal 2 0
    connection: start-bottleneck
    connection: bottleneck-goal
    """
    graph, drones = MapParser().parse(write_map(tmp_path, content))
    Scheduler(graph).solve(drones)
    arrivals = [d.movements[t] for d in drones for t in d.movements
                if d.movements[t] == "bottleneck"]
    # Both drones pass through, but never at the same simulated tick.
    tick_a = [t for t, label in drones[0].movements.items()
              if label == "bottleneck"][0]
    tick_b = [t for t, label in drones[1].movements.items()
              if label == "bottleneck"][0]
    assert len(arrivals) == 2
    assert tick_a != tick_b


def test_unreachable_end_raises_simulation_error(tmp_path: Path) -> None:
    """If the end zone cannot be reached, SimulationError is raised."""
    content = """
    nb_drones: 1
    start_hub: a 0 0
    end_hub: b 1 0
    hub: isolated 5 5
    """
    graph, drones = MapParser().parse(write_map(tmp_path, content))
    with pytest.raises(SimulationError):
        Scheduler(graph).solve(drones)
