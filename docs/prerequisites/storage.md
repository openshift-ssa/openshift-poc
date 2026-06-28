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

## Pre-Installation Requirements

Before installing OpenShift, coordinate with your storage vendor to ensure:

- [ ] Storage array is accessible from all cluster nodes over the network
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
