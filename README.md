*This project has been created as part of the 42 curriculum by anzongan.*

# Fly-in

## Description

Fly-in routes a fleet of drones from a single start zone to a single end
zone across a graph of connected zones, in the fewest possible simulation
turns, while respecting per-zone and per-connection capacity limits and
per-zone-type movement costs (`normal`, `priority`, `restricted`,
`blocked`).

The project is split into five independent, fully object-oriented, fully
typed modules:

- `fly_in/models.py` — domain model: `ZoneType`, `Zone`, `Connection`,
  `Drone`, `Graph` (plain `dataclasses`, zero external dependency).
- `fly_in/parser.py` — `MapParser`: turns a map file into a `Graph` and a
  list of `Drone`s, with precise, line-numbered error messages.
- `fly_in/engine.py` — `Scheduler`: computes a conflict-free path for
  every drone.
- `fly_in/output.py` — writes the turn-by-turn output file in the exact
  format required by the subject.
- `fly_in/display.py` — `TerminalDisplay`: colored terminal visual
  feedback of the simulation.
- `fly_in/main.py` — CLI entry point wiring everything together.

## Instructions

No external runtime dependency is required (standard library only).

```bash
make install     # creates .venv and installs dev tools: flake8, mypy, pytest
make run MAP=maps/easy_2_fork.txt          # runs the simulation
make run MAP=maps/hard_3_ultimate.txt OUTPUT=out.txt
make debug MAP=maps/easy_1_linear.txt      # runs under pdb
make lint         # flake8 + mypy (subject's mandatory flags)
make lint-strict  # flake8 + mypy --strict
make test         # runs the pytest suite
make clean        # removes __pycache__ / .mypy_cache / .pytest_cache
```

The Makefile runs development commands with `.venv` automatically. To
activate the environment in your shell, run `source .venv/bin/activate`.

Or directly:

```bash
python3 -m fly_in.main maps/easy_2_fork.txt -o sim_output.txt
python3 -m fly_in.main maps/hard_3_ultimate.txt --quiet   # no terminal visual
```

Ten test maps (the ones provided with the subject, split one-per-file)
are available under `maps/`.

## Algorithm choice and implementation strategy

Drones are scheduled **one at a time**, in a **space-time Dijkstra**
search over `(zone, tick)` states:

- From a state `(zone, t)`, a drone can either **wait** (move to
  `(zone, t+1)`) or **move** along an adjacent connection to a
  neighboring zone, provided:
  - the neighbor is not `blocked`;
  - the connection has free capacity (`max_link_capacity`) on every
    tick of the transit;
  - the destination zone has free capacity (`max_drones`) on the tick
    of arrival (this check is skipped entirely for the start/end
    zones, which have unlimited capacity by definition).
- A move to a `restricted` zone costs 2 ticks: the drone is reported as
  being on the *connection* for the first tick, then on the destination
  zone for the second — it cannot wait mid-connection.
- A move to a `priority` zone gets an infinitesimal cost bonus
  (`+0.001` avoided) over an equally-costly `normal` move, so the
  priority queue naturally prefers priority zones when several
  equally-short options exist, without distorting turn counts.
- Once a drone's path is found, its node/connection usage is
  **committed** to a global reservation table (`(name, tick) -> count`)
  that subsequent drones' searches must respect. This greedy,
  sequential scheduling is what lets later drones route around
  congestion left by earlier ones.

**Complexity**: for a single drone, the search explores at most
`O(zones * max_ticks)` states, each expanded in `O(degree)`, so a full
simulation of `n` drones is `O(n * zones * max_ticks * degree *
log(...))` for the heap operations. No path is ever recomputed once a
drone is scheduled — reservations are looked up in O(1) dict access.
Memory is dominated by the reservation tables and, per search, the
occupancy/movement lists carried on each heap entry (small: bounded by
path length).

**Observed performance vs the subject's reference targets**
(`make run MAP=... `, see `maps/`):

