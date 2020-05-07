#!/usr/bin/env python

import geojson
from shapely.geometry import Point
from geopy.distance import great_circle
import math
from datetime import datetime

nm_to_metres = 1852.0
proximity_radius = 50.0 / nm_to_metres

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
    def __init__(self, mmsi, name, cruise_speed=7.0):
        self.mmsi = mmsi
        self.name = name
        self.cruise_speed = cruise_speed

    def __str__(self):
        s = "Vessel %s (%s)" % \
            (self.mmsi, self.name)
        return s

class LKP(object):
    # Last know position object
    def __init__(self, vessel, as_at=datetime.utcnow(), leg=None, pos=None, course=0.0, speed=0.0):
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

    def new(as_at=datetime.utcnow()):
        # Calculation the movement of the vessel along the route and return a new last know position

        # heading to next waypoint
        hdg_deg = heading_Deg(self.pos, self.leg.end_point)
        
        
        
        
        


if __name__ == "__main__":

    # read the route from a geojson file
    fname = "./lbg_route.json"
    fname = "./lake_pambula_route.json"
    with open(fname,'r') as infile:
        gj = geojson.load(infile)

    # assemble an array of waypoints
    waypoints =[]
    for c in gj.features[0]['geometry']['coordinates']:
        p = Point(c)
        waypoints.append(p)

    # assemble the legs into a route
    route = Route(waypoints, endless=True)
    print "Route is %d legs totalling %f NM" % (route.leg_count(), route.length_NM())

    
    # print leg details

    for leg in route.legs:
        print str(leg)

    v = Vessel("1234", "Trilogy")

    lkp = LKP(v, leg=route.first_leg, pos=route.first_leg.start_point, course=0.0, speed=v.cruise_speed)
    print(lkp)
