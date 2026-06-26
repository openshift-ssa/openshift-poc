# Hub Storage

After installing the SNO hub cluster, configure storage before installing ACM. These examples are for environments without existing external storage on the hub node.

## Install Storage Operators

Install via the OperatorHub in the OpenShift web console:

- LVM Storage Operator
- OpenShift Data Foundation (ODF) Operator

Label the node as a storage node:

```bash
oc label node <node-name> cluster.ocs.openshift.io/openshift-storage=
```

## Create LVM Storage

Change the path for your data disk:

```bash
cat <<EOF | oc apply -f -
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
EOF
```

## Create ODF StorageCluster for Object Storage

ODF is used here specifically for object storage required by MultiClusterObservability:

```bash
cat <<EOF | oc apply -f -
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
EOF
```

## Install MultiClusterObservability

Storage must be configured first (above).

```bash
oc create namespace open-cluster-management-observability
DOCKER_CONFIG_JSON=$(oc extract secret/pull-secret -n openshift-config --to=-)
oc create secret generic multiclusterhub-operator-pull-secret \
    -n open-cluster-management-observability \
    --from-literal=.dockerconfigjson="$DOCKER_CONFIG_JSON" \
    --type=kubernetes.io/dockerconfigjson
```

Create the object bucket:

```bash
cat <<EOF | oc apply -f -
apiVersion: objectbucket.io/v1alpha1
kind: ObjectBucketClaim
metadata:
  name: thanos-object-storage-obc
  namespace: open-cluster-management-observability
spec:
  bucketName: thanos-object-storage-bucket
  storageClassName: openshift-storage.noobaa.io
EOF
```

Configure the Thanos secret:

```bash
ACCESS_KEY=$(oc get secret thanos-object-storage-obc -n open-cluster-management-observability -o jsonpath='{.data.AWS_ACCESS_KEY_ID}' | base64 -d)
SECRET_KEY=$(oc get secret thanos-object-storage-obc -n open-cluster-management-observability -o jsonpath='{.data.AWS_SECRET_ACCESS_KEY}' | base64 -d)

cat <<EOF | oc apply -f -
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
EOF
```

Create the MultiClusterObservability instance:

```bash
cat <<EOF | oc apply -f -
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
EOF
```
