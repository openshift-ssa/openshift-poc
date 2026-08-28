# Storage

Persistent storage for OpenShift will be provided by a third-party storage vendor with a supported CSI (Container Storage Interface) driver. etcd storage remains local to the control plane nodes.

!!! warning "Storage Vendor Inclusion"
    It is **highly recommended** to bring your storage vendor in to assist directly in the installation and configuration of their CSI driver. See [Post-Installation — Storage](../configure-the-cluster/storage/index.md) for CSI driver installation guidance.

## Storage Requirements

| Component         | Access Mode     | Minimum Size       | Provider                                 | Notes                                                                                                                 |
| ----------------- | --------------- | ------------------ | ---------------------------------------- | --------------------------------------------------------------------------------------------------------------------- |
| etcd              | Local NVMe/SSD  | 40 GB              | Local disk                               | Not CSI                                                                                                               |
| Internal Registry | RWX (preferred) | 100 GB             | CSI driver                               | RWO works if you set `replicas: 1` and `rolloutStrategy: Recreate` — see [Registry](../configure-the-cluster/registry.md) |
| Monitoring        | RWO             | 50 GB              | CSI driver                               | Prometheus / Alertmanager PVCs                                                                                        |
| Logging           | Object storage  | Sized by LokiStack | S3-compatible (NooBaa, StorageGRID, AWS) | Loki stores log chunks in **object storage**. Block RWO PVCs are only for Loki WAL/cache, not the 200 GB log data.    |
| Application PVCs  | RWO/RWX         | Varies             | CSI driver                               |                                                                                                                       |

## Storage Network

The storage network should support jumbo frames (MTU 9000) for optimal performance. This applies to every network hop between the cluster nodes and the storage array — switches, NICs, and the storage array ports must all be configured consistently.

- [ ] All switch ports on the storage VLAN/network configured for MTU 9000
- [ ] Storage array network ports configured for MTU 9000
- [ ] Cluster node NICs (or bond/VLAN interfaces used for storage) configured for MTU 9000

!!! warning
    If any single hop in the path does not support jumbo frames, packets will be fragmented or dropped, causing severe performance degradation or connectivity failures. Verify end-to-end with a ping test from a cluster node to the storage array:

    ```bash
    ping -M do -s 8972 {{ storage_array_ip }}
    ```

## Storage Connection Protocol

Before installation, you must understand exactly how the cluster nodes will connect to the storage array. The protocol determines kernel services, MachineConfigs, network infrastructure, and CSI driver configuration. Get answers to all of the following before the install begins.

### Questions to Answer

| Question                                                             | Why It Matters                                                                                                      |
| -------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------- |
| What storage array make and model?                                   | Determines the CSI driver, supported protocols, and vendor-specific tuning                                          |
| What connection protocol? (FC, iSCSI, NVMe/TCP, NVMe/FC, NFS, S3)    | Drives kernel services, network design, and multipath configuration                                                 |
| Is multipathing required?                                            | FC and iSCSI require `multipathd` via MachineConfig; NVMe uses native ANA; NFS and S3 do not use multipathing       |
| How many fabric paths per node?                                      | Determines HBA/NIC requirements and multipath policy (`round-robin`, `service-time`, etc.)                          |
| Is the array ALUA, active/active symmetric, or active/passive?       | Controls the `prio` and `path_grouping_policy` in `multipath.conf`                                                  |
| What are the vendor/product SCSI strings?                            | Required for the `device {}` block in `multipath.conf` — each vendor has different strings                          |
| Are there dedicated storage VLANs?                                   | Storage traffic should be isolated; VLAN IDs are needed for NMState NNCPs                                           |
| What IP addresses / subnets for the storage network?                 | Needed for iSCSI target portals, NVMe/TCP discovery controllers, and node interface configuration                   |
| Are iSCSI CHAP credentials required?                                 | Some arrays require CHAP authentication — credentials must be available for CSI driver configuration                |
| Does the array support RWX (ReadWriteMany)?                          | Required for OpenShift Virtualization live migration and the internal registry                                       |
| What firmware / ONTAP / PowerStore OS version is running?            | Vendor multipath recommendations and CSI driver compatibility vary by firmware version                              |
| Will you run multiple storage arrays on the same cluster?            | Requires a merged `multipath.conf` with device blocks for each vendor — see [Multipathing](../configure-the-cluster/storage/multipathing.md) |

### Protocol Comparison

| Protocol  | Transport      | Multipath Mechanism             | Kernel Services Needed             | Network Requirements                                             |
| --------- | -------------- | ------------------------------- | ---------------------------------- | ---------------------------------------------------------------- |
| FC        | Fibre Channel  | `dm-multipath` (`multipathd`)   | `multipathd`                       | FC HBAs, FC switches, zoning                                     |
| iSCSI     | Ethernet (TCP) | `dm-multipath` (`multipathd`)   | `iscsid` + `multipathd`            | Dedicated storage VLAN, jumbo frames (MTU 9000), CHAP (optional) |
| NVMe/TCP  | Ethernet (TCP) | Native NVMe ANA                 | `nvme-tcp` kernel module           | Dedicated storage VLAN, jumbo frames (MTU 9000)                  |
| NVMe/FC   | Fibre Channel  | Native NVMe ANA                 | `nvme-fc` kernel module            | FC HBAs, FC switches, zoning                                     |
| NFS       | Ethernet (TCP) | N/A (stateless reconnect)       | NFS client (built into RHCOS)      | Network connectivity to NFS server, firewall ports               |
| S3        | HTTPS          | N/A                             | None                               | HTTPS access to S3 endpoint                                      |

