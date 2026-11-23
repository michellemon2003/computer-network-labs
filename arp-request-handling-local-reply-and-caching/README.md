# ARP Request Handling in a Software Router: Local Replies and an IP/MAC Cache (Switchyard)

> Coursework project (Computer Networks), first step toward a software IPv4 router. The course supplied the router skeleton, the Mininet topology and the test suites; the ARP logic and the analysis are implemented. The assigned tasks were implemented using course materials and AI assistance. I ran the experiments and verified the results, and documented the implementation with AI assistance to support my understanding.

## Summary

Before a router can forward an IP packet it must know the MAC address of the next hop, and other hosts must be able to learn the router's MAC. Both are done with ARP. In this lab I:

1. **Observed** real ARP request/reply packets in Wireshark and identified which header fields matter for an implementation.
2. **Implemented** the router side of ARP: answer a request when it asks about one of the router's own IP addresses (`2-Local-reply`).
3. **Extended** it with a lookup table that remembers the sender of every ARP request and answers later requests about those hosts too (`3-Cached-ARP`).
4. **Validated** (2) both with scripted Switchyard tests and live in Mininet against a real Linux client.

The router does not yet forward IP packets or answer ICMP, so `pingall` is not expected to work. That is by design for this stage.

## Repository layout

```text
arp-router/
├── myrouter.py                                   # provided skeleton
├── 1-ARP-monitoring/
│   └── start_mininet.py                          # provided topology (+ my Wireshark screenshots)
├── 2-Local-reply/
│   ├── myrouter_handle_arp_req_local.py          # answers requests for the router's own IPs
│   ├── router_tests_handle_arp_req_local.py      # provided tests (8 steps)
│   └── start_mininet.py
├── 3-Cached-ARP/
│   ├── myrouter_handle_arp_req_cache.py          # + learns senders, answers for them too
│   └── router_tests_handle_arp_req_cache.py      # provided tests (14 steps)
└── README.md
```

## Test network

```text
  server1 192.168.100.1 --- router-eth0 192.168.100.2   (MAC 40:00:00:00:00:01)
  server2 192.168.200.1 --- router-eth1 192.168.200.2   (MAC 40:00:00:00:00:02)
  client  10.1.1.1      --- router-eth2 10.1.1.2        (MAC 40:00:00:00:00:03)
```

The client reaches the 192.168.x.x networks through the router at `10.1.1.2`, so its first packet to a server triggers an ARP request for `10.1.1.2`. Host MACs are `10:..`, `20:..`, `30:..` for server1, server2 and client.

## 1. What an ARP exchange looks like (Wireshark)

Captured on the router with interface `any` and display filter `arp`, while the client pinged a server:

| Field | Request | Reply |
| :--- | :--- | :--- |
| Opcode | 1 (request) | 2 (reply) |
| Sender MAC / IP | `30:00:00:00:00:01` / `10.1.1.1` | `40:00:00:00:00:03` / `10.1.1.2` |
| Target MAC / IP | `00:00:00:00:00:00` / `10.1.1.2` | `30:00:00:00:00:01` / `10.1.1.1` |

Points that shaped the implementation:

* The **opcode**, not the target MAC, identifies a request. The target MAC in a request is all zeros here but may be anything, so the code must not rely on it.
* The reply swaps roles: its sender is the address that was asked about, and its target is the original sender.
* Whoever answers must put *its own* MAC in the sender field. That is exactly what `create_ip_arp_reply(srchw, srcip, dsthw, targetip)` takes.

In this first experiment no router program was running, so the reply presumably came from the router's Linux kernel. Later, the reply from my Python code (below) has identical field values, which is a useful end-to-end check.

## 2. Local reply (`myrouter_handle_arp_req_local.py`)

Setup: build `my_ip_to_mac = {ip: interface MAC}` for every interface of the router.

Per packet:

