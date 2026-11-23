#!/usr/bin/env python3

'''
Basic IPv4 router (static routing) in Python.
'''

import sys
import os
import time
from switchyard.lib.userlib import *

class Router(object):
    def __init__(self, net):
        self.net = net
        # other initialization stuff here
        #{router IP address : router MAC address} for every interface
        self.my_ip_to_mac = {}
        for intf in self.net.interfaces():
            for ip in intf.ipaddrs:
                ip = getattr(ip, 'ip', ip)
                self.my_ip_to_mac[ip] = intf.ethaddr


    def router_main(self):    
        '''
        Main method for router; we stay in a loop in this method, receiving
        packets until the end of time.
        '''
        while True:
            gotpkt = True
            try:
                # this router waits for a second to receive packets
                # if no packet arrives in a second, NoPackets except occurs
                timestamp,dev,pkt = self.net.recv_packet(timeout=1.0)
            except NoPackets:
                log_info("No packets available in recv_packet")
                gotpkt = False
            except Shutdown:
                log_info("Got shutdown signal")
                break

            if gotpkt:
                log_info("Got a packet: {}".format(str(pkt)))
                self.handle_packet(dev, pkt)

    def handle_packet(self, dev, pkt):
        arp = pkt.get_header(Arp)
        if arp is None or arp.operation != ArpOperation.Request:
            return

        mac_addr_found = self.my_ip_to_mac.get(arp.targetprotoaddr)
        if mac_addr_found is None:
            return

        reply = create_ip_arp_reply(srchw=mac_addr_found,
                                    srcip=arp.targetprotoaddr,
                                    dsthw=arp.senderhwaddr,
                                    targetip=arp.senderprotoaddr)

        log_info("Sending ARP reply on {}: {}".format(dev, str(reply)))
        self.net.send_packet(dev, reply)

def main(net):
    '''
    Main entry point for router.  Just create Router
    object and get it going.
    '''
    r = Router(net)
    r.router_main()
    net.shutdown()