| Map                          | Turns | Target  |
|-------------------------------|------:|:-------:|
| easy_1_linear                 |     4 | ≤ 6     |
| easy_2_fork                   |     5 | ≤ 8     |
| easy_3_capacity               |     6 | ≤ 6     |
| medium_1_dead_end             |     8 | ≤ 12    |
| medium_2_loop                 |    16 | ≤ 15*   |
| medium_3_priority             |     7 | ≤ 12    |
| hard_1_maze                   |    14 | ≤ 30    |
| hard_2_capacity_timing        |    18 | ≤ 35    |
| hard_3_ultimate               |    26 | ≤ 45    |
| challenger_impossible_dream   |    43 | 45 (record) |

`*` `medium_2_loop`'s `start` zone has a single exit connection with
`max_link_capacity=1` and a `restricted` (2-turn) neighbor. With 6
drones that single-file bottleneck alone imposes a lower bound of
`6 * 2 = 12` ticks just to funnel everyone through it, plus 4 more
ticks to reach the goal from there — i.e. 16 turns is provably optimal
for this map, one tick above the reference target.

## Visual representation

`TerminalDisplay` prints one colored line per simulation turn, e.g.:

```
Turn   1: D1->junction
Turn   2: D1->path_a D2->junction
```

- Each movement is colored by the destination zone's declared `color`
  metadata when present, otherwise by its zone type (red = restricted,
  green = priority, default = normal). A drone in flight toward a
  restricted zone (shown as the connection name) is colored cyan.
- A summary block after the simulation reports the total number of
  turns, how many drones were delivered, and the average turns per
  drone — the secondary metrics suggested by the subject.
- This gives an at-a-glance read of congestion (many colored zone
  names on one line = high throughput that turn) and of which drones
  are stuck queuing on restricted/limited-capacity zones.

## Example input and output

Input (`maps/easy_2_fork.txt`, simple fork with 3 drones):

```
nb_drones: 3
start_hub: start 0 0 [color=green]
hub: junction 1 0 [color=yellow max_drones=2]
hub: path_a 2 1 [color=blue]
hub: path_b 2 -1 [color=blue]
end_hub: goal 3 0 [color=red max_drones=3]
connection: start-junction
connection: junction-path_a
connection: junction-path_b
connection: path_a-goal
connection: path_b-goal
```

Output (`sim_output.txt`):

```
D1-junction
D1-path_a D2-junction
D1-goal D2-path_a D3-junction
D2-goal D3-path_a
D3-goal
```

## Resources

- 42 subject: *Fly-in* (v1.6).
- Python `dataclasses`, `enum`, `heapq`, `argparse`, `pathlib` — standard
  library documentation (docs.python.org).
- Background reading: multi-agent pathfinding / conflict-based search
  (the general family of algorithms this project's space-time
  reservation approach belongs to).
- ANSI escape codes for terminal color output (Wikipedia: "ANSI escape
  code").

### AI usage

Claude (Anthropic) was used as a pair-programming assistant under time
pressure, with a plan-first workflow (full requirement checklist, then
pseudocode before code for every module). Concretely, it was used to:

- Draft the initial project plan/checklist from the subject PDF.
- Co-design the domain model (`models.py`) and the parser (`parser.py`),
  including the line-numbered error reporting required by the subject.
- Co-design and implement the space-time Dijkstra scheduling algorithm
  (`engine.py`) — the reservation-table approach was adapted from the
  general idea of a previously-explored reference implementation, then
  rewritten from scratch with plain `dataclasses` (no `pydantic`/`pyray`
  dependency) to guarantee `mypy --strict` compliance.
- Write the output formatter, terminal display, and CLI wiring.
- Write and run the `pytest` suite, and iteratively fix every
  `flake8`/`mypy --strict` warning.
- Validate the implementation's turn counts against every map provided
  with the subject, including the optional Challenger map.

Every module was read, understood, and manually verified (including by
running the full test suite and the linters) before being considered
part of the final submission, in line with the subject's AI-usage
guidelines (Chapter II).
