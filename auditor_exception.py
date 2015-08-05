"""Service Auditor Exception
"""
from __future__ import absolute_import
from auditor_db import AuditorDB

class AuditorException(Exception):
    """Auditor Framework Exception

    Throws an Exception and logs any data that may
    be passed by the application into the database
    This is raised by the inherited application

    Args:
        @log_data:  any data that the caller wants to save (optional)
        @user_id :  the user who executed the query that
                    caused the exception (optional)
    """

    def __init__(self, log_data=None, username=None):
        self._db = AuditorDB()
        self._db.connect()
        # log any data passed
        if log_data is not None:
            self._log_exception(log_data, username)

        self._db.close_connection()
        # then call the base class
        Exception.__init__(self)

    def _log_exception(self, blob, username):
        """Log the exception data that was passed by the user
        into the database inside the exception handler. The
        caller will need to perform the cleanup and link the
        log with the respective query.
        """
        self._db.log_exception(blob, username)

class AuditorExceptionUnknown(Exception):
    """Unknown Exception was thrown. Handle it here.

    This is raised by the Auditing Framework in case the application
    raised an unknown exception for any reason. It performs logging
    of the query and account info
    """

    def __init__(self, msg, query_id=None):
        # log everything as failed into the database
        self._db = AuditorDB()
        self._db.connect()
        self._db.log_unknown_exception(msg, query_id)
        self._db.close_connection()

        # print error
        print "\n\tException thrown! Error:" + str(msg)

        # then call the base class
        Exception.__init__(self)
