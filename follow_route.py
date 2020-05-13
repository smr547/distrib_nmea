#!/usr/bin/env python

# Test program. Simulate a vessel's passage around a specifed route 
# issue NMEA sentences representing position reports and vessel identification details 
# at specified periods

import argparse
import geojson
from shapely.geometry import Point
from geopy.distance import great_circle
import math
from datetime import datetime as dt
from copy import deepcopy
import pygc
from time import sleep
import aislib
import sys

nm_to_metres = 1852.0
# proximity_radius = 50.0 / nm_to_metres

def heading_Deg(from_point, to_point):
    # return the heading in degrees from_point to_point

    dLon = math.radians(to_point.x) - math.radians(from_point.x);
    y = math.sin(dLon) * math.cos(math.radians(to_point.y));
    x = math.cos(math.radians(from_point.y)) * math.sin(math.radians(to_point.y)) \
        - math.sin(math.radians(from_point.y)) * math.cos(math.radians(to_point.y)) \
        * math.cos(dLon);
    hdg = math.degrees(math.atan2(y, x))
    if hdg < 0: hdg += 360.0
    return hdg

def asLatLongTuple(point):
    return [point.y, point.x]

def distance_NM(from_point, to_point):
    # return the distance in nautical miles from_point to_point
    return great_circle(asLatLongTuple(from_point), asLatLongTuple(to_point)).miles

def new_point_given_distance_and_bearing(from_point, distance_NM, bearing_Deg):
    result = pygc.great_circle(distance=distance_NM * nm_to_metres, azimuth=bearing_Deg, \
        latitude=from_point.y, longitude=from_point.x)
    return Point(result['longitude'], result['latitude'])


class Leg(object):
    def __init__(self, start_point, end_point):
        self.start_point = start_point
        self.end_point = end_point
        self.next = None
      
    def length_NM(self):
        return distance_NM(self.start_point, self.end_point)

    def heading_Deg(self):
        return heading_Deg(self.start_point, self.end_point)

    def __str__(self):
        return "Leg of %f NM heading %f degrees" % (self.length_NM(), self.heading_Deg())


class Route(object):
    def __init__(self, waypoints, endless=False):

        self.legs = []

        if len(waypoints) < 3:
            raise ValueError("Not enough waypoints for Route")
        
        # assemble the legs into a route
        self.first_leg = Leg(waypoints[0], waypoints[1])
        self.legs.append(self.first_leg)
        prior_leg = self.first_leg 
        for i in range(2, len(waypoints)):
            leg = Leg(prior_leg.end_point, waypoints[i])
            self.legs.append(leg)
            prior_leg.next = leg
            prior_leg = leg
        self.last_leg = prior_leg
        if endless:
            implied_leg = Leg(self.last_leg.end_point, self.first_leg.start_point)
            prior_leg.next = implied_leg
            implied_leg.next = self.first_leg
            self.legs.append(implied_leg)
            self.last_leg = implied_leg
        self.endless = endless

    def leg_count(self):
        return len(self.legs)

    def length_NM(self):
        result = 0.0
        leg = self.first_leg
        while True:
            result += leg.length_NM() 
            if leg == self.last_leg:
                break
            leg = leg.next

        return result

class Vessel(object):
    def __init__(self, mmsi, name, cruise_speed=7.0, draught=2.3, callsign='', imo=0):
        self.mmsi = mmsi
        self.name = name
        self.draught = draught
        self.imo = imo
        self.callsign = callsign
        self.cruise_speed = cruise_speed

    def as_AIS_report(self, route={}):
        # Message Type 5
        aismsg = aislib.AISStaticAndVoyageReportMessage(mmsi=self.mmsi,
            imo=self.imo,
            callsign=self.callsign,
            shipname=self.name,
            shiptype=36,
            to_bow=5,to_stern=5,to_port=1,to_starboard=1, 
            draught=int(self.draught * 10.0),
            epfd=1, month=5, day=14, hour=20, minute=15,
            destination='CANBERRA')

        ais = aislib.AIS(aismsg)
        payload = ais.build_payload(False)
        return payload

    def __str__(self):
        s = "Vessel %s (%s)" % \
            (self.mmsi, self.name)
        return s

