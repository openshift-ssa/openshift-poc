# Hub Storage

[OpenShift Storage - Persistent Storage using LVMS](https://docs.redhat.com/en/documentation/openshift_container_platform/4.22/html/storage/persistent-storage-using-local-storage#persistent-storage-using-lvms)

After installing the SNO hub cluster, configure storage before installing ACM. These examples are for environments without existing external storage on the hub node.

## Install LVM Storage Operator

1. Go to Ecosystem -> Software Catalog -> filter for "LVM Storage" -> click the tile
2. Click Install
3. Leave all the defaults and click Install
4. Wait for the Operator to install

Label the node as a storage node:

```bash
oc label node {{ node_name }} cluster.ocs.openshift.io/openshift-storage=
```

## Create LVM Storage

1. Go to Ecosystem -> Installed Operators -> click "LVM Storage"
2. Click on the "LVMCluster" tab and then click "Create LVMCluster"
3. Switch to YAML view and update the path for your data disk:

  ```yaml
  apiVersion: lvm.topolvm.io/v1alpha1
  kind: LVMCluster
  metadata:
    name: local-storage-lvm-cluster
    namespace: openshift-storage
  spec:
    storage:
      deviceClasses:
        - name: local-storage
          default: true
          fstype: xfs
          deviceSelector:
            paths:
              - /dev/nvme0n1
          thinPoolConfig:
            name: thin-pool-1
            sizePercent: 90
            overprovisionRatio: 10
            chunkSizeCalculationPolicy: Static
            metadataSizeCalculationPolicy: Host
  ```

4. Click Create

## OPTIONAL - Install OpenShift Data Foundation - Object Storage

[OpenShift Data Foundation Documentation](https://docs.redhat.com/en/documentation/red_hat_openshift_data_foundation/latest)

This is only needed if you are planning to use ODF as part of your OPP subscription. ODF is used here specifically for object storage required by MultiClusterObservability. 

1. Go to Ecosystem -> Software Catalog -> filter for "OpenShift Data Foundation" -> click the tile
2. Click Install
3. Leave all the defaults and click Install
4. Wait for the Operator to install
5. Go to Ecosystem -> Installed Operators -> click "OpenShift Data Foundation"
6. Click on the "StorageCluster" tab and then click "Create StorageCluster"
7. Switch to YAML view and paste:

  ```yaml
  apiVersion: ocs.openshift.io/v1
  kind: StorageCluster
  metadata:
    name: mcog-storagecluster
    namespace: openshift-storage
  spec:
    arbiter: {}
    encryption:
      keyRotation:
        schedule: '@weekly'
      kms: {}
    externalStorage: {}
    managedResources:
      cephObjectStoreUsers: {}
      cephCluster: {}
      cephBlockPools: {}
      cephNonResilientPools: {}
      cephObjectStores: {}
      cephFilesystems: {}
      cephRBDMirror: {}
      cephToolbox: {}
      cephDashboard: {}
      cephConfig: {}
    multiCloudGateway:
      dbStorageClassName: lvms-local-storage
      reconcileStrategy: standalone
    resourceProfile: balanced
  ```

8. Click Create

## Verify

```bash
oc get lvmcluster -n openshift-storage
oc get storagecluster -n openshift-storage
oc get storageclass
oc get pods -n openshift-storage
```

Ensure the LVM StorageClass is set as default:

```bash
oc get storageclass | grep default
```