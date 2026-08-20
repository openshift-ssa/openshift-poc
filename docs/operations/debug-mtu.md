# Debugging MTU Mismatches

When OpenShift pods or VMs cannot reliably reach external services — dropped connections, timeouts on large payloads, or TLS handshakes failing mid-stream — the root cause is often an MTU mismatch somewhere in the path between the cluster overlay network and the upstream infrastructure.

## How MTU Issues Manifest

Symptoms that point to MTU problems rather than routing or firewall issues:

- Small requests (DNS, health checks) succeed but large transfers stall or time out
- `curl` hangs after headers are received
- TLS handshakes fail intermittently (certificate exchange exceeds MTU)
- NFS or iSCSI mounts timeout during initial negotiation
- `oc rsync` or image pulls hang partway through

!!! note
    If traffic works for small packets but fails for large ones, MTU is almost always the cause. Firewalls and routing issues tend to block everything regardless of packet size.

## Understanding the MTU Stack

OpenShift uses an overlay network (OVN-Kubernetes or OpenShift SDN) which encapsulates pod traffic. Each layer adds overhead:

```
┌─────────────────────────────────────────────┐
│ Application payload                          │
├─────────────────────────────────────────────┤
│ Inner IP + TCP headers (40 bytes)           │
├─────────────────────────────────────────────┤
│ Overlay encapsulation (Geneve = 50 bytes)   │
├─────────────────────────────────────────────┤
│ Outer IP + UDP headers (28 bytes)           │
├─────────────────────────────────────────────┤
│ Physical NIC MTU                            │
└─────────────────────────────────────────────┘
```

| Layer | Typical MTU | Notes |
| ----- | ----------- | ----- |
| Physical NIC | 1500 or 9000 | Set at the switch/NIC level |
| Cluster network (pods) | 1400 or 8900 | Physical MTU minus overlay overhead |
| Geneve overhead | 50 bytes | OVN-Kubernetes default encapsulation |
| Service network | Inherits pod MTU | ClusterIP traffic stays in overlay |

If the physical MTU is 1500, the pod MTU must be 1400 (1500 − 100 for Geneve + outer headers). If any hop between the pod and the destination has a lower MTU and does not fragment or return ICMP "Fragmentation Needed," packets are silently dropped.

## Step 1: Check the Cluster MTU Configuration

```bash
oc get network.operator cluster -o jsonpath='{.spec.defaultNetwork.ovnKubernetesConfig.mtu}'
```

If empty, check the status for the effective value:

```bash
oc get network.operator cluster -o jsonpath='{.status.defaultNetwork.ovnKubernetesConfig.mtu}'
```

For OpenShift SDN clusters:

```bash
oc get network.operator cluster -o jsonpath='{.spec.defaultNetwork.openshiftSDNConfig.mtu}'
```

## Step 2: Verify the Pod-Level MTU

Pick any running pod and check what MTU it sees:

```bash
oc exec -it deploy/router-default -n openshift-ingress -- cat /sys/class/net/eth0/mtu
```

Or from a debug pod:

```bash
oc debug node/<node-name> -- chroot /host ip link show ovn-k8s-mp0 | grep mtu
```

The pod MTU should be exactly **physical NIC MTU − 100** (for Geneve).

## Step 3: Check the Node Physical MTU

```bash
oc debug node/<node-name> -- chroot /host ip link show <primary-interface>
```

Look for `mtu XXXX` in the output. This must match what the upstream switch port is configured for. Common values:

- **1500** — standard Ethernet, pod MTU should be 1400
- **9000** — jumbo frames, pod MTU should be 8900

!!! warning
    Every device in the path must support the same MTU. If your nodes are set to 9000 but a single switch, router, or firewall in the path only supports 1500, large packets will be dropped silently.

## Step 4: Test the Path with Specific Packet Sizes

From a pod, send packets of increasing size to the external service with the "Don't Fragment" bit set. This isolates exactly where the path breaks.

```bash
oc run mtu-test --image=registry.access.redhat.com/ubi9/ubi-minimal --rm -it --restart=Never -- bash
```

Inside the pod:

```bash
# Start at a size you know works and increase
# -M do = set Don't Fragment bit
# -s = payload size (add 28 for IP+ICMP headers)

ping -M do -s 1372 -c 3 <external-service-ip>   # Should work (1372 + 28 = 1400)
ping -M do -s 1373 -c 3 <external-service-ip>   # Might fail if path MTU is 1400
ping -M do -s 1450 -c 3 <external-service-ip>   # Will fail if physical MTU is 1500
```

If ping succeeds at 1372 but fails at 1373, your effective path MTU is 1400 (which is correct for a 1500 physical MTU with Geneve overlay).

If ping fails at a lower value (e.g., 1272), something in the path has a lower MTU than expected.

