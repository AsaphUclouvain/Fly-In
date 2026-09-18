"""Colored terminal display of the simulation (visual feedback)."""

from __future__ import annotations

from fly_in.models import Drone, Graph, ZoneType

_RESET = "\033[0m"
_BOLD = "\033[1m"

# Best-effort mapping from arbitrary color-name strings (as allowed by
# the map format) to ANSI escape codes. Unknown names fall back to the
# zone-type default, then to plain white.
_NAMED_COLORS: dict[str, str] = {
    "red": "\033[31m", "green": "\033[32m", "yellow": "\033[33m",
    "blue": "\033[34m", "magenta": "\033[35m", "cyan": "\033[36m",
    "white": "\033[37m", "gray": "\033[90m", "grey": "\033[90m",
    "black": "\033[90m", "orange": "\033[93m", "purple": "\033[95m",
    "gold": "\033[33m", "lime": "\033[92m", "violet": "\033[95m",
    "crimson": "\033[91m", "maroon": "\033[31m", "darkred": "\033[31m",
    "brown": "\033[33m", "rainbow": "\033[36m",
}

_ZONE_TYPE_DEFAULT: dict[ZoneType, str] = {
    ZoneType.RESTRICTED: "\033[31m",
    ZoneType.PRIORITY: "\033[32m",
    ZoneType.NORMAL: "\033[37m",
}


class TerminalDisplay:
    """Render a solved simulation as colored, turn-by-turn console output."""

    def __init__(
        self, graph: Graph,
    ) -> None:
        """Initialize the display for a given graph.

        Args:
            graph: The map's parsed graph (used to color zones by
                their declared color or zone type).
        """
        self.graph = graph

    def _color_for_label(self, label: str) -> str:
        """Pick an ANSI color code for a movement label.

        Args:
            label: Either a zone name (on arrival) or a connection
                name (while a drone is in flight toward a restricted
                zone).

        Returns:
            An ANSI escape code string.
        """
        zone = self.graph.zones.get(label)
        if zone is not None:
            if zone.color and zone.color.lower() in _NAMED_COLORS:
                return _NAMED_COLORS[zone.color.lower()]
            return _ZONE_TYPE_DEFAULT.get(zone.zone_type, "\033[37m")
        return "\033[36m"  # in-flight on a connection

    def render(
        self,
        drones: list[Drone],
        total_turns: int,
    ) -> None:
        """Print the full turn-by-turn simulation with colors.

        Args:
            drones: Drones with their `movements` already computed.
            total_turns: The last turn during which any drone moves.

        Returns:
            None.
        """
        print(f"{_BOLD}Map:{_RESET} {len(self.graph.zones)} zones, "
              f"{len(self.graph.connections)} connections, "
              f"{len(drones)} drones | start={self.graph.start} "
              f"end={self.graph.end}")
        print(f"{_BOLD}--- Simulation ---{_RESET}")

        delivered_turn: dict[int, int] = {}
        for turn in range(1, total_turns + 1):
            events = [(d, d.movements[turn]) for d in drones
                      if turn in d.movements]
            if not events:
                continue
            pieces = []
            for drone, label in events:
                color = self._color_for_label(label)
                pieces.append(f"{color}D{drone.id + 1}->{label}{_RESET}")
                if label == self.graph.end:
                    delivered_turn[drone.id] = turn
            print(f"{_BOLD}Turn {turn:>3}:{_RESET} " + " ".join(pieces))
        self._render_summary(drones, total_turns, delivered_turn)

    def _render_summary(
        self, drones: list[Drone], total_turns: int,
        delivered_turn: dict[int, int],
    ) -> None:
        """Print secondary performance metrics after the simulation."""
        turns_per_drone = [
            delivered_turn[d.id] for d in drones if d.id in delivered_turn]
        avg_turns = (sum(turns_per_drone) / len(turns_per_drone)
                     if turns_per_drone else 0.0)
        print(f"{_BOLD}--- Summary ---{_RESET}")
        print(f"Total simulation turns: {total_turns}")
        print(f"Drones delivered: {len(turns_per_drone)}/{len(drones)}")
        print(f"Average turns per drone: {avg_turns:.2f}")
