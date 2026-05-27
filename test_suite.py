"""
tests/test_suite.py – Comprehensive test suite for the Auto Driving Car Simulation.

Run:
    python test_suite.py
    or
    pytest tests/ -v
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from field import Field
from car import Car
from simulation import Simulation


# ═══════════════════════════════════════════════════════════════════════
# FIELD TESTS
# ═══════════════════════════════════════════════════════════════════════

class TestField(unittest.TestCase):

    def test_valid_field_creation(self):
        f = Field(10, 10)
        self.assertEqual(f.width, 10)
        self.assertEqual(f.height, 10)

    def test_field_str(self):
        self.assertEqual(str(Field(10, 10)), "10 x 10")

    def test_within_bounds_corners(self):
        f = Field(10, 10)
        self.assertTrue(f.is_within_bounds(0, 0))   # bottom-left
        self.assertTrue(f.is_within_bounds(9, 9))   # top-right
        self.assertTrue(f.is_within_bounds(0, 9))   # top-left
        self.assertTrue(f.is_within_bounds(9, 0))   # bottom-right

    def test_outside_bounds(self):
        f = Field(10, 10)
        self.assertFalse(f.is_within_bounds(-1, 0))
        self.assertFalse(f.is_within_bounds(0, -1))
        self.assertFalse(f.is_within_bounds(10, 0))
        self.assertFalse(f.is_within_bounds(0, 10))
        self.assertFalse(f.is_within_bounds(10, 10))

    def test_invalid_field_zero_width(self):
        with self.assertRaises(ValueError):
            Field(0, 10)

    def test_invalid_field_negative(self):
        with self.assertRaises(ValueError):
            Field(-1, 10)

    def test_minimal_field(self):
        f = Field(1, 1)
        self.assertTrue(f.is_within_bounds(0, 0))
        self.assertFalse(f.is_within_bounds(1, 0))


# ═══════════════════════════════════════════════════════════════════════
# CAR TESTS
# ═══════════════════════════════════════════════════════════════════════

class TestCar(unittest.TestCase):

    def _car(self, name="A", x=5, y=5, direction="N", commands=""):
        return Car(name, x, y, direction, commands)

    def test_valid_car_creation(self):
        car = self._car()
        self.assertEqual(car.name, "A")
        self.assertEqual(car.x, 5)
        self.assertEqual(car.y, 5)
        self.assertEqual(car.direction, "N")
        self.assertFalse(car.collided)

    def test_invalid_direction(self):
        with self.assertRaises(ValueError):
            Car("A", 0, 0, "X", "")

    def test_invalid_command(self):
        with self.assertRaises(ValueError):
            Car("A", 0, 0, "N", "FFLZR")

    def test_empty_name(self):
        with self.assertRaises(ValueError):
            Car("", 0, 0, "N", "")

    # -- turning --

    def test_turn_left_from_north(self):
        car = self._car(direction="N")
        car.turn_left()
        self.assertEqual(car.direction, "W")

    def test_turn_right_from_north(self):
        car = self._car(direction="N")
        car.turn_right()
        self.assertEqual(car.direction, "E")

    def test_full_left_rotation(self):
        car = self._car(direction="N")
        for expected in ["W", "S", "E", "N"]:
            car.turn_left()
            self.assertEqual(car.direction, expected)

    def test_full_right_rotation(self):
        car = self._car(direction="N")
        for expected in ["E", "S", "W", "N"]:
            car.turn_right()
            self.assertEqual(car.direction, expected)

    def test_full_360_rotation(self):
        """Four right turns returns car to original direction without moving."""
        f   = Field(10, 10)
        car = Car("A", 5, 5, "N", "RRRR")
        sim = Simulation(f, [car])
        results = sim.run()
        self.assertEqual(results[0].direction, "N")
        self.assertEqual((results[0].x, results[0].y), (5, 5))

    # -- forward movement --

    def test_move_north(self):
        f   = Field(10, 10)
        car = self._car(x=5, y=5, direction="N")
        car.move_forward(f)
        self.assertEqual((car.x, car.y), (5, 6))

    def test_move_south(self):
        f   = Field(10, 10)
        car = self._car(x=5, y=5, direction="S")
        car.move_forward(f)
        self.assertEqual((car.x, car.y), (5, 4))

    def test_move_east(self):
        f   = Field(10, 10)
        car = self._car(x=5, y=5, direction="E")
        car.move_forward(f)
        self.assertEqual((car.x, car.y), (6, 5))

    def test_move_west(self):
        f   = Field(10, 10)
        car = self._car(x=5, y=5, direction="W")
        car.move_forward(f)
        self.assertEqual((car.x, car.y), (4, 5))

    # -- boundary clamping --

    def test_boundary_north(self):
        f   = Field(10, 10)
        car = self._car(x=5, y=9, direction="N")
        car.move_forward(f)
        self.assertEqual((car.x, car.y), (5, 9))  # stays put

    def test_boundary_south(self):
        f   = Field(10, 10)
        car = self._car(x=5, y=0, direction="S")
        car.move_forward(f)
        self.assertEqual((car.x, car.y), (5, 0))

    def test_boundary_east(self):
        f   = Field(10, 10)
        car = self._car(x=9, y=5, direction="E")
        car.move_forward(f)
        self.assertEqual((car.x, car.y), (9, 5))

    def test_boundary_west(self):
        f   = Field(10, 10)
        car = self._car(x=0, y=5, direction="W")
        car.move_forward(f)
        self.assertEqual((car.x, car.y), (0, 5))

    def test_car_str(self):
        car = Car("A", 1, 2, "N", "FFRFFFFRRL")
        self.assertEqual(str(car), "- A, (1,2) N, FFRFFFFRRL")

    def test_car_reverses_direction_and_returns(self):
        """Car moves forward 2, turns 180, moves forward 2 — back at start."""
        f       = Field(10, 10)
        car     = Car("A", 5, 5, "N", "FFLLFF")
        sim     = Simulation(f, [car])
        results = sim.run()
        self.assertEqual((results[0].x, results[0].y), (5, 5))
        self.assertEqual(results[0].direction, "S")


# ═══════════════════════════════════════════════════════════════════════
# SIMULATION TESTS
# ═══════════════════════════════════════════════════════════════════════

class TestSimulation(unittest.TestCase):

    def _run(self, field, cars):
        return Simulation(field, cars).run()

    # ── Scenario 1: single car ───────────────────────────────────────

    def test_scenario1_single_car(self):
        """Assignment Scenario 1: car A ends at (5,4) facing S."""
        f       = Field(10, 10)
        car     = Car("A", 1, 2, "N", "FFRFFFFRRL")
        results = self._run(f, [car])
        self.assertEqual(len(results), 1)
        r = results[0]
        self.assertFalse(r.collided)
        self.assertEqual(r.x, 5)
        self.assertEqual(r.y, 4)
        self.assertEqual(r.direction, "S")

    def test_scenario1_output_str(self):
        f       = Field(10, 10)
        car     = Car("A", 1, 2, "N", "FFRFFFFRRL")
        results = self._run(f, [car])
        self.assertEqual(str(results[0]), "- A, (5,4) S")

    # ── Scenario 2: two cars with collision ──────────────────────────

    def test_scenario2_collision(self):
        """Assignment Scenario 2: A and B collide at (5,4) at step 7."""
        f     = Field(10, 10)
        car_a = Car("A", 1, 2, "N", "FFRFFFFRRL")
        car_b = Car("B", 7, 8, "W", "FFLFFFFFFF")
        results = self._run(f, [car_a, car_b])
        ra, rb  = results[0], results[1]
        self.assertTrue(ra.collided)
        self.assertTrue(rb.collided)
        self.assertIn("(5,4)",  ra.collision_info)
        self.assertIn("step 7", ra.collision_info)
        self.assertIn("(5,4)",  rb.collision_info)
        self.assertIn("step 7", rb.collision_info)

    def test_scenario2_output_str(self):
        f     = Field(10, 10)
        car_a = Car("A", 1, 2, "N", "FFRFFFFRRL")
        car_b = Car("B", 7, 8, "W", "FFLFFFFFFF")
        results = self._run(f, [car_a, car_b])
        self.assertEqual(str(results[0]), "- A, collides with B at (5,4) at step 7")
        self.assertEqual(str(results[1]), "- B, collides with A at (5,4) at step 7")

    # ── No collision ─────────────────────────────────────────────────

    def test_two_cars_no_collision(self):
        """Two cars that never meet finish without collision."""
        f     = Field(10, 10)
        car_a = Car("A", 0, 0, "N", "FFF")
        car_b = Car("B", 9, 9, "S", "FFF")
        results = self._run(f, [car_a, car_b])
        self.assertFalse(results[0].collided)
        self.assertFalse(results[1].collided)
        self.assertEqual((results[0].x, results[0].y), (0, 3))
        self.assertEqual((results[1].x, results[1].y), (9, 6))

    def test_two_cars_same_direction_no_collision(self):
        """Car behind can never catch car in front at the same speed."""
        f     = Field(10, 10)
        car_a = Car("A", 0, 5, "E", "FFFF")  # starts behind
        car_b = Car("B", 2, 5, "E", "FFFF")  # starts in front
        results = self._run(f, [car_a, car_b])
        self.assertFalse(results[0].collided)
        self.assertFalse(results[1].collided)

    # ── Boundary behaviour ───────────────────────────────────────────

    def test_commands_ignored_at_boundary(self):
        """Forward commands at the wall are silently ignored."""
        f       = Field(10, 10)
        car     = Car("A", 0, 0, "S", "FFFF")
        results = self._run(f, [car])
        self.assertEqual((results[0].x, results[0].y), (0, 0))

    def test_car_stays_in_bounds_north_wall(self):
        f       = Field(5, 5)
        car     = Car("A", 2, 4, "N", "FFF")
        results = self._run(f, [car])
        self.assertEqual(results[0].y, 4)

    # ── Unequal command lengths ──────────────────────────────────────

    def test_unequal_command_lengths(self):
        """Car with fewer commands stops when commands run out."""
        f     = Field(10, 10)
        car_a = Car("A", 0, 0, "N", "F")
        car_b = Car("B", 5, 5, "S", "FFFFFFF")
        results = self._run(f, [car_a, car_b])
        self.assertEqual((results[0].x, results[0].y), (0, 1))
        self.assertEqual((results[1].x, results[1].y), (5, 0))

    # ── Empty simulation / no commands ───────────────────────────────

    def test_empty_simulation(self):
        f       = Field(10, 10)
        results = self._run(f, [])
        self.assertEqual(results, [])

    def test_car_with_no_commands(self):
        f       = Field(10, 10)
        car     = Car("A", 3, 3, "E", "")
        results = self._run(f, [car])
        self.assertEqual((results[0].x, results[0].y), (3, 3))
        self.assertEqual(results[0].direction, "E")

    def test_car_with_no_commands_in_multi_car_sim(self):
        """A car with no commands stays put and does not affect others."""
        f     = Field(10, 10)
        car_a = Car("A", 0, 0, "N", "")
        car_b = Car("B", 5, 5, "S", "FF")
        results = self._run(f, [car_a, car_b])
        self.assertFalse(results[0].collided)
        self.assertEqual((results[0].x, results[0].y), (0, 0))
        self.assertFalse(results[1].collided)

    # ── Turns only ───────────────────────────────────────────────────

    def test_turns_only_no_movement(self):
        f       = Field(10, 10)
        car     = Car("A", 5, 5, "N", "LLRR")
        results = self._run(f, [car])
        self.assertEqual((results[0].x, results[0].y), (5, 5))
        self.assertEqual(results[0].direction, "N")

    # ── Collision edge cases ─────────────────────────────────────────

    def test_collision_at_step_1(self):
        """Two cars facing each other one cell apart collide at step 1."""
        f     = Field(10, 10)
        car_a = Car("A", 4, 5, "E", "F")
        car_b = Car("B", 5, 5, "W", "F")
        results = self._run(f, [car_a, car_b])
        self.assertTrue(results[0].collided)
        self.assertTrue(results[1].collided)
        self.assertIn("step 1", results[0].collision_info)

    def test_collided_car_stops(self):
        """After collision, cars stop moving."""
        f     = Field(10, 10)
        car_a = Car("A", 4, 5, "E", "FFFF")
        car_b = Car("B", 5, 5, "N", "FFFF")
        results = self._run(f, [car_a, car_b])
        self.assertTrue(results[0].collided)
        self.assertEqual(results[0].x, 5)
        self.assertEqual(results[0].y, 5)

    def test_two_cars_same_starting_position(self):
        """Cars starting at the same position collide at step 1."""
        f     = Field(10, 10)
        car_a = Car("A", 5, 5, "N", "FFF")
        car_b = Car("B", 5, 5, "S", "FFF")
        results = self._run(f, [car_a, car_b])
        self.assertTrue(results[0].collided)
        self.assertTrue(results[1].collided)

    def test_third_car_collides_with_already_collided_cars(self):
        """A third car hitting a frozen collision site is also marked collided."""
        f     = Field(10, 10)
        # A moves east into B's cell at step 1 → both collide at (5,5)
        car_a = Car("A", 4, 5, "E", "FF")
        car_b = Car("B", 5, 5, "N", "FF")
        # C moves north and arrives at (5,5) at step 2
        car_c = Car("C", 5, 3, "N", "FF")
        results = self._run(f, [car_a, car_b, car_c])
        self.assertTrue(results[2].collided)

    # ── Three cars ───────────────────────────────────────────────────

    def test_three_cars_two_collide_one_survives(self):
        """Two cars collide; the third continues unaffected."""
        f     = Field(10, 10)
        car_x = Car("X", 3, 5, "E", "FF")   # moves to (4,5) then (5,5)
        car_y = Car("Y", 5, 5, "W", "FF")   # moves to (4,5) → collision at step 1
        car_z = Car("Z", 0, 0, "N", "FF")   # unaffected
        results = self._run(f, [car_x, car_y, car_z])
        collided = [r for r in results if r.collided]
        survived = [r for r in results if not r.collided]
        self.assertEqual(len(collided), 2)
        self.assertEqual(len(survived), 1)
        self.assertEqual(survived[0].name, "Z")


# ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    loader = unittest.TestLoader()
    suite  = unittest.TestSuite()
    for cls in [TestField, TestCar, TestSimulation]:
        suite.addTests(loader.loadTestsFromTestCase(cls))
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)
