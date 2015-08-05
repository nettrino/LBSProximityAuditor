"""ServiceAuditor wrapper on pykml
"""
from __future__ import absolute_import

import os
import random
from shapely.geometry import Point, Polygon, MultiPolygon
from pykml.factory import KML_ElementMaker as KML
from pykml import parser as kparser
from pykml.parser import Schema
from lxml import etree

from . import vector

class KMLParser(object):
    """KML/MultiPolygon conversions
    """

    schema_gx = Schema("kml22gx.xsd")

    def __init__(self, projection):
        self.proj = projection

    def _create_placemark(self, polygon):
        """Creates placemark node from projected polygon

        Args:
            @polygon: the polygon to provide coordinates from the placemark
        """
        placemark = KML.Placemark()

        # get exterior
        exterior = ""
        for coords in polygon.exterior.coords:
            (lon, lat) = self.proj(coords[0], coords[1], inverse=True)
            exterior += vector.to_str([lon, lat]) + " "
            kmlpoly = KML.Polygon()
            outer_boundary = KML.outerBoundaryIs(
                KML.LinearRing(
                    KML.coordinates(exterior)
                )
            )
            kmlpoly.append(outer_boundary)

        # get interior (holes in the polygon)
        for linear_ring in polygon.interiors:
            interior = ""
            for coords in linear_ring.coords:
                (lon, lat) = self.proj(coords[0], coords[1], inverse=True)
                interior += vector.to_str([lon, lat]) + " "

            inner_boundary = KML.innerBoundaryIs(
                KML.LinearRing(
                    KML.coordinates(interior)
                )
            )
            kmlpoly.append(inner_boundary)
            placemark.append(kmlpoly)

        return placemark


    def kml_from_poly(self, cut_poly, kmlfile):
        """Creates a kml file in lat/lon coordinates from polygon whose
        coordinates are in projected x/y coordinates

        Args:
            @input_poly: the polygon to be represented in the kmlfile
            @kmlfile:    the filename for the kml to be output
        """
        kml = KML.kml(
            KML.Document(
            )
        )
        if cut_poly.geom_type == "MultiPolygon":
            for p in cut_poly:
                pm = KML.Placemark()

                c = ""
                for coords in p.exterior.coords:
                        (lon, lat) = self.proj(coords[0],
                                               coords[1],
                                               inverse = True)
                        # TODO add flags for inverse
                        c += str(lon) + "," + str(lat) + " "
                poly = KML.Polygon()
                ob =  KML.outerBoundaryIs(
                            KML.LinearRing(
                                KML.coordinates(c)
                            )
                        )
                poly.append(ob)

                for linear_ring in p.interiors:
                    cin = ""
                    for c in linear_ring.coords:
                        (lon, lat) = self.proj(c[0], c[1], inverse = True)
                        # TODO add flags for inverse
                        cin += str(lon) + "," + str(lat) + " "

                    ib =  KML.innerBoundaryIs(
                                KML.LinearRing(
                                    KML.coordinates(cin)
                                )
                            )
                    poly.append(ib)
                pm.append(poly)
                kml.Document.append(pm)
        else:
            pm = KML.Placemark()

            c = ""
            for coords in cut_poly.exterior.coords:
                    (lon, lat) = self.proj(coords[0], coords[1], inverse = True)
                    # TODO add flags for inverse
                    c += str(lon) + "," + str(lat) + " "
            poly = KML.Polygon()
            ob =  KML.outerBoundaryIs(
                        KML.LinearRing(
                            KML.coordinates(c)
                        )
                    )
            poly.append(ob)

            for linear_ring in cut_poly.interiors:
                cin = ""
                for c in linear_ring.coords:
                    (lon, lat) = self.proj(c[0], c[1], inverse = True)
                    # TODO add flags for inverse
                    cin += str(lon) + "," + str(lat) + " "

                ib =  KML.innerBoundaryIs(
                            KML.LinearRing(
                                KML.coordinates(cin)
                            )
                        )
                poly.append(ib)
            pm.append(poly)
            kml.Document.append(pm)

        with open(kmlfile, "w") as outfile:
            outfile.write(etree.tostring(kml, pretty_print=True))

        # return kml to the caller
        return etree.tostring(kml, pretty_print=True)

    def poly_from_kml(self, kml_file):
        """Creates a MultiPOlygon from a kml file

        This is not a generic function and does not work with kml files
        of all formats. It only supports kml files as the default kml
        used by ServiceAuditor found in ../files/data

        Args:
            @kml_file: the kml file to be parsed
        """
        xpath_poly = ".//{http://www.opengis.net/kml/2.2}Polygon"

        if not os.path.isfile(kml_file):
            raise SystemExit("No such file")

        with open(kml_file) as kmlf:
            doc = kparser.parse(kmlf).getroot()
            multi = []
            for polygon in doc.Document.findall(xpath_poly):
                boundary = []
                boundstr = polygon.outerBoundaryIs.LinearRing.coordinates
                # get outer boundaries of polygon
                for poly in str(boundstr).rstrip().split(' '):
                    # transform with given projection
                    coords = poly.split(',')
                    # we ignore z coordinate
                    # XXX this assumes that coords are in format [lon, lat]!
                    coords = self.proj(float(coords[0]), float(coords[1]))
                    # add to polygon
                    boundary.append(coords)
                multi.append(Polygon(boundary))

        return MultiPolygon(multi)

    def random_from_polygon(self, poly, points_no):
        """Gets at most N distinct points from within polygon poly
        """
        (minx, miny, maxx, maxy) = poly.bounds
        count = 0
        points = []

        if points_no <= 0:
            return points

        p_x = random.uniform(minx, maxx)
        p_y = random.uniform(miny, maxy)
        point = Point(p_x, p_y)
        while count < points_no:
            while not poly.contains(point):
                p_x = random.uniform(minx, maxx)
                p_y = random.uniform(miny, maxy)
                point = Point(p_x, p_y)
            points.append((p_x, p_y))
            count += 1
        return points