### Fibre Channel

FC is the most common protocol in enterprise environments. Each node needs at least two FC HBAs connected to independent fabric switches for redundancy. The storage team must configure zoning so that each node's HBA WWPNs can see the storage array target ports, and the array must have host groups or masking configured to present LUNs to the correct initiators.

Gather before install:

- [ ] Node HBA WWPNs (two per node minimum)
- [ ] Storage array target port WWPNs
- [ ] Zone configuration confirmed on both fabric switches
- [ ] LUN masking / host group configuration on the array
- [ ] Vendor-recommended `multipath.conf` device block

### iSCSI

iSCSI runs over standard Ethernet. Each node should have at least two network paths to the storage array (separate NICs, bonds, or VLANs) for redundancy. The iSCSI initiator service (`iscsid`) must be enabled on RHCOS nodes via MachineConfig.

Gather before install:

- [ ] iSCSI target portal IP addresses (at least two for redundancy)
- [ ] iSCSI target IQN
- [ ] CHAP credentials (if required by the array)
- [ ] Dedicated storage VLAN ID and subnet
- [ ] Jumbo frames (MTU 9000) confirmed end-to-end
- [ ] Vendor-recommended `multipath.conf` device block

### NVMe over Fabrics (NVMe/TCP, NVMe/FC)

NVMe-oF provides lower latency than iSCSI or traditional FC SCSI. It uses native NVMe Asymmetric Namespace Access (ANA) for multipathing instead of `dm-multipath`, so no `multipath.conf` is needed. Not all arrays support NVMe-oF — confirm with your vendor.

Gather before install:

- [ ] Discovery controller IP addresses (NVMe/TCP) or FC target NQNs (NVMe/FC)
- [ ] Dedicated storage VLAN ID and subnet (NVMe/TCP)
- [ ] Array firmware supports NVMe-oF with OpenShift / RHCOS
- [ ] HBA firmware supports NVMe/FC (if applicable)

### NFS

NFS is the simplest protocol to set up — no special kernel services or multipath configuration. It provides RWX access natively, making it useful for the internal registry and shared workload data. However, NFS has higher latency than block protocols and is not suitable for database workloads that require low-latency IOPS.

Gather before install:

- [ ] NFS server IP address and export paths
- [ ] NFS version supported (NFSv4.0, NFSv4.1)
- [ ] Firewall ports open (TCP 2049 minimum)
- [ ] Export permissions configured for the cluster node subnet

## Pre-Installation Checklist

Before installing OpenShift, coordinate with your storage vendor to ensure:

- [ ] Storage array is accessible from all cluster nodes over the network
- [ ] Connection protocol identified and infrastructure in place (FC zoning, iSCSI VLANs, etc.)
- [ ] Storage network supports jumbo frames (MTU 9000) end-to-end (block protocols)
- [ ] Required network ports are open between nodes and the storage array
- [ ] Multipath configuration documented (vendor-specific `device {}` block or NVMe ANA confirmed)
- [ ] Storage credentials or certificates are available for CSI driver configuration
- [ ] A StorageClass will be created after installation to provision PVCs

!!! note
    The CSI driver is installed post-installation. Storage is not required during the initial OpenShift installation, but must be available before deploying workloads that need persistent volumes.

## etcd Storage

etcd requires low-latency local storage on control plane nodes. Raft must persist the write-ahead log with `fdatasync` before a proposal can commit, so etcd is sensitive to disk-write latency even though it is not particularly I/O intensive. Slow disks cause missed heartbeats, leader elections, and API timeouts.

Use locally-attached NVMe or SSD drives. Do not use network-attached storage for etcd unless it meets the disk performance requirements below.

See [Recommended etcd practices](https://docs.redhat.com/en/documentation/openshift_container_platform/latest/html/etcd/etcd-practices) for the official guidance.

### Disk performance requirements

| Requirement                                   | Minimum                | Heavy-load recommendation |
| --------------------------------------------- | ---------------------- | ------------------------- |
| Sequential writes (8 KB, including fdatasync) | 50 IOPS in under 10 ms | 500 IOPS in 2 ms          |
| 99th percentile fdatasync / fsync latency     | Below 10 ms            | Below 10 ms (target 2 ms) |
| Media                                         | SSD                    | Local NVMe                |

The following practices help meet those numbers:

- Use dedicated local SSD or NVMe drives on control plane nodes. Prefer NVMe in production.
- Do not share etcd disks with log files or other I/O-intensive workloads.
- Avoid NAS, SAN, iSCSI, NFS, and Ceph RBD. Network-attached storage introduces unpredictable latency.
- If the control plane is virtualized, use PCI passthrough so NVMe devices are presented directly to the VMs.

Verify disk performance:

```bash
podman run --privileged --rm -v /var/lib/etcd:/var/lib/etcd:Z \
  registry.redhat.io/ubi9/ubi-minimal:latest \
  sh -c "microdnf install -y fio && fio --rw=write --ioengine=sync --fdatasync=1 --directory=/var/lib/etcd --size=22m --bs=2300 --name=etcd-benchmark"
```

!!! note
    RHCOS is an immutable OS without `dnf`. The benchmark runs inside a container that bind-mounts `/var/lib/etcd`. If you are running this from a live RHEL ISO before installation, you can install `fio` directly with `dnf` instead.

The 99th percentile fdatasync latency from this test must be below 10 ms. The disk is not suitable for etcd if that threshold is not met.
