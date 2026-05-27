# Auto Driving Car Simulation

A command-line simulation program for autonomous cars on a rectangular grid.
Cars can be added with starting positions and a sequence of commands (L, R, F).
The simulator runs all commands step-by-step, detecting collisions in real time.

---

## Project Structure

```
auto_driving/
├── src/
│   ├── main.py          # CLI entry point
│   ├── field.py         # Rectangular grid model
│   ├── car.py           # Car model (position, direction, commands)
│   └── simulation.py    # Step-by-step simulation engine
├── tests/
│   └── test_suite.py    # Unit tests covering all components
└── README.md
```

---

## Requirements

- Python 3.9 or higher
- No third-party libraries required (uses only the standard library)

---

## How to Run

### Start the simulation

```bash
cd auto_driving
python src/main.py
```

### Run the test suite

```bash
# Option 1 — plain Python (no install needed)
python tests/test_suite.py

# Option 2 — pytest (better output formatting)
pip install pytest
pytest tests/ -v
```

---

## Example Session

```
Welcome to Auto Driving Car Simulation!

Please enter the width and height of the simulation field in x y format:
10 10

You have created a field of 10 x 10.

Please choose from the following options:
[1] Add a car to field
[2] Run simulation
1

Please enter the name of the car:
A

Please enter initial position of car A in x y Direction format:
1 2 N

Please enter the commands for car A:
FFRFFFFRRL

Your current list of cars are:
- A, (1,2) N, FFRFFFFRRL

Please choose from the following options:
[1] Add a car to field
[2] Run simulation
2

Your current list of cars are:
- A, (1,2) N, FFRFFFFRRL

After simulation, the result is:
- A, (5,4) S
```

---

## Commands Reference

| Command | Action |
|---------|--------|
| `F` | Move forward one grid cell |
| `L` | Rotate 90 degrees to the left |
| `R` | Rotate 90 degrees to the right |

| Direction | Meaning |
|-----------|---------|
| `N` | North (up, +y) |
| `S` | South (down, -y) |
| `E` | East (right, +x) |
| `W` | West (left, -x) |

---

## Assumptions

**A1. Field coordinates**
The bottom-left cell is (0,0) and the top-right cell is (width-1, height-1).
A 10×10 field has valid positions (0,0) through (9,9).

**A2. Out-of-bounds movement**
If a car tries to move beyond the boundary, the F command is silently ignored
and the car stays in its current position.

**A3. Collision detection timing**
Collisions are checked after each individual car moves within a step.
If Car A moves into Car B's current cell, both are marked as collided
immediately — Car B does not need to move first.

**A4. Collided cars stop**
Once a car is involved in a collision it stops processing all further commands,
regardless of how many steps remain.

**A5. Unequal command lengths**
Cars run out of commands at different times. A car with fewer commands simply
stays in its last position while other cars continue executing.

**A6. Car names are case-sensitive**
Cars named "A" and "a" are treated as different cars.

**A7. Step numbering**
Steps are reported as 1-based (the first command processed is step 1).

**A8. Command characters**
Only uppercase L, R, F are valid. Input is automatically uppercased before
validation to be forgiving of lowercase entry.

**A9. All cars move at the same speed**
Every car processes exactly one command per step. There is no concept of a
faster or slower car — a step always advances all cars by one command each.

**A10. No two cars start at the same position**
The simulation assumes all cars are placed at distinct starting positions.
The program enforces this by re-prompting the user if a duplicate starting
position is entered.

**A11. No reverse command**
Cars cannot move backwards directly. To move in the opposite direction
a car must turn 180 degrees first (LL or RR) then move forward.

---

## Known Gaps & Improvement Areas

**G1. Head-on swap collisions not detected**
If Car A is at (4,5) facing East and Car B is at (5,5) facing West, and both
move forward in the same step, they swap positions. The current engine does not
detect this as a collision because it only checks final positions, not paths.
Fix: compare each car's next position against other cars' current positions
before committing moves.

**G2. No persistent state / save-load**
The simulation only exists in memory during a session. There is no way to save
a configuration and resume it later.
Fix: serialise field and car state to JSON and add save/load commands.

**G3. No GUI**
The interface is text-only. A visual grid would make it much easier to reason
about car positions and collision points.
Fix: add an optional grid renderer using a library like curses or a web-based
front end.

**G4. No maximum car limit enforced**
The program allows any number of cars to be added. On a very small field with
many cars, almost every move results in a collision.
Fix: optionally warn the user when the number of cars approaches field capacity.

**G5. Single-session only**
"Start over" resets everything but re-runs within the same process.
Fix: refactor session state into an isolated object that is fully discarded
on reset.

**G6. No validation for overlapping starting positions (simulation layer)**
While the CLI prevents duplicate starting positions via re-prompting,
the simulation engine itself does not enforce this. If the Car and Simulation
classes are used directly (e.g. in tests or via API), two cars can be created
at the same position without any warning.
Fix: add a pre-flight check in Simulation.run() that raises an error if any
two cars share the same starting coordinates.

**G7. Collided cars remain on the field as obstacles**
When two cars collide they freeze in place but still occupy their cell.
A third car moving into that cell will also be marked as collided.
The spec is silent on this case — this behaviour is an intentional extension
of the collision rules and is covered by the test suite.

**G8. No exit option on the main menu**
The main menu only offers [1] Add a car and [2] Run simulation. Users cannot
exit the program without first running the simulation.
Fix: add a [3] Exit option to the main menu so users can quit at any point
without being forced to complete a simulation.

**G9. No way to interrupt a running simulation**
Once the user selects [2] Run simulation, all commands execute immediately
with no option to pause or cancel mid-run.
Fix: introduce a step-by-step mode where the user presses Enter to advance
one step at a time, with an option to abort.
