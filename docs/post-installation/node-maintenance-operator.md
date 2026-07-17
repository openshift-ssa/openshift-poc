# Node Maintenance Operator

[Node Maintenance Operator Documentation](https://docs.redhat.com/en/documentation/workload_availability_for_red_hat_openshift/latest/html/remediation_fencing_and_maintenance/node-maintenance-operator)

The Node Maintenance Operator provides a declarative way to place nodes into maintenance mode. When a `NodeMaintenance` custom resource is created, the operator cordons the node and drains evictable pods (including virtual machines). Deleting the CR resumes the node and makes it schedulable again.

This achieves the same result as `oc adm cordon` and `oc adm drain`, but through standard OpenShift custom resource processing.

## Install the Operator via WebUI

1. Go to Ecosystem -> Software Catalog -> filter for "Node Maintenance" -> click the tile
2. Click Install
3. Install into the `openshift-workload-availability` namespace (create it if it does not already exist from Workload Availability)
4. Leave the remaining defaults and click Install
5. Wait for the Operator to install

## Install the Operator via YAML

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: openshift-workload-availability
---
apiVersion: operators.coreos.com/v1
kind: OperatorGroup
metadata:
  name: workload-availability-operator-group
  namespace: openshift-workload-availability
---
apiVersion: operators.coreos.com/v1alpha1
kind: Subscription
metadata:
  name: node-maintenance-operator
  namespace: openshift-workload-availability
spec:
  channel: stable
  installPlanApproval: Automatic
  name: node-maintenance-operator
  source: redhat-operators
  sourceNamespace: openshift-marketplace
```

```bash
oc apply -f node-maintenance-operator.yaml
```

Wait for the operator to install:

```bash
oc get csv -n openshift-workload-availability -w
```

## Place a Node in Maintenance Mode

Create a `NodeMaintenance` CR for the target node:

```yaml
apiVersion: nodemaintenance.medik8s.io/v1beta1
kind: NodeMaintenance
metadata:
  name: node-maintenance-example
spec:
  nodeName: {{ node_name }}
  reason: Scheduled maintenance
```

```bash
oc apply -f node-maintenance.yaml
```

Check status:

```bash
oc get nodemaintenance
oc describe nodemaintenance node-maintenance-example
```

## Resume a Node from Maintenance Mode

Delete the `NodeMaintenance` CR to uncordon the node and allow workloads to schedule again:

```bash
oc delete nodemaintenance node-maintenance-example
```
