
Allows navigation, weather and other data to be shared with multiple devices on board a boat or yacht. 

The system reads NMEA sentences from multiple sources and distribute to multiple clients. 

## Application

The software is designed to run on a [Raspberry Pi](https://www.raspberrypi.org/) installed on board a yacht. 
The system will collect data from various sensors on board and distribute copies to any remote client. 
The system has been tested with [Navionics](https://www.navionics.com/aus/) running on various iPads
and receiving real time [AIS](https://www.amsa.gov.au/safety-navigation/navigation-systems/about-automatic-identification-system) data from the Raspberry Pi.

## Server
The python program [server.py](./server.py) is run as a system service [see the control file](./nmea_server.service). 
The program reads NMEA sentences from the 
named pipe (aka: FIFO) ``nmea_fifo``. The server also listens for connections on a TCP port.
As each client connects the program will then feed a copy of all NMEA sentences received on the input FIFO. 

## NMEA sources
A cruising yacht will typically have multiple sensors on board capable of generating interesting data as NMEA sentences.
The [distrib_nmea system](./README.md) provides a service for each NMEA source. An ``NMEA source service`` reads the 
sentences via the appropriate hardward interface and writes them to the ``nmea_fifo`` from which they are read by the 
server and distributed to the attached clients.

## Test service
The only ``NMEA source service`` currently available is the [follow route program](./follow_route.py). This program is 
designed for testing the system. It simulates the operation of an AIS system by predicting the passage of a vessel around a
specified route. The program will emit real time AIS sentences as the vessel moves around the route

* routes are generated using the [geojson tool](http://geojson.io) 
* Here is an [example route around Lake Burley Griffin](./lbg_route.json)
* [Ruby Princess](./ruby_princess_LBG.sh) test script
* Test script [as a service](./ruby_princess_LBG.service)
