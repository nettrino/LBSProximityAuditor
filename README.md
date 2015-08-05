LBSProximityAuditor
===================

As location-based services are becoming more and more popular, new
applications with location proximity functionality are expected to emerge.
Furthermore, misconceptions about the actual privacy offered by various
proximity models, has led services and major media into cultivating a
false sense of security which has exposed users of these services to
life-threatening risks. Evaluating the privacy guarantees of a large,
diverse, and constantly evolving set of applications and services is
not an easy task. As such we are releasing LBSProximityAuditor.

LBSProximityAuditor is an auditing framework for Location Based Services
designed to facilitate researchers, developers, and privacy-sensitive
individuals, in verifying the privacy offered by proximity applications.

This is a series of tests for the automatic evaluation of applications,
regarding their query speed limiting, the verification of API parameters, and
their effectiveness in protecting users against our precise user discovery attacks.
It also provides a set of libraries that can be used to facilitate
common operations on geographical data, both on natural and projected
coordinates.  Since we cannot predict what the specific requirements of each
application might be, we expect auditors to implement the parts that are
application-specific. In particular, our framework requires the auditor to
implemented the following two API calls:

* auditor_get_distance(user_a, user_b), which returns the distance between two
    users of the service.
* auditor_set_location(user, lat, lon), which sets the location of a user at
    a specific set of coordinates.

Once the auditor implements the above calls, both the limit tests and the
attacks work "off-the-shelf". In cases where the service does not use
standard proximity oracles (i.e., exact distance, ring-based or disk-based)
auditors can specify their own proximity oracle; subsequently, that can be
passed as a parameter to LBSProximityAuditor for automatically evaluating the service.
For thorough examples on how to implement your own auditing class for your
service, please see the example_auditor.py file.


Installation
============

The following installation instructions are based onthe pip package manager but
if you would like to follow a different installation procedure, you can find
all the required packages in requirements.txt

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

Users can define their own exception handlers as well as their own
proximity oracles to be used with the rest of this API. See the API functions
for more info on each class.

Once the auditor class is properly set up for your service, you simply invoke
it via

                    python your_auditor_class.py

An example of how to invoke the framework is given in example_auditor.py. In
this example, we have implemented a class Tester which inherits from the Auditor
class and implements auditor_get_distance and auditor_set_location functions.

Disclaimer
==========
    !!! The example_auditor.py file as provided is not a working example !!!

This framework is intended for security research purposes only. Our goal is to
assist security researchers and service developers in improving the privacy
offered to users. Under no circumstances do we condone the use of our framework
as an offensive tool.

Reverse engineering the protocols and API calls of various services may violate
the Terms and Conditions of those services.
