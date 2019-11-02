import math

import numpy


def cart2pol(x, y, in_deg=True):
    r = math.sqrt(pow(x, 2) + pow(y, 2))
    theta = math.atan2(y, x)

    if in_deg:
        theta = math.degrees(theta)

    return r, theta


def pol2cart(r, theta, in_degs=True):
    if in_degs:
        theta = (theta + 180) % 360 - 180
        theta = math.radians(theta)
    else:
        theta = (theta + (math.pi / 2)) % math.pi - (math.pi / 2)

    x = r * math.cos(theta)
    y = r * math.sin(theta)

    return x, y


def make_even_grid(n):
    nx = int(math.ceil(math.sqrt(n)))
    ny = int(math.ceil(float(n) / float(nx)))
    return nx, ny


def init_arrow_coords(dims, n):
    w, h = dims
    nx, ny = make_even_grid(n)

    xx = numpy.linspace(0, w, num=nx + 1, endpoint=False)[1:]
    yy = numpy.linspace(0, h, num=ny + 1, endpoint=False)[1:]

    yy, xx = numpy.meshgrid(yy, xx)
    xx, yy = numpy.ravel(xx), numpy.ravel(yy)
    xx, yy = xx[:n], yy[:n]
    xx, yy = (int(round(x)) for x in xx), (int(round(y)) for y in yy)

    return list(zip(xx, yy))
