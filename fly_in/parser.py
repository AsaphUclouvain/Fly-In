"""Parser for the Fly-in map description format (see subject Chapter VI)."""

from __future__ import annotations

from pathlib import Path

from fly_in.errors import FlyInError
from fly_in.models import Connection, Drone, Graph, Zone, ZoneType


class ParseError(FlyInError):
    """Raised when a map file is malformed.

    Carries the offending line number so the caller can print a clear,
    precise diagnostic (as required by the subject).
    """

    def __init__(self, path: str, line_no: int, reason: str) -> None:
        """Build a parse error tied to a specific file/line.

        Args:
            path: Path of the map file being parsed.
            line_no: 1-indexed line number where the error occurred.
            reason: Human-readable explanation of what went wrong.
        """
        message = f'File "{path}", line {line_no}: {reason}'
        super().__init__(message)
        self.path = path
        self.line_no = line_no
        self.reason = reason


_HUB_DIRECTIVES = {"hub", "start_hub", "end_hub"}


class MapParser:
    """Parse a map file into a Graph and a list of Drones."""

    def parse(self, path: str) -> tuple[Graph, list[Drone]]:
        """Parse the given map file.

        Args:
            path: Path to the map description file.

        Returns:
            A tuple of (Graph, list of Drones).

        Raises:
            ParseError: If the file is malformed.
            FileNotFoundError: If the file does not exist.
        """
        graph = Graph()
        nb_drones: int | None = None
        seen_connections: set[frozenset[str]] = set()

        raw_lines = Path(path).read_text(encoding="utf-8").splitlines()

        for i, raw_line in enumerate(raw_lines, start=1):
            line = raw_line.split("#", 1)[0].strip()
            if not line:
                continue

            if ":" not in line:
                raise ParseError(path, i, f"expected ':' in line: {line!r}")

            left, right = line.split(":", 1)
            left = left.strip()
            right = right.strip()

            try:
                if left == "nb_drones":
                    if nb_drones is not None:
                        raise ValueError("multiple nb_drones entries")
                    nb_drones = self._parse_nb_drones(right)
                elif left in _HUB_DIRECTIVES:
                    if nb_drones is None:
                        raise ValueError(
                            "nb_drones must be declared before any hub")
                    zone = self._parse_zone(right, left)
                    if zone.name in graph.zones:
                        raise ValueError(
                            f"duplicate zone name {zone.name!r}")
                    graph.zones[zone.name] = zone
                    if left == "start_hub":
                        if graph.start:
                            raise ValueError("multiple start_hub entries")
                        graph.start = zone.name
                    elif left == "end_hub":
                        if graph.end:
                            raise ValueError("multiple end_hub entries")
                        graph.end = zone.name
                elif left == "connection":
                    if nb_drones is None:
                        raise ValueError(
                            "nb_drones must be declared before any "
                            "connection")
                    connection = self._parse_connection(right, graph)
                    key = frozenset((connection.a, connection.b))
                    if key in seen_connections:
                        raise ValueError(
                            f"duplicate connection between "
                            f"{connection.a!r} and {connection.b!r}")
                    seen_connections.add(key)
                    graph.connections[connection.name] = connection
                else:
                    raise ValueError(f"unknown directive {left!r}")
            except ValueError as exc:
                raise ParseError(path, i, str(exc)) from exc

        if nb_drones is None:
            raise ParseError(path, len(raw_lines), "missing 'nb_drones'")
        if not graph.start:
            raise ParseError(path, len(raw_lines), "missing 'start_hub'")
        if not graph.end:
            raise ParseError(path, len(raw_lines), "missing 'end_hub'")

        graph.build_adjacency()
        drones = [Drone(id=i) for i in range(nb_drones)]
        return graph, drones

    def _parse_nb_drones(self, text: str) -> int:
        """Parse and validate the nb_drones value.

        Args:
            text: Right-hand-side text after 'nb_drones:'.

        Returns:
            The number of drones as a positive integer.

        Raises:
            ValueError: If the value is missing or not a positive int.
        """
        if not text:
            raise ValueError("nb_drones requires a value")
        try:
            value = int(text)
        except ValueError:
            raise ValueError(f"nb_drones must be an integer, got {text!r}")
        if value <= 0:
            raise ValueError("nb_drones must be a positive integer")
        return value

    def _parse_metadata(self, tokens: list[str]) -> dict[str, str]:
        """Parse a bracketed metadata block into a key/value mapping.

        Args:
            tokens: Whitespace-split tokens making up the "[...]" block
                (may be empty if there is no metadata at all).

        Returns:
            A dict mapping metadata keys to their raw string values.

        Raises:
            ValueError: If brackets are missing/mismatched, or a token
                is not a valid key=value pair, or a key is repeated.
        """
        if not tokens:
            return {}
        joined = " ".join(tokens).strip()
        if not (joined.startswith("[") and joined.endswith("]")):
            raise ValueError(f"malformed metadata block: {joined!r}")
        inner = joined[1:-1].strip()
        if not inner:
            return {}
        result: dict[str, str] = {}
        for token in inner.split():
            if "=" not in token:
                raise ValueError(f"malformed metadata entry: {token!r}")
            key, _, value = token.partition("=")
            key = key.strip()
            value = value.strip()
            if not key or not value:
                raise ValueError(f"malformed metadata entry: {token!r}")
            if key in result:
                raise ValueError(f"duplicate metadata key: {key!r}")
            result[key] = value
        return result

    def _parse_zone(self, text: str, kind: str) -> Zone:
        """Parse a hub/start_hub/end_hub definition line.

        Args:
            text: Right-hand-side text (everything after the ':').
            kind: One of 'hub', 'start_hub', 'end_hub'.

        Returns:
            The constructed Zone.

        Raises:
            ValueError: On any structural or semantic error.
        """
        tokens = text.split()
        if len(tokens) < 3:
            raise ValueError(f"incomplete {kind} definition: {text!r}")

        name, x_raw, y_raw = tokens[0], tokens[1], tokens[2]
        if "-" in name or " " in name or "#" in name:
            raise ValueError(
                f"zone name {name!r} contains a forbidden character "
                f"(dash/space/#)")
        try:
            x, y = int(x_raw), int(y_raw)
        except ValueError:
            raise ValueError(f"zone {name!r} has non-integer coordinates")

        metadata = self._parse_metadata(tokens[3:])

        zone_type = ZoneType.NORMAL
        color: str | None = None
        max_drones = 1

        for key, value in metadata.items():
            if key == "zone":
                try:
                    zone_type = ZoneType(value.lower())
                except ValueError:
                    raise ValueError(f"{value!r} is not a valid zone type")
            elif key == "color":
                color = value
            elif key == "max_drones":
                try:
                    max_drones = int(value)
                except ValueError:
                    raise ValueError(
                        f"max_drones must be an integer, got {value!r}")
                if max_drones < 1:
                    raise ValueError(
                        f"max_drones must be positive, got {max_drones}")
            else:
                raise ValueError(f"invalid zone metadata key: {key!r}")

        return Zone(
            name=name, x=x, y=y, zone_type=zone_type, color=color,
            max_drones=max_drones,
            is_start=(kind == "start_hub"), is_end=(kind == "end_hub"),
        )

    def _parse_connection(self, text: str, graph: Graph) -> Connection:
        """Parse a connection definition line.

        Args:
            text: Right-hand-side text (everything after the ':').
            graph: Graph parsed so far (used to validate zone names).

        Returns:
            The constructed Connection.

        Raises:
            ValueError: On any structural or semantic error.
        """
        tokens = text.split()
        if not tokens:
            raise ValueError("empty connection definition")

        head = tokens[0]
        if head.count("-") != 1:
            raise ValueError(f"malformed connection endpoints: {head!r}")
        a, b = head.split("-")
        if not a or not b:
            raise ValueError(f"malformed connection endpoints: {head!r}")
        if a == b:
            raise ValueError(
                f"a connection cannot link a zone to itself: {a!r}")
        if a not in graph.zones:
            raise ValueError(f"connection references unknown zone {a!r}")
        if b not in graph.zones:
            raise ValueError(f"connection references unknown zone {b!r}")

        metadata = self._parse_metadata(tokens[1:])
        max_link_capacity = 1
        for key, value in metadata.items():
            if key == "max_link_capacity":
                try:
                    max_link_capacity = int(value)
                except ValueError:
                    raise ValueError(
                        f"max_link_capacity must be an integer, "
                        f"got {value!r}")
                if max_link_capacity < 1:
                    raise ValueError(
                        f"max_link_capacity must be positive, "
                        f"got {max_link_capacity}")
            else:
                raise ValueError(f"invalid connection metadata key: {key!r}")

        name = f"{a}-{b}"
        return Connection(
            name=name, a=a, b=b, max_link_capacity=max_link_capacity)
