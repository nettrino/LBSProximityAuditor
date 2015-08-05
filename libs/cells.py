"""Polygon and grid implementation
"""
from __future__ import absolute_import
import sys
import math
from math import sqrt
from shapely.geometry import LineString, Polygon, Point
import random

from . import projections

def circle(lat, lon, R, proj):
    (x, y) = proj(lon, lat)
    return Point(x, y).buffer(R)

def check_if_in(proj, poly, point, is_latlon = True):
    """Check if point is inside polygon. Polygon is given in projected
    coordinates

    @proj: projection used
    @point: coordinates of the point (either proj or lat lon)
    """
    if is_latlon:
        (proj_v_x, proj_v_y) = proj(point[1], point[0])
    else:
        proj_v_x = point[0]
        proj_v_y = point[1]

    if Point(proj_v_x, proj_v_y).within(poly):
        is_in = True
    else:
        if not __debug__:
            print "\t\t\tOUT"
            is_in = False
            return is_in

def cut(poly, proj, R, grid):
    """Takes a polygon and a radius R and returns the coordinates
    of a circle (p;R) which cuts the polygon in half.
    The returned coordinates are in projected plane.

    @poly: 	polygon to be cut in half (in PROJECTED COORDINATES)
    @proj: 	projection used
    @R: 	radius of circle used for cutting in km
    @grid_point_dist: the distance of point to be used in the grid
    @err_adj: account for errors of the projection
    """
    R = R * 1000

    (minx, miny, maxx, maxy) = poly.bounds
    half = poly.area / 2
    if half < 1000:
        grid = 1

    # get shortest polygon part
    if ((maxx - minx) <= (maxy - miny)):
        # if x side is shortest, or circle has to be at
        # least as big as the y half side
        E = (maxy - miny) / 2000

        # refine grid
        px = (minx + maxx) / 2

        # max_pos and min_pos hold the min and max value for the edge of the
        # circle for various cases and we perform a binary search
        min_pos = py = miny - R
        max_pos = maxy - R

        it = 0 # debug purposes
        best_py = py
        best_diff = sys.maxint
        while min_pos < max_pos:
            py = (min_pos + max_pos) / 2
            cut_area = 0
            (lon, lat) = proj(px, py, inverse = True)
            R += projections.proj_error(proj, [lat, lon], R, 0)
            cut_circle = Point(px, py).buffer(R)

            if poly.geom_type == "MultiPolygon":
                for p in poly:
                    cut_inter = p.intersection(cut_circle)
                    cut_area += cut_inter.area
            else:
                cut_area = poly.intersection(cut_circle).area

            diff = int(half - cut_area)
            if math.fabs(diff) < best_diff:
                best_diff = math.fabs(diff)
                best_py = py
            if diff < 0:
                # cut is bigger than half
                max_pos = py - grid
            elif diff > 0:
                min_pos = py + grid
            else:
                break
            it += 1

        # Get best of all
        py = best_py
    else:
        # if y side is shortest, or circle has to be at least
        # as big as the x half side
        py = (miny + maxy) / 2

        # max_pos and min_pos hold the min and max value for the edge of the
        # circle for various cases and we perform a binary search
        min_pos = px = minx - R
        max_pos = maxx - R
        it = 0

        # keep best out of iterations
        best_px = px
        best_diff = sys.maxint
        while min_pos < max_pos:
            px = (min_pos + max_pos) / 2
            cut_area = 0
            (lon, lat) = proj(px, py, inverse = True)
            R += projections.proj_error(proj, [lat, lon], R, 0)
            cut_circle = Point(px, py).buffer(R)
            if poly.geom_type == "MultiPolygon":
                for p in poly:
                    cut_inter = p.intersection(cut_circle)
                    cut_area += cut_inter.area
            else:
                cut_area = poly.intersection(cut_circle).area

            diff = int(half - cut_area)
            if math.fabs(diff) < best_diff:
                best_diff = math.fabs(diff)
                best_px = px
            if diff < 0:
                # cut is bigger than half
                max_pos = px - grid
            elif diff > 0:
                min_pos = px + grid
            else:
                break
            it +=1
        # Get best of all
        px = best_px

    (lon, lat) = proj(px, py, inverse=True)
    print "\t\tCutting from " + str([lat, lon])
    return [px, py]

def get_random_points_in_polygon(poly, N):
    """Gets at most N distinct points from within polygon poly
    Attention: randomness is not strong
    """
    INVALID_X = -9999
    INVALID_Y = -9999

    (minx, miny, maxx, maxy) = poly.bounds
    count = 0
    points = []

    if N <=0:
        return points

    while count < N:
        p = Point(INVALID_X, INVALID_Y)
        while not poly.contains(p):
            p_x = random.uniform(minx, maxx)
            p_y = random.uniform(miny, maxy)
            p = Point(p_x, p_y)
            points.append((p_x, p_y))
            count += 1
            return points

def poly_centroid(poly, proj):
    """Returns the real centroid coordinates for a given projected polygon
    """
    centr = poly.centroid.wkt.split('(')[1].split(')')[0].split(' ')
    (lon, lat) = proj(float(centr[0]), float(centr[1]), inverse = True)
    return [lat, lon]

