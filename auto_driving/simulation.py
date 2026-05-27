"""
simulation.py – Core simulation engine.

Runs commands step-by-step across all cars, detecting collisions
after each car moves within a step.
"""

from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from field import Field
    from car import Car


class SimulationResult:
    """Holds the outcome for a single car after the simulation completes."""

    def __init__(self, car: "Car") -> None:
        self.name           = car.name
        self.x              = car.x
        self.y              = car.y
        self.direction      = car.direction
        self.collided       = car.collided
        self.collision_info = car.collision_info

    def __str__(self) -> str:
        if self.collided:
            return f"- {self.name}, {self.collision_info}"
        return f"- {self.name}, ({self.x},{self.y}) {self.direction}"


class Simulation:
    """
    Runs the step-by-step simulation for all cars on a field.

    Assumes all cars move at the same speed — each car processes
    exactly one command per step before moving to the next step.

    Processing order per step (per spec):
      For each step index i:
        For each car in insertion order:
          If the car has a command at index i and has not collided:
            Execute the command.
            Check for collisions with all other cars.

    Collision semantics:
      - Two cars collide when they occupy the same (x, y) cell
        after any individual move within a step.
      - Both cars are marked as collided and stop processing.
      - The step number reported is 1-based.
      - Collided cars remain frozen on the field as obstacles.
        A third car moving into a collision site will also collide.

    Gaps / improvement areas:
      - Head-on swap collisions (cars swapping positions in the same
        step) are not detected; a future version could check paths,
        not just positions.
      - No step-by-step mode; simulation runs to completion instantly.
      - No exit option mid-simulation.
    """

    def __init__(self, field: "Field", cars: list["Car"]) -> None:
        self.field = field
        self.cars  = cars

    def run(self) -> list[SimulationResult]:
        """Execute the simulation and return one result per car."""
        # Pre-flight: mark cars that share a starting position as immediately collided
        self._check_starting_collisions()

        if not self.cars:
            return []

        max_steps = max(len(car.commands) for car in self.cars)

        for step in range(max_steps):
            for car in self.cars:
                if car.collided:
                    continue
                if step >= len(car.commands):
                    continue

                cmd = car.commands[step]
                self._execute_command(car, cmd)

                if not car.collided:
                    self._check_collisions(car, step + 1)  # 1-based step

        return [SimulationResult(c) for c in self.cars]

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _execute_command(self, car: "Car", cmd: str) -> None:
        if cmd == "L":
            car.turn_left()
        elif cmd == "R":
            car.turn_right()
        elif cmd == "F":
            car.move_forward(self.field)

    def _check_collisions(self, moved_car: "Car", step: int) -> None:
        """
        After moved_car has executed its command, check whether it
        now shares a cell with any other car — including cars that
        are already collided (frozen obstacles).
        Only update collision_info on the other car if it has not
        already been set.
        """
        for other in self.cars:
            if other is moved_car:
                continue
            if moved_car.x == other.x and moved_car.y == other.y:
                pos = f"({moved_car.x},{moved_car.y})"
                moved_car.collided      = True
                moved_car.collision_info = (
                    f"collides with {other.name} at {pos} at step {step}"
                )
                if not other.collided:
                    other.collided      = True
                    other.collision_info = (
                        f"collides with {moved_car.name} at {pos} at step {step}"
                    )

    def _check_starting_collisions(self) -> None:
        """
        Before any commands run, check if any two cars share the same
        starting position and mark them as collided at step 0.
        """
        for i, car in enumerate(self.cars):
            for other in self.cars[i + 1:]:
                if car.x == other.x and car.y == other.y:
                    pos = f"({car.x},{car.y})"
                    if not car.collided:
                        car.collided      = True
                        car.collision_info = f"collides with {other.name} at {pos} at step 0"
                    if not other.collided:
                        other.collided      = True
                        other.collision_info = f"collides with {car.name} at {pos} at step 0"
