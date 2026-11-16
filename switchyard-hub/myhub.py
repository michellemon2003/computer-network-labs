#!/usr/bin/env python3

'''
Ethernet hub in Switchyard.
'''
from switchyard.lib.userlib import *


def main(net):


    my_interfaces = net.interfaces()  # get all NIC interface
    mymacs = [intf.ethaddr for intf in my_interfaces]  # get all MAC addresses
    counter = 0

    while True:
        try:
            # wait for a packet to arrive infinitely
            # dev : input port for the received packet

            timestamp,dev,packet = net.recv_packet()
        except NoPackets:
            continue
        except Shutdown:
            return

        log_info("In {} received packet {} on {}".format(net.name, packet, dev))
        eth = packet.get_header(Ethernet)
        if eth is None:
            log_info("Received a non-Ethernet packet?!")
            continue

        if eth.dst in mymacs:
            log_info("Received a packet intended for me")
        else:
            for intf in my_interfaces:
                if dev != intf.name:
                    log_info("Flooding packet {} to {}".format(packet, intf.name))
                    # the received packet will be sent out to all the rest ports
                    # except the port to which this packet is arrived
                    net.send_packet(intf, packet)

            counter += 1
            log_info("Forwarded {} packets (except the ones for me)".format(counter))
    net.shutdown()
