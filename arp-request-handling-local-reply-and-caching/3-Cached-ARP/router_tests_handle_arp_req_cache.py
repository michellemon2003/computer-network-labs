#!/usr/bin/env python3

"""
Handle ARP Request only if
- the packet if ARP REQ
- the ARP is asking the translation for one of the interfaces of the router
"""

from switchyard.lib.userlib import *
from switchyard.lib.packet import *
import time

TYPE_REQUEST = 1
TYPE_REPLY = 2
bc_mac, zero_mac = "ff:ff:ff:ff:ff:ff", "00:00:00:00:00:00" # broadcasting , zero MAC

"""
def mk_pkt(hwsrc, hwdst, ipsrc, ipdst, reply=True):
    ether = Ethernet(src=hwsrc, dst=hwdst, ethertype=EtherType.IP)
    ippkt = IPv4(src=ipsrc, dst=ipdst, protocol=IPProtocol.ICMP, ttl=32)
    icmppkt = ICMP()
    if reply:
        icmppkt.icmptype = ICMPType.EchoReply
    else:
        icmppkt.icmptype = ICMPType.EchoRequest
    return ether + ippkt + icmppkt
"""


def my_tests():
    s = TestScenario("My_Switch_LRU tests")

    router_nic_names = ['eth0','eth1','eth2']
    router_mac_addrs = ['10:00:00:00:00:00','10:00:00:00:00:01','10:00:00:00:00:02']
    router_ip_addrs  = ['192.168.0.1','172.192.0.1','10.0.0.1']

    s.add_interface(router_nic_names[0], router_mac_addrs[0], router_ip_addrs[0])
    s.add_interface(router_nic_names[1], router_mac_addrs[1], router_ip_addrs[1])
    s.add_interface(router_nic_names[2], router_mac_addrs[2], router_ip_addrs[2])

    host0_ip, host0_mac = '192.168.0.10', '30:00:00:00:00:00'
    host1_ip, host1_mac = '172.192.0.10', '30:00:00:00:00:01'
    host2_ip, host2_mac = '10.0.0.10'   , '30:00:00:00:00:02'
    
    zero_ip = "0.0.0.0"
    # TC 1-------------------------------------------
    # for an unknown IP, do nothing
    unknown_ip = "1.2.3.4"
    testArpREQpkt = create_ip_arp_request(srchw    = host0_mac,
                                          srcip    = host0_ip,
                                          targetip = unknown_ip)
    s.expect(PacketInputEvent(router_nic_names[0], testArpREQpkt, display=Ethernet), "TC 1a. Request for an unknown IP addr.")
    s.expect(PacketInputTimeoutEvent(1.0), "TC 1. No response expected")
    # TC 2-------------------------------------------
    testArpREQpkt = create_ip_arp_request(srchw    = host0_mac,
                                          srcip    = host0_ip,
                                          targetip = router_ip_addrs[0])
    s.expect(PacketInputEvent(router_nic_names[0], testArpREQpkt, display=Ethernet), "TC 2a. REQ for Router-eth0 IP addr.")
    testArpRESPpkt = create_ip_arp_reply(srchw    = router_mac_addrs[0],
                                         dsthw    = host0_mac,
                                         srcip    = router_ip_addrs[0],
                                         targetip = host0_ip)
    s.expect(PacketOutputEvent(router_nic_names[0], testArpRESPpkt, display=Ethernet), "TC 2b. response generated")
    # TC 3-------------------------------------------
    testArpREQpkt = create_ip_arp_request(srchw    = host1_mac,
                                          srcip    = host1_ip,
                                          targetip = router_ip_addrs[1])
    s.expect(PacketInputEvent(router_nic_names[1], testArpREQpkt, display=Ethernet), "TC 3. REQ for Router-eth1 IP addr.")
    testArpRESPpkt = create_ip_arp_reply(srchw    = router_mac_addrs[1],
                                         dsthw    = host1_mac,
                                         srcip    = router_ip_addrs[1],
                                         targetip = host1_ip)
    s.expect(PacketOutputEvent(router_nic_names[1], testArpRESPpkt, display=Ethernet), "TC 3B. response generated")
    # TC 4-------------------------------------------
    testArpREQpkt = create_ip_arp_request(srchw    = host2_mac,
                                          srcip    = host2_ip,
                                          targetip = router_ip_addrs[2])
    s.expect(PacketInputEvent(router_nic_names[2], testArpREQpkt, display=Ethernet), "TC 4a. REQ for Router-eth2 IP addr.")
    testArpRESPpkt = create_ip_arp_reply(srchw    = router_mac_addrs[2],
                                         dsthw    = host2_mac,
                                         srcip    = router_ip_addrs[2],
                                         targetip = host2_ip)
    s.expect(PacketOutputEvent(router_nic_names[2], testArpRESPpkt, display=Ethernet), "TC 4b. response generated")
    # TC 5: now we know about host 1 ----------------
    testArpREQpkt = create_ip_arp_request(srchw    = host0_mac,
                                          srcip    = host0_ip,
                                          targetip = host1_ip)
    s.expect(PacketInputEvent(router_nic_names[0], testArpREQpkt, display=Ethernet), "TC 5. REQ for host1 IP addr by host0.")
    testArpRESPpkt = create_ip_arp_reply(srchw    = host1_mac,
                                         dsthw    = host0_mac,
                                         srcip    = host1_ip,
                                         targetip = host0_ip)
    s.expect(PacketOutputEvent(router_nic_names[0], testArpRESPpkt, display=Ethernet), "TC 5. response generated")
    # TC 6: now we know about host 2 ----------------
    testArpREQpkt = create_ip_arp_request(srchw    = host1_mac,
                                          srcip    = host1_ip,
                                          targetip = host2_ip)
    s.expect(PacketInputEvent(router_nic_names[1], testArpREQpkt, display=Ethernet), "TC 6. REQ for host2 IP addr by host1.")
    testArpRESPpkt = create_ip_arp_reply(srchw    = host2_mac,
                                         dsthw    = host1_mac,
                                         srcip    = host2_ip,
                                         targetip = host1_ip)
    s.expect(PacketOutputEvent(router_nic_names[1], testArpRESPpkt, display=Ethernet), "TC 6. response generated")
    # TC 7: now we know about host 0 ----------------
    testArpREQpkt = create_ip_arp_request(srchw    = host2_mac,
                                          srcip    = host2_ip,
                                          targetip = host0_ip)
    s.expect(PacketInputEvent(router_nic_names[2], testArpREQpkt, display=Ethernet), "TC 7. REQ for host0 IP addr by host2.")
    testArpRESPpkt = create_ip_arp_reply(srchw    = host0_mac,
                                         dsthw    = host2_mac,
                                         srcip    = host0_ip,
                                         targetip = host2_ip)
    s.expect(PacketOutputEvent(router_nic_names[2], testArpRESPpkt, display=Ethernet), "TC 7. response generated")

    return s

scenario = my_tests()
