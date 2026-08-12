# Dell Unity Bare Metal

[Dell CSM — Install CSI Unity XT on OpenShift](https://dell.github.io/csm-docs/docs/getting-started/installation/openshift/unityxt/csmoperator/) | [Dell CSM Support Matrix](https://dell.github.io/csm-docs/docs/supportmatrix/) | [Dell CSI Unity samples](https://github.com/dell/csi-unity/tree/main/samples)

This guide configures **Dell Unity XT** as persistent storage for an OpenShift **bare metal** cluster over **iSCSI**, using the Dell CSI Driver for Unity XT installed through the Dell Container Storage Modules (CSM) Operator.

!!! warning "Storage Vendor Inclusion"
    Bring Dell in to assist with Unity CSI installation and validation. Red Hat SEs can help with the OpenShift side of the integration, but array-side best practices, multipath settings, and support-matrix alignment belong with the storage vendor.

!!! info "Bare metal focus"
    This page is for bare metal (or bare-metal-equivalent) workers that act as iSCSI initiators to Unity. It is **not** the vSphere CSI path — for clusters on VMware, see [VMware vSphere CSI](vsphere-csi.md).

## CSI vs CSM

Three related but different things get lumped under “Dell CSM”:

| Component | Role |
| --------- | ---- |
| **Dell CSI Driver for Unity XT** | Required. Creates Unity LUNs, maps them to OpenShift nodes, attaches/mounts volumes, expands volumes, and integrates snapshots. |
| **Dell CSM Operator** | Recommended on OpenShift. Red Hat–certified install and lifecycle mechanism for the CSI driver (OperatorHub). |
| **Optional CSM modules** (Authorization, Replication, Observability, Resiliency) | Separate Dell features. As of the CSM 1.17 support matrix, Unity XT is **not** supported for Authorization, Replication, or Observability through the Operator. Do not design the PoC around those modules for Unity XT. |

Creating a `ContainerStorageModule` custom resource installs the Unity CSI driver — it does **not** enable every optional CSM module.

## Version Alignment

Confirm your combination against the current Dell CSM support matrix before calling the design production-supported. As of CSM 1.17, Dell lists:

| Component | Typical target |
| --------- | -------------- |
| Red Hat OpenShift | 4.18–4.21 |
| Dell CSM Operator | 1.12.x |
| Dell CSM release | 1.17.x |
| Dell CSI Driver for Unity | 2.17.x |
| Unity OE | 5.3.x, 5.4.x, or 5.5 |
| Protocol (this guide) | iSCSI |

```bash
oc get clusterversion
oc get csv -A | grep -i dell
```

Also record the Unity OE release and array serial from Unisphere. If Unity OE is older than 5.3, do not assume the current driver is supported.

## Requirements

- OpenShift bare metal cluster with `cluster-admin`
- Dell Unity XT with Unisphere API access and at least one storage pool
- Layer-3 reachability from **every storage-capable worker** to Unity iSCSI portals on TCP **3260**
- HTTPS (TCP **443**) reachability from the CSI controller pods to the Unisphere management endpoint
- Unique iSCSI initiator IQN on each worker
- Multipathing configured for Unity iSCSI
- OperatorHub access for **Dell Container Storage Modules** (Certified)

!!! note "Two Unity addresses"
    The CSI controller uses the **Unisphere management** endpoint (HTTPS/443) to create and map LUNs. Application I/O uses the **iSCSI target** portals (TCP/3260). Do not treat the management IP as an iSCSI data path.

!!! tip "Dual fabric"
    For production resilience, put SPA and SPB iSCSI portals on independent switches/fabrics so both multipath legs do not share a single switch failure domain. A single-switch lab can pilot; do not call it highly available.

## Prepare Workers (iSCSI + Multipath)

Dell requires iSCSI initiator utilities and multipathing on every worker that may run a Unity PVC. On RHCOS, prefer MachineConfig — do not use unmanaged `dnf`/`yum` edits on nodes.

### 1. Verify initiator readiness

```bash
for node in $(oc get nodes -l node-role.kubernetes.io/worker -o name); do
  echo "===== ${node} ====="
  oc debug "${node}" -- chroot /host bash -c '
    rpm -q iscsi-initiator-utils device-mapper-multipath 2>/dev/null || true
    cat /etc/iscsi/initiatorname.iscsi 2>/dev/null || true
    systemctl is-enabled iscsid 2>/dev/null || true
    systemctl is-active iscsid 2>/dev/null || true
    systemctl is-enabled multipathd 2>/dev/null || true
    systemctl is-active multipathd 2>/dev/null || true
  '
done
```

!!! warning "Unique IQNs required"
    Each worker must have a **unique** initiator IQN. Cloned templates that reuse the same IQN cause Unity host-registration and mapping failures. Do **not** write one MachineConfig that sets the same `InitiatorName` on every node.

### 2. Prove portal reachability

```bash
oc debug node/<worker-node> -- chroot /host bash -c '
  timeout 3 bash -c "cat < /dev/null > /dev/tcp/<UNITY_ISCSI_PORTAL>/3260" \
    && echo "TCP 3260 reachable" \
    || echo "TCP 3260 unavailable"
  iscsiadm -m discovery -t sendtargets -p <UNITY_ISCSI_PORTAL>
'
```

### 3. Enable iscsid

`99-workers-enable-iscsid.yaml`:

```yaml
apiVersion: machineconfiguration.openshift.io/v1
kind: MachineConfig
metadata:
  name: 99-workers-enable-iscsid
  labels:
    machineconfiguration.openshift.io/role: worker
spec:
  config:
    ignition:
      version: 3.4.0
    systemd:
      units:
        - name: iscsid.service
          enabled: true
```

### 4. Configure Unity multipath.conf

Cleartext `multipath.conf` (from Dell’s OpenShift Unity XT guide):

```text
defaults {
  polling_interval 5
  checker_timeout 15
  disable_changed_wwids yes
  find_multipaths no
}
devices {
  device {
    vendor                   DellEMC
    product                  Unity
    detect_prio              "yes"
    path_selector            "queue-length 0"
    path_grouping_policy     "group_by_prio"
    path_checker             tur
    failback                 immediate
    fast_io_fail_tmo         5
    no_path_retry            3
    rr_min_io_rq             1
    max_sectors_kb           1024
    dev_loss_tmo             10
  }
}
```

!!! warning "Existing multipath.conf"
    If another vendor’s device stanza already exists in `/etc/multipath.conf`, do not blindly overwrite the whole file — add the Unity stanza alongside it. Coordinate `no_path_retry` / queueing policy with Dell’s Host Connectivity Guide and any other vendor requirements.

Encode and wrap in a MachineConfig (prefer Ignition `contents.source` data URLs):

```bash
base64 -w0 multipath.conf
```

`99-workers-multipath-conf.yaml`:

```yaml
apiVersion: machineconfiguration.openshift.io/v1
kind: MachineConfig
metadata:
  name: 99-workers-multipath-conf
  labels:
    machineconfiguration.openshift.io/role: worker
spec:
  config:
    ignition:
      version: 3.4.0
    storage:
      files:
        - path: /etc/multipath.conf
          mode: 256
          overwrite: true
          contents:
            source: data:text/plain;charset=utf-8;base64,<BASE64_OF_MULTIPATH_CONF>
```

### 5. Enable multipathd

`99-workers-enable-multipathd.yaml`:

```yaml
apiVersion: machineconfiguration.openshift.io/v1
kind: MachineConfig
metadata:
  name: 99-workers-enable-multipathd
  labels:
    machineconfiguration.openshift.io/role: worker
spec:
  config:
    ignition:
      version: 3.4.0
    systemd:
      units:
        - name: multipathd.service
          enabled: true
```

### 6. Apply and wait

```bash
oc apply -f 99-workers-enable-iscsid.yaml
oc apply -f 99-workers-multipath-conf.yaml
oc apply -f 99-workers-enable-multipathd.yaml
oc get mcp/worker -w
```

Wait until `UPDATED=True`, `UPDATING=False`, `DEGRADED=False`. Workers reboot as the config rolls out.

## Install the Dell CSM Operator

1. In the OpenShift console: **OperatorHub** → search **Dell Container Storage Modules**
2. Install into `openshift-operators` (All namespaces)
3. For PoC/production control, prefer **Manual** approval so InstallPlans are reviewed before storage-driver upgrades

```bash
oc get subscription -A | grep -i dell
oc get csv -A | grep -i csm
oc get pods -n openshift-operators | grep -i dell
```

## Create the Unity Credentials Secret

```bash
oc create namespace unity
```

Create `config.yaml` (do not commit real passwords):

```yaml
storageArrayList:
  - arrayId: "<ARRAY_ID>"
    username: "<unisphere-user>"
    password: "<unisphere-password>"
    endpoint: "https://<ARRAY_MGMT_HOST>/"
    skipCertificateValidation: true
    isDefault: true
```

`arrayId` is the Unity system serial (for example `APM…`), not the management IP and not the pool name. `endpoint` is the Unisphere management URL.

```bash
oc create secret generic unity-creds \
  --from-file=config=config.yaml \
  -n unity
rm -f config.yaml
oc get secret unity-creds -n unity
```

!!! tip "Secret name"
    Some Dell samples use `unity-creds`; others use `unity-config`. Match the Secret name expected by the `ContainerStorageModule` sample for your Operator version.

!!! note "Certificates"
    `skipCertificateValidation: true` is acceptable for an initial lab connection. For anything shared or production-bound, install the Unisphere CA (`unity-cert-0`, …) and set validation to `false`.

## Deploy the Unity CSI Driver

Start from the **versioned** Unity sample shipped with your installed Operator release, then edit credentials/env values. Newer CSM Operator releases use top-level `spec.version` (for example `v1.17.2`) instead of the older `driver.configVersion` field.

Minimal shape (excerpt — retain required sidecars from the full Dell sample):

```yaml
apiVersion: storage.dell.com/v1
kind: ContainerStorageModule
metadata:
  name: unity
  namespace: unity
spec:
  version: v1.17.2
  driver:
    csiDriverType: unity
    csiDriverSpec:
      fSGroupPolicy: ReadWriteOnceWithFSType
      storageCapacity: true
    replicas: 2
    forceRemoveDriver: true
    common:
      envs:
        # Required on OpenShift/RHCOS so the node plug-in can reach host iSCSI
        - name: X_CSI_ISCSI_CHROOT
          value: "/noderoot"
        - name: X_CSI_UNITY_ALLOW_MULTI_POD_ACCESS
          value: "false"
        - name: X_CSI_UNITY_SKIP_CERTIFICATE_VALIDATION
          value: "true"
```

```bash
oc apply -f csm-unity.yaml
oc get containerstoragemodule -n unity
oc get pods -n unity -o wide
oc get csidriver
```

You want the CR in a healthy/`Succeeded` state, controller pods Running, and a node pod on each storage-capable worker. Confirm the CSIDriver name is `csi-unity.dellemc.com`.

!!! warning "Do not manage CSI LUNs out of band"
    After the driver is live, do not resize, delete, remap, or rename CSI-managed Unity LUNs directly in Unisphere or with UEMCLI. Out-of-band changes can leave Kubernetes and array metadata inconsistent.

## Create the StorageClass

Prefer `WaitForFirstConsumer` and `Retain` for the first PoC/production-oriented class. Add a second `Delete`-based class later for disposable workloads if needed.

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: unity-iscsi-retain
provisioner: csi-unity.dellemc.com
reclaimPolicy: Retain
allowVolumeExpansion: true
volumeBindingMode: WaitForFirstConsumer
parameters:
  protocol: iSCSI
  arrayId: "<ARRAY_ID>"
  storagePool: "<STORAGE_POOL>"
  thinProvisioned: "true"
  isDataReductionEnabled: "false"
  csi.storage.k8s.io/fstype: ext4
```

!!! note "Pool CLI ID"
    `storagePool` must be the Unity pool **CLI ID** (for example `pool_0`), not only the friendly display name.

!!! note "Object name casing"
    Kubernetes object names must be lowercase. Keep the real mixed-case array serial in the `arrayId` parameter; lowercase any array ID fragment you put into `metadata.name`.

```bash
oc apply -f unity-iscsi-storageclass.yaml
oc get storageclass
```

### Optional: set as default

```bash
oc patch storageclass unity-iscsi-retain \
  -p '{"metadata":{"annotations":{"storageclass.kubernetes.io/is-default-class":"true"}}}'
```

### Optional: topology constraints

Dell samples may include `allowedTopologies` keyed on a driver-generated label such as `csi-unity.dellemc.com/<array-id>-iscsi`. Deploy the driver first, then copy the **exact** label from a node — do not guess capitalization:

```bash
oc get nodes --show-labels | grep csi-unity
```

### Optional VolumeSnapshotClass

```yaml
apiVersion: snapshot.storage.k8s.io/v1
kind: VolumeSnapshotClass
metadata:
  name: vsclass-unity
driver: csi-unity.dellemc.com
deletionPolicy: Delete
```

## Test Dynamic Provisioning

Because the StorageClass uses `WaitForFirstConsumer`, the PVC stays `Pending` until a consuming pod is scheduled — that is expected.

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: unity-validation
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: unity-smoke
  namespace: unity-validation
spec:
  accessModes:
    - ReadWriteOnce
  storageClassName: unity-iscsi-retain
  resources:
    requests:
      storage: 10Gi
---
apiVersion: v1
kind: Pod
metadata:
  name: unity-smoke
  namespace: unity-validation
spec:
  containers:
    - name: writer
      image: registry.access.redhat.com/ubi9/ubi-minimal:latest
      command: ["/bin/sh", "-c"]
      args:
        - |
          date > /data/created.txt
          sync
          sleep infinity
      volumeMounts:
        - name: data
          mountPath: /data
  volumes:
    - name: data
      persistentVolumeClaim:
        claimName: unity-smoke
```

```bash
oc apply -f unity-smoke.yaml
oc get pvc,pod -n unity-validation -o wide
oc exec -n unity-validation unity-smoke -- cat /data/created.txt
```

On the scheduled worker, confirm multipath and iSCSI sessions:

```bash
oc debug node/<scheduled-worker> -- chroot /host bash -c 'multipath -ll; iscsiadm -m session'
```

You should see more than one usable path when dual portals are configured. Clean up when finished:

```bash
oc delete -f unity-smoke.yaml
```

!!! note "Retain reclaim policy"
    With `reclaimPolicy: Retain`, deleting the PVC does **not** automatically delete the Unity volume. Clean up released volumes in Unisphere after confirming they are no longer needed.

## OpenShift Virtualization Notes

Unity iSCSI filesystem PVCs are normally **ReadWriteOnce**. That is sufficient for many VM disks, but **live migration** requires **ReadWriteMany (RWX)** shared storage. Do not promise VMotion-like live migration on RWO iSCSI alone.

| Need | Approach |
| ---- | -------- |
| RWO VM disks / most stateful pods | Unity iSCSI StorageClass (this guide) |
| Cross-node RWX / live migration | Unity NAS/NFS (where available) or another RWX-capable platform (for example ODF) |

See also [OpenShift Virtualization Storage Requirements](index.md#openshift-virtualization-storage-requirements).

## Shared Pool Governance

Multiple StorageClasses pointing at the same Unity pool are different Kubernetes policies, not physical isolation. If several teams share one pool, use namespace `ResourceQuota` objects and continue monitoring Unity pool capacity, thin commitment, latency, and SP utilization in Unisphere.

## Troubleshooting

| Symptom | What to check |
| ------- | ------------- |
| PVC stuck `Pending` | Expected with `WaitForFirstConsumer` until a pod exists; otherwise CSI pods, Secret credentials/`arrayId`, `storagePool` / `protocol` |
| Attach / node plug-in failures | Worker → portal `:3260`, unique IQN, `iscsid` active, `X_CSI_ISCSI_CHROOT=/noderoot` |
| Single multipath path | Dual portals reachable, Unity stanza in `/etc/multipath.conf`, `multipathd` active |
| CR failed after copying an old sample | Confirm `spec.version` vs older `driver.configVersion` — do not mix CR schemas |
| Cert errors to Unisphere | `skipCertificateValidation` vs `unity-cert-*` Secrets |
| Wrong Secret name | Align Secret name with the Operator sample for your CSM version |

```bash
oc logs -n unity -l app=csi-unity --tail=200
oc describe containerstoragemodule unity -n unity
oc get events -n unity --sort-by=.lastTimestamp
```

## Supported Features

| Feature | Supported | Notes |
| ------- | --------- | ----- |
| Dynamic provisioning | Yes | Unity CSI |
| Volume expansion | Yes | Controller and node expansion |
| Volume snapshots | Yes | Via VolumeSnapshotClass |
| PVC cloning | Yes | |
| ReadWriteOnce (RWO) | Yes | Typical iSCSI filesystem PVC |
| ReadWriteMany (RWX) | NFS path | Use Unity NAS/NFS when shared file access is required — not iSCSI RWO |
| Topology | Yes | Driver-generated labels; do not invent them |
| Optional CSM modules (Auth/Repl/Obs) | No (Operator matrix) | Use OpenShift RBAC/quotas, backup/DR, and monitoring instead |

## References

- [Dell CSM — Install CSI Unity XT on OpenShift (CSM Operator)](https://dell.github.io/csm-docs/docs/getting-started/installation/openshift/unityxt/csmoperator/)
- [Dell CSM — Support Matrix](https://dell.github.io/csm-docs/docs/supportmatrix/)
- [Dell CSM Operator — upgrading drivers](https://dell.github.io/csm-docs/docs/getting-started/upgrade/openshift/unityxt/operator/)
- [Dell CSI Unity — samples](https://github.com/dell/csi-unity/tree/main/samples)
- Related lab notes: [Configuring OpenShift Virtualization with Dell Unity Storage over iSCSI](https://thomasphall.github.io/posts/openshift-virt-dell-unity-iscsi/)
