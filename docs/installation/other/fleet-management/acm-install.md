# Advanced Cluster Management

[Red Hat ACM Documentation](https://docs.redhat.com/en/documentation/red_hat_advanced_cluster_management_for_kubernetes/latest)

Red Hat Advanced Cluster Management (ACM) provides multicluster lifecycle management, governance, and observability. Installing ACM also automatically installs the multicluster engine operator.

!!! note
    Only one ACM hub cluster can exist per OpenShift cluster.

## Prerequisites

- Hub cluster is installed and storage is configured
- Cluster administrator privileges

## Install the Operator via WebUI

1. Go to Ecosystem -> Software Catalog -> filter for "Advanced Cluster Management" -> click the tile
2. Click Install
3. Leave all the defaults and click Install
4. Wait for the Operator to install
5. Go to Ecosystem -> Installed Operators -> click "Advanced Cluster Management for Kubernetes"
6. Click on the "MultiClusterHub" tab and then click "Create MultiClusterHub"
7. Leave all the defaults and click Create

!!! note
    It can take up to 10 minutes for the hub to finish deploying all components.

8. Wait for the status to show `Running`

## Install the Operator via YAML

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: open-cluster-management
---
apiVersion: operators.coreos.com/v1
kind: OperatorGroup
metadata:
  name: open-cluster-management
  namespace: open-cluster-management
spec:
  targetNamespaces:
    - open-cluster-management
---
apiVersion: operators.coreos.com/v1alpha1
kind: Subscription
metadata:
  name: acm-operator-subscription
  namespace: open-cluster-management
spec:
  sourceNamespace: openshift-marketplace
  source: redhat-operators
  channel: release-2.12
  installPlanApproval: Automatic
  name: advanced-cluster-management
```

```bash
oc apply -f acm-operator.yaml
```

Wait for the operator to install:

```bash
oc get csv -n open-cluster-management -w
```

The `PHASE` should show `Succeeded`.

## Create the MultiClusterHub

```yaml
apiVersion: operator.open-cluster-management.io/v1
kind: MultiClusterHub
metadata:
  name: multiclusterhub
  namespace: open-cluster-management
spec: {}
```

```bash
oc apply -f multiclusterhub.yaml
```

Monitor the status:

```bash
oc get mch -n open-cluster-management -w
```

The status should show `Running`.

## Verify the Installation

```bash
oc get pods -n open-cluster-management
oc get route multicloud-console -n open-cluster-management -o jsonpath='{.spec.host}'
```

## Enable Bare Metal Provisioning

Enable bare metal provisioning for spoke cluster deployment:

```yaml
apiVersion: metal3.io/v1alpha1
kind: Provisioning
metadata:
  name: provisioning-configuration
spec:
  provisioningNetwork: "Disabled"
  watchAllNamespaces: true
```

```bash
oc apply -f provisioning.yaml
```

## Import an Existing Cluster

To import an existing cluster (one not provisioned by ACM) into the hub:

1. Create the ManagedCluster resource on the hub:

  ```yaml
  apiVersion: cluster.open-cluster-management.io/v1
  kind: ManagedCluster
  metadata:
    name: {{ managed_cluster_name }}
  spec:
    hubAcceptsClient: true
  ```

  ```bash
  oc apply -f managed-cluster.yaml
  ```

2. Wait for ACM to generate the import resources:

  ```bash
  oc get secret -n {{ managed_cluster_name }} | grep import
  ```

3. Extract the import YAML and apply it on the target cluster:

  ```bash
  oc get secret {{ managed_cluster_name }}-import -n {{ managed_cluster_name }} \
    -o jsonpath='{.data.import\.yaml}' | base64 -d > import.yaml

  oc apply -f import.yaml --kubeconfig={{ managed_cluster_kubeconfig }}
  ```

4. Verify the managed cluster is connected:

  ```bash
  oc get managedcluster {{ managed_cluster_name }}
  ```

  The `HubAcceptedManagedCluster` condition should be `True` and the cluster should show as `Available`.
