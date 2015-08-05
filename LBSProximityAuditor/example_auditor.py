#/usr/bin/python
import time
import random
import string
import datetime
import json
import os
import sys

import swarm
from libs import earth

import swarm

from auditor import Auditor
import auditor_constants as const

import random

DEVICE_ID1 = '54adab89499e9beda93c905d'
DEVICE_ID2 = '56ddab89499e9eeda93c905d'

def _repr_coords(coords):
	return repr(coords[0]) + "," + repr(coords[1])

users= [
    ['ankskywalker66@gmail.com', 'fakefake'],
    ['oliv.summer13@gmail.com', 'fakefake']
]

brng = 180
travel_dist = 0
center_coords = [40.807849, -73.962121]
class Tester(Auditor):

    def auditor_get_distance(self, user_a, user_b, user_loc):
        usera_crdnt = swarm.sw_login(users[user_a][0],
                                     users[user_a][1],
                                     _repr_coords(center_coords),
                                     30 + random.uniform(-20, 10),
                                     DEVICE_ID1)
        usera_acc_token = usera_crdnt['access_token']
        userb_crdnt = swarm.sw_login(users[user_b][0],
                                     users[user_b][1],
                                     _repr_coords(center_coords),
                                     30 + random.uniform(-20, 10),
                                     DEVICE_ID2)
        userb_acc_token = usera_crdnt['access_token']

        userb = swarm.sw_get_friend_info(usera_acc_token, users[user_b][0])
        userb_id = str(userb['id'])
        rspn = swarm.sw_get_user_location(usera_acc_token,
                                          _repr_coords(user_loc),
                                          str(30 + random.uniform(-20, 10)),
                                          userb_id)
        if rspn is None:
            return (None, 1)
        else:
            return (float(rspn[2]) / 1000, 1)

    def auditor_set_location(self, user, lat, lon):
        user_crdnt = swarm.sw_login(users[user][0],
                                    users[user][1],
                                    _repr_coords(center_coords),
                                    30 + random.uniform(-20, 10),
                                    DEVICE_ID1)
        user_acc_token = user_crdnt['access_token']
        update = swarm.update_location(user_acc_token,
                                       DEVICE_ID1,
                                       _repr_coords([lat, lon]),
                                       str(30 + random.uniform(-20, 10)),
                                       _repr_coords([lat, lon]),
                                       str(30 + random.uniform(-20, 10)), '')
        if update is False:
            return (False, 1)
        else:
            return (True, 1)

t = Tester("swarm", [0, 1])
t.test_speed_limit()
t.test_location_verification()
t.test_query_limit()
t.test_dudp_attack([0.321869, 1.60934, 8.04672, 32.1869, 64.3738])
t.test_rudp_attack([[[0.1, float('inf')], 0.03, const.ROUNDING.BOTH]])
