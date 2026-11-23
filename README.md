# Computer Network Labs

A collection of university networking labs using Mininet, Open vSwitch, and
Switchyard. I ran the experiments, checked the results, and documented how the
network behavior matched the implementation. Each write-up describes the
course-provided materials and my contributions.

| Lab | What it demonstrates |
| --- | --- |
| [Mininet and OpenFlow Routing](mininet-openflow-routing/) | Custom topologies, link-delay measurements, and manual OpenFlow rules that let one host pair communicate over the shortest path. |
| [Layer 2 Learning Switch](switchyard-learning-switch/) | MAC address learning and a comparison of timeout, LRU, and traffic-volume eviction policies. |
| [ARP Request Handling and Caching](arp-request-handling-local-reply-and-caching/) | Local ARP replies and IP-to-MAC caching, with packet-level test scenarios. |
| [Layer 2 Flooding Hub](switchyard-hub/) | Flooding frames across ports and verifying the behavior with Switchyard and Mininet. |

**Start with [Mininet and OpenFlow Routing](mininet-openflow-routing/).** With
four manual flow rules installed, the selected host pair communicated in both
directions. The other ten directed host pairs failed as expected.