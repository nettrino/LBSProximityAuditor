ServiceAuditor
==============

As Location Based Services are becoming more and more widespread, new
applications with location proximity functionality are expected to emerge.
Evaluating the privacy guarantees of a large, diverse and constantly evolving
set of applications is not an easy task as a newly-introduced feature might
break the overall privacy of the application. Unfortunately, although many tools
exist to detect bugs in traditional software, we still lack concrete mechanisms
evaluating the privacy properties of applications.

ServiceAuditor is an auditing framework for Location Based Services designed
designed to facilitate researchers, developers, and privacy-sensitive
individuals, in verifying the privacy offered by proximity applications.

This is a series of tests for the automatic evaluation of applications,
regarding their query speed limiting, the verification of API parameters, and
their effectiveness in protecting users against the attacks presented in this
paper.  It also provides a set of libraries that can be used to facilitate
common operations on geographical data, both on natural and projected
coordinates.  Since we cannot predict what the specific requirements of each
application might be, we expect auditors to implement the parts that are
application-specific. In particular, our framework requires that the auditor has
implemented the following two API calls:

* auditor_get_distance(user_a, user_b), which returns the distance between two
    users of the service.
* auditor_set_location(user, lat, lon), which sets the location of a user at
    a specific set of coordinates.

Once the auditor implements the above calls, both the limit tests and the
attacks work out of the box. In cases where the service is not a straightforward
does not use standard proximity oracles (e.x. ring-based or disk-based)
auditors can specify their own proximity oracle; subsequently, that can be
passed as a parameter to ServiceAuditor for automatically evaluating the service.
For thorough examples on how to implement your own auditing class for your
service, please see the example_auditor.py file.

Installation
============

The following installation instructions are based on pip package manager but
if you would like to follow a different installation procedure, you can find
all required packages at requirements.txt

Install the dependencies via

    pip install -r requirements.txt


Running
=======

When running tests, a database named 'testing.db' is created and holds all
information about the experiments that have been run, the users in each
experiment, their queries, the limits of the service etc. In addition, a kml
file is produced for each step of the auditing under files/kml. Finally, a
json file with all the steps of the RUDP/DUDP attack is also produced for
each attack that has been succesfully carried out.

An example of how to invoke the framework is given in example_auditor.py. In
this example, we have implemented a class Tester which inherits from the Auditor
class and implements the auditor_get_distance and auditor_set_location
functions.

The swarm class is not included yet as the respective service is not yet
patched. Users can define their own exception handlers as well as their own
proximity oracles to be used with the rest of this API. See the API functions
for more info on each class.

Once the auditor class is properly set up for your service, you simply invoke
it via

    python your_auditor_class.py

(example_auditor.py will fail as swarm.py is missing)
