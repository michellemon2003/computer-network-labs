#!/usr/bin/env python3

'''
Basic IPv4 router (static routing) in Python.
'''

import sys
import os
import time
import common
from ipaddress import IPv4Address, IPv4Network
from switchyard.lib.userlib import *

class Router(object):
    def __init__(self, net):
        self.net = net
        # other initialization stuff here
        # Look-up table: IP address -> MAC address
        self.arp_table = {}
        self.router_ips = set()
        self.interfaces = {
            intf.name: intf
            for intf in self.net.interfaces()
        }

        for intf in self.net.interfaces():
            for ip in intf.ipaddrs:
                ip = getattr(ip, 'ip', ip)
                self.arp_table[ip] = intf.ethaddr
                self.router_ips.add(ip)

        #Initialize forwarding table
        self.routing_table = []
        self.initialize_routing_table("forwarding_table.txt")

    def initialize_routing_table(self, in_file):
        filepath = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            in_file
        )

        self.routing_table = []

        with open(filepath, 'r') as src_file:
            for line in src_file:
                if not line.strip():
                    continue

                network, mask, next_hop, interface = line.split()

                entry = {
                    'network': IPv4Network(
                        network + '/' + mask,
                        strict = False
                    ),
                    'next_hop': IPv4Address(next_hop),
                    'interface': interface
                }

                self.routing_table.append(entry)

        log_info("Forwarding table: {}".format(self.routing_table))

    def forwarding_table_lookup(self, dst_ip):
        best_match = None

        for entry in self.routing_table:
            if dst_ip in entry['network']:
                if best_match is None:
                    best_match = entry

                elif entry['network'].prefixlen > \
                        best_match['network'].prefixlen:
                    best_match = entry

        return best_match

    def resolve_mac(self, next_hop):

        # Check the existing ARP cache
        if next_hop in self.arp_table:
            return self.arp_table[next_hop]

        # Search interfaces in ascending order
        for name in sorted(self.interfaces):
            intf = self.interfaces[name]

            for ip in intf.ipaddrs:
                src_ip = getattr(ip, 'ip', ip)

                if not isinstance(src_ip, IPv4Address):
                    continue

                for i in range(common.ARP_REQ_RETRY_LIMIT):

                    # Generate ARP Request
                    request = create_ip_arp_request(
                        srchw=intf.ethaddr,
                        srcip=src_ip,
                        targetip=next_hop
                    )

                    log_info("Sending ARP request on {}".format(name))
                    self.net.send_packet(name, request)

                    # Wait for ARP Reply
                    try:
                        timestamp, dev, pkt = self.net.recv_packet(
                            timeout=common.PACKET_RECV_TIMEOUT
                        )

                    except NoPackets:
                        log_info("ARP request timeout on {}".format(name))
                        continue

                    arp = pkt.get_header(Arp)

                    if arp is not None:
                        self.arp_table[arp.senderprotoaddr] = \
                            arp.senderhwaddr

                        if arp.operation == ArpOperation.Reply:
                            if arp.senderprotoaddr == next_hop:
                                return arp.senderhwaddr

        # MAC address resolution failed
        log_info("ARP resolution failed for {}".format(next_hop))
        return None   

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

        # Existing ARP Request handling
        if arp is not None:
            self.arp_table[arp.senderprotoaddr] = arp.senderhwaddr
            log_info("ARP table: {}".format(self.arp_table))

            if arp.operation != ArpOperation.Request:
                return

            mac_addr_found = self.arp_table.get(arp.targetprotoaddr)

            if mac_addr_found is None:
                return

            reply = create_ip_arp_reply(
                srchw=mac_addr_found,
                srcip=arp.targetprotoaddr,
                dsthw=arp.senderhwaddr,
                targetip=arp.senderprotoaddr
            )

            log_info("Sending ARP reply on {}: {}".format(
                dev, str(reply)
            ))

            self.net.send_packet(dev, reply)
            return

        # IPv4 packet handling
        ipv4 = pkt.get_header(IPv4)

        if ipv4 is None:
            return

        dst_ip = ipv4.dst

        # Drop packets addressed to the router itself
        if dst_ip in self.router_ips:
            log_info("Destination is the router itself")
            return

        # Forwarding Table Lookup
        entry = self.forwarding_table_lookup(dst_ip)

        # Drop packets if no matching entry exists
        if entry is None:
            log_info("No matching forwarding entry")
            return

        log_info("Destination IP: {}".format(dst_ip))
        log_info("Next hop IP: {}".format(entry['next_hop']))
        log_info("Output interface: {}".format(entry['interface']))
        
        # Decrease TTL
        ipv4.ttl -= 1

        # Get next hop and output interface
        next_hop = entry['next_hop']
        out_interface = entry['interface']

        # Resolve next hop MAC address
        next_hop_mac = self.resolve_mac(next_hop)

        if next_hop_mac is None:
            return

        # Update Ethernet header
        ethernet = pkt.get_header(Ethernet)
        ethernet.src = self.interfaces[out_interface].ethaddr
        ethernet.dst = next_hop_mac

        # Forward packet
        log_info("Forwarding packet on {}".format(out_interface))
        self.net.send_packet(out_interface, pkt)

def main(net):
    '''
    Main entry point for router.  Just create Router
    object and get it going.
    '''
    r = Router(net)
    r.router_main()
    net.shutdown()
