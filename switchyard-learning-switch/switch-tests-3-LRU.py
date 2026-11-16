#!/usr/bin/env python3

from switchyard.lib.userlib import *
import time

invalid_ip_addr = "0.0.0.0"
bc_mac_addr = "ff:ff:ff:ff:ff:ff"  # broadcast mac address
SMALL_TIME_INTERVAL = 1

def mk_pkt(hwsrc, hwdst, ipsrc=invalid_ip_addr, ipdst=invalid_ip_addr, reply=False):
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
    # port name, port mac, mac of the host connected to the port
    eth0_name, eth0_mac, eth0_host_mac = 'eth0', '10:00:00:00:00:00', '30:00:00:00:00:00'
    eth1_name, eth1_mac, eth1_host_mac = 'eth1', '10:00:00:00:00:01', '30:00:00:00:00:01'
    eth2_name, eth2_mac, eth2_host_mac = 'eth2', '10:00:00:00:00:02', '30:00:00:00:00:02'
    s.add_interface(eth0_name, eth0_mac)  # (assume) connected to a host (30:00:...:00)
    s.add_interface(eth1_name, eth1_mac)  # (assume) connected to a host (30:00:...:01)
    s.add_interface(eth2_name, eth2_mac)  # (assume) connected to a host (30:00:...:02)
    # IP addr is not important now (when dealing with Ethernet switch)
    # So, we'll set the IP address to 0.0.0.0 in any cases

    # a frame sent to switch that will not be forwarded (host0 -> switch)
    # now, an entry is installed 
    # -------------------------------------------
    # <Table entries>
    # t0: host0 (first installed)
    # -------------------------------------------
    # seding a packet to switch, and thus there is no output event expecting
    testpkt = mk_pkt(eth0_host_mac, eth0_mac, invalid_ip_addr, invalid_ip_addr)
    s.expect(PacketInputEvent(eth0_name, testpkt, display=Ethernet), "TC 1a PKT to switch received (do nothing)")
    s.expect(PacketInputTimeoutEvent(SMALL_TIME_INTERVAL), "TC 1b generating a second of time pass (to be safe)")

    # a unicast request (host1 -> host0)
    # already installed the rule, so the req will be forwarded to host0 correctly
    # also, we can learn another rule (t1: switch -> host1)
    # -------------------------------------------
    # <Table entries>
    # t1: host1 (first installed)
    # t2: host0 (first installed at t0, updated at t2)
    # -------------------------------------------
    testpkt = mk_pkt(eth1_host_mac, eth0_host_mac, invalid_ip_addr, invalid_ip_addr)
    s.expect(PacketInputEvent(eth1_name, testpkt, display=Ethernet), "TC 2a (UNICAST) host1 to host0 recvd)")
    # we already have info about host0, do unicast
    s.expect(PacketOutputEvent(eth0_name, testpkt, display=Ethernet), "TC 2b Unicast to eth0")
    s.expect(PacketInputTimeoutEvent(SMALL_TIME_INTERVAL), "TC 2c generating a second of time pass (to be safe)")

    # a unicast request (host0 -> host1)
    # already installed the rule, so the req will be forwarded to host1 correctly
    # there is nothing to learn from this unicast transmission
    # but, the access times will be updates
    # -------------------------------------------
    # <Table entries>
    # t3: host0 (first installed at t0, updated at t2, t3)
    # t4: host1 (first installed at t1, updated at t4)
    # -------------------------------------------
    testpkt = mk_pkt(eth0_host_mac, eth1_host_mac, invalid_ip_addr, invalid_ip_addr)
    s.expect(PacketInputEvent(eth0_name, testpkt, display=Ethernet), "TC 3a (UNICAST) host0 to host1 recvd)")
    s.expect(PacketOutputEvent(eth1_name, testpkt, display=Ethernet), "TC 3b Unicast to eth1")
    s.expect(PacketInputTimeoutEvent(SMALL_TIME_INTERVAL), "TC 3c generating a second of time pass (to be safe)")

    # a frame sent to switch that will not be forwarded (host2 -> switch)
    # now, an entry is installed (t2: switch -> host2), but no more space to save
    # thus, oldest rule will be removed
    # -------------------------------------------
    # <Table entries>
    # (removed) t3: host0 (first installed at t0, updated at t2, t3)
    # t4: host1 (first installed at t1, updated at t4)
    # t5: host2 (first installed at t5)
    # -------------------------------------------
    testpkt = mk_pkt(eth2_host_mac, eth2_mac, invalid_ip_addr, invalid_ip_addr)
    s.expect(PacketInputEvent(eth2_name, testpkt, display=Ethernet), "TC 4a PKT to switch received (do nothing)")
    # packet sent to switch does not generate any output
    s.expect(PacketInputTimeoutEvent(SMALL_TIME_INTERVAL), "TC 4b generating a second of time pass (to be safe)")

    # a unicast request (host1 -> host0)
    # now, switch does not know about host0, causing flooding
    testpkt = mk_pkt(eth1_host_mac, eth0_host_mac, invalid_ip_addr, invalid_ip_addr)
    s.expect(PacketInputEvent(eth1_name, testpkt, display=Ethernet), "TC 5a (UNICAST) host1 to host0 recvd)")
    s.expect(PacketOutputEvent(eth0_name, testpkt, eth2_name, testpkt, display=Ethernet), "TC 5b do flooding")

    return s

scenario = my_tests()
