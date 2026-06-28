# Hub Storage

[OpenShift Data Foundation Documentation](https://docs.redhat.com/en/documentation/red_hat_openshift_data_foundation/latest)

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

## Install OpenShift Data Foundation

ODF is used here specifically for object storage required by MultiClusterObservability.

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

## Install MultiClusterObservability

Storage must be configured first (above).

1. Create the namespace and pull secret:

  ```bash
  oc create namespace open-cluster-management-observability
  DOCKER_CONFIG_JSON=$(oc extract secret/pull-secret -n openshift-config --to=-)
  oc create secret generic multiclusterhub-operator-pull-secret \
      -n open-cluster-management-observability \
      --from-literal=.dockerconfigjson="$DOCKER_CONFIG_JSON" \
      --type=kubernetes.io/dockerconfigjson
  ```

2. Create the object bucket:

  ```yaml
  apiVersion: objectbucket.io/v1alpha1
  kind: ObjectBucketClaim
  metadata:
    name: thanos-object-storage-obc
    namespace: open-cluster-management-observability
  spec:
    bucketName: thanos-object-storage-bucket
    storageClassName: openshift-storage.noobaa.io
  ```

3. Configure the Thanos secret:

  ```bash
  ACCESS_KEY=$(oc get secret thanos-object-storage-obc -n open-cluster-management-observability -o jsonpath='{.data.AWS_ACCESS_KEY_ID}' | base64 -d)
  SECRET_KEY=$(oc get secret thanos-object-storage-obc -n open-cluster-management-observability -o jsonpath='{.data.AWS_SECRET_ACCESS_KEY}' | base64 -d)
  ```

  ```yaml
  apiVersion: v1
  kind: Secret
  metadata:
    name: thanos-object-storage
    namespace: open-cluster-management-observability
  type: Opaque
  stringData:
    thanos.yaml: |
      type: s3
      config:
        bucket: thanos-object-storage-bucket
        endpoint: s3.openshift-storage.svc:443
        insecure: false
        access_key: $ACCESS_KEY
        secret_key: $SECRET_KEY
  ```

4. Create the MultiClusterObservability instance:

  ```yaml
  apiVersion: observability.open-cluster-management.io/v1beta2
  kind: MultiClusterObservability
  metadata:
    name: multi-cluster-observability
  spec:
    enableDownsampling: true
    imagePullPolicy: Always
    imagePullSecret: multiclusterhub-operator-pull-secret
    observabilityAddonSpec:
      enableMetrics: true
      interval: 300
    storageConfig:
      alertmanagerStorageSize: 1Gi
      compactStorageSize: 100Gi
      metricObjectStorage:
        key: thanos.yaml
        name: thanos-object-storage
      receiveStorageSize: 100Gi
      ruleStorageSize: 1Gi
      storageClass: lvms-local-storage
      storeStorageSize: 10Gi
  ```

5. Watch it deploy:

  ```bash
  oc get multiclusterobservability -w
  ```
