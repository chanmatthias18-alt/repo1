"""
field.py – Represents the rectangular simulation grid.
"""


class Field:
    """
    A rectangular grid with bottom-left at (0,0) and
    top-right at (width-1, height-1).
    """

    def __init__(self, width: int, height: int) -> None:
        if width <= 0 or height <= 0:
            raise ValueError("Field dimensions must be positive integers.")
        self.width = width
        self.height = height

    def is_within_bounds(self, x: int, y: int) -> bool:
        """Return True if (x, y) lies inside the field."""
        return 0 <= x < self.width and 0 <= y < self.height

    def __str__(self) -> str:
        return f"{self.width} x {self.height}"
