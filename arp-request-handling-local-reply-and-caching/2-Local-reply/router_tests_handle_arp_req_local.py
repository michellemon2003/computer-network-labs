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
    #s.add_interface('eth0', '10:00:00:00:00:00', '192.168.0.0/24') # (assume) connected to a host0 (30:00:...:00)
    s.add_interface(router_nic_names[0], router_mac_addrs[0], router_ip_addrs[0])
    #s.add_interface('eth1', '10:00:00:00:00:01', '172.192.0.0/24') # (assume) connected to a host1 (30:00:...:01)
    s.add_interface(router_nic_names[1], router_mac_addrs[1], router_ip_addrs[1])
    #s.add_interface('eth2', '10:00:00:00:00:02',    '10.0.0.0/24') # (assume) connected to a host2 (30:00:...:02)
    s.add_interface(router_nic_names[2], router_mac_addrs[2], router_ip_addrs[2])

    host0_ip, host0_mac = '192.168.0.10', '30:00:00:00:00:00'
    host1_ip, host1_mac = '172.192.0.10', '30:00:00:00:00:01'
    host2_ip, host2_mac = '10.0.0.10'   , '30:00:00:00:00:02'
    
    zero_ip = "0.0.0.0"

    # TC 1-------------------------------------------
    unknown_ip = "1.2.3.4"
    testArpREQpkt = create_ip_arp_request(srchw    = host0_mac,
                                          srcip    = host0_ip,
                                          targetip = unknown_ip)
    s.expect(PacketInputEvent("eth0", testArpREQpkt, display=Ethernet), "TC 1. Request for an unknown IP addr.")
    s.expect(PacketInputTimeoutEvent(2.0), "TC 1. No response expected")
    # TC 2-------------------------------------------
    testArpREQpkt = create_ip_arp_request(srchw    = host0_mac,
                                          srcip    = host0_ip,
                                          targetip = router_ip_addrs[0])
    s.expect(PacketInputEvent("eth0", testArpREQpkt, display=Ethernet), "TC 2. REQ for Router-eth0 IP addr.")
    testArpRESPpkt = create_ip_arp_reply(srchw    = router_mac_addrs[0],
                                         dsthw    = host0_mac,
                                         srcip    = router_ip_addrs[0],
                                         targetip = host0_ip)
    s.expect(PacketOutputEvent("eth0", testArpRESPpkt, display=Ethernet), "TC 2. response generated")
    # TC 3-------------------------------------------
    testArpREQpkt = create_ip_arp_request(srchw    = host1_mac,
                                          srcip    = host1_ip,
                                          targetip = router_ip_addrs[1])
    s.expect(PacketInputEvent("eth1", testArpREQpkt, display=Ethernet), "TC 3. REQ for Router-eth1 IP addr.")
    testArpRESPpkt = create_ip_arp_reply(srchw    = router_mac_addrs[1],
                                         dsthw    = host1_mac,
                                         srcip    = router_ip_addrs[1],
                                         targetip = host1_ip)
    s.expect(PacketOutputEvent("eth1", testArpRESPpkt, display=Ethernet), "TC 3. response generated")
    # TC 4-------------------------------------------
    testArpREQpkt = create_ip_arp_request(srchw    = host2_mac,
                                          srcip    = host2_ip,
                                          targetip = router_ip_addrs[2])
    s.expect(PacketInputEvent("eth2", testArpREQpkt, display=Ethernet), "TC 4. REQ for Router-eth2 IP addr.")
    testArpRESPpkt = create_ip_arp_reply(srchw    = router_mac_addrs[2],
                                         dsthw    = host2_mac,
                                         srcip    = router_ip_addrs[2],
                                         targetip = host2_ip)
    s.expect(PacketOutputEvent("eth2", testArpRESPpkt, display=Ethernet), "TC 4. response generated")

    return s

scenario = my_tests()
