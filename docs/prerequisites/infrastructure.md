# Infrastructure

All nodes are bare metal servers in an on-premise environment. Provision compute resources that meet or exceed the minimum requirements for each node type.

## Minimum Resource Requirements

| Node Type      | vCPU | RAM (GB) | Storage (GB) | Count |
| -------------- | ---- | -------- | ------------ | ----- |
| Control Plane  | 4    | 16       | 120          | 3     |
| Worker         | 4    | 16       | 120          | 2     |
| Infrastructure | 4    | 16       | 120          | 3     |

```bash
# Verify hardware on each node
lscpu | grep -E "^CPU\(s\)|^Thread"
free -g
lsblk
```

---

## Details

### Control Plane Nodes

Control plane nodes run etcd, the Kubernetes API server, and cluster controllers. etcd is sensitive to disk latency, so SSD-backed storage is strongly recommended. The 120 GB disk allocation accounts for etcd data, container images, and logs.

### Worker Nodes

Worker nodes run your application workloads. Scale the count and resources based on your expected workload. The minimums listed here support a basic proof of concept.

### Infrastructure Nodes

Infrastructure nodes are optional but recommended. They isolate cluster services (ingress router, internal registry, monitoring stack) from application workloads. In a PoC environment, these services can run on worker nodes instead.

### BMC / Out-of-Band Management

Each bare metal server must have out-of-band management access for remote operations:

| Management Type | Protocol | Purpose                          |
| --------------- | -------- | -------------------------------- |
| IPMI            | IPMI     | Power control, virtual media     |
| Redfish         | HTTPS    | Modern BMC API, virtual media    |
| iLO / iDRAC    | HTTPS    | Vendor-specific BMC              |

Virtual media (mounting the discovery ISO remotely) is the recommended method for booting nodes during installation.

### BIOS/Firmware Settings

Ensure the following on all nodes:

- Boot mode set to UEFI
- Secure Boot supported (optional but recommended)
- Boot order set to local disk (the discovery ISO is mounted via virtual media)
- Hardware clock set to UTC
