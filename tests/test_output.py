"""Tests for fly_in.output.build_lines."""

from fly_in.models import Drone
from fly_in.output import build_lines


def test_build_lines_matches_subject_example() -> None:
    """Reproduce the exact example from the subject (chapter VII.5)."""
    d1 = Drone(id=0, movements={1: "roof1", 2: "roof2", 3: "goal"})
    d2 = Drone(id=1, movements={1: "corridorA", 2: "tunnelB", 3: "goal"})
    lines = build_lines([d1, d2], total_turns=3)
    assert lines == [
        "D1-roof1 D2-corridorA",
        "D1-roof2 D2-tunnelB",
        "D1-goal D2-goal",
    ]


def test_turns_with_no_movement_are_omitted() -> None:
    """A turn where no drone moves must not produce an output line."""
    d1 = Drone(id=0, movements={1: "a", 3: "goal"})
    lines = build_lines([d1], total_turns=3)
    assert lines == ["D1-a", "D1-goal"]
