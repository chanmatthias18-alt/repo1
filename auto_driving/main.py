"""
main.py – Command-line interface for the Auto Driving Car Simulation.

Run:
    python main.py

Assumptions:
  - Input is via stdin; all prompts go to stdout.
  - Car names must be unique within a session.
  - At least one car must be added before running the simulation.
  - Invalid inputs trigger a re-prompt rather than crashing.
  - No two cars may start at the same position.
"""

from __future__ import annotations
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from field import Field
from car import Car
from simulation import Simulation


# ── helpers ───────────────────────────────────────────────────────────────────

def prompt(msg: str) -> str:
    """Print a prompt and return stripped user input."""
    return input(msg).strip()


def print_car_list(cars: list[Car]) -> None:
    print("\nYour current list of cars are:")
    for car in cars:
        print(car)


def print_menu_main() -> None:
    print("\nPlease choose from the following options:")
    print("[1] Add a car to field")
    print("[2] Run simulation")


def print_menu_end() -> None:
    print("\nPlease choose from the following options:")
    print("[1] Start over")
    print("[2] Exit")


# ── input collection helpers ──────────────────────────────────────────────────

def collect_field() -> Field:
    while True:
        raw = prompt(
            "\nPlease enter the width and height of the simulation field in x y format:\n"
        )
        parts = raw.split()
        try:
            if len(parts) != 2:
                raise ValueError
            w, h = int(parts[0]), int(parts[1])
            field = Field(w, h)
            print(f"\nYou have created a field of {field}.")
            return field
        except (ValueError, Exception):
            print("Invalid input. Please enter two positive integers, e.g. 10 10")


def collect_car(field: Field, existing_names: set[str], existing_cars: list[Car]) -> Car:
    # Name
    while True:
        name = prompt("\nPlease enter the name of the car:\n")
        if not name:
            print("Car name cannot be empty.")
        elif name in existing_names:
            print(f"A car named '{name}' already exists. Please choose a different name.")
        else:
            break

    # Position + direction
    while True:
        raw = prompt(f"\nPlease enter initial position of car {name} in x y Direction format:\n")
        parts = raw.split()
        try:
            if len(parts) != 3:
                raise ValueError("Expected format: x y Direction")
            x, y      = int(parts[0]), int(parts[1])
            direction = parts[2].upper()
            if direction not in ("N", "S", "E", "W"):
                raise ValueError("Direction must be N, S, E or W.")
            if not field.is_within_bounds(x, y):
                raise ValueError("Position is outside the field boundaries.")
            occupied = [c for c in existing_cars if c.x == x and c.y == y]
            if occupied:
                raise ValueError(
                    f"Position ({x},{y}) is already taken by car '{occupied[0].name}'."
                )
            break
        except (ValueError, Exception) as e:
            print(f"Invalid input ({e}). Use format: x y Direction  e.g. 1 2 N")

    # Commands
    while True:
        commands = prompt(f"\nPlease enter the commands for car {name}:\n").upper()
        invalid  = set(commands) - {"L", "R", "F"}
        if invalid:
            print(f"Invalid command(s): {invalid}. Only L, R, F are allowed.")
        else:
            break

    return Car(name, x, y, direction, commands)


# ── main loop ─────────────────────────────────────────────────────────────────

def run_session() -> bool:
    """
    Run one full session (field setup → add cars → simulate).
    Returns True if the user wants to start over, False to exit.
    """
    field          = collect_field()
    cars: list[Car] = []
    existing_names: set[str] = set()

    while True:
        print_menu_main()
        choice = prompt("")

        if choice == "1":
            car = collect_car(field, existing_names, cars)
            cars.append(car)
            existing_names.add(car.name)
            print_car_list(cars)

        elif choice == "2":
            if not cars:
                print("Please add at least one car before running the simulation.")
                continue

            print_car_list(cars)

            sim     = Simulation(field, cars)
            results = sim.run()

            print("\nAfter simulation, the result is:")
            for result in results:
                print(result)

            print_menu_end()
            end_choice = prompt("")
            if end_choice == "1":
                return True   # start over
            else:
                return False  # exit

        else:
            print("Invalid option. Please enter 1 or 2.")


def main() -> None:
    print("Welcome to Auto Driving Car Simulation!")
    while True:
        start_over = run_session()
        if not start_over:
            break
        print("\nWelcome to Auto Driving Car Simulation!")
    print("\nThank you for running the simulation. Goodbye!")


if __name__ == "__main__":
    main()
