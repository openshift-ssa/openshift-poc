# NetApp Trident

[NetApp Trident Documentation](https://docs.netapp.com/us-en/trident/) | [Requirements](https://docs.netapp.com/us-en/trident/trident-get-started/requirements.html)

NetApp Trident is a CSI driver that provides dynamic storage provisioning for Kubernetes clusters using NetApp ONTAP storage systems. It supports NFS (FlexVol and FlexGroup), iSCSI, NVMe/TCP, and Fibre Channel protocols.

## Prerequisites

### Worker Node Preparation

Worker nodes must be configured for the storage protocols you plan to use **before** installing Trident. Follow the [NetApp worker node preparation guide](https://docs.netapp.com/us-en/trident/trident-use/worker-node-prep.html) and complete the steps for each protocol you need.

!!! tip
    The protocol instruction boxes in the NetApp docs are tabbed — click the tab for the protocol you need (NFS, iSCSI, NVMe/TCP, etc.).

!!! warning "NFS v4 Requires Additional Configuration"
    If NFS v4 will be used:

    - The `/etc/idmapd.conf` domain on each worker node **must match** the NFS v4 domain configured on the NetApp array
    - Use `mountOptions: sec=sys` in your StorageClass (shown in the examples below)

#### iSCSI and Multipath MachineConfigs

For iSCSI, NVMe, or Fibre Channel protocols, enable `iscsid` and configure multipath on both master and worker nodes. Apply the following MachineConfigs, then wait for the nodes to reboot.

##### Enable iscsid

```yaml
apiVersion: machineconfiguration.openshift.io/v1
kind: MachineConfig
metadata:
  labels:
    machineconfiguration.openshift.io/role: master
  name: 99-master-enable-iscsid
spec:
  config:
    ignition:
      version: 3.2.0
    systemd:
      units:
      - enabled: true
        name: iscsid.service
---
apiVersion: machineconfiguration.openshift.io/v1
kind: MachineConfig
metadata:
  labels:
    machineconfiguration.openshift.io/role: worker
  name: 99-worker-enable-iscsid
spec:
  config:
    ignition:
      version: 3.2.0
    systemd:
      units:
      - enabled: true
        name: iscsid.service
```

```bash
oc apply -f enable-iscsid.yaml
```

##### Multipath Configuration

Configures `multipathd` to blacklist all devices except NetApp LUNs:

```yaml
apiVersion: machineconfiguration.openshift.io/v1
kind: MachineConfig
metadata:
  labels:
    machineconfiguration.openshift.io/role: master
  name: 99-master-multipath-conf
spec:
  config:
    ignition:
      version: 3.2.0
    storage:
      files:
      - path: /etc/multipath.conf
        mode: 0644
        overwrite: true
        contents:
          source: data:text/plain;charset=utf-8;base64,ZGVmYXVsdHMgewogICAgZmluZF9tdWx0aXBhdGhzIG5vCn0KYmxhY2tsaXN0IHsKICAgIGRldmljZSB7CiAgICAgICAgdmVuZG9yICAuKgogICAgICAgIHByb2R1Y3QgLioKICAgIH0KfQpibGFja2xpc3RfZXhjZXB0aW9ucyB7CiAgICBkZXZpY2UgewogICAgICAgIHByb2R1Y3QgTFVOCiAgICAgICAgdmVuZG9yICBORVRBUFAKICAgIH0KfQ==
---
apiVersion: machineconfiguration.openshift.io/v1
kind: MachineConfig
metadata:
  labels:
    machineconfiguration.openshift.io/role: worker
  name: 99-worker-multipath-conf
spec:
  config:
    ignition:
      version: 3.2.0
    storage:
      files:
      - path: /etc/multipath.conf
        mode: 0644
        overwrite: true
        contents:
          source: data:text/plain;charset=utf-8;base64,ZGVmYXVsdHMgewogICAgZmluZF9tdWx0aXBhdGhzIG5vCn0KYmxhY2tsaXN0IHsKICAgIGRldmljZSB7CiAgICAgICAgdmVuZG9yICAuKgogICAgICAgIHByb2R1Y3QgLioKICAgIH0KfQpibGFja2xpc3RfZXhjZXB0aW9ucyB7CiAgICBkZXZpY2UgewogICAgICAgIHByb2R1Y3QgTFVOCiAgICAgICAgdmVuZG9yICBORVRBUFAKICAgIH0KfQ==
```

```bash
oc apply -f multipath-conf.yaml
```

##### Wait for Rollout

Nodes reboot serially. Wait for both MachineConfigPools to finish:

```bash
oc get mcp master worker -w
```

All pools should show `UPDATED=True`, `UPDATING=False`, `DEGRADED=False`.

!!! warning "Order Matters"
    The MachineConfig rollout must fully complete before installing Trident. If node pods CrashLoop with initiator or multipath errors, the rollout was not finished before the driver was deployed.

### NetApp Storage Array Preparation

Prepare the ONTAP SVM (Storage Virtual Machine) before installing Trident:

| Requirement | Details |
| --- | --- |
| **SVM credentials** | An `vsadmin`-equivalent username and password |
| **API protocols** | Enable `ontapi`, `ssh`, and `http` on the SVM user |
| **Storage protocols** | Enable NFS, iSCSI, and/or NVMe on the SVM as needed |
| **Aggregate assignment** | Assign at least one aggregate directly to the SVM (this does not remove it from other SVMs) |
| **SVM root export** | The SVM root export policy must include the worker nodes |
| **SVM capacity limit** | Set an [SVM capacity limit](https://docs.netapp.com/us-en/ontap/volumes/manage-svm-capacity.html) to protect the array from being overrun with storage requests from Kubernetes |

!!! info "Trident Handles igroup and NQN Registration"
    You do **not** need to manually create an igroup for iSCSI or input NQNs for NVMe — Trident manages these dynamically.

#### Firewall Rules

Open the following ports from **all worker nodes**:

| Destination | Ports | Purpose |
| --- | --- | --- |
| SVM Management LIF | 22, 443 | Trident management API access |
| Data LIFs | Protocol-specific ports (2049 for NFS, 3260 for iSCSI, etc.) | Data path traffic |

#### DNS and Networking Best Practices

- Create DNS entries for all NFS LIFs and management LIFs — use FQDNs instead of IPs for DR and migration purposes
- Place a load balancer or DNS round-robin in front of NFS data LIFs for better distribution
- For Kubernetes-managed replication, peer the clusters and SVMs **before** installing Trident

### Air-Gapped / Disconnected Environments

If your cluster has no access to public container registries, download the required images and push them to your private registry.

**Trident images** — listed at the bottom of the [requirements page](https://docs.netapp.com/us-en/trident/trident-get-started/requirements.html#tested-host-operating-systems)

**Trident Protect images** — see the private registry instructions on the [Trident Protect installation page](https://docs.netapp.com/us-en/trident/trident-protect/trident-protect-installation.html) (click "Install Trident Protect from private registry")

For disconnected installation instructions, see the offline install methods in the [Trident deployment guide](https://docs.netapp.com/us-en/trident/trident-get-started/kubernetes-deploy.html) (look for entries labelled "Offline" in the left-hand navigation).

## Install Trident

=== "OpenShift OperatorHub"

    1. Go to Ecosystem -> Software Catalog -> filter for "Trident" -> click the "NetApp Trident" tile
    2. Click Install
    3. Leave all the defaults and click Install
    4. Wait for the Operator to install

=== "Helm"

    ```bash
    helm repo add netapp-trident https://netapp.github.io/trident-helm-chart
    helm install my-trident-operator netapp-trident/trident-operator \
      --create-namespace -n trident
    ```

Wait for the operator to be ready:

```bash
oc get csv -n trident -w
```

The `PHASE` should show `Succeeded`.

## Create the SVM Credentials Secret

Create this secret in the `trident` namespace. All backend configurations reference it.

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: netappsvm-secret
  namespace: trident
type: Opaque
stringData:
  username: {{ svm_username }}
  password: {{ svm_password }}
```

```bash
oc apply -f netappsvm-secret.yaml
```

## Configure Storage Backends

Create backends in the `trident` namespace for each protocol you need. You can deploy multiple backends side by side.

=== "NFS (FlexVol)"

    ### TridentBackendConfig

    ```yaml
    apiVersion: trident.netapp.io/v1
    kind: TridentBackendConfig
    metadata:
      name: netapp-nfs-backend
      namespace: trident
    spec:
      version: 1
      storageDriverName: ontap-nas
      managementLIF: {{ management_lif_fqdn }}
      dataLIF: {{ data_lif_fqdn_or_loadbalancer }}
      backendName: netapp-nfs-backend
      svm: {{ svm_name }}
      autoExportPolicy: true
      credentials:
        name: netappsvm-secret
    ```

    ```bash
    oc apply -f netapp-nfs-backend.yaml
    ```

    ### StorageClass

    ```yaml
    apiVersion: storage.k8s.io/v1
    kind: StorageClass
    metadata:
      name: basic-netapp-nfs
    provisioner: csi.trident.netapp.io
    parameters:
      storagePools: "netapp-nfs-backend:.*"
      fsType: "nfs"
      backendType: "ontap-nas"
    mountOptions:
      - sec=sys
      - vers=4
    allowVolumeExpansion: true
    ```

    ```bash
    oc apply -f basic-netapp-nfs-sc.yaml
    ```

=== "iSCSI"

    ### TridentBackendConfig

    ```yaml
    apiVersion: trident.netapp.io/v1
    kind: TridentBackendConfig
    metadata:
      name: netapp-iscsi-backend
      namespace: trident
    spec:
      version: 1
      storageDriverName: ontap-san
      managementLIF: {{ management_lif_fqdn }}
      backendName: netapp-iscsi-backend
      svm: {{ svm_name }}
      credentials:
        name: netappsvm-secret
    ```

    ```bash
    oc apply -f netapp-iscsi-backend.yaml
    ```

    ### StorageClass

    ```yaml
    apiVersion: storage.k8s.io/v1
    kind: StorageClass
    metadata:
      name: basic-netapp-iscsi
    provisioner: csi.trident.netapp.io
    parameters:
      storagePools: "netapp-iscsi-backend:.*"
      fsType: "ext4"
      backendType: "ontap-san"
    mountOptions:
      - discard
    allowVolumeExpansion: true
    ```

    ```bash
    oc apply -f basic-netapp-iscsi-sc.yaml
    ```

=== "NFS (FlexGroup)"

    ### TridentBackendConfig

    ```yaml
    apiVersion: trident.netapp.io/v1
    kind: TridentBackendConfig
    metadata:
      name: netapp-nfsflexgroup-backend
      namespace: trident
    spec:
      version: 1
      storageDriverName: ontap-nas-flexgroup
      managementLIF: {{ management_lif_fqdn }}
      dataLIF: {{ data_lif_fqdn_or_loadbalancer }}
      backendName: netapp-nfsflexgroup-backend
      svm: {{ svm_name }}
      autoExportPolicy: true
      credentials:
        name: netappsvm-secret
    ```

    ```bash
    oc apply -f netapp-nfsflexgroup-backend.yaml
    ```

    ### StorageClass

    ```yaml
    apiVersion: storage.k8s.io/v1
    kind: StorageClass
    metadata:
      name: basic-netapp-nfs-flexgroup
    provisioner: csi.trident.netapp.io
    parameters:
      storagePools: "netapp-nfsflexgroup-backend:.*"
      fsType: "nfs"
      backendType: "ontap-nas-flexgroup"
    mountOptions:
      - sec=sys
      - vers=4
    allowVolumeExpansion: true
    ```

    ```bash
    oc apply -f basic-netapp-nfs-flexgroup-sc.yaml
    ```

=== "NVMe/TCP"

    ### TridentBackendConfig

    ```yaml
    apiVersion: trident.netapp.io/v1
    kind: TridentBackendConfig
    metadata:
      name: netapp-nvme-backend
      namespace: trident
    spec:
      version: 1
      storageDriverName: ontap-san
      managementLIF: {{ management_lif_fqdn }}
      backendName: netapp-nvme-backend
      sanType: nvme
      svm: {{ svm_name }}
      credentials:
        name: netappsvm-secret
    ```

    ```bash
    oc apply -f netapp-nvme-backend.yaml
    ```

    ### StorageClass

    ```yaml
    apiVersion: storage.k8s.io/v1
    kind: StorageClass
    metadata:
      name: basic-netapp-nvme
    provisioner: csi.trident.netapp.io
    parameters:
      storagePools: "netapp-nvme-backend:.*"
      fsType: "ext4"
      backendType: "ontap-san"
    mountOptions:
      - discard
    allowVolumeExpansion: true
    ```

    ```bash
    oc apply -f basic-netapp-nvme-sc.yaml
    ```

=== "Fibre Channel"

    ### TridentBackendConfig

    ```yaml
    apiVersion: trident.netapp.io/v1
    kind: TridentBackendConfig
    metadata:
      name: netapp-fcp-backend
      namespace: trident
    spec:
      version: 1
      storageDriverName: ontap-san
      managementLIF: {{ management_lif_fqdn }}
      backendName: netapp-fcp-backend
      sanType: fcp
      svm: {{ svm_name }}
      credentials:
        name: netappsvm-secret
    ```

    ```bash
    oc apply -f netapp-fcp-backend.yaml
    ```

    ### StorageClass

    ```yaml
    apiVersion: storage.k8s.io/v1
    kind: StorageClass
    metadata:
      name: basic-netapp-fcp
    provisioner: csi.trident.netapp.io
    parameters:
      storagePools: "netapp-fcp-backend:.*"
      fsType: "ext4"
      backendType: "ontap-san"
    mountOptions:
      - discard
    allowVolumeExpansion: true
    ```

    ```bash
    oc apply -f basic-netapp-fcp-sc.yaml
    ```

## Verify Backends

```bash
oc get tridentbackendconfig -n trident
oc get tridentbackend -n trident
oc get sc
```

All backends should show `Bound` status.

## VolumeSnapshotClass

Create a single VolumeSnapshotClass for the cluster. Install the [CSI snapshot controller](https://docs.netapp.com/us-en/trident/trident-use/vol-snapshots.html) first if it is not already present.

```yaml
apiVersion: snapshot.storage.k8s.io/v1
kind: VolumeSnapshotClass
metadata:
  name: trident-csi-snapclass
driver: csi.trident.netapp.io
deletionPolicy: Delete
```

```bash
oc apply -f trident-csi-snapclass.yaml
```

## OpenShift Virtualization (KubeVirt) Configuration

If you are using block-based storage classes (iSCSI, NVMe, or Fibre Channel) with [OpenShift Virtualization](../virtualization.md), additional configuration is required.

### Mark the StorageClass as the Default for Virtualization

Add the KubeVirt default annotation to your block StorageClass:

```bash
oc patch storageclass {{ storage_class_name }} -p \
  '{"metadata":{"annotations":{"storageclass.kubevirt.io/is-default-virt-class":"true"}}}'
```

### Create a StorageProfile

Create a StorageProfile that configures block volume mode with ReadWriteMany access (required for live migration):

```yaml
apiVersion: cdi.kubevirt.io/v1beta1
kind: StorageProfile
metadata:
  name: {{ storage_class_name }}
spec:
  claimPropertySets:
    - accessModes:
        - ReadWriteMany
      volumeMode: Block
  cloneStrategy: snapshot
```

```bash
oc apply -f storageprofile.yaml
```

!!! tip
    Set `filesystemOverhead` to at least 10% to avoid potential space issues. The extra space has no real cost since NetApp is thin-provisioned.

    ```yaml
    spec:
      claimPropertySets:
        - accessModes:
            - ReadWriteMany
          volumeMode: Block
      filesystemOverhead:
        global: "0.1"
    ```

## Set as Default StorageClass

If this is the primary storage for the cluster:

```bash
oc patch storageclass {{ storage_class_name }} -p \
  '{"metadata":{"annotations":{"storageclass.kubernetes.io/is-default-class":"true"}}}'
```
