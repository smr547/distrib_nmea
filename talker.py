#!/usr/bin/env python

import time

n = 0
with open("./nmea_fifo",'w') as fifo:
    while 1:
        fifo.write("Line number %d\n" % (n, ))
        fifo.flush()
        n += 1
        time.sleep(3)


