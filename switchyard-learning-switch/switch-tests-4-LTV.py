#!/usr/bin/env python3

from switchyard.lib.userlib import *
import time

def mk_pkt(hwsrc, hwdst, ipsrc, ipdst, reply=False):
    ether = Ethernet(src=hwsrc, dst=hwdst, ethertype=EtherType.IP)
    ippkt = IPv4(src=ipsrc, dst=ipdst, protocol=IPProtocol.ICMP, ttl=32)
    icmppkt = ICMP()
    if reply:
        icmppkt.icmptype = ICMPType.EchoReply
    else:
        icmppkt.icmptype = ICMPType.EchoRequest
    return ether + ippkt + icmppkt

def my_tests():
    s = TestScenario("My_Switch_LRU tests")
    s.add_interface('eth0', '10:00:00:00:00:00') # (assume) connected to a host0 (30:00:...:00)
    s.add_interface('eth1', '10:00:00:00:00:01') # (assume) connected to a host1 (30:00:...:01)
    s.add_interface('eth2', '10:00:00:00:00:02') # (assume) connected to a host2 (30:00:...:02)
    # IP addr is not important now (when dealing with Ethernet switch)
    # So, we'll set the IP address to 0.0.0.0 in any cases

    # a frame sent to switch that will not be forwarded (host0 -> switch)
    # now, an entry is installed 
    # -------------------------------------------
    # <Table entries>
    # switch -> host0 (0) // (?) indicates the num of forwarded pkts
    # switch -> host1 (0)
    # -------------------------------------------
    testpkt = mk_pkt("30:00:00:00:00:00", "10:00:00:00:00:00", "0.0.0.0", "0.0.0.0")
    s.expect(PacketInputEvent("eth0", testpkt, display=Ethernet), "TC 1 PKT to switch received (do nothing)")
    testpkt = mk_pkt("30:00:00:00:00:01", "10:00:00:00:00:01", "0.0.0.0", "0.0.0.0")
    s.expect(PacketInputEvent("eth1", testpkt, display=Ethernet), "TC 2 PKT to switch received (do nothing)")
    

    # a unicast request (host1 -> host0)
    # already installed the rule, so the req will be forwarded to host0 correctly
    # -------------------------------------------
    # <Table entries>
    # switch -> host0 (2)
    # switch -> host1 (1)
    # -------------------------------------------
    testpkt = mk_pkt("30:00:00:00:00:01", "30:00:00:00:00:00", "0.0.0.0", "0.0.0.0")
    s.expect(PacketInputEvent("eth1", testpkt, display=Ethernet), "TC 3a (UNICAST) host1 to host0 recvd)")
    s.expect(PacketOutputEvent("eth0", testpkt, display=Ethernet), "TC 3b Unicast to eth0")
    s.expect(PacketInputEvent("eth1", testpkt, display=Ethernet), "TC 4a (UNICAST) host1 to host0 recvd)")
    s.expect(PacketOutputEvent("eth0", testpkt, display=Ethernet), "TC 4b Unicast to eth0")
    testpkt = mk_pkt("30:00:00:00:00:00", "30:00:00:00:00:01", "0.0.0.0", "0.0.0.0")
    s.expect(PacketInputEvent("eth0", testpkt, display=Ethernet), "TC 5a (UNICAST) host0 to host1 recvd)")
    s.expect(PacketOutputEvent("eth1", testpkt, display=Ethernet), "TC 5b Unicast to eth1")

    # a frame sent to switch that will not be forwarded (host2 -> switch)
    # now, an entry is installed 
    # -------------------------------------------
    # <Table entries>
    # switch -> host0 (2)
    # (removed) switch -> host1 (1)
    # switch -> host2 (0)
    # -------------------------------------------
    testpkt = mk_pkt("30:00:00:00:00:02", "10:00:00:00:00:02", "0.0.0.0", "0.0.0.0")
    s.expect(PacketInputEvent("eth2", testpkt, display=Ethernet), "TC 6 PKT to switch received (do nothing)")
    testpkt = mk_pkt("30:00:00:00:00:00", "30:00:00:00:00:02", "0.0.0.0", "0.0.0.0")
    s.expect(PacketInputEvent("eth0", testpkt, display=Ethernet), "TC 7a (UNICAST) host0 to host2 recvd)")
    s.expect(PacketOutputEvent("eth2", testpkt, display=Ethernet), "TC 7b Unicast to eth2")    
    testpkt = mk_pkt("30:00:00:00:00:02", "30:00:00:00:00:00", "0.0.0.0", "0.0.0.0")
    s.expect(PacketInputEvent("eth2", testpkt, display=Ethernet), "TC 8a (UNICAST) host2 to host0 recvd)")
    s.expect(PacketOutputEvent("eth0", testpkt, display=Ethernet), "TC 8b Unicast to eth0")    
    # pkt destined to host1 will cause flooding
    testpkt = mk_pkt("30:00:00:00:00:00", "30:00:00:00:00:01", "0.0.0.0", "0.0.0.0")
    s.expect(PacketInputEvent("eth0", testpkt, display=Ethernet), "TC 9a (UNICAST) host0 to host1 recvd)")
    s.expect(PacketOutputEvent("eth1", testpkt, "eth2", testpkt, display=Ethernet), "TC 9b Causing flooding")    

    return s


scenario = my_tests()
