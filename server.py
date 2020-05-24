#!/usr/bin/env python
import select
import socket
import sys
import Queue
import time
import argparse


parser = argparse.ArgumentParser("Read NMEA sentence from FIFO and distribute to TCP clients")
parser.add_argument('-f', '--fifo', default='./nmea_fifo', help='path to NMEA input FIFO')
parser.add_argument('-p', '--port', default=10000, type=int, help='TCP port for client connections')
args = parser.parse_args()


nmea_fifo = open(args.fifo, "r", 0)


# Create a TCP/IP socket
server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.setblocking(0)

# Bind the socket to the port
server_address = ('', args.port)
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
    # print >>sys.stderr, '\nwaiting for the next event'
    readable, writeable, exceptional = select.select(inputs, outputs, inputs)
    # print "select returned, %d readable, %d writeable, %d exceptional\n" % (len(readable), len(writeable), len(exceptional))

    # process the readable files

    for s in readable:
        if s is server:

            # A "readable" server socket is ready to accept a connection
            connection, client_address = s.accept()
            # print >>sys.stderr, 'new connection from', client_address
            connection.setblocking(0)
            outputs.append(connection)
            inputs.append(connection)
 

            # Give the connection a queue for data we want to send
            message_queues[connection] = Queue.Queue()

        elif s is nmea_fifo:
            # print >>sys.stderr, 'Reading from fifo'
            data = nmea_fifo.readline()
            if len(data) == 0:
                print >>sys.stderr, "No data read from fifo, must be closed"
                sys.exit(0) 
            # distribute msg to all queues
            # sys.stdout.write("read data: %s\n" % (data, ))
            # sys.stdout.flush()
            for c in message_queues.keys():
                message_queues[c].put(data) 
                if c not in outputs:
                    outputs.append(c)
            if len(message_queues) == 0:
                # print >> sys.stderr, "Discarding sentence, no readers"
                pass

        else:
            # any input from a client should close the connection
   
            # print >>sys.stderr, "Closing client %s" % (s)
            inputs.remove(s)
            if s in outputs:
                outputs.remove(s)
            if s in message_queues:
                del message_queues[s]
            s.close()

    # Handle outputs
    for s in writeable:
        try:
            # print >>sys.stderr, "%s is writeables" % (s)
            next_msg = message_queues[s].get_nowait()
        except Queue.Empty:
            # No messages waiting so stop checking for writability.
            # print >>sys.stderr, 'output queue for', s.getpeername(), 'is empty'
            outputs.remove(s)
        else:
            # print >>sys.stderr, 'sending "%s" to %s' % (next_msg, s.getpeername())
            s.send(next_msg)

    # process exceptions

    for e in exceptional:
        if e is nmea_fifo:
            # fifo is close there are no more writers
            print >> sys.stderr,  'fifo has closed there are no more writers'
            sys.exit(1)