class LKP(object):
    # Last know position object
    def __init__(self, vessel, as_at=dt.utcnow(), leg=None, pos=None, course=0.0, speed=0.0):
        self.vessel = vessel
        self.as_at = as_at
        self.leg = leg
        self.pos = pos
        self.course = course
        self.speed = speed

    def __str__(self):
        s = "LKP of %s: at %s at %s -- course=%01f, speed=%01f" % \
            (self.vessel, self.as_at, self.pos, self.course, self.speed)
        return s

    def next(self, as_at=dt.utcnow()):
        # Calculation the movement of the vessel along the route and return a new last know position

        # heading to next waypoint
        hdg_deg = heading_Deg(self.pos, self.leg.end_point)

        now = dt.utcnow()
        period_seconds = (now - self.as_at).seconds
        dist_travelled_NM = self.speed * period_seconds / 3600.0
        
        # move position along route until we reach distance_travelled
        pos = deepcopy(self.pos)
        leg = self.leg
        hdg = 0.0
        dist2go = dist_travelled_NM
        while dist2go > 0.0 and leg is not None:
            dd = distance_NM(pos, leg.end_point)
            if dd >= dist2go:
                hdg = heading_Deg(pos, leg.end_point)
                # compute new pos (d2dist towards end point of this leg)
                pos = new_point_given_distance_and_bearing(pos, dist2go, hdg)
                dist2go = 0.0 # and end
            else:
                # move to next waypoint and continue moving
                dist2go -= dd
                pos = deepcopy(leg.end_point)
                leg = leg.next

        return LKP(self.vessel, as_at=now, leg=leg, pos=pos, course=hdg, speed=self.speed)

    def as_AIS_pos_report(self):
        # return an NMEA encoded position report
        
        aismsg = aislib.AISPositionReportMessage( \
            mmsi = self.vessel.mmsi, \
            status = 8, \
            sog = int(self.speed*10.0), \
            pa = 1, \
            lon = int(self.pos.x * 600000),
            lat = int(self.pos.y * 600000),
            # lon = (25*60+00)*10000,
            # lat = (35*60+30)*10000,
            cog = int(self.course * 10.0),
            ts = 40,
            raim = 1,
            comm_state = 82419
        )
        ais = aislib.AIS(aismsg)
        payload = ais.build_payload(False)
        return payload


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description='Vessel follows route')
    parser.add_argument('-f', '--fname', required=True, help='Route file (json format')
    parser.add_argument('-m', '--mmsi', required=True, type=long, help='Vessel mmsi number')
    parser.add_argument('-n', '--vessel_name', required=True, help='Vessel name')
    parser.add_argument('-s', '--vessel_speed', type=float, required=True, help='Vessel speed in knots')
    args = parser.parse_args()


    # read the route from a geojson file
    fname = args.fname
    with open(fname,'r') as infile:
        gj = geojson.load(infile)

    # assemble an array of waypoints
    waypoints =[]
    for c in gj.features[0]['geometry']['coordinates']:
        p = Point(c)
        waypoints.append(p)

    # assemble the legs into a route
    route = Route(waypoints, endless=True)
    # print "Route is %d legs totalling %f NM" % (route.leg_count(), route.length_NM())

    
    # print leg details

    # for leg in route.legs:
    #     print str(leg)

    v = Vessel(args.mmsi, args.vessel_name.upper(), cruise_speed=args.vessel_speed)

    lkp = LKP(v, leg=route.first_leg, pos=route.first_leg.start_point, course=0.0, speed=v.cruise_speed)
    # print(lkp)
    # print(lkp.as_AIS_pos_report())

    i = 0
    while 1:
        lkp = lkp.next()
        sys.stdout.write(lkp.as_AIS_pos_report() + "\n")
        i += 1
        if i >= 9:
            sys.stdout.write(v.as_AIS_report() + "\n")
            i = 0
        sys.stdout.flush()
        sleep(6)
         

