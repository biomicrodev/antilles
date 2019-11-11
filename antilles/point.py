from __future__ import annotations

from typing import Union


class Int2D:
    def __init__(self, x: Union[float, int] = None, y: Union[float, int] = None):
        """
        Helper class for managing tuples of two integers. Operations with these happens
        often enough that abstracting away some of the behavior helps a lot, especially
        the transformations.

        :param x: float or int, cast to int
        :param y: float or int, cast to int
        """
        self.x: int = x
        self.y: int = y

    @property
    def x(self) -> int:
        return self.__x

    @x.setter
    def x(self, val: Union[float, int]) -> None:
        self.__x = int(round(val))

    @property
    def y(self) -> int:
        return self.__y

    @y.setter
    def y(self, val: Union[float, int]) -> None:
        self.__y = int(round(val))

    def __str__(self):
        return f"Int2D({self.x}, {self.y})"

    def __len__(self):
        return 2

    def __iter__(self):
        return self.x, self.y

    def __add__(self, point):
        return Int2D(self.x + point.x, self.y + point.y)

    def __sub__(self, point):
        return Int2D(self.x - point.x, self.y - point.y)

    def __mul__(self, factor):
        return Int2D(self.x * factor, self.y * factor)

    def __rmul__(self, factor):
        return self * factor

    def __imul__(self, factor):
        self.x *= factor
        self.y *= factor
