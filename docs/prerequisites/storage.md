# Storage

Persistent storage for OpenShift will be provided by a third-party storage vendor with a supported CSI (Container Storage Interface) driver. etcd storage remains local to the control plane nodes.

!!! warning "Storage Vendor Inclusion"
    It is **highly recommend** to bring your storage vendor in to assist directly in the installation and configuration of their CSI driver. While the Red Hat sales engineers are multidisciplinary and bring tons of expertise, it is impossible for them to keep up with the nuances and best practices of every single storage provider in the market. 

## Storage Requirements

| Component        | Access Mode | Minimum Size | Provider   |
| ---------------- | ----------- | ------------ | ---------- |
| etcd             | Local SSD   | 40 GB        | Local disk |
| Internal Registry | RWX        | 100 GB       | CSI driver |
| Monitoring       | RWO         | 50 GB        | CSI driver |
| Logging          | RWO         | 200 GB       | CSI driver |
| Application PVCs | RWO/RWX     | Varies       | CSI driver |

## Storage Network

The storage network must support jumbo frames (MTU 9000) for optimal performance. This applies to every network hop between the cluster nodes and the storage array — switches, NICs, and the storage array ports must all be configured consistently.

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

etcd requires low-latency storage. Use locally-attached NVMe or SSD drives on control plane nodes if possible. Do not use network-attached storage for etcd unless it meets strict performance guarantees.

Verify disk performance:

```bash
sudo dnf install -y fio
fio --rw=write --ioengine=sync --fdatasync=1 --directory=/var/lib/etcd --size=22m --bs=2300 --name=etcd-benchmark
```

The 99th percentile fdatasync latency should be below 10ms.
