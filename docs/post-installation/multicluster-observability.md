# MultiCluster Observability

[Red Hat ACM Observability Documentation](https://docs.redhat.com/en/documentation/red_hat_advanced_cluster_management_for_kubernetes/latest/html/observability/index)

MultiCluster Observability provides centralized monitoring and metrics collection across all managed clusters. It requires object storage on the hub cluster.

!!! note
    Hub storage (ODF or LVM with NooBaa) must be configured before installing MultiCluster Observability. See [Hub Storage](../fleet-management/hub-storage.md).

## Install

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

  ```bash
  oc apply -f thanos-obc.yaml
  ```

3. Wait for the bucket to be bound and then configure the Thanos secret:

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

  ```bash
  oc apply -f thanos-secret.yaml
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

  ```bash
  oc apply -f multiclusterobservability.yaml
  ```

5. Watch it deploy:

  ```bash
  oc get multiclusterobservability -w
  ```

## Verify

```bash
oc get pods -n open-cluster-management-observability
oc get route -n open-cluster-management-observability
```