## Step 5: Test from the Node Directly

To isolate whether the problem is the overlay or the physical network, test from the node itself:

```bash
oc debug node/<node-name> -- chroot /host ping -M do -s 1472 -c 3 <external-service-ip>
```

- **1472 + 28 = 1500** — tests the full physical MTU from the node
- If this fails, the issue is in the physical network (switches, routers, firewalls)
- If this succeeds but the pod test fails, the issue is overlay overhead

## Step 6: Check for PMTUD (Path MTU Discovery) Blackholes

Path MTU Discovery relies on receiving ICMP "Fragmentation Needed" (type 3, code 4) messages. If a firewall blocks ICMP, the sender never learns the path MTU is too small and keeps sending oversized packets that get silently dropped.

From a node, verify ICMP is not being blocked:

```bash
oc debug node/<node-name> -- chroot /host tcpdump -i <primary-interface> -c 10 'icmp and icmp[icmptype] == 3'
```

In another terminal, trigger a large packet:

```bash
oc debug node/<node-name> -- chroot /host ping -M do -s 9000 -c 1 <external-service-ip>
```

If you get no ICMP responses captured, a firewall in the path is blocking ICMP fragmentation messages. This is the most common cause of "silent" MTU failures.

!!! tip
    Ask your network team to allow ICMP type 3 (Destination Unreachable) through all firewalls in the path. Blocking ICMP type 3 breaks Path MTU Discovery and causes hard-to-diagnose connectivity issues.

## Step 7: Trace the Entire Path

If the problem is somewhere between the node and the destination, trace each hop:

```bash
oc debug node/<node-name> -- chroot /host tracepath -n <external-service-ip>
```

`tracepath` automatically discovers the path MTU at each hop. Look for a line showing a lower MTU value — that identifies the bottleneck device.

If `tracepath` is not available:

```bash
oc debug node/<node-name> -- chroot /host traceroute --mtu <external-service-ip>
```

## Common Scenarios and Fixes

### Scenario 1: Cluster MTU Set Too High

**Symptom:** Pods can reach some external services but not others.

**Cause:** Cluster was installed with jumbo frames (MTU 9000) but the path to certain services traverses a segment limited to 1500.

**Fix:** Either enable jumbo frames on all intermediate devices, or lower the cluster MTU:

```yaml
apiVersion: operator.openshift.io/v1
kind: Network
metadata:
  name: cluster
spec:
  defaultNetwork:
    ovnKubernetesConfig:
      mtu: 1400
```

!!! warning
    Changing the cluster MTU requires a rolling reboot of all nodes. Plan for maintenance downtime.

### Scenario 2: PMTUD Blocked by Firewall

**Symptom:** Small requests work, large transfers hang. Problem appears intermittently depending on payload size.

**Cause:** A firewall is dropping ICMP type 3 messages, preventing Path MTU Discovery.

**Fix:** Allow ICMP type 3 code 4 (Fragmentation Needed) through all firewalls between the cluster nodes and external services.

### Scenario 3: Mismatched Jumbo Frames

**Symptom:** Nodes show MTU 9000 but pods cannot reach external services that are on a 1500 MTU segment.

**Cause:** The node NICs are configured for jumbo frames but the upstream switch port or router is not.

**Fix:** Verify the switch port configuration matches the node MTU. Use `ip link show` on the node and compare with the switch port settings. Every hop must agree on the MTU.

### Scenario 4: Storage Traffic Failing (NFS/iSCSI)

**Symptom:** PVCs timeout during provisioning or mounts hang.

**Cause:** Storage network has a different MTU than the cluster node interfaces.

**Fix:** Ensure the storage network interfaces (often a dedicated VLAN or bond) have the correct MTU. Check:

```bash
oc debug node/<node-name> -- chroot /host ip link show <storage-interface>
```

Compare against the storage array's network port MTU setting.

## Quick Reference: Expected MTU Values

| Physical NIC MTU | Cluster Network MTU (pods) | Max ping payload from pod |
| ---------------- | -------------------------- | ------------------------- |
| 1500             | 1400                       | 1372                      |
| 9000             | 8900                       | 8872                      |

Formula: **Pod MTU = Physical MTU − 100** (Geneve + outer headers)

Formula: **Max ping payload = Pod MTU − 28** (IP + ICMP headers)

## Checklist

- [ ] Cluster MTU matches (physical NIC MTU − 100)
- [ ] All nodes report the same physical NIC MTU
- [ ] Upstream switches and routers match the node MTU
- [ ] ICMP type 3 is allowed through all firewalls
- [ ] Storage network MTU matches between nodes and storage array
- [ ] No intermediate device (load balancer, firewall) has a lower MTU
- [ ] `tracepath` shows consistent MTU across all hops
