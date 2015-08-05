import math

from math import radians, cos, sin, asin, sqrt

#FIXME cleanup & check correctness
"""
Helper functions for calculations of points on Earth surface
"""

RADIUS = 6378.1

def distance_on_unit_sphere(lat1, lon1, lat2, lon2):
    """
    Calculate the great circle distance between two points
    on the earth (specified in decimal degrees)
    Taken from Michael Dunn's Stack Overflow answer at questions/4913349
    """
    # convert decimal degrees to radians
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
    # haversine formula
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a))
    km = RADIUS * c

    return km

def polar(x, y, R, phi):
    """PROJECTED COORDINATES on X-Y plane
    Get a point at angle phi and distance R from (x, y), in polar coordinates
    @x, y are projected coordinates
    @R is radius in meters
    @phi is angle in degrees
    """
    angle = math.radians(phi)
    return [x + R * math.cos(angle), y + R * math.sin(angle)]


def point_on_earth(lat, lon, dist, brng):
    """
    Get lat and lon from current point to given distance and bearing
    @lat:	latitude
    @lon:	longitude
    @dist:	distance from current point in km
    @brng:	bearing (in degrees)
    """
    # convert degree to radians
    brng = (90.0 - brng) * math.pi/180.0

    # convert current point to radians
    lat1 = math.radians(lat)
    lon1 = math.radians(lon)

    a1 = math.sin(lat1) * math.cos(dist/RADIUS)
    a2 = math.cos(lat1) * math.sin(dist/RADIUS) * math.cos(brng)
    lat2 = math.asin(a1 + a2)

    a1 = math.sin(brng) * math.sin(dist/RADIUS) * math.cos(lat1)
    a2 = math.cos(dist/RADIUS) - math.sin(lat1) * math.sin(lat2)

    lon2 = lon1 + math.atan2(a1, a2)

    lat2 = math.degrees(lat2)
    lon2 = math.degrees(lon2)

    # return latitude and longitude
    return [lat2, lon2]

def mile_to_km(dist_mile):
    return dist_mile * 1.609344

def km_to_mile(dist_km):
    return dist_km * 0.6213711922

def get_middle_point(coord1, coord2):
    '''
    Get middle coordinate between coord1 and coord2
    @coord1:       [lat1, lon1]
    @coord2:       [lat2, lon2]
    @return:      middle point [lat, lon]
    To get the middle point of parallelogram, get the middle point of
    one of diagonals
    '''
    # get lat and lon of each coord
    lat1 = coord1[0]
    lon1 = coord1[1]
    lat2 = coord2[0]
    lon2 = coord2[1]

    dlon = math.radians(lon2 - lon1)

    # convert points to radians
    lat1 = math.radians(lat1)
    lat2 = math.radians(lat2)
    lon1 = math.radians(lon1)

    bx = math.cos(lat2) * math.cos(dlon);
    by = math.cos(lat2) * math.sin(dlon);

    lat3 = math.atan2(
        math.sin(lat1) + math.sin(lat2),
        math.sqrt((math.cos(lat1) + bx) * (math.cos(lat1) + bx) + by * by))
    lon3 = lon1 + math.atan2(by, math.cos(lat1) + bx)

    lat3 = math.degrees(lat3)
    lon3 = math.degrees(lon3)

    return [lat3, lon3]
