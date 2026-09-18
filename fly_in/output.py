"""Writer for the simulation's turn-by-turn output format."""

from __future__ import annotations

from typing import TextIO

from fly_in.models import Drone


def build_lines(drones: list[Drone], total_turns: int) -> list[str]:
    """Build the turn-by-turn output lines for a solved simulation.

    Args:
        drones: Drones with their `movements` already computed.
        total_turns: The last turn during which any drone still moves.

    Returns:
        A list of output lines, one per turn that has at least one
        drone movement (turns with no movement at all are omitted).
    """
    lines: list[str] = []
    for turn in range(1, total_turns + 1):
        parts = []
        for drone in drones:
            label = drone.movements.get(turn)
            if label is not None:
                parts.append(f"D{drone.id + 1}-{label}")
        if parts:
            lines.append(" ".join(parts))
    return lines


def write_output(
    drones: list[Drone], total_turns: int, stream: TextIO
) -> None:
    """Write the simulation output to a text stream.

    Args:
        drones: Drones with their `movements` already computed.
        total_turns: The last turn during which any drone still moves.
        stream: Destination text stream (an open file or stdout).

    Returns:
        None.
    """
    for line in build_lines(drones, total_turns):
        stream.write(line + "\n")
