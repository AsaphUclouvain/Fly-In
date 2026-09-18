"""Multi-drone scheduling engine for the Fly-in simulation.

Each drone's path is computed with a space-time Dijkstra search over
(zone, turn_count) states, respecting zone/link capacity already reserved by
previously scheduled drones. This mirrors how air-traffic-style
sequential slot allocation works: drones are scheduled one at a time,
each avoiding the space-time "shadow" left by the ones before it.
"""

from __future__ import annotations

import heapq
import itertools
from fly_in.errors import FlyInError
from fly_in.models import Drone, Graph, ZoneType

# (kind, name, turn_count) where kind is either "node" or "link".
Occupancy = tuple[str, str, int]

# (weight, turn_count, tie_breaker, node, occupancy, movements).
HeapItem = tuple[float, int, int, str, list[Occupancy], dict[int, str]]


class SimulationError(FlyInError):
    """Raised when no valid path can be found for a drone."""


class Scheduler:
    """Compute conflict-free, capacity-respecting paths for all drones."""

    def __init__(self, graph: Graph, max_turn_count: int = 600) -> None:
        """Initialize the scheduler.

        Args:
            graph: The parsed zone/connection graph to route through.
            max_turn_count: Safety bound on the search horizon, to avoid
                infinite exploration on unsolvable/pathological maps.
        """
        self.graph = graph
        self.max_turn_count = max_turn_count
        self._node_reservations: dict[tuple[str, int], int] = {}
        self._link_reservations: dict[tuple[str, int], int] = {}

    def solve(self, drones: list[Drone]) -> int:
        """Compute and assign a path to every drone.

        Args:
            drones: Drones to route, scheduled in list order. Each
                drone's `movements` attribute is filled in place.

        Returns:
            The total number of simulation turns (the last turn during
            which any drone still moves).

        Raises:
            SimulationError: If any drone cannot reach the end zone.
        """
        total_turns = 0
        for drone in drones:
            occupancy, movements = self._find_path()
            if movements is None:
                raise SimulationError(
                    f"No valid path found for drone D{drone.id + 1} "
                    f"within {self.max_turn_count} turns")
            self._commit(occupancy)
            drone.movements = movements
            if movements:
                total_turns = max(total_turns, max(movements))
        return total_turns

    def _node_available(self, name: str, turn_count: int) -> bool:
        """Check whether a zone has free capacity at a given turn."""
        zone = self.graph.zones[name]
        if zone.has_unlimited_capacity:
            return True
        used = self._node_reservations.get((name, turn_count), 0)
        return used < zone.max_drones

    def _link_available(self, name: str, turn_count: int) -> bool:
        """Check whether a connection has free capacity at a given turn."""
        connection = self.graph.connections[name]
        used = self._link_reservations.get((name, turn_count), 0)
        return used < connection.max_link_capacity

    def _commit(self, occupancy: list[Occupancy]) -> None:
        """Permanently reserve the occupancy slots used by a found path."""
        for kind, name, turn_count in occupancy:
            table = (
                self._node_reservations if kind == "node"
                else self._link_reservations)
            table[(name, turn_count)] = table.get((name, turn_count), 0) + 1

    def _find_path(self) -> tuple[list[Occupancy], dict[int, str] | None]:
        """Search the shortest, capacity-respecting path for one drone.

        Args:
            drone_id: Identifier of the drone being routed (used only
                for error messages).

        Returns:
            A tuple of (occupancy slots to reserve, movement events by
            turn). movements is None if no path was found.
        """
        start, end = self.graph.start, self.graph.end
        counter = itertools.count()
        start_item: HeapItem = (0.0, 0, next(counter), start, [], {})
        heap: list[HeapItem] = [start_item]
        visited: set[tuple[str, int]] = set()

        while heap:
            (weight, turn_count, _, node,
                occupancy, movements) = heapq.heappop(heap)

            if node == end:
                return occupancy, movements
            if (node, turn_count) in visited:
                continue
            visited.add((node, turn_count))
            if turn_count >= self.max_turn_count:
                continue

            self._push_wait(
                heap, counter, weight, turn_count, node, occupancy, movements)
            for (neighbor, connection_name,
                    move_cost) in self._reachable(node):
                self._push_move(
                    heap, counter, weight, turn_count, neighbor,
                    connection_name, move_cost, occupancy, movements)

        return [], None

    def _reachable(self, node: str) -> list[tuple[str, str, int]]:
        """List (neighbor, connection name, travel cost) reachable from node.

        Blocked neighbors are excluded entirely.
        """
        results = []
        for connection in self.graph.neighbors(node):
            neighbor = connection.other(node)
            zone_type = self.graph.zones[neighbor].zone_type
            if zone_type is ZoneType.BLOCKED:
                continue
            results.append((neighbor, connection.name, zone_type.cost))
        return results

    def _push_wait(
        self, heap: list[HeapItem], counter: "itertools.count[int]",
        weight: float, turn_count: int, node: str,
        occupancy: list[Occupancy],
        movements: dict[int, str],
    ) -> None:
        """Push the "stay in place for one more turn" transition."""
        next_turn = turn_count + 1
        if next_turn > self.max_turn_count:
            return
        if not self._node_available(node, next_turn):
            return
        new_occupancy = occupancy
        if not self.graph.zones[node].has_unlimited_capacity:
            new_occupancy = occupancy + [("node", node, next_turn)]
        item: HeapItem = (
            weight + 1, next_turn, next(counter), node, new_occupancy,
            movements)
        heapq.heappush(heap, item)

    def _push_move(
        self, heap: list[HeapItem], counter: "itertools.count[int]",
        weight: float, turn_count: int, neighbor: str, connection_name: str,
        move_cost: int, occupancy: list[Occupancy],
        movements: dict[int, str],
    ) -> None:
        """Push the "move to neighbor" transition, if capacity allows."""
        total_turn_count = turn_count + move_cost
        if total_turn_count > self.max_turn_count:
            return

        for step in range(1, move_cost + 1):
            if not self._link_available(connection_name, turn_count + step):
                return
        neighbor_zone = self.graph.zones[neighbor]
        if not neighbor_zone.has_unlimited_capacity:
            if not self._node_available(neighbor, total_turn_count):
                return

        new_occupancy = list(occupancy)
        for step in range(1, move_cost + 1):
            new_occupancy.append(("link", connection_name, turn_count + step))
        if not neighbor_zone.has_unlimited_capacity:
            new_occupancy.append(("node", neighbor, total_turn_count))

        new_movements = dict(movements)
        if move_cost == 1:
            new_movements[turn_count + 1] = neighbor
        else:
            new_movements[turn_count + 1] = connection_name
            new_movements[total_turn_count] = neighbor

        tie_break = 0.0 if neighbor_zone.zone_type.is_priority else 0.001
        item: HeapItem = (
            weight + move_cost + tie_break, total_turn_count, next(counter),
            neighbor, new_occupancy, new_movements)
        heapq.heappush(heap, item)