def ring(lat, lon, R, r, proj, EC=2.5):
    """Creates a ring defined by two circles with radiuses r, R
    centered at x, y

    Args:
        lat, lon:   latitude and longitude
        R: outer radius of the ring in m
        r: inner radius of the ring in m
        proj. projection used
        EC: correction parameter
    """
    if R == r:
        return None

    # get projected coordinates
    (x, y) = proj(lon, lat)

    # error adjust rings
    error_r = EC * projections.proj_error(proj, [lat, lon], r, 0)
    error_R = EC * projections.proj_error(proj, [lat, lon], R, 0)

    r -= math.fabs(error_r)
    R += math.fabs(error_R)

    if R > r:
        outer_circle = Point(x, y).buffer(R)
        inner_circle = Point(x, y).buffer(r)
    else:
        outer_circle = Point(x, y).buffer(r)
        inner_circle = Point(x, y).buffer(R)

    ring = outer_circle.difference(inner_circle)

    return ring

class Cells(object):
    """Cell grid with hexagons and polygon implementation
    """
    def __init__(self, proj):
        # Dictionary to hold points in grid
        self.pdict = {}
        self.projection = proj

    def __check_and_add(self, x, y, poly, R):
        """
        Checks if the circle (@x, @y, @R) intersects with the polygon @poly
        If so, it adds the points to the dictionary
        """
        if Point(x,y).buffer(R).intersects(poly):
            self.pdict[(int(x), int(y))] = 1

    def create_cell(self, p_coords, poly, R, pos):
        """
        Creates a cell around a point with coordinates @p_coords,
        for a given cell density R and polygon. Depending on where the point is,
        not all vertices of its cell have an intersection with the polygon.Thus,
        when creating the cell, for each vertex ("neighbour") to the point, we
        need to check whether the corresponding circle of the vertex intersects
        with the polygon

        @p_coords: 	[lat, lon] for of the point which is the cell center
        @poly: 		The polygon for which we construct the grid
        @R: 		The density of the cell grid. This is the radius of each
        circle in the cell vertices and center
        @pos: 		Position of the point.
        """
        x = p_coords[0]
        y = p_coords[1]
        R = float(R)
        r3= R * sqrt(3)
        gridy = 3 * R / 2

        self.__check_and_add(x + r3, y, poly, R)
        self.__check_and_add(x + r3/2, y - gridy, poly, R)
        self.__check_and_add(x - r3/2, y - gridy, poly, R)
        self.__check_and_add(x - r3, y, poly, R)
        self.__check_and_add(x - r3/2, y + gridy, poly, R)
        self.__check_and_add(x + r3/2, y + gridy, poly, R)

    def cell_points_x(self, poly, inter, grid, R, start_p, ypoint):
        """
        Creates cells in a line parallel to x axis passing through point ypoint

        @poly:  	the polygon we are gcreating the grid in
        @inter: 	is the intersection of the parallel line with the polygon
        @grid: 		the distance between vertices in the x axis
        @R: 		the radius of each circle places in a vertex
        @start_p: 	starting point for the cell. The grid has to be consistent,
        so it does not always start at the beginning of the
        intersection with the polygon
        """
        ipoints = list(inter.coords)

        # Get minimux x of intersection
        minx = ipoints[0][0]
        maxx = ipoints[-1][0]

        # align intersection with grid
        start = minx + grid - (minx - start_p) % grid

        # get the starting point
        i = start

        # Go all the way up to maxx + grid as we check for intersection with
        # a circle of size grid
        while (i < maxx + grid):
            # Add point to grid
            # We are working with ints because we are using a dictionary
            # Not much precision lost since we work on the projection
            self.pdict[(int(i), int(ypoint))] = 1
            self.create_cell((i, ypoint), poly, R, 0)
            i += grid

    def construct_grid_in_polygon(self, poly, R):
        """
        Constructs a cell-like grid inside a polygon
        @poly: 	the polygon
        @R: 	the radius of the circle to be placed on each vertex in m
        """
        (minx, miny, maxx, maxy) = poly.bounds

        xpoint = minx
        ypoint = miny

        # only increase y by 3*R/2 and take parallel horizontal lines
        grid = float(R) * sqrt(3)
        grid_start = [xpoint - grid/2, xpoint]
        grid_pos = 0

        #FIXME do we need extra iteration in y?
        while ypoint <= maxy:
            grid_s = grid_start[grid_pos]

            # get interseciton points of current parallel with the multipolygon
            line = LineString([(minx, ypoint), (maxx, ypoint)])
            inter = poly.intersection(line)

            if inter.geom_type == "Point":
                coords = list(inter.coords)

            if inter.geom_type == "LineString":
                self.cell_points_x(poly, inter, grid, R, grid_s, ypoint)
            elif inter.geom_type == "MultiLineString":
                for line in inter.geoms:
                    self.cell_points_x(poly, line, grid, R, grid_s, ypoint)

            grid_pos = 1 - grid_pos
            ypoint += 3 * float(R) / 2

    def construct_grid_in_circle(self, x, y, R, r):
        """Creates a grid of cells inside a circle of radius R centered around
        (x, y) Cell form - Hexagon (six circles and a center circle):
            In each of the cell vertices we place a circle of radius r.

        @x: latitude of circle where the grid will be created
        @y: longitude of circle where the grid will be created
        @R: radius of circle where the grid will be created
        @r: radius of each circle to be placed in the edges of each cell
        """

        # map projection of the points
        (px, py) = self.projection(y, x)

        # circle arround the point
        circle = Point(px, py).buffer(R)
        coords = circle.exterior.coords

        # create a polygon from the circle points
        boundary = []
        for p in coords:
            c = (int(p[0]), int(p[1]))
            boundary.append(c)

        # construct the grid
        self.construct_grid_in_polygon(Polygon(boundary), r)

