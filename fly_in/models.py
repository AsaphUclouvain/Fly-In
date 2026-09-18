"""Domain model for the Fly-in drone routing simulation.

Everything here is plain stdlib (dataclasses + enum): no external
dependency, fully typed, fully object-oriented.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class ZoneType(Enum):
    """Type of a zone, with its movement cost and pathfinding weight.

    Attributes:
        NORMAL: Standard zone, costs 1 turn to enter.
        BLOCKED: Cannot be entered at all.
        RESTRICTED: Costs 2 turns to enter; the drone must arrive on
            the second turn and cannot wait mid-connection.
        PRIORITY: Costs 1 turn, but should be preferred by the
            pathfinding algorithm over an equally-costly normal zone.
    """

    NORMAL = "normal"
    BLOCKED = "blocked"
    RESTRICTED = "restricted"
    PRIORITY = "priority"

    @property
    def cost(self) -> int:
        """Number of simulation turns required to enter this zone type."""
        if self is ZoneType.RESTRICTED:
            return 2
        if self is ZoneType.BLOCKED:
            raise ValueError("blocked zones have no movement cost")
        return 1

    @property
    def is_priority(self) -> bool:
        """Whether this zone type should be preferred by pathfinding."""
        return self is ZoneType.PRIORITY


@dataclass
class Zone:
    """A single zone (node) in the drone network.

    Attributes:
        name: Unique zone identifier.
        x: X coordinate.
        y: Y coordinate.
        zone_type: The zone's type (normal/blocked/restricted/priority).
        color: Optional display color name, for terminal output.
        max_drones: Maximum number of drones allowed simultaneously.
            Ignored (treated as unlimited) for start/end zones.
        is_start: Whether this zone is the unique start hub.
        is_end: Whether this zone is the unique end hub.
    """

    name: str
    x: int
    y: int
    zone_type: ZoneType = ZoneType.NORMAL
    color: str | None = None
    max_drones: int = 1
    is_start: bool = False
    is_end: bool = False

    @property
    def has_unlimited_capacity(self) -> bool:
        """Whether occupancy limits are ignored for this zone."""
        return self.is_start or self.is_end


@dataclass
class Connection:
    """A bidirectional connection (edge) between two zones.

    Attributes:
        name: Unique connection identifier, e.g. "hub_connection_roof1".
        a: Name of the first connected zone.
        b: Name of the second connected zone.
        max_link_capacity: Maximum drones allowed to traverse
            simultaneously.
    """

    name: str
    a: str
    b: str
    max_link_capacity: int = 1

    def other(self, zone_name: str) -> str:
        """Return the zone on the other end of this connection.

        Args:
            zone_name: One of the two zones this connection links.

        Returns:
            The name of the opposite zone.

        Raises:
            ValueError: If zone_name is not part of this connection.
        """
        if zone_name == self.a:
            return self.b
        if zone_name == self.b:
            return self.a
        raise ValueError(
            f"{zone_name!r} is not part of connection {self.name!r}")


@dataclass
class Drone:
    """A single drone agent.

    Attributes:
        id: Unique numeric identifier (0-indexed internally).
        movements: Mapping of turn number to the label displayed for
            that turn (a zone name on arrival, a connection name while
            in flight toward a restricted zone). Populated by the
            simulation engine once a path has been found.
    """

    id: int
    movements: dict[int, str] = field(default_factory=dict)


@dataclass
class Graph:
    """Container for all zones and connections of a parsed map.

    Attributes:
        zones: Mapping of zone name to Zone.
        connections: Mapping of connection name to Connection.
        start: Name of the unique start zone.
        end: Name of the unique end zone.
    """

    zones: dict[str, Zone] = field(default_factory=dict)
    connections: dict[str, Connection] = field(default_factory=dict)
    start: str = ""
    end: str = ""
    _adjacency: dict[str, list[Connection]] = field(
        default_factory=dict, init=False, repr=False)

    def build_adjacency(self) -> None:
        """(Re)build the zone -> connections adjacency index.

        Must be called once after all zones/connections have been
        added (the parser does this automatically).
        """
        self._adjacency = {name: [] for name in self.zones}
        for connection in self.connections.values():
            self._adjacency[connection.a].append(connection)
            self._adjacency[connection.b].append(connection)

    def neighbors(self, zone_name: str) -> list[Connection]:
        """Return all connections attached to a given zone.

        Args:
            zone_name: Name of the zone to look up.

        Returns:
            List of Connection objects touching this zone.
        """
        return self._adjacency.get(zone_name, [])
