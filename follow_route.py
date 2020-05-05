#!/usr/bin/env python

import geojson
from shapely.geometry import Point
from geopy.distance import great_circle

class Leg(object):
    def __init__(self, start_point, end_point):
        self.start_point = start_point
        self.end_point = end_point
        self.next = None
      
    def length_NM(self):

        def asLatLongTuple(point):
            return [point.y, point.x]

        return great_circle(asLatLongTuple(self.start_point), asLatLongTuple(self.end_point)).miles


class Route(object):
    def __init__(self, waypoints, endless=False):

        if len(waypoints) < 3:
            raise ValueError("Not enough waypoints for Route")
        
        # assemble the legs into a route
        self.first_leg = Leg(waypoints[0], waypoints[1])
        prior_leg = self.first_leg 
        for i in range(2, len(waypoints)):
            leg = Leg(prior_leg.end_point, waypoints[i])
            prior_leg.next = leg
            prior_leg = leg
        self.last_leg = prior_leg
        if endless:
            prior_leg.next = self.first_leg
        self.endless = endless

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
    print "Route is %f NM" % (route.length_NM())
    
