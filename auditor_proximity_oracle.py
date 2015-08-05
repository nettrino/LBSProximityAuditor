"""Proximity Oracle
"""
from __future__ import absolute_import
import auditor_constants as const
from libs import verbose as vb
from time import time

class ProximityOracle(object):
    """Generic proximity oracle class

    Allows a user to define their own oracle depending on the service
    """

    def set_radius(self, radius):
        """Set the radius for a DUDP-behavior-like oracle
        """
        raise AttributeError('set_radius undefined in child class')

    def in_proximity(self, _auditor_user_a, _auditor_user_b):
        """
        - To be defined by inherited classes.
        This function should be inherited by the specific service auditing class
        and should True or False depeding on the oracle outcome
        """
        raise AttributeError('in_proximity undefined in child class')

class DiskProximityOracle(ProximityOracle):
    """Defines a disk proximity oracle
    """

    def __init__(self, auditor, radius, verbose=True):
        """Initiate radius in km for disk oracle
        """
        self.auditor = auditor
        self.radius = radius
        self.verbose = verbose

    def set_radius(self, radius):
        """Set the radius for a DUDP-behavior-like oracle
        """
        self.radius = radius

    def in_proximity(self, auditor_user_a, auditor_user_b, test_id):
        """auditor_user_a examines if auditor_user_b is in proximity radius
        (in km) using a disk proximity oracle

        Args:
            auditor_user_a: auditor user instance for attacker
            auditor_user_b: auditor user instance for target
            radius: radius of disk in km

        Returns:
            (answer, queries) where @answer is True if user_b is in proximity
            to user_a with respect to the oracle else False.
        """

        vb.vb_print(self.verbose, "Examining oracle:", "DUDP", True)
        query_id = int(time())
        (dist, q) = self.auditor.auditor_handled_distance(auditor_user_a,
                                                          auditor_user_b,
                                                          test_id,
                                                          auditor_user_a.loc,
                                                          query_id)
        if dist is None:
            vb.vb_print(self.verbose, " |-- None", "DUDP", True)
            return (None, 1)
        if dist < self.radius:
            vb.vb_print(self.verbose, " |-- True", "DUDP", True)
            return (True, q)
        else:
            vb.vb_print(self.verbose, " |-- False", "DUDP", True)
            return (False, q)


class RoundingProximityOracle(ProximityOracle):
    """Defines a rounding proximity oracle
    """

    def __init__(self, auditor, rounding_classes, verbose=True):
        """Initiate the class of intervals for this proximity oracle

        Args:
            @rounding_classes is a list of rounding classes in the form
            [range (in km), rounding (in km), rounding_type], ex.
            the class [[0.1, 0.2], 0.005, const.ROUNDING.UP] denotes that
            from 100m to 200m, the services rounds up the returned distance
            by 5m
        """
        self.auditor = auditor
        self.round_cl = rounding_classes
        self.verbose = verbose

    def in_proximity(self, auditor_user_a, auditor_user_b, test_id):
        """auditor_user_a gets the distance from auditor_user_b
        using the disk proximity oracle

        Args:
            auditor_user_a: auditor user instance for attacker
            auditor_user_b: auditor user instance for target
        """

        vb.vb_print(self.verbose, "Examining oracle:", "RUDP", True)
        query_id = int(time())
        return self.auditor.auditor_handled_distance(auditor_user_a,
                                                     auditor_user_b,
                                                     test_id,
                                                     auditor_user_a.loc,
                                                     query_id)
