# OpenShift Logging

[Red Hat OpenShift Logging Documentation](https://docs.redhat.com/en/documentation/red_hat_openshift_logging/6.5/html-single/installing_logging/index)

OpenShift Logging provides centralized log collection, storage, and querying for application, infrastructure, and audit logs. The stack consists of three operators:

| Operator                           | Namespace                                    | Purpose                                                     |
| ---------------------------------- | -------------------------------------------- | ----------------------------------------------------------- |
| Loki Operator                      | `openshift-operators-redhat`               | Manages the LokiStack log store (receives, indexes, stores) |
| Red Hat OpenShift Logging Operator | `openshift-logging`                        | Manages log collection and forwarding (Vector collector)    |
| Cluster Observability Operator     | `openshift-cluster-observability-operator` | Adds Logs tab to the web console (optional)                 |

!!! info
    The Loki Operator and the Red Hat OpenShift Logging Operator must use the same major and minor version (e.g., both on `stable-6.5`).

## Prerequisites

- Cluster administrator privileges
- A StorageClass available for LokiStack internal PVCs (block storage)
- S3-compatible object storage for log data (ODF NooBaa, NetApp StorageGRID, AWS S3, etc.)
- Storage configured on the cluster (CSI driver installed)

!!! warning "LokiStack Requires Two Types of Storage"
    - **Block storage** (via StorageClass): For internal PVCs that store the write-ahead log (WAL), index cache, and compactor working space
    - **Object storage** (S3-compatible): For the actual log data chunks and indices

    Missing either storage type causes silent deployment failures where the LokiStack shows`Ready` but logs are not collected or stored.

## Deployment Sizing

Choose an initial size based on your cluster. You can resize after deployment based on observed log volume.

| Size               | Data Transfer | Queries/sec | Total CPU | Total Memory | Total Disk |
| ------------------ | ------------- | ----------- | --------- | ------------ | ---------- |
| `1x.demo`        | Demo only     | Demo only   | Minimal   | Minimal      | 40 Gi      |
| `1x.extra-small` | 100 GB/day    | 1-25 QPS    | 14 vCPUs  | 31 Gi        | 430 Gi     |
| `1x.small`       | 500 GB/day    | 25-50 QPS   | 34 vCPUs  | 67 Gi        | 430 Gi     |
| `1x.medium`      | 2 TB/day      | 25-75 QPS   | 54 vCPUs  | 139 Gi       | 590 Gi     |

!!! tip
    For a POC environment, `1x.extra-small` or `1x.small` is typically sufficient.

## Install the Loki Operator

The Loki Operator must be installed first, before the Logging Operator.

### Install via WebUI

1. Go to Ecosystem -> Software Catalog -> filter for "Loki Operator" -> click the "Loki Operator" tile (provided by Red Hat)
2. Click Install
3. Select `stable-6.5` as the Update channel
4. Ensure the namespace is `openshift-operators-redhat` (this should be pre-selected)
5. Select "Enable Operator-recommended cluster monitoring on this namespace"
6. Click Install
7. Wait for the Operator to install

### Install via YAML

1. Create the namespace and operator group:

   ```yaml
   apiVersion: v1
   kind: Namespace
   metadata:
     name: openshift-operators-redhat
     annotations:
       openshift.io/node-selector: ""
     labels:
       openshift.io/cluster-monitoring: "true"
   ---
   apiVersion: operators.coreos.com/v1
   kind: OperatorGroup
   metadata:
     name: loki-operator
     namespace: openshift-operators-redhat
   spec:
     upgradeStrategy: Default
   ```

   ```bash
   oc apply -f loki-operator-ns.yaml
   ```
2. Create the subscription:

   ```yaml
   apiVersion: operators.coreos.com/v1alpha1
   kind: Subscription
   metadata:
     name: loki-operator
     namespace: openshift-operators-redhat
   spec:
     channel: stable-6.5
     installPlanApproval: Automatic
     name: loki-operator
     source: redhat-operators
     sourceNamespace: openshift-marketplace
   ```

   ```bash
   oc apply -f loki-operator-sub.yaml
   ```
3. Wait for the operator:

   ```bash
   oc get csv -n openshift-operators-redhat -w
   ```

   The `PHASE` should show `Succeeded`.

## Configure Object Storage

LokiStack requires an S3-compatible object storage secret. The secret must be named `logging-loki-s3` and created in the `openshift-logging` namespace.

4. Create the `openshift-logging` namespace:

   ```bash
   oc create namespace openshift-logging
   ```

### Using ODF NooBaa

5. If you have ODF with NooBaa available, create an ObjectBucketClaim:

   ```yaml
   apiVersion: objectbucket.io/v1alpha1
   kind: ObjectBucketClaim
   metadata:
     name: loki-bucket
     namespace: openshift-logging
   spec:
     bucketName: loki-bucket
     storageClassName: openshift-storage.noobaa.io
   ```

   ```bash
   oc apply -f loki-bucket.yaml
   ```
6. Wait for the bucket to be bound, then create the secret:

   ```bash
   ACCESS_KEY=$(oc get secret loki-bucket -n openshift-logging -o jsonpath='{.data.AWS_ACCESS_KEY_ID}' | base64 -d)
   SECRET_KEY=$(oc get secret loki-bucket -n openshift-logging -o jsonpath='{.data.AWS_SECRET_ACCESS_KEY}' | base64 -d)

   oc create secret generic logging-loki-s3 \
     -n openshift-logging \
     --from-literal=bucketnames="loki-bucket" \
     --from-literal=endpoint="https://s3-openshift-storage.apps.{{ cluster_name }}.{{ base_domain }}" \
     --from-literal=access_key_id="$ACCESS_KEY" \
     --from-literal=access_key_secret="$SECRET_KEY"
   ```

### Using S3 Compatible Storage (NetApp StorageGRID, etc.)

5. Create the secret directly with your storage credentials:

   ```bash
   oc create secret generic logging-loki-s3 \
     -n openshift-logging \
     --from-literal=bucketnames="{{ bucket_name }}" \
     --from-literal=endpoint="{{ s3_endpoint_url }}" \
     --from-literal=access_key_id="{{ access_key }}" \
     --from-literal=access_key_secret="{{ secret_key }}" \
     --from-literal=forcepathstyle="true"
   ```

   !!! note
       The `forcepathstyle="true"` parameter is required for S3 Compatible storage (not needed for AWS S3).

### TLS CA Bundle (If Required)

6. If your object storage uses self-signed or internal certificates, create a ConfigMap with the CA bundle:

   ```bash
   oc create configmap loki-s3-ca-bundle \
     -n openshift-logging \
     --from-file=ca-bundle.crt=./storage-ca.crt
   ```

   You will reference this in the LokiStack CR under `spec.storage.tls`.

## Create the LokiStack

7. Create the LokiStack custom resource:

   ```yaml
   apiVersion: loki.grafana.com/v1
   kind: LokiStack
   metadata:
     name: logging-loki
     namespace: openshift-logging
   spec:
     size: 1x.extra-small
     storage:
       schemas:
         - version: v13
           effectiveDate: "2024-10-01"
       secret:
         name: logging-loki-s3
         type: s3
     storageClassName: {{ storage_class }}
     tenants:
       mode: openshift-logging
   ```

   !!! note "If using self-signed storage certificates"
       Add the TLS section to the LokiStack CR:

       ```yaml
       spec:
         storage:
           tls:
             caName: loki-s3-ca-bundle
       ```

   ```bash
   oc apply -f lokistack.yaml
   ```
8. Wait for the LokiStack to be ready:

   ```bash
   oc get lokistack logging-loki -n openshift-logging -w
   ```
9. Verify PVCs are bound:

   ```bash
   oc get pvc -n openshift-logging
   ```

   All PVCs should show `Bound`.

## Install the Red Hat OpenShift Logging Operator

### Install via WebUI

10. Go to Ecosystem -> Software Catalog -> filter for "Red Hat OpenShift Logging" -> click the tile
11. Click Install
12. Select `stable-6.5` as the Update channel
13. Ensure the namespace is `openshift-logging`
14. Select "Enable Operator-recommended cluster monitoring on this namespace"
15. Click Install
16. Wait for the Operator to install

### Install via YAML

10. Create the operator group and subscription:

    ```yaml
    apiVersion: operators.coreos.com/v1
    kind: OperatorGroup
    metadata:
      name: cluster-logging
      namespace: openshift-logging
    spec:
      upgradeStrategy: Default
    ---
    apiVersion: operators.coreos.com/v1alpha1
    kind: Subscription
    metadata:
      name: cluster-logging
      namespace: openshift-logging
    spec:
      channel: stable-6.5
      installPlanApproval: Automatic
      name: cluster-logging
      source: redhat-operators
      sourceNamespace: openshift-marketplace
    ```

    ```bash
    oc apply -f logging-operator.yaml
    ```
11. Wait for the operator:

    ```bash
    oc get csv -n openshift-logging -w
    ```

    The `PHASE` should show `Succeeded`.

## Create the Collector Service Account and RBAC

The log collector requires a service account with specific cluster roles to read container logs and write to the LokiStack.

12. Create the service account:

    ```bash
    oc create sa logging-collector -n openshift-logging
    ```
13. Assign the required cluster roles:

    ```bash
    oc adm policy add-cluster-role-to-user logging-collector-logs-writer \
      -z logging-collector -n openshift-logging

    oc adm policy add-cluster-role-to-user collect-application-logs \
      -z logging-collector -n openshift-logging

    oc adm policy add-cluster-role-to-user collect-infrastructure-logs \
      -z logging-collector -n openshift-logging
    ```

    Cluster Roles

    | Role                              | Purpose                              |
    | --------------------------------- | ------------------------------------ |
    | `logging-collector-logs-writer` | Allows writing logs to the LokiStack |
    | `collect-application-logs`      | Allows reading application logs      |
    | `collect-infrastructure-logs`   | Allows reading infrastructure logs   |
    | `collect-audit-logs`            | Allows reading audit logs (optional) |

    To also collect audit logs:


    ```bash
    oc adm policy add-cluster-role-to-user collect-audit-logs \
      -z logging-collector -n openshift-logging
    ```

!!! warning
    You must create the service account and grant the ClusterRoleBindings before creating the ClusterLogForwarder. Adding an input type to the CR without the required RBAC binding destroys the entire log collector DaemonSet.

## Create the ClusterLogForwarder

14. Create the ClusterLogForwarder to define how logs are collected and forwarded to the LokiStack:

    ```yaml
    apiVersion: observability.openshift.io/v1
    kind: ClusterLogForwarder
    metadata:
      name: instance
      namespace: openshift-logging
    spec:
      serviceAccount:
        name: logging-collector
      outputs:
        - name: lokistack-out
          type: lokiStack
          lokiStack:
            target:
              name: logging-loki
              namespace: openshift-logging
            authentication:
              token:
                from: serviceAccount
          tls:
            ca:
              key: service-ca.crt
              configMapName: openshift-service-ca.crt
      pipelines:
        - name: infra-app-logs
          inputRefs:
            - application
            - infrastructure
          outputRefs:
            - lokistack-out
    ```

    !!! warning "TLS CA Block is Required"
        The `tls.ca` block is required when forwarding logs to a LokiStack in the same cluster. The LokiStack gateway uses a TLS certificate signed by the cluster's service-serving CA. Without this block, collector pods fail with `certificate verify failed: self-signed certificate in certificate chain`.

    To also collect audit logs, add `audit` to `inputRefs`:

    ```yaml
    pipelines:
      - name: all-logs
        inputRefs:
          - application
          - infrastructure
          - audit
        outputRefs:
          - lokistack-out
    ```

    ```bash
    oc apply -f clusterlogforwarder.yaml
    ```

## Verify

15. Check that collector pods are running on all nodes:

    ```bash
    oc get pods -n openshift-logging -l component=collector
    ```

    You should see one collector pod per node in `Running` state.
16. Check the LokiStack components:

    ```bash
    oc get pods -n openshift-logging -l app.kubernetes.io/instance=logging-loki
    ```
17. Verify the ClusterLogForwarder status:

    ```bash
    oc get clusterlogforwarder instance -n openshift-logging -o yaml | grep -A 5 conditions
    ```

    The status should show `Ready: True`.
18. Test log ingestion by viewing recent logs:

    ```bash
    oc logs -l component=collector -n openshift-logging --tail=20
    ```

## Install Cluster Observability Operator (Optional)

The Cluster Observability Operator (COO) adds a **Logs** tab under **Observe** in the OpenShift web console. This is optional — without it, you can still query logs using the CLI or Loki API.

### Install via WebUI

19. Go to Ecosystem -> Software Catalog -> filter for "Cluster Observability Operator" -> click the tile
20. Click Install
21. Leave all defaults and click Install
22. Wait for the Operator to install

### Install via YAML

19. Create the subscription:

    ```yaml
    apiVersion: operators.coreos.com/v1alpha1
    kind: Subscription
    metadata:
      name: cluster-observability-operator
      namespace: openshift-operators
    spec:
      channel: stable
      installPlanApproval: Automatic
      name: cluster-observability-operator
      source: redhat-operators
      sourceNamespace: openshift-marketplace
    ```

    ```bash
    oc apply -f coo-operator.yaml
    ```
20. Create the UIPlugin to enable the Logs tab:

    ```yaml
    apiVersion: observability.openshift.io/v1alpha1
    kind: UIPlugin
    metadata:
      name: logging
    spec:
      type: Logging
      logging:
        lokiStack:
          name: logging-loki
    ```

    ```bash
    oc apply -f uiplugin-logging.yaml
    ```
21. Verify the Logs tab is available:

    - Navigate to **Observe -> Logs** in the web console
    - You should be able to query application and infrastructure logs

## Log Access Control

By default, the Logging Operator does not grant all users access to logs. Grant access using the following cluster roles:

| Cluster Role                            | Access Granted           |
| --------------------------------------- | ------------------------ |
| `cluster-logging-application-view`    | Read application logs    |
| `cluster-logging-infrastructure-view` | Read infrastructure logs |
| `cluster-logging-audit-view`          | Read audit logs          |

Example — grant a user access to application logs:

```bash
oc adm policy add-cluster-role-to-user cluster-logging-application-view {{ username }}
```

Example — grant a group access to infrastructure logs:

```bash
oc adm policy add-cluster-role-to-group cluster-logging-infrastructure-view {{ group_name }}
```
