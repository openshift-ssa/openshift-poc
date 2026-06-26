# Infrastructure

Provision compute resources that meet or exceed the minimum requirements for each node type.

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

### Supported Platforms

- VMware vSphere 7.0+
- Red Hat OpenStack Platform
- Bare Metal (IPMI/BMC or Redfish)
- Red Hat Virtualization (RHV)

### BIOS/Firmware Settings

Ensure the following on all nodes:

- Virtualization extensions enabled (VT-x / AMD-V)
- Boot order set to network (PXE) or local disk depending on install method
- UEFI Secure Boot supported (optional but recommended)
