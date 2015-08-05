from __future__ import absolute_import
from math import acos, sqrt

def lin_comb(a, X, b, Y):
    """Returns a linear combination aX+bY of vectors X, Y
    @a, b are floats
    @X, Y are (two-dimensional) arrays
    """

    X = map(lambda x: x * a, X)
    Y = map(lambda x: x * b, Y)
    return [X[0] + Y[0], X[1] + Y[1]]

def dot_product(a, b):
    """Return dot product of two vectors
    """
    return a[0] * b[0] + a[1] * b[1]

def magnitude(a):
    """Returns magnitude of a vector
    """
    return sqrt(a[0] * a[0] + a[1] * a[1])

def angle(a, b):
    """Returns angle between two vectors a, b
    """
    return acos(dot_product(a, b) / (magnitude(a) * magnitude(b)))

def vector(a, b):
    """Returns a vector from point a to point b
    """
    return vector_p(a[0], a[1], b[0], b[1])

def vector_p(ax, ay, bx, by):
    """Returns a vector from point a (ax, ay) to point b (bx, by)
    """
    return (bx - ax, by - ay)

def reverse(a):
    return [a[1], a[0]]

def to_str(a):
    return str(float(a[0])) + "," + str(float(a[1]))

def almost_eq(a, b, N):
    """Checks if coordinates of a, b differ by at most N
    """
    return (round(a[0], N) == round(b[0], N) and
            round(a[1], N) == round(b[1], N))
