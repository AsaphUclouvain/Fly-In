"""Command-line entry point for the Fly-in drone routing simulation."""

from __future__ import annotations

import argparse
import sys

from fly_in.display import TerminalDisplay
from fly_in.engine import Scheduler, SimulationError
from fly_in.output import write_output
from fly_in.parser import MapParser, ParseError


def display_error(message: str) -> None:
    """Print an error message to stderr in red.

    Args:
        message: The error message to display.

    Returns:
        None.
    """
    sys.stderr.write(f"\033[31m[ERROR]\033[0m {message}\n")


def build_arg_parser() -> argparse.ArgumentParser:
    """Build the command-line argument parser.

    Returns:
        A configured argparse.ArgumentParser.
    """
    description = (
        "Route a fleet of drones from a start zone to an end zone "
        "across a network of connected zones.")
    parser = argparse.ArgumentParser(prog="fly-in", description=description)
    parser.add_argument("map", help="Path to the map description file")
    parser.add_argument(
        "-o", "--output", default="sim_output.txt",
        help="Path of the output file (default: sim_output.txt)")
    parser.add_argument(
        "-q", "--quiet", action="store_true",
        help="Skip the colored terminal visualization")
    return parser


def run(argv: list[str] | None = None) -> int:
    """Run the full parse -> solve -> display -> write pipeline.

    Args:
        argv: Command-line arguments (excluding program name). Uses
            sys.argv when None.

    Returns:
        Process exit code (0 on success, 1 on failure).
    """
    args = build_arg_parser().parse_args(argv)

    try:
        graph, drones = MapParser().parse(args.map)
    except ParseError as exc:
        display_error(str(exc))
        return 1
    except UnicodeDecodeError as exc:
        display_error(
            f"map file {args.map!r} is not valid UTF-8 text: {exc}")
        return 1
    except OSError as exc:
        display_error(f"cannot read map file {args.map!r}: {exc}")
        return 1

    try:
        total_turns = Scheduler(graph).solve(drones)
    except SimulationError as exc:
        display_error(str(exc))
        return 1

    if not args.quiet:
        TerminalDisplay(graph).render(drones, total_turns)

    try:
        with open(args.output, "w", encoding="utf-8") as stream:
            write_output(drones, total_turns, stream)
    except OSError as exc:
        display_error(f"cannot write output file {args.output!r}: {exc}")
        return 1

    print(f"\nOutput written to {args.output} ({total_turns} turns).")
    return 0


def main() -> None:
    """Console-script entry point."""
    try:
        exit_code = run()
    except Exception as exc:  # noqa: BLE001 - deliberate last-resort catch
        display_error(f"unexpected internal error: {exc}")
        exit_code = 1
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