1. `arp = pkt.get_header(Arp)`; if there is no ARP header, or `arp.operation` is not `Request`, ignore.
2. Look up `arp.targetprotoaddr` in the table; if it is not one of the router's addresses, ignore.
3. Send `create_ip_arp_reply(srchw=mac_found, srcip=arp.targetprotoaddr, dsthw=arp.senderhwaddr, targetip=arp.senderprotoaddr)` back out the interface the request arrived on.

Notes:

* The MAC in the reply is the one that belongs to the *asked-about IP's interface*, as the assignment specifies; the reply goes out on the *ingress* interface.
* Table setup normalises each interface address to a plain IP, so the lookup works whichever form the interface address takes.

### Verification

* **Switchyard suite:** `swyard -t router_tests_handle_arp_req_local.py myrouter_handle_arp_req_local.py` -> **8 of 8 steps pass** (unknown IP gets no reply; requests for the eth0, eth1 and eth2 addresses each get a correct reply).
* **Mininet:** router runs `swyard ./myrouter_handle_arp_req_local.py`; client runs `ping -c3 10.1.1.2` with Wireshark on `client-eth0`. Captured 5 packets as the assignment predicts:
  1. ARP request, broadcast from `30:00:00:00:00:01`;
  2. ARP reply from `40:00:00:00:00:03` (about 61 ms later);
  3. three ICMP echo requests, about one second apart, with **no replies**, because the router has no ICMP logic.

## 3. Caching (`myrouter_handle_arp_req_cache.py`)

Changes relative to part 2:

* The table (`arp_table`) is initialised with the router's own `IP -> MAC` pairs, as before.
* On **every ARP request** the sender's pair `senderprotoaddr -> senderhwaddr` is stored *before* answering.
* Replies are generated from the same table, so the router now also answers requests about any host it has previously heard from, not only about itself.
* Non-ARP packets and ARP replies are ignored; the assignment's 1:1 IP/MAC assumption is taken as given.

### Verification

* **Switchyard suite:** `swyard -t router_tests_handle_arp_req_cache.py myrouter_handle_arp_req_cache.py` -> **14 of 14 steps pass**, including three cases where one host asks about another host that was learned from an earlier request.
* **Cross-checks I ran:**
  * the cache implementation also passes the *local* suite (it is a superset);
  * the local implementation **fails** the cache suite, so the new tests do exercise the new behaviour.
* As the assignment states, this part is not tested in Mininet.

## Limitations and observations

These come from reading the code; I did not test them.

* **No validation or aging.** The cache is overwritten by any request, including one that claims the router's own IP as sender. A forged request could therefore change what the router answers for its own address. A real implementation would protect its own entries and age learned ones.
* **The router answers for other hosts** (it is proxying learned mappings). That is what this assignment asks for; in practice a router answering on behalf of hosts is a deliberate feature (proxy ARP) with its own risks.
* **Learns only from requests,** not from ARP replies, per the specification.
* **Unbounded table**, no timeout. (Lab 5's eviction policies would apply here.)
* The router does not respond to ICMP or forward packets yet, which is why the Mininet pings show requests but no replies.

## What this project demonstrates

* Reading a protocol from packet captures and turning the field semantics into code.
* Implementing protocol logic against a test-first framework and checking what the tests do and do not distinguish.
* Validating the same logic in two environments: scripted packets and a live Mininet network with a real Linux client.

## Reproduce

```bash
# scripted tests (no root needed)
swyard -t 2-Local-reply/router_tests_handle_arp_req_local.py 2-Local-reply/myrouter_handle_arp_req_local.py
swyard -t 3-Cached-ARP/router_tests_handle_arp_req_cache.py  3-Cached-ARP/myrouter_handle_arp_req_cache.py

# live check of the local-reply router
cd 2-Local-reply && sudo python3 start_mininet.py
mininet> xterm client          # client# wireshark -k &
mininet> xterm router          # router# swyard ./myrouter_handle_arp_req_local.py
mininet> client ping -c3 10.1.1.2
```
