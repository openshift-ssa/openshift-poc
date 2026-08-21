# Storage

Persistent storage for OpenShift will be provided by a third-party storage vendor with a supported CSI (Container Storage Interface) driver. etcd storage remains local to the control plane nodes.

!!! warning "Storage Vendor Inclusion"
    It is **highly recommended** to bring your storage vendor in to assist directly in the installation and configuration of their CSI driver. See [Post-Installation — Storage](../post-installation/storage/index.md) for CSI driver installation guidance.

## Storage Requirements

| Component         | Access Mode    | Minimum Size | Provider   |
| ----------------- | -------------- | ------------ | ---------- |
| etcd              | Local NVMe/SSD | 40 GB        | Local disk |
| Internal Registry | RWX            | 100 GB       | CSI driver |
| Monitoring        | RWO            | 50 GB        | CSI driver |
| Logging           | RWO            | 200 GB       | CSI driver |
| Application PVCs  | RWO/RWX        | Varies       | CSI driver |

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

## Pre-Installation Requirements

Before installing OpenShift, coordinate with your storage vendor to ensure:

- [ ] Storage array is accessible from all cluster nodes over the network
- [ ] Storage network supports jumbo frames (MTU 9000) end-to-end
- [ ] Required network ports are open between nodes and the storage array
- [ ] Storage credentials or certificates are available for CSI driver configuration
- [ ] A StorageClass will be created after installation to provision PVCs

!!! note
    The CSI driver is installed post-installation. Storage is not required during the initial OpenShift installation, but must be available before deploying workloads that need persistent volumes.

## etcd Storage

etcd requires low-latency local storage on control plane nodes. Raft must persist the write-ahead log with `fdatasync` before a proposal can commit, so etcd is sensitive to disk-write latency even though it is not particularly I/O intensive. Slow disks cause missed heartbeats, leader elections, and API timeouts.

Use locally-attached NVMe or SSD drives. Do not use network-attached storage for etcd unless it meets the disk performance requirements below.

See [Recommended etcd practices](https://docs.redhat.com/en/documentation/openshift_container_platform/latest/html/etcd/etcd-practices) for the official guidance.

### Disk performance requirements

| Requirement                                   | Minimum                    | Heavy-load recommendation |
| --------------------------------------------- | -------------------------- | ------------------------- |
| Sequential writes (8 KB, including fdatasync) | 50 IOPS in under 10 ms     | 500 IOPS in 2 ms          |
| 99th percentile fdatasync / fsync latency     | Below 10 ms                | Below 10 ms (target 2 ms) |
| Media                                         | SSD                        | Local NVMe                |

The following practices help meet those numbers:

- Use dedicated local SSD or NVMe drives on control plane nodes. Prefer NVMe in production.
- Do not share etcd disks with log files or other I/O-intensive workloads.
- Avoid NAS, SAN, iSCSI, NFS, and Ceph RBD. Network-attached storage introduces unpredictable latency.
- If the control plane is virtualized, use PCI passthrough so NVMe devices are presented directly to the VMs.

Verify disk performance:

```bash
podman run --privileged --rm -v /var/lib/etcd:/var/lib/etcd:Z \
  registry.access.redhat.com/ubi9/ubi-minimal:latest \
  sh -c "microdnf install -y fio && fio --rw=write --ioengine=sync --fdatasync=1 --directory=/var/lib/etcd --size=22m --bs=2300 --name=etcd-benchmark"
```

!!! note
    RHCOS is an immutable OS without `dnf`. The benchmark runs inside a container that bind-mounts `/var/lib/etcd`. If you are running this from a live RHEL ISO before installation, you can install `fio` directly with `dnf` instead.

The 99th percentile fdatasync latency from this test must be below 10 ms. The disk is not suitable for etcd if that threshold is not met.
