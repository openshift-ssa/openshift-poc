# Network Observability

[Network Observability Documentation](https://docs.redhat.com/en/documentation/openshift_container_platform/latest/html/network_observability/index)

The Network Observability Operator captures cluster network flows with an eBPF agent on each node, enriches them with Kubernetes metadata, and shows topology, metrics, and traffic tables in the OpenShift web console under **Observe -> Network Traffic**.

| Component                        | Namespace                      | Purpose                                                                  |
| -------------------------------- | ------------------------------ | ------------------------------------------------------------------------ |
| Loki Operator                    | `openshift-operators-redhat`   | Manages LokiStack (cluster-wide; reuse if already installed for logging) |
| LokiStack                        | `netobserv-loki`               | Stores flow logs with the `openshift-network` tenant                     |
| Network Observability Operator   | `openshift-netobserv-operator` | Manages the `FlowCollector` CR                                           |
| Flow pipeline and console plugin | `netobserv`                    | Receives, enriches, and displays flows                                   |
| eBPF agents                      | `netobserv-privileged`         | DaemonSet that samples packets on every node                             |

!!! warning "Use a dedicated LokiStack"
    Do not reuse the [Logging](logging.md) LokiStack. Network Observability requires its own LokiStack with `tenants.mode: openshift-network`. The Loki Operator itself can be shared.

Loki is recommended. Without Loki you still get dashboards, topology, and exporters, but you lose the traffic flows table, per-pod filtering, and packet-drop statistics.

| Capability                         | With Loki | Without Loki |
| ---------------------------------- | --------- | ------------ |
| Flow-based metrics and dashboards  | Yes       | Yes          |
| Topology view                      | Yes       | Yes          |
| Traffic flows table                | Yes       | No           |
| Per-pod filtering and aggregations | Yes       | No           |
| Packet-drop statistics             | Yes       | No           |
| Kafka / IPFIX / OTLP exporters     | Yes       | Yes          |

## Prerequisites

- Cluster administrator privileges
- OVN-Kubernetes as the cluster network plugin
- [Storage](storage/index.md) configured (CSI driver installed)
- A StorageClass for LokiStack internal PVCs (block storage, `ReadWriteOnce`)
- S3-compatible object storage for flow data (ODF NooBaa, NetApp StorageGRID, AWS S3, etc.)
- Loki Operator 6.0 or later (`stable-6.6` in this guide)

!!! warning "LokiStack Requires Two Types of Storage"
    - **Block storage** (via StorageClass): WAL, index cache, and compactor working space
    - **Object storage** (S3-compatible): flow log chunks and indices

    Missing either type causes silent failures where LokiStack reports `Ready` but flows are not stored.

## Deployment Sizing

| Size             | Use case              | Notes                                        |
| ---------------- | --------------------- | -------------------------------------------- |
| `1x.demo`        | POC / compact cluster | No HA; use on 3-node or small labs           |
| `1x.extra-small` | Small cluster         | Typical starting size for a POC with workers |
| `1x.small`       | Medium cluster        | Higher ingest and query load                 |

!!! tip
    For a POC, start with `1x.demo` on compact or single-node clusters, or `1x.extra-small` otherwise. Leave eBPF sampling at `50` (1 in 50 packets) unless you need denser data.

## Install the Loki Operator

Skip this section if the Loki Operator is already installed for [Logging](logging.md). Confirm with:

```bash
oc get csv -n openshift-operators-redhat | grep loki
```

The `PHASE` should show `Succeeded`.

### Install via WebUI

1. Go to Ecosystem -> Software Catalog -> filter for "Loki Operator" -> click the "Loki Operator" tile (provided by Red Hat)
2. Click Install
3. Select `stable-6.6` as the Update channel
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
     channel: stable-6.6
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

Create a dedicated bucket and secret named `loki-s3` in `netobserv-loki`. This secret is separate from the logging Loki secret.

1. Create the namespace:

   ```bash
   oc create namespace netobserv-loki
   oc label namespace netobserv-loki openshift.io/cluster-monitoring=true
   ```

### Using ODF NooBaa

2. Create an ObjectBucketClaim:

   ```yaml
   apiVersion: objectbucket.io/v1alpha1
   kind: ObjectBucketClaim
   metadata:
     name: netobserv-loki-bucket
     namespace: netobserv-loki
   spec:
     bucketName: netobserv-loki-bucket
     storageClassName: openshift-storage.noobaa.io
   ```

   ```bash
   oc apply -f netobserv-loki-bucket.yaml
   ```

3. Wait for the bucket to be bound, then create the secret. Loki talks to NooBaa in-cluster over the service and the cluster service CA:

   ```bash
   ACCESS_KEY=$(oc get secret netobserv-loki-bucket -n netobserv-loki -o jsonpath='{.data.AWS_ACCESS_KEY_ID}' | base64 -d)
   SECRET_KEY=$(oc get secret netobserv-loki-bucket -n netobserv-loki -o jsonpath='{.data.AWS_SECRET_ACCESS_KEY}' | base64 -d)

   oc create secret generic loki-s3 \
     -n netobserv-loki \
     --from-literal=bucketnames="netobserv-loki-bucket" \
     --from-literal=endpoint="https://s3.openshift-storage.svc:443" \
     --from-literal=access_key_id="$ACCESS_KEY" \
     --from-literal=access_key_secret="$SECRET_KEY"
   ```

### Using S3 Compatible Storage (NetApp StorageGRID, etc.)

2. Create the secret directly with your storage credentials:

   ```bash
   oc create secret generic loki-s3 \
     -n netobserv-loki \
     --from-literal=bucketnames="{{ bucket_name }}" \
     --from-literal=endpoint="{{ s3_endpoint_url }}" \
     --from-literal=access_key_id="{{ access_key }}" \
     --from-literal=access_key_secret="{{ secret_key }}" \
     --from-literal=forcepathstyle="true"
   ```

!!! note
    The `forcepathstyle="true"` parameter is required for S3-compatible storage (not needed for AWS S3).

### TLS CA Bundle (If Required)

3. If your object storage uses self-signed or internal certificates, create a ConfigMap with the CA bundle:

   ```bash
   oc create configmap loki-s3-ca-bundle \
     -n netobserv-loki \
     --from-file=ca-bundle.crt=./storage-ca.crt
   ```

   You will reference this in the LokiStack CR under `spec.storage.tls`.

## Create the LokiStack

4. Create the LokiStack custom resource. `tenants.mode` **must** be `openshift-network`:

   ```yaml
   apiVersion: loki.grafana.com/v1
   kind: LokiStack
   metadata:
     name: loki
     namespace: netobserv-loki
   spec:
     size: 1x.extra-small
     storage:
       schemas:
         - version: v13
           effectiveDate: "2024-10-01"
       secret:
         name: loki-s3
         type: s3
       tls:
         caName: openshift-service-ca.crt
         caKey: service-ca.crt
     storageClassName: {{ storage_class }}
     tenants:
       mode: openshift-network
   ```

!!! note "TLS for object storage"
    `caName` references a **ConfigMap** (not a Secret) in the LokiStack namespace containing the CA bundle. `caKey` is the key within that ConfigMap holding the CA cert (defaults to `service-ca.crt` if omitted).

    - For in-cluster ODF NooBaa (`https://s3.openshift-storage.svc:443`), use `caName: openshift-service-ca.crt` with `caKey: service-ca.crt`.
    - For self-signed S3-compatible storage, set `caName` to the ConfigMap you created (e.g. `loki-s3-ca-bundle`) and set `caKey` to match the key in that ConfigMap.
    - For public AWS S3, remove the `tls` block entirely.

5. Apply the LokiStack CR:

   ```bash
   oc apply -f netobserv-lokistack.yaml
   ```

6. Wait for the LokiStack to be ready:

   ```bash
   oc get lokistack loki -n netobserv-loki -w
   ```

7. Verify PVCs are bound:

   ```bash
   oc get pvc -n netobserv-loki
   ```

   All PVCs should show `Bound`.

## Install the Network Observability Operator

The operator must be installed in `openshift-netobserv-operator`. Do not install it in `openshift-operators`.

### Install via WebUI

1. Go to Ecosystem -> Software Catalog -> filter for "Network Observability" -> click the "Network Observability Operator" tile (provided by Red Hat)
2. Click Install
3. Select the `stable` channel
4. Ensure the namespace is `openshift-netobserv-operator`
5. Select "Enable Operator recommended cluster monitoring on this namespace"
6. Click Install
7. Wait for the Operator to install

### Install via YAML

1. Create the namespace, operator group, and subscription:

   ```yaml
   apiVersion: v1
   kind: Namespace
   metadata:
     name: openshift-netobserv-operator
     labels:
       openshift.io/cluster-monitoring: "true"
   ---
   apiVersion: operators.coreos.com/v1
   kind: OperatorGroup
   metadata:
     name: openshift-netobserv-operator
     namespace: openshift-netobserv-operator
   spec:
     upgradeStrategy: Default
   ---
   apiVersion: operators.coreos.com/v1alpha1
   kind: Subscription
   metadata:
     name: netobserv-operator
     namespace: openshift-netobserv-operator
   spec:
     channel: stable
     installPlanApproval: Automatic
     name: netobserv-operator
     source: redhat-operators
     sourceNamespace: openshift-marketplace
   ```

   ```bash
   oc apply -f netobserv-operator.yaml
   ```

2. Wait for the operator:

   ```bash
   oc get csv -n openshift-netobserv-operator -w
   ```

   The `PHASE` should show `Succeeded`.

## Create the FlowCollector

Only one `FlowCollector` is allowed per cluster, and it must be named `cluster`. Changing it later restarts the eBPF agents and flow pipeline, so set sampling and Loki references at create time.

### Create via WebUI

1. Go to Ecosystem -> Installed Operators -> Network Observability Operator
2. Click the **Flow Collector** tab
3. Click **Create FlowCollector** and follow the setup wizard, or switch to YAML and paste the example below
4. Confirm Loki is enabled, mode is `LokiStack`, name is `loki`, and namespace is `netobserv-loki`
5. Click Create

### Create via YAML

```yaml
apiVersion: flows.netobserv.io/v1beta2
kind: FlowCollector
metadata:
  name: cluster
spec:
  namespace: netobserv
  deploymentModel: Service
  networkPolicy:
    enable: true
  agent:
    type: eBPF
    ebpf:
      sampling: 50
      privileged: false
      features: []
  processor:
    addZone: false
    subnetLabels:
      openShiftAutoDetect: true
      customLabels: []
    consumerReplicas: 1
  loki:
    enable: true
    mode: LokiStack
    lokiStack:
      name: loki
      namespace: netobserv-loki
  consolePlugin:
    enable: true
  exporters: []
```

```bash
oc apply -f flowcollector.yaml
```

!!! note "POC defaults"
    `consumerReplicas: 1` and `sampling: 50` keep resource use down on a lab cluster. Production extra-small deployments typically use 3 processor replicas. A sampling value of `0` or `1` captures every packet and is much more expensive.

The operator creates `netobserv` and `netobserv-privileged`. eBPF agents run in `netobserv-privileged`; the flowlogs-pipeline and console plugin run in `netobserv`.

## Verify

1. Check the FlowCollector status:

   ```bash
   oc get flowcollector cluster
   ```

   The status should report that the collector is ready.

2. Check eBPF agents on every node:

   ```bash
   oc get pods -n netobserv-privileged
   ```

   You should see one `netobserv-ebpf-agent` pod per node in `Running` state.

3. Check the pipeline and console plugin:

   ```bash
   oc get pods -n netobserv
   ```

4. Check the LokiStack components:

   ```bash
   oc get pods -n netobserv-loki
   ```

5. Open the web console and go to **Observe -> Network Traffic**.

   If the view shows "No results", click **Clear all filters**. A quiet cluster with the default application-traffic filter can look empty.

## Using Network Traffic

The **Network Traffic** page includes:

- **Overview** — aggregated bytes, packets, and drop statistics
- **Traffic flows** — per-flow table (requires Loki)
- **Topology** — graph of namespaces, owners, and pods

Use the built-in quick filters (Applications, Infrastructure, Pods, Services) or query by namespace, name, kind, port, or protocol.

## Optional Features

These require a FlowCollector change and restart the agents.

### Packet drops, DNS, and RTT

Privileged mode is required for packet drops and some other features:

```yaml
spec:
  agent:
    ebpf:
      privileged: true
      features:
        - PacketDrop
        - DNSTracking
        - FlowRTT
```

| Feature       | What it adds                     | Privileged required |
| ------------- | -------------------------------- | ------------------- |
| `PacketDrop`  | Dropped-packet counters on flows | Yes                 |
| `DNSTracking` | DNS latency and response codes   | No                  |
| `FlowRTT`     | TCP smoothed RTT                 | No                  |

### Secondary networks and virtual machines

Default pod-network traffic from VMs is captured automatically. Secondary interfaces (SR-IOV, localnet / CUDN, additional networks) need privileged agents. If enrichment is incomplete, index the secondary network by MAC (and IP if MACs overlap):

```yaml
spec:
  agent:
    ebpf:
      privileged: true
  processor:
    advanced:
      secondaryNetworks:
        - name: {{ namespace }}/{{ network_attachment_definition }}
          index:
            - MAC
```

`name` must match the `k8s.v1.cni.cncf.io/network-status` annotation on the virt-launcher pod (`namespace/nad-name`).

See [Networking](networking.md) and [OpenShift Virtualization](virtualization.md) for how those secondary networks are created.

## Access Control

Cluster administrators can view all flows. Grant others access with:

| Role                       | Scope                                            |
| -------------------------- | ------------------------------------------------ |
| `netobserv-loki-reader`    | Cluster-wide flow logs in Loki                   |
| `cluster-monitoring-view`  | Cluster-wide Prometheus metrics                  |
| `netobserv-metrics-reader` | Metrics; bind as a cluster role or per namespace |

Cluster-wide access for a non-admin user:

```bash
oc adm policy add-cluster-role-to-user netobserv-loki-reader {{ username }}
oc adm policy add-cluster-role-to-user cluster-monitoring-view {{ username }}
oc adm policy add-cluster-role-to-user netobserv-metrics-reader {{ username }}
```

Per-namespace metrics for a developer:

```bash
oc adm policy add-cluster-role-to-user netobserv-loki-reader {{ username }}
oc adm policy add-role-to-user netobserv-metrics-reader {{ username }} -n {{ namespace }}
```

## Uninstall

1. Delete the FlowCollector:

   ```bash
   oc delete flowcollector cluster
   ```

2. Uninstall the Network Observability Operator (Ecosystem -> Installed Operators -> Uninstall), or:

   ```bash
   oc delete subscription netobserv-operator -n openshift-netobserv-operator
   oc delete csv -n openshift-netobserv-operator -l operators.coreos.com/netobserv-operator.openshift-netobserv-operator
   ```

3. Delete leftover namespaces and the FlowCollector CRD if you are fully removing the product:

   ```bash
   oc delete project openshift-netobserv-operator netobserv netobserv-privileged
   oc delete crd flowcollectors.flows.netobserv.io
   ```

The Loki Operator, the `netobserv-loki` LokiStack, object-storage data, and PVCs are not removed automatically. Delete those separately if they are not shared with other workloads.
