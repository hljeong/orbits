from __future__ import annotations
from dataclasses import dataclass
from functools import singledispatchmethod, cache
from itertools import pairwise
from threading import Thread
from time import sleep
from tkinter import Tk, Canvas as TkCanvas

DEFAULT_DELTA_T: float = 0.05
MAX_DURATION: float = 120
MAX_FRAMES: int = int(MAX_DURATION / DEFAULT_DELTA_T)

G: float = 1.0


class Shape:
    pass


# todo: profile performance hit by setting slots=False
@dataclass(frozen=True, slots=True)
class Vector:
    x: float = 0
    y: float = 0

    def __add__(self, other: Vector) -> Vector:
        if type(other) is not Vector:
            return NotImplemented
        return Vector(self.x + other.x, self.y + other.y)

    def __sub__(self, other: Vector) -> Vector:
        if type(other) is not Vector:
            return NotImplemented
        return Vector(self.x - other.x, self.y - other.y)

    def __mul__(self, c: float) -> Vector:
        return Vector(c * self.x, c * self.y)

    def __rmul__(self, c: float) -> Vector:
        return self * c

    def __truediv__(self, d: float) -> Vector:
        return Vector(self.x / d, self.y / d)

    def __abs__(self) -> float:
        return (self.x * self.x + self.y * self.y) ** 0.5


@dataclass(frozen=True, slots=True)
class BBox:
    min: Vector
    max: Vector

    @property
    @cache
    def as_tuple(self) -> tuple[float, float, float, float]:
        return (self.min.x, self.min.y, self.max.x, self.max.y)

    def __add__(self, d: Vector) -> BBox:
        return BBox(self.min + d, self.max + d)

    def __radd__(self, d: Vector) -> BBox:
        return self + d


@dataclass(frozen=True, slots=True)
class Circle(Shape):
    o: Vector
    r: float

    @property
    @cache
    def bbox(self) -> BBox:
        return BBox(
            Vector(self.o.x - self.r, self.o.y - self.r),
            Vector(self.o.x + self.r, self.o.y + self.r),
        )

    def __add__(self, d: Vector) -> Circle:
        return Circle(self.o + d, self.r)

    def __radd__(self, d: Vector) -> Circle:
        return self + d


@dataclass(frozen=True, slots=True)
class Curve(Shape):
    points: tuple[Vector, ...]

    def __add__(self, d: Vector) -> Curve:
        return Curve(tuple(p + d for p in self.points))

    def __radd__(self, d: Vector) -> Curve:
        return self + d


@dataclass(frozen=True, slots=True)
class Scene:
    shapes: tuple[Shape, ...]


class Canvas:
    def __init__(self, w, h):
        self.root: Tk = Tk()
        self.w, self.h = w, h
        self.o = Vector(w / 2, h / 2)
        self.canvas = TkCanvas(self.root, width=w, height=h, bg="#000")
        self.canvas.pack()

    def start(self):
        self.root.mainloop()

    def render(self, scene: Scene):
        for shape in scene.shapes:
            self.render_shape(shape)

    def clear(self):
        self.canvas.delete("all")

    @singledispatchmethod
    def render_shape(self, _: Shape):
        raise NotImplementedError()

    @render_shape.register
    def render_circle(self, c: Circle):
        self.canvas.create_oval((self.o + c.bbox).as_tuple, outline="#fff")

    @render_shape.register
    def render_curve(self, c: Curve):
        for p1, p2 in pairwise(c.points):
            shifted_p1 = self.o + p1
            shifted_p2 = self.o + p2
            self.canvas.create_line(
                shifted_p1.x, shifted_p1.y, shifted_p2.x, shifted_p2.y, fill="#fff"
            )


class Universe:
    def __init__(self):
        self.yellow_r: float = 50.0
        self.yellow_m: float = 5000000.0
        self.yellow_p: Vector = Vector(0, 0)

        self.blue_r: float = 15.0
        self.blue_m: float = 3000.0
        self.blue_p: Vector = Vector(200, 0)
        self.blue_v: Vector = Vector(
            0, -(((G * self.yellow_m) / abs(self.blue_p - self.yellow_p)) ** 0.5)
        )
        self.blue_trail: list[Vector] = []

        self.white_r: float = 5.0
        self.white_m: float = 100.0
        self.white_p: Vector = Vector(200, 30)
        self.white_v: Vector = Vector(
            0, -(((G * self.yellow_m) / abs(self.white_p - self.yellow_p)) ** 0.5)
        )
        self.white_trail: list[Vector] = []

    @property
    def scene(self) -> Scene:
        return Scene(
            (
                Circle(self.yellow_p, self.yellow_r),
                Circle(self.blue_p, self.blue_r),
                # Curve(tuple(self.blue_trail)),
                Circle(self.white_p, self.white_r),
                # Curve(tuple(self.white_trail)),
            )
        )

    def update(self, delta_t: float = DEFAULT_DELTA_T):
        self.blue_trail.append(self.blue_p)
        while len(self.blue_trail) > 2.0 / delta_t:
            self.blue_trail.pop(0)

        self.blue_p = self.blue_p + self.blue_v * delta_t
        d: Vector = self.blue_p - self.yellow_p
        self.blue_v = self.blue_v - G * self.yellow_m * d / (abs(d) ** 3) * delta_t

        self.white_trail.append(self.white_p)
        while len(self.white_trail) > 2.0 / delta_t:
            self.white_trail.pop(0)

        self.white_p = self.white_p + self.white_v * delta_t
        dyellow: Vector = self.white_p - self.yellow_p
        dblue: Vector = self.white_p - self.blue_p
        self.white_v = (
            self.white_v
            - G * self.yellow_m * dyellow / (abs(dyellow) ** 3) * delta_t
            - G * self.blue_m * dblue / (abs(dblue) ** 3) * delta_t
        )


universe: Universe = Universe()


def loop(canvas: Canvas, frame_num: int) -> bool:
    canvas.o = Vector(
        canvas.w / 2 - universe.blue_p.x, canvas.h / 2 - universe.blue_p.y
    )
    canvas.render(universe.scene)
    universe.update()
    return frame_num < MAX_FRAMES


def run(canvas: Canvas, delta_t: float = DEFAULT_DELTA_T):
    frame_num: int = 0
    while loop(canvas, frame_num):
        frame_num += 1
        sleep(delta_t)
        canvas.clear()


def main():
    canvas: Canvas = Canvas(800, 600)
    mainloop = Thread(target=run, args=[canvas])
    mainloop.start()
    canvas.start()
    mainloop.join()


if __name__ == "__main__":
    main()
