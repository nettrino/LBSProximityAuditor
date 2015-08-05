from __future__ import absolute_import
from pyproj import Proj
import math

from . import earth

# lon_0 is the longitude axis which is used to center the projection.
# unless else noted, the projection's x axis origins at lon_0.
# lat_0 is used to designate a central parallel and associated y axis origin
# for several projections.
# x_0 and y_0 are refered to as false easting and false northing respectively.
# Unless the user specifies a value for these parameters, they all assume a
# zero value

# USA equidistant conic
# +proj=eqdc +lat_0=39 +lon_0=-96 +lat_1=33 +lat_2=45 +x_0=0 +y_0=0
# +datum=NAD83 +units=m +no_defs
us_eqdc = Proj(init = "esri:102005")

alaska = Proj(init = "esri:102006")

# North America equidistant conic
#+proj=eqdc +lat_0=40 +lon_0=-96 +lat_1=20 +lat_2=60 +x_0=0 +y_0=0
#+datum=NAD83 +units=m +no_defs
na_eqdc = Proj(init = "esri:102010")

# South America equidistant conic
# +proj=eqdc +lat_0=-32 +lon_0=-60 +lat_1=-5 +lat_2=-42 +x_0=0 +y_0=0
# +ellps=aust_SA +units=m +no_defs
sa_eqdc = Proj(init = "esri:102032")

# Europe equidistant conic
# +proj=eqdc +lat_0=30 +lon_0=10 +lat_1=43 +lat_2=62 +x_0=0 +y_0=0
# +ellps=intl +units=m +no_defs
eu_eqdc = Proj(init = "esri:102031")

# Asia South equidistant conic
# +proj=eqdc +lat_0=-15 +lon_0=125 +lat_1=7 +lat_2=-32 +x_0=0 +y_0=0
# +datum=WGS84 +units=m +no_defs
as_eqdc = Proj(init = "esri:102029")

# Asia North equidistant conic
# +proj=eqdc +lat_0=30 +lon_0=95 +lat_1=15 +lat_2=65 +x_0=0 +y_0=0
# +datum=WGS84 +units=m +no_defs
an_eqdc = Proj(init = "esri:102026")

# Afrika equidistant conic
# +proj=eqdc +lat_0=0 +lon_0=25 +lat_1=20 +lat_2=-23 +x_0=0 +y_0=0
# +datum=WGS84 +units=m +no_defs
af_eqdc = Proj(init = "esri:102026")

google = Proj(init = "epsg:3857")


class Projection():
    """Projection settings and error
    """
    def __init__(self, proj):
        if proj == "af":
            self.proj = af_eqdc
        elif proj == "an":
            self.proj = an_eqdc
        elif proj == "as":
            self.proj = as_eqdc
        elif proj == "eu":
            self.proj = eu_eqdc
        elif proj == "sa":
            self.proj = sa_eqdc
        elif proj == "na":
            self.proj = na_eqdc
        elif proj == "us":
            self.proj = us_eqdc
        elif proj == "al":
            self.proj = alaska
        else:
            # if none of the above, use Google Mercator
            self.proj = google

def proj_error(proj, p, R, angle = 0):
    """Error in the projected plane due to projection used.

    The error is calculated measuring a distance @R from point @p

    @R distance in m on sphere
    @angle is the angle for maximum distortion for the projection
    """

    (px, py) = proj(p[1], p[0])
    random_p = earth.point_on_earth(p[0], p[1], float(R) / 1000, angle)
    (rx, ry) = proj(random_p[1], random_p[0])

    # error is distance in projected coordinates - real
    return math.hypot(px - rx, py - ry) - R
