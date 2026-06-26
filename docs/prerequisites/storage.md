# Storage

OpenShift requires persistent storage for the internal registry, monitoring, and application workloads.

## Storage Requirements

| Component          | Access Mode    | Minimum Size | Notes                          |
| ------------------ | -------------- | ------------ | ------------------------------ |
| etcd               | Local SSD      | 40 GB        | Low latency required           |
| Internal Registry  | RWX            | 100 GB       | Shared across all nodes        |
| Monitoring         | RWO            | 50 GB        | Prometheus and Alertmanager    |
| Logging            | RWO            | 200 GB       | Elasticsearch/Loki storage     |
| Application PVCs   | RWO/RWX        | Varies       | Based on workload needs        |

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

### Supported Storage Backends

| Backend             | RWO | RWX | Notes                              |
| ------------------- | --- | --- | ---------------------------------- |
| NFS                 | Yes | Yes | Simple but limited IOPS            |
| OpenShift Data Foundation (ODF) | Yes | Yes | Recommended for production |
| VMware vSphere CSI  | Yes | No  | vSphere environments               |
| Local Storage Operator | Yes | No | Bare metal, high performance    |
| iSCSI / FC          | Yes | No  | Enterprise SAN                     |

### NFS Provisioner (PoC)

For proof of concept environments, an NFS server can provide quick shared storage:

```bash
sudo dnf install -y nfs-utils
sudo mkdir -p /exports/openshift
sudo chown nobody:nobody /exports/openshift
sudo chmod 777 /exports/openshift
echo "/exports/openshift *(rw,sync,no_subtree_check,no_root_squash)" | sudo tee /etc/exports
sudo systemctl enable --now nfs-server
sudo exportfs -rav
sudo firewall-cmd --permanent --add-service=nfs
sudo firewall-cmd --reload
```

!!! warning
    NFS is suitable for PoC environments only. For production workloads, use OpenShift Data Foundation (ODF) or an enterprise storage solution.
