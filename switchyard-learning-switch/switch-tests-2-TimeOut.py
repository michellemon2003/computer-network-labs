#!/usr/bin/env python3

from switchyard.lib.userlib import *
import time

TIMEOUT_SECONDS = 10 # supposed to be 10
invalid_ip_addr = "0.0.0.0"
bc_mac_addr = "ff:ff:ff:ff:ff:ff"  # broadcast mac address

def mk_pkt(hwsrc, hwdst, ipsrc=bc_mac_addr, ipdst=bc_mac_addr, reply=False):
    ether = Ethernet(src=hwsrc, dst=hwdst, ethertype=EtherType.IP)
    ippkt = IPv4(src=ipsrc, dst=ipdst, protocol=IPProtocol.ICMP, ttl=32)
    icmppkt = ICMP()
    if reply:
        icmppkt.icmptype = ICMPType.EchoReply
    else: #  by default (reply=False), we'll generate ICMP EchoRequest
        icmppkt.icmptype = ICMPType.EchoRequest
    return ether + ippkt + icmppkt

def my_tests():
    s = TestScenario("My_Switch_TimeOut tests")
    # port name, port mac, mac of the host connected to the port
    eth0_name, eth0_mac, eth0_host_mac = 'eth0', '10:00:00:00:00:00', '30:00:00:00:00:00'
    eth1_name, eth1_mac, eth1_host_mac = 'eth1', '10:00:00:00:00:01', '30:00:00:00:00:01'
    eth2_name, eth2_mac, eth2_host_mac = 'eth2', '10:00:00:00:00:02', '30:00:00:00:00:02'
    s.add_interface(eth0_name, eth0_mac) # (assume) connected to a host (30:00:...:00)
    s.add_interface(eth1_name, eth1_mac) # (assume) connected to a host (30:00:...:01)
    s.add_interface(eth2_name, eth2_mac) # (assume) connected to a host (30:00:...:02)
    # IP addr is not important now (when dealing with Ethernet switch)
    # So, we'll set the IP address to 0.0.0.0 in any cases

    # test case 1: 
    # Sending unicast packet from eth0_host_mac to eth1_host_mac
    # Since the switch has no cached entry, it will be broadcasted
    # also, the packet will not be replied at the destination for the invalid ip addr
    # Now, switch knows mac-port info about the host connected to the eth0 from the input packet
    testpkt = mk_pkt(eth0_host_mac, eth1_host_mac, invalid_ip_addr, invalid_ip_addr)
    s.expect(PacketInputEvent(eth0_name, testpkt, display=Ethernet), "TC 1.1a a pkt received")
    s.expect(PacketOutputEvent(eth1_name, testpkt, eth2_name, testpkt, display=Ethernet), "TC 1.1b the pkt will be flooded")

    # Sending unicast packet from eth1_host_mac to eth2_host_mac
    # Since the switch has no cached entry, it will be broadcasted
    # also, the packet will not be replied at the destination for the invalid ip addr
    # Now, switch knows mac-port info about the host connected to the eth1 from the input packet
    testpkt = mk_pkt(eth1_host_mac, eth2_host_mac, invalid_ip_addr, invalid_ip_addr)
    s.expect(PacketInputEvent(eth1_name, testpkt, display=Ethernet), "TC 1.2a a pkt received")
    s.expect(PacketOutputEvent(eth0_name, testpkt, eth2_name, testpkt, display=Ethernet), "TC 1.2b the pkt will be flooded")

    # Sending unicast packet from eth2_host_mac to broadcast mac address
    # Since the switch has no cached entry, it will be broadcasted
    # also, the packet will not be replied at the destination for the invalid ip addr
    # Now, switch knows mac-port info about the host connected to the eth2 from the input packet
    testpkt = mk_pkt(eth2_host_mac, bc_mac_addr, invalid_ip_addr, invalid_ip_addr)
    s.expect(PacketInputEvent(eth2_name, testpkt, display=Ethernet), "TC 1.3a a BC pkt received")
    s.expect(PacketOutputEvent(eth0_name, testpkt, eth1_name, testpkt, display=Ethernet), "TC 1.3b the pkt will be flooded")

    # test case 2:
    # - now, all forwarding rules are installed, so unicast can be carried out without flooding
    testpkt = mk_pkt(eth0_host_mac, eth1_host_mac, invalid_ip_addr, invalid_ip_addr)
    s.expect(PacketInputEvent(eth0_name, testpkt, display=Ethernet),  "TC 2.1a Unicast msg received")
    s.expect(PacketOutputEvent(eth1_name, testpkt, display=Ethernet), "TC 2.1b Unicast msg forwarded")

    testpkt = mk_pkt(eth1_host_mac, eth2_host_mac, invalid_ip_addr, invalid_ip_addr)
    s.expect(PacketInputEvent(eth1_name, testpkt, display=Ethernet),  "TC 2.2a Unicast msg received")
    s.expect(PacketOutputEvent(eth2_name, testpkt, display=Ethernet), "TC 2.2b Unicast msg forwarded")

    testpkt = mk_pkt(eth2_host_mac, eth0_host_mac, invalid_ip_addr, invalid_ip_addr)
    s.expect(PacketInputEvent(eth2_name, testpkt, display=Ethernet),  "TC 2.3a Unicast msg received")
    s.expect(PacketOutputEvent(eth0_name, testpkt, display=Ethernet), "TC 2.3b Unicast msg forwarded")

    # test case 3:
    # - after 10 seconds, all rules are gone
    # - time.sleep(11) # this cannot simulate the 10-second delay situation
    # - instead, the following can simulate the 10-second delay situation
    #   (to be safe, let's wait for 11 seconds, not 10)
    testpkt = mk_pkt(bc_mac_addr, eth0_mac, invalid_ip_addr, invalid_ip_addr)
    s.expect(PacketInputEvent(eth0_name, testpkt, display=Ethernet), "3.1a Generate a fake pkt for timeout")
    #s.expect(PacketOutputEvent("eth1", testpkt, "eth2", testpkt, display=Ethernet), "7The Ethernet frame with a broadcast destination address should be forwarded out ports eth0 and eth2")
    s.expect(PacketInputTimeoutEvent(TIMEOUT_SECONDS+1.0), "3.1b Wait for 11 seconds to clear the forwarding table")

    # REPEATING test case 1 again:
    # Now, all entries are lost in the forwarding table
    # Thus, if we repeat test case 1, it will now be broadcasted

    # Sending unicast packet from eth0_host_mac to eth1_host_mac
    # Since the switch has no cached entry, it will be broadcasted
    # also, the packet will not be replied at the destination for the invalid ip addr
    # Now, switch knows mac-port info about the host connected to the eth0 from the input packet
    testpkt = mk_pkt(eth0_host_mac, eth1_host_mac, invalid_ip_addr, invalid_ip_addr)
    s.expect(PacketInputEvent(eth0_name, testpkt, display=Ethernet), "(repeat) TC 1.1a a pkt received")
    s.expect(PacketOutputEvent(eth1_name, testpkt, eth2_name, testpkt, display=Ethernet),
             "(repeat) TC 1.1b the pkt will be flooded")

    # Sending unicast packet from eth1_host_mac to eth2_host_mac
    # Since the switch has no cached entry, it will be broadcasted
    # also, the packet will not be replied at the destination for the invalid ip addr
    # Now, switch knows mac-port info about the host connected to the eth1 from the input packet
    testpkt = mk_pkt(eth1_host_mac, eth2_host_mac, invalid_ip_addr, invalid_ip_addr)
    s.expect(PacketInputEvent(eth1_name, testpkt, display=Ethernet), "(repeat) TC 1.2a a pkt received")
    s.expect(PacketOutputEvent(eth0_name, testpkt, eth2_name, testpkt, display=Ethernet),
             "(repeat) TC 1.2b the pkt will be flooded")

    # since the mac-port info about the host connected to eth0 is already learned, let's rerun TC 2.3a/b
    testpkt = mk_pkt(eth2_host_mac, eth0_host_mac, invalid_ip_addr, invalid_ip_addr)
    s.expect(PacketInputEvent(eth2_name, testpkt, display=Ethernet), "(repeat) TC 2.3a Unicast msg received")
    s.expect(PacketOutputEvent(eth0_name, testpkt, display=Ethernet), "(repeat) TC 2.3b Unicast msg forwarded")

    return s

scenario = my_tests()
