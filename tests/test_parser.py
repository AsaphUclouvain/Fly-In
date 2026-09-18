"""Tests for fly_in.parser.MapParser."""

from pathlib import Path

import pytest

from fly_in.models import ZoneType
from fly_in.parser import MapParser, ParseError


def write_map(tmp_path: Path, content: str) -> str:
    """Write a map fixture to a temp file and return its path."""
    path = tmp_path / "map.txt"
    path.write_text(content)
    return str(path)


def test_parses_easy_map(tmp_path: Path) -> None:
    """A well-formed map is parsed into the expected graph/drones."""
    content = """
    nb_drones: 2
    start_hub: start 0 0 [color=green]
    hub: mid 1 0 [zone=priority]
    end_hub: goal 2 0
    connection: start-mid
    connection: mid-goal
    """
    graph, drones = MapParser().parse(write_map(tmp_path, content))
    assert graph.start == "start"
    assert graph.end == "goal"
    assert len(drones) == 2
    assert graph.zones["mid"].zone_type is ZoneType.PRIORITY


def test_max_drones_ignored_on_start_end_is_not_an_error(
        tmp_path: Path) -> None:
    """max_drones on start/end hubs is accepted, just ignored later."""
    content = """
    nb_drones: 3
    start_hub: start 0 0 [max_drones=1]
    end_hub: goal 1 0 [max_drones=1]
    connection: start-goal
    """
    graph, _ = MapParser().parse(write_map(tmp_path, content))
    assert graph.zones["start"].has_unlimited_capacity
    assert graph.zones["goal"].has_unlimited_capacity


def test_duplicate_connection_raises(tmp_path: Path) -> None:
    """a-b and b-a are considered duplicate connections."""
    content = """
    nb_drones: 1
    start_hub: a 0 0
    end_hub: b 1 0
    connection: a-b
    connection: b-a
    """
    with pytest.raises(ParseError):
        MapParser().parse(write_map(tmp_path, content))


def test_invalid_zone_type_raises(tmp_path: Path) -> None:
    """An unknown zone= value must raise a ParseError."""
    content = """
    nb_drones: 1
    start_hub: a 0 0 [zone=lava]
    end_hub: b 1 0
    connection: a-b
    """
    with pytest.raises(ParseError):
        MapParser().parse(write_map(tmp_path, content))


def test_dash_in_zone_name_raises(tmp_path: Path) -> None:
    """Zone names cannot contain dashes."""
    content = """
    nb_drones: 1
    start_hub: a-b 0 0
    end_hub: c 1 0
    """
    with pytest.raises(ParseError):
        MapParser().parse(write_map(tmp_path, content))


def test_missing_end_hub_raises(tmp_path: Path) -> None:
    """A map without an end_hub must raise a ParseError."""
    content = """
    nb_drones: 1
    start_hub: a 0 0
    """
    with pytest.raises(ParseError):
        MapParser().parse(write_map(tmp_path, content))


def test_multiple_start_hub_raises(tmp_path: Path) -> None:
    """A second start_hub must raise a ParseError."""
    content = """
    nb_drones: 1
    start_hub: a 0 0
    start_hub: b 1 0
    end_hub: c 2 0
    """
    with pytest.raises(ParseError):
        MapParser().parse(write_map(tmp_path, content))
