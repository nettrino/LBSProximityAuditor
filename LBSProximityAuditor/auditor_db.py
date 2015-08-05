"""Database interface for ServiceAuditor
"""
from __future__ import absolute_import
import sqlite3
import os

from libs import verbose
import auditor_constants as const

class AuditorDB(object):
    """Database related functionality
    """

    def __init__(self, db_name="testing.db", logging=const.LOG.STANDARD):
        if os.path.isfile(db_name):
            self._db = db_name
        else:
            self._db = ''.join(os.getcwd() + "/" + os.path.basename(db_name))

        self.setup()

        self.conn = None
        self.loglevel = logging

    def setup(self):
        """Setup database if not created
        """
        self.connect()
        self._create_errors()
        self._create_services()
        self._create_tests()
        self._create_users()
        self._create_queries()
        self.close_connection()

    def connect(self):
        """Connect to db
        """
        self.conn = sqlite3.connect(self._db)

    def close_connection(self):
        """Close connection to the database
        """
        self.conn.close()

    #
    #
    #
    # CREATE Statements
    #
    #
    #

    def _create_tests(self):
        """Creates SERVICE_TESTS table:
        ID: the primary key in the table
        NAME: the name of the test
        """
        cur = self.conn.cursor()
        stmt = ("CREATE TABLE IF NOT EXISTS SERVICE_TESTS("
                "ID INTEGER PRIMARY KEY AUTOINCREMENT, "
                "NAME TEXT NOT NULL, "
                "ISSUED_AT DATETIME DEFAULT CURRENT_TIMESTAMP"
                ")"
               )

        cur.execute(stmt)
        self.conn.commit()

    def _create_services(self):
        """Creates SERVICES table:
        ID: the primary key in the table
        NAME: the name of the service
        SPEED_LIMIT: the current speed limit for the service
        QUERY_LIMIT INTEGER: the total query limit
        ABS_LIMIT INTEGER: limit on absolute queries
        QPS_LIMIT INTEGER: rate limiting of queries in queries per second
        DUDP_ACCURACY REAL: accuracy of dudp attack
        RUDP_ACCURACY REAL: accuracy of rudp attack
        VERIFIES_LOC TINYINT: 0 or 1 if the service verifies the location
                              on each distance query
        """
        cur = self.conn.cursor()
        stmt = ("CREATE TABLE IF NOT EXISTS SERVICES("
                "ID INTEGER PRIMARY KEY AUTOINCREMENT, "
                "NAME TEXT UNIQUE NOT NULL, "
                "SPEED_LIMIT REAL, "
                "QUERY_LIMIT INTEGER, "
                "ABS_LIMIT INTEGER, "
                "QPS_LIMIT INTEGER, "
                "DUDP_ACCURACY REAL, "
                "RUDP_ACCURACY REAL, "
                "VERIFIES_LOC TINYINT"
                ")"
               )

        cur.execute(stmt)
        self.conn.commit()

    def _create_errors(self):
        """Creates ERRORS table:
        ID: the primary key in the table
        LOG: any info about the error
        USERNAME: name of the user that triggered the error
        LINKED: if the error data has been linked with a query
        """
        cur = self.conn.cursor()
        stmt = ("CREATE TABLE IF NOT EXISTS ERRORS("
                "ID INTEGER PRIMARY KEY AUTOINCREMENT, "
                "LOG BLOB, "
                "USER TEXT NOT NULL, "
                "LINKED TINYINT DEFAULT 0, "
                "ISSUED_AT DATETIME DEFAULT CURRENT_TIMESTAMP"
                ")"
               )

        cur.execute(stmt)
        self.conn.commit()

    def _create_users(self):
        """Creates USERS table:
        ID: the primary key in the table
        IS_ACTIVE: whether the user is currently being used in some
        experiment
        QUERIES: queries the user has issued since they were last active
        SERVICE: the service the user belongs to
        USERNAME: the unique id of the user in that service
        LAT: user's latitude
        LON: user's longitude
        UPDATED_AT: last time the user location was updated
        """
        cur = self.conn.cursor()
        stmt = ("CREATE TABLE IF NOT EXISTS USERS("
                "ID INTEGER PRIMARY KEY AUTOINCREMENT, "
                "IS_ACTIVE TINYINT, "
                "QUERIES INTEGER, "
                "SERVICE INTEGER, "
                "USERNAME BLOB NOT NULL, "
                "LAT DOUBLE, "
                "LON DOUBLE, "
                "UPDATED_AT DATETIME DEFAULT CURRENT_TIMESTAMP,"
                "FOREIGN KEY(SERVICE) REFERENCES SERVICES(ID)"
                "UNIQUE (USERNAME, SERVICE)"
                ")"
               )

        cur.execute(stmt)
        self.conn.commit()

    def _create_queries(self):
        """Creates QUERIES table:
        ISSUED_AT: the primary key in the table
        TEST: the test that issued the query
        USER: the user that issued the query
        SERVICE: the service towards the query was issued
        INFO: query specific info (e.x. function, parameters etc)
        LOG: Any logging data that may be passed by the inherited class
        ISSUED_AT: Timestamp of the request
        FAILED: 0 if successful, 1 if failed
        """
        # TODO Currently we do not add TEST as a foreign key in case a user
        # implements their own oracle in a manner that does not pass a test_id
        cur = self.conn.cursor()
        stmt = ("CREATE TABLE IF NOT EXISTS QUERIES("
                "ID INTEGER PRIMARY KEY, "
                "TEST INTEGER, "
                "USER INTEGER NOT NULL, "
                "SERVICE INTEGER NOT NULL, "
                "INFO TEXT, "
                "LOG BLOB, "
                "FAILED TINYINT DEFAULT 0,"
                "FOREIGN KEY(USER) REFERENCES USERS(ID),"
                "FOREIGN KEY(SERVICE) REFERENCES SERVICES(ID)"
                ")"
               )

        cur.execute(stmt)
        self.conn.commit()

    #
    #
    #
    # INSERT Statements
    #
    #
    #

    def insert_test(self, name):
        """Insert a new service_test in the database.
        @service_name is the name of the service
        """

        # retrieve service id
        cur = self.conn.cursor()
        cur.execute("INSERT INTO SERVICE_TESTS(NAME) VALUES (?)", [name])
        self.conn.commit()

    def insert_service(self, service_name):
        """Insert a new service in the database.
        @service_name is the name of the service
        """

        # retrieve service id
        try:
            cur = self.conn.cursor()
            cur.execute("INSERT OR IGNORE INTO SERVICES(NAME) VALUES (?)",
                      [service_name])

            self.conn.commit()
        except sqlite3.IntegrityError:
            print "[db] Record already exists.. ignoring"

    def insert_user(self, username, service_id, lat=None, lon=None):
        """Insert user in the database.
        @service_id is the id of the service for that user
        @user_id the id of the user in that service (email or other identifier)
        """
        # retrieve service id
        cur = self.conn.cursor()
        try:
            stmt = ("INSERT OR IGNORE INTO USERS (IS_ACTIVE, QUERIES, SERVICE, "
                    "USERNAME, LAT, LON) VALUES (0, 0, ?, ?, ?, ?)")
            cur.execute(stmt, (service_id, username, lat, lon))
            self.conn.commit()
        except sqlite3.IntegrityError:
            print "[db] Record already exists.. ignoring"

    def insert_query(self, query_id, test_id, user_id, service_id, info):
        """Insert query in the database.
        @test_id: the id of the test that issued the query
        @user_id: the id of the user that issued the query
        @service_id: the id of the service to which the query is issued
        @req: the request issued at this query
        @resp: the response from the service for this query
        @timestamp: the time at which the query was issued
        """

        try:
            # retrieve service id
            cur = self.conn.cursor()
            stmt = ("INSERT INTO QUERIES (ID, TEST, USER, SERVICE, "
                    "INFO) VALUES (?, ?, ?, ?, ?)")
            cur.execute(stmt, (query_id, test_id, user_id, service_id, info))
            self.conn.commit()
        except sqlite3.IntegrityError as error:
            print "[db] Insertion failed"
            print error

    #
    #
    #
    # UPDATE Statements
    #
    #
    #

    def update_service(self, service_id, speed_limit, abs_limit, qps_limit,
                       dudp_accuracy, rudp_accuracy, verifies_loc):
        """Update limits of service
        """
        cur = self.conn.cursor()

        # store total queries
        stmt = ("UPDATE SERVICES SET SPEED_LIMIT=?, ABS_LIMIT=?, QPS_LIMIT=?, "
                "DUDP_ACCURACY=?, RUDP_ACCURACY=?, VERIFIES_LOC=? WHERE ID=?")

        cur.execute(stmt, (speed_limit,
                           abs_limit,
                           qps_limit,
                           dudp_accuracy,
                           rudp_accuracy,
                           verifies_loc,
                           service_id))
        self.conn.commit()

    def update_user(self, user_id, is_active, queries, lat=None, lon=None,
                    add_queries=False):
        """Update a user record in the database setting them active/inactive
        and setting their number of queries respectively.

        If add_queries is True, @queries are added to the user's existing
        queries
        """
        cur = self.conn.cursor()

        # store total queries
        if add_queries:
            cur.execute("SELECT QUERIES FROM USERS WHERE ID=?", user_id)
            self.conn.commit()
            _row = cur.fetchone()
            if _row is None:
                raise SystemExit("USER not found")
            _db_queries = _row[2]
            t_queries = _db_queries + queries
        else:
            t_queries = queries

        stmt = ("UPDATE USERS SET IS_ACTIVE=?, QUERIES=?, LAT=?, "
                "LON=? WHERE ID=?")
        cur.execute(stmt, (is_active, t_queries, lat, lon, user_id))
        self.conn.commit()

    def log_query_fail(self, query_id):
        """Update a query in the database.
        @service_id: the id of the service to which the query is issued
        """
        cur = self.conn.cursor()
        stmt = ("UPDATE QUERIES SET FAILED=1 WHERE ID=?")
        cur.execute(stmt, [query_id])
        self.conn.commit()

    #
    #
    #
    # SELECT Statements
    #
    #
    #

    def get_ordered_users(self, user_no=None):
        """Order users by queries and order @user_no users with the least
        queries in descending order. If user_no is None, return All users
        """
        cur = self.conn.cursor()
        cur.execute("SELECT USERNAME FROM USERS ORDER BY QUERIES DESC")
        self.conn.commit()
        _row = cur.fetchall()
        if _row is not None:
            if user_no is None:
                return [x[0] for x in _row]
            else:
                return [x[0] for x in _row][:user_no]
        else:
            raise SystemExit("No users found!")

    def get_service_id(self, name):
        """Get the id of a service with name @name
        """
        cur = self.conn.cursor()
        cur.execute("SELECT ID FROM SERVICES WHERE NAME=?", [name])
        self.conn.commit()
        _row = cur.fetchone()
        if _row == None:
            answ_is_yes = verbose.yes_no("No such service. Create it now?")
            if answ_is_yes:
                self.insert_service(name)
            else:
                raise SystemExit("Could not insert user")
        return _row[0]

    def get_test_id(self, name):
        """Get the id of a test with name @name
        """
        cur = self.conn.cursor()
        stmt = ("SELECT ID FROM SERVICE_TESTS WHERE NAME=?"
                "ORDER BY ISSUED_AT DESC")
        cur.execute(stmt, [name])
        self.conn.commit()
        _row = cur.fetchone()
        if _row == None:
            raise SystemExit("No such test")
        return _row[0]

    def fetch_user_info(self, username, service_id):
        """Gets user queries, location and update_timestamp for that location
        """
        cur = self.conn.cursor()
        stmt = ("SELECT ID, QUERIES, LAT, LON, UPDATED_AT FROM USERS WHERE "
                "SERVICE=? AND USERNAME=?")

        cur.execute(stmt, (service_id, username))
        self.conn.commit()
        _row = cur.fetchone()

        if _row != None:
            # return id, queries, [lat, lon], timestamp
            return _row[0], _row[1], [_row[2], _row[3]], _row[4]
        else:
            return None

    #
    #
    #
    # Exception statements
    #
    #
    #

    def log_exception(self, log_data, username=None):
        """Update the database records in case of failure

            Args:
                log_data: any log info passed by the caller
                username: the service username of whover issued the query
        """
        cur = self.conn.cursor()
        cur.execute("INSERT INTO ERRORS(LOG, USER) VALUES (?, ?)",
                    log_data,
                    username)
        self.conn.commit()

    def log_unknown_exception(self, error_msg, user_id):
        """Catch an unkown exception raised by the caller app
        """
        cur = self.conn.cursor()
        stmt = "INSERT INTO ERRORS(LOG, USER) VALUES (?, ?)"
        cur.execute(stmt, (error_msg, user_id))
        self.conn.commit()

    def exception_recovery(self, query_id):
        """Get last exception that was inserted and update the respective query
        to insert any log data in the query log
        """
        # FIXME check that this works as expected
        cur = self.conn.cursor()

        cur.execute("SELECT * FROM ERRORS")
        self.conn.commit()
        _rows = cur.fetchall()
        # get last result and check if 'LINKED' field is 1
        # that is, check if the error is already linked with a query
        if _rows is not None and _rows[-1][3] == 0:
            # if not get the log data
            log_data = _rows[-1][1]
            stmt = ("UPDATE QUERIES SET LOG=?  WHERE ID=?")
            cur.execute(stmt, (log_data, query_id))
            self.conn.commit()

            #update the link field
            error_id = _rows[-1][0]
            cur.execute("UPDATE ERRORS SET LINKED=1 WHERE ID=?", (error_id))
            self.conn.commit()
