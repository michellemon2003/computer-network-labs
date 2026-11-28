#!/usr/bin/env python3

"""
Handle ARP Request only if
- the packet if ARP REQ
- the ARP is asking the translation for one of the interfaces of the router
"""

from switchyard.lib.userlib import *
from switchyard.lib.packet import *
from switchyard.lib.address import *
from switchyard.lib.interface import *
import time
import common

TYPE_REQUEST = 1
TYPE_REPLY = 2
bc_mac, zero_mac = "ff:ff:ff:ff:ff:ff", "00:00:00:00:00:00" # broadcasting , zero MAC
zero_ip = "0.0.0.0"

def mk_udp_pkt(hwsrc, hwdst, ipsrc, ipdst, ttl):
    ether = Ethernet(src=hwsrc, dst=hwdst, ethertype=EtherType.IP)
    ippkt = IPv4(src=ipsrc, dst=ipdst, protocol=IPProtocol.UDP, ttl=ttl)
    udp = UDP()
    pkt = ether + ippkt + udp
    pkt[UDP].src = 10_000
    pkt[UDP].dst = 20_000
    pkt += b'Some application data bypes'
    return pkt

def mk_icmp_pkt(hwsrc, hwdst, ipsrc, ipdst, request=True, ttl=32):
    ether = Ethernet(src=hwsrc, dst=hwdst, ethertype=EtherType.IP)
    ippkt = IPv4(src=ipsrc, dst=ipdst, protocol=IPProtocol.ICMP, ttl=ttl)
    icmppkt = ICMP()    
    if request:
        icmppkt.icmptype = ICMPType.EchoRequest
    else:
        icmppkt.icmptype = ICMPType.EchoReply

    return ether + ippkt + icmppkt

