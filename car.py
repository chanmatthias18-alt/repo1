"""
car.py – Represents a single autonomous car in the simulation.
"""

from __future__ import annotations
from typing import Optional

# Ordered clockwise so that turning left/right is an index shift
DIRECTIONS = ["N", "E", "S", "W"]

# How much (x, y) changes when moving forward in each direction
DIRECTION_DELTA = {
    "N": (0, 1),
    "E": (1, 0),
    "S": (0, -1),
    "W": (-1, 0),
}

VALID_COMMANDS  = frozenset("LRF")
VALID_DIRECTIONS = frozenset(DIRECTIONS)


class Car:
    """
    An autonomous car with a name, position, facing direction,
    and a sequence of commands to execute.

    Assumptions:
      - Car names are case-sensitive and must be unique within a field.
      - Commands must consist only of L, R, F characters.
      - A car that has collided stops processing further commands.
      - There is no reverse command; to move backwards a car must
        turn 180 degrees first (LL or RR) then move forward.
    """

    def __init__(
        self,
        name: str,
        x: int,
        y: int,
        direction: str,
        commands: str,
    ) -> None:
        if not name.strip():
            raise ValueError("Car name cannot be empty.")
        if direction not in VALID_DIRECTIONS:
            raise ValueError(
                f"Invalid direction '{direction}'. Must be one of {sorted(VALID_DIRECTIONS)}."
            )
        invalid = set(commands) - VALID_COMMANDS
        if invalid:
            raise ValueError(
                f"Invalid command(s) {invalid}. Only L, R, F are allowed."
            )

        self.name      = name
        self.x         = x
        self.y         = y
        self.direction = direction
        self.commands  = commands

        # Runtime state
        self.collided: bool          = False
        self.collision_info: Optional[str] = None

    # ------------------------------------------------------------------
    # Command execution
    # ------------------------------------------------------------------

    def turn_left(self) -> None:
        idx = DIRECTIONS.index(self.direction)
        self.direction = DIRECTIONS[(idx - 1) % 4]

    def turn_right(self) -> None:
        idx = DIRECTIONS.index(self.direction)
        self.direction = DIRECTIONS[(idx + 1) % 4]

    def next_position(self) -> tuple[int, int]:
        """Return the (x, y) the car would occupy after moving forward."""
        dx, dy = DIRECTION_DELTA[self.direction]
        return self.x + dx, self.y + dy

    def move_forward(self, field) -> None:
        """
        Move the car one step forward if the target cell is within bounds.
        Out-of-bounds moves are silently ignored per the spec.
        """
        nx, ny = self.next_position()
        if field.is_within_bounds(nx, ny):
            self.x = nx
            self.y = ny

    # ------------------------------------------------------------------
    # Display
    # ------------------------------------------------------------------

    def position_str(self) -> str:
        return f"({self.x},{self.y})"

    def __str__(self) -> str:
        return f"- {self.name}, ({self.x},{self.y}) {self.direction}, {self.commands}"
