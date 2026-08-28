# VMware

[VMware vSphere CSI Driver Operator Official Documentation](https://docs.redhat.com/en/documentation/openshift_container_platform/latest/html/storage/using-container-storage-interface-csi#persistent-storage-vsphere)  
[Assisted Installer vSphere Post-Install Configuration](https://docs.redhat.com/en/documentation/assisted_installer_for_openshift_container_platform/2026/html/installing_openshift_container_platform_with_the_assisted_installer/installing-on-vsphere)

!!! important "Use the Official Documentation"
    Always refer to the official vendor documentation for the latest installation and configuration guidance. The examples below are field notes from POC engagements and may not reflect the most current driver versions or recommended settings.

# VMware vSphere CSI

When OpenShift is installed on vSphere with `platform: vsphere`, the **vSphere CSI Driver Operator** and CSI driver are installed automatically in the `openshift-cluster-csi-drivers` namespace. A default StorageClass called `thin-csi` is created and ready to use.

!!! warning "vSphere platform integration required"
    The vSphere CSI Driver Operator is **only supported on clusters deployed with `platform: vsphere`**. The cluster nodes must be VMs running inside vSphere — the driver provisions VMDKs that attach directly to VMs. **Bare metal clusters cannot use this driver.** For bare metal clusters, use your storage vendor's CSI driver instead (see [Storage](./index.md)).

!!! info "Assisted Installer"
    When using the [Assisted Installer](../../install-the-cluster/assisted-installer.md), you must select **vSphere** as the platform integration during cluster creation (not "No platform integration"). After installation completes, you must then manually configure the vSphere connection as described in the [Configure vSphere Connection](#configure-vsphere-connection) section below. The CSI driver will not become operational until this post-install configuration is finished.

## Requirements

- VMware vSphere 8.0 Update 1 or later, VMware vSphere Foundation (VVF) 9, or VMware Cloud Foundation (VCF) 5 or later
- vCenter 8.0 Update 1 or later, VVF 9, or VCF 5 or later
- Virtual machine hardware version 15 or later
- `disk.EnableUUID` set to `TRUE` on all cluster VMs
- No third-party vSphere CSI driver present in the cluster

!!! warning "Third-party CSI drivers"
    If a third-party vSphere CSI driver is already installed, OpenShift will not overwrite it and upgrades will be blocked. See the [official documentation](https://docs.redhat.com/en/documentation/openshift_container_platform/latest/html/storage/using-container-storage-interface-csi#persistent-storage-csi-vsphere-remove-third-party) for removal instructions.

## Configure vSphere Connection

When using the Assisted Installer with vSphere platform integration, the cluster installs successfully but the vSphere connection details are not yet configured. You must complete this step before the CSI driver can provision storage.

!!! note
    If you installed using VMware vSphere IPI, this connection is already configured — skip to [Verify the Driver](#verify-the-driver).

### Option 1: Web Console (Recommended)

1. In the **Administrator** perspective, navigate to **Home > Overview**
2. Under **Status**, click **vSphere connection** to open the configuration wizard
3. Fill in the following fields:

    | Field                  | Value                                                                   |
    | ---------------------- | ----------------------------------------------------------------------- |
    | vCenter                | vCenter server FQDN or IP (e.g., `vcenter.example.com`)                 |
    | Username               | vCenter service account username                                        |
    | Password               | vCenter service account password                                        |
    | Datacenter             | vSphere datacenter name (e.g., `SDDC-Datacenter`)                       |
    | Default data store     | Full datastore path (e.g., `/SDDC-Datacenter/datastore/vsanDatastore`)  |
    | Virtual Machine Folder | Folder containing cluster VMs (e.g., `/SDDC-Datacenter/vm/ocp-cluster`) |
    | vCenter cluster        | vSphere cluster where OpenShift is installed                            |

4. Click **Save Configuration**

!!! warning
    An incorrect username or password will make cluster nodes unschedulable. The credentials are stored in the `vsphere-creds` secret in the `kube-system` namespace.

### Option 2: CLI

1. Generate base64-encoded credentials:

    ```bash
    VCENTER_USER_B64=$(echo -n "{{ vcenter_username }}" | base64 -w0)
    VCENTER_PASS_B64=$(echo -n "{{ vcenter_password }}" | base64 -w0)
    ```

2. Back up the secret, then copy it to a working file you will edit:

    ```bash
    oc get secret vsphere-creds -o yaml -n kube-system > vsphere-creds-backup.yaml
    cp vsphere-creds-backup.yaml vsphere-creds.yaml
    ```

    Edit `vsphere-creds.yaml` to set your encoded credentials:

    ```yaml
    apiVersion: v1
    data:
      {{ vcenter_address }}.username: {{ base64_encoded_username }}
      {{ vcenter_address }}.password: {{ base64_encoded_password }}
    kind: Secret
    metadata:
      annotations:
        cloudcredential.openshift.io/mode: passthrough
      name: vsphere-creds
      namespace: kube-system
    type: Opaque
    ```

    ```bash
    oc replace -f vsphere-creds.yaml
    ```

3. Redeploy the kube-controller-manager:

    ```bash
    oc patch kubecontrollermanager cluster \
      -p='{"spec": {"forceRedeploymentReason": "recovery-'"$( date --rfc-3339=ns )"'"}}' \
      --type=merge
    ```

4. Back up and update the cloud provider config:

    ```bash
    oc get cm cloud-provider-config -o yaml -n openshift-config > cloud-provider-config-backup.yaml
    cp cloud-provider-config-backup.yaml cloud-provider-config.yaml
    ```

    Edit `cloud-provider-config.yaml`:

    ```yaml
    apiVersion: v1
    data:
      config: |
        global:
          insecureFlag: true
          secretName: vsphere-creds
          secretNamespace: kube-system
        vcenter:
          {{ vcenter_address }}:
            server: "{{ vcenter_address }}"
            port: 443
            insecureFlag: true
            datacenters:
            - {{ datacenter }}
    kind: ConfigMap
    metadata:
      name: cloud-provider-config
      namespace: openshift-config
    ```

    ```bash
    oc apply -f cloud-provider-config.yaml
    ```

5. Taint all nodes to trigger cloud provider initialization:

    ```bash
    for NODE in $(oc get nodes -o name); do
      oc adm taint node ${NODE##*/} \
        node.cloudprovider.kubernetes.io/uninitialized=true:NoSchedule
    done
    ```

6. Update the infrastructure object with your vSphere topology:

    ```bash
    oc get infrastructure cluster -o yaml > infra-backup.yaml
    cp infra-backup.yaml infra.yaml
    ```

    Edit `spec.platformSpec` in `infra.yaml` to include your vSphere details (vcenters, failureDomains, topology), then apply:

    ```bash
    oc apply -f infra.yaml
    ```

### Wait for Configuration to Complete

The configuration process updates operator statuses and triggers control plane node reboots. It takes approximately one hour to complete.

```bash
oc get co
```

Wait for all cluster operators to show `Available=True` and `Progressing=False`.

## Verify the Driver

After the vSphere connection is configured, confirm the driver is running and the default StorageClass exists:

```bash
oc get pods -n openshift-cluster-csi-drivers -l app=vsphere-csi-driver
oc get csidrivers
oc get storageclass
```

You should see a `thin-csi` StorageClass backed by `csi.vsphere.vmware.com`.

## Default StorageClass

The vSphere CSI Driver Operator automatically creates the `thin-csi` StorageClass using a vSphere storage policy that targets the datastore configured during installation:

```yaml
kind: StorageClass
apiVersion: storage.k8s.io/v1
metadata:
  name: thin-csi
provisioner: csi.vsphere.vmware.com
parameters:
  StoragePolicyName: "$openshift-storage-policy-xxxx"
volumeBindingMode: WaitForFirstConsumer
allowVolumeExpansion: false
reclaimPolicy: Delete
```

### Set as Default StorageClass

If `thin-csi` is not already the default, or if you have created a custom StorageClass you'd prefer as default:

```bash
oc patch storageclass thin-csi -p '{"metadata":{"annotations":{"storageclass.kubernetes.io/is-default-class":"true"}}}'
```

## Custom StorageClass

To target a specific vSphere storage policy or datastore, create a custom StorageClass:

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: vsphere-custom
provisioner: csi.vsphere.vmware.com
parameters:
  StoragePolicyName: "<your-vsphere-storage-policy>"
volumeBindingMode: WaitForFirstConsumer
allowVolumeExpansion: true
reclaimPolicy: Delete
```

The `StoragePolicyName` must match a storage policy defined in vCenter. You can create storage policies in vCenter under **Policies and Profiles > VM Storage Policies**.

## Volume Expansion

Online volume expansion is supported on vSphere 8.0 Update 1 and later. To enable it, set `allowVolumeExpansion: true` on your StorageClass (it is `false` by default on `thin-csi`).

```bash
oc patch storageclass thin-csi -p '{"allowVolumeExpansion": true}'
```

Then expand a PVC by editing its requested storage size:

```bash
oc patch pvc <pvc-name> -p '{"spec":{"resources":{"requests":{"storage":"10Gi"}}}}'
```

## ReadWriteMany (RWX) Volumes

If your vSphere environment has the **vSAN file service** configured, the vSphere CSI driver supports RWX volumes. Without vSAN file service, only ReadWriteOnce (RWO) is available.

To request an RWX volume:

```yaml
kind: PersistentVolumeClaim
apiVersion: v1
metadata:
  name: shared-data
spec:
  resources:
    requests:
      storage: 1Gi
  accessModes:
    - ReadWriteMany
  storageClassName: thin-csi
```

!!! note
    If vSAN file service is not configured and you request RWX, the volume will fail to provision. Confirm with your VMware administrator that vSAN file service is enabled before requesting RWX volumes.

## Volume Snapshots

The vSphere CSI driver supports volume snapshots on vSphere 8.0 Update 1 or later. The default maximum is 3 snapshots per volume, configurable up to 32.

### Create a VolumeSnapshotClass

```yaml
apiVersion: snapshot.storage.k8s.io/v1
kind: VolumeSnapshotClass
metadata:
  name: vsphere-snapclass
driver: csi.vsphere.vmware.com
deletionPolicy: Delete
```

```bash
oc apply -f volumesnapshotclass.yaml
```

### Take a Snapshot

```yaml
apiVersion: snapshot.storage.k8s.io/v1
kind: VolumeSnapshot
metadata:
  name: my-snap
spec:
  volumeSnapshotClassName: vsphere-snapclass
  source:
    persistentVolumeClaimName: <pvc-name>
```

!!! warning "Quiesce before snapshotting"
    Delete the pod using the PVC before creating a snapshot to ensure all data is flushed to disk. Snapshotting a PVC in active use may exclude unwritten or cached data.

### Change Maximum Snapshots Per Volume

```bash
oc patch clustercsidriver/csi.vsphere.vmware.com --type=merge \
  -p '{"spec":{"driverConfig":{"vSphere":{"globalMaxSnapshotsPerBlockVolume": 10}}}}'
```

For granular control per storage type:

```bash
# vSAN volumes
oc patch clustercsidriver/csi.vsphere.vmware.com --type=merge \
  -p '{"spec":{"driverConfig":{"vSphere":{"granularMaxSnapshotsPerBlockVolumeInVSAN": 7}}}}'

# vVOL volumes
oc patch clustercsidriver/csi.vsphere.vmware.com --type=merge \
  -p '{"spec":{"driverConfig":{"vSphere":{"granularMaxSnapshotsPerBlockVolumeInVVOL": 5}}}}'
```

!!! tip
    VMware recommends keeping snapshots at 2-3 per volume for optimal performance. Only increase the limit if your use case requires it.

## Persistent Disk Encryption

You can encrypt dynamically provisioned PVs on vSphere. VMs must be encrypted first (either during or after installation), then you create a StorageClass that references an encryption-enabled storage policy.

### Using Tag-Based Placement (Recommended)

1. In vCenter, create a category for tagging datastores (ensure `StoragePod`, `Datastore`, and `Folder` are selected as Associable Entities)
2. Create a tag using that category and assign it to each target datastore
3. Create a VM Storage Policy under **Policies and Profiles > VM Storage Policies**:
    - Enable **host based rules** and **tag based placement rules**
    - Select **Encryption and Default Encryption Properties**
    - Select the tag category and tag from step 1-2
4. Create a StorageClass referencing the policy:

```yaml
kind: StorageClass
apiVersion: storage.k8s.io/v1
metadata:
  name: csi-encrypted
provisioner: csi.vsphere.vmware.com
reclaimPolicy: Delete
volumeBindingMode: WaitForFirstConsumer
parameters:
  storagePolicyName: "<encryption-storage-policy-name>"
```

!!! note
    RWX encrypted PVs are not supported. You cannot request RWX PVs from an encrypted StorageClass.

## Topology-Aware Provisioning

For multi-zone or multi-datacenter deployments, vSphere CSI supports topology-aware provisioning. This ensures PVs are created in datastores accessible to the zone where the pod is scheduled.

### Post-Installation Setup

1. In vCenter, create `openshift-region` and `openshift-zone` tag categories
2. Create tags for each region/zone and assign them to the appropriate compute clusters or datacenters
3. Create a datastore tag category (e.g., `openshift-zonal-datastore-cat`) and tag datastores in each zone
4. Create a VM Storage Policy using tag-based placement rules targeting the zonal datastore tag
5. Create a topology-aware StorageClass:

```yaml
kind: StorageClass
apiVersion: storage.k8s.io/v1
metadata:
  name: zoned-sc
provisioner: csi.vsphere.vmware.com
parameters:
  StoragePolicyName: "<zoned-storage-policy>"
reclaimPolicy: Delete
allowVolumeExpansion: true
volumeBindingMode: WaitForFirstConsumer
```

6. Define failure domains in the OpenShift infrastructure object (see [Specifying multiple regions and zones](https://docs.redhat.com/en/documentation/openshift_container_platform/latest/html/installing_on_vmware_vsphere/installer-provisioned-infrastructure#specifying-regions-zones-infrastructure-vsphere_ipi-vsphere-ipi))

### Verify Topology

```bash
oc get csinode
oc get csinode <node-name> -o yaml
```

Topology keys (`topology.csi.vmware.com/openshift-zone` and `topology.csi.vmware.com/openshift-region`) should appear in the CSINode spec.

## Test Dynamic Provisioning

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: test-vsphere-pvc
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 1Gi
  storageClassName: thin-csi
```

```bash
oc apply -f test-pvc.yaml
oc get pvc test-vsphere-pvc -w
```

The PVC should transition to `Bound` within a minute. Clean up with:

```bash
oc delete pvc test-vsphere-pvc
```

## Supported Features

| Feature                     | Supported | Notes                                      |
| --------------------------- | --------- | ------------------------------------------ |
| Dynamic provisioning        | Yes       |                                            |
| Volume expansion            | Yes       | vSphere 8.0 Update 1+ for online expansion |
| Volume snapshots            | Yes       | vSphere 8.0 Update 1+ required             |
| ReadWriteOnce (RWO)         | Yes       |                                            |
| ReadWriteMany (RWX)         | Yes       | Requires vSAN file service                 |
| Disk encryption             | Yes       | RWX encrypted PVs not supported            |
| Topology-aware provisioning | Yes       |                                            |
| CSI migration (in-tree)     | Yes       | Automatic                                  |
