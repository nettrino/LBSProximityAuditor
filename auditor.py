"""ServiceAuditor

Copyright (c) 2014, Columbia University
All rights reserved.

This software was developed by (alphabetically)

George Argyros <argyros@cs.columbia.edu>
Theofilos Petsios <theofilos@cs.columbia.edu>
Jason Polakis <polakis@cs.columbia.edu>
Suphannee Sivakorn <suphannee@cs.columbia.edu>

and developed by Theofilos Petsios at Columbia University, New York, NY,
USA, in November 2014. You should receive a copy of the GPLv3 license
with this document.
"""
from __future__ import absolute_import
from time import time, sleep
from random import randint, uniform
import math
import random

from libs import earth
from libs import projections as pr
from libs import verbose as vb
from auditor_db import AuditorDB
from auditor_user import AuditorUser
from auditor_exception import AuditorException, AuditorExceptionUnknown
import auditor_discovery_attack
import auditor_constants as const

class Auditor(object):
    """Class implementing basic auditing of the service

    Inhereted classes should implement the following functions:
        auditor_get_distance(user_a, user_b)
        auditor_set_location(user, lat, lon)

    Each of these functions should raise an Exception in case of an error
    otherwise return its result and the number of queries required to perform
    the operation in a tuple of the form (result, queries)
    """

    # TODO check with logging const.LOG.NORMAL to see if any issues occur
    def __init__(self, service_name, user_list, oracle=None, proj=pr.us_eqdc,
                 logging=const.LOG.ALL, verbose=True):
        """Initializes a Proximity Auditor for service @service_name

            Args:
                service_name: the name of the service to be audited
                users_list  : a list of user accounts to be used in the auditing
                oracle      : a custom proximity oracle defined by the user
                proj        : projection used. Defaults to US equidistant
                logging     : LOG.ALL to log all queries, LOG.STANDARD to only
                              log number of queries per user
                verbose     : verbose output of the testing stages
        """
        # initialize database
        self._db = AuditorDB()
        self._db.connect()

        # initialize service
        self._db.insert_service(service_name)
        self.__serv_name = service_name
        self.service_id = self._db.get_service_id(service_name)

        # initialize users
        if type(user_list) != list:
            raise TypeError("Constructor is expecting a list of users")

        # user ids as specified by the inherited class
        self.users = user_list

        # insert all users in database if they don't exist
        for user in user_list:
            self._db.insert_user(user, self.service_id)

        # set verbose output
        self.verbose = verbose

        # set log level in database
        if logging != const.LOG.STANDARD and logging != const.LOG.ALL:
            raise TypeError("logging options are only STANDARD or ALL")

        self.proj = proj
        self.logging = logging
        self.oracle = oracle

        #
        #
        # To be used during testing
        #
        #
        self.test_id = None
        self.attackers = None
        self.attacker = None
        self.victim = None

        #
        #
        # To be determined from tests
        #
        #

        #
        # speed limit
        #
        self.speed_limit = None

        #
        # query limits
        #
        # absolute limit on queries (global)
        self.absq_limit = None
        # queries per minute limit (global)
        self.qps_limit = None

        # absolute limit on update queries
        self.absq_u_limit = None
        # queries per minute limit on update queries
        self.qps_u_limit = None

        # absolute limit on update queries
        self.absq_r_limit = None
        # queries per minute limit on update queries
        self.qps_r_limit = None

        # Generic limit to be used in experiments
        self.query_limit = None

        #
        # accuracy of dudp and rudp attacks
        #
        self.dudp_accuracy = None
        self.rudp_accuracy = None

        #
        # other characteristics of the service
        #
        self.service_verifies_location = None

    def __del__(self):
        """Update service limits on db before cleanup and close connection
        """
        self._db.update_service(self.service_id,
                                self.speed_limit,
                                self.absq_limit,
                                self.qps_limit,
                                self.dudp_accuracy,
                                self.rudp_accuracy,
                                self.service_verifies_location)
        self._db.close_connection()


    #
    #
    #
    #
    #   SETTERS & GETTERS
    #
    #
    #
    #

    def set_query_limit(self, limit):
        self.query_limit = limit


    #
    #
    #
    #
    #   TESTS
    #
    #
    #
    #

    def _update_attacker(self):
        """Get a new attacker from the available users
        """
        if len(self.attackers) == 0:
            raise SystemExit("Run out of attackers")

        vb.vb_print(self.verbose, " *** updating attacker ***", None, True)
        self.attacker = self.attackers.pop()
        # sleep for some period
        sleep(10)


    #
    #
    #   Speed Limits
    #
    #

    def test_speed_limit(self, users=None):
        """Run a speed limit test binary searching for the max allowed speed
        """

        vb.vb_print(self.verbose, "Initiating speed limit test")

        if users is None:
            users = self._db.get_ordered_users()

        self.attackers = [AuditorUser(self.service_id, u) for u in users]
        self.attacker = self.attackers.pop()

        self._db.insert_test("speed_limit")
        self.test_id = self._db.get_test_id("speed_limit")

        # set a sleep time between queries
        sleep_time = 5

        # First we test teleportation: No speed constraints.
        # We set the user in New York and subsequently in San Fransisco
        # Hardcode coordinates for first check
        (ny_lat, ny_lon) = (40.708306, -74.008839)
        (sf_lat, sf_lon) = (37.761398, -122.415413)

        vb.vb_print(self.verbose, "testing teleportation", "speed-limit", True)

        # place user in New York
        (success, queries) = self.auditor_handled_place_at_coords(self.attacker,
                                                                  ny_lat,
                                                                  ny_lon,
                                                                  self.test_id)
        if not success:
            raise SystemExit("Could not place user at New York")

        # Wait some time for the query to be processed.
        sleep(sleep_time)

        # Teleport!
        (success, queries) = self.auditor_handled_place_at_coords(self.attacker,
                                                                  sf_lat,
                                                                  sf_lon,
                                                                  self.test_id)
        # Wait some time for the query to be processed.
        sleep(sleep_time)

        if success:
            # back in New York!
            (success, q_n) = self.auditor_handled_place_at_coords(self.attacker,
                                                                  ny_lat,
                                                                  ny_lon,
                                                                  self.test_id)

            # Wait some time for the query to be processed.
            sleep(sleep_time)

            if success:
                self.speed_limit = None
                vb.vb_print(self.verbose, " |->..Success!", "speed-limit", True)
                return None

        vb.vb_print(self.verbose, " |->..Failed", "speed-limit", True)
        # If we could not teleport, binary search in distances

        # Hardcode max speed in km/h
        [min_speed, max_speed] = [1, 1024]

        vb.vb_print(self.verbose, "Searching cut-off", "speed-limit", True)
        while min_speed < max_speed:
            cur_speed = float(min_speed + max_speed) / 2
            dist = float(cur_speed * sleep_time) / 3600

            # output speed if verbose
            vb.vb_print(self.verbose,
                        " |--current speed: " + str(cur_speed),
                        "speed-limit",
                        True)

            # keep a bearing of 70 degrees to make sure we place
            # the user over mainland and not at sea
            (success, q_no) = self.auditor_handled_place_at_dist(self.attacker,
                                                                 dist,
                                                                 70,
                                                                 self.test_id)
            if success:
                # if we succeeded increase min to cur_speed
                min_speed = cur_speed
            else:
                # if we are blocked change attacker
                self._update_attacker()
                max_speed = cur_speed
            # sleep till the next query
            sleep(sleep_time)

        self.speed_limit = cur_speed
        return cur_speed


    #
    #
    #   Query Limits
    #
    #

    def test_query_limit(self, users=None, rate_limit_only=False, rate=2):
        """Initializes a test for speed constraints
        @users: a user list to be used for this experiment
        @rate_limit_only:   only check rate limiting (do not attempt continuous
                            queries but only a certain number of queries / min)
        @rate: start rate limiting check with this many queries per second and
                adjust accordintgly.
        """

        vb.vb_print(self.verbose, "Initiating query limit test")

        if users is None:
            users = self._db.get_ordered_users()

        if len(users) == 1:
            raise SystemExit("Not enough users! At least two users required")

        self.attackers = [AuditorUser(self.service_id, u) for u in users]
        self.attacker = self.attackers.pop()
        victim = self.attackers.pop(0)

        self._db.insert_test("query_limit")
        self.test_id = self._db.get_test_id("query_limit")

        # limit on update location queries
        self.qps_u_limit = self._query_rate_limit_update(rate_limit_only,
                                                         rate)

        # limit on get_distance queries
        self.qps_r_limit = self._query_rate_limit_request(rate_limit_only,
                                                          rate)

        # total query limit should be the minimum of update/request limits
        self.absq_limit = math.min(self.absq_u_limit, self.absq_r_limit)
        self.qps_limit = math.min(self.qps_u_limit, self.qps_r_limit)

    def _query_rate_limit_request(self, rate_limit_only=False, rate=2):
        """Check query limit when we get distance of a user
        """

        vb.vb_print(self.verbose, "Examining limits on update queries")

        # Pass the arguments for update location:
        # attacker, victim, test_id, ERROR_VALUE of function
        args = (self.attacker, self.victim, self.test_id, None)
        return self.__limit_check(self.auditor_handled_distance,
                                  rate_limit_only,
                                  rate,
                                  *args)

    def _query_rate_limit_update(self, rate_limit_only=False, rate=2):
        """Check limits on update location queries
        """

        vb.vb_print(self.verbose, "Examining limits on update queries")

        # Pass the arguments for update location:
        # attacker, distance to move, angle, test_id, ERROR_VALUE for function
        args = (self.attacker, 0.001, randint(0, 360), self.test_id, False)
        return self.__limit_check(self.auditor_handled_place_at_dist,
                                  rate_limit_only,
                                  rate,
                                  *args)

    def __limit_check(self, function, rate_limit_only=False, rate=2, *args):
        """Check query limit when we update the location of the user

        Initially we check
        Args:
            function: function to be checked against query limiting
            rate_limit_only: Only perform rate limiting check
            rate: starting rate of queries per second
            args: the argumetns of the function with the error value being
                  the last argument
        """
        limit = None

        if not rate_limit_only:
            vb.vb_print(self.verbose,
                        "Testing if there is a global limit on query number",
                        "query-limit",
                        True)

            # Query once per second: our attacks require around
            # 100 queries so lets do 1000 queries for the worst case
            sleep_time = 1
            total_queries = 1000
            # place the user 2 meters away
            for i in range(total_queries):
                # perform micro-adjustments in location so as to
                # not trigger any speed constraints
                success, queries = function(*args[:-1])

                if success is args[-1]:
                    limit = i
                    break

                sleep(sleep_time)

            # if we did not have a limit return None
            if limit is None:
                vb.vb_print(self.verbose, " |--> False", "query-limit", True)
                return None

            vb.vb_print(self.verbose,
                        " |--> True: stopped at " + str(limit),
                        "query-limit",
                        True)

            # update absolute limits depending on the functions
            if function == self.auditor_handled_distance:
                self.absq_u_limit = limit
            else:
                self.absq_r_limit = limit

        vb.vb_print(self.verbose,
                    "Testing if there is rate limiting on queries",
                    "query-limit",
                    True)
        # If we were blocked check rate limiting
        # Currently rate limiting is eq. to @limit queries / sec
        # Initialize minimum and maximum queries / sec
        if limit is not None:
            [min_rate, max_rate] = [0, limit]
        else:
            [min_rate, max_rate] = [0, rate]

        while min_rate < max_rate:
            cur_rate = float(min_rate + max_rate) / 2

            vb.vb_print(self.verbose,
                        " |--current rate: " + str(cur_rate),
                        "query-limit",
                        True)

            # we apply each rate per second thus
            total_queries = cur_rate * 60
            # calculate sleep time per queries approximately
            sleep_time = float(1 / cur_rate)

            counter = 0
            while counter < total_queries:
                successful = function(*args[:-1])

                if successful is args[-1]:
                    # if we are blocked change attacker
                    self._update_attacker()
                    max_rate = cur_rate
                else:
                    # if we succeeded increase min_rate to cur_rate
                    min_rate = cur_rate

                # sleep till the next query
                sleep(sleep_time)
                counter += 1
        return cur_rate


    #
    #
    #  Attack Accuracy
    #
    #

    def test_dudp_attack(self, disk_radii, victim=None, users=None,
                         kml=None, grid=20):
        """Run the DUDP attack and set the accuracy in the Auditor class
        """
        # TODO add documentation & user checking add check for no of users
        # but provision for the case where the auditor supplied victim and
        # not user!
        vb.vb_print(self.verbose, "Testing accuracy of DUDP attack")

        if users is None:
            users = self._db.get_ordered_users()

        if victim is not None:
            self.victim = AuditorUser(self.service_id, victim)
            # make sure that victim is not in users
            #users.remove(victim)

            # and create instances of AuditorUser for attackers
            self.attackers = [AuditorUser(self.service_id, u) for u in users]
            self.attacker = self.attackers.pop()

        else:
            # and create instances of AuditorUser for attackers
            self.attackers = [AuditorUser(self.service_id, u) for u in users]
            self.attacker = self.attackers.pop()
            # pick the guy with the most queries to be the victim
            self.victim = self.attackers.pop(0)

        [ny_lat, ny_lon] = [40.753506, -73.988800]
        ny_lat += random.uniform(-0.01, 0.01)
        ny_lon += random.uniform(-0.01, 0.01)
        # place victim
        (success, queries) = self.auditor_handled_place_at_coords(self.victim,
                                                                  ny_lat,
                                                                  ny_lon,
                                                                  self.test_id)
        if type(disk_radii) != list:
            raise TypeError("Expecting a list of radii in km")

        if len(disk_radii) == 0:
            raise SystemExit("At least one radius in km is required!")

        if not success:
            raise SystemExit("Could not place user 1")

        self._db.insert_test("dudp")
        self.test_id = self._db.get_test_id("dudp")

        # FIXME check query rate limiting for both dudp and rudp
        self.query_limit = self.absq_limit


        disc_attack = auditor_discovery_attack.DiscoveryAttack(self,
                                                               self.attackers,
                                                               self.attacker,
                                                               self.victim,
                                                               self.proj,
                                                               self.oracle,
                                                               self.test_id,
                                                               self.__serv_name,
                                                               "dudp",
                                                               self.verbose,
                                                               self.query_limit,
                                                               self.speed_limit)

        self.dudp_accuracy = disc_attack.dudp_attack(disk_radii, kml, grid)


    def test_rudp_attack(self, rounding_classes, victim=None, users=None,
                         kml=None, grid=20):
        """Run the RUDP attack and set the accuracy in the Auditor class
        """

        vb.vb_print(self.verbose, "Testing accuracy of RUDP attack")
        # FIXME check rounding classes
        if users is None:
            users = self._db.get_ordered_users()

        if victim is not None:
            self.victim = AuditorUser(self.service_id, victim)
            # make sure that victim is not in users
            #users.remove(victim)

            # and create instances of AuditorUser for attackers
            self.attackers = [AuditorUser(self.service_id, u) for u in users]
            self.attacker = self.attackers.pop()

        else:
            # and create instances of AuditorUser for attackers
            self.attackers = [AuditorUser(self.service_id, u) for u in users]
            self.attacker = self.attackers.pop()
            # pick the guy with the most queries to be the victim
            self.victim = self.attackers.pop(0)

        [ny_lat, ny_lon] = [40.753506, -73.988800]
        ny_lat += random.uniform(-0.01, 0.01)
        ny_lon += random.uniform(-0.01, 0.01)
        # place victim
        (success, queries) = self.auditor_handled_place_at_coords(self.victim,
                                                                  ny_lat,
                                                                  ny_lon,
                                                                  self.test_id)
        if not success:
            raise SystemExit("Could not place user 1")

        self._db.insert_test("rudp")
        self.test_id = self._db.get_test_id("rudp")


        if self.query_limit is None:
            query_limit = self.absq_limit

        disc_attack = auditor_discovery_attack.DiscoveryAttack(self,
                                                               self.attackers,
                                                               self.attacker,
                                                               self.victim,
                                                               self.proj,
                                                               self.oracle,
                                                               self.test_id,
                                                               self.__serv_name,
                                                               "rudp",
                                                               self.verbose,
                                                               self.query_limit,
                                                               self.speed_limit)

        self.rudp_accuracy = disc_attack.rudp_attack(rounding_classes,
                                                     kml,
                                                     grid)

    #
    #
    #   Other checks
    #
    #

    def test_location_verification(self, users=None):
        """Checks whether the service verifies the location
        of a user when they perform a query
        """

        if users is None:
            users = self._db.get_ordered_users(2)

        if len(users) < 2:
            raise SystemExit("Not enough users! Three users required")

        user_list = [AuditorUser(self.service_id, u) for u in users]


        vb.vb_print(self.verbose, "Examining if service verifies coordinates")
        self._db.insert_test("coordinate_verification")
        self.test_id = self._db.get_test_id("coordinate_verification")

        # place user1 and user2 at a fixed distance (say 1km)
        user_1 = user_list.pop()
        user_2 = user_list.pop()

        [ny_lat1, ny_lon1] = [40.708306, -74.008839]
        [ny_lat2, ny_lon2] = [40.725412, -73.995323]
        [ny_lat3, ny_lon3] = [40.753506, -73.988800]


        # place user1
        (success, queries) = self.auditor_handled_place_at_coords(user_1,
                                                                  ny_lat1,
                                                                  ny_lon1,
                                                                  self.test_id)
        if not success:
            raise SystemExit("Could not place user 1")

        # place user2
        (success, queries) = self.auditor_handled_place_at_coords(user_2,
                                                                  ny_lat2,
                                                                  ny_lon2,
                                                                  self.test_id)
        if not success:
            raise SystemExit("Could not place user 2")

        # measure current distance of user1, user2
        (distance1, queries) = self.auditor_handled_distance(user_1,
                                                             user_2,
                                                             self.test_id,
                                                             [ny_lat1,
                                                              ny_lon1])

        (distance2, queries) = self.auditor_handled_distance(user_1,
                                                             user_2,
                                                             self.test_id,
                                                             [ny_lat3,
                                                              ny_lon3])

        location_verified = (distance1 == distance2 and (distance1 is not None))
        self.service_verifies_location = location_verified
        vb.vb_print(self.verbose,
                    " |-->" + str(location_verified),
                    "verification check",
                    True)
        return location_verified

    #
    #
    #
    #
    #
    #       WRAPPERS ON GET DISTANCE AND UPDATE LOCATION FUNCTIONS
    #
    #
    #
    #
    #

    def _get_max_distance(self, auditor_user):
        """Returns the maximum distance that a user is allowed to travel
        given the speed constraints of the service and the last update of
        their location
        """
        if self.speed_limit is not None:
            # if we have a speed limit check if the last update of the location
            # allows us to move at current distance
            time_since_last_update = time() - auditor_user.last_updated
            # since distance is in km/h divide time (in sec) with 3600 to get h
            max_distance = self.speed_limit * (time_since_last_update / 3600)
        else:
            max_distance = float('inf')

        return max_distance

    def auditor_handled_place_at_coords(self, user, lat, lon, test_id,
                                       query_id=None):
        """Place a user of the auditing testsuite  at [lat, lon] if that is
        allowed by the speed constraints

        Notice that @auditor_user is not the user passed by the inherited class
        but an instance of the AuditorUser class used by the auditing framework


        Args:
            user: the user to be placed in a new location (AuditorUser instance)
            dist: distance further from the user's location in km
            lat, lon: latitude & longitude
            test_id: the test_id of the test being run

        Return Value:
            Returns a tuple (@result, @queries) where @result is True or False
            depending on whether the location was updated successfully or not.
            @queries is the total queries towards the service required to
            perform the update.

        Raises:
            AuditorException(with optional log data) if inh. class raises it.
            AuditorExceptionUnknown in case an unknown error error occurs
        """

        if not (isinstance(lat, float) and isinstance(lon, float)):
            raise TypeError("lat and lon parameters should be of type float!")

        # get the max distance the user is allowed to travel
        max_distance = self._get_max_distance(user)

        # get the distance of the current location with the new location
        if user.loc[0] is not None and user.loc[1] is not None:
            dist = earth.distance_on_unit_sphere(user.loc[0],
                                                 user.loc[1],
                                                 lat,
                                                 lon)
        else:
            # it's our first update
            dist = 0

        # If we have a speed limit and the distance is bigger than what
        # we are allowed to cross, sleep until we are allowed
        if dist > max_distance:
            sleep_time = (dist - max_distance) / self.speed_limit
            sleep(sleep_time + 1)

        try:
            # given that the clocks won't change and we don't
            # run stuff in parallel, have time as primary key
            if query_id is None:
                query_id = int(time())

            # if we have full logging create query record
            # create it here in case any exception is raised
            if self.logging == const.LOG.ALL:
                query_info = "auditor_set_location: "
                query_info += "[" + str(lat) + "," + str(lon) + "]"
                self._db.insert_query(query_id,
                                     test_id,
                                     user.user_id,
                                     user.service_id,
                                     query_info)

            # do not catch any exceptions here, let the caller handle it
            set_loc_rspn = self.auditor_set_location(user.user,
                                                     lat,
                                                     lon)
            sleep(5)
            if len(set_loc_rspn) != 2:
                raise SystemExit("auditor_set_location must return a tuple!")

            (result, queries) = set_loc_rspn
            if not isinstance(result, bool) and not isinstance(queries, int):
                error = "Wrong return type: Expecting (bool, int) or None"
                raise TypeError(error)

            # if no exception was raised but we failed log it
            if result is False and self.logging == const.LOG.ALL:
                self._db.log_query_fail(query_id)

        except AuditorException:
            if self.logging == const.LOG.ALL:
                self._db.log_query_fail(query_id)
                # handle any data that has been passed by the user
                self._db.exception_recovery(query_id)
            # user has been removed from the pool already
            # so no need to update queries, just return
            return (False, 1)
        except Exception as exception:
            # remove user from active users
            self.users.remove(user.user)
            self._db.log_query_fail(query_id)
            # else raise exception and record failure
            raise AuditorExceptionUnknown(str(exception), user.user_id)

        user.update_queries(queries)
        user.loc = [lat, lon]

        return (result, queries)

    def auditor_handled_place_at_dist(self, user, dist, bear, test_id,
                                      query_id=None):
        """Place a user of the auditing testsuite in a distance @dist km from
        their current location, at a bearing of @bearing, if it is allowed by
        the speed constraints.

        Notice that @auditor_user is not the user passed by the inherited class
        but an instance of the AuditorUser class used by the auditing framework

        Args:
            user: the user to be placed in a new location (AuditorUser instance)
            dist: distance further from the user's location in km
            bear: bearing in degrees
            test: the id of the test being run
            query: the query id for the current query

        Return Value:
            Returns a tuple (@result, @queries) where @result is True or False
            depending on whether the location was updated successfully or not.
            @queries is the total queries towards the service required to
            perform the update.

        Raises:
            AuditorException(with optional log data) in case an error occurs.
        """

        # get the max distance the user is allowed to travel
        max_distance = self._get_max_distance(user)

        # If we have a speed limit and the distance is bigger than what
        # we are allowed to cross, sleep until we are allowed
        if dist > max_distance:
            sleep_time = (dist - max_distance) / self.speed_limit
            sleep(sleep_time + 1)

        # find new position at distance and angle
        new_pos = earth.point_on_earth(user.loc[0],
                                       user.loc[1],
                                       dist,
                                       bear)

        try:
            # given that the clocks won't change and we don't
            # run stuff in parallel, have time as primary key
            if query_id is None:
                query_id = int(time())

            # if we have full logging create query record
            # create it here in case any exception is raised
            if self.logging == const.LOG.ALL:
                query_info = "auditor_set_location ["
                query_info += str(new_pos[0]) + "," + str(new_pos[1]) + "]"
                self._db.insert_query(query_id,
                                     test_id,
                                     user.user_id,
                                     user.service_id,
                                     query_info)

            set_loc_rspn = self.auditor_set_location(user.user,
                                                     new_pos[0],
                                                     new_pos[1])
            if len(set_loc_rspn) != 2:
                raise SystemExit("auditor_set_location must return a tuple!")

            sleep(5)
            (result, queries) = set_loc_rspn

            if not isinstance(result, bool) and not isinstance(queries, int):
                error = "Wrong return type: Expecting (bool, int) or None"
                raise TypeError(error)

            # if no exception was raised but we failed log it
            if result is False and self.logging == const.LOG.ALL:
                self._db.log_query_fail(query_id)

        except AuditorException:
            if self.logging == const.LOG.ALL:
                self._db.log_query_fail(query_id)
                # handle any data that has been passed by the user
                self._db.exception_recovery(query_id)
            return (False, 1)
        except Exception as exception:
            # remove user from active users
            self.users.remove(user.user)
            self._db.log_query_fail(query_id)
            # else raise exception and record failure
            raise AuditorExceptionUnknown(str(exception), user.user_id)

        # update user info
        user.update_queries(queries)
        user.loc = new_pos

        return (result, queries)


    def auditor_handled_distance(self, user_a, user_b, test_id, u_coords=None,
                                 query_id=None):
        """Get distance between user_a and user_b and handle
        any possible exceptions that may be raised

        Args:
            user_a: AuditorUser instance performing the query
            user_b: AuditorUser instance to measure the distance from
            test_id: the id of the current test performed

        Return Value:
            Returns a tuple (@result, @queries) where @result is the distance
            between users in km or None if the distance was not found.
            @queries is the total queries towards the service required to
            perform the update.
        """
        try:
            # given that the clocks won't change and we don't
            # run stuff in parallel, have time as primary key
            if query_id is None:
                query_id = int(time())

            # if we have full logging create query record
            # create it here in case any exception is raised
            if self.logging == const.LOG.ALL:
                query_info = "auditor_get_distance "
                query_info += str(user_a.user) + "," + str(user_b.user) + "]"
                self._db.insert_query(query_id,
                                     test_id,
                                     user_a.user_id,
                                     user_a.service_id,
                                     query_info)

            # get distance of users user_a, user_b
            get_dist_rspn = self.auditor_get_distance(user_a.user,
                                                      user_b.user,
                                                      u_coords)

            if len(get_dist_rspn) != 2:
                raise SystemExit("auditor_set_location must return a tuple!")

            (dist, queries) = get_dist_rspn

            if not isinstance(dist, float) and not isinstance(queries, int):
                error = "Wrong return type: Expecting (float/int, int) or None"
                raise TypeError(error)

            # if no exception was raised but we failed log it
            if dist is None and self.logging == const.LOG.ALL:
                self._db.log_query_fail(query_id)

        except AuditorException:
            if self.logging == const.LOG.ALL:
                # handle any data that has been passed by the user
                self._db.log_query_fail(query_id)
                self._db.exception_recovery(query_id)
            return (None, 1)
        except Exception as exception:
            # remove user from active users
            self.users.remove(user_a.user)
            # else raise exception and record failure
            self._db.log_query_fail(query_id)
            raise AuditorExceptionUnknown(str(exception), user_a.user_id)

        user_a.update_queries(queries)

        return (dist, queries)


    #####################################################################
    #                                                                   #
    #                                                                   #
    #                                                                   #
    #   THE FOLLOWING FUNCTIONS SHOULD BE DEFINED IN INHERITED CLASSES  #
    #                                                                   #
    #                      ** DO NOT MODIFY **                          #
    #                                                                   #
    #                                                                   #
    #                                                                   #
    #####################################################################

    def auditor_get_distance(self, _user_a, _user_b, _user_a_loc):
        """Get distance between two users as returned by the service

        - To be defined by inherited classes. This function should be inherited
        by the specific service auditing class and should return the distance
        as returned by the service between user_a and user_b in km.

        @_user_a_loc contains the coordinates of _user_a in [lat, lon].
        These coordinates are usually used as parameters passed to the service
        when the _user_a asks for her distance in respect to _user_b. In
        case the service being audited does not require the coordinates of
        _user_a to fetch the distance information (for instance, because they
        keep a record of the user's coordinates from their last update location
        query) then this parameter should be ignored by the method in the
        inherited class implementation.

        Args:
            _user_a: user identifier as defined by the inherited class. This
                    user issues the query to ask for the distance from _user_b
            _user_b: user identifier as defined by the inherited class
            _user_a_loc: the location of user_a in format [lat, lon]

        Return Value:
            Returns a tuple (@result, @queries) where @result is the distance
            between users in km or None if the distance was not found.
            @queries is the total queries towards the service required to
            perform the update.

        Raises:
            AuditorException(with optional log data) in case an error occurs.
        """

        raise AttributeError("auditor_get_distance undefined in child class")

    def auditor_set_location(self, _user, _lat, _lon):
        """Set location of user

        - To be defined by inherited classes.

        Args:
            user: user identifier as defined by the inherited class
            lat, lon: latitude and longitude

        Return Value:
            Returns a tuple (@result, @queries) where @result is True or False
            depending on whether the location was updated successfully or not.
            @queries is the total queries towards the service required to
            perform the update.

        Raises:
            AuditorException(with optional log data) in case an error occurs.
        """

        raise AttributeError("auditor_set_location undefined in child class")
