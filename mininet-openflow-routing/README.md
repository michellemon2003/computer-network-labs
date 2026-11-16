# Mininet Topologies, Link-Delay Emulation & Controller-less OpenFlow Routing


> Coursework labs (Computer Networks). The lab requirements and instructions were provided by the professor. The assigned tasks were implemented using course materials and AI assistance. I ran the experiments and verified the results, and documented the implementation with AI assistance to support my understanding.

Environment: Ubuntu Linux virtual machine running via Oracle VirtualBox, utilizing Mininet and Open vSwitch.

## Summary

SDN separates the control plane (who decides where packets go) from the data plane (the switch that forwards them). This lab works at the data-plane level:

1. Built custom topologies in Python with Mininet's 'Topo' API.
2. Measured how per-link delay shows up in end-to-end RTT, including ARP's effect on the first packets.
3. Started a network with **no controller** (`controller=none`) and hand-wrote the minimum OpenFlow rules on Open vSwitch to allow exactly one host pair to communicate over the shortest path, and nothing else.

## Repository layout

```text
mininet-openflow-routing/
├── dumbell.py # 2 switches, 4 hosts (dumbbell)
├── rect.py # 5 switches, 4 hosts (rectangle with a central switch)
└── README.md
```

## 1. Custom topologies
The built-in `single,4`, `linear,4` and `tree,2,2` topologies (Graphviz) are generated and visualised to understand how Mininet numbers ports. Then, two custom ones are written.

**Dumbbell (`dumbell.py`)** - `h1,h2 = s1-s2-h3,h4`.
`pingall` result: `0% dropped (12/12 received)`.

**Rectangle (`rect.py`)** = 5 switches, 4 hosts, with redundant paths: s5 is linked to s1, s2, s3 and s4
* Outer ring: `s1-s4`, `s4-s3`, `s3-s2`, `s2-s1`.
* Central switch `s5` linked to all four ring switches.
* Hosts: `h1-s1`, `h4-s4`, `h2-s2`, `h3-s3`

Design point: several paths exist between most host pairs, so "the shortest path" is a real choice rather than the only option.

## 2. Link delay and RTT (`tc`)

Command: `sudo mn --link tc,delay=100ms`, then `h1 ping h2 -c 10`, compared with the default network (`h1-s1-h2`).

| Configuration | min | avg | max | mdev |
| :--- | ---: | ---: | ---: | ---: |
| Default links | 0.119 ms | **0.575 ms** | 4.282 ms | 1.237 ms |
| `delay=100ms` per link | 401.377 ms | **443.339 ms** | 808.843 ms| 121.839 ms |

What the numbers show:

* **Steady state matches the model.** A ping crosses 4 links (h1 -> s1 -> h2 and back), each adding 100 ms, so the floor is 400 ms. The measured minimum is 401.4 ms.
* **First packet is likely affected by ARP resolution.** With delay enabled, ARP resolution can add approximately 400 ms before the ICMP exchange, which is consistent with the maximum RTT of 808.8 ms. However, I did not capture ARP packets separately to verify this explanation.
* **Without delay** the maximum (4.3 ms) is about 35x the minimum; the same cold-start effect is visible, but here it is dominated by one-time setup costs, not by a clean 2x.

## 3. Controller-less shortest-path routing (`ovs-ofctl`)

Goal: allow 'h1 <-> h4` only, with the fewest possible rules.

With `--controller=none` the switches have empty flow tables and drop everything. The shortest `h1 -> h4` path is `h1-s1-s4-h4` via the direct `s1-s4` link (2 switches). Alternatives such as `s1-s5-s4` (3 switches) or `s1-s2-s3-s4` (4 switches) are longer.

Port numbers (from the order of `addLink` calls in `rect.py`):

| Switch | port 1 | port 2 |
| :--- | :--- | :--- |
| `s1` | `h1` | `s4` |
| `s4` | `h4` | `s1` |

Four rules are enough:

```bash
sh ovs-ofctl add-flow s1 priority=500,in_port=1,actions=output:2
sh ovs-ofctl add-flow s1 priority=500,in_port=2,actions=output:1
sh ovs-ofctl add-flow s4 priority=500,in_port=1,actions=output:2
sh ovs-ofctl add-flow s4 priority=500,in_port=2,actions=output:1
```

The rules match only in ingress port, so ARP(broadcast) and ICMP both follow the same path without separate rules. Each direction needs one rule per switch.

### Verification

* `dump-flows s1` and `s4`: two rules each, each showing `n_packets=10, n_bytes=532`.
* `dump-flows s2`, `s3`, `s5`: empty, confirming that no forwarding rules were installed on the switches outside the selected path.
* `pingall`: `h1 -> h4` and `h4 -> h1` succeed; the other 10 directed pairs fail: `83% dropped (2/12 received)`.

## Limitations and observations

* The rules are **port-based**, not address-based. They are correct for this fixed wiring, but they would forward anything that arrives on those ports; real isolation would also match on MAC/IP.
* A rule that simply flooded on this topology would loop, because the topology contains cycles. Using explicit single path rules sidesteps this (my reasoning from the topology: I did not test a flooding setup).
* Everything here is static. A controller would install, update and remove such rules automatically in response to events.