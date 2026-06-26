# Storage

Persistent storage for OpenShift will be provided by a third-party storage vendor with a supported CSI (Container Storage Interface) driver. etcd storage remains local to the control plane nodes.

## Storage Requirements

| Component        | Access Mode | Minimum Size | Provider           |
| ---------------- | ----------- | ------------ | ------------------ |
| etcd             | Local SSD   | 40 GB        | Local disk         |
| Internal Registry | RWX        | 100 GB       | CSI driver         |
| Monitoring       | RWO         | 50 GB        | CSI driver         |
| Logging          | RWO         | 200 GB       | CSI driver         |
| Application PVCs | RWO/RWX     | Varies       | CSI driver         |

## Pre-Installation Requirements

Before installing OpenShift, coordinate with your storage vendor to ensure:

- [ ] Storage array is accessible from all cluster nodes over the network
- [ ] Required network ports are open between nodes and the storage array
- [ ] Storage credentials or certificates are available for CSI driver configuration
- [ ] A StorageClass will be created after installation to provision PVCs

!!! note
    The CSI driver is installed post-installation. Storage is not required during the initial OpenShift installation, but must be available before deploying workloads that need persistent volumes.

---

## Details

### etcd Storage

etcd requires low-latency storage. Use locally-attached NVMe or SSD drives on control plane nodes. Do not use network-attached storage for etcd.

Verify disk performance:

```bash
sudo dnf install -y fio
fio --rw=write --ioengine=sync --fdatasync=1 --directory=/var/lib/etcd --size=22m --bs=2300 --name=etcd-benchmark
```

The 99th percentile fdatasync latency should be below 10ms.

### CSI Driver Installation

After the cluster is running, install your vendor's CSI driver. Most vendors provide an Operator available through OperatorHub or a Helm chart. The general process is:

1. Install the CSI driver Operator (or deploy via manifests provided by the vendor)
2. Configure the driver with storage array credentials and connectivity details
3. Create a StorageClass that references the CSI driver
4. Set the StorageClass as the cluster default

```bash
# Verify CSI driver is running
oc get csidrivers

# Verify StorageClass is available
oc get storageclass

# Set default StorageClass
oc patch storageclass <storage-class-name> -p '{"metadata":{"annotations":{"storageclass.kubernetes.io/is-default-class":"true"}}}'
```

### Access Modes

Confirm with your storage vendor which access modes are supported:

| Access Mode | Description                           | Common Use                        |
| ----------- | ------------------------------------- | --------------------------------- |
| RWO         | Read-Write Once (single node)         | Databases, monitoring             |
| RWX         | Read-Write Many (multiple nodes)      | Registry, shared application data |
| ROX         | Read-Only Many (multiple nodes)       | Static content, shared configs    |

### Vendor Compatibility

Verify your storage vendor and driver version are listed in the [Red Hat Ecosystem Catalog](https://catalog.redhat.com) for your target OpenShift version.
