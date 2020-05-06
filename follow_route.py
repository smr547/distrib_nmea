#!/usr/bin/env python

import geojson
from shapely.geometry import Point
from geopy.distance import great_circle
import math

class Leg(object):
    def __init__(self, start_point, end_point):
        self.start_point = start_point
        self.end_point = end_point
        self.next = None
      
    def length_NM(self):

        def asLatLongTuple(point):
            return [point.y, point.x]

        return great_circle(asLatLongTuple(self.start_point), asLatLongTuple(self.end_point)).miles

    def heading_Deg(self):

        dLon = math.radians(self.end_point.x) - math.radians(self.start_point.x);
        y = math.sin(dLon) * math.cos(math.radians(self.end_point.y));
        x = math.cos(math.radians(self.start_point.y))*math.sin(math.radians(self.end_point.y)) - math.sin(math.radians(self.start_point.y))*math.cos(math.radians(self.end_point.y))*math.cos(dLon);
        hdg = math.degrees(math.atan2(y, x))
        if hdg < 0: hdg += 360.0
        return hdg

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
        


if __name__ == "__main__":

    # read the route from a geojson file
    fname = "./lbg_route.json"
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
