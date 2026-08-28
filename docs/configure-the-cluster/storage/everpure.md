# Everpure

[PX-CSI](https://docs.portworx.com/portworx-csi)  
[Portworx Enterprise](https://docs.portworx.com/portworx-enterprise)


!!! important "Use the Official Documentation"
    Always refer to the official vendor documentation for the latest installation and configuration guidance. The examples below are field notes from POC engagements and may not reflect the most current driver versions or recommended settings.

# Pure Storage (Evergreen)

Pure Storage offers two paths for providing persistent storage on OpenShift:

- **PX-CSI (Portworx CSI)** — The current recommended approach. Provisions FlashArray and FlashBlade volumes directly as PVCs via the Portworx Operator. Supports iSCSI, Fibre Channel, and NVMe-oF (NVMe/TCP, NVMe/FC, NVMe/RoCE).
- **Portworx Enterprise** — A full software-defined storage layer that runs on the OpenShift nodes. Provides data services (replication, snapshots, encryption, DR) on top of FlashArray or local disks.

Both are deployed through the **Portworx Operator** available in the OpenShift Software Catalog.

## Documentation

| Product             | Documentation                                                                                                        |
| ------------------- | -------------------------------------------------------------------------------------------------------------------- |
| PX-CSI              | [Install and Run PX-CSI](https://docs.portworx.com/portworx-csi/install)                                            |
| PX-CSI Air-Gapped   | [Install PX-CSI in Air-Gapped Clusters](https://docs.portworx.com/portworx-csi/install/airgapped-install)           |
| Portworx Enterprise | [Install on Bare Metal OpenShift](https://docs.portworx.com/portworx-enterprise/platform/install/bare-metal/openshift-non-airgap) |
| FlashArray Prep     | [Use FlashArray as Backend Storage](https://docs.portworx.com/portworx-csi/install/prepare/flash-array)              |
| Portworx Central    | [Portworx Central — Generate Specs](https://central.portworx.com)                                                   |

---

## PX-CSI (Direct Access Volumes)

PX-CSI provisions FlashArray and FlashBlade volumes directly — there is no software-defined storage layer in between. Volumes are mapped to PVCs and mounted to pods. Applications write data directly to the array.

### Prerequisites

- FlashArray or FlashBlade with API access configured
- FlashArray management endpoint IP and API token
- OpenShift cluster with worker nodes connected to the storage network
- For block volumes (iSCSI, NVMe-oF, FC): multipath and udev configuration via MachineConfig — see [Multipathing](multipathing.md)
- For NFS (FlashBlade File Services): no multipath or udev configuration needed

### Step 1 — Create the FlashArray Secret

Create a `pure.json` file with your FlashArray management endpoint and API token:

```json
{
  "FlashArrays": [
    {
      "MgmtEndPoint": "10.0.0.50",
      "APIToken": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
    }
  ]
}
```

If you are also using FlashBlade, add a `FlashBlades` section to the same file:

```json
{
  "FlashArrays": [
    {
      "MgmtEndPoint": "10.0.0.50",
      "APIToken": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
    }
  ],
  "FlashBlades": [
    {
      "MgmtEndPoint": "10.0.0.51",
      "APIToken": "yyyyyyyy-yyyy-yyyy-yyyy-yyyyyyyyyyyy",
      "NFSEndPoint": "10.0.0.52"
    }
  ]
}
```

Create the secret in the namespace where PX-CSI will be installed:

```bash
oc create secret generic px-pure-secret \
  --namespace portworx \
  --from-file=pure.json=pure.json
```

!!! warning
    The secret must be named `px-pure-secret` — PX-CSI looks for this specific name at startup.

### Step 2 — Install the Portworx Operator

From the OpenShift web console:

1. Go to **Ecosystem > Software Catalog**
2. Search for **Portworx Operator**
3. Click **Install** and deploy into the `portworx` namespace

Or via CLI:

```bash
cat << 'EOF' | oc apply -f -
apiVersion: v1
kind: Namespace
metadata:
  name: portworx
  labels:
    pod-security.kubernetes.io/enforce: privileged
    pod-security.kubernetes.io/audit: privileged
    pod-security.kubernetes.io/warn: privileged
---
apiVersion: operators.coreos.com/v1
kind: OperatorGroup
metadata:
  name: portworx-operator
  namespace: portworx
spec:
  targetNamespaces:
    - portworx
---
apiVersion: operators.coreos.com/v1alpha1
kind: Subscription
metadata:
  name: portworx-certified
  namespace: portworx
spec:
  channel: stable
  name: portworx-certified
  source: certified-operators
  sourceNamespace: openshift-marketplace
  installPlanApproval: Manual
EOF
```

Approve the install plan:

```bash
oc get installplan -n portworx
oc patch installplan <name> -n portworx --type merge -p '{"spec":{"approved":true}}'
```

### Step 3 — Generate and Deploy the StorageCluster

Use [Portworx Central](https://central.portworx.com) to generate a StorageCluster spec tailored to your environment. Select **PX-CSI** as the product and **OpenShift 4+** as the distribution.

The generated spec will look similar to:

```yaml
apiVersion: core.libopenstorage.org/v1
kind: StorageCluster
metadata:
  name: px-cluster
  namespace: portworx
  annotations:
    portworx.io/is-openshift: "true"
    portworx.io/misc-args: "--oem px-csi"
spec:
  image: portworx/px-pure-csi-driver:26.1.0
  imagePullPolicy: Always
  csi:
    enabled: true
  monitoring:
    telemetry:
      enabled: true
    prometheus:
      exportMetrics: true
  env:
  - name: PURE_FLASHARRAY_SAN_TYPE
    value: "ISCSI"
```

Set `PURE_FLASHARRAY_SAN_TYPE` to your protocol:

| Value         | Protocol           |
| ------------- | ------------------ |
| `ISCSI`       | iSCSI              |
| `FC`          | Fibre Channel      |
| `NVMEOF-TCP`  | NVMe over TCP      |
| `NVMEOF-FC`   | NVMe over FC       |
| `NVMEOF-RDMA` | NVMe over RoCE     |

For NVMe/TCP, also set the allowed storage CIDRs:

```yaml
  env:
  - name: PURE_FLASHARRAY_SAN_TYPE
    value: "NVMEOF-TCP"
  - name: PURE_NVME_ALLOWED_CIDRS
    value: "10.10.20.0/24"
```

Apply the spec:

```bash
oc apply -f storagecluster.yaml
```

### Step 4 — Verify

```bash
oc get storagecluster -n portworx
oc get pods -n portworx
oc get sc
```

PX-CSI automatically creates a set of default StorageClasses during installation. You can use these or create custom ones.

### Step 5 — Create a StorageClass (Optional)

If you need a custom StorageClass:

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: pure-block
provisioner: pxd.portworx.com
parameters:
  backend: pure_block
  pure_fa_pod_name: ""
reclaimPolicy: Delete
allowVolumeExpansion: true
volumeBindingMode: WaitForFirstConsumer
```

---

## Portworx Enterprise

Portworx Enterprise is a full software-defined storage platform that runs on OpenShift worker nodes. It aggregates local or cloud-attached disks into a shared storage pool and provides enterprise data services (synchronous replication, snapshots, encryption, disaster recovery, auto-capacity management) on top.

Use Portworx Enterprise when you need data services beyond what the FlashArray provides natively, or when you want storage pooling across heterogeneous disks.

### Installation

Portworx Enterprise installation follows the same Operator-based approach:

1. Install the **Portworx Operator** from the Software Catalog
2. Generate a StorageCluster spec from [Portworx Central](https://central.portworx.com) — select **Portworx Enterprise** as the product
3. Apply the generated spec

See [Installation on a Bare Metal OpenShift Cluster](https://docs.portworx.com/portworx-enterprise/platform/install/bare-metal/openshift-non-airgap) for the full walkthrough.

### Key Differences from PX-CSI

| Capability              | PX-CSI (Direct Access)                | Portworx Enterprise                        |
| ----------------------- | ------------------------------------- | ------------------------------------------ |
| Storage model           | Direct FlashArray/FlashBlade volumes  | Software-defined pool across local disks   |
| Data replication        | Array handles replication             | Portworx replicates across nodes           |
| Snapshots               | Array-native snapshots                | Portworx-managed snapshots                 |
| Encryption              | Array-level encryption                | Portworx per-volume encryption             |
| Disaster recovery       | Array-based DR (ActiveCluster, etc.)  | Portworx PX-DR (async replication)         |
| Node local storage      | Not used                              | Aggregated into storage pools              |
| Resource overhead       | Minimal (CSI driver only)             | Runs storage services on every worker node |

---

## Troubleshooting

### PX-CSI Pods Not Starting

```bash
oc get pods -n portworx
oc logs -n portworx -l name=portworx --tail=50
```

Common causes:

- `px-pure-secret` not created or in the wrong namespace
- FlashArray management endpoint not reachable from worker nodes
- API token invalid or expired

### PVCs Stuck in Pending

```bash
oc describe pvc <pvc-name>
oc logs -n portworx -l name=portworx-csi-driver --tail=50
```

Common causes:

- StorageClass provisioner name mismatch
- SAN type mismatch (e.g., `NVMEOF-TCP` specified but nodes only have iSCSI connectivity)
- Multipath not configured on worker nodes (required for iSCSI and FC)

### Multipath Issues

For iSCSI and FC block volumes, multipath must be configured on the worker nodes via MachineConfig. See [Multipathing](multipathing.md) for the framework and delivery mechanism. Pure Storage FlashArray is active/active symmetric — consult the [FlashArray preparation guide](https://docs.portworx.com/portworx-csi/install/prepare/flash-array) for the recommended multipath and udev configuration.
