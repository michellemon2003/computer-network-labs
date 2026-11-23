# Stateful L2 Learning Switch with Cache-Eviction Policies (Switchyard + Mininet)

> Coursework project (Computer Networks). For this lab, the test scenarios, the topology launcher and the flowcharts for each policy were supplied by the course. The assigned tasks were implemented using course materials and AI assistance. I ran the experiments and verified the results, and documented the implementation with AI assistance to support my understanding.

Environment: Ubuntu Linux virtual machine running via Oracle VirtualBox, utilizing Mininet and Open vSwitch.

## Summary

A learning switch builds a table mapping MAC addresses to ports, so it can forward unicast frames out one port instead of flooding. Real switches have limited table memory, so entries must be removed. I implemented four versions:

| Version | File | Policy |
| :--- | :--- | :--- |
| 1 | `myswitch-1-BasicSwitch.py` | learn only, never remove |
| 2 | `myswitch-2-TimeOut.py` | remove entries not updated for 10 s |
| 3 | `myswitch-3-LRU.py` | table holds at most 2 entries, evict least recently used |
| 4 | `myswitch-4-LTV.py` | table holds at most 2 entries, evict least traffic volume |

## Repository layout

```text
switchyard-learning-switch/
├── myswitch.py                               # starter (still a hub)
├── myswitch-1-BasicSwitch.py
├── myswitch-2-TimeOut.py
├── myswitch-3-LRU.py
├── myswitch-4-LTV.py
├── switch-tests-1-BasicSwitch-DoNotNeed.py   # placeholder: course says no tests for version 1
├── switch-tests-2-TimeOut.py                 # 20 test steps
├── switch-tests-3-LRU.py                     # 12 test steps
├── switch-tests-4-LTV.py                     # 15 test steps
├── start_mininet.py                          # client, hub, server1, server2
├── BasicSwitch.png, TimeOutPurging.jpg, LruPurging.jpg, LtvPurging.jpg   # course flowcharts
└── README.md
```

## Common forwarding pipeline

Every received frame goes through the same steps in all four versions:

1. **Purge** (TimeOut version only): delete entries older than the limit.
2. **Learn from the source MAC:** record or update `src -> input_port`. The LRU and LTV versions evict first if the table is full and `src` is new.
3. **Decide on the destination MAC:**
   * destination is one of the switch's own MACs: log and drop;
   * destination is in the table: forward out the learned port;
   * otherwise (unknown or broadcast): flood out every port except the ingress port.

Learning happens before the forwarding decision, so the first reply in a conversation can already be switched, not flooded.

## The policies

### 1. Basic switch
Unbounded dictionary `mac -> port`. Fixes the hub's problem of flooding everything, but the table never shrinks and never forgets a host that moved away or disconnected (a moved host is updated the next time it sends).

### 2. TimeOut (10 s)
Entries are `[port, last_updated]`.

* At the start of each packet, delete every entry with `now - last_updated >= 10`.
* A packet from a known source overwrites the port and resets its timer.
* Only the **source** side refreshes an entry; being used as a destination does not.

Implementation note: purging is lazy (it runs when a packet arrives) and uses `time.time()`.

### 3. LRU, capacity 2
Entries are `[port, last_access_time]`.

* New source and table full: evict `min(table, key=last_access_time)`, then insert.
* Known source: update the port if it changed **and refresh its access time**.
* Destination hit: refresh the destination entry's access time, then forward.

> **Spec ambiguity.** The assignment's prose says the sender's entry gets its access time updated on every packet, and that is what my code does. The supplied flowchart instead shows a known source with an unchanged port doing nothing, and a changed port updating the port "without modifying LRU order". The two descriptions differ for known sources. I followed the prose. I checked that a variant following the flowchart also passes all 12 provided tests, so the tests do not distinguish them.

### 4. LTV (least traffic volume), capacity 2
Entries are `[port, packet_count]`.

* New entries start at `0`.
* The count increases by 1 **only** when the entry is the destination of a forwarded packet (a table hit). Learning or refreshing a source never changes it, and a port change leaves it untouched.
* On a full table, a new source evicts the entry with the smallest count (on a tie, the one inserted first; the assignment allows any).

## Comparison

| Policy | Tracked per entry | Evicts | Strength | Weakness |
| :--- | :--- | :--- | :--- | :--- |
| TimeOut | last-update time | entries idle >= 10 s | stale hosts disappear on their own | no size bound; table can grow during bursts |
| LRU | last-access time | oldest access | follows shifting activity | many one-off hosts can flush useful entries |
| LTV | forwarded-packet count | lowest count | keeps hosts that receive a lot of traffic | a heavy but now idle host is never aged out |

Observations from reading my own code, not separate experiments:

* In LTV a freshly learned entry has count 0, so with a full table it is the most likely victim of the *next* new source. Under a stream of new hosts the table can churn on its newest entry.
* The victim is chosen before the new source is inserted, so a table that evicts the destination of the current packet will flood it instead of switching it.

## Verification

### Switchyard scenarios
```bash
swyard -t switch-tests-2-TimeOut.py myswitch-2-TimeOut.py   # 20 steps
swyard -t switch-tests-3-LRU.py     myswitch-3-LRU.py       # 12 steps
swyard -t switch-tests-4-LTV.py     myswitch-4-LTV.py       # 15 steps
```
I re-ran all three: **all pass (47 steps in total)**. The TimeOut suite uses `PacketInputTimeoutEvent(11)`, which waits 11 seconds of real time, so it takes about 12 s.

### Mininet
Topology: `client`, `server1`, `server2` linked to `hub` (the switch node). `pingall` before and after starting the switch in the `hub` node's `xterm`:

| Version | Before | After |
| :--- | :--- | :--- |
| Basic | `0/12` (100% dropped) | `6/12` (50% dropped) |
| TimeOut | `0/12` | `6/12` |
| LRU | `0/12` | `6/12` |
| LTV | `0/12` | `6/12` |

All traffic among `client`, `server1` and `server2` works (6 directed pairs). The other 6 attempts involve the `hub` node itself, which has no IP and drops frames addressed to it, so they fail by design.

## Known limitations

* Capacity is hard-coded as `2` in the LRU and LTV files (the assignment overview mentions 5, the problem text says 2).
* If a frame's destination is learned on the same port it arrived on, my code sends it back out that port; a real switch would filter it.
* No VLANs, no spanning tree, no multicast handling, no thread safety (single receive loop).
* TimeOut has no background timer, so stale entries live until the next packet arrives. Real switches age entries for minutes, not seconds.

## What this project demonstrates

* Implementing stateful network logic and translating a flowchart into code, and noticing where the specification is ambiguous.
* Test-driven development with scripted packet scenarios, plus checking what the tests do *not* cover.
* Reasoning about cache-eviction trade-offs (recency vs frequency vs age) in a networking setting.

## Reproduce

```bash
sudo python3 start_mininet.py
mininet> xterm hub
# in the hub terminal:
swyard myswitch-4-LTV.py      # or any other version
mininet> pingall
```
