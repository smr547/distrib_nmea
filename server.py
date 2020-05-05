#!/usr/bin/env python
import select
import socket
import sys
import Queue
import time

# open the input fifo

# dummy = open("./nmea_fifo", "w")
nmea_fifo = open("./nmea_fifo", "r", 0)


# Create a TCP/IP socket
server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.setblocking(0)

# Bind the socket to the port
server_address = ('localhost', 10000)
print >>sys.stderr, 'starting up on %s port %s' % server_address
server.bind(server_address)

# Listen for incoming connections
server.listen(5)

# fifo  from which we expect to read
inputs = [ server, nmea_fifo ]
# inputs = [ server, nmea_fifo ]

# Sockets to which we expect to write
outputs = [ ]

# Outgoing message queues (socket:Queue)
message_queues = {}

while inputs:

    # Wait for at least one of the sockets to be ready for processing
    print >>sys.stderr, '\nwaiting for the next event'
    readable, writeable, exceptional = select.select(inputs, outputs, inputs)
    print "select returned, %d readable, %d writeable, %d exceptional\n" % (len(readable), len(writeable), len(exceptional))

    # process the readable files

    for s in readable:
        if s is server:

            # A "readable" server socket is ready to accept a connection
            connection, client_address = s.accept()
            print >>sys.stderr, 'new connection from', client_address
            connection.setblocking(0)
#           inputs.append(connection)

            # Give the connection a queue for data we want to send
            message_queues[connection] = Queue.Queue()

        if s is nmea_fifo:
            print >>sys.stderr, 'Reading from fifo'
            data = nmea_fifo.readline()
            if len(data) == 0:
                print >>sys.stderr, "No data read from fifo, must be closed"
                sys.exit(0) 
            # distribute msg to all queues
            sys.stdout.write("read data: %s\n" % (data, ))
            sys.stdout.flush()
            for q in message_queues.values():
                q.put(data) 

    # process exceptions

    for e in exceptional:
        if e is nmea_fifo:
            # fifo is close there are no more writers
            print >> sys.stderr,  'fifo has closed there are no more writers'
            sys.exit(1)


    time.sleep(1)
