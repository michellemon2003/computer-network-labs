import time
from switchyard.lib.userlib import *

def main(net):
    my_interfaces = net.interfaces() 
    mymacs = [intf.ethaddr for intf in my_interfaces]
    forwarding_table = {}

    while True:
        try:
            timestamp,input_port,packet = net.recv_packet()
        except NoPackets:
            continue
        except Shutdown:
            return

        now = time.time()
        for mac in list(forwarding_table.keys()):
            if now - forwarding_table[mac][1] >= 10:
                del forwarding_table[mac]

        log_info("In {} received packet {} on {}".format(net.name, packet, input_port))
        forwarding_table[packet[0].src] = [input_port, now]

        if packet[0].dst in mymacs:
            log_info("Packet intended for me")
        elif packet[0].dst in forwarding_table:
            out_port = forwarding_table[packet[0].dst][0]
            log_info("Forwarding packet {} to {}".format(packet, out_port))
            net.send_packet(out_port, packet)
        else:
            for intf in my_interfaces:
                if input_port != intf.name:
                    log_info("Flooding packet {} to {}".format(packet, intf.name))
                    # the received packet will be sent out to all the rest ports
                    # except the port to which this packet is arrived
                    net.send_packet(intf.name, packet)
    net.shutdown()
