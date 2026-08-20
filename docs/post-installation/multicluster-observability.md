# MultiCluster Observability

[Red Hat ACM Observability Documentation](https://docs.redhat.com/en/documentation/red_hat_advanced_cluster_management_for_kubernetes/latest/html/observability/index)

MultiCluster Observability provides centralized monitoring and metrics collection across all managed clusters. Thanos stores historical metrics in S3-compatible object storage on the hub cluster. Block storage (a StorageClass) is also required for Thanos component PVCs.

!!! note
    The install example uses [OpenShift Data Foundation](storage/odf.md) (ODF) NooBaa for object storage via an `ObjectBucketClaim`. If your storage provider does not offer object storage, deploy [MinIO](#using-minio) as an S3-compatible stand-in.

    Hub block storage must still be configured before installing MultiCluster Observability. See [Hub Storage](../fleet-management/hub-storage.md).

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

## Configure Object Storage

Thanos requires a dedicated S3-compatible bucket. Use ODF if it is installed on the hub. Use MinIO only when the storage provider does not provide object storage.

### Using OpenShift Data Foundation

This example uses ODF NooBaa. The `ObjectBucketClaim` storage class `openshift-storage.noobaa.io` and the in-cluster endpoint `s3.openshift-storage.svc:443` are provided by ODF. ODF must already be installed. See [Hub Storage](../fleet-management/hub-storage.md) on a SNO hub, or [OpenShift Data Foundation](storage/odf.md) on a full cluster.

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

### Using MinIO

Use this section when the storage provider does not offer S3-compatible object storage (for example NetApp ONTAP without StorageGRID, or a cluster with only block/file CSI).

!!! warning "POC only"
    In-cluster MinIO is a stand-in for object storage during a POC. Prefer ODF, NetApp StorageGRID, or another vendor-supported S3 endpoint for production. This deployment is a single replica and is not highly available.

This pattern matches the [ACM Multicluster Observability Operator MinIO example](https://github.com/stolostron/multicluster-observability-operator/tree/main/examples/minio). Complete the [Install](#install) namespace and pull-secret step first, then deploy MinIO instead of the ODF ObjectBucketClaim.

2. Create a PVC for MinIO data. Set `storageClassName` to a StorageClass that already exists on the hub (the same class you will use for Thanos PVCs):

  ```yaml
  apiVersion: v1
  kind: PersistentVolumeClaim
  metadata:
    name: minio
    namespace: open-cluster-management-observability
    labels:
      app.kubernetes.io/name: minio
  spec:
    accessModes:
      - ReadWriteOnce
    storageClassName: {{ storage_class_name }}
    resources:
      requests:
        storage: 100Gi
  ```

  ```bash
  oc apply -f minio-pvc.yaml
  ```

3. Deploy MinIO. The startup command creates a `thanos` bucket directory before serving S3:

  ```yaml
  apiVersion: apps/v1
  kind: Deployment
  metadata:
    name: minio
    namespace: open-cluster-management-observability
    labels:
      app.kubernetes.io/name: minio
  spec:
    replicas: 1
    selector:
      matchLabels:
        app.kubernetes.io/name: minio
    strategy:
      type: Recreate
    template:
      metadata:
        labels:
          app.kubernetes.io/name: minio
      spec:
        containers:
          - name: minio
            image: quay.io/minio/minio:RELEASE.2025-09-07T16-13-09Z
            command:
              - /bin/sh
              - -c
              - mkdir -p /storage/thanos && /usr/bin/minio server /storage
            env:
              - name: MINIO_ROOT_USER
                value: minio
              - name: MINIO_ROOT_PASSWORD
                value: minio123
            ports:
              - containerPort: 9000
                protocol: TCP
            volumeMounts:
              - name: storage
                mountPath: /storage
            readinessProbe:
              httpGet:
                path: /minio/health/ready
                port: 9000
              initialDelaySeconds: 10
              periodSeconds: 5
            livenessProbe:
              httpGet:
                path: /minio/health/live
                port: 9000
              initialDelaySeconds: 15
              periodSeconds: 10
        volumes:
          - name: storage
            persistentVolumeClaim:
              claimName: minio
  ---
  apiVersion: v1
  kind: Service
  metadata:
    name: minio
    namespace: open-cluster-management-observability
  spec:
    type: ClusterIP
    selector:
      app.kubernetes.io/name: minio
    ports:
      - name: api
        port: 9000
        protocol: TCP
        targetPort: 9000
  ```

  ```bash
  oc apply -f minio.yaml
  oc rollout status deployment/minio -n open-cluster-management-observability --timeout=120s
  ```

!!! note
    Change `MINIO_ROOT_USER` and `MINIO_ROOT_PASSWORD` before applying if you do not want the demo credentials. The Thanos secret in the next step must use the same values.

4. Create the Thanos object storage secret pointing at the in-cluster MinIO service. The endpoint has no protocol, and `insecure: true` is required because this MinIO instance serves HTTP:

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
        bucket: thanos
        endpoint: minio.open-cluster-management-observability.svc:9000
        insecure: true
        access_key: minio
        secret_key: minio123
  ```

  ```bash
  oc apply -f thanos-secret.yaml
  ```

Continue with [Create the MultiClusterObservability instance](#create-the-multiclusterobservability-instance).

## Create the MultiClusterObservability instance

`storageConfig.storageClass` is the block StorageClass for Thanos component PVCs (`alertmanager`, `compact`, `receive`, `rule`, `store`). It is independent of whether object storage is ODF or MinIO. Change `lvms-local-storage` if that is not the StorageClass on your hub.

5. Create the MultiClusterObservability instance:

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

6. Watch it deploy:

  ```bash
  oc get multiclusterobservability -w
  ```

The status should report that observability components are deployed and running.

## Verify

```bash
oc get pods -n open-cluster-management-observability
oc get route -n open-cluster-management-observability
```

If you deployed MinIO, confirm it is ready and that Thanos can reach it:

```bash
oc get pvc,deployment,svc minio -n open-cluster-management-observability
oc get secret thanos-object-storage -n open-cluster-management-observability
```
