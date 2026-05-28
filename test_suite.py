"""
tests/test_suite.py – Test suite for the Auto Driving Car Simulation.

Run:
    python test_suite.py
    or
    pytest tests/ -v
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from field import Field
from car import Car
from simulation import Simulation


# FIELD TESTS

class TestField(unittest.TestCase):

    def test_valid_field_creation(self):
        f = Field(10, 10)
        self.assertEqual(f.width, 10)
        self.assertEqual(f.height, 10)

    def test_invalid_field_zero_width(self):
        with self.assertRaises(ValueError):
            Field(0, 10)


# CAR TESTS

class TestCar(unittest.TestCase):

    def test_invalid_direction(self):
        with self.assertRaises(ValueError):
            Car("A", 0, 0, "X", "")

    def test_invalid_command(self):
        with self.assertRaises(ValueError):
            Car("A", 0, 0, "N", "FFLZR")

    def test_full_360_rotation(self):
        """Four right turns returns car to original direction without moving."""
        f       = Field(10, 10)
        car     = Car("A", 5, 5, "N", "RRRR")
        results = Simulation(f, [car]).run()
        self.assertEqual(results[0].direction, "N")
        self.assertEqual((results[0].x, results[0].y), (5, 5))

    def test_boundary_north(self):
        """Forward command at the north wall is silently ignored."""
        f   = Field(10, 10)
        car = Car("A", 5, 9, "N", "F")
        car.move_forward(f)
        self.assertEqual((car.x, car.y), (5, 9))

    def test_commands_ignored_at_boundary(self):
        """Forward commands at the south wall are silently ignored."""
        f       = Field(10, 10)
        car     = Car("A", 0, 0, "S", "FFFF")
        results = Simulation(f, [car]).run()
        self.assertEqual((results[0].x, results[0].y), (0, 0))

    def test_car_with_no_commands(self):
        """Car with no commands stays at starting position."""
        f       = Field(10, 10)
        car     = Car("A", 3, 3, "E", "")
        results = Simulation(f, [car]).run()
        self.assertEqual((results[0].x, results[0].y), (3, 3))
        self.assertEqual(results[0].direction, "E")


# SIMULATION TESTS

class TestSimulation(unittest.TestCase):

    def _run(self, field, cars):
        return Simulation(field, cars).run()

    # ── Scenario 1: single car ───────────────────────────────────────

    def test_scenario1_single_car(self):
        """Assignment Scenario 1: car A ends at (5,4) facing S."""
        f       = Field(10, 10)
        car     = Car("A", 1, 2, "N", "FFRFFFFRRL")
        results = self._run(f, [car])
        r = results[0]
        self.assertFalse(r.collided)
        self.assertEqual(r.x, 5)
        self.assertEqual(r.y, 4)
        self.assertEqual(r.direction, "S")

    def test_scenario1_output_str(self):
        """Assignment Scenario 1: exact output format."""
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
        """Assignment Scenario 2: exact output format."""
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

    def test_three_cars_two_collide_one_survives(self):
        """Two cars collide; the third continues unaffected."""
        f     = Field(10, 10)
        car_x = Car("X", 3, 5, "E", "FF")
        car_y = Car("Y", 5, 5, "W", "FF")
        car_z = Car("Z", 0, 0, "N", "FF")
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
