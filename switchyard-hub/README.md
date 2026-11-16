# Test-Driven Layer-2 Ethernet Hub (Switchyard + Mininet)

> Coursework lab (Computer Networks). This was an introductory lab: the course supplied a working flooding hub, a test suite and a Mininet launcher. The assigned tasks were implemented using course materials and AI assistance. I ran the experiments and verified the results, and documented the implementation with AI assistance to support my understanding.

Environment: Ubuntu Linux virtual machine running via Oracle VirtualBox, utilizing Mininet and Open vSwitch.

## Summary

A hub is the simplest L2 device: whatever arrives on one port is copied to every other port. This lab introduces the workflow used in the later labs (a learning switch, and in general a network function developed with tests first):

1. Run the device logic in Python with **Switchyard**.
2. Verify its behavior against the provided packet-level test scenarios (`swyard -t`).
3. Run the same module on a node in a **Mininet** network and watch ARP/ICMP traffic passing through it.

- myhub.py, hubtests.py and start_mininet.py were provided by the professor.
- start_mininet.py was modified by removing `server2`and myhub.py was modified by adding forwarded-packet counter and log line.

## Repository layout

```text
switchyard-hub/
├── myhub.py #hub
├── hubtests.py #provided test scenario
├── start_mininet.py #launcher
└── README.md
```

## How the hub works

For every received frame:

1. Read the Ethernet header.
2. If the destination MAC equals one of the hub's own interface MACs, log it and do nothing (the hub does not act as a host).
3. Otherwise send a copy out of **every interface except the one the frame arrived on**, then increment `counter` and log `Forwarded N packets (except the ones for me)`.

Note on the counter: it counts *received frames that were forwarded*, not copies sent. With two interfaces these are the same; with three, one frame produces two copies but increments the counter once. It is an ordinary integer in a single-threaded loop.

## Testing

```bash
swyard -t hubtests.py myhub.py
```
When this suite is run against `myhub.py`, **all 8 scripted steps pass**. The scenario covers three cases:

1. A broadcast frame arriving on `eth1` is flooded out `eth0` and `eth2`.
2. A unicast frame to an unknown MAC (and its reply) is flooded to all other ports. This is hub behaviour; a learning switch would not do this.
3. A frame addressed to the hub's own MAC produces no output (checked with `PacketInputTimeoutEvent`, which asserts that nothing happens for 1s).

The tests require neither root privileges nor active network interfaces, making it possible to verify the forwarding logic quickly.

### Running it in Mininet

```bash
sudo python3 start_mininet.py # client, server1 and hub
mininet> xterm hub
# in the hub's terminal:
swyard myhub.py
mininet> pingall
```

### Results

- In the starter topology with server2, the hub had 3 NICs and the pingall reported 50% dropped (6/12). All communication between the client, server1, and server2 worked.
- In the final topology, after removing server2, the hub had 2 NICs, and pingall reported 66% dropped (2/6). Only communication between the client and server1 worked.

Pings to or from `hub` fail by design: the hub has no IP address and discards frames addressed to its MACs.

## Why more than 4 packets are forwarded

A ping between two hosts involves 4 ICMP frames (2 requests, 2 replies), so I expected `counter == 4`. However, the final counter value in the captured run was 8.

* The first exchange needs ARP: a broadcast request and a unicast reply. That alone brings the minimum to 6.
* The hub log also shows a **second ARP request/reply pair about five seconds after the ICMP traffic**. I did not investigate further; this is consistent with the Linux neighbor cache re-validating the entry, but I only observed the packets, not the kernel's reason.
* IPv6 is disabled in `start_mininet.py`, so IPv6 neighbour discovery is not the source of extra frames.

4 ICMP + 2 ARP + 2 ARP re-check = 8, and the count varies run to run depending on timing.

## Takeaways
* Packet-level assertions (`PacketInputEvent` / `PacketOutputEvent`) let you verify forwarding logic without a network.
* ARP precedes the first IP packet on an Ethernet LAN, and the hub forwards it like any frame, which makes the control traffic visible in the counter.
* A hub wastes bandwidth and shows every frame to every host, which is the motivation for the learning switch in the next lab.