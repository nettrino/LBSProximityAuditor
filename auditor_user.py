"""User class
"""
from __future__ import absolute_import
from time import time

from auditor_db import AuditorDB

class AuditorUser(object):
    """Describes a user in the auditing framework.

    Each AuditorUser instance contains the user as passed by the inherited
    class, as well as metadata about the user such as queries, location etc
    """

    def __init__(self, service_id, user, location=None):
        """Initializes a user class as used by the auditor
        inh_user is the user instance as passed by the inherited Class

        Args:
            service_id: the id of the service as defined in db
            user: the username of the user for that service
            location: location in [lat, lon] for the user
        """

        # initialize database
        self._db = AuditorDB()
        self._db.connect()

        # insert in db if not exists
        if location is not None:
            self._db.insert_user(user, service_id, location[0], location[1])
        else:
            self._db.insert_user(user, service_id, None, None)

        # load user info from inherited class
        self.user = user
        self.service_id = service_id
        # mark this Auditor user as inactive until used in an experiment
        self.is_active = False
        # will be set in _restore_from_db
        self.user_id = None
        self.loc = None

        # update user info from the latest record in db
        if not self._restore_from_db():
            self.last_updated = 0
            self.queries = 0

        # if location was provided at init
        # overwrite whatever was provided by the database
        if location is not None:
            self.loc = location

    def __del__(self):
        """Update user record on db before cleanup
        """
        if self.loc[0] is not None and self.loc[1] is not None:
            self._db.update_user(self.user_id,
                                 False,
                                 self.queries,
                                 self.loc[0],
                                 self.loc[1])
        else:
            self._db.update_user(self.user_id,
                                 False,
                                 self.queries,
                                 None,
                                 None)
        self._db.close_connection()

    def _restore_from_db(self):
        """Fetch user information from database
        """
        _db_info = self._db.fetch_user_info(self.user, self.service_id)

        if _db_info is None:
            return False
        else:
            self.user_id, self.queries, self.loc, self.last_updated = _db_info
            return True

    def update_location(self, lat, lon):
        """Update location in memory
        """
        self.loc = [lat, lon]
        self.last_updated = time()

    def update_queries(self, queries=1):
        """Update queries in memory
        """
        self.queries += queries