PORT2SERVER1 = 0
PORT2SERVER2 = 1
PORT2CLIENT  = 2
def my_tests():
    s = TestScenario("My Router Tests")
    router_nic_names = ['router-eth0','router-eth1','router-eth2']
    router_mac_addrs = ['40:00:00:00:00:00','40:00:00:00:00:01','40:00:00:00:00:02']
    router_ip_addrs  = ['192.168.100.2','192.168.200.2','10.1.1.2']

    #s.add_interface('eth0', '10:00:00:00:00:00', '192.168.0.0/24') # (assume) connected to a host0 (30:00:...:00)
    s.add_interface(router_nic_names[0], router_mac_addrs[0], router_ip_addrs[0])
    #s.add_interface('eth1', '10:00:00:00:00:01', '172.192.0.0/24') # (assume) connected to a host1 (30:00:...:01)
    s.add_interface(router_nic_names[1], router_mac_addrs[1], router_ip_addrs[1])
    #s.add_interface('eth2', '10:00:00:00:00:02',    '10.0.0.0/24') # (assume) connected to a host2 (30:00:...:02)
    s.add_interface(router_nic_names[2], router_mac_addrs[2], router_ip_addrs[2])

    server1_ip, server1_mac = '192.168.100.1', '10:00:00:00:00:00'
    server2_ip, server2_mac = '192.168.200.1', '20:00:00:00:00:00'
    client_ip,  client_mac  = '10.1.1.1'     , '30:00:00:00:00:02'
    
    Enable_Static_Routing_With_Empty_ARP_Cache = True
    if Enable_Static_Routing_With_Empty_ARP_Cache:
        """
            This is the very first part of the test case
            So, the ARP cache table must be empty
            The following test cases may trigger ARP Request,
                which makes the problem more complex
            ARP search will be carried out on the ascending order
                of the *interface name*
        """
        # TC 0.1: server1->server2 ----------------
        # 0.1a. UDP pkt:  server 1 => server 2
        udp_packet1 = mk_udp_pkt(hwsrc = server1_mac,
                                 hwdst = router_mac_addrs[PORT2SERVER1],
                                 ipsrc = server1_ip,
                                 ipdst = server2_ip,
                                 ttl = 32)
        s.expect(PacketInputEvent(router_nic_names[PORT2SERVER1], udp_packet1, display=Ethernet), 
                                  "TC 0.1a. udp pkt to fwd svr1 -> router")

        # Router does not know about the ip/mac info about server 2
        # thus, let's send out ARP query messages

        # 0.1b. ARP query over eth0, multiple times (= common.ARP_REQ_RETRY_LIMIT)
        # router will not get the reply
        for _ in range(common.ARP_REQ_RETRY_LIMIT):
            arp_pkt1 = create_ip_arp_request(srchw=router_mac_addrs[PORT2SERVER1],
                                             srcip=router_ip_addrs[PORT2SERVER1],
                                             targetip=server2_ip)
            s.expect(PacketOutputEvent(router_nic_names[PORT2SERVER1], arp_pkt1, display=Ethernet), 
                                       "TC 0.1b. ARP query over eth0 (expecting no response)")
            s.expect(PacketInputTimeoutEvent(common.PACKET_RECV_TIMEOUT+1.0), "TC 0.1b. Timeout (added +1 sec to be safe)")

        # 0.1c. ARP query over eth1 => router will recv reply from server 2
        # since the server 2 is attached to eth1
        for _ in range(common.ARP_REQ_RETRY_LIMIT):
            arp_pkt1 = create_ip_arp_request(srchw=router_mac_addrs[PORT2SERVER2],
                                             srcip=router_ip_addrs[PORT2SERVER2],
                                             targetip=server2_ip)
            s.expect(PacketOutputEvent(router_nic_names[PORT2SERVER2], arp_pkt1, display=Ethernet), 
                                       "TC 0.1c. ARP query over eth1 (expecting arp reply)")
            arp_pkt2 = create_ip_arp_reply(srchw=server2_mac,
                                           dsthw=router_mac_addrs[PORT2SERVER2],
                                           srcip=server2_ip,
                                           targetip=router_ip_addrs[PORT2SERVER2])
            s.expect(PacketInputEvent(router_nic_names[PORT2SERVER2], arp_pkt2, display=Ethernet),
                                      "TC 0.1d. ARP reply recvd")
            break  # router will get what it wants, so let's stop here

        # 0.1d. UDP pkt from router to server2
        # now, router can forward the packet to setver2
        udp_packet2 = mk_udp_pkt(hwsrc = router_mac_addrs[PORT2SERVER2],
                                 hwdst = server2_mac,
                                 ipsrc = server1_ip, # shouldn't change
                                 ipdst = server2_ip, # shouldn't change
                                 ttl = 31) # decrement by 1
        s.expect(PacketOutputEvent(router_nic_names[PORT2SERVER2], udp_packet2, display=Ethernet), 
                                   "TC 0.1e. udp pkt to fwd router -> svr2")

    Enable_ArpReplyTest = True
    if Enable_ArpReplyTest:
        # TC 1.1-------------------------------------------
        # assume that arp request cannot trigger additional request
        unknown_ip = "1.2.3.4"
        testArpREQpkt = create_ip_arp_request(srchw    = server1_mac,
                                              srcip    = server1_ip,
                                              targetip = unknown_ip)
        s.expect(PacketInputEvent(router_nic_names[0], testArpREQpkt, display=Ethernet), "TC 1.1. ARP Request for an unknown IP addr.")
        # no one will reply to this request
        s.expect(PacketInputTimeoutEvent(1.0), "TC 1.1. No response expected")
        
        # TC 1.2-------------------------------------------
        testArpREQpkt = create_ip_arp_request(srchw    = server1_mac,
                                              srcip    = server1_ip,
                                              targetip = router_ip_addrs[0])
        s.expect(PacketInputEvent(router_nic_names[0], testArpREQpkt, display=Ethernet), "TC 1.2. REQ for Router-eth0 IP addr.")
        # router can reply to this request
        testArpRESPpkt = create_ip_arp_reply(srchw   = router_mac_addrs[0],
                                            dsthw    = server1_mac,
                                            srcip    = router_ip_addrs[0],
                                            targetip = server1_ip)
        s.expect(PacketOutputEvent(router_nic_names[0], testArpRESPpkt, display=Ethernet), "TC 1.2. response generated")
        # TC 1.3-------------------------------------------
        testArpREQpkt = create_ip_arp_request(srchw  = server2_mac,
                                            srcip    = server2_ip,
                                            targetip = router_ip_addrs[1])
        s.expect(PacketInputEvent(router_nic_names[1], testArpREQpkt, display=Ethernet), "TC 1.3. REQ for Router-eth1 IP addr.")
        # router can reply to this request
        testArpRESPpkt = create_ip_arp_reply(srchw   = router_mac_addrs[1],
                                            dsthw    = server2_mac,
                                            srcip    = router_ip_addrs[1],
                                            targetip = server2_ip)
        s.expect(PacketOutputEvent(router_nic_names[1], testArpRESPpkt, display=Ethernet), "TC 1.3. response generated")
        # TC 1.4-------------------------------------------
        testArpREQpkt = create_ip_arp_request(srchw  = client_mac,
                                            srcip    = client_ip,
                                            targetip = router_ip_addrs[2])
        s.expect(PacketInputEvent(router_nic_names[2], testArpREQpkt, display=Ethernet), "TC 1.4. REQ for Router-eth2 IP addr.")
        # router can reply to this request
        testArpRESPpkt = create_ip_arp_reply(srchw   = router_mac_addrs[2],
                                            dsthw    = client_mac,
                                            srcip    = router_ip_addrs[2],
                                            targetip = client_ip)
        s.expect(PacketOutputEvent(router_nic_names[2], testArpRESPpkt, display=Ethernet), "TC 1.4. response generated")

        # TC 1.5: now we know about host 1 (= server 2)
        # we learned it from the ARP request from host 1
        testArpREQpkt = create_ip_arp_request(srchw  = server1_mac,
                                            srcip    = server1_ip,
                                            targetip = server2_ip)
        s.expect(PacketInputEvent(router_nic_names[0], testArpREQpkt, display=Ethernet), "TC 1.5. REQ for server2's IP addr by server1.")
        testArpRESPpkt = create_ip_arp_reply(srchw   = server2_mac,
                                            dsthw    = server1_mac,
                                            srcip    = server2_ip,
                                            targetip = server1_ip)
        s.expect(PacketOutputEvent(router_nic_names[0], testArpRESPpkt, display=Ethernet), "TC 1.5. response generated")
        # TC 1.6: now we know about host 2 (= client))
        # we learned it from the ARP request from host 2
        testArpREQpkt = create_ip_arp_request(srchw  = server2_mac,
                                            srcip    = server2_ip,
                                            targetip = client_ip)
        s.expect(PacketInputEvent(router_nic_names[1], testArpREQpkt, display=Ethernet), "TC 1.6. REQ for client IP addr by server2.")
        testArpRESPpkt = create_ip_arp_reply(srchw   = client_mac,
                                            dsthw    = server2_mac,
                                            srcip    = client_ip,
                                            targetip = server2_ip)
        s.expect(PacketOutputEvent(router_nic_names[1], testArpRESPpkt, display=Ethernet), "TC 1.6. response generated")
        # TC 1.7: now we know about host 0 (= server1)
        # we learned it from the ARP request from host 0
        testArpREQpkt = create_ip_arp_request(srchw  = client_mac,
                                            srcip    = client_ip,
                                            targetip = server1_ip)
        s.expect(PacketInputEvent(router_nic_names[2], testArpREQpkt, display=Ethernet), "TC 1.7. REQ for server1 IP addr by client.")
        testArpRESPpkt = create_ip_arp_reply(srchw   = server1_mac,
                                            dsthw    = client_mac,
                                            srcip    = server1_ip,
                                            targetip = client_ip)
        s.expect(PacketOutputEvent(router_nic_names[2], testArpRESPpkt, display=Ethernet), "TC 1.7. response generated")

    Enable_Static_Routing = True
    if Enable_Static_Routing:
        # TC 2.1: server1->server2 ----------------
        udp_packet1 = mk_udp_pkt(hwsrc = server1_mac,
                                 hwdst = router_mac_addrs[PORT2SERVER1],
                                 ipsrc = server1_ip,
                                 ipdst = server2_ip,
                                 ttl = 32)
        s.expect(PacketInputEvent(router_nic_names[PORT2SERVER1], udp_packet1, display=Ethernet), 
                                  "TC 2.1. udp pkt to fwd server1 -> router")
        udp_packet2 = mk_udp_pkt(hwsrc = router_mac_addrs[PORT2SERVER2],
                                 hwdst = server2_mac,
                                 ipsrc = server1_ip, # shouldn't change
                                 ipdst = server2_ip, # shouldn't change
                                 ttl = 31) # decrement by 1
        s.expect(PacketOutputEvent(router_nic_names[PORT2SERVER2], udp_packet2, display=Ethernet), 
                                   "TC 2.1. udp pkt to fwd router -> server2")
        # TC 2.2: server2->client ----------------
        udp_packet1 = mk_udp_pkt(hwsrc = server2_mac,
                                 hwdst = router_mac_addrs[PORT2SERVER2],
                                 ipsrc = server2_ip,
                                 ipdst = client_ip,
                                 ttl = 32)
        s.expect(PacketInputEvent(router_nic_names[PORT2SERVER2], udp_packet1, display=Ethernet), 
                                  "TC 2.2. udp pkt to fwd server2 -> router")
        udp_packet2 = mk_udp_pkt(hwsrc = router_mac_addrs[PORT2CLIENT],
                                 hwdst = client_mac,
                                 ipsrc = server2_ip, # shouldn't change
                                 ipdst = client_ip, # shouldn't change
                                 ttl = 31) # decrement by 1
        s.expect(PacketOutputEvent(router_nic_names[PORT2CLIENT], udp_packet2, display=Ethernet), 
                                   "TC 2.2. udp pkt to fwd router -> client")
        # TC 2.3: client -> server1 ----------------
        udp_packet1 = mk_udp_pkt(hwsrc = client_mac,
                                 hwdst = router_mac_addrs[PORT2CLIENT],
                                 ipsrc = client_ip,
                                 ipdst = server1_ip,
                                 ttl = 32)
        s.expect(PacketInputEvent(router_nic_names[PORT2CLIENT], udp_packet1, display=Ethernet), 
                                  "TC 2.3. udp pkt to fwd client -> router")
        udp_packet2 = mk_udp_pkt(hwsrc = router_mac_addrs[PORT2SERVER1],
                                 hwdst = server1_mac,
                                 ipsrc = client_ip, # shouldn't change
                                 ipdst = server1_ip, # shouldn't change
                                 ttl = 31) # decrement by 1
        s.expect(PacketOutputEvent(router_nic_names[PORT2SERVER1], udp_packet2, display=Ethernet), 
                                   "TC 2.3. udp pkt to fwd router -> server1")

    Enable_ICMP = True
    if Enable_ICMP:
        # TC 3.1 : forwarding icmp req ---------------------------------------------------------
        # icmp request not for me (server 1 => client)
        icmp_req = mk_icmp_pkt(hwsrc=server1_mac,
                               hwdst=router_mac_addrs[PORT2SERVER1],
                               ipsrc=server1_ip,
                               ipdst=client_ip,
                               request=True,
                               ttl=32)
        s.expect(PacketInputEvent(router_nic_names[PORT2SERVER1], icmp_req, display=Ethernet), 
                                  "TC 3.1a. icmp pkt to fwd svr1 -> client")
        icmp_req = mk_icmp_pkt(hwsrc=router_mac_addrs[PORT2CLIENT],
                               hwdst=client_mac,
                               ipsrc=server1_ip,
                               ipdst=client_ip,
                               request=True,
                               ttl=31) # forwarded packet should decrease TTL by 1
        s.expect(PacketOutputEvent(router_nic_names[PORT2CLIENT], icmp_req, display=Ethernet), 
                                   "TC 3.1b. icmp pkt to fwd router -> client")
        # TC 3.2 : responding icmp req --------------------------------------------------------
        icmp_req = mk_icmp_pkt(hwsrc=server2_mac,
                               hwdst=router_mac_addrs[PORT2SERVER2],
                               ipsrc=server2_ip,
                               ipdst=router_ip_addrs[PORT2SERVER2],
                               request=True,
                               ttl=32)
        s.expect(PacketInputEvent(router_nic_names[PORT2SERVER2], icmp_req, display=Ethernet), 
                                  "TC 3.2a. icmp pkt for me")
        icmp_reply = mk_icmp_pkt(hwsrc=router_mac_addrs[PORT2SERVER2],
                               hwdst=server2_mac,
                               ipsrc=router_ip_addrs[PORT2SERVER2],
                               ipdst=server2_ip,
                               request=False,
                               ttl=32) # this is a newly created ICMP reply, so no decrease of TTL
        s.expect(PacketOutputEvent(router_nic_names[PORT2SERVER2], icmp_reply, display=Ethernet), 
                                   "TC 3.2b. icmp reply by the router")

    return s

scenario = my_tests()

